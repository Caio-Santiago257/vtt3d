"""Texturas do Observatório de Letarion, pintadas por código (numpy + Pillow + scipy). Versão 2: mais nítidas e com relevo.

Todas emendam sem costura (ruído periódico) e trazem a luz e a sombra das juntas "assadas" na cor,
porque o material do jogo é de desenho (toon) e não mostra relevo sozinho. As principais têm normal map (_n.png).

Chão do terreno: reaproveita terra, grama, calçada e rocha da Encruzilhada e o musgo do covil.
Paredes e pisos: pedra, pedra_base, reboco, madeira (vigas), tabuas, moveis (madeira polida), lajes, telha, cobre.
Metais e tecidos: latao, ferro, couro, saco, tecido_azul, estandarte (brasão do observatório), tapecaria.
Objetos: lombadas (atlas de 48 livros + páginas), globo, mapa (Ilhas Moonshae), pergaminho, quadro (fases da lua),
         pintura (o observatório à noite), carta_a/b (cartas estelares), tapetes, janela (vitral de dia e aceso à noite),
         casca (tronco), hera e folhas (cartões com transparência), cascata, cascata2, espuma, caldo (poção do caldeirão).
Saída: public/assets/maps/letarion/tex/
Rodar: python3 fontes/mapas/letarion_texturas.py
"""
import math, os, shutil
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy import ndimage
from scipy.spatial import cKDTree

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
OUT = os.path.join(ROOT, 'public', 'assets', 'maps', 'letarion', 'tex')
os.makedirs(OUT, exist_ok=True)
LUZ = np.array([-0.45, 0.55, 0.7]); LUZ = LUZ / np.linalg.norm(LUZ)

# ---------------------------------------------------------------- ferramentas
def pn(n, scale, seed, beta=1.9, m=None):
    """ruído periódico (emenda nos dois sentidos): scale = tamanho dos detalhes maiores, em fração da imagem"""
    m = m or n
    r = np.random.default_rng(seed)
    fx = np.fft.fftfreq(m)[None, :] * m; fy = np.fft.fftfreq(n)[:, None] * n
    f = np.sqrt(fx ** 2 + fy ** 2); f[0, 0] = 1
    k0 = 1 / scale
    filt = 1 / (1 + (k0 / np.maximum(f, 1e-6)) ** 4) / f ** beta    # corta abaixo de k0 (sem manchas maiores que scale)
    filt[0, 0] = 0
    z = np.real(np.fft.ifft2(np.fft.fft2(r.normal(size=(n, m))) * filt))
    z = (z - z.min()) / (z.max() - z.min() + 1e-9)
    return z
def hexc(h): h = h.lstrip('#'); return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], float) / 255
def sstep(a, b, x): t = np.clip((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t)
def normal_de(h, forca):
    gx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) * 0.5; gy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) * 0.5
    nm = np.stack([-gx * forca, gy * forca, np.ones_like(h)], -1)     # verde para cima (OpenGL)
    return nm / np.linalg.norm(nm, axis=-1, keepdims=True)
def assa(col, h, forca, ao=0.0, luz=0.32):
    """luz e sombra do relevo, e escuro nas cavidades, gravados na cor"""
    nm = normal_de(h, forca)
    nl = np.clip(nm[..., 0] * LUZ[0] - nm[..., 1] * LUZ[1] + nm[..., 2] * LUZ[2], 0, 1)
    sh = (1 - luz) + luz * nl / max(1e-6, LUZ[2])
    if ao:
        cav = np.clip(ndimage.gaussian_filter(h, 6, mode='wrap') - h, 0, None)
        sh = sh * (1 - np.clip(cav * ao, 0, 0.6))
    return col * sh[..., None], nm
def save(name, arr, q=90):
    img = Image.fromarray((np.clip(arr, 0, 1) * 255 + 0.5).astype(np.uint8))
    if name.endswith('.png'): img.save(os.path.join(OUT, name), optimize=True)
    else: img.convert('RGB').save(os.path.join(OUT, name), quality=q)
def save_n(name, nm): save(name, nm * 0.5 + 0.5)

def cursos(n, alturas, larg, seed, junta=0.012, m=None):
    """fiadas de blocos (periódico): devolve id (0..1 por bloco), distância à borda (px), coordenadas locais"""
    m = m or n
    r = np.random.default_rng(seed)
    ids = np.zeros((n, m)); dist = np.zeros((n, m))
    y = 0; rows = []
    while y < n:
        h = int(r.choice(alturas) * n)
        if n - y < min(alturas) * n * 1.4: h = n - y
        rows.append((y, min(n, y + h))); y += h
    X = np.arange(m)
    for (y0, y1) in rows:
        xs = [r.uniform(0, m)]; tot = 0
        while tot < m * 0.999:
            w = r.uniform(*larg) * m
            if m - tot < larg[0] * m * 1.5: w = m - tot
            tot += w; xs.append(xs[0] + tot)
        for k in range(len(xs) - 1):
            a, b = xs[k], xs[k + 1]
            xx = (X - a) % m; msk = xx < (b - a)
            ids[y0:y1, msk] = r.random()
            dx = np.minimum(xx, (b - a) - xx)[msk]
            yy = np.arange(y0, y1)[:, None]
            dy = np.minimum(yy - y0, y1 - 1 - yy)
            dist[y0:y1, msk] = np.minimum(dx[None, :], dy)
    return ids, dist

def voronoi(n, pts_n, seed, m=None):
    m = m or n
    r = np.random.default_rng(seed)
    P = r.random((pts_n, 2))
    t = cKDTree(P, boxsize=1.0)
    yy, xx = np.mgrid[0:n, 0:m]
    q = np.stack([(xx.ravel() + 0.5) / m, (yy.ravel() + 0.5) / n], -1)
    d, i = t.query(q, k=2)
    d1 = d[:, 0].reshape(n, m); d2 = d[:, 1].reshape(n, m); idx = i[:, 0].reshape(n, m)
    return idx, (d2 - d1), d1, r.random(pts_n)

