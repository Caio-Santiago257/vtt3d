"""Planta do mapa "Encruzilhada da Floresta": relevo, estradas, poças, mistura de texturas, sombra das árvores,
custo do terreno, colisão e a posição de cada árvore, pedra e planta (instâncias do kit feito no Blender).

Baseado na referência Forest_Crossroads (fontes/recebidos/estrada-referencias/):
  - uma estrada antiga de lajes de pedra, meio coberta de lama, corta a mata de oeste para leste;
  - outra desce do norte e se cruza com ela numa encruzilhada com uma placa de madeira;
  - beiras de terra batida com blocos de pedra soltos (restos do meio-fio), samambaias e florzinhas;
  - mata de pinheiros (alguns quase pretos), árvores de outono alaranjadas, arbustos amarelos,
    uma árvore morta branca, pedras grandes e poças escuras na mata;
  - em volta do mapa a mata continua e, mais longe, abre numa planície (o fundo panorâmico vem do Blender).

Medidas: 64 x 64 quadrados (96 x 96 m). 1 quadrado = 2 unidades = 1,5 m. Alturas em unidades.
Saídas:
  public/assets/maps/estrada/dados.json      relevo, poças, colisão, instâncias (lido pelo jogo)
  public/assets/maps/estrada/mistura_a.png   terra / grama / chão da mata (RGB)
  public/assets/maps/estrada/mistura_b.png   lajes da estrada / sombra das árvores / musgo (RGB)
  mapas/prontos/estrada-floresta.json        o mapa pronto (carregado pelo servidor)
Rodar: python3 fontes/mapas/estrada_gerar.py
"""
import base64, json, math, os
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy import ndimage
from scipy.spatial import cKDTree

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
OUT = os.path.join(ROOT, 'public', 'assets', 'maps', 'estrada')
SQ = 64; G = 2.0; SIZE = SQ * G         # 128 unidades
EXT = 96                                 # a mata continua 96 unidades (72 m) além da borda
RES = 1.0
X0 = -EXT
NG = int((SIZE + 2 * EXT) / RES) + 1     # 321 pontos por lado
SUN = np.array([0.5, -0.35]) / math.hypot(0.5, 0.35)   # para onde as sombras caem (o sol do jogo vem de -x, +z)
SUN_K = 0.61                             # comprimento da sombra por unidade de altura
rng = np.random.default_rng(1848)

gx = X0 + np.arange(NG) * RES
XX, ZZ = np.meshgrid(gx, gx)
CX = CZ = SIZE / 2

def vnoise(scale, seed):
    n = int((SIZE + 2 * EXT) / scale) + 4
    lat = np.random.default_rng(seed).random((n, n))
    return ndimage.map_coordinates(lat, [(ZZ - X0) / scale, (XX - X0) / scale], order=3, mode='reflect')

def fbm(scale, seed, oct=4):
    v = sum(vnoise(scale / 2 ** o, seed + o * 17) * 0.5 ** o for o in range(oct))
    return (v - v.min()) / (v.max() - v.min())

