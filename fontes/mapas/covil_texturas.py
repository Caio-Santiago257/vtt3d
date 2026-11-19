"""Texturas do mapa "Covil do Dragão Negro", geradas por código (numpy + Pillow).

Todas emendam nas bordas (repetem sem costura), exceto o painel de ossuário e o fundo panorâmico.
Saída: public/assets/maps/covil/tex/*.jpg (cor) e *_n.png (relevo para luz, quando faz diferença).

Rodar: python3 fontes/mapas/covil_texturas.py
"""
import math, os
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy import ndimage
from scipy.spatial import cKDTree

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
OUT = os.path.join(ROOT, 'public', 'assets', 'maps', 'covil', 'tex')
os.makedirs(OUT, exist_ok=True)
N = 1024

# ---------------------------------------------------------------- ruído que emenda
def pnoise(n, f, seed):
    """ruído de valor periódico: grade f x f ampliada com interpolação cúbica que dá a volta nas bordas."""
    r = np.random.default_rng(seed).random((f, f))
    return ndimage.zoom(r, n / f, order=3, mode='grid-wrap')[:n, :n]

def fbm(n, f, seed, oct=5, gain=0.5):
    out = np.zeros((n, n)); amp = 1.0; tot = 0
    for o in range(oct):
        ff = f * 2 ** o
        if ff > n // 2: break
        out += amp * pnoise(n, ff, seed + o * 31); tot += amp; amp *= gain
    out /= tot
    return (out - out.min()) / (out.max() - out.min() + 1e-9)

def voronoi(n, k, seed, jitter=1.0):
    """F1, F2 e índice da célula, periódicos. Pontos numa grade com tremido (pedras de tamanho parecido)."""
    rng = np.random.default_rng(seed)
    g = int(math.sqrt(k))
    gx, gy = np.meshgrid(np.arange(g), np.arange(g))
    pts = np.stack([(gx.ravel() + 0.5 + (rng.random(g * g) - 0.5) * jitter) / g,
                    (gy.ravel() + 0.5 + (rng.random(g * g) - 0.5) * jitter) / g], 1) % 1.0
    tiles = np.concatenate([pts + [dx, dy] for dx in (-1, 0, 1) for dy in (-1, 0, 1)])
    ids = np.tile(np.arange(len(pts)), 9)
    yy, xx = np.mgrid[0:n, 0:n] / n
    d, i = cKDTree(tiles).query(np.stack([xx.ravel(), yy.ravel()], 1), k=2)
    return d[:, 0].reshape(n, n), d[:, 1].reshape(n, n), ids[i[:, 0]].reshape(n, n), len(pts)

def lerp(a, b, t): return a + (b - a) * t
def sstep(a, b, x): t = np.clip((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t)
def col(h): h = h.lstrip('#'); return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], float) / 255
def mix(c1, c2, t): return c1[None, None, :] * (1 - t[..., None]) + c2[None, None, :] * t[..., None]

def normal_map(h, strength=4.0):
    gx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) * strength
    gy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) * strength
    nz = np.ones_like(h); l = np.sqrt(gx * gx + gy * gy + nz * nz)
    return np.stack([(-gx / l + 1) / 2, (gy / l + 1) / 2, (nz / l + 1) / 2], -1)

def save(name, rgb, q=90):
    img = Image.fromarray((np.clip(rgb, 0, 1) * 255).astype(np.uint8))
    if name.endswith('.png'): img.save(os.path.join(OUT, name), optimize=True)
    else: img.save(os.path.join(OUT, name), quality=q)
    print('  ', name, img.size)

def stamp_wrap(draw_fn, n=N, mode='L', bg=0):
    """desenha com Pillow repetindo nas 9 posições, para o desenho atravessar as bordas sem costura."""
    img = Image.new(mode, (n, n), bg); d = ImageDraw.Draw(img)
    for ox in (-n, 0, n):
        for oy in (-n, 0, n):
            draw_fn(d, ox, oy)
    return img

# ---------------------------------------------------------------- formas: ossos e crânios
def bone_shapes(rng, count, smin, smax, n=N):
    out = []
    for _ in range(count):
        out.append(dict(x=rng.random() * n, y=rng.random() * n, a=rng.random() * math.pi, L=rng.uniform(smin, smax),
                        kind=rng.choice(['osso', 'osso', 'osso', 'cranio', 'costela'], p=[0.35, 0.25, 0.15, 0.15, 0.10])))
    return out