# ---------------------------------------------------------------- pedra das paredes: cantaria em fiadas, blocos com quinas lascadas
def pedra(nome='pedra', base='#a59c8c', var=0.16, seed=5, alturas=(0.125, 0.1666, 0.25), larg=(0.18, 0.42)):
    n = 1024
    ids, dist = cursos(n, alturas, larg, seed)
    bord = dist + (pn(n, 0.04, seed + 1) - 0.5) * 12 + (pn(n, 0.015, seed + 2) - 0.5) * 4   # bordas irregulares e lascadas
    bloco = sstep(3.0, 18.0, bord)                                    # 0 na junta, 1 no meio do bloco
    sup = pn(n, 0.15, seed + 3) * 0.55 + pn(n, 0.05, seed + 4) * 0.35 + pn(n, 0.02, seed + 9) * 0.1
    pits = np.clip((pn(n, 0.03, seed + 5) - 0.85) * 6, 0, 1)
    h = bloco * (0.85 + 0.15 * sup) - pits * 0.05
    borda_esc = 1 - 0.35 * (1 - sstep(0.0, 0.5, bloco))   # quina do bloco um pouco mais escura
    tons = np.stack([ids, np.roll(ids, 1, 0), ids * 0.7], -1)
    col = hexc(base)[None, None] * (1 + (tons - 0.5) * var * 2.4)
    quente = (np.roll(ids, 3, 1) > 0.7)[..., None] * np.array([0.06, 0.02, -0.03])   # alguns blocos mais amarelados
    col = col + quente
    manch = pn(n, 0.06, seed + 10)
    col = col * (0.78 + 0.3 * sup[..., None]) * (0.9 + 0.16 * manch[..., None])
    musgo = np.clip((pn(n, 0.12, seed + 6) - 0.68) * 3.5, 0, 1) * (1 - bloco * 0.5)
    col = col * (1 - musgo[..., None] * 0.35) + hexc('#56603a') * musgo[..., None] * 0.35
    arg = hexc('#bdb3a0') * (0.8 + 0.2 * pn(n, 0.03, seed + 7))[..., None]
    col = col * bloco[..., None] + arg * (1 - bloco[..., None])
    col = col * borda_esc[..., None]
    col, nm = assa(col, h * 22, 1.0, ao=0, luz=0.42)
    save(nome + '.jpg', col); save_n(nome + '_n.png', nm)

# ---------------------------------------------------------------- reboco de cal (andar de cima)
def reboco():
    n = 1024
    a = pn(n, 0.25, 11); b = pn(n, 0.05, 12); c = pn(n, 0.01, 13)
    h = a * 0.4 + b * 0.35 + c * 0.25
    col = hexc('#e9dcc2')[None, None] * (0.86 + 0.16 * a[..., None]) * (0.95 + 0.07 * c[..., None])
    mancha = np.clip((pn(n, 0.2, 14) - 0.6) * 2.5, 0, 1)
    col = col * (1 - mancha[..., None] * 0.12) + hexc('#b9a582') * mancha[..., None] * 0.08
    # rachaduras finas
    idx, borda, _, _ = voronoi(n, 14, 15)
    rach = np.exp(-(borda * n / 1.2) ** 2) * (pn(n, 0.1, 16) > 0.62)
    col = col * (1 - rach[..., None] * 0.35); h = h - rach * 0.5
    col, nm = assa(col, h * 6, 1.0, luz=0.22)
    save('reboco.jpg', col); save_n('reboco_n.png', nm)

# ---------------------------------------------------------------- madeiras
def veio(n, m, seed, aneis=26, torcer=9):
    """veios ao longo do eixo x"""
    y, x = np.mgrid[0:n, 0:m] / np.array([n, m])[:, None, None]
    w = pn(n, 0.5, seed, m=m) * torcer + pn(n, 0.12, seed + 1, m=m) * 0.25
    g = np.sin((y * aneis + w) * math.pi * 2) * 0.5 + 0.5
    return g ** 3, w
def madeira(nome, c0, c1, n=1024, tabuas=0, seed=21, nos=True, forca=6.0):
    r = np.random.default_rng(seed)
    g, w = veio(n, n, seed, aneis=26, torcer=1.1)
    fibra = ndimage.uniform_filter1d(pn(n, 0.02, seed + 2), 90, axis=1, mode='wrap')
    fibra = (fibra - fibra.min()) / (fibra.max() - fibra.min() + 1e-9)
    fibra = fibra * 0.7 + pn(n, 0.08, seed + 3) * 0.3
    t = (0.35 + 0.4 * fibra + 0.25 * g)[..., None]
    col = hexc(c0)[None, None] * (1 - t) + hexc(c1)[None, None] * t
    h = g * 0.4 + fibra * 0.5
    y, x = np.mgrid[0:n, 0:n] / n
    if tabuas:
        pid = np.floor(y * tabuas).astype(int)
        tom = r.uniform(0.78, 1.12, tabuas)[pid]
        col = col * tom[..., None]
        # cada tábua emenda num ponto diferente
        cut = r.random(tabuas)[pid]; cx = (x - cut) % 1
        junta = np.minimum(np.abs((y * tabuas) - np.round(y * tabuas)) * n / tabuas, np.minimum(cx, 1 - cx) * n)
        gap = sstep(1.0, 4.0, junta)
        col = col * (0.35 + 0.65 * gap[..., None]); h = h * gap - (1 - gap) * 0.6
        # pregos nas pontas
        prego = np.zeros((n, n))
        for k in range(tabuas):
            c = r.random(); yc = (k + 0.5) / tabuas
            for dx in (0.012, 1 - 0.012):
                for dy in (-0.25, 0.25):
                    xc = (c + dx) % 1; yy = yc + dy / tabuas
                    prego += np.exp(-(((x - xc + 0.5) % 1 - 0.5) ** 2 + ((y - yy + 0.5) % 1 - 0.5) ** 2) / (0.0025 ** 2))
        col = col * (1 - np.clip(prego, 0, 1)[..., None] * 0.6)
    if nos:
        for _ in range(5):
            cx, cy = r.random(), r.random(); rr = r.uniform(0.012, 0.03)
            d = np.hypot(((x - cx + 0.5) % 1 - 0.5), ((y - cy + 0.5) % 1 - 0.5) * 1.6)
            k = np.exp(-(d / rr) ** 2)
            col = col * (1 - k[..., None] * 0.55); h = h - k * 0.3
    col, nm = assa(col, h * forca, 1.0, luz=0.25)
    save(nome + '.jpg', col); save_n(nome + '_n.png', nm)

