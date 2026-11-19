"""Texturas do mapa "Encruzilhada da Floresta", geradas por código (numpy + Pillow).

Chão (emendam nas bordas): grama, terra, serrapilheira, calçada de lajes, rocha.
Cartões com transparência (para as árvores e plantas modeladas no Blender): ramo de pinheiro, folhas de
outono, folhas verde-amareladas, samambaia, florzinhas, tufo de capim. Casca e madeira para troncos e placa.
Saída: public/assets/maps/estrada/tex/

Rodar: python3 fontes/mapas/estrada_texturas.py
"""
import math, os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, os.path.dirname(__file__))
from covil_texturas import fbm, voronoi, lerp, sstep, col, mix, normal_map, stamp_wrap  # mesmas ferramentas do covil

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
OUT = os.path.join(ROOT, 'public', 'assets', 'maps', 'estrada', 'tex')
os.makedirs(OUT, exist_ok=True)
N = 1024

def save(name, arr, q=88):
    a = np.clip(arr, 0, 1)
    img = Image.fromarray((a * 255).astype(np.uint8))
    if name.endswith('.png'): img.save(os.path.join(OUT, name), optimize=True)
    else: img.convert('RGB').save(os.path.join(OUT, name), quality=q)

def dots(rng, count, rmin, rmax, n=N):
    """manchas redondas que emendam (seixos, flores, folhas)."""
    pts = rng.random((count, 2)) * n; rs = rng.uniform(rmin, rmax, count); vs = rng.uniform(120, 255, count)
    return np.asarray(stamp_wrap(lambda d, ox, oy: [d.ellipse([x + ox - r, y + oy - r * 0.8, x + ox + r, y + oy + r * 0.8], fill=int(v))
                                                    for (x, y), r, v in zip(pts, rs, vs)], n), float) / 255

def blades(rng, count, lmin, lmax, n=N, width=(1, 2)):
    """traços curtos (capim, agulhas caídas, gravetos)."""
    P = rng.random((count, 2)) * n; A = rng.uniform(-math.pi, math.pi, count); L = rng.uniform(lmin, lmax, count)
    V = rng.uniform(110, 255, count); W = rng.integers(width[0], width[1] + 1, count)
    return np.asarray(stamp_wrap(lambda d, ox, oy: [d.line([(x + ox, y + oy), (x + ox + math.cos(a) * l, y + oy + math.sin(a) * l)], fill=int(v), width=int(w))
                                                    for (x, y), a, l, v, w in zip(P, A, L, V, W)], n), float) / 255

# ================================================================ chão
def grama():
    """grama da clareira: verde-oliva com manchas amareladas de sol, tufos escuros, trevos e pedrinhas."""
    rng = np.random.default_rng(1)
    big = fbm(N, 3, 101); mid = fbm(N, 10, 102, 4); fine = fbm(N, 70, 103, 3)
    c = mix(col('#3f5320'), col('#7c8a32'), sstep(0.25, 0.8, big * 0.6 + mid * 0.4))
    c = lerp(c, col('#9a9a45')[None, None, :], (sstep(0.62, 0.85, mid) * 0.45)[..., None])     # manchas secas
    bl = blades(rng, 26000, 4, 11)
    c = lerp(c, mix(col('#2c3f16'), col('#a8b052'), fine), (bl * 0.55)[..., None])
    clover = dots(rng, 500, 2.5, 5) * sstep(0.55, 0.7, fbm(N, 8, 104))
    c = lerp(c, col('#4f7a2a')[None, None, :], (clover * 0.7)[..., None])
    peb = dots(rng, 260, 1.5, 4)
    soil = sstep(0.68, 0.82, fbm(N, 6, 105))
    c = lerp(c, mix(col('#5a4127'), col('#7d5a36'), fine), (soil * 0.5)[..., None])
    c = lerp(c, mix(col('#7e7262'), col('#b7ab98'), fine), (peb * 0.85)[..., None])
    c *= (0.86 + 0.28 * fine)[..., None]
    save('grama.jpg', c)