def draw_bones(d, ox, oy, shapes, fill=255):
    for s in shapes:
        x, y, a, L = s['x'] + ox, s['y'] + oy, s['a'], s['L']
        ca, sa = math.cos(a), math.sin(a)
        if s['kind'] == 'osso':
            w = L * 0.12
            x1, y1, x2, y2 = x - ca * L / 2, y - sa * L / 2, x + ca * L / 2, y + sa * L / 2
            d.line([(x1, y1), (x2, y2)], fill=fill, width=max(1, int(w)))
            for ex, ey in ((x1, y1), (x2, y2)):
                for k in (-1, 1):
                    d.ellipse([ex - sa * w * 0.6 * k - w * 0.7, ey + ca * w * 0.6 * k - w * 0.7, ex - sa * w * 0.6 * k + w * 0.7, ey + ca * w * 0.6 * k + w * 0.7], fill=fill)
        elif s['kind'] == 'cranio':
            r = L * 0.32
            d.ellipse([x - r, y - r, x + r, y + r * 0.9], fill=fill)
            d.rectangle([x - r * 0.55, y + r * 0.5, x + r * 0.55, y + r * 1.15], fill=fill)
            for k in (-1, 1):  # órbitas
                d.ellipse([x + k * r * 0.42 - r * 0.24, y - r * 0.05, x + k * r * 0.42 + r * 0.24, y + r * 0.42], fill=int(fill * 0.25))
            d.polygon([(x, y + r * 0.42), (x - r * 0.1, y + r * 0.62), (x + r * 0.1, y + r * 0.62)], fill=int(fill * 0.3))
        else:  # costela: arco
            r = L * 0.5
            d.arc([x - r, y - r * 0.6, x + r, y + r * 0.6], start=math.degrees(a) % 360, end=(math.degrees(a) + 150) % 360, fill=fill, width=max(1, int(L * 0.07)))

# ---------------------------------------------------------------- texturas
def musgo():
    """chão do pântano: musgo verde-escuro em tufos, folhinhas e terra aparecendo."""
    base = fbm(N, 4, 11); clump = fbm(N, 16, 12, 4); fine = fbm(N, 64, 13, 3)
    dirt = sstep(0.62, 0.78, fbm(N, 6, 14))
    c = mix(col('#26331a'), col('#55692c'), clump ** 1.3)
    c = c * (0.75 + 0.5 * base[..., None])
    c = lerp(c, mix(col('#3a3020'), col('#54452c'), fine), (dirt * 0.65)[..., None])
    rng = np.random.default_rng(5)
    leaves = stamp_wrap(lambda d, ox, oy: [d.ellipse([x + ox, y + oy, x + ox + rng.uniform(3, 9), y + oy + rng.uniform(2, 5)], fill=int(rng.uniform(120, 255)))
                                          for x, y in rng.random((900, 2)) * N])
    lv = np.asarray(leaves.filter(ImageFilter.GaussianBlur(0.6)), float) / 255
    c = lerp(c, mix(col('#6f8a33'), col('#a3b04a'), fine), (lv * 0.55)[..., None])
    c *= (0.85 + 0.3 * fine)[..., None]
    h = clump * 0.6 + fine * 0.3 + lv * 0.2
    save('musgo.jpg', c); save('musgo_n.png', normal_map(h, 3.0))

def lama():
    """lama do brejo: marrom-oliva, poças escuras e brilhantes, gravetos."""
    a = fbm(N, 5, 21); b = fbm(N, 24, 22, 4); wet = sstep(0.55, 0.7, fbm(N, 7, 23))
    c = mix(col('#2b2416'), col('#4e4528'), a) * (0.8 + 0.35 * b[..., None])
    c = lerp(c, col('#1b1d12')[None, None, :], (wet * 0.6)[..., None])
    rng = np.random.default_rng(6)
    sticks = stamp_wrap(lambda d, ox, oy: [d.line([(x + ox, y + oy), (x + ox + math.cos(t) * l, y + oy + math.sin(t) * l)], fill=int(rng.uniform(140, 230)), width=int(rng.uniform(1, 3)))
                                           for (x, y), t, l in zip(rng.random((140, 2)) * N, rng.random(140) * 6.3, rng.uniform(8, 40, 140))])
    st = np.asarray(sticks, float) / 255
    c = lerp(c, col('#5d4a2e')[None, None, :], (st * 0.8)[..., None])
    h = a * 0.4 + b * 0.4 - wet * 0.3 + st * 0.3
    save('lama.jpg', c); save('lama_n.png', normal_map(h, 3.0))

