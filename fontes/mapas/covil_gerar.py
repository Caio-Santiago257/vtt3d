"""Planta do mapa "Covil do Dragão Negro": relevo, água, mistura de texturas, colisão e posição de tudo.

Baseado nas referências em fontes/recebidos/covil-referencias/ (planta_de_cima.jpg e as vistas das ruínas):
  - noroeste: o covil do dragão, uma caverna aberta cercada de paredões, chão coberto de ossos,
    tesouro no fundo e um bosque de cogumelos que brilham;
  - uma crista de rocha em diagonal separa o covil do resto, com uma boca de caverna;
  - um rio fundo e sinuoso corre em diagonal, de sudoeste para nordeste, com um vau raso;
  - sudeste: as ruínas do laboratório, inundadas pela água do pântano; quanto mais se entra, mais fundo:
    sala D (entrada, rasa) -> anexo -> sala B -> corredor -> sala C -> sala A (a mais funda, com o altar);
  - sudoeste: a cabeça de uma estátua colossal tombada na lama;
  - em volta: pântano, e na borda árvores e rochas que funcionam como parede.

Medidas: 64 x 64 quadrados (96 x 96 m). 1 quadrado = 2 unidades = 1,5 m. Alturas em unidades.
Saídas:
  public/assets/maps/covil/dados.json     relevo, água, custo, colisão, vegetação (lido pelo jogo)
  public/assets/maps/covil/mistura_a.png  lama / musgo / chão do covil (RGB)
  public/assets/maps/covil/mistura_b.png  piso do laboratório / sujeira escura / limo (RGB)
  fontes/mapas/covil_plano.json           paredes e objetos para o Blender modelar
  mapas/prontos/covil-dragao-negro.json   o mapa pronto (carregado pelo servidor)
Rodar: python3 fontes/mapas/covil_gerar.py
"""
import base64, json, math, os
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy import ndimage

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
OUT = os.path.join(ROOT, 'public', 'assets', 'maps', 'covil')
SQ = 64                 # quadrados por lado
G = 2.0                 # unidades por quadrado
SIZE = SQ * G           # 128 unidades
EXT = 44                # o relevo continua além da borda (só cenário)
RES = 1.0               # espaçamento da grade de relevo
X0 = -EXT
NG = int((SIZE + 2 * EXT) / RES) + 1      # 217 pontos por lado
RIVER_LEVEL = -0.35     # nível da água do rio e das poças
LAB_LEVEL = 0.35        # nível da água dentro do laboratório
WALL_TOP = 4.6
rng = np.random.default_rng(2026)

gx = X0 + np.arange(NG) * RES
XX, ZZ = np.meshgrid(gx, gx)          # XX[j, i] = x, ZZ[j, i] = z

def S(*pts): return [(x * G, y * G) for x, y in pts]   # quadrados -> unidades

# ---------------------------------------------------------------- ruído
def vnoise(scale, seed):
    """ruído suave no tamanho do relevo (scale = tamanho das manchas, em unidades)."""
    n = int((SIZE + 2 * EXT) / scale) + 4
    lat = np.random.default_rng(seed).random((n, n))
    cx = (XX - X0) / scale; cz = (ZZ - X0) / scale
    return ndimage.map_coordinates(lat, [cz, cx], order=3, mode='reflect')

def fbm(scale, seed, oct=4):
    v = sum(vnoise(scale / 2 ** o, seed + o * 17) * 0.5 ** o for o in range(oct))
    v = (v - v.min()) / (v.max() - v.min()); return v