def terra():
    """terra batida da beira da estrada: marrom-alaranjada, cascalho, seixos e marcas de roda."""
    rng = np.random.default_rng(2)
    a = fbm(N, 5, 201); b = fbm(N, 30, 202, 4); f = fbm(N, 90, 203, 2)
    c = mix(col('#5b3a22'), col('#9a6a3e'), a * 0.6 + b * 0.4) * (0.8 + 0.3 * f[..., None])
    grav = dots(rng, 2600, 0.8, 2.6)
    peb = dots(rng, 380, 2.5, 7)
    c = lerp(c, mix(col('#6e6458'), col('#bfb3a0'), b), (grav * 0.6)[..., None])
    sh = np.roll(np.roll(peb, 2, 0), 2, 1)
    c *= (1 - 0.35 * sh)[..., None]
    c = lerp(c, mix(col('#8a7f70'), col('#c9bfae'), f), (peb * 0.9)[..., None])
    wet = sstep(0.66, 0.8, fbm(N, 7, 204))
    c = lerp(c, col('#3b2616')[None, None, :], (wet * 0.4)[..., None])
    save('terra.jpg', c)
    save('terra_n.png', normal_map(a * 0.3 + grav * 0.3 + peb * 0.6, 3.0))

def folhas():
    """chão da mata sob os pinheiros: capim escuro, agulhas caídas, folhas secas e musgo."""
    rng = np.random.default_rng(3)
    a = fbm(N, 4, 301); b = fbm(N, 20, 302, 4); f = fbm(N, 80, 303, 2)
    c = mix(col('#2a3317'), col('#556328'), a * 0.5 + b * 0.5)
    nd = blades(rng, 16000, 5, 14)
    c = lerp(c, mix(col('#5e3c1f'), col('#9a6533'), f), (nd * 0.55 * sstep(0.3, 0.7, b))[..., None])
    lv = dots(rng, 900, 2, 6)
    c = lerp(c, mix(col('#7a4a1e'), col('#b8742c'), f), (lv * 0.6)[..., None])
    moss = sstep(0.6, 0.78, fbm(N, 6, 304))
    c = lerp(c, col('#45612a')[None, None, :], (moss * 0.5)[..., None])
    c *= (0.82 + 0.3 * f)[..., None]
    save('folhas.jpg', c)

def calcada():
    """estrada antiga: lajes de pedra irregulares cinza-azuladas e escuras, juntas finas de terra, lajes faltando,
    lama nas rodeiras e cascalho. Pensada para ler bem de cima, como na referência."""
    rng = np.random.default_rng(4)
    f1, f2, ids, k = voronoi(N, 110, 401, 1.0)
    gap = f2 - f1
    edge = sstep(0.002, 0.012, gap)
    bevel = sstep(0.002, 0.05, gap)
    tone = rng.random(k)[ids]; tilt = rng.random(k)[ids]
    g = fbm(N, 24, 402, 5); f = fbm(N, 90, 403, 2); spots = fbm(N, 60, 406, 3)
    stone = mix(col('#3c434b'), col('#7d848b'), tone * 0.45 + g * 0.55)
    stone = lerp(stone, mix(col('#5e5447'), col('#8d7d68'), g), (sstep(0.6, 0.95, tone) * 0.55)[..., None])
    stone = lerp(stone, col('#2b2f33')[None, None, :], (sstep(0.55, 0.8, spots) * 0.35)[..., None])
    stone *= (0.6 + 0.5 * bevel * (0.85 + 0.3 * tilt))[..., None]
    soil = mix(col('#3a2414'), col('#7a4d29'), f * 0.6 + g * 0.4)
    c = lerp(soil, stone, edge[..., None])
    missing = (rng.random(k) < 0.07)[ids]
    c = np.where(missing[..., None], soil * (0.85 + 0.3 * g[..., None]), c)
    mud = sstep(0.58, 0.8, fbm(N, 5, 405) * 0.7 + g * 0.3)
    c = lerp(c, mix(col('#4a2e17'), col('#6e4826'), f), (mud * 0.6)[..., None])
    grav = dots(rng, 1600, 0.8, 2.2)
    c = lerp(c, col('#a59a88')[None, None, :], (grav * 0.55 * (1 - edge * 0.8))[..., None])
    c *= (0.9 + 0.2 * f)[..., None]
    h = np.where(missing, 0.1, bevel * (0.7 + 0.3 * tilt)) + g * 0.1 - mud * 0.1
    save('calcada.jpg', c)
    save('calcada_n.png', normal_map(h, 6.0))