def caverna():
    """chão do covil: cascalho escuro e pedras, coberto de ossos de muitas criaturas."""
    f1, f2, ids, k = voronoi(N, 400, 31, 0.9)
    edge = sstep(0.0, 0.012, f2 - f1)
    tone = np.random.default_rng(32).random(k)[ids]
    g = fbm(N, 32, 33, 4)
    c = mix(col('#2e2a26'), col('#5a5249'), tone * 0.6 + g * 0.4) * (0.55 + 0.45 * edge)[..., None]
    c = lerp(c, col('#2c3320')[None, None, :], (sstep(0.6, 0.8, fbm(N, 5, 34)) * 0.5)[..., None])  # musgo úmido
    rng = np.random.default_rng(35)
    shapes = bone_shapes(rng, 340, 18, 70)
    bones = np.asarray(stamp_wrap(lambda d, ox, oy: draw_bones(d, ox, oy, shapes)), float) / 255
    shadow = np.asarray(Image.fromarray((bones * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(3)), float) / 255
    shadow = np.roll(np.roll(shadow, 3, 0), 3, 1)
    c *= (1 - 0.45 * shadow)[..., None]
    bonec = mix(col('#a99d84'), col('#e0d6bd'), g)
    c = lerp(c, bonec, (bones * 0.95)[..., None])
    h = edge * 0.5 + tone * 0.2 + bones * 0.8
    save('caverna.jpg', c); save('caverna_n.png', normal_map(h, 4.0))

def piso():
    """piso do laboratório: lajes grandes e irregulares, rachadas, com limo nas juntas e manchas."""
    rng = np.random.default_rng(41)
    hmap = Image.new('L', (N, N), 0); d = ImageDraw.Draw(hmap)
    tone = Image.new('L', (N, N), 0); dt = ImageDraw.Draw(tone)
    rows = [0]
    while rows[-1] < N: rows.append(rows[-1] + int(rng.choice([128, 128, 192, 256])))
    rows[-1] = N
    for r in range(len(rows) - 1):
        y0, y1 = rows[r], rows[r + 1]; x = int(rng.integers(0, 200))
        start = x
        while x < start + N:
            w = int(rng.choice([128, 192, 256, 256, 320]))
            x2 = min(x + w, start + N)
            for ox in (-N, 0):
                bx0, bx1 = x + ox, x2 + ox
                d.rectangle([bx0 + 5, y0 + 5, bx1 - 5, y1 - 5], fill=255)
                dt.rectangle([bx0, y0, bx1, y1], fill=int(rng.uniform(80, 230)))
            x = x2
    hm = np.asarray(hmap.filter(ImageFilter.GaussianBlur(2.5)), float) / 255
    tn = np.asarray(tone, float) / 255
    g = fbm(N, 16, 42, 5)
    # rachaduras: veios do voronoi
    f1, f2, _, _ = voronoi(N, 36, 43, 1.0)
    crack = (1 - sstep(0.0, 0.004, f2 - f1)) * sstep(0.45, 0.6, fbm(N, 8, 44))
    stone = mix(col('#5f5a4e'), col('#8e8670'), tn * 0.5 + g * 0.5)
    c = stone * (0.35 + 0.65 * hm)[..., None]
    c = lerp(c, col('#141711')[None, None, :], (crack * 0.85)[..., None])
    algae = (1 - hm) * 0.9 + sstep(0.62, 0.8, fbm(N, 6, 45)) * 0.5
    c = lerp(c, col('#3d5a23')[None, None, :], (np.clip(algae, 0, 1) * 0.55)[..., None])
    stain = sstep(0.55, 0.85, fbm(N, 4, 46))
    c *= (1 - 0.35 * stain)[..., None]
    h = hm * 0.8 + g * 0.15 - crack * 0.5
    save('piso.jpg', c); save('piso_n.png', normal_map(h, 5.0))

def rocha():
    """paredão de rocha: camadas horizontais, fendas e musgo escorrendo (vista lateral, para encostas)."""
    yy = np.mgrid[0:N, 0:N][0] / N
    warp = fbm(N, 4, 51)
    strata = 0.5 + 0.5 * np.sin((yy * 9 + warp * 1.6) * 2 * math.pi)
    g = fbm(N, 24, 52, 5)
    f1, f2, _, _ = voronoi(N, 60, 53, 1.0)
    crack = 1 - sstep(0.0, 0.006, f2 - f1)
    c = mix(col('#3a3833'), col('#6d685d'), strata * 0.45 + g * 0.55)
    c = lerp(c, col('#15140f')[None, None, :], (crack * 0.7)[..., None])
    moss = sstep(0.58, 0.75, fbm(N, 6, 54) * 0.7 + (1 - g) * 0.3)
    c = lerp(c, col('#3e4f22')[None, None, :], (moss * 0.6)[..., None])
    h = strata * 0.3 + g * 0.5 - crack * 0.6
    save('rocha.jpg', c); save('rocha_n.png', normal_map(h, 5.0))

def tijolo():
    """parede do laboratório: blocos de pedra assentados, juntas escuras, manchas de umidade."""
    rng = np.random.default_rng(61)
    hmap = Image.new('L', (N, N), 0); d = ImageDraw.Draw(hmap)
    tone = Image.new('L', (N, N), 0); dt = ImageDraw.Draw(tone)
    bh = 64
    for r in range(N // bh):
        y0 = r * bh; x = 0 if r % 2 == 0 else -64
        while x < N:
            w = int(rng.choice([128, 128, 160, 96]))
            if x + w > N - 32 and x + w < N + 32: w = N - x
            for ox in (-N, 0, N):
                d.rectangle([x + ox + 3, y0 + 3, x + w + ox - 3, y0 + bh - 3], fill=255)
                dt.rectangle([x + ox, y0, x + w + ox, y0 + bh], fill=int(rng.uniform(70, 230)))
            x += w
    hm = np.asarray(hmap.filter(ImageFilter.GaussianBlur(2)), float) / 255
    tn = np.asarray(tone, float) / 255
    g = fbm(N, 32, 62, 5)
    chip = sstep(0.68, 0.8, fbm(N, 24, 63))
    c = mix(col('#5b5546'), col('#9a917a'), tn * 0.45 + g * 0.55) * (0.3 + 0.7 * hm)[..., None]
    c *= (1 - 0.3 * chip)[..., None]
    damp = sstep(0.5, 0.8, fbm(N, 5, 64))
    c = lerp(c, col('#2f3a1c')[None, None, :], (damp * 0.45)[..., None])
    h = hm * 0.8 + g * 0.2 - chip * 0.25
    save('tijolo.jpg', c); save('tijolo_n.png', normal_map(h, 5.0))

def ossuario():
    """painel de ossuário (como os nichos de crânios das ruínas): moldura, fileiras de crânios e ossos cruzados."""
    W, H = 512, 768
    hmap = Image.new('L', (W, H), 40); d = ImageDraw.Draw(hmap)
    d.rectangle([0, 0, W, H], fill=150); d.rectangle([28, 28, W - 28, H - 28], fill=30)   # moldura funda
    d.rectangle([38, 38, W - 38, H - 38], fill=60)
    rng = np.random.default_rng(71)
    # borda de crânios
    def skull(x, y, r, v=235):
        d.ellipse([x - r, y - r, x + r, y + r * 0.9], fill=v)
        d.rectangle([x - r * 0.55, y + r * 0.5, x + r * 0.55, y + r * 1.12], fill=v - 20)
        for k in (-1, 1): d.ellipse([x + k * r * 0.42 - r * 0.25, y - r * 0.02, x + k * r * 0.42 + r * 0.25, y + r * 0.45], fill=25)
        d.polygon([(x, y + r * 0.45), (x - r * 0.12, y + r * 0.66), (x + r * 0.12, y + r * 0.66)], fill=35)
        for t in range(-2, 3): d.line([(x + t * r * 0.2, y + r * 0.85), (x + t * r * 0.2, y + r * 1.1)], fill=60, width=2)
    for x in range(70, W - 40, 62): skull(x, 70, 24); skull(x, H - 92, 24)
    for y in range(140, H - 120, 62): skull(66, y, 22); skull(W - 66, y, 22)
    # miolo: crânios pequenos amontoados e ossos cruzados
    for y in range(135, H - 130, 30):
        for x in range(115, W - 105, 30):
            skull(x + rng.uniform(-4, 4), y + rng.uniform(-3, 3), rng.uniform(11, 14), int(rng.uniform(180, 225)))
    for k in range(5):
        y = 180 + k * 105
        d.line([(110, y - 30), (W - 110, y + 30)], fill=210, width=9); d.line([(110, y + 30), (W - 110, y - 30)], fill=210, width=9)
    hm = np.asarray(hmap.filter(ImageFilter.GaussianBlur(1.6)), float) / 255
    g = fbm(512, 16, 72, 4)
    g = np.asarray(Image.fromarray((g * 255).astype(np.uint8)).resize((W, H)), float) / 255
    c = mix(col('#2a2720'), col('#c8bc9c'), np.clip(hm * 1.05, 0, 1)) * (0.8 + 0.3 * g[..., None])
    c = lerp(c, col('#33421f')[None, None, :], (sstep(0.6, 0.8, g) * 0.35)[..., None])
    save('ossuario.jpg', c); save('ossuario_n.png', normal_map(hm, 6.0))

def madeira():
    """tábuas velhas e úmidas (mesas, estantes, gaiolas)."""
    yy, xx = np.mgrid[0:N, 0:N] / N
    warp = fbm(N, 8, 81)
    grain = 0.5 + 0.5 * np.sin((xx * 60 + warp * 6) * 2 * math.pi * 0.25)
    planks = (np.floor(yy * 8) % 2)
    seam = 1 - sstep(0.0, 0.01, np.abs((yy * 8) % 1 - 0.0)) * 0.0 - (np.abs(((yy * 8) % 1) - 0.5) > 0.47) * 0.6
    c = mix(col('#3b2a1a'), col('#6e5132'), grain * 0.6 + fbm(N, 16, 82) * 0.4) * (0.85 + planks * 0.1)[..., None] * seam[..., None]
    c = lerp(c, col('#2c3a1c')[None, None, :], (sstep(0.6, 0.85, fbm(N, 5, 83)) * 0.4)[..., None])
    save('madeira.jpg', c)

def metal():
    """bronze/cobre oxidado: base marrom-alaranjada com zinabre verde-azulado."""
    g = fbm(N, 16, 91, 5); p = sstep(0.5, 0.75, fbm(N, 6, 92))
    c = mix(col('#4a3220'), col('#9a6a3a'), g)
    c = lerp(c, col('#3f8f7a')[None, None, :], (p * 0.75)[..., None])
    save('metal.jpg', c)

def ouro():
    """moedas de ouro amontoadas (tesouro do dragão)."""
    rng = np.random.default_rng(101)
    img = Image.new('RGB', (N, N), (60, 40, 10)); d = ImageDraw.Draw(img)
    for _ in range(4200):
        x, y, r = rng.random() * N, rng.random() * N, rng.uniform(9, 17)
        t = rng.uniform(0.6, 1.0)
        for ox in (-N, 0, N):
            for oy in (-N, 0, N):
                d.ellipse([x + ox - r, y + oy - r * 0.8, x + ox + r, y + oy + r * 0.8], fill=(int(255 * t), int(196 * t), int(70 * t)), outline=(int(150 * t), int(100 * t), 20))
    c = np.asarray(img, float) / 255
    save('ouro.jpg', c)

def agua():
    """ondulações para a superfície da água (tons de cinza; a cor vem do material)."""
    f1, f2, _, _ = voronoi(N, 140, 111, 1.0)
    v = sstep(0.0, 0.02, f2 - f1)
    g = fbm(N, 8, 112, 4)
    c = 0.55 + 0.25 * g - 0.3 * (1 - v)
    c = np.repeat(np.clip(c, 0, 1)[..., None], 3, -1)
    save('agua.jpg', c)
    save('agua_n.png', normal_map(v * 0.6 + g * 0.4, 3.0))

def fundo():
    """fundo panorâmico 360°: céu enevoado do pântano e camadas de árvores sumindo na névoa.
    A base fica da cor da névoa da cena, para emendar com o chão distante."""
    W, H = 4096, 1024
    yy = np.mgrid[0:H, 0:W][0] / H
    fogc, skytop = col('#4c5a49'), col('#1d2622')
    sky = mix(skytop, col('#6d7a63'), sstep(0.0, 0.62, yy))
    img = Image.fromarray((sky * 255).astype(np.uint8)); d = ImageDraw.Draw(img, 'RGBA')
    rng = np.random.default_rng(121)
    # nuvens baixas
    cl = fbm(1024, 6, 122, 5); cl = np.asarray(Image.fromarray((cl * 255).astype(np.uint8)).resize((W, H)), float) / 255
    a = (sstep(0.5, 0.8, cl) * sstep(0.05, 0.4, yy) * (1 - sstep(0.4, 0.6, yy)) * 0.35)
    base = np.asarray(img, float) / 255
    base = lerp(base, col('#9aa58a')[None, None, :], a[..., None])
    img = Image.fromarray((np.clip(base, 0, 1) * 255).astype(np.uint8)); d = ImageDraw.Draw(img, 'RGBA')
    # 4 camadas de mata: as de trás mais claras (névoa), as da frente mais escuras e altas
    layers = [(0.60, '#57654f', 0.10, 180, 30), (0.66, '#46523f', 0.14, 140, 40), (0.72, '#333d2d', 0.18, 110, 55), (0.80, '#232b1f', 0.26, 80, 75)]
    for li, (horizon, hexc, hmax, count, wmax) in enumerate(layers):
        c = tuple(int(v * 255) for v in col(hexc)) + (255,)
        yb = int(horizon * H)
        d.rectangle([0, yb, W, H], fill=c)
        for k in range(count):
            x = rng.random() * W; h = rng.uniform(0.35, 1.0) * hmax * H; w = rng.uniform(0.3, 1.0) * wmax
            kind = rng.random()
            for ox in (-W, 0, W):
                xx = x + ox
                if kind < 0.45:  # árvore morta: tronco e galhos tortos
                    d.line([(xx, yb), (xx + rng.uniform(-8, 8), yb - h)], fill=c, width=int(max(3, w * 0.18)))
                    for _ in range(5):
                        t = rng.uniform(0.35, 0.95); bx, by = xx, yb - h * t; ang = rng.uniform(-2.6, -0.5); L = rng.uniform(0.15, 0.45) * h
                        d.line([(bx, by), (bx + math.cos(ang) * L * (1 if rng.random() < 0.5 else -1), by + math.sin(ang) * L * 0.6)], fill=c, width=int(max(2, w * 0.07)))
                else:  # árvore de copa caída (salgueiro do brejo)
                    d.line([(xx, yb), (xx, yb - h * 0.75)], fill=c, width=int(max(3, w * 0.15)))
                    for _ in range(9):
                        r = rng.uniform(0.25, 0.5) * w; cx = xx + rng.uniform(-0.6, 0.6) * w; cy = yb - h * rng.uniform(0.55, 1.0)
                        d.ellipse([cx - r, cy - r * 0.8, cx + r, cy + r * 1.3], fill=c)
                        d.line([(cx, cy), (cx + rng.uniform(-6, 6), cy + h * rng.uniform(0.2, 0.45))], fill=c, width=2)  # musgo pendurado
        # névoa sobre a camada (mais forte nas de trás)
        fogk = [0.55, 0.42, 0.28, 0.12][li]
        arr = np.asarray(img, float) / 255
        fogmask = (sstep(horizon - hmax * 1.1, horizon + 0.05, yy) * fogk)
        arr = lerp(arr, fogc[None, None, :], fogmask[..., None])
        img = Image.fromarray((np.clip(arr, 0, 1) * 255).astype(np.uint8)); d = ImageDraw.Draw(img, 'RGBA')
    # base: névoa cobrindo tudo (emenda com a cor da névoa da cena)
    arr = np.asarray(img, float) / 255
    arr = lerp(arr, fogc[None, None, :], (sstep(0.8, 0.98, yy) * 0.9)[..., None])
    Image.fromarray((np.clip(arr, 0, 1) * 255).astype(np.uint8)).save(os.path.join(OUT, 'fundo.jpg'), quality=88)
    print('   fundo.jpg', (W, H))

if __name__ == '__main__':
    for f in (musgo, lama, caverna, piso, rocha, tijolo, ossuario, madeira, metal, ouro, agua, fundo):
        print(f.__name__); f()
