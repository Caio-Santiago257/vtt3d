"""Texturas do Observatório de Letarion, geradas por código (numpy + Pillow).

Chão do terreno: reaproveita terra, grama, calçada e rocha da Encruzilhada e o musgo do covil.
Novas: pedra (blocos da parede), reboco, madeira escura, tábuas do piso, telhas, lajes, cobre da cúpula,
tapetes (vermelho, azul, verde), lombadas de livros, cartas estelares, quadro da lua, cascata e espuma.
Saída: public/assets/maps/letarion/tex/
Rodar: python3 fontes/mapas/letarion_texturas.py
"""
import math, os, shutil
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
OUT = os.path.join(ROOT, 'public', 'assets', 'maps', 'letarion', 'tex')
os.makedirs(OUT, exist_ok=True)
rng = np.random.default_rng(31)

def noise(n, f, seed, oct=4):
    r = np.random.default_rng(seed); out = np.zeros((n, n)); a = 1; t = 0
    for o in range(oct):
        k = f * 2 ** o; g = r.random((k, k))
        img = Image.fromarray((g * 255).astype(np.uint8)).resize((n, n), Image.BICUBIC)
        # emenda nas bordas: média com a versão deslocada
        arr = np.asarray(img, float) / 255
        out += arr * a; t += a; a *= 0.5
    out /= t
    return out
def tile(arr):   # deixa emendável misturando com a cópia deslocada pela metade
    n = arr.shape[0]; s = np.roll(np.roll(arr, n // 2, 0), n // 2, 1)
    y, x = np.mgrid[0:n, 0:n] / n
    w = (np.minimum(x, 1 - x) * np.minimum(y, 1 - y)) ** 0.5; w = w / w.max()
    if arr.ndim == 3: w = w[..., None]
    return arr * w + s * (1 - w)
def hexc(h): h = h.lstrip('#'); return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], float) / 255
def save(name, arr, q=88):
    img = Image.fromarray((np.clip(arr, 0, 1) * 255).astype(np.uint8))
    if name.endswith('.png'): img.save(os.path.join(OUT, name), optimize=True)
    else: img.convert('RGB').save(os.path.join(OUT, name), quality=q)

def blocks(n, rows, seed, jitter=0.35, mortar=0.035):
    """blocos de pedra em fiadas, com comprimentos variados; devolve (id do bloco, distância à junta)"""
    r = np.random.default_rng(seed); ids = np.zeros((n, n)); edge = np.ones((n, n))
    rh = n / rows; y = np.arange(n)[:, None]; x = np.arange(n)[None, :]
    for i in range(rows):
        y0, y1 = int(i * rh), int((i + 1) * rh)
        xs = [0]; off = r.uniform(0, n / 3)
        while xs[-1] < n: xs.append(xs[-1] + r.uniform(n / 6, n / 3.2))
        xs = [(v + off) % n for v in xs[:-1]]; xs = sorted(xs) + [xs[0] + n] if xs else [0, n]
        for k in range(len(xs) - 1):
            a, b = xs[k], xs[k + 1]
            xx = (np.arange(n) - a) % n
            m = (xx < (b - a))
            ids[y0:y1, m] = r.random()
            dx = np.minimum(xx, (b - a) - xx)[m]; dy = np.minimum(np.arange(y0, y1) - y0, y1 - 1 - np.arange(y0, y1))[:, None]
            edge[y0:y1, m] = np.minimum(dx[None, :], dy) / n
    return ids, edge

def pedra():
    n = 1024; ids, edge = blocks(n, 8, 5)
    base = hexc('#9a9184'); var = (ids[..., None] - 0.5) * 0.22
    nz = noise(n, 16, 1)[..., None]; nz2 = noise(n, 64, 2)[..., None]
    col = base + var * np.array([1, 0.95, 0.85]) + (nz - 0.5) * 0.18 + (nz2 - 0.5) * 0.08
    mort = np.clip(1 - edge / 0.008, 0, 1)[..., None]
    col = col * (1 - mort * 0.55) + hexc('#5c554c') * mort * 0.55
    bev = np.clip(edge / 0.02, 0, 1)[..., None]
    col *= 0.82 + 0.18 * bev
    save('pedra.jpg', col)
    h = np.clip(edge / 0.02, 0, 1) * 0.7 + noise(n, 32, 3) * 0.3
    gx, gy = np.gradient(h); nm = np.stack([-gx * 6, -gy * 6, np.ones_like(h)], -1); nm /= np.linalg.norm(nm, axis=-1, keepdims=True)
    save('pedra_n.png', nm * 0.5 + 0.5)

def reboco():
    n = 512; nz = noise(n, 8, 11); nz2 = noise(n, 48, 12)
    col = hexc('#e2d6bd') * (0.9 + 0.12 * nz[..., None]) - (nz2[..., None] - 0.5) * 0.06
    stain = np.clip((noise(n, 4, 13) - 0.62) * 3, 0, 1)[..., None]
    col = col * (1 - stain * 0.18)
    save('reboco.jpg', tile(col))