def rocha():
    """granito cinza com líquen e musgo, para pedras grandes e barrancos."""
    g = fbm(N, 8, 501, 6); f = fbm(N, 60, 502, 3)
    f1, f2, _, _ = voronoi(N, 50, 503, 1.0)
    crack = 1 - sstep(0.0, 0.007, f2 - f1)
    c = mix(col('#3f4144'), col('#8a8a84'), g * 0.7 + f * 0.3)
    spk = sstep(0.75, 0.9, fbm(N, 200, 504, 1))
    c = lerp(c, col('#2c2d2f')[None, None, :], (spk * 0.4)[..., None])
    c = lerp(c, col('#1e1f1f')[None, None, :], (crack * sstep(0.4, 0.7, fbm(N, 6, 507)) * 0.6)[..., None])
    lich = sstep(0.6, 0.75, fbm(N, 10, 505, 4))
    c = lerp(c, col('#a8a77a')[None, None, :], (lich * 0.35)[..., None])
    moss = sstep(0.66, 0.8, fbm(N, 5, 506))
    c = lerp(c, col('#4c5f25')[None, None, :], (moss * 0.55)[..., None])
    save('rocha.jpg', c)
    save('rocha_n.png', normal_map(g * 0.5 + f * 0.3 - crack * 0.7, 5.0))

def casca(name='casca.jpg', dark='#2a2019', light='#5e4a3b', seed=601):
    """casca de pinheiro: placas verticais com fendas fundas (vertical = eixo v)."""
    n = 512
    yy, xx = np.mgrid[0:n, 0:n] / n
    w = fbm(n, 6, seed, 4)
    ridges = 0.5 + 0.5 * np.sin((xx * 14 + w * 1.4) * 2 * math.pi)
    plates = fbm(n, 18, seed + 1, 4)
    fiss = sstep(0.25, 0.05, ridges * 0.7 + plates * 0.3 - 0.15)
    c = mix(col(dark), col(light), ridges * 0.5 + plates * 0.5)
    c = lerp(c, col('#120d0a')[None, None, :], (fiss * 0.8)[..., None])
    Image.fromarray((np.clip(c, 0, 1) * 255).astype(np.uint8)).save(os.path.join(OUT, name), quality=88)

def madeira():
    """tábuas velhas da placa: veios, nós e desgaste acinzentado."""
    n = 512
    yy, xx = np.mgrid[0:n, 0:n] / n
    w = fbm(n, 5, 701, 4)
    grain = 0.5 + 0.5 * np.sin((yy * 40 + w * 3) * 2 * math.pi)
    c = mix(col('#4f3824'), col('#9a7550'), grain * 0.4 + fbm(n, 30, 702, 3) * 0.6)
    c = lerp(c, col('#8b8577')[None, None, :], (sstep(0.5, 0.8, fbm(n, 6, 703)) * 0.45)[..., None])
    Image.fromarray((np.clip(c, 0, 1) * 255).astype(np.uint8)).save(os.path.join(OUT, 'madeira.jpg'), quality=88)

# ================================================================ cartões transparentes (RGBA)
def card(n=512):
    img = Image.new('RGBA', (n, n), (0, 0, 0, 0)); return img, ImageDraw.Draw(img)

def shade(hexc, k, rng=None, var=0.12):
    c = col(hexc) * k
    if rng is not None: c = c * (1 + rng.uniform(-var, var))
    return tuple(int(v) for v in np.clip(c * 255, 0, 255)) + (255,)