# ---------------------------------------------------------------- lajes do pátio e dos pisos: pedras irregulares
def lajes():
    n = 1024
    idx, borda, d1, tom = voronoi(n, 46, 51)
    b = borda * n + (pn(n, 0.02, 52) - 0.5) * 6
    laje = sstep(2.5, 10.0, b)
    sup = pn(n, 0.12, 53) * 0.6 + pn(n, 0.04, 54) * 0.4
    t = tom[idx]
    col = hexc('#c1b296')[None, None] * (0.82 + 0.32 * t[..., None]) * (0.9 + 0.15 * sup[..., None])
    col = col * np.array([1, 0.98 + 0.04 * 0, 0.96])
    rej = hexc('#8a7e68') * (0.8 + 0.3 * pn(n, 0.03, 55))[..., None]
    col = col * laje[..., None] + rej * (1 - laje[..., None])
    h = laje * (0.92 + 0.08 * sup)
    col, nm = assa(col, h * 18, 1.0, ao=0, luz=0.3)
    save('lajes.jpg', col); save_n('lajes_n.png', nm)

# ---------------------------------------------------------------- telhas de barro sobrepostas
def telha():
    n = 1024; rows = 12; cols = 9
    y, x = np.mgrid[0:n, 0:n] / n
    row = np.floor(y * rows); off = (row % 2) * 0.5
    u = (x * cols + off) % 1; v = (y * rows) % 1
    ci = np.floor(x * cols + off).astype(int) % cols
    r = np.random.default_rng(41); tons = r.uniform(0.7, 1.15, (rows, cols))
    t = tons[row.astype(int) % rows, ci]
    arco = 1 - ((u - 0.5) * 2) ** 2                                   # telha curva (capa)
    fundo_ponta = sstep(0.0, 0.15, v)                                  # sombra da fiada de cima
    h = arco * 0.6 + (1 - v) * 0.5
    borda = np.minimum(u, 1 - u)
    lado = sstep(0.0, 0.06, borda)
    col = hexc('#a5502f')[None, None] * t[..., None] * (0.55 + 0.45 * arco[..., None]) * (0.55 + 0.45 * fundo_ponta[..., None])
    col = col * (0.6 + 0.4 * lado[..., None])
    sup = pn(n, 0.03, 42)
    col = col * (0.9 + 0.15 * sup[..., None])
    musgo = np.clip((pn(n, 0.15, 43) - 0.62) * 3, 0, 1) * (v > 0.5)
    col = col * (1 - musgo[..., None] * 0.5) + hexc('#6a7a3a') * musgo[..., None] * 0.45
    col, nm = assa(col, h * 10 + sup, 1.0, luz=0.3)
    save('telha.jpg', col); save_n('telha_n.png', nm)

# ---------------------------------------------------------------- cobre da cúpula: placas com costura em pé e pátina verde
def cobre():
    n = 1024
    y, x = np.mgrid[0:n, 0:n] / n
    pan = 8
    su = np.abs((x * pan) % 1 - 0.5) * 2                               # 1 na costura
    costura = sstep(0.9, 0.97, su)
    fiada = (np.abs((y * 5) % 1 - 0.5) * 2 > 0.965)
    patina = pn(n, 0.12, 61) * 0.6 + pn(n, 0.02, 62) * 0.4
    escorrido = pn(n, 0.03, 63, m=n)
    esc = np.clip((np.repeat(pn(1, 0.05, 64, m=n), n, 0) - 0.4) * 2, 0, 1) * (0.6 + 0.4 * escorrido)
    verde = hexc('#5fa08a'); marrom = hexc('#8a5a34'); escuro = hexc('#3e5e54')
    k = np.clip(patina * 1.3 - 0.15 + esc * 0.4, 0, 1)[..., None]
    col = marrom * (1 - k) + verde * k
    col = col * (0.8 + 0.3 * pn(n, 0.006, 65)[..., None])
    col = np.where(costura[..., None] > 0.5, col * 0.75 + escuro * 0.2, col)
    col = np.where(fiada[..., None], col * 0.7, col)
    h = costura * 1.0 - fiada * 0.4 + patina * 0.1
    col, nm = assa(col, h * 8, 1.0, luz=0.3)
    save('cobre.jpg', col); save_n('cobre_n.png', nm)

# ---------------------------------------------------------------- metais, couro, tecidos
def latao():
    n = 512
    esc = pn(n, 0.006, 71, m=n); esc = ndimage.uniform_filter1d(esc, 40, axis=1, mode='wrap')   # escovado
    manch = pn(n, 0.25, 72)
    col = hexc('#c99a45')[None, None] * (0.82 + 0.3 * esc[..., None])
    col = col * (1 - np.clip(manch - 0.6, 0, 1)[..., None] * 0.8)
    col = col + np.clip(esc - 0.65, 0, 1)[..., None] * 0.5                # riscos claros
    save('latao.jpg', col)
def ferro():
    n = 512
    m = pn(n, 0.04, 81) * 0.6 + pn(n, 0.01, 82) * 0.4
    col = hexc('#3a3a3e')[None, None] * (0.7 + 0.6 * m[..., None])
    fer = np.clip((pn(n, 0.1, 83) - 0.62) * 3, 0, 1)
    col = col * (1 - fer[..., None] * 0.5) + hexc('#7a4426') * fer[..., None] * 0.5
    col, _ = assa(col, m * 4, 1.0, luz=0.25)
    save('ferro.jpg', col)
def couro():
    n = 512
    idx, borda, _, _ = voronoi(n, 900, 91)
    rug = sstep(0, 0.006, borda)
    m = pn(n, 0.2, 92)
    col = hexc('#6b2a1c')[None, None] * (0.8 + 0.3 * m[..., None]) * (0.85 + 0.15 * rug[..., None])
    col, _ = assa(col, rug * 2 + m, 1.0, luz=0.2)
    save('couro.jpg', col)
def saco():
    n = 512; y, x = np.mgrid[0:n, 0:n] / n
    tr = (np.sin(x * n * math.pi / 3) * np.sin(y * n * math.pi / 3)) * 0.5 + 0.5
    m = pn(n, 0.1, 95)
    col = hexc('#a48a5c')[None, None] * (0.75 + 0.35 * tr[..., None]) * (0.85 + 0.2 * m[..., None])
    save('saco.jpg', col)
def tecido(nome, cor, n=256, seed=101):
    y, x = np.mgrid[0:n, 0:n] / n
    tr = (np.sin(x * n * math.pi / 2) * 0.5 + 0.5) * 0.5 + (np.sin(y * n * math.pi / 2) * 0.5 + 0.5) * 0.5
    col = hexc(cor)[None, None] * (0.82 + 0.25 * tr[..., None]) * (0.9 + 0.15 * pn(n, 0.2, seed)[..., None])
    save(nome, col)