def madeira(name='madeira.jpg', c0='#4a2f1c', c1='#6b4528', planks=6, n=512, seed=21):
    r = np.random.default_rng(seed)
    y, x = np.mgrid[0:n, 0:n] / n
    pid = np.floor(y * planks); tone = r.random(planks)[pid.astype(int)]
    grain = np.sin((x * 40 + noise(n, 6, seed)[..., None][..., 0] * 9 + pid * 3.1) * math.pi) * 0.5 + 0.5
    col = hexc(c0)[None, None] * (1 - grain[..., None] * 0.35) + hexc(c1)[None, None] * grain[..., None] * 0.35
    col = col * (0.85 + 0.25 * tone[..., None])
    gap = (np.abs(y * planks - np.round(y * planks)) < 0.03)[..., None]
    col = np.where(gap, col * 0.45, col)
    save(name, col)

def telha():
    n = 512; rows = 10; y, x = np.mgrid[0:n, 0:n] / n
    row = np.floor(y * rows); off = (row % 2) * 0.5
    u = (x * 7 + off) % 1; v = (y * rows) % 1
    shape = np.clip(1 - ((u - 0.5) * 2) ** 2 * 0.6 - v * 0.35, 0, 1)
    r = np.random.default_rng(41); tone = r.random((rows, 8))[row.astype(int) % rows, np.floor(x * 7 + off).astype(int) % 8]
    base = hexc('#7a3e2a') * (0.75 + 0.35 * tone[..., None]) * (0.55 + 0.45 * shape[..., None])
    moss = np.clip((noise(n, 6, 42) - 0.6) * 3, 0, 1)[..., None]
    base = base * (1 - moss * 0.5) + hexc('#4f5a32') * moss * 0.5
    save('telha.jpg', base)

def lajes():
    n = 1024; ids, edge = blocks(n, 6, 51, mortar=0.02)
    col = hexc('#b5a58a') + (ids[..., None] - 0.5) * 0.18 + (noise(n, 24, 52)[..., None] - 0.5) * 0.12
    mort = np.clip(1 - edge / 0.006, 0, 1)[..., None]
    col = col * (1 - mort * 0.6)
    save('lajes.jpg', col)

def cobre():
    n = 512; y, x = np.mgrid[0:n, 0:n] / n
    base = hexc('#5f7a72') * (0.85 + 0.25 * noise(n, 10, 61)[..., None])
    streak = noise(n, 3, 62)[..., None]
    base = base * (0.9 + 0.15 * streak)
    seam = ((np.abs((x * 8) % 1 - 0.5) > 0.47) | (np.abs((y * 6) % 1 - 0.5) > 0.46))[..., None]
    rivet = ((((x * 64) % 1 - 0.5) ** 2 + (((y * 6) % 1) - 0.06) ** 2) < 0.02)[..., None]
    base = np.where(seam, base * 0.6 + hexc('#3c4a44') * 0.2, base)
    base = np.where(rivet, base * 1.3, base)
    save('cobre.jpg', base)

def tapete(name, c_fundo, c_borda, c_motivo, seed):
    n = 512; y, x = np.mgrid[0:n, 0:n] / n
    col = np.ones((n, n, 3)) * hexc(c_fundo)
    b = np.minimum(np.minimum(x, 1 - x), np.minimum(y, 1 - y))
    col[b < 0.1] = hexc(c_borda); col[(b > 0.035) & (b < 0.05)] = hexc(c_motivo)
    cx, cy = x - 0.5, y - 0.5; rr = np.hypot(cx * 1.0, cy * 1.6)
    med = (np.abs(np.sin(np.arctan2(cy, cx) * 8)) * 0.06 + 0.16 > rr) & (rr > 0.05)
    col[med] = hexc(c_motivo); col[rr < 0.05] = hexc(c_borda)
    pat = ((np.sin(x * 60) * np.sin(y * 60)) > 0.85) & (b > 0.12) & ~med
    col[pat] = col[pat] * 0.6 + hexc(c_motivo) * 0.4
    col *= (0.88 + 0.12 * noise(n, 32, seed)[..., None])
    save(name, col)