def ramo_pinho():
    """ramo de pinheiro (abeto) visto de cima: haste no meio, de baixo para cima, raminhos laterais cheios de
    agulhas, formando um leque denso que afina na ponta. A base do ramo fica na borda de baixo (v=0)."""
    rng = np.random.default_rng(801); n = 512
    img, d = card(n)
    def twig(x0, y0, ang, L, width, nl, tip):
        x1, y1 = x0 + math.cos(ang) * L, y0 + math.sin(ang) * L
        steps = max(4, int(L / 2.0))
        for s in range(steps):
            t = s / steps; px, py = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
            for side in (-1, 1):
                a = ang + side * rng.uniform(0.6, 1.0)
                l = nl * (1 - 0.5 * t) * rng.uniform(0.8, 1.2)
                k = rng.uniform(0.55, 1.05) * (0.8 + 0.4 * t) * tip
                hexc = '#24473a' if rng.random() < 0.55 else ('#2f5a43' if rng.random() < 0.7 else '#4d7c4a')
                d.line([(px, py), (px + math.cos(a) * l, py + math.sin(a) * l)], fill=shade(hexc, k, rng, 0.08), width=2)
        d.line([(x0, y0), (x1, y1)], fill=shade('#3b2b1c', 0.9, rng), width=max(1, int(width)))
    x0, y0, L = n / 2, n - 2, n * 0.97
    # raminhos laterais, dos maiores (base) aos menores (ponta)
    for i in range(26):
        t = 0.06 + i / 26 * 0.9; py = y0 - L * t
        span = math.sin(math.pi * min(1, 0.25 + t * 0.95)) * (1 - t * 0.55)
        for side in (-1, 1):
            ang = -math.pi / 2 + side * rng.uniform(0.75, 1.05)
            twig(x0 + rng.normal(0, 1), py, ang, n * 0.42 * span + 10, 2, 13 * (1 - 0.3 * t), 0.9 + 0.25 * t)
    twig(x0, y0, -math.pi / 2, L, 4, 15, 1.0)
    img.save(os.path.join(OUT, 'ramo_pinho.png'), optimize=True)

def folhagem(name, palette, seed, count=2600, rmin=7, rmax=15, n=512):
    """raminho de folhas para copas e arbustos: galhinhos saindo do meio, cada um com um cacho de folhas ovais
    (com nervura). A borda fica recortada e com buracos, para a copa não parecer feita de discos."""
    rng = np.random.default_rng(seed)
    img, d = card(n)
    twigs = []
    for _ in range(9):
        a = rng.uniform(0, 2 * math.pi); L = rng.uniform(0.25, 0.44) * n
        x1, y1 = n / 2 + math.cos(a) * L, n / 2 + math.sin(a) * L
        d.line([(n / 2, n / 2), (x1, y1)], fill=shade('#3a2a1c', 1, rng), width=3)
        twigs.append((a, L))
    per = count // len(twigs)
    for a, L in twigs:
        for _ in range(per):
            t = rng.uniform(0.25, 1.0); spread = rng.normal(0, 0.11 * n * t)
            x = n / 2 + math.cos(a) * L * t - math.sin(a) * spread; y = n / 2 + math.sin(a) * L * t + math.cos(a) * spread
            if math.hypot(x - n / 2, y - n / 2) > n * 0.48: continue
            s = rng.uniform(rmin, rmax); ang = a + rng.normal(0, 0.9)
            k = rng.uniform(0.55, 1.15) * (0.75 + 0.35 * t)
            hexc = palette[int(rng.integers(len(palette)))]
            pts = [(x + math.cos(ang) * s * math.cos(q) - math.sin(ang) * s * 0.45 * math.sin(q),
                    y + math.sin(ang) * s * math.cos(q) + math.cos(ang) * s * 0.45 * math.sin(q)) for q in np.linspace(0, 2 * math.pi, 9)]
            d.polygon(pts, fill=shade(hexc, k, rng, 0.1))
            d.line([(x - math.cos(ang) * s * 0.8, y - math.sin(ang) * s * 0.8), (x + math.cos(ang) * s * 0.8, y + math.sin(ang) * s * 0.8)], fill=shade(hexc, k * 0.7), width=1)
    img.save(os.path.join(OUT, name), optimize=True)