def sstep(a, b, x): t = np.clip((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t)

def sample(A, x, z, order=1):
    return ndimage.map_coordinates(A, [np.atleast_1d((np.asarray(z) - X0) / RES), np.atleast_1d((np.asarray(x) - X0) / RES)], order=order, mode='nearest')

# ---------------------------------------------------------------- estradas (em quadrados; saem do mapa)
def catmull(pts, step=0.5):
    P = np.array(pts, float); out = []
    P = np.vstack([P[0] * 2 - P[1], P, P[-1] * 2 - P[-2]])
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        n = max(2, int(np.linalg.norm(p2 - p1) / step))
        for t in np.linspace(0, 1, n, endpoint=False):
            t2, t3 = t * t, t * t * t
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    out.append(P[-2]); return np.array(out)

J = np.array([36.0, 33.0]) * G           # a encruzilhada
ROADS = {
    # leste-oeste: entra pelo oeste, sobe até a encruzilhada e sai pelo leste ondulando
    'oeste': catmull([(-50, 47), (-20, 46), (0, 44.5), (10, 42), (20, 38.5), (29, 35), (36, 33)]) * G,
    'leste': catmull([(36, 33), (44, 31.5), (52, 33), (60, 31), (68, 28), (90, 24), (115, 25)]) * G,
    # norte-sul: desce do norte, cruza e segue para o sudoeste (mais estreita)
    'norte': catmull([(44, -50), (42, -20), (40, 0), (39, 12), (37, 24), (36, 33)]) * G,
    'sul': catmull([(36, 33), (34, 42), (30, 51), (27, 64), (22, 90), (20, 115)]) * G,
}
HALF = {'oeste': 4.6, 'leste': 4.6, 'norte': 3.6, 'sul': 3.4}   # meia largura das lajes, em unidades

def road_fields():
    pts = np.vstack([p for p in ROADS.values()]); half = np.concatenate([np.full(len(p), HALF[k]) for k, p in ROADS.items()])
    tree = cKDTree(pts)
    d, i = tree.query(np.stack([XX.ravel(), ZZ.ravel()], 1))
    d = d.reshape(XX.shape); hw = half[i].reshape(XX.shape)
    wob = (fbm(10, 71) - 0.5) * 2.2 + (fbm(3, 72) - 0.5) * 0.8             # borda irregular
    rd = d - hw - wob                                                        # < 0 dentro das lajes
    return rd, tree, pts, half

# ---------------------------------------------------------------- relevo
def build():
    print('relevo...')
    big = fbm(70, 11) - 0.5; mid = fbm(24, 12) - 0.5; small = fbm(7, 13, 3) - 0.5
    rr = np.hypot(XX - CX, ZZ - CZ)
    outk = sstep(80, 190, np.maximum(np.abs(XX - CX), np.abs(ZZ - CZ)) + 0 * rr)   # longe do mapa: morros maiores
    H = big * (5.0 + 10.0 * outk) + mid * 2.2 + small * 0.5
    H += sstep(150, 205, np.maximum(np.abs(XX - CX), np.abs(ZZ - CZ))) * 6.0         # a borda do terreno sobe (esconde o fim)
    rd, rtree, rpts, rhalf = road_fields()
    # a estrada segue o relevo suavizado, um pouco afundada; os barrancos da mata ficam acima dela
    Hs = ndimage.gaussian_filter(H, 9)
    road = sstep(3.5, -0.5, rd)
    bank = sstep(0.0, 3.0, rd) * sstep(9.0, 3.0, rd)
    H = H * (1 - road) + (Hs - 0.25) * road + bank * 0.35
    ruts = (fbm(4, 14, 2) - 0.5) * 0.12 * road
    H += ruts
    # clareira da encruzilhada: mais plana
    dj = np.hypot(XX - J[0], ZZ - J[1])
    cl = sstep(22, 10, dj)
    H = H * (1 - cl * 0.7) + Hs * cl * 0.7
    # poças: cavadas na mata e nas rodeiras
    ponds = []
    spots = [(26, 21, 3.4), (55, 15, 2.6), (47, 47, 4.2), (14, 54, 2.8), (58, 54, 3.0), (6, 14, 2.4), (30, 58, 2.6),
             (49, 37, 1.6), (22, 42.5, 1.5), (9, 30, 2.0), (61, 40, 2.2), (42, 6, 2.6), (-14, 20, 4.0), (80, 52, 4.5), (20, -16, 3.5)]
    for (sx, sz, r) in spots:
        x, z, r = sx * G, sz * G, r * G * 0.5
        ang = np.arctan2(ZZ - z, XX - x); dd = np.hypot(XX - x, ZZ - z)
        rr2 = r * (1 + 0.28 * np.sin(ang * 3 + sx) + 0.15 * np.sin(ang * 5 + sz))
        prof = sstep(rr2 * 1.25, rr2 * 0.3, dd)
        rim = float(H[(dd > r * 1.3) & (dd < r * 1.7)].min())
        depth = 0.7 + 0.06 * r
        H = np.minimum(H, H * (1 - prof) + (rim - depth) * prof) if True else H
        ponds.append([round(x, 2), round(z, 2), round(r * 1.5, 2), round(rim - 0.1, 3)])
    M = dict(rd=rd, road=road, bank=bank, clear=cl, outk=outk, rtree=rtree, rpts=rpts, dj=dj)
    return H, M, ponds

def water_level(ponds, x, z):
    for px, pz, r, wl in ponds:
        if (x - px) ** 2 + (z - pz) ** 2 < r * r: return wl
    return -999

# ---------------------------------------------------------------- vegetação e objetos (instâncias do kit)
def scatter(H, M, ponds):
    print('vegetação...')
    inst = {}
    obstacles = []
    occ = []                                # (x, z, r) para não encavalar troncos/pedras
    def put(model, x, z, s=1.0, ry=None, tint=1.0, y=None):
        if y is None: y = float(sample(H, x, z)[0])
        inst.setdefault(model, []).append([round(x, 2), round(y, 2), round(z, 2), round(rng.uniform(0, 6.283) if ry is None else ry, 2), round(s, 2), round(tint, 2)])
    rd = M['rd']
    def rdist(x, z): return float(sample(rd, x, z)[0])
    def inpond(x, z, pad=0.0):
        return any((x - px) ** 2 + (z - pz) ** 2 < (r + pad) ** 2 for px, pz, r, _ in ponds)
    def free(x, z, r):
        return all((x - a) ** 2 + (z - b) ** 2 > (r + c) ** 2 for a, b, c in occ[-4000:]) if occ else True
    inside = lambda x, z, m=0: -m <= x <= SIZE + m and -m <= z <= SIZE + m
    dens = fbm(26, 31); dens2 = fbm(9, 32)
    shade_list = []                          # (x, z, raio da copa, altura) para a sombra no chão

    # --- pinheiros: grade com tremido, aceitos pela densidade (clareiras onde a densidade é baixa)
    step = 3.1
    for gz in np.arange(X0 + 2, SIZE + EXT - 2, step):
        for gxx in np.arange(X0 + 2, SIZE + EXT - 2, step):
            x = gxx + rng.uniform(-1.3, 1.3); z = gz + rng.uniform(-1.3, 1.3)
            ins = inside(x, z)
            dmap = max(0, max(-x, x - SIZE, -z, z - SIZE))          # distância para fora do mapa
            d = float(sample(dens, x, z)[0]) * 0.7 + float(sample(dens2, x, z)[0]) * 0.3
            # dentro do mapa: mata com clareiras; logo fora: mata fechada; longe: abre em planície ao sul e leste
            if ins: p = sstep(0.36, 0.62, d) * 0.85
            elif dmap < 34: p = 0.55 + 0.4 * sstep(0.3, 0.5, d)
            else:
                far_open = sstep(40, 80, dmap) * (0.75 if (z > SIZE * 0.6 or x > SIZE * 0.7) else 0.25)
                p = (0.5 + 0.4 * sstep(0.3, 0.5, d)) * (1 - far_open)
            if dmap > 12 and rng.random() < 0.45: continue          # longe: mais espaçado (e mais leve)
            if rng.random() > p: continue
            if rdist(x, z) < 2.6 + rng.uniform(0, 2.5): continue
            if float(sample(M['dj'], x, z)[0]) < 16: continue
            if inpond(x, z, 1.2): continue
            if ins and math.hypot(x - SPAWN[0], z - SPAWN[1]) < 10: continue
            far = dmap > 12
            r = rng.random()
            s = rng.uniform(0.75, 1.25) * (1.1 if far else 1.0)
            dark = rng.random() < (0.22 if ins else 0.3)
            tint = rng.uniform(0.32, 0.5) if dark else rng.uniform(0.82, 1.08)
            model = ('pinho_longe' if far else ('pinho_a' if r < 0.45 else 'pinho_b' if r < 0.8 else 'pinho_c'))
            put(model, x, z, s, tint=tint)
            occ.append((x, z, 0.7 * s))
            hgt = {'pinho_a': 24, 'pinho_b': 19, 'pinho_c': 14, 'pinho_longe': 22}[model] * s
            rad = {'pinho_a': 4.6, 'pinho_b': 3.9, 'pinho_c': 3.0, 'pinho_longe': 4.4}[model] * s
            shade_list.append((x, z, rad, hgt))
            if inside(x, z, 1): obstacles.append([round(x, 2), round(z, 2), round(0.55 * s, 2)])
    print('  pinheiros dentro do mapa:', sum(1 for k in ('pinho_a', 'pinho_b', 'pinho_c') for v in inst.get(k, []) if inside(v[0], v[2])))
    print('  pinheiros:', sum(len(inst.get(k, [])) for k in ('pinho_a', 'pinho_b', 'pinho_c', 'pinho_longe')))

    # --- árvores de outono, árvore morta, arbustos (como na referência: perto das bordas da estrada)
    specials = [('outono', 50.5, 23.5), ('outono', 55, 25.5), ('outono', 58.5, 37), ('outono', 43, 9), ('outono', 51, 9.5), ('outono', 12, 23),
                ('outono', 18, 60), ('outono', 62.5, 11), ('morta', 47, 13), ('morta', 62, 3.5), ('morta', 9, 39), ('outono', 83, 40), ('outono', -10, 60)]
    for kind, sx, sz in specials:
        x, z = sx * G, sz * G
        if kind == 'outono':
            s = rng.uniform(0.9, 1.2); put('arvore_outono', x, z, s); shade_list.append((x, z, 5.2 * s, 16 * s))
            obstacles.append([x, z, 0.6 * s]); occ.append((x, z, 3.0))
        else:
            put('arvore_morta', x, z, rng.uniform(0.9, 1.15)); obstacles.append([x, z, 0.7]); occ.append((x, z, 2.0)); shade_list.append((x, z, 2.5, 10))
    # arbustos: amarelos e verdes, na beira da mata
    for _ in range(3000):
        x, z = rng.uniform(-30, SIZE + 30, 2)
        rdx = rdist(x, z)
        if rdx < 2.0 or inpond(x, z, 0.8) or not free(x, z, 1.2): continue
        edge = sstep(12, 3, rdx) + sstep(0.4, 0.6, float(sample(dens, x, z)[0])) * 0.4
        if rng.random() > edge * 0.35: continue
        model = 'arbusto_amarelo' if rng.random() < 0.35 else 'arbusto_verde'
        s = rng.uniform(0.7, 1.3); put(model, x, z, s); occ.append((x, z, 1.4 * s)); shade_list.append((x, z, 1.8 * s, 3 * s))

    # --- pedras grandes (algumas na beira da estrada, como na referência)
    big_spots = [(30, 3), (17.5, 31), (22.5, 61), (51.5, 17), (35, 44.5), (48.5, 43.5), (59.5, 49), (5, 47), (66, 20), (40, 36.5), (7, 9), (28.5, 47.5), (44, 57)]
    for sx, sz in big_spots:
        x, z = sx * G + rng.uniform(-1, 1), sz * G + rng.uniform(-1, 1)
        if inpond(x, z, 1): continue
        s = rng.uniform(0.85, 1.35); put('pedra_%d' % rng.integers(1, 5), x, z, s); obstacles.append([round(x, 2), round(z, 2), round(1.5 * s, 2)]); occ.append((x, z, 2 * s))
    for _ in range(140):                       # pedras médias e pequenas espalhadas
        x, z = rng.uniform(-60, SIZE + 60, 2)
        if inpond(x, z, 0.5) or rdist(x, z) < -1 or not free(x, z, 0.8): continue
        if rng.random() < 0.5:
            s = rng.uniform(0.35, 0.7); put('pedra_%d' % rng.integers(1, 5), x, z, s); occ.append((x, z, s * 1.5))
            if inside(x, z) and s > 0.55: obstacles.append([round(x, 2), round(z, 2), round(1.3 * s, 2)])
        else: put('seixo_%d' % rng.integers(1, 3), x, z, rng.uniform(0.6, 1.4))

    # --- blocos de pedra do meio-fio, soltos ao longo das duas beiras de cada estrada (às vezes em montinhos)
    for name, P in ROADS.items():
        hw = HALF[name]
        for i in range(1, len(P) - 1, 1):
            if rng.random() > 0.55: continue
            t = P[i + 1] - P[i - 1]; t /= np.linalg.norm(t) + 1e-9; nrm = np.array([-t[1], t[0]])
            for side in (-1, 1):
                if rng.random() < 0.5: continue
                off = hw + rng.uniform(-0.6, 1.4)
                x, z = P[i] + nrm * side * off + t * rng.uniform(-0.5, 0.5)
                if not inside(x, z, 40) or inpond(x, z, 0.3): continue
                if rng.random() < 0.06: put('blocos_monte', x, z, rng.uniform(0.8, 1.2))
                else: put('bloco_%d' % rng.integers(1, 4), x, z, rng.uniform(0.6, 1.25), y=float(sample(H, x, z)[0]) - 0.05)
    # --- troncos caídos e tocos
    nlog = 0
    for _ in range(1500):
        if nlog >= 34: break
        x, z = rng.uniform(-40, SIZE + 40, 2)
        if rdist(x, z) < 3 or inpond(x, z, 1) or not free(x, z, 1.6): continue
        nlog += 1
        if rng.random() < 0.5:
            s = rng.uniform(0.8, 1.3); put('tronco_caido', x, z, s); occ.append((x, z, 2.5 * s))
            if inside(x, z): obstacles.append([round(x, 2), round(z, 2), round(0.9 * s, 2)])
        else:
            put('toco', x, z, rng.uniform(0.8, 1.2)); occ.append((x, z, 0.8))
            if inside(x, z): obstacles.append([round(x, 2), round(z, 2), 0.6])
    # --- placa da encruzilhada (no canto nordeste do cruzamento, virada para quem chega pelo oeste)
    px, pz = J[0] + 7.5, J[1] - 7.0
    put('placa', px, pz, 1.0, ry=0.55); obstacles.append([round(px, 2), round(pz, 2), 0.45])
    # --- objetos modelados no Blender do Caio (props.glb): carroça quebrada na beira da estrada do oeste, caixotes
    # caídos dela, uma fogueira apagada na clareira, o marco de pedra da estrada leste e um trecho de cerca velha
    for model, sx, sz, ry, r in (('carroca', 25.5, 39.8, 0.35, 3.2), ('caixotes', 22.0, 41.8, 1.2, 1.3), ('fogueira', 44.5, 25.5, 0.0, 1.4),
                                 ('marco', 47.5, 34.6, 1.6, 0.5), ('cerca', 54.0, 20.0, 0.25, 0.0), ('cerca', 57.0, 21.0, 0.6, 0.0)):
        x, z = sx * G, sz * G
        put(model, x, z, 1.0, ry=ry)
        if r: obstacles.append([round(x, 2), round(z, 2), r])

    # --- plantas rasteiras: samambaias, touceiras com flor, capim; mais densas na beira das estradas e da mata
    shade_pts = np.array([(a, b) for a, b, _, _ in shade_list])
    stree = cKDTree(shade_pts)
    counts = {'samambaia': 0, 'flores': 0, 'capim': 0}
    tries = 26000
    xs = rng.uniform(-48, SIZE + 48, tries); zs = rng.uniform(-48, SIZE + 48, tries)
    rds = sample(rd, xs, zs); dn = sample(dens, xs, zs)
    for x, z, rdx, dd in zip(xs, zs, rds, dn):
        if rdx < -0.8 + rng.uniform(0, 1.2): continue           # um pouco invade as lajes
        if inpond(x, z, 0.2): continue
        near_road = sstep(8, 0.5, rdx)
        nt = len(stree.query_ball_point((x, z), 3.0))
        p = 0.12 + near_road * 0.55 + min(nt, 3) * 0.08
        if rng.random() > p: continue
        r = rng.random()
        if r < 0.38 and dd > 0.35: model = 'samambaia'
        elif r < 0.68: model = 'flores'
        else: model = 'capim'
        counts[model] += 1
        put(model, x, z, rng.uniform(0.7, 1.35), tint=rng.uniform(0.8, 1.1))
    print('  rasteiras:', counts)
    return inst, obstacles, shade_list

# ---------------------------------------------------------------- mistura de texturas e sombra das árvores
def splat(H, M, ponds, shade_list):
    print('mistura de texturas e sombras...')
    rd = M['rd']
    n1 = fbm(8, 41); n2 = fbm(20, 42); n3 = fbm(3, 43, 3)
    paving = sstep(0.6, -0.8, rd + (n3 - 0.5) * 1.5)                         # lajes, com falhas
    paving *= 1 - sstep(0.7, 0.85, n1) * 0.85                               # trechos sem laje (só terra)
    verge = sstep(4.5 + n2 * 3, 0.0, rd) * (1 - paving)                     # beira de terra
    # chão da mata: sob as copas, mais serrapilheira; nas clareiras, grama
    can = np.zeros_like(H)
    for x, z, r, h in shade_list:
        i0, j0 = int((x - X0) / RES), int((z - X0) / RES); R = int(r * 1.4) + 1
        sl = (slice(max(0, j0 - R), j0 + R + 1), slice(max(0, i0 - R), i0 + R + 1))
        dd = np.hypot(XX[sl] - x, ZZ[sl] - z)
        can[sl] = np.maximum(can[sl], sstep(r * 1.3, r * 0.4, dd))
    forest = np.clip(can * 0.8 + sstep(0.45, 0.7, n2) * 0.4, 0, 1) * (1 - verge) * (1 - paving)
    grass = np.clip(1 - verge - forest - paving, 0, 1)
    mud = np.zeros_like(H)
    for px, pz, r, wl in ponds:
        dd = np.hypot(XX - px, ZZ - pz); mud = np.maximum(mud, sstep(r * 1.6, r * 0.9, dd))
    verge = np.clip(verge + mud * 0.7, 0, 1)
    tot = verge + grass + forest + 1e-6
    A = np.stack([verge / tot, grass / tot, forest / tot], -1)
    # sombra das copas projetada pelo sol (mesma direção da luz do jogo), mais escura no meio da copa
    sh = np.zeros_like(H)
    for x, z, r, h in shade_list:
        cx, cz = x + SUN[0] * SUN_K * h * 0.55, z + SUN[1] * SUN_K * h * 0.55   # o centro da copa fica a meia altura
        ln = SUN_K * h * 0.6
        i0, j0 = int((cx - X0) / RES), int((cz - X0) / RES); R = int(r + ln) + 2
        sl = (slice(max(0, j0 - R), j0 + R + 1), slice(max(0, i0 - R), i0 + R + 1))
        px, pz = XX[sl] - cx, ZZ[sl] - cz
        along = px * SUN[0] + pz * SUN[1]; across = -px * SUN[1] + pz * SUN[0]
        e = np.hypot(along / (r + ln * 0.5), across / r)                       # elipse alongada na direção da sombra
        sh[sl] = np.maximum(sh[sl], sstep(1.05, 0.55, e) * (0.75 + 0.25 * min(1, h / 20)))
    sh = ndimage.gaussian_filter(sh, 1.2)
    sh = np.clip(sh * (0.85 + 0.3 * n3), 0, 1)
    # oclusão: pés de barranco e fundo das poças um pouco mais escuros
    lap = ndimage.gaussian_filter(H, 2) - ndimage.gaussian_filter(H, 6)
    ao = np.clip(-lap * 0.6, 0, 0.35)
    dark = np.clip(sh * 0.95 + ao, 0, 1)
    moss = np.clip(mud * 0.6 + can * sstep(0.6, 0.8, n1) * 0.5, 0, 1)
    Bm = np.stack([paving, dark, moss], -1)
    def save(arr, name, size=2048):
        Image.fromarray((np.clip(arr, 0, 1) * 255).astype(np.uint8)).resize((size, size), Image.BILINEAR).save(os.path.join(OUT, name), optimize=True)
    save(A, 'mistura_a.png'); save(Bm, 'mistura_b.png')
    return A, Bm, paving

def cells(H, M, ponds, paving):
    out = []
    for j in range(SQ):
        for i in range(SQ):
            x, z = (i + 0.5) * G, (j + 0.5) * G
            h = float(sample(H, x, z)[0]); wl = water_level(ponds, x, z)
            if wl - h > 0.15: c = 'a'
            elif float(sample(paving, x, z)[0]) > 0.5: c = 'p'
            elif float(sample(M['rd'], x, z)[0]) < 3.0: c = 't'
            else: c = 'g'
            out.append(c)
    return ''.join(out)

SPAWN = (6.0 * G, 44.5 * G)              # chegando pela estrada do oeste

def main():
    os.makedirs(OUT, exist_ok=True)
    H, M, ponds = build()
    print('altura min %.2f max %.2f (dentro do mapa %.2f a %.2f)' % (H.min(), H.max(), float(sample(H, np.linspace(0, SIZE, 50), np.linspace(0, SIZE, 50)).min()), float(sample(H, np.linspace(0, SIZE, 50), np.linspace(0, SIZE, 50)).max())))
    inst, obst, shade_list = scatter(H, M, ponds)
    A, Bm, paving = splat(H, M, ponds, shade_list)
    cl = cells(H, M, ponds, paving)
    segs = [[0, 0, SIZE, 0, 999], [SIZE, 0, SIZE, SIZE, 999], [SIZE, SIZE, 0, SIZE, 999], [0, SIZE, 0, 0, 999]]
    hq = np.clip(np.round(H * 100), -32000, 32000).astype('<i2')
    obst_in = [o for o in obst if -2 <= o[0] <= SIZE + 2 and -2 <= o[1] <= SIZE + 2]
    dados = dict(
        versao=2, nome='Encruzilhada da Floresta', quadrados=SQ, ext=EXT, res=RES, n=NG, x0=X0,
        relevo=base64.b64encode(hq.tobytes()).decode(),
        agua=dict(pocas=ponds, cor=[0.07, 0.13, 0.2], fundo=[0.015, 0.035, 0.08]),
        texturas=dict(lama='terra.jpg', musgo='grama.jpg', caverna='folhas.jpg', piso='calcada.jpg', rocha='rocha.jpg',
                      escalas=[7.0, 5.5, 6.0, 9.5], limo=[0.2, 0.3, 0.1], sombra=0.62, molhado=False),
        kit='kit.glb', kit_extra=['props.glb'], instancias=inst,
        fundo=dict(img='fundo.webp', repetir=1, raio=300, base=-30, faixa=210, chao=[0.36, 0.42, 0.2], chao_y=-9),
        colisao=segs, obstaculos=obst_in, vegetacao=[],
        bioma='estrada', spawn=dict(x=SPAWN[0], z=SPAWN[1]))
    with open(os.path.join(OUT, 'dados.json'), 'w') as f: json.dump(dados, f, separators=(',', ':'))
    # o mesmo relevo e as instâncias, para o Blender montar a prévia
    with open(os.path.join(ROOT, 'fontes', 'mapas', 'estrada_plano.json'), 'w') as f:
        json.dump(dict(n=NG, x0=X0, res=RES, relevo=dados['relevo'], pocas=ponds, instancias=inst, j=J.tolist()), f)
    os.makedirs(os.path.join(ROOT, 'mapas', 'prontos'), exist_ok=True)
    pronto = dict(map=dict(name='Encruzilhada da Floresta', w=SQ, h=SQ, walls=[], doors=[], lights=[], hasImage=False, floorMode='tiles',
                           terrain=dict(biome='estrada', cells=cl), spawn=dict(x=SPAWN[0], z=SPAWN[1]), cenario='estrada'), ents=[])
    with open(os.path.join(ROOT, 'mapas', 'prontos', 'estrada-floresta.json'), 'w') as f: json.dump(pronto, f, ensure_ascii=False)
    print('células:', {c: cl.count(c) for c in sorted(set(cl))})
    print('instâncias:', {k: len(v) for k, v in sorted(inst.items())}, 'total', sum(len(v) for v in inst.values()))
    print('obstáculos no mapa:', len(obst_in), 'poças:', len(ponds))
    print('dados.json: %.1f KB' % (os.path.getsize(os.path.join(OUT, 'dados.json')) / 1024))
    # prévia de cima
    cA = np.array([[0.48, 0.33, 0.2], [0.42, 0.48, 0.2], [0.25, 0.3, 0.14]])
    prev = A @ cA
    prev = prev * (1 - Bm[..., 0:1]) + Bm[..., 0:1] * np.array([0.45, 0.47, 0.5])
    prev *= (1 - 0.55 * Bm[..., 1:2])
    for px, pz, r, wl in ponds:
        m = (np.hypot(XX - px, ZZ - pz) < r) & (H < wl); prev[m] = [0.08, 0.15, 0.25]
    img = Image.fromarray((np.clip(prev, 0, 1) * 255).astype(np.uint8)).resize((NG * 3, NG * 3))
    d = ImageDraw.Draw(img); T = lambda x, z: ((x - X0) * 3, (z - X0) * 3)
    d.rectangle([T(0, 0), T(SIZE, SIZE)], outline=(255, 255, 255), width=2)
    for k, l in inst.items():
        if k.startswith('pinho'):
            for x, y, z, ry, s, t in l: a, b = T(x, z); r = 3 * 3.5 * s; d.ellipse([a - r, b - r, a + r, b + r], outline=(20, 50, 30) if t > 0.6 else (10, 10, 10))
        if k in ('arvore_outono',):
            for x, y, z, ry, s, t in l: a, b = T(x, z); r = 3 * 4.5 * s; d.ellipse([a - r, b - r, a + r, b + r], fill=(200, 90, 30))
    a, b = T(*SPAWN); d.ellipse([a - 8, b - 8, a + 8, b + 8], fill=(255, 255, 0))
    img.save('/tmp/estrada_planta.png')

if __name__ == '__main__':
    main()