def livros():
    W, Hh = 1024, 512; img = Image.new('RGB', (W, Hh), (40, 25, 15)); d = ImageDraw.Draw(img)
    pal = ['#7a1f1f', '#1f3d7a', '#2f5a2a', '#6b4a1a', '#4a2a5a', '#8a6a2a', '#2a2a2a', '#5a1a2a', '#1a4a4a', '#a0522d']
    for row in range(4):
        y0 = row * Hh // 4; x = 0
        while x < W:
            w = int(rng.integers(14, 34)); h = int(Hh // 4 - rng.integers(4, 30))
            c = hexc(pal[int(rng.integers(len(pal)))]) * rng.uniform(0.7, 1.15)
            cc = tuple(int(v * 255) for v in np.clip(c, 0, 1))
            d.rectangle([x, y0 + Hh // 4 - h, x + w - 2, y0 + Hh // 4 - 2], fill=cc)
            for k in range(int(rng.integers(1, 3))):
                yy = y0 + Hh // 4 - h + int(rng.uniform(0.15, 0.8) * h)
                d.rectangle([x + 2, yy, x + w - 4, yy + 3], fill=(200, 170, 90))
            x += w
        d.rectangle([0, y0 + Hh // 4 - 3, W, y0 + Hh // 4], fill=(30, 18, 10))
    img = img.filter(ImageFilter.SMOOTH)
    img.save(os.path.join(OUT, 'livros.jpg'), quality=88)

def carta(seed, name):
    n = 512; r = np.random.default_rng(seed)
    img = Image.new('RGB', (n, n), (14, 26, 52)); d = ImageDraw.Draw(img)
    for _ in range(600):
        x, y = r.random(2) * n; s = r.random() ** 3 * 2.2
        c = int(150 + r.random() * 105); d.ellipse([x - s, y - s, x + s, y + s], fill=(c, c, int(min(255, c + 20))))
    for _ in range(5):   # constelações
        pts = [tuple(r.random(2) * n * 0.7 + n * 0.15)]
        for k in range(int(r.integers(3, 7))): px, py = pts[-1]; pts.append((px + r.normal(0, 50), py + r.normal(0, 50)))
        d.line(pts, fill=(170, 190, 230), width=1)
        for p in pts: d.ellipse([p[0] - 3, p[1] - 3, p[0] + 3, p[1] + 3], fill=(255, 245, 210))
    for rr in (n * 0.46, n * 0.3):
        d.ellipse([n / 2 - rr, n / 2 - rr, n / 2 + rr, n / 2 + rr], outline=(190, 160, 90), width=2)
    d.rectangle([3, 3, n - 4, n - 4], outline=(190, 160, 90), width=6)
    img.save(os.path.join(OUT, name), quality=90)

def quadro_lua():
    n = 512; img = Image.new('RGB', (n, n), (22, 30, 58)); d = ImageDraw.Draw(img)
    for k, ph in enumerate([0.0, 0.3, 0.6, 1.0, 0.6, 0.3]):
        cx = 50 + k * 82; cy = n // 2; r = 34
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(230, 225, 200))
        if ph < 1: d.ellipse([cx - r + ph * 2 * r * (1 if k < 3 else -1), cy - r, cx + r + ph * 2 * r * (1 if k < 3 else -1), cy + r], fill=(22, 30, 58))
    d.rectangle([4, 4, n - 5, n - 5], outline=(170, 130, 60), width=10)
    img.save(os.path.join(OUT, 'quadro.jpg'), quality=88)

def cascata():
    n = 256; y, x = np.mgrid[0:n, 0:n] / n
    st = np.zeros((n, n))
    r = np.random.default_rng(71)
    for _ in range(90):
        cx = r.random(); w = r.uniform(0.004, 0.02); a = r.uniform(0.3, 1)
        st += a * np.exp(-(((x - cx + 0.5) % 1 - 0.5) / w) ** 2) * (0.6 + 0.4 * np.sin(y * math.pi * 2 * r.integers(1, 4) + r.random() * 6))
    st = np.clip(st / st.max(), 0, 1)
    col = np.stack([0.75 + 0.25 * st, 0.86 + 0.14 * st, 0.95 + 0.05 * st, 0.35 + 0.6 * st], -1)
    save('cascata.png', col)
    f = np.clip(noise(n, 8, 72) * 1.4 - 0.2, 0, 1)
    save('espuma.png', np.stack([f * 0 + 1, f * 0 + 1, f * 0 + 1, f * 0.9], -1))

def main():
    for src, dst in [('estrada/tex/terra.jpg', 'terra.jpg'), ('estrada/tex/grama.jpg', 'grama.jpg'), ('estrada/tex/calcada.jpg', 'calcada.jpg'),
                     ('estrada/tex/rocha.jpg', 'rocha.jpg'), ('estrada/tex/agua_n.png', 'agua_n.png'), ('covil/tex/musgo.jpg', 'musgo.jpg'),
                     ('estrada/tex/capim.png', 'capim.png'), ('estrada/tex/flores.png', 'flores.png'), ('estrada/tex/folhas_verdes.png', 'folhas_verdes.png')]:
        shutil.copy(os.path.join(ROOT, 'public', 'assets', 'maps', src), os.path.join(OUT, dst))
    pedra(); reboco(); madeira(); madeira('tabuas.jpg', '#6a4426', '#94643a', planks=8, seed=22); telha(); lajes(); cobre()
    tapete('tapete_vermelho.jpg', '#7a1c1c', '#3a1010', '#c9a24a', 81); tapete('tapete_azul.jpg', '#1d2f5a', '#101830', '#c9b06a', 82)
    tapete('tapete_verde.jpg', '#24452a', '#101e12', '#c9a24a', 83)
    livros(); carta(91, 'carta_a.jpg'); carta(92, 'carta_b.jpg'); quadro_lua(); cascata()
    print('texturas:', sorted(os.listdir(OUT)))

if __name__ == '__main__':
    main()