def samambaia():
    """folha de samambaia: haste da base (embaixo) até a ponta, folíolos compridos e recortados."""
    rng = np.random.default_rng(901); n = 512
    img, d = card(n)
    x0, y0 = n / 2, n - 4; L = n * 0.95
    for i in range(30):
        t = i / 30; py = y0 - L * (0.1 + t * 0.88); taper = math.sin(math.pi * (0.12 + t * 0.85)) * (1 - t * 0.45)
        for side in (-1, 1):
            l = n * 0.4 * taper; ang = -math.pi / 2 + side * 1.15
            ex, ey = x0 + math.cos(ang) * l, py + math.sin(ang) * l
            w = 9 * taper + 2
            # folíolo: losango comprido com bordas serrilhadas
            pts = [(x0, py)]
            for j in range(1, 9):
                u = j / 9; bx, by = x0 + (ex - x0) * u, py + (ey - py) * u
                ww = w * math.sin(math.pi * min(1, u * 1.1)) * (1.0 if j % 2 else 0.7)
                pts.append((bx - math.sin(ang) * ww, by + math.cos(ang) * ww))
            pts.append((ex, ey))
            for j in range(8, 0, -1):
                u = j / 9; bx, by = x0 + (ex - x0) * u, py + (ey - py) * u
                ww = w * math.sin(math.pi * min(1, u * 1.1)) * (1.0 if j % 2 else 0.7)
                pts.append((bx + math.sin(ang) * ww, by - math.cos(ang) * ww))
            d.polygon(pts, fill=shade('#4e7d2b', rng.uniform(0.7, 1.15) * (0.8 + 0.3 * t), rng, 0.06))
            d.line([(x0, py), (ex, ey)], fill=shade('#2f4d18', 1.0), width=1)
    d.line([(x0, y0), (x0, y0 - L)], fill=shade('#3f5a22', 1), width=3)
    img.save(os.path.join(OUT, 'samambaia.png'), optimize=True)

def flores():
    """touceira baixa: folhas verdes e flores brancas/amarelas pequenas (umbelas), vista de cima."""
    rng = np.random.default_rng(951); n = 512
    img, d = card(n)
    for _ in range(420):
        r = (rng.random() ** 0.7) * n * 0.44; a = rng.uniform(0, 2 * math.pi); x, y = n / 2 + math.cos(a) * r, n / 2 + math.sin(a) * r
        s = rng.uniform(8, 16)
        d.ellipse([x - s, y - s * 0.6, x + s, y + s * 0.6], fill=shade('#4f7a2c', rng.uniform(0.6, 1.1), rng))
    for _ in range(70):
        r = (rng.random() ** 0.8) * n * 0.4; a = rng.uniform(0, 2 * math.pi); x, y = n / 2 + math.cos(a) * r, n / 2 + math.sin(a) * r
        hexc = '#efeee0' if rng.random() < 0.75 else '#e9c94a'
        for _ in range(9):
            ox, oy = rng.normal(0, 5, 2); s = rng.uniform(2, 3.5)
            d.ellipse([x + ox - s, y + oy - s, x + ox + s, y + oy + s], fill=shade(hexc, rng.uniform(0.85, 1.05)))
    img.save(os.path.join(OUT, 'flores.png'), optimize=True)

def capim():
    """tufo de capim visto de lado: lâminas saindo da base (embaixo do cartão)."""
    rng = np.random.default_rng(971); n = 256
    img, d = card(n)
    for _ in range(90):
        x0 = n / 2 + rng.normal(0, 18); h = rng.uniform(0.45, 0.95) * n; lean = rng.normal(0, 0.35)
        pts = [(x0 + lean * h * (t ** 1.6) * 0.6, n - t * h) for t in np.linspace(0, 1, 8)]
        cc = shade('#6f8a35' if rng.random() < 0.6 else '#a3a548', rng.uniform(0.6, 1.1), rng)
        d.line(pts, fill=cc, width=2)
    img.save(os.path.join(OUT, 'capim.png'), optimize=True)

def agua():
    """ondulações finas para as poças (relevo de luz)."""
    f1, f2, _, _ = voronoi(N, 160, 1101, 1.0)
    v = sstep(0.0, 0.02, f2 - f1); g = fbm(N, 8, 1102, 4)
    save('agua_n.png', normal_map(v * 0.5 + g * 0.5, 2.5))

if __name__ == '__main__':
    for f in (grama, terra, folhas, calcada, rocha, madeira, ramo_pinho, samambaia, flores, capim, agua):
        print(f.__name__); f()
    print('casca'); casca(); casca('casca_morta.jpg', '#8b857a', '#d8d2c6', 611)
    print('folhagens')
    folhagem('folhas_outono.png', ['#c2481a', '#d8621f', '#e07a26', '#a8331a', '#e89a3a'], 1201)
    folhagem('folhas_amarelas.png', ['#a7a326', '#c4bb2c', '#8e9a24', '#d6c23c'], 1202, count=2200, rmin=6, rmax=12)
    folhagem('folhas_verdes.png', ['#3f6b25', '#4f7d2d', '#5f8a31', '#36592a'], 1203, count=2200, rmin=6, rmax=12)
