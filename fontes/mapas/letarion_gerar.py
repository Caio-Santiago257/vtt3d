"""Planta do mapa "Observatório de Letarion": uma montanha alta no mar, perto das Ilhas Moonshae,
com o observatório no topo.

- Montanha em cone saindo do mar, platô no topo a 40 unidades (30 m) acima da água.
- Escadaria escavada na encosta, em espiral (quase uma volta inteira), do píer até o pátio de entrada.
- Queda d'água: nasce numa fonte no platô, cai pela encosta numa bacia ao lado da escadaria, passa sob uma ponte
  e desce de novo até o mar (só visual; o mar é a água do jogo).
- No platô: pátio de entrada, recepção, biblioteca (com a torre), cúpula do observatório (plataforma com rampa e o
  grande telescópio), laboratório de alquimia e uma varanda sobre o penhasco.

Saída:
  public/assets/maps/letarion/dados.json          relevo, mar, colisão, obstáculos, fundo e céu (lido pelo jogo)
  public/assets/maps/letarion/mistura_a.png / _b  mistura das texturas do chão
  fontes/mapas/letarion_plano.json                o mesmo relevo + caminho + cômodos + móveis, para o Blender
  mapas/prontos/letarion.json                     mapa pronto, com as fontes de luz já posicionadas
Rodar: python3 fontes/mapas/letarion_gerar.py
"""
import base64, json, math, os
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
OUT = os.path.join(ROOT, 'public', 'assets', 'maps', 'letarion')
os.makedirs(OUT, exist_ok=True)
G = 2; SQ = 48; SIZE = SQ * G          # 48 × 48 quadrados = 96 unidades
EXT = 72; RES = 1.0; X0 = -EXT
NG = int((SIZE + 2 * EXT) / RES) + 1
XX, ZZ = np.meshgrid(X0 + np.arange(NG) * RES, X0 + np.arange(NG) * RES)
C = np.array([48.0, 48.0])                # centro da montanha
PH = 40.0                                 # altura do platô (30 m acima do mar)
RP = 23.5                                 # raio do platô
SLOPE = 2.0                               # queda da encosta por unidade de raio (penhasco íngreme)
rng = np.random.default_rng(7)

def vnoise(scale, seed):
    r = np.random.default_rng(seed); k = int(math.ceil((SIZE + 2 * EXT) / scale)) + 3
    g = r.random((k, k)); fx = (XX - X0) / scale; fz = (ZZ - X0) / scale
    return ndimage.map_coordinates(g, [fz.ravel(), fx.ravel()], order=3, mode='wrap').reshape(XX.shape)
def fbm(scale, seed, oct=4):
    s = 0; a = 1; t = 0
    for o in range(oct): s += vnoise(scale / 2 ** o, seed + o) * a; t += a; a *= 0.5
    return s / t