def estandarte():
    """estandarte do observatório: azul-noite com borda dourada, uma estrela de oito pontas sobre o telescópio"""
    W, H = 512, 1024
    img = Image.new('RGB', (W, H), (26, 38, 82)); d = ImageDraw.Draw(img)
    ouro = (214, 172, 82)
    d.rectangle([14, 14, W - 15, H - 15], outline=ouro, width=10)
    d.rectangle([34, 34, W - 35, H - 35], outline=(150, 118, 58), width=3)
    cx, cy = W // 2, int(H * 0.36)
    for k in range(8):
        a = k * math.pi / 4; R = 150 if k % 2 == 0 else 90
        p = [(cx + math.cos(a) * R, cy + math.sin(a) * R), (cx + math.cos(a + 0.22) * 28, cy + math.sin(a + 0.22) * 28), (cx, cy), (cx + math.cos(a - 0.22) * 28, cy + math.sin(a - 0.22) * 28)]
        d.polygon(p, fill=ouro if k % 2 == 0 else (240, 216, 150))
    d.ellipse([cx - 22, cy - 22, cx + 22, cy + 22], fill=(255, 240, 200))
    # telescópio estilizado e um arco de estrelas
    d.polygon([(150, 760), (330, 600), (350, 625), (172, 785)], fill=ouro)
    d.polygon([(230, 700), (210, 860), (232, 860), (250, 712)], fill=(150, 118, 58)); d.polygon([(250, 700), (300, 860), (322, 860), (268, 700)], fill=(150, 118, 58))
    for k in range(9):
        a = math.pi * (0.15 + 0.7 * k / 8); x = cx + math.cos(a) * 200; y = cy + 120 + math.sin(a) * 200 * 0.0 + (k % 2) * 0
        x = cx + math.cos(math.pi + a) * 205; y = cy - math.sin(a) * 40 + 250
        d.ellipse([x - 7, y - 7, x + 7, y + 7], fill=(240, 216, 150))
    arr = np.asarray(img, float) / 255
    tr = (np.sin(np.arange(W) * math.pi / 2) * 0.5 + 0.5)[None, :, None] * 0.08
    arr = arr * (0.94 + tr) * (0.9 + 0.12 * pn(H, 0.2, 111, m=W)[..., None])
    save('estandarte.jpg', arr)

def tapecaria():
    """tapeçaria da biblioteca: a roda do céu com os signos em volta"""
    W, H = 768, 1024
    img = Image.new('RGB', (W, H), (88, 24, 30)); d = ImageDraw.Draw(img)
    ouro = (206, 162, 78)
    d.rectangle([12, 12, W - 13, H - 13], outline=ouro, width=14)
    for k in range(0, W, 48): d.polygon([(k, 40), (k + 24, 64), (k + 48, 40)], outline=ouro)
    cx, cy, R = W // 2, H // 2, 290
    for rr, w in [(R, 6), (R - 70, 3), (R - 160, 4)]: d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], outline=ouro, width=w)
    for k in range(12):
        a = k * math.pi / 6
        d.line([(cx + math.cos(a) * (R - 70), cy + math.sin(a) * (R - 70)), (cx + math.cos(a) * R, cy + math.sin(a) * R)], fill=ouro, width=3)
        b = a + math.pi / 12; x, y = cx + math.cos(b) * (R - 35), cy + math.sin(b) * (R - 35)
        d.ellipse([x - 12, y - 12, x + 12, y + 12], outline=(240, 220, 160), width=3)
        d.line([(x - 8, y), (x + 8, y)], fill=(240, 220, 160), width=2)
    d.ellipse([cx - 60, cy - 60, cx + 60, cy + 60], fill=(236, 196, 96))
    for k in range(16):
        a = k * math.pi / 8; d.line([(cx + math.cos(a) * 70, cy + math.sin(a) * 70), (cx + math.cos(a) * 120, cy + math.sin(a) * 120)], fill=(236, 196, 96), width=5)
    arr = np.asarray(img, float) / 255
    tr = ((np.sin(np.arange(W) * math.pi / 2) * 0.5 + 0.5)[None, :] * (np.sin(np.arange(H) * math.pi / 2) * 0.5 + 0.5)[:, None])[..., None]
    arr = arr * (0.86 + 0.18 * tr) * (0.9 + 0.12 * pn(H, 0.15, 121, m=W)[..., None])
    save('tapecaria.jpg', arr)