def sstep(a, b, x): t = np.clip((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t)

# ---------------------------------------------------------------- linhas e polígonos
def poly_dist(px, pz, pts):
    """distância de cada ponto até a linha quebrada pts, e a posição ao longo dela (em unidades)."""
    best = np.full(px.shape, np.inf); along = np.zeros(px.shape); acc = 0.0
    for (ax, az), (bx, bz) in zip(pts[:-1], pts[1:]):
        vx, vz = bx - ax, bz - az; L2 = vx * vx + vz * vz; L = math.sqrt(L2)
        t = np.clip(((px - ax) * vx + (pz - az) * vz) / L2, 0, 1)
        d = np.hypot(px - (ax + vx * t), pz - (az + vz * t))
        m = d < best; best[m] = d[m]; along[m] = acc + t[m] * L; acc += L
    return best, along

def resample(pts, step=1.5):
    out = []
    for (ax, az), (bx, bz) in zip(pts[:-1], pts[1:]):
        L = math.hypot(bx - ax, bz - az); n = max(1, int(L / step))
        for k in range(n): out.append((ax + (bx - ax) * k / n, az + (bz - az) * k / n))
    out.append(pts[-1]); return out

def smooth_line(pts, it=3):
    p = np.array(pts, float)
    for _ in range(it):  # cantos arredondados (Chaikin)
        q = [p[0]]
        for a, b in zip(p[:-1], p[1:]): q += [0.75 * a + 0.25 * b, 0.25 * a + 0.75 * b]
        q.append(p[-1]); p = np.array(q)
    return [tuple(v) for v in p]

def raster(polys, ss=4, blur=0.0):
    """máscara (0..1) dos polígonos na grade de relevo, com borda suave."""
    n = NG * ss
    img = Image.new('L', (n, n), 0); d = ImageDraw.Draw(img)
    for poly in polys:
        d.polygon([((x - X0) / RES * ss, (z - X0) / RES * ss) for x, z in poly], fill=255)
    if blur: img = img.filter(ImageFilter.GaussianBlur(blur * ss / RES))
    return np.asarray(img.resize((NG, NG), Image.BILINEAR), float) / 255

# ---------------------------------------------------------------- traçado (em quadrados, convertido para unidades)
RIDGE = smooth_line(S((-12, 50), (-4, 46), (5, 41), (11, 37), (17, 33), (22, 30), (27, 26), (31, 21), (35, 17), (40, 14), (45, 12), (50, 9), (52, 4), (53, -4), (54, -14)), 2)
RIVER = smooth_line(S((-16, 60), (-4, 58), (5, 57), (9, 52), (10, 47), (15, 43), (22, 42), (26, 38), (27, 33), (33, 30), (37, 27), (38, 22), (41, 19), (47, 17), (53, 14), (58, 11), (64, 9), (80, 6)), 3)
CAVE_MOUTH = (16 * G, 34.5 * G)     # boca da caverna na crista
FORD = (15 * G, 43 * G)             # vau raso no rio, na frente da boca
SPAWN = (12.5 * G, 58.5 * G)
STATUE = (5.5 * G, 60.2 * G)
GROVE = (37 * G, 6 * G)             # bosque de cogumelos
HOARD = (7 * G, 7 * G)              # tesouro

# salas do laboratório (interior, em quadrados): x0, z0, x1, z1, piso (unidades)
ROOMS = {
    'D':      (15, 50, 28, 61, -0.15),
    'anexo':  (28, 52, 31, 58, -0.6),
    'B':      (31, 40, 46, 61, None),     # piso inclinado de oeste (-0.9) para leste (-1.9)
    'corr':   (46, 36, 51, 61, None),     # corredor: -2.1 no sul até -2.5 no norte
    'C':      (51, 40, 61, 61, -2.6),
    'A':      (44, 27, 61, 36, -2.9),
}
ALTAR = (50, 30, 55, 33)                  # plataforma seca no meio da sala A
def room_floor(name, x, z):
    if name == 'B': return -0.9 - 1.0 * np.clip((x / G - 31) / 15, 0, 1)
    if name == 'corr': return -2.1 - 0.4 * np.clip((61 - z / G) / 25, 0, 1)
    return ROOMS[name][4]

# paredes (em quadrados), já com as passagens abertas; 'brecha' marca o trecho desabado (com entulho)
WALLS = [
    # sala A
    ((44, 27), (50, 27)), ((54, 27), (61, 27)), ((44, 27), (44, 36)), ((61, 27), (61, 36)),
    ((44, 36), (46, 36)), ((51, 36), (61, 36)),
    # corredor (entre A, B e C) e portão sul desabado
    ((46, 36), (46, 40)), ((51, 36), (51, 40)), ((46, 61), (51, 61)),
    # sala B
    ((31, 40), (46, 40)), ((46, 40), (46, 49)), ((46, 52), (46, 61)), ((31, 40), (31, 53)), ((31, 56), (31, 61)), ((31, 61), (46, 61)),
    # sala C
    ((51, 40), (61, 40)), ((51, 40), (51, 44)), ((51, 47), (51, 55)), ((51, 57), (51, 61)), ((61, 40), (61, 61)), ((51, 61), (61, 61)),
    # sala D
    ((15, 50), (19, 50)), ((24, 50), (28, 50)), ((15, 50), (15, 61)), ((28, 50), (28, 53)), ((28, 56), (28, 61)), ((15, 61), (28, 61)),
    # anexo
    ((28, 52), (31, 52)), ((28, 58), (31, 58)),
]
# passagens para fora do laboratório: a água fica presa por um aterro de entulho (pisável)
DAMS = [((50, 27), (54, 27)), ((19, 50), (24, 50))]
GATE = ((46, 61), (51, 61))                # portão sul: arco desabado, bloqueado

def lab_mask_rooms():
    return {k: raster([[(x0 * G, z0 * G), (x1 * G, z0 * G), (x1 * G, z1 * G), (x0 * G, z1 * G)]]) for k, (x0, z0, x1, z1, _) in ROOMS.items()}

# ---------------------------------------------------------------- relevo
def build():
    print('relevo...')
    n_sw = fbm(14, 1); n_mud = fbm(10, 2); n_hum = fbm(5, 3)
    H = 0.1 + 0.4 * (n_sw - 0.5) + 0.12 * (n_hum - 0.5)
    mud = sstep(0.58, 0.74, n_mud)
    H -= 0.75 * mud                                     # poças de lama (abaixo do nível viram água)

    # crista: faixa de largura irregular em volta da linha, com uma boca de caverna
    rr = resample(RIDGE, 1.0)
    wl = 3.5 + 1.6 * (np.random.default_rng(7).random(len(rr)))
    wl = ndimage.gaussian_filter1d(wl, 3); wr = ndimage.gaussian_filter1d(3.0 + 1.6 * np.random.default_rng(8).random(len(rr)), 3)
    left, right = [], []
    for k, (x, z) in enumerate(rr):
        a, b = rr[max(0, k - 1)], rr[min(len(rr) - 1, k + 1)]
        tx, tz = b[0] - a[0], b[1] - a[1]; L = math.hypot(tx, tz) or 1; nx, nz = -tz / L, tx / L   # normal para o sudeste
        left.append((x + nx * wl[k], z + nz * wl[k])); right.append((x - nx * wr[k], z - nz * wr[k]))
    # corta a boca da caverna
    gapr = 5.5
    keep = [math.hypot(x - CAVE_MOUTH[0], z - CAVE_MOUTH[1]) > gapr for x, z in rr]
    parts, cur = [], []
    for k, ok in enumerate(keep):
        if ok: cur.append(k)
        elif cur: parts.append(cur); cur = []
    if cur: parts.append(cur)
    ridge_polys = [[left[k] for k in p] + [right[k] for k in reversed(p)] for p in parts if len(p) > 2]
    B = raster(ridge_polys, blur=0.28)
    ridge_top = 6.0 + 2.2 * (fbm(9, 9) - 0.5) + 0.8 * (n_hum - 0.5)

    # covil: tudo a noroeste da crista
    # (left é a borda sudeste da crista: o covil vai dela até o canto noroeste, passando pela própria crista)
    lair_poly = [(-300, 300)] + left + [(300, -300), (-300, -300)]
    L = raster([lair_poly])
    lair_floor = 0.15 + 0.35 * (fbm(8, 10) - 0.5)          # acima do nível do rio: o covil é seco
    # afloramentos de rocha no covil
    out_h = np.zeros_like(H); outcrops = []
    for k in range(14):
        while True:
            cx, cz = rng.uniform(4, 90), rng.uniform(4, 80)
            if L[int((cz - X0) / RES), int((cx - X0) / RES)] > 0.99 and math.hypot(cx - GROVE[0], cz - GROVE[1]) > 14 and math.hypot(cx - HOARD[0], cz - HOARD[1]) > 12: break
        r = rng.uniform(2.0, 4.5); h = rng.uniform(1.5, 3.5); outcrops.append((cx, cz, r, h))
        out_h = np.maximum(out_h, h * sstep(r, r * 0.45, np.hypot(XX - cx, ZZ - cz) + 0.8 * (n_hum - 0.5)))
    # bosque de cogumelos: um pouco afundado
    grove = sstep(13, 7, np.hypot((XX - GROVE[0]) * 0.75, ZZ - GROVE[1]) + 3 * (n_hum - 0.5))
    Hl = lair_floor + out_h - 0.3 * grove
    H = H * (1 - L) + Hl * L

    # paredões fora do mapa: altos do lado do covil, morros baixos do lado do pântano
    dx = np.maximum(np.maximum(-XX, XX - SIZE), 0); dz = np.maximum(np.maximum(-ZZ, ZZ - SIZE), 0)
    outside = np.maximum(dx, dz)
    cliff_out = 10 + 3 * (fbm(7, 11) - 0.5)
    H = lerp(H, cliff_out, sstep(0.3, 3.5, outside) * L)
    H += 0.6 * sstep(2, 20, outside) * (1 - L) * fbm(12, 12)

    # rio (depois do covil, antes da crista)
    dr, along = poly_dist(XX, ZZ, RIVER)
    hw = 3.3 + 1.1 * (vnoise(16, 13) - 0.5) * 2
    t = dr / hw
    bed = -2.7 * np.clip(1 - t * t, 0, 1) ** 0.8 - 0.55
    ford = sstep(7, 3, np.hypot(XX - FORD[0], ZZ - FORD[1]))
    bed = lerp(bed, np.maximum(bed, -1.15), ford)
    bank = lerp(-0.6, H, sstep(1.0, 2.6, t))
    river_h = np.where(t < 1.0, bed, bank)
    H = np.minimum(H, river_h) * (dr < hw * 2.6) + H * (dr >= hw * 2.6)
    # crista por cima de tudo
    H = H * (1 - B) + ridge_top * B

    # laboratório
    rooms = lab_mask_rooms()
    lab_any = np.zeros_like(H)
    for name, m in rooms.items():
        x0, z0, x1, z1, _ = ROOMS[name]
        inside = (XX > x0 * G) & (XX < x1 * G) & (ZZ > z0 * G) & (ZZ < z1 * G)
        fl = room_floor(name, XX, ZZ) + 0.05 * (n_hum - 0.5)
        H = np.where(inside, fl, H); lab_any = np.maximum(lab_any, inside)
    ax0, az0, ax1, az1 = ALTAR
    altar = (XX >= ax0 * G) & (XX <= ax1 * G) & (ZZ >= az0 * G) & (ZZ <= az1 * G)
    H = np.where(altar, 0.55, H)
    # em volta do laboratório não há poça (a água de fora não entra na área das salas)
    lx0, lz0, lx1, lz1 = 14 * G, 26 * G, 62 * G, 62 * G
    near_lab = (XX > lx0) & (XX < lx1) & (ZZ > lz0) & (ZZ < lz1) & (lab_any < 0.5)
    H = np.where(near_lab, np.maximum(H, 0.05), H)
    # aterros de entulho nas brechas que dão para fora
    for (a, b) in DAMS:
        (x1_, z1_), (x2_, z2_) = (a[0] * G, a[1] * G), (b[0] * G, b[1] * G)
        d, _ = poly_dist(XX, ZZ, [(x1_, z1_), (x2_, z2_)])
        H = np.where(d < 1.6, np.maximum(H, 0.65 - d * 0.25), H)
    return H, dict(B=B, L=L, mud=mud, grove=grove, rooms=rooms, lab_any=lab_any, ridge_polys=ridge_polys, outcrops=outcrops, dr=dr, hw=hw)

def lerp(a, b, t): return a + (b - a) * t

# ---------------------------------------------------------------- água, mistura, custo
def water_level(x, z):
    for name, (x0, z0, x1, z1, _) in ROOMS.items():
        if x0 * G <= x <= x1 * G and z0 * G <= z <= z1 * G: return LAB_LEVEL
    return RIVER_LEVEL

def sample(H, x, z):
    fx, fz = (x - X0) / RES, (z - X0) / RES
    return float(ndimage.map_coordinates(H, [[fz], [fx]], order=1)[0])

def splat(H, M):
    print('mistura de texturas...')
    n = fbm(6, 21); n2 = fbm(18, 22)
    wet = sstep(0.1, -0.5, H) * (1 - M['L'])                                      # beira d'água: lama
    mud = np.clip(M['mud'] * 0.9 + wet * 0.9 + sstep(0.65, 0.8, n) * 0.4, 0, 1)
    moss = np.clip(1 - mud, 0, 1)
    cave = M['L'] * (1 - M['B'])
    labf = np.clip(M['lab_any'], 0, 1)
    # crista: musgo no alto
    moss = lerp(moss, 1.0, M['B']); mud = mud * (1 - M['B'])
    # covil: chão de ossos; perto das poças e do bosque, lama escura
    mud = lerp(mud, sstep(0.6, 0.8, n2) * 0.5 + M['grove'] * 0.6, cave); moss = moss * (1 - cave)
    for arr in (mud, moss): arr *= (1 - labf)
    cave = cave * (1 - labf) * (1 - mud * 0.6)
    tot = mud + moss + cave + 1e-6
    A = np.stack([mud / tot, moss / tot, cave / tot], -1) * (1 - labf)[..., None]
    dirt = np.clip(sstep(0.55, 0.85, n2) * 0.5 + M['grove'] * 0.5 + wet * 0.3, 0, 1)
    slime = labf * np.clip(-H / 3.0, 0, 1)                                          # mais limo onde é mais fundo
    Bm = np.stack([labf, dirt, slime], -1)
    def save(arr, name):
        img = Image.fromarray((np.clip(arr, 0, 1) * 255).astype(np.uint8)).resize((1024, 1024), Image.BILINEAR)
        img.save(os.path.join(OUT, name), optimize=True)
    save(A, 'mistura_a.png'); save(Bm, 'mistura_b.png')

def cells(H, M):
    out = []
    for j in range(SQ):
        for i in range(SQ):
            x, z = (i + 0.5) * G, (j + 0.5) * G
            h = sample(H, x, z); wl = water_level(x, z)
            if wl - h > 0.2: c = 'a'                                    # água: terreno difícil
            elif sample(M['B'], x, z) > 0.5: c = 'r'
            elif sample(M['lab_any'], x, z) > 0.5: c = 'p'
            elif sample(M['L'], x, z) > 0.5: c = 't'
            elif sample(M['mud'], x, z) > 0.5: c = 'l'                  # lama: terreno difícil
            else: c = 'g'
            out.append(c)
    return ''.join(out)

# ---------------------------------------------------------------- colisão e enfeites
def collision(M):
    # cada trecho: x1, z1, x2, z2, altura do topo (quem voa acima disso passa por cima; a borda do mapa nunca)
    segs = [[0, 0, SIZE, 0, 999], [SIZE, 0, SIZE, SIZE, 999], [SIZE, SIZE, 0, SIZE, 999], [0, SIZE, 0, 0, 999]]
    for poly in M['ridge_polys']:
        p = resample(poly + [poly[0]], 2.0)
        segs += [[a[0], a[1], b[0], b[1], 8.5] for a, b in zip(p[:-1], p[1:])]
    for (a, b) in WALLS + [GATE]:
        segs.append([a[0] * G, a[1] * G, b[0] * G, b[1] * G, WALL_TOP + 0.6])
    # só o que fica dentro (ou rente) do mapa interessa
    segs = [s for s in segs if min(s[0], s[2]) < SIZE + 1 and max(s[0], s[2]) > -1 and min(s[1], s[3]) < SIZE + 1 and max(s[1], s[3]) > -1]
    return [[round(v, 2) for v in s] for s in segs]

def scatter(H, M):
    print('vegetação e objetos...')
    veg, obstacles = [], []
    def okfree(x, z, clear):
        if math.hypot(x - SPAWN[0], z - SPAWN[1]) < 6: return False
        for (a, b) in WALLS + DAMS + [GATE]:
            d, _ = poly_dist(np.array([x]), np.array([z]), [(a[0] * G, a[1] * G), (b[0] * G, b[1] * G)])
            if d[0] < clear: return False
        return True
    def put(m, x, z, s, solid=0.0):
        veg.append([m, round(x, 2), round(z, 2), round(s, 2), round(rng.uniform(0, 6.28), 2), round(sample(H, x, z), 2)])
        if solid and -2 < x < SIZE + 2 and -2 < z < SIZE + 2: obstacles.append([round(x, 2), round(z, 2), round(solid * s, 2)])
    def kind(x, z):
        h = sample(H, x, z); wl = water_level(x, z)
        return dict(h=h, water=wl - h > 0.15, lab=sample(M['lab_any'], x, z) > 0.3, ridge=sample(M['B'], x, z) > 0.5,
                    lair=sample(M['L'], x, z) > 0.5, mud=sample(M['mud'], x, z) > 0.5, inside=0 <= x <= SIZE and 0 <= z <= SIZE)
    # borda: árvores grandes e pedras lado a lado (a "parede" do mapa), fora do covil
    for side in range(4):
        t = 0.0
        while t < SIZE + 8:
            off = rng.uniform(0.5, 3.0)
            if side == 0: x, z = t - 4, -off
            elif side == 1: x, z = SIZE + off, t - 4
            elif side == 2: x, z = t - 4, SIZE + off
            else: x, z = -off, t - 4
            k = kind(x, z)
            if not k['lair'] and not k['ridge']:
                if rng.random() < 0.72: put('swamp' if rng.random() < 0.45 else 'dead', x, z, rng.uniform(2.0, 3.2), 0.35)
                else: put('rock', x, z, rng.uniform(2.2, 3.4), 0.5)
                if rng.random() < 0.6: put('bush', x + rng.uniform(-1.5, 1.5), z + rng.uniform(-1.5, 1.5), rng.uniform(1.4, 2.2))
            t += rng.uniform(2.2, 3.6)
    # mata além da borda (cenário)
    for _ in range(900):
        x, z = rng.uniform(-EXT + 4, SIZE + EXT - 4), rng.uniform(-EXT + 4, SIZE + EXT - 4)
        k = kind(x, z)
        if k['inside'] or k['lair'] or k['ridge'] or min(abs(x - SIZE / 2), abs(z - SIZE / 2)) < 0 or k['h'] > 3: continue
        if -3 < x < SIZE + 3 and -3 < z < SIZE + 3: continue
        put('swamp' if rng.random() < 0.45 else 'dead', x, z, rng.uniform(1.8, 3.4))
    # pântano dentro do mapa
    for _ in range(5200):
        x, z = rng.uniform(1, SIZE - 1), rng.uniform(1, SIZE - 1); k = kind(x, z)
        if k['lab'] or k['ridge'] or k['lair']: continue
        if k['water']:
            if rng.random() < 0.08 and water_level(x, z) - k['h'] < 1.6: put('lily', x, z, rng.uniform(0.8, 1.5))
            continue
        near_water = water_level(x, z) - sample(H, x + 1.5, z) > 0.1 or water_level(x, z) - sample(H, x - 1.5, z) > 0.1 or water_level(x, z) - sample(H, x, z + 1.5) > 0.1 or water_level(x, z) - sample(H, x, z - 1.5) > 0.1
        p = rng.random()
        if near_water and p < 0.5: put('reed', x, z, rng.uniform(0.9, 1.5)); continue
        if p < 0.28: put('tuft' if rng.random() < 0.5 else 'tuft2', x, z, rng.uniform(0.9, 1.6))
        elif p < 0.31 and okfree(x, z, 2.5): put('swamp', x, z, rng.uniform(1.2, 2.0), 0.3)
        elif p < 0.34 and okfree(x, z, 2.5): put('dead', x, z, rng.uniform(1.1, 1.8), 0.3)
        elif p < 0.37 and okfree(x, z, 1.5): put('bush', x, z, rng.uniform(1.0, 1.6))
        elif p < 0.39 and k['mud']: put('mushroom', x, z, rng.uniform(0.8, 1.3))
        elif p < 0.41 and okfree(x, z, 1.5): put('rock', x, z, rng.uniform(0.7, 1.4), 0.4)
    # crista: tufos, arbustos e árvores mortas recortadas no alto
    for _ in range(1400):
        x, z = rng.uniform(-10, SIZE), rng.uniform(-10, SIZE); k = kind(x, z)
        if not k['ridge'] or sample(M['B'], x, z) < 0.95: continue
        p = rng.random()
        if p < 0.5: put('tuft' if rng.random() < 0.5 else 'tuft2', x, z, rng.uniform(1.0, 1.8))
        elif p < 0.62: put('bush', x, z, rng.uniform(1.0, 1.8))
        elif p < 0.68: put('dead', x, z, rng.uniform(1.0, 1.7))
        elif p < 0.72: put('rock', x, z, rng.uniform(1.0, 2.0))
    # covil: estalagmites e pedras
    for _ in range(900):
        x, z = rng.uniform(1, 100), rng.uniform(1, 92); k = kind(x, z)
        if not k['lair'] or k['ridge'] or not k['inside']: continue
        if math.hypot(x - HOARD[0], z - HOARD[1]) < 9: continue
        p = rng.random()
        if p < 0.05: put('stalagmite', x, z, rng.uniform(1.0, 2.6), 0.3)
        elif p < 0.09: put('rock', x, z, rng.uniform(0.8, 2.0), 0.4)
        elif p < 0.11: put('tuft_dry', x, z, rng.uniform(0.8, 1.3))
    # paredões do covil fora do mapa: estalagmites grandes para quebrar o contorno
    for _ in range(260):
        x, z = rng.uniform(-EXT, 110), rng.uniform(-EXT, 100); k = kind(x, z)
        if not k['lair'] or k['inside']: continue
        put('stalagmite', x, z, rng.uniform(2.0, 4.5))
    return veg, obstacles

# ---------------------------------------------------------------- objetos para o Blender
def props(H, M):
    print('objetos das ruínas e do covil...')
    P = dict(walls=[], panels=[], rubble=[], pillars=[], vats=[], tables=[], shelves=[], cages=[], pipes=[], jars=[],
             altar=None, gate=None, statue=None, skeletons=[], beasts=[], bones=[], hoard=None, mushrooms=[], spires=[], boulders=[], obstacles=[], lights=[])
    def h(x, z): return round(sample(H, x, z), 3)
    def floor_below(x, z):
        return min(h(x + dx, z + dz) for dx, dz in ((0.8, 0), (-0.8, 0), (0, 0.8), (0, -0.8)))
    # paredes: base no piso mais baixo dos dois lados, alto arruinado
    for (a, b) in WALLS:
        x1, z1, x2, z2 = a[0] * G, a[1] * G, b[0] * G, b[1] * G
        mx, mz = (x1 + x2) / 2, (z1 + z2) / 2
        P['walls'].append(dict(a=[x1, z1], b=[x2, z2], base=round(min(floor_below(x1 * 0.9 + mx * 0.1, z1 * 0.9 + mz * 0.1), floor_below(mx, mz), floor_below(x2 * 0.9 + mx * 0.1, z2 * 0.9 + mz * 0.1)) - 0.4, 2), top=WALL_TOP, seed=int(rng.integers(1e6))))
    # entulho: nas brechas (aterros), no portão e espalhado nas salas
    for (a, b) in DAMS:
        x1, z1, x2, z2 = a[0] * G, a[1] * G, b[0] * G, b[1] * G
        for k in range(26):
            t = rng.random(); x, z = x1 + (x2 - x1) * t + rng.uniform(-1.8, 1.8), z1 + (z2 - z1) * t + rng.uniform(-1.8, 1.8)
            P['rubble'].append([round(x, 2), round(z, 2), h(x, z), round(rng.uniform(0.4, 1.2), 2), round(rng.uniform(0, 6.28), 2), int(rng.integers(4))])
    gx1, gz1, gx2, gz2 = GATE[0][0] * G, GATE[0][1] * G, GATE[1][0] * G, GATE[1][1] * G
    P['gate'] = dict(a=[gx1, gz1], b=[gx2, gz2], base=-2.4)
    for k in range(22):
        x, z = rng.uniform(gx1 + 0.5, gx2 - 0.5), gz1 + rng.uniform(-2.2, 0.8)
        P['rubble'].append([round(x, 2), round(z, 2), h(x, z), round(rng.uniform(0.5, 1.4), 2), round(rng.uniform(0, 6.28), 2), int(rng.integers(4))])
    for name, (x0, z0, x1, z1, _) in ROOMS.items():
        area = (x1 - x0) * (z1 - z0)
        for k in range(int(area * 0.09)):
            x, z = rng.uniform(x0 * G + 1, x1 * G - 1), rng.uniform(z0 * G + 1, z1 * G - 1)
            P['rubble'].append([round(x, 2), round(z, 2), h(x, z), round(rng.uniform(0.25, 1.0), 2), round(rng.uniform(0, 6.28), 2), int(rng.integers(4))])
        # colunas (algumas caídas)
        for k in range(max(1, int(area / 70))):
            x, z = rng.uniform(x0 * G + 2, x1 * G - 2), rng.uniform(z0 * G + 2, z1 * G - 2)
            fallen = rng.random() < 0.55
            P['pillars'].append(dict(x=round(x, 2), z=round(z, 2), y=h(x, z), fallen=bool(fallen), ry=round(rng.uniform(0, 6.28), 2), h=round(rng.uniform(2.5, 4.5), 2)))
            if not fallen: P['obstacles'].append([round(x, 2), round(z, 2), 0.7])
    # equipamento do laboratório
    def along_wall(room, n, inset=1.3):
        x0, z0, x1, z1, _ = ROOMS[room]; out = []
        for k in range(n):
            side = rng.integers(4); t = rng.uniform(0.12, 0.88)
            if side == 0: x, z, ry = (x0 + (x1 - x0) * t) * G, z0 * G + inset, 0
            elif side == 1: x, z, ry = (x0 + (x1 - x0) * t) * G, z1 * G - inset, math.pi
            elif side == 2: x, z, ry = x0 * G + inset, (z0 + (z1 - z0) * t) * G, math.pi / 2
            else: x, z, ry = x1 * G - inset, (z0 + (z1 - z0) * t) * G, -math.pi / 2
            out.append((x, z, ry))
        return out
    for room, n in (('A', 6), ('C', 7), ('B', 3), ('corr', 2)):
        for x, z, ry in along_wall(room, n, 1.6):
            st = rng.choice(['inteiro', 'quebrado', 'quebrado', 'tombado'])
            P['vats'].append(dict(x=round(x, 2), z=round(z, 2), y=h(x, z), ry=round(ry, 2), state=str(st), glow=bool(rng.random() < 0.6)))
            if st != 'tombado': P['obstacles'].append([round(x, 2), round(z, 2), 1.0])
    for room, n in (('B', 7), ('D', 4), ('C', 2), ('A', 2), ('corr', 2)):
        x0, z0, x1, z1, _ = ROOMS[room]
        for k in range(n):
            x, z = rng.uniform(x0 * G + 2.5, x1 * G - 2.5), rng.uniform(z0 * G + 2.5, z1 * G - 2.5)
            P['tables'].append(dict(x=round(x, 2), z=round(z, 2), y=h(x, z), ry=round(rng.uniform(0, 6.28), 2), tipped=bool(rng.random() < 0.4)))
    for room, n in (('anexo', 4), ('B', 5), ('D', 3), ('C', 2)):
        for x, z, ry in along_wall(room, n, 0.8):
            P['shelves'].append(dict(x=round(x, 2), z=round(z, 2), y=h(x, z), ry=round(ry, 2), fallen=bool(rng.random() < 0.35)))
    for room, n in (('B', 2), ('C', 2), ('A', 1)):
        for x, z, ry in along_wall(room, n, 2.0):
            P['cages'].append(dict(x=round(x, 2), z=round(z, 2), y=h(x, z), ry=round(rng.uniform(0, 6.28), 2), broken=bool(rng.random() < 0.6)))
            P['obstacles'].append([round(x, 2), round(z, 2), 1.1])
    for w in P['walls']:  # canos ao longo de algumas paredes, a meia altura
        if rng.random() < 0.35: P['pipes'].append(dict(a=w['a'], b=w['b'], y=1.6 + rng.uniform(-0.3, 0.6), off=0.75, seed=int(rng.integers(1e6))))
    for _ in range(140):
        room = rng.choice(list(ROOMS)); x0, z0, x1, z1, _ = ROOMS[room]
        x, z = rng.uniform(x0 * G + 1, x1 * G - 1), rng.uniform(z0 * G + 1, z1 * G - 1)
        P['jars'].append([round(x, 2), round(z, 2), h(x, z), round(rng.uniform(0.7, 1.3), 2), round(rng.uniform(0, 6.28), 2), int(rng.integers(3))])
    ax0, az0, ax1, az1 = ALTAR
    P['altar'] = dict(x0=ax0 * G, z0=az0 * G, x1=ax1 * G, z1=az1 * G, base=-3.0, top=0.55)
    P['lights'].append(dict(x=(ax0 + ax1) / 2, y=(az0 + az1) / 2, color='#b46cff', range=7, intensity=1.6))
    for v in P['vats']:
        if v['glow'] and v['state'] != 'tombado' and rng.random() < 0.5:
            P['lights'].append(dict(x=round(v['x'] / G, 2), y=round(v['z'] / G, 2), color='#7dff6a', range=4, intensity=1.0))
    # painéis de crânios: nas faces das paredes, a cada ~3,2 unidades (pulando as pontas)
    for w in P['walls']:
        (x1, z1), (x2, z2) = w['a'], w['b']; L = math.hypot(x2 - x1, z2 - z1)
        n = int((L - 1.6) / 3.2)
        for k in range(n):
            t = (1.6 + 3.2 * (k + 0.5)) / L
            if rng.random() < 0.8: P['panels'].append([round(x1 + (x2 - x1) * t, 2), round(z1 + (z2 - z1) * t, 2), round(math.atan2(z2 - z1, x2 - x1), 3)])
    # estátua tombada
    P['statue'] = dict(x=STATUE[0], z=STATUE[1], y=h(*STATUE), ry=0.7, s=1.0)
    P['obstacles'].append([STATUE[0], STATUE[1], 5.0])
    # covil: esqueletos humanos e de criaturas, ossos soltos, tesouro, cogumelos, rochas
    def lair_spot(minr_from=None, tries=200):
        for _ in range(tries):
            x, z = rng.uniform(3, 100), rng.uniform(3, 92)
            if sample(M['L'], x, z) > 0.99 and sample(M['B'], x, z) < 0.01 and 0 < x < SIZE and 0 < z < SIZE:
                if minr_from and any(math.hypot(x - a, z - b) < r for a, b, r in minr_from): continue
                return x, z
        return None
    avoid = [(HOARD[0], HOARD[1], 8)]
    for k in range(26):
        p = lair_spot(avoid)
        if p: P['skeletons'].append(dict(x=round(p[0], 2), z=round(p[1], 2), y=h(*p), ry=round(rng.uniform(0, 6.28), 2), pose=int(rng.integers(3))))
    for k in range(7):
        p = lair_spot(avoid + [(b['x'], b['z'], 10) for b in P['beasts']])
        if p:
            s = rng.uniform(0.8, 1.6)
            P['beasts'].append(dict(x=round(p[0], 2), z=round(p[1], 2), y=h(*p), ry=round(rng.uniform(0, 6.28), 2), s=round(s, 2), kind=str(rng.choice(['quadrupede', 'serpente', 'chifrudo']))))
            P['obstacles'].append([round(p[0], 2), round(p[1], 2), round(2.0 * s, 2)])
    for k in range(1100):
        p = lair_spot(tries=30)
        if p: P['bones'].append([round(p[0], 2), round(p[1], 2), h(*p), round(rng.uniform(0.6, 1.4), 2), round(rng.uniform(0, 6.28), 2), int(rng.integers(5))])
    P['hoard'] = dict(x=HOARD[0], z=HOARD[1], y=h(*HOARD), r=7.5)
    P['lights'].append(dict(x=HOARD[0] / G, y=HOARD[1] / G, color='#ffcf6a', range=8, intensity=1.4))
    for k in range(240):
        a = rng.uniform(0, 6.28); r = 11 * math.sqrt(rng.random())
        x, z = GROVE[0] + math.cos(a) * r * 1.3, GROVE[1] + math.sin(a) * r
        if not (0 < x < SIZE and 0 < z < SIZE) or sample(M['B'], x, z) > 0.2: continue
        big = rng.random() < 0.08
        P['mushrooms'].append([round(x, 2), round(z, 2), h(x, z), round(rng.uniform(1.6, 3.2) if big else rng.uniform(0.35, 1.1), 2), int(rng.integers(4)), round(rng.uniform(0, 6.28), 2)])
    P['mushrooms'].append([GROVE[0], GROVE[1], h(*GROVE), 5.5, 1, 0.0])     # o cogumelo gigante
    P['obstacles'].append([GROVE[0], GROVE[1], 1.2])
    for c, cols in ((GROVE, '#5ef2ff'), ((GROVE[0] - 9, GROVE[1] + 4), '#ff5ad8'), ((GROVE[0] + 9, GROVE[1] + 2), '#7dff9a')):
        P['lights'].append(dict(x=round(c[0] / G, 2), y=round(c[1] / G, 2), color=cols, range=8, intensity=1.5))
    # cogumelos menores perto das paredes escuras do laboratório e da boca da caverna
    for k in range(40):
        x, z = CAVE_MOUTH[0] + rng.uniform(-6, 6), CAVE_MOUTH[1] + rng.uniform(-8, 2)
        if sample(M['B'], x, z) < 0.3 and 0 < x < SIZE: P['mushrooms'].append([round(x, 2), round(z, 2), h(x, z), round(rng.uniform(0.3, 0.8), 2), int(rng.integers(4)), round(rng.uniform(0, 6.28), 2)])
    P['lights'].append(dict(x=CAVE_MOUTH[0] / G, y=(CAVE_MOUTH[1] - 3) / G, color='#5ef2ff', range=6, intensity=1.1))
    # agulhas de pedra e matacões nos afloramentos e na crista
    for (cx, cz, r, hh) in M['outcrops']:
        for k in range(3):
            x, z = cx + rng.uniform(-r, r) * 0.6, cz + rng.uniform(-r, r) * 0.6
            P['spires'].append([round(x, 2), round(z, 2), h(x, z), round(rng.uniform(2.5, 6.0), 2), round(rng.uniform(0.8, 1.6), 2), round(rng.uniform(0, 6.28), 2)])
        P['obstacles'].append([round(cx, 2), round(cz, 2), round(r * 0.8, 2)])
    # paredão da crista: matacões e lajes de rocha encostados nas duas faces, do pé até o alto
    for poly in M['ridge_polys']:
        edge = resample(poly + [poly[0]], 2.4)
        for (x, z) in edge:
            if not (-16 < x < SIZE + 4 and -16 < z < SIZE + 4): continue
            for k in range(2):
                ox, oz = rng.uniform(-1.2, 1.2), rng.uniform(-1.2, 1.2)
                P['boulders'].append([round(x + ox, 2), round(z + oz, 2), round(min(h(x + ox, z + oz), 3.0), 2), round(rng.uniform(1.4, 2.8), 2), round(rng.uniform(0, 6.28), 2)])
    for _ in range(120):
        x, z = rng.uniform(-14, SIZE), rng.uniform(-14, SIZE)
        if sample(M['B'], x, z) > 0.9:
            P['boulders'].append([round(x, 2), round(z, 2), h(x, z), round(rng.uniform(1.2, 3.0), 2), round(rng.uniform(0, 6.28), 2)])
    # tochas da entrada (acampamento dos aventureiros perto da estátua)
    P['lights'].append(dict(x=SPAWN[0] / G + 1.5, y=SPAWN[1] / G - 1, color='#ffb36a', range=6, intensity=1.3))
    return P

def main():
    os.makedirs(OUT, exist_ok=True)
    H, M = build()
    print('altura min %.2f max %.2f' % (H.min(), H.max()))
    splat(H, M)
    cl = cells(H, M)
    segs = collision(M)
    veg, obst = scatter(H, M)
    P = props(H, M)
    # relevo compacto: inteiros em centésimos de unidade (int16), base64
    hq = np.clip(np.round(H * 100), -32000, 32000).astype('<i2')
    rooms_u = [[x0 * G, z0 * G, x1 * G, z1 * G] for (x0, z0, x1, z1, _) in ROOMS.values()]
    dados = dict(
        versao=1, nome='Covil do Dragão Negro', quadrados=SQ, ext=EXT, res=RES, n=NG, x0=X0,
        relevo=base64.b64encode(hq.tobytes()).decode(),
        agua=dict(rio=RIVER_LEVEL, lab=LAB_LEVEL, salas=rooms_u, lab_area=[14 * G, 26 * G, 62 * G, 62 * G]),
        colisao=segs, obstaculos=obst + P['obstacles'], vegetacao=veg,
        bioma='covil', spawn=dict(x=SPAWN[0], z=SPAWN[1]))
    with open(os.path.join(OUT, 'dados.json'), 'w') as f: json.dump(dados, f, separators=(',', ':'))
    with open(os.path.join(ROOT, 'fontes', 'mapas', 'covil_plano.json'), 'w') as f:
        json.dump(dict(P, relevo=dict(n=NG, x0=X0, res=RES, b64=dados['relevo']), agua=dados['agua']), f)
    # o mapa pronto (o que o servidor carrega)
    os.makedirs(os.path.join(ROOT, 'mapas', 'prontos'), exist_ok=True)
    pronto = dict(
        map=dict(name='Covil do Dragão Negro', w=SQ, h=SQ, walls=[], doors=[], lights=P['lights'], hasImage=False, floorMode='tiles',
                 terrain=dict(biome='covil', cells=cl), spawn=dict(x=SPAWN[0], z=SPAWN[1]), cenario='covil'),
        ents=[dict(kind='monster', model='Dragao_Negro', x=12 * G, z=13 * G, ry=2.4, scale=1),
              dict(kind='monster', model='Skeleton_Warrior', x=38 * G, z=50 * G, ry=0.5, scale=1),
              dict(kind='monster', model='Skeleton_Minion', x=48.5 * G, z=45 * G, ry=3.1, scale=1),
              dict(kind='monster', model='Skeleton_Mage', x=52.5 * G, z=31.5 * G, ry=1.2, scale=1),
              dict(kind='monster', model='Skeleton_Rogue', x=21 * G, z=56 * G, ry=-0.6, scale=1)])
    with open(os.path.join(ROOT, 'mapas', 'prontos', 'covil-dragao-negro.json'), 'w') as f: json.dump(pronto, f, ensure_ascii=False)
    print('células:', {c: cl.count(c) for c in set(cl)})
    print('colisão: %d trechos, %d obstáculos, %d plantas/pedras' % (len(segs), len(dados['obstaculos']), len(veg)))
    print('objetos:', {k: (len(v) if isinstance(v, list) else 1) for k, v in P.items()})
    # prévia de cima, para conferir a planta
    prev = np.zeros((NG, NG, 3))
    A = np.asarray(Image.open(os.path.join(OUT, 'mistura_a.png')).resize((NG, NG)), float) / 255
    Bm = np.asarray(Image.open(os.path.join(OUT, 'mistura_b.png')).resize((NG, NG)), float) / 255
    prev += A[..., 0:1] * np.array([0.33, 0.28, 0.17]) + A[..., 1:2] * np.array([0.30, 0.42, 0.18]) + A[..., 2:3] * np.array([0.38, 0.35, 0.32]) + Bm[..., 0:1] * np.array([0.55, 0.52, 0.45])
    shade = 0.65 + 0.35 * np.clip(0.5 + (np.roll(H, 1, 1) - H) * 0.5, 0, 1)
    prev *= shade[..., None]
    wl = np.full(H.shape, RIVER_LEVEL)
    for x0, z0, x1, z1 in rooms_u: wl[(XX >= x0) & (XX <= x1) & (ZZ >= z0) & (ZZ <= z1)] = LAB_LEVEL
    depth = np.clip((wl - H) / 3.0, 0, 1)
    wat = wl > H
    prev[wat] = prev[wat] * (1 - 0.6 - 0.3 * depth[wat, None]) + np.array([0.15, 0.32, 0.18]) * (0.6 + 0.3 * depth[wat, None])
    img = Image.fromarray((np.clip(prev, 0, 1) * 255).astype(np.uint8)).resize((NG * 4, NG * 4), Image.NEAREST)
    d = ImageDraw.Draw(img)
    T = lambda x, z: ((x - X0) / RES * 4, (z - X0) / RES * 4)
    d.rectangle([T(0, 0), T(SIZE, SIZE)], outline=(255, 255, 255))
    for s in segs: d.line([T(s[0], s[1]), T(s[2], s[3])], fill=(255, 80, 80), width=2)
    for v in veg:
        if v[0] in ('swamp', 'dead'): x, z = T(v[1], v[2]); d.ellipse([x - 3, z - 3, x + 3, z + 3], fill=(20, 60, 20))
    for o in P['mushrooms']: x, z = T(o[0], o[1]); d.ellipse([x - 2, z - 2, x + 2, z + 2], fill=(90, 240, 255))
    x, z = T(*SPAWN); d.ellipse([x - 6, z - 6, x + 6, z + 6], fill=(255, 255, 0))
    img.save('/tmp/covil_planta.png')

if __name__ == '__main__':
    main()