def sstep(a, b, x): t = np.clip((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t)
def sample(A, x, z):
    return ndimage.map_coordinates(A, [(np.atleast_1d(z) - X0) / RES, (np.atleast_1d(x) - X0) / RES], order=1)

# ---------------------------------------------------------------- caminho da escadaria
def r_cone(h): return RP + (PH - h) / SLOPE           # raio onde a encosta tem a altura h
T0, SWEEP = math.radians(65), math.radians(330)       # começa no sudeste, sobe pelo leste, norte, oeste e chega ao sul
def path_points(n=700):
    pts = []
    for k in range(n + 1):
        t = k / n; th = T0 - SWEEP * t; h = 0.45 + (PH - 0.45) * t
        r = r_cone(h) - 0.8                            # escavada na encosta: por dentro fica o barranco
        pts.append((C[0] + r * math.cos(th), C[1] + r * math.sin(th), h))
    # último trecho: reto, para dentro do platô (chega ao arco de entrada do pátio)
    ex, ez, eh = pts[-1]
    for k in range(1, 6): f = k / 5; pts.append((ex + (46.0 - ex) * f, ez + (66.8 - ez) * f, PH))
    return np.array(pts)
PATH = path_points()
PW = 1.7                                               # meia largura da escadaria

# ---------------------------------------------------------------- cômodos (unidades; piso = PH)
DOME = dict(c=(48.0, 37.5), r=8.6)
ROOMS = {
    'recepcao': (40.0, 46.6, 56.0, 56.0),
    'biblioteca': (29.0, 42.0, 40.0, 55.0),
    'laboratorio': (56.0, 44.0, 66.0, 54.0),
    'varanda': (66.0, 45.0, 72.5, 53.0),
    'patio': (36.0, 56.0, 60.0, 66.0),
}
# portas: (x1, z1, x2, z2) do vão
DOORS = [(46.4, 56.0, 49.6, 56.0), (46.4, 46.6, 49.6, 46.6), (40.0, 49.3, 40.0, 52.3), (56.0, 48.0, 56.0, 51.0), (66.0, 47.5, 66.0, 50.5)]
PLATAFORMA = dict(c=(48.0, 35.8), r=2.7, h=2.6)        # plataforma do telescópio
RAMPA = (46.9, 38.4, 49.1, 43.4)                       # rampa de degraus até a plataforma (sobe para o norte)
FONTE = (62.0, 61.0)                                   # fonte que alimenta a queda d'água
TH_CASCATA = math.radians(28)

def bacia():
    """onde a queda d'água cai: logo por dentro do ponto da escadaria que cruza a direção da cascata (o Blender usa a mesma conta)"""
    ux, uz = math.cos(TH_CASCATA), math.sin(TH_CASCATA)
    k = int(np.argmin((PATH[:, 0] - (C[0] + 40 * ux)) ** 2 + (PATH[:, 1] - (C[1] + 40 * uz)) ** 2))
    best = PATH[k]; rb = math.hypot(best[0] - C[0], best[1] - C[1]) - PW - 1.4
    return C[0] + rb * ux, C[1] + rb * uz, float(best[2])

def build():
    print('relevo...')
    dc = np.hypot(XX - C[0], ZZ - C[1]); th = np.arctan2(ZZ - C[1], XX - C[0])
    n1 = fbm(14, 11); n2 = fbm(5, 12); n3 = fbm(40, 13, 3)
    # encosta: cone rochoso com saliências; mais áspera embaixo
    rough = (n1 - 0.5) * 5.0 + (n2 - 0.5) * 2.2
    H = PH - np.maximum(0, dc - RP) * SLOPE + np.where(dc > RP + 1, rough * sstep(RP, RP + 8, dc), 0)
    H = np.minimum(H, PH)
    # fundo do mar e ilhotas de pedra em volta
    H = np.maximum(H, -7 + (n3 - 0.5) * 4)
    rocks = sstep(0.72, 0.82, fbm(9, 21, 3)) * sstep(60, 52, dc) * sstep(44, 50, dc)
    H = np.maximum(H, -7 + rocks * 8.5)
    # platô: chão plano; a varanda avança sobre o penhasco
    x0, z0, x1, z1 = ROOMS['varanda']
    plat = (dc <= RP) | ((XX >= x0 - 0.5) & (XX <= x1 + 0.3) & (ZZ >= z0 - 0.5) & (ZZ <= z1 + 0.5))
    H[plat] = PH
    # escadaria: faixa plana na altura do caminho; por dentro fica o barranco da encosta
    from scipy.spatial import cKDTree
    tree = cKDTree(PATH[:, :2]); d, idx = tree.query(np.stack([XX.ravel(), ZZ.ravel()], -1))
    d = d.reshape(XX.shape); hp = PATH[idx.reshape(XX.shape), 2]
    on = d < PW
    H = np.where(on, hp, H)
    lip = (d >= PW) & (d < PW + 2.2)
    H = np.where(lip & (H < hp), np.minimum(H, hp - (d - PW) * 1.1), H)
    # bacia da cascata: um nicho na encosta ao lado da escadaria, onde a queda d'água cai
    bx, bz, hb = bacia()
    db = np.hypot(XX - bx, ZZ - bz)
    H = np.where(db < 2.6, np.minimum(H, hb), H)
    H = np.where((db >= 2.6) & (db < 4.2), np.minimum(H, hb + (db - 2.6) * 6.0), H)
    # píer: um quebra-mar de pedra sob o deque de madeira
    sx, sz, _ = PATH[0]
    pier = (np.abs(XX - sx) < 1.6) & (ZZ > sz - 1) & (ZZ < sz + 9)
    H[pier] = 0.55
    # plataforma do telescópio e a rampa
    pc = PLATAFORMA['c']; plt = np.hypot(XX - pc[0], ZZ - pc[1]) < PLATAFORMA['r']
    H[plt] = PH + PLATAFORMA['h']
    a, b, c2, dd = RAMPA
    rm = (XX >= a) & (XX <= c2) & (ZZ >= b) & (ZZ <= dd)
    H[rm] = PH + PLATAFORMA['h'] * (dd - ZZ[rm]) / (dd - b)
    M = dict(dc=dc, d=d, hp=hp, plat=plat, on=on, pier=pier)
    return H, M

# ---------------------------------------------------------------- colisão
def ring(cx, cz, r, n, a0=0.0, a1=2 * math.pi, gaps=()):
    segs = []
    for k in range(n):
        u0 = a0 + (a1 - a0) * k / n; u1 = a0 + (a1 - a0) * (k + 1) / n; um = (u0 + u1) / 2
        if any(g0 <= um <= g1 for g0, g1 in gaps): continue
        segs.append([cx + r * math.cos(u0), cz + r * math.sin(u0), cx + r * math.cos(u1), cz + r * math.sin(u1)])
    return segs
def wall_rect(x0, z0, x1, z1, doors):
    """paredes de um retângulo com vãos de porta"""
    out = []
    for (a, b, c, d) in [(x0, z0, x1, z0), (x1, z0, x1, z1), (x1, z1, x0, z1), (x0, z1, x0, z0)]:
        cuts = []
        for (p, q, r2, s) in doors:
            if abs(b - d) < 1e-6 and abs(q - b) < 0.05 and abs(s - b) < 0.05: cuts.append((min(p, r2), max(p, r2)))
            if abs(a - c) < 1e-6 and abs(p - a) < 0.05 and abs(r2 - a) < 0.05: cuts.append((min(q, s), max(q, s)))
        horiz = abs(b - d) < 1e-6
        lo, hi = (min(a, c), max(a, c)) if horiz else (min(b, d), max(b, d))
        pts = [lo]
        for g0, g1 in sorted(cuts):
            if g0 > lo and g1 < hi: pts += [g0, g1]
        pts.append(hi)
        for i in range(0, len(pts), 2):
            u, v = pts[i], pts[i + 1]
            out.append([u, b, v, d] if horiz else [a, u, c, v])
    return out
def collision():
    segs = []
    # escadaria: guarda-corpo por fora e barranco por dentro (ao longo do caminho)
    P = PATH
    for side in (-1, 1):
        prev = None
        for k in range(0, len(P) - 5, 6):
            x, z, h = P[k]; nx, nz = P[min(k + 6, len(P) - 6)][:2]
            tx, tz = nx - x, nz - z; L = math.hypot(tx, tz) or 1; ox, oz = -tz / L * (PW + 0.15) * side, tx / L * (PW + 0.15) * side
            pt = (x + ox, z + oz)
            if prev: segs.append([prev[0], prev[1], pt[0], pt[1]])
            prev = pt
    # borda do platô: mureta, com a abertura da escadaria (sul) e da varanda (leste)
    gaps = [(math.radians(96), math.radians(104)), (math.radians(-18), math.radians(18))]
    segs += ring(C[0], C[1], RP - 0.3, 72, gaps=gaps)
    # varanda: guarda-corpo
    x0, z0, x1, z1 = ROOMS['varanda']
    segs += [[x0, z0, x1, z0], [x1, z0, x1, z1], [x1, z1, x0, z1]]
    # cúpula: parede redonda com a porta ao sul
    dc, R = DOME['c'], DOME['r']
    segs += ring(dc[0], dc[1], R, 40, gaps=[(math.radians(80), math.radians(100))])
    # cômodos
    for k in ('recepcao', 'biblioteca', 'laboratorio'):
        segs += wall_rect(*ROOMS[k], DOORS)
    # plataforma do telescópio: borda (menos onde chega a rampa)
    pc = PLATAFORMA['c']
    segs += [s + [PH + PLATAFORMA['h'] + 1.1] for s in ring(pc[0], pc[1], PLATAFORMA['r'] + 0.05, 24, gaps=[(math.radians(68), math.radians(112))])]
    a, b, c2, dd = RAMPA
    segs += [[a, b, a, dd, PH + 1], [c2, b, c2, dd, PH + 1]]
    # bordas do mapa
    segs += [[0, 0, SIZE, 0], [SIZE, 0, SIZE, SIZE], [SIZE, SIZE, 0, SIZE], [0, SIZE, 0, 0]]
    # píer: laterais
    sx, sz, _ = PATH[0]
    segs += [[sx - 1.5, sz + 1.5, sx - 1.5, sz + 8.5], [sx + 1.5, sz + 1.5, sx + 1.5, sz + 8.5], [sx - 1.5, sz + 8.5, sx + 1.5, sz + 8.5]]
    return [[round(v, 3) for v in s] + ([999] if len(s) == 4 else []) for s in segs]

# ---------------------------------------------------------------- móveis e enfeites (o Blender monta; o jogo usa como obstáculo)
# (tipo, x, z, giro em graus, raio do obstáculo ou 0)
def furniture():
    F = []
    add = lambda t, x, z, ry=0, r=0, **kw: F.append(dict(t=t, x=x, z=z, ry=ry, r=r, **kw))
    dcx, dcz = DOME['c']
    # cúpula do observatório
    add('telescopio', 48.0, 35.8, 35, 0)                       # na plataforma, apontado pela fresta para nordeste
    add('orrery', 42.6, 33.5, 0, 0)                            # planetas pendurados
    add('armilar', 54.2, 34.6, 20, 1.3)
    add('mesa_mapas', 41.6, 40.2, 70, 1.4); add('cadeira', 40.6, 41.6, 250, 0.5)
    add('mesa_globo', 55.0, 40.8, -60, 1.0); add('globo', 55.0, 40.8, 0, 0)
    for k, a in enumerate([200, 235, 305, 340]):
        rr = DOME['r'] - 0.75; add('estante_curva', dcx + rr * math.cos(math.radians(a)), dcz + rr * math.sin(math.radians(a)), -a + 90, 0)
    for k, a in enumerate([160, 215, 270, 325, 20]):
        rr = DOME['r'] - 0.35; add('carta_estelar', dcx + rr * math.cos(math.radians(a)), dcz + rr * math.sin(math.radians(a)), -a + 90, 0, seed=k)
    for x, z, ry in [(44.5, 42.5, 30), (51.5, 43.0, -20), (45.8, 33.0, 80), (52.6, 39.6, 10), (50.5, 31.0, 140)]: add('pergaminhos', x, z, ry)
    add('tapete', 48.0, 42.6, 0, 0, w=6, d=3.2, cor='azul')
    add('luneta', 44.0, 31.2, 210, 0.6)
    # recepção
    add('balcao', 48.0, 50.3, 0, 0); F.append(dict(t='_obst', x=48.0, z=50.3, r=0, caixa=(45.2, 49.7, 50.8, 51.1)))
    add('gato', 46.3, 50.3, 160, 0)
    add('livro_aberto', 49.8, 50.3, 10, 0)
    add('tapete', 48.0, 53.4, 0, 0, w=7, d=3.6, cor='vermelho')
    for x in (41.0, 55.0):
        add('estante', x, 47.4, 90 if x < 48 else -90, 0); add('vaso_planta', x, 55.0, 0, 0.6)
    add('poltrona', 42.4, 52.6, 60, 0.7); add('poltrona', 53.6, 52.6, -60, 0.7); add('banquinho', 44.2, 54.0, 0, 0.4)
    add('mesinha', 48.0, 47.6, 0, 0.6); add('ampulheta', 48.0, 47.6, 0, 0)
    add('cabideiro', 54.8, 55.2, 0, 0.3)
    add('quadro_lua', 44.0, 46.8, 0, 0); add('quadro_lua', 52.0, 46.8, 0, 0, seed=2)
    # biblioteca
    for z in (43.0, 45.6, 48.2, 50.8, 53.5): add('estante', 29.4, z, 90, 0)
    for x in (31.4, 34.0, 36.6): add('estante', x, 42.4, 0, 0)
    for x in (31.4, 34.0, 36.6): add('estante', x, 54.6, 180, 0)
    add('atril_livro', 34.6, 48.6, 90, 1.0)                    # o grande livro aberto (referência 4)
    add('mesa_leitura', 34.6, 51.4, 0, 1.2); add('cadeira', 34.6, 52.8, 180, 0.5)
    add('globo_pe', 37.8, 44.8, 0, 0.6); add('escada_mao', 30.6, 46.8, 90, 0)
    for x, z in [(31.8, 50.2), (37.6, 53.2), (32.6, 44.6)]: add('pilha_livros', x, z, rng.uniform(0, 360))
    add('tapete', 34.6, 49.6, 90, 0, w=5, d=3.0, cor='verde')
    # laboratório de alquimia
    add('bancada', 61.0, 44.7, 0, 0); F.append(dict(t='_obst', x=61, z=44.7, r=0, caixa=(57.8, 44.1, 64.2, 45.6)))
    add('caldeirao', 63.6, 51.4, 0, 0.9)
    add('prateleira_frascos', 65.4, 47.0, -90, 0); add('prateleira_frascos', 57.2, 53.4, 180, 0)
    add('mesa_lente', 59.0, 50.6, 30, 1.0)
    add('caixotes', 64.6, 53.0, 20, 0.8)
    # varanda
    add('luneta', 70.6, 46.6, -60, 0.6); add('banco', 69.4, 52.0, 90, 0.5)
    # pátio de entrada
    add('arco', 46.0, 66.4, 0, 0)
    add('banco', 39.0, 60.0, 90, 0.6); add('banco', 57.0, 60.0, -90, 0.6)
    add('estatua', 41.0, 63.4, 30, 0.9)
    add('canteiro', 38.0, 57.2, 0, 0.8); add('canteiro', 58.0, 57.2, 0, 0.8)
    add('fonte', FONTE[0], FONTE[1], 0, 1.4)
    add('relogio_sol', 52.6, 62.0, 0, 0.7)
    # base da escadaria e píer
    sx, sz, _ = PATH[0]
    add('pier', sx, sz + 5.0, 0, 0)
    add('barco', sx + 3.6, sz + 7.2, 10, 0)
    add('barris', sx - 2.3, sz + 1.6, 0, 0)
    return F

FONTES_LUZ = []
def lights(F):
    L = []
    add = lambda m, x, z, ry=0: L.append(dict(kind='luz', model=m, x=round(x, 2), z=round(z, 2), ry=math.radians(ry), scale=1, aceso=True))
    # escadaria: lanternas por fora do caminho
    for t in np.linspace(0.04, 0.97, 8):
        k = int(t * (len(PATH) - 6)); x, z, h = PATH[k]; nx, nz = PATH[k + 3][:2]
        tx, tz = nx - x, nz - z; L2 = math.hypot(tx, tz) or 1
        ox, oz = -tz / L2 * (PW - 0.3), tx / L2 * (PW - 0.3)
        # lado de fora (mais longe do centro)
        if math.hypot(x + ox - C[0], z + oz - C[1]) < math.hypot(x - ox - C[0], z - oz - C[1]): ox, oz = -ox, -oz
        add('lanterna', x + ox, z + oz, -math.degrees(math.atan2(oz, ox)) + 180)
    sx, sz, _ = PATH[0]
    add('lanterna', sx + 1.2, sz + 8.4, 180); add('fogueira', sx - 3.0, sz - 1.2)
    # pátio
    add('braseiro', 42.0, 58.2); add('braseiro', 54.0, 58.2)
    add('poste', 37.6, 64.6); add('poste', 58.4, 64.6)
    add('tocha', 45.2, 56.25, 0); add('tocha', 50.8, 56.25, 0)
    # recepção
    add('orbe', 48.0, 51.8); add('candelabro', 41.2, 49.6); add('candelabro', 54.8, 49.6); add('velas', 47.0, 47.7)
    # biblioteca
    add('orbe', 34.6, 46.4); add('velas', 34.0, 51.4); add('candelabro', 38.6, 50.8)
    # cúpula
    add('cristal', 44.2, 36.0); add('cristal', 52.6, 33.0); add('velas', 41.6, 40.2); add('orbe', 48.0, 41.6); add('velas', 55.2, 41.4)
    # laboratório
    add('braseiro', 63.6, 51.4); add('velas', 61.0, 44.8); add('fatuo', 59.4, 47.0)
    # varanda
    add('lanterna', 71.4, 52.2, 90)
    return L

# ---------------------------------------------------------------- mistura de texturas
def splat(H, M):
    print('mistura de texturas...')
    dc = M['dc']; n1 = fbm(8, 41); n2 = fbm(20, 42); n3 = fbm(3, 43, 3)
    grass = sstep(0.42, 0.62, n2) * (H > 0.8) * (1 - M['on'])
    grass = np.where(M['plat'], 0.65 + 0.3 * n1, grass * sstep(PH - 3, PH - 12, H) * 0.9 + grass * 0.25)
    dirt = np.clip(sstep(0.5, 0.3, n1) * 0.7, 0, 1) * (1 - grass)
    moss = np.clip(1 - grass - dirt, 0, 1)
    sea = H < 0.2
    dirt = np.where(sea, 0.2, dirt); moss = np.where(sea, 0.8, moss); grass = np.where(sea, 0, grass)
    tot = dirt + grass + moss + 1e-6
    A = np.stack([dirt / tot, grass / tot, moss / tot], -1)
    pav = np.clip(M['on'] * 1.0 + M['pier'] * 1.0, 0, 1)
    x0, z0, x1, z1 = ROOMS['patio']
    pav = np.maximum(pav, ((XX > x0) & (XX < x1) & (ZZ > z0) & (ZZ < z1)).astype(float))
    pav = ndimage.gaussian_filter(pav, 0.6)
    lap = ndimage.gaussian_filter(H, 1.5) - ndimage.gaussian_filter(H, 5)
    ao = np.clip(-lap * 0.25, 0, 0.45)
    ao = np.maximum(ao, (M['d'] < PW + 0.3) * (M['d'] > PW - 0.4) * 0.35)     # pé do barranco escuro
    limo = np.clip(sstep(2.5, 0.0, H) * 0.8 + sstep(0.6, 0.8, n3) * 0.3, 0, 1) * (1 - pav)
    Bm = np.stack([pav, ao, limo], -1)
    def save(arr, name, size=2048):
        Image.fromarray((np.clip(arr, 0, 1) * 255).astype(np.uint8)).resize((size, size), Image.BILINEAR).save(os.path.join(OUT, name), optimize=True)
    save(A, 'mistura_a.png'); save(Bm, 'mistura_b.png')
    return A, Bm

def cells(H, M):
    out = []
    for j in range(SQ):
        for i in range(SQ):
            x, z = (i + 0.5) * G, (j + 0.5) * G
            h = float(sample(H, x, z)[0]); d = float(sample(M['d'], x, z)[0])
            out.append('a' if h < -0.3 else 'p' if (d < PW or h >= PH - 0.01) else 'r')
    return ''.join(out)

def main():
    H, M = build()
    F = furniture()
    A, Bm = splat(H, M)
    segs = collision()
    obst = [[f['x'], f['z'], f['r']] for f in F if f.get('r')]
    bx, bz, _ = bacia(); obst.append([round(bx, 2), round(bz, 2), 2.2])   # ninguém entra na bacia
    for f in F:
        if f.get('caixa'):
            a, b, c, d = f['caixa']; segs += [[a, b, c, b, 999], [c, b, c, d, 999], [c, d, a, d, 999], [a, d, a, b, 999]]
    hq = np.clip(np.round(H * 100), -32000, 32000).astype('<i2')
    sx, sz, _ = PATH[0]
    spawn = dict(x=round(sx, 2), z=round(sz + 7.5, 2))
    dados = dict(
        versao=2, nome='Observatório de Letarion', quadrados=SQ, ext=EXT, res=RES, n=NG, x0=X0,
        relevo=base64.b64encode(hq.tobytes()).decode(),
        agua=dict(rio=0.0, lab=-99, salas=[], cor=[0.05, 0.16, 0.24], fundo=[0.01, 0.04, 0.09]),
        texturas=dict(lama='terra.jpg', musgo='grama.jpg', caverna='musgo.jpg', piso='calcada.jpg', rocha='rocha.jpg',
                      escalas=[7.0, 6.0, 6.0, 4.5], limo=[0.12, 0.2, 0.14], sombra=0.55, molhado=True),
        glb='letarion.glb',
        fundo=dict(chao=[0.05, 0.14, 0.22], chao_y=-0.05),   # sem cilindro: o céu (esfera) já traz o horizonte
        ceu=dict(dia='ceu_dia.webp', noite='ceu_noite.webp', tarde='ceu_tarde.webp', raio=600, y=PH, luar=0.06),
        # texturas que os materiais do GLB pedem (o jogo carrega só estas)
        tex_glb=['pedra.jpg', 'pedra_n.png', 'lajes.jpg', 'reboco.jpg', 'madeira.jpg', 'tabuas.jpg', 'telha.jpg', 'cobre.jpg', 'livros.jpg',
                 'carta_a.jpg', 'carta_b.jpg', 'quadro.jpg', 'tapete_vermelho.jpg', 'tapete_azul.jpg', 'tapete_verde.jpg', 'cascata.png', 'espuma.png'],
        colisao=segs, obstaculos=obst, vegetacao=[], bioma='montanha', spawn=spawn,
    )
    with open(os.path.join(OUT, 'dados.json'), 'w') as f: json.dump(dados, f, separators=(',', ':'))
    plano = dict(n=NG, x0=X0, res=RES, relevo=dados['relevo'], ph=PH, rp=RP, c=C.tolist(), path=PATH.round(3).tolist(), pw=PW,
                 dome=DOME, rooms=ROOMS, doors=DOORS, plataforma=PLATAFORMA, rampa=RAMPA, fonte=FONTE, th_cascata=TH_CASCATA,
                 slope=SLOPE, moveis=F)
    with open(os.path.join(ROOT, 'fontes', 'mapas', 'letarion_plano.json'), 'w') as f: json.dump(plano, f)
    cl = cells(H, M)
    L = lights(F)
    pronto = dict(map=dict(name='Observatório de Letarion', w=SQ, h=SQ, walls=[], doors=[], lights=[], hasImage=False, floorMode='tiles',
                           terrain=dict(biome='montanha', cells=cl), spawn=spawn, cenario='letarion'), ents=L)
    with open(os.path.join(ROOT, 'mapas', 'prontos', 'letarion.json'), 'w') as f: json.dump(pronto, f, ensure_ascii=False)
    print('relevo min %.1f max %.1f | colisão %d | obstáculos %d | móveis %d | luzes %d' % (H.min(), H.max(), len(segs), len(obst), len(F), len(L)))
    print('dados.json %.0f KB' % (os.path.getsize(os.path.join(OUT, 'dados.json')) / 1024))
    # prévia de cima
    prev = A @ np.array([[0.45, 0.33, 0.22], [0.36, 0.46, 0.22], [0.25, 0.32, 0.2]])
    prev = prev * (1 - Bm[..., 0:1]) + Bm[..., 0:1] * np.array([0.6, 0.58, 0.55])
    shade = np.clip(1 + (np.gradient(H, axis=1) - np.gradient(H, axis=0)) * 0.12, 0.4, 1.4)
    prev = prev * shade[..., None]
    prev[H < 0] = [0.08, 0.2, 0.32]
    img = Image.fromarray((np.clip(prev, 0, 1) * 255).astype(np.uint8)).resize((NG * 4, NG * 4))
    d = ImageDraw.Draw(img); T = lambda x, z: ((x - X0) * 4, (z - X0) * 4)
    for s in segs: d.line([T(s[0], s[1]), T(s[2], s[3])], fill=(255, 60, 60), width=1)
    for l in L: a, b = T(l['x'], l['z']); d.ellipse([a - 4, b - 4, a + 4, b + 4], fill=(255, 220, 80))
    for f in F: a, b = T(f['x'], f['z']); d.rectangle([a - 2, b - 2, a + 2, b + 2], fill=(80, 200, 255))
    a, b = T(spawn['x'], spawn['z']); d.ellipse([a - 6, b - 6, a + 6, b + 6], fill=(0, 255, 0))
    d.rectangle([T(0, 0), T(SIZE, SIZE)], outline=(255, 255, 255))
    img.save('/tmp/letarion_planta.png')

if __name__ == '__main__':
    main()