# ---------------------------------------------------------------- livros: atlas de lombadas (48) + faixa de páginas
def lombadas():
    W, H = 2048, 1024; cols, rows = 16, 3
    cw, ch = W // cols, (H * 3 // 4) // rows
    r = np.random.default_rng(131)
    img = Image.new('RGB', (W, H), (40, 25, 15)); d = ImageDraw.Draw(img)
    pal = ['#7a1f1f', '#1f3d7a', '#2f5a2a', '#6b4a1a', '#4a2a5a', '#8a6a2a', '#2a2a2a', '#5a1a2a', '#1a4a4a', '#a0522d', '#3d5a8a', '#7a5a3a', '#244a32', '#8a2a2a', '#c49a50', '#5a3a6a']
    ouro = [(222, 186, 96), (200, 160, 80), (236, 210, 140)]
    for i in range(rows):
        for j in range(cols):
            x0, y0 = j * cw, i * ch
            c = hexc(pal[(i * cols + j) * 7 % len(pal)]) * r.uniform(0.75, 1.15)
            cc = tuple(int(v * 255) for v in np.clip(c, 0, 1))
            d.rectangle([x0, y0, x0 + cw - 1, y0 + ch - 1], fill=cc)
            g = ouro[int(r.integers(3))]
            estilo = int(r.integers(4))
            # nervuras (faixas em relevo) e bandas douradas
            nb = int(r.integers(2, 5))
            for k in range(nb):
                yy = y0 + int(ch * (0.12 + 0.76 * k / max(1, nb - 1)))
                d.rectangle([x0 + 4, yy - 6, x0 + cw - 5, yy + 6], fill=tuple(int(v * 0.7) for v in cc))
                d.line([(x0 + 4, yy - 7), (x0 + cw - 5, yy - 7)], fill=g, width=2); d.line([(x0 + 4, yy + 7), (x0 + cw - 5, yy + 7)], fill=g, width=2)
            # etiqueta do título
            ty = y0 + int(ch * r.uniform(0.25, 0.4)); th = int(ch * 0.16)
            if estilo < 2:
                d.rectangle([x0 + 14, ty, x0 + cw - 15, ty + th], fill=(28, 20, 14) if estilo == 0 else g)
                for k in range(3):
                    lx = x0 + 22 + k * 4; d.line([(x0 + 22, ty + 10 + k * 14), (x0 + cw - 22 - r.integers(0, 30), ty + 10 + k * 14)], fill=g if estilo == 0 else (40, 26, 16), width=4)
            elif estilo == 2:
                for k in range(int(r.integers(4, 8))):
                    yy = ty + k * 16; d.line([(x0 + cw // 2 - 3, yy), (x0 + cw // 2 + 3, yy)], fill=g, width=6)
            else:
                d.ellipse([x0 + cw // 2 - 22, ty, x0 + cw // 2 + 22, ty + 44], outline=g, width=4)
                d.ellipse([x0 + cw // 2 - 6, ty + 16, x0 + cw // 2 + 6, ty + 28], fill=g)
            # sombra nas bordas (lombada arredondada)
    arr = np.asarray(img, float) / 255
    xx = (np.arange(W) % cw) / cw
    arred = (0.55 + 0.45 * np.sin(xx * math.pi) ** 0.6)[None, :, None]
    yy = np.arange(H)[:, None, None]
    arr = np.where(yy < H * 3 // 4, arr * arred, arr)
    arr = arr * (0.88 + 0.18 * pn(H, 0.01, 132, m=W)[..., None])
    # páginas: faixa de baixo (miolo creme com linhas finas)
    y0 = H * 3 // 4
    pg = np.ones((H - y0, W, 3)) * hexc('#e8dcb8')
    linhas = (np.sin(np.arange(H - y0) * math.pi / 1.6) * 0.5 + 0.5)[:, None, None]
    pg = pg * (0.82 + 0.18 * linhas) * (0.92 + 0.1 * pn(H - y0, 0.05, 133, m=W)[..., None])
    arr[y0:] = pg
    save('lombadas.jpg', arr, q=92)

def globo():
    W, H = 1024, 512
    y, x = np.mgrid[0:H, 0:W] / np.array([H, W])[:, None, None]
    lat = (0.5 - y) * math.pi; lon = x * 2 * math.pi
    terra = pn(H, 0.6, 141, m=W) * 0.75 + pn(H, 0.12, 142, m=W) * 0.25
    terra = terra - np.abs(lat) * 0.15
    land = terra > 0.56
    mar = hexc('#3d6f86') * (0.85 + 0.15 * pn(H, 0.1, 143, m=W))[..., None]
    chao = hexc('#c8ac74') * (0.85 + 0.25 * pn(H, 0.04, 144, m=W))[..., None]
    col = np.where(land[..., None], chao, mar)
    costa = np.abs(terra - 0.56) < 0.006
    col = np.where(costa[..., None], hexc('#4a3a22'), col)
    grade = (np.abs(((lat / math.pi * 12) + 0.5) % 1 - 0.5) < 0.02) | (np.abs(((lon / math.pi * 12) + 0.5) % 1 - 0.5) < 0.012)
    col = np.where(grade[..., None], col * 0.75 + hexc('#e8dcb0') * 0.25, col)
    col = col * (0.9 + 0.12 * pn(H, 0.3, 145, m=W)[..., None]) * np.array([1.0, 0.97, 0.88])   # verniz envelhecido
    save('globo.jpg', col)

def mapa():
    """mapa das Ilhas Moonshae em pergaminho"""
    W, H = 1024, 768
    y, x = np.mgrid[0:H, 0:W] / np.array([H, W])[:, None, None]
    papel = hexc('#e3cf9e') * (0.82 + 0.2 * pn(H, 0.2, 151, m=W))[..., None]
    borda = np.minimum(np.minimum(x, 1 - x), np.minimum(y, 1 - y))
    papel = papel * (0.7 + 0.3 * sstep(0, 0.08, borda))[..., None]
    ilhas = np.zeros((H, W))
    for (cx, cy, rx, ry, s) in [(0.42, 0.4, 0.16, 0.22, 1), (0.62, 0.62, 0.12, 0.14, 2), (0.3, 0.72, 0.08, 0.1, 3), (0.72, 0.3, 0.07, 0.06, 4), (0.85, 0.75, 0.04, 0.05, 5)]:
        e = 1 - np.hypot((x - cx) / rx, (y - cy) / ry)
        ilhas = np.maximum(ilhas, e + (pn(H, 0.1, 160 + s, m=W) - 0.5) * 0.6)
    land = ilhas > 0.05
    col = np.where(land[..., None], papel * np.array([0.92, 0.95, 0.8]), papel * np.array([0.82, 0.9, 0.95]))
    costa = np.abs(ilhas - 0.05) < 0.012
    col = np.where(costa[..., None], hexc('#5a3e22'), col)
    ondas = (np.abs(ilhas + 0.08) < 0.004) | (np.abs(ilhas + 0.16) < 0.003)
    col = np.where(ondas[..., None], col * 0.8, col)
    img = Image.fromarray((np.clip(col, 0, 1) * 255).astype(np.uint8)); d = ImageDraw.Draw(img)
    cx, cy = 880, 140
    for k in range(8):
        a = k * math.pi / 4; R = 70 if k % 2 == 0 else 35
        d.polygon([(cx, cy), (cx + math.cos(a - 0.2) * 16, cy + math.sin(a - 0.2) * 16), (cx + math.cos(a) * R, cy + math.sin(a) * R), (cx + math.cos(a + 0.2) * 16, cy + math.sin(a + 0.2) * 16)], fill=(90, 60, 30) if k % 2 == 0 else (160, 110, 60))
    d.ellipse([cx - 80, cy - 80, cx + 80, cy + 80], outline=(90, 60, 30), width=3)
    for (px, py) in [(420, 300), (640, 470), (300, 550), (500, 260)]:
        d.rectangle([px - 5, py - 5, px + 5, py + 5], fill=(140, 30, 30))
        d.line([(px + 10, py), (px + 70, py)], fill=(70, 50, 30), width=3)
    d.rectangle([20, 20, W - 21, H - 21], outline=(110, 75, 40), width=6)
    img.save(os.path.join(OUT, 'mapa.jpg'), quality=90)

def pergaminho():
    W, H = 512, 512
    r = np.random.default_rng(171)
    papel = hexc('#eadcb4') * (0.85 + 0.18 * pn(H, 0.2, 172, m=W))[..., None]
    img = Image.fromarray((np.clip(papel, 0, 1) * 255).astype(np.uint8)); d = ImageDraw.Draw(img)
    y = 40
    while y < H - 40:
        x = 36
        while x < W - 60:
            w = int(r.integers(12, 60)); d.line([(x, y), (x + w, y + int(r.integers(-1, 2)))], fill=(70, 50, 32), width=2); x += w + 10
        y += 22
    d.ellipse([360, 380, 450, 470], outline=(140, 40, 40), width=4); d.ellipse([385, 405, 425, 445], fill=(150, 40, 40))
    img.save(os.path.join(OUT, 'pergaminho.jpg'), quality=88)

def quadro_lua():
    n = 512; img = Image.new('RGB', (n, n), (22, 30, 58)); d = ImageDraw.Draw(img)
    r = np.random.default_rng(181)
    for _ in range(140):
        x, y = r.random(2) * n; s = r.random() * 1.6; d.ellipse([x - s, y - s, x + s, y + s], fill=(220, 220, 240))
    for k, ph in enumerate([0.0, 0.3, 0.6, 1.0, 0.6, 0.3]):
        cx = 52 + k * 82; cy = n // 2; rr = 34
        d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill=(234, 228, 204))
        if ph < 1: d.ellipse([cx - rr + ph * 2 * rr * (1 if k < 3 else -1), cy - rr, cx + rr + ph * 2 * rr * (1 if k < 3 else -1), cy + rr], fill=(22, 30, 58))
    d.arc([40, 120, n - 40, 520], 200, 340, fill=(200, 170, 90), width=3)
    d.rectangle([4, 4, n - 5, n - 5], outline=(170, 130, 60), width=14)
    d.rectangle([20, 20, n - 21, n - 21], outline=(110, 80, 40), width=3)
    img.save(os.path.join(OUT, 'quadro.jpg'), quality=90)

def pintura():
    """pintura a óleo: o observatório no pico, à noite, visto do mar"""
    W, H = 768, 512
    y, x = np.mgrid[0:H, 0:W] / np.array([H, W])[:, None, None]
    ceu = hexc('#0e1a3c') * (1 - y[..., None]) + hexc('#3a4a7a') * y[..., None]
    mar_y = 0.72
    pico = mar_y - 0.55 * np.clip(1 - np.abs(x - 0.55) / 0.28, 0, 1) ** 1.4 - (pn(H, 0.05, 191, m=W)[0:1] - 0.5) * 0.04
    col = np.where((y > pico)[..., None], hexc('#1c1a24') * (0.8 + 0.3 * pn(H, 0.05, 192, m=W))[..., None], ceu)
    col = np.where((y > mar_y)[..., None], hexc('#13213c') * (0.8 + 0.4 * (np.sin(y * 300 + x * 20) * 0.5 + 0.5))[..., None], col)
    img = Image.fromarray((np.clip(col, 0, 1) * 255).astype(np.uint8)); d = ImageDraw.Draw(img)
    r = np.random.default_rng(193)
    for _ in range(260):
        px, py = r.random() * W, r.random() * H * 0.6; s = r.random() ** 3 * 2.5 + 0.5
        d.ellipse([px - s, py - s, px + s, py + s], fill=(240, 236, 210))
    d.ellipse([110, 60, 170, 120], fill=(244, 236, 200))
    top = int(H * (mar_y - 0.55)); cx = int(W * 0.55)
    d.rectangle([cx - 40, top - 26, cx + 40, top + 6], fill=(60, 50, 44)); d.pieslice([cx - 22, top - 52, cx + 22, top - 8], 180, 360, fill=(80, 130, 110))
    for k in range(5): d.rectangle([cx - 34 + k * 15, top - 14, cx - 28 + k * 15, top - 6], fill=(255, 200, 110))
    d.line([(cx, top - 40), (cx + 34, top - 70)], fill=(210, 170, 90), width=5)
    arr = np.asarray(img, float) / 255
    pinc = pn(H, 0.01, 194, m=W)
    arr = arr * (0.9 + 0.2 * pinc[..., None])
    img = Image.fromarray((np.clip(arr, 0, 1) * 255).astype(np.uint8)).filter(ImageFilter.SMOOTH_MORE); d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W - 1, H - 1], outline=(176, 134, 60), width=22); d.rectangle([22, 22, W - 23, H - 23], outline=(100, 70, 34), width=4)
    img.save(os.path.join(OUT, 'pintura.jpg'), quality=90)

def carta(seed, nome):
    n = 1024; r = np.random.default_rng(seed)
    y, x = np.mgrid[0:n, 0:n] / n
    fundo = hexc('#0f1d3e') * (0.8 + 0.3 * pn(n, 0.3, seed + 1))[..., None]
    img = Image.fromarray((np.clip(fundo, 0, 1) * 255).astype(np.uint8)); d = ImageDraw.Draw(img)
    ouro = (206, 170, 92)
    for rr in (n * 0.47, n * 0.33, n * 0.18):
        d.ellipse([n / 2 - rr, n / 2 - rr, n / 2 + rr, n / 2 + rr], outline=ouro, width=3)
    for k in range(24):
        a = k * math.pi / 12; d.line([(n / 2 + math.cos(a) * n * 0.33, n / 2 + math.sin(a) * n * 0.33), (n / 2 + math.cos(a) * n * 0.47, n / 2 + math.sin(a) * n * 0.47)], fill=ouro, width=2)
    for _ in range(1400):
        px, py = r.random(2) * n; s = r.random() ** 4 * 3.5 + 0.6
        c = int(170 + r.random() * 85); d.ellipse([px - s, py - s, px + s, py + s], fill=(c, c, min(255, c + 15)))
    for _ in range(7):
        pts = [tuple(r.random(2) * n * 0.6 + n * 0.2)]
        for k in range(int(r.integers(3, 7))): px, py = pts[-1]; pts.append((px + r.normal(0, 90), py + r.normal(0, 90)))
        d.line(pts, fill=(160, 190, 240), width=2)
        for p in pts: d.ellipse([p[0] - 6, p[1] - 6, p[0] + 6, p[1] + 6], fill=(255, 246, 214))
    d.rectangle([6, 6, n - 7, n - 7], outline=ouro, width=12)
    img.save(os.path.join(OUT, nome), quality=90)

def tapete(nome, c_fundo, c_borda, c_motivo, seed, redondo=False):
    n = 1024; y, x = np.mgrid[0:n, 0:n] / n
    F, Bd, Mt = hexc(c_fundo), hexc(c_borda), hexc(c_motivo)
    col = np.ones((n, n, 3)) * F
    if redondo:
        rr = np.hypot(x - 0.5, y - 0.5) * 2
        a = np.arctan2(y - 0.5, x - 0.5)
        col = np.where((rr > 0.86)[..., None], Bd, col)
        col = np.where((np.abs(rr - 0.8) < 0.012)[..., None] | (np.abs(rr - 0.93) < 0.01)[..., None], Mt, col)
        raios = (np.abs(((a / math.pi * 6) + 0.5) % 1 - 0.5) < 0.015) & (rr < 0.8) & (rr > 0.2)
        col = np.where(raios[..., None], Mt * 0.8 + F * 0.2, col)
        anel = np.abs(rr - 0.5) < 0.008
        col = np.where(anel[..., None], Mt, col)
        r = np.random.default_rng(seed)
        for _ in range(200):
            px, py = r.random(2)
            if np.hypot(px - 0.5, py - 0.5) * 2 > 0.78: continue
            s = r.random() ** 3 * 0.008 + 0.002
            col = np.where((np.hypot(x - px, y - py) < s)[..., None], hexc('#f0e4b8'), col)
        st = np.hypot(x - 0.5, y - 0.5) * 2 < 0.14
        col = np.where(st[..., None], Mt, col)
    else:
        b = np.minimum(np.minimum(x, 1 - x), np.minimum(y, 1 - y))
        col = np.where((b < 0.11)[..., None], Bd, col)
        for e in (0.035, 0.1, 0.12):
            col = np.where((np.abs(b - e) < 0.006)[..., None], Mt, col)
        # gregas na barra
        dente = ((np.sin(x * 2 * math.pi * 24) > 0) ^ (np.sin(y * 2 * math.pi * 24) > 0)) & (b > 0.05) & (b < 0.085)
        col = np.where(dente[..., None], Mt * 0.85 + Bd * 0.15, col)
        cx, cy = x - 0.5, y - 0.5
        rr = np.hypot(cx, cy * 1.35); a = np.arctan2(cy, cx)
        med = (np.abs(np.sin(a * 8)) * 0.07 + 0.17 > rr)
        col = np.where((med & (b > 0.12))[..., None], Mt, col)
        col = np.where((rr < 0.12)[..., None], Bd, col); col = np.where((rr < 0.05)[..., None], Mt, col)
        flor = (np.cos(x * 2 * math.pi * 6) * np.cos(y * 2 * math.pi * 6) > 0.8) & (b > 0.14) & ~med
        col = np.where(flor[..., None], F * 0.5 + Mt * 0.5, col)
        cant = (np.hypot(np.minimum(x, 1 - x) - 0.2, np.minimum(y, 1 - y) - 0.2) < 0.05)
        col = np.where(cant[..., None], Mt, col)
    pelo = pn(n, 0.004, seed) * 0.6 + pn(n, 0.05, seed + 1) * 0.4
    col = col * (0.82 + 0.25 * pelo[..., None])
    save(nome, col)

def janela():
    """vitral de losangos: de dia vidro escuro com reflexo; à noite os vidros acesos"""
    W, H = 256, 512
    y, x = np.mgrid[0:H, 0:W] / np.array([H, W])[:, None, None]
    u = (x * 4 + y * 4) % 1; v = (x * 4 - y * 4) % 1
    chumbo = (np.minimum(np.minimum(u, 1 - u), np.minimum(v, 1 - v)) < 0.045)
    caix = (np.minimum(np.minimum(x, 1 - x) * W, np.minimum(y, 1 - y) * H) < 10) | (np.abs(x - 0.5) * W < 6) | (np.abs(y - 0.55) * H < 6)
    pane = np.floor(x * 4 + y * 4) * 7 + np.floor(x * 4 - y * 4) * 3
    t = (np.sin(pane * 12.9898) * 43758.5453) % 1
    dia = hexc('#304a5c') * (0.7 + 0.4 * t[..., None]) + (1 - y[..., None]) * 0.15 * (x[..., None] < 0.55)
    dia = dia + np.clip(np.sin((x - y) * 9), 0, 1)[..., None] * 0.12
    noite = hexc('#ffc86a') * (0.8 + 0.3 * t[..., None]) * (0.85 + 0.2 * (1 - y[..., None]))
    for img, nome in ((dia, 'janela.jpg'), (noite, 'janela_noite.jpg')):
        out = np.where(chumbo[..., None], hexc('#2a2622'), img)
        out = np.where(caix[..., None], hexc('#4a2e1a') * (0.9 + 0.2 * pn(H, 0.05, 201, m=W))[..., None], out)
        save(nome, out)

def casca():
    n = 512; y, x = np.mgrid[0:n, 0:n] / n
    sulco = pn(n, 0.05, 211, m=n); sulco = ndimage.uniform_filter1d(sulco, 30, axis=0, mode='wrap')
    s = np.abs(np.sin((x * 14 + sulco * 3) * math.pi))
    col = hexc('#5a4632')[None, None] * (0.6 + 0.5 * s[..., None]) * (0.85 + 0.2 * pn(n, 0.02, 212)[..., None])
    col, _ = assa(col, s * 3, 1.0, luz=0.3)
    save('casca.jpg', col)

def folhagem(nome, cor_a, cor_b, seed, n=512, folhas=260, flores=0):
    """cartão de folhas com transparência (arbustos, hera, copas)"""
    r = np.random.default_rng(seed)
    img = Image.new('RGBA', (n, n), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    A, Bc = hexc(cor_a), hexc(cor_b)
    for _ in range(folhas):
        cx, cy = r.random(2) * n; L = r.uniform(18, 40); a = r.uniform(0, 2 * math.pi); w = L * 0.45
        c = A + (Bc - A) * r.random(); c = c * r.uniform(0.7, 1.15)
        cc = tuple(int(v * 255) for v in np.clip(c, 0, 1)) + (255,)
        p = [(cx, cy), (cx + math.cos(a + 0.5) * w, cy + math.sin(a + 0.5) * w), (cx + math.cos(a) * L, cy + math.sin(a) * L), (cx + math.cos(a - 0.5) * w, cy + math.sin(a - 0.5) * w)]
        d.polygon(p, fill=cc)
        d.line([(cx, cy), (cx + math.cos(a) * L * 0.9, cy + math.sin(a) * L * 0.9)], fill=tuple(int(v * 180) for v in np.clip(c, 0, 1)) + (255,), width=1)
    for _ in range(flores):
        cx, cy = r.random(2) * n; s = r.uniform(4, 8)
        cor = [(240, 230, 250), (250, 210, 90), (220, 120, 170), (170, 150, 240)][int(r.integers(4))]
        for k in range(5):
            a = k * 2 * math.pi / 5; d.ellipse([cx + math.cos(a) * s - s * 0.7, cy + math.sin(a) * s - s * 0.7, cx + math.cos(a) * s + s * 0.7, cy + math.sin(a) * s + s * 0.7], fill=cor + (255,))
        d.ellipse([cx - 3, cy - 3, cx + 3, cy + 3], fill=(250, 220, 90, 255))
    img.save(os.path.join(OUT, nome), optimize=True)

def cascata():
    """água que cai: listras verticais (a textura desliza para baixo no jogo); duas camadas com padrões diferentes"""
    for nome, seed, nst, opa in (('cascata.png', 71, 140, 0.55), ('cascata2.png', 72, 80, 0.35)):
        W, H = 256, 512
        y, x = np.mgrid[0:H, 0:W] / np.array([H, W])[:, None, None]
        r = np.random.default_rng(seed)
        st = np.zeros((H, W))
        for _ in range(nst):
            cx = r.random(); w = r.uniform(0.004, 0.025); a = r.uniform(0.3, 1)
            fase = r.random(); per = int(r.integers(1, 4))
            st += a * np.exp(-((((x - cx) + 0.5) % 1 - 0.5) / w) ** 2) * (0.55 + 0.45 * np.sin((y * per + fase) * 2 * math.pi))
        st = st / st.max()
        bolhas = np.clip((pn(H, 0.03, seed + 5, m=W) - 0.55) * 3, 0, 1)
        k = np.clip(st * 1.2 + bolhas * 0.6, 0, 1)
        col = np.stack([0.78 + 0.22 * k, 0.88 + 0.12 * k, 0.95 + 0.05 * k, opa + (1 - opa) * k], -1)
        save(nome, col)
    n = 512; y, x = np.mgrid[0:n, 0:n] / n
    f = np.clip(pn(n, 0.08, 73) * 1.3 - 0.25, 0, 1) * 0.6 + np.clip(pn(n, 0.02, 74) * 1.4 - 0.3, 0, 1) * 0.4
    rr = np.hypot(x - 0.5, y - 0.5) * 2
    a = f * np.clip(1.15 - rr, 0, 1)
    save('espuma.png', np.stack([np.ones_like(f), np.ones_like(f) * 0.98, np.ones_like(f) * 0.96, np.clip(a * 1.4, 0, 1)], -1))

def caldo():
    n = 256; y, x = np.mgrid[0:n, 0:n] / n
    rr = np.hypot(x - 0.5, y - 0.5); a = np.arctan2(y - 0.5, x - 0.5)
    sw = np.sin(a * 3 + rr * 18) * 0.5 + 0.5
    b = np.clip((pn(n, 0.06, 221) - 0.6) * 4, 0, 1)
    col = hexc('#3cd36a')[None, None] * (0.7 + 0.4 * sw[..., None]) + b[..., None] * 0.35
    save('caldo.jpg', col)

def main():
    for src, dst in [('estrada/tex/terra.jpg', 'terra.jpg'), ('estrada/tex/grama.jpg', 'grama.jpg'), ('estrada/tex/calcada.jpg', 'calcada.jpg'),
                     ('estrada/tex/rocha.jpg', 'rocha.jpg'), ('estrada/tex/agua_n.png', 'agua_n.png'), ('covil/tex/musgo.jpg', 'musgo.jpg'),
                     ('estrada/tex/capim.png', 'capim.png'), ('estrada/tex/flores.png', 'flores.png'), ('estrada/tex/folhas_verdes.png', 'folhas_verdes.png')]:
        shutil.copy(os.path.join(ROOT, 'public', 'assets', 'maps', src), os.path.join(OUT, dst))
    pedra(); pedra('pedra_base', base='#8c8578', var=0.12, seed=8, alturas=(0.25, 0.333), larg=(0.3, 0.6))
    reboco()
    madeira('madeira', '#2e1c10', '#6e4a2a', seed=21, forca=5)                 # vigas
    madeira('tabuas', '#5a3820', '#a87444', tabuas=6, seed=22, forca=4)       # piso
    madeira('moveis', '#3a1c0e', '#8a4a26', seed=23, nos=False, forca=3)      # móveis polidos
    lajes(); telha(); cobre(); latao(); ferro(); couro(); saco()
    tecido('tecido_azul.jpg', '#2a3a7a'); tecido('tecido_vermelho.jpg', '#8a2228', seed=102); tecido('tecido_creme.jpg', '#e6d8b8', seed=103)
    estandarte(); tapecaria(); lombadas(); globo(); mapa(); pergaminho(); quadro_lua(); pintura()
    carta(91, 'carta_a.jpg'); carta(92, 'carta_b.jpg')
    tapete('tapete_vermelho.jpg', '#7a1c1c', '#3a1010', '#d0aa52', 81); tapete('tapete_azul.jpg', '#1d2f5a', '#101830', '#d0b46a', 82)
    tapete('tapete_verde.jpg', '#24452a', '#101e12', '#d0aa52', 83); tapete('tapete_estrelas.jpg', '#101c3c', '#0a1228', '#d0b46a', 84, redondo=True)
    janela(); casca()
    folhagem('arbusto.png', '#2e5a26', '#6a9a3a', 231, folhas=420)
    folhagem('hera.png', '#244a20', '#4a7a2a', 232, folhas=200)
    folhagem('flores_canteiro.png', '#2e5a26', '#5a8a32', 233, folhas=300, flores=60)
    folhagem('copa.png', '#2a5222', '#7aa040', 234, folhas=600)
    cascata(); caldo()
    print('texturas:', len(os.listdir(OUT)))

if __name__ == '__main__':
    main()
