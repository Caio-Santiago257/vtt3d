"""Céus de Letarion: três panoramas (manhã, tarde, noite) em projeção equirretangular, pintados do zero.

Rodar:  python3 fontes/mapas/letarion_ceu.py
Saída:  public/assets/maps/letarion/ceu_dia.webp, ceu_tarde.webp, ceu_noite.webp (4096 x 2048)

Geometria (igual à do jogo): a esfera tem raio 600 e o centro fica no alto do pico (y = 40).
  - o mar vai até o horizonte, que fica quase na linha do olho;
  - as Ilhas Moonshae ficam a oeste, a costa de Faerûn bem longe a leste;
  - coluna u do panorama = direção no mapa: u = 0 aponta para +x (leste), u = 0,25 para +z (sul), u = 0,5 oeste, u = 0,75 norte.
  - à noite a Lua fica a nordeste, perto de onde o telescópio aponta (azimute -40°, 50° de altura); a Via Láctea cruza o céu.
"""
import math, os
import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
OUT = os.path.join(ROOT, 'public', 'assets', 'maps', 'letarion')
W, H = 4096, 2048
rng = np.random.default_rng(31)

u = (np.arange(W) + 0.5) / W
e = 90 - 180 * (np.arange(H) + 0.5) / H          # elevação em graus, linha 0 = zênite
U, E = np.meshgrid(u, e)
AZ = U * 2 * math.pi
ER = np.radians(E)
DX, DY, DZ = np.cos(ER) * np.cos(AZ), np.sin(ER), np.cos(ER) * np.sin(AZ)
HZ = -0.35                                      # linha do horizonte do mar (graus)

def hexc(h): return np.array([(h >> 16) & 255, (h >> 8) & 255, h & 255], float) / 255
def mixc(a, b, t): return a + (b - a) * t
def sstep(a, b, x): t = np.clip((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t)
def ang(az_deg, el_deg):
    a, b = math.radians(az_deg), math.radians(el_deg)
    v = np.array([math.cos(b) * math.cos(a), math.sin(b), math.cos(b) * math.sin(a)])
    return np.degrees(np.arccos(np.clip(DX * v[0] + DY * v[1] + DZ * v[2], -1, 1)))

def ruido(w, h, beta, seed, wrap_rows=False):
    """ruído 1/f^beta periódico na horizontal (o panorama fecha sem emenda)"""
    r = np.random.default_rng(seed)
    fx = np.fft.fftfreq(w)[None, :]; fy = np.fft.fftfreq(h)[:, None]
    f = np.sqrt(fx ** 2 + fy ** 2); f[0, 0] = 1
    spec = (r.normal(size=(h, w)) + 1j * r.normal(size=(h, w))) / f ** beta
    n = np.real(np.fft.ifft2(spec)); n = (n - n.mean()) / n.std()
    return n
def up(a, w=W, h=H): return np.array(Image.fromarray(a.astype(np.float32)).resize((w, h), Image.BICUBIC))

# ---------------------------------------------------------------- ilhas (silhuetas no horizonte)
def perfil(u0, larg, alt, seed, picos=3):
    r = np.random.default_rng(seed)
    du = (u - u0 + 0.5) % 1 - 0.5
    x = du / larg
    base = np.clip(1 - x ** 2, 0, None) ** 0.7
    rug = np.zeros_like(u)
    for k in range(picos):
        c = r.uniform(-0.6, 0.6); s = r.uniform(0.12, 0.35)
        rug += r.uniform(0.4, 1.0) * np.exp(-((x - c) / s) ** 2)
    n = np.interp(u * 900 % 900, np.arange(901), r.normal(size=901).cumsum() * 0.02)
    h = alt * base * (0.45 + 0.55 * rug / max(1e-6, rug.max())) * (1 + 0.08 * np.sin(x * 37 + seed)) + n * alt * 0.04
    return np.where(np.abs(x) < 1, np.clip(h, 0, None), 0)
ILHAS = [  # (u, meia-largura, altura em graus, distância 0..1 para a névoa, semente)
    (0.47, 0.055, 4.2, 0.55, 1), (0.55, 0.035, 2.6, 0.7, 2), (0.405, 0.03, 1.8, 0.8, 3),   # Moonshae: Gwynneth, Moray, Alaron
    (0.62, 0.02, 1.2, 0.9, 4), (0.33, 0.012, 0.9, 0.85, 5), (0.71, 0.01, 0.6, 0.6, 6),
    (0.06, 0.09, 1.1, 0.97, 7), (0.95, 0.07, 0.8, 0.98, 8),                                # costa de Faerûn, bem longe a leste
    (0.2, 0.008, 0.7, 0.35, 9),                                                            # rochedo perto, ao sul
]
def silhuetas():
    """devolve (máscara 0..1, névoa 0..1) por pixel; ilhas mais perto escondem as de trás"""
    m = np.zeros((H, W)); nev = np.ones((H, W))
    for (u0, lg, alt, dist, sd) in sorted(ILHAS, key=lambda t: -t[3]):
        h = perfil(u0, lg, alt, sd)[None, :]
        inside = (E > HZ - 0.05) & (E < HZ + h)
        edge = np.clip((HZ + h - E) / 0.06, 0, 1) * inside
        m = np.maximum(m, edge); nev = np.where(edge > 0.5, dist, nev)
    return m, nev

# ---------------------------------------------------------------- céu em degradê
def degrade(stops):
    """stops: lista de (elevação, cor) de baixo para cima"""
    out = np.zeros((H, W, 3))
    es = [s[0] for s in stops]; cs = [s[1] for s in stops]
    for c in range(3): out[..., c] = np.interp(E, es, [k[c] for k in cs])
    return out

BORDA = -math.degrees(math.atan(40 / 590))      # onde acaba o mar de verdade do jogo (o disco de água, raio 590)
def mar(img, perto, longe, brilho_az=None, brilho_cor=None, largura=6, forca=1.0, seed=0, nevoa=None):
    """mar abaixo do horizonte: escurece para perto, ondas e o caminho de luz do sol ou da lua.
    Perto da borda do disco de água o mar do panorama fica na cor da névoa do jogo, para não aparecer emenda."""
    m = E < HZ
    t = sstep(HZ, BORDA, E)                    # 0 no horizonte, 1 na borda do disco
    cor = mixc(longe[None, None, :], perto[None, None, :], t[..., None])
    if nevoa is not None:
        cor = mixc(cor, nevoa[None, None, :], sstep(HZ - 0.6, BORDA + 0.3, E)[..., None] * 0.85)
    # ondas: esticadas na horizontal (vistas de lado), mais finas perto do horizonte
    ond = up(ruido(512, 1024, 1.1, seed), W, H) * 0.6 + up(ruido(1024, 2048, 0.6, seed + 1), W, H) * 0.4
    ond = ond * (0.25 + 0.75 * sstep(HZ, -6, E))
    cor = cor * (1 + 0.05 * ond[..., None])
    if brilho_az is not None:
        da = np.abs(((U - brilho_az + 0.5) % 1) - 0.5) * 360
        lar = largura * (0.25 + sstep(HZ, -8, E) * 1.2)
        trilha = np.exp(-(da / lar) ** 2) * (0.35 + 0.65 * np.clip(ond * 1.4, 0, None) ** 1.6)
        trilha *= 1 - 0.6 * sstep(-2, -12, E)
        cor = cor + brilho_cor[None, None, :] * trilha[..., None] * forca
    img[m] = cor[m]
    # linha do horizonte um pouco mais clara (luz rasante)
    hz = np.exp(-((E - HZ) / 0.25) ** 2)
    return img, hz

def salva(img, nome):
    a = np.clip(img, 0, 1) ** (1 / 1.0)
    im = Image.fromarray((a * 255 + 0.5).astype(np.uint8))
    im.save(os.path.join(OUT, nome), 'WEBP', quality=88, method=6)
    im.resize((1024, 512), Image.LANCZOS).save('/tmp/' + nome.replace('.webp', '_prev.png'))
    print(nome, os.path.getsize(os.path.join(OUT, nome)) // 1024, 'KB')

def nuvens(seed, cobertura=0.35, alto=34, achatar=3.0):
    n = up(ruido(1024, 256, 1.45, seed), W, H // 4)
    n2 = up(ndimage.gaussian_filter(ruido(2048, 512, 0.95, seed + 7), 1.2, mode='wrap'), W, H // 4)
    c = np.zeros((H, W))
    # faixa de elevação 0..alto vai para as primeiras linhas da textura achatada (perto do horizonte as nuvens ficam finas)
    k = np.clip(E / alto, 0, 1)
    rows = np.clip((k ** (1 / achatar)) * (H // 4 - 1), 0, H // 4 - 1).astype(int)
    v = n[rows, np.arange(W)[None, :]] + 0.22 * n2[rows, np.arange(W)[None, :]]
    d = sstep(cobertura * 2 - 0.3, cobertura * 2 + 1.3, v)
    d *= sstep(0.3, 3.0, E) * (1 - sstep(alto * 0.75, alto, E))
    return d, v

ilha_m, ilha_nev = silhuetas()

# ================================================================ MANHÃ
def dia():
    hor = hexc(0xa9c3d8); zen = hexc(0x2f68b8)
    img = degrade([(-90, hor), (0, mixc(hor, hexc(0xffffff), 0.25)), (3, hor), (25, mixc(hor, zen, 0.55)), (90, zen)])
    sol_az, sol_el = 145 / 360, 58
    d = ang(145, 58)
    img += hexc(0xfff4dc)[None, None, :] * (np.exp(-d / 9) * 0.35 + np.exp(-(d / 1.6) ** 2) * 2.5)[..., None]
    nv, v = nuvens(11, 0.32)
    claro = 0.92 + 0.08 * np.clip(v, -1, 1)
    sombra = mixc(hexc(0xb8c6d8), hexc(0xffffff), np.clip(0.5 + 0.4 * v, 0, 1)[..., None])
    img = mixc(img, sombra * claro[..., None], (nv * 0.92)[..., None])
    img, hz = mar(img, hexc(0x1c4768), hexc(0x5d87a8), brilho_az=sol_az, brilho_cor=hexc(0xfff0d0), largura=7, forca=0.18, seed=3, nevoa=hexc(0xa9c3d8))
    # ilhas: verdes escuras ao perto, azuladas ao longe
    perto = hexc(0x3d5440); longe = hor * 0.92
    ilha = mixc(perto[None, None, :], longe[None, None, :], ilha_nev[..., None] ** 0.8)
    img = mixc(img, ilha, ilha_m[..., None])
    img += (hexc(0xffffff) * 0.08)[None, None, :] * hz[..., None]
    salva(img, 'ceu_dia.webp')

# ================================================================ TARDE
def tarde():
    sol_az = 0.47
    hor_sol = hexc(0xffb46a); hor = mixc(hexc(0xa9c3d8), hexc(0xf0a060), 0.55); zen = hexc(0x3a3f86)
    img = degrade([(-90, hor), (0, hexc(0xffc58a)), (4, hor), (14, hexc(0xd98a86)), (35, hexc(0x8a6aa0)), (90, zen)])
    da = np.abs(((U - sol_az + 0.5) % 1) - 0.5) * 2         # 0 no lado do sol, 1 do lado oposto
    lado = np.exp(-(da / 0.35) ** 2) * (1 - sstep(0, 40, E))
    img = mixc(img, img * 0.6 + hor_sol[None, None, :] * 0.6, lado[..., None] * 0.7)
    d = ang(sol_az * 360, 5.5)
    img += hexc(0xffd9a0)[None, None, :] * (np.exp(-d / 6) * 0.5 + np.exp(-(d / 1.3) ** 2) * 3.0)[..., None]
    nv, v = nuvens(23, 0.28, alto=28, achatar=3.5)
    base_n = mixc(hexc(0x7a5a8a), hexc(0xffa57a), np.clip(lado * 1.3 + 0.2 * v, 0, 1)[..., None])
    borda = np.clip(ndimage.gaussian_filter(nv, 3) - nv * 0.6, 0, 1)
    img = mixc(img, base_n, (nv * 0.85)[..., None])
    img += hexc(0xffc070)[None, None, :] * (borda * lado * 1.2)[..., None]
    img, hz = mar(img, hexc(0x2a2a4c), hexc(0xc08a7a), brilho_az=sol_az, brilho_cor=hexc(0xffb060), largura=4, forca=1.3, seed=5, nevoa=mixc(hexc(0xa9c3d8), hexc(0xf0a060), 0.55))
    ilha = mixc(hexc(0x3a2a40)[None, None, :], (hor * 0.85)[None, None, :], ilha_nev[..., None] ** 0.8)
    img = mixc(img, ilha, ilha_m[..., None])
    img += (hexc(0xffc080) * 0.25)[None, None, :] * hz[..., None] * (0.3 + lado[..., None])
    salva(img, 'ceu_tarde.webp')

# ================================================================ NOITE
def noite():
    hor = hexc(0x1a2846); zen = hexc(0x02040c)
    img = degrade([(-90, hexc(0x050a16)), (0, hexc(0x24365a)), (6, hor), (30, hexc(0x070d1e)), (90, zen)])
    # Via Láctea: faixa num grande círculo inclinado, com poeira escura no meio
    pol = np.array([math.cos(math.radians(25)) * math.cos(math.radians(200)), math.sin(math.radians(25)), math.cos(math.radians(25)) * math.sin(math.radians(200))])
    pol /= np.linalg.norm(pol)
    lat = np.degrees(np.arcsin(np.clip(DX * pol[0] + DY * pol[1] + DZ * pol[2], -1, 1)))
    lon = np.arctan2(DZ * 1.0 - pol[2] * 0, DX)            # só para variar o brilho ao longo da faixa
    n1 = up(ruido(1024, 512, 1.0, 41)); n2 = up(ruido(2048, 1024, 0.7, 42)); n3 = up(ruido(512, 256, 1.4, 43))
    faixa = np.exp(-(lat / (9 + 3 * n3)) ** 2)
    nucleo = 0.6 + 0.4 * np.cos(np.radians(ang(60, 20)) * 0.9)      # mais brilhante para um lado (o centro da galáxia)
    poeira = sstep(-0.2, 1.4, n1 + 0.5 * n2) * np.exp(-(lat / 3.5) ** 2)
    via = faixa * nucleo * (0.55 + 0.45 * np.clip(n2 * 0.6 + 0.5, 0, 1.4)) * (1 - 0.75 * poeira)
    via *= sstep(-1, 12, E)
    cor_via = mixc(hexc(0x8fa4d8), hexc(0xf0dcc0), np.clip(nucleo - 0.5, 0, 1)[..., None] * 1.4)
    img += cor_via * (via * 0.32)[..., None]
    # estrelas: distribuição uniforme na esfera, brilho em lei de potência, mais densas na Via Láctea
    est = np.zeros((H, W, 3))
    def poe(n, bmin, bmax, alpha, concentrar=0.0, seed=0):
        r = np.random.default_rng(seed)
        z = r.uniform(-0.25, 1, n); a = r.uniform(0, 2 * math.pi, n)
        el = np.degrees(np.arcsin(z)); az = a
        if concentrar:
            # puxa parte das estrelas para perto do plano da Via Láctea
            vx, vy, vz = np.cos(np.radians(el)) * np.cos(az), np.sin(np.radians(el)), np.cos(np.radians(el)) * np.sin(az)
            dlat = vx * pol[0] + vy * pol[1] + vz * pol[2]
            keep = r.uniform(size=n) < np.exp(-(np.degrees(np.arcsin(np.clip(dlat, -1, 1))) / 10) ** 2) * concentrar + (1 - concentrar)
            el, az = el[keep], az[keep]
        b = bmin + (bmax - bmin) * r.uniform(size=len(el)) ** alpha
        tc = r.uniform(size=len(el))
        cor = np.where(tc[:, None] < 0.15, hexc(0xffc89a), np.where(tc[:, None] < 0.45, hexc(0xcfdcff), hexc(0xfff6ea)))
        x = ((az / (2 * math.pi)) % 1 * W).astype(int); y = ((90 - el) / 180 * H).astype(int)
        ok = (y >= 0) & (y < H)
        np.add.at(est, (y[ok], x[ok]), cor[ok] * b[ok, None])
    poe(26000, 0.12, 0.55, 3.0, seed=1)
    poe(30000, 0.08, 0.4, 2.5, concentrar=0.9, seed=2)
    poe(2600, 0.5, 1.6, 2.2, seed=3)
    poe(180, 1.6, 3.5, 1.5, seed=4)
    fino = ndimage.gaussian_filter(est, (0.55, 0.55, 0))
    halo = ndimage.gaussian_filter(np.clip(est - 1.2, 0, None), (2.2, 2.2, 0)) * 3.5
    cintila = np.clip(fino * 2.2 + halo, 0, 2.5) * sstep(HZ + 0.4, 6, E)[..., None]   # perto do horizonte a atmosfera apaga as fracas
    img += cintila
    # Lua (minguante gibosa) a nordeste, perto de onde o telescópio aponta
    lua_az, lua_el = 322, 41
    d = ang(lua_az, lua_el)
    R = 1.45
    disco = sstep(R + 0.06, R - 0.06, d)
    # crateras e mares: ruído só dentro do disco
    mares = up(ruido(512, 256, 1.6, 77)); cr = up(ruido(2048, 1024, 0.6, 78))
    tom = np.clip(0.86 + 0.09 * mares + 0.05 * cr, 0.55, 1)
    # terminador: o lado de baixo-esquerdo na sombra
    a0, b0 = math.radians(lua_az), math.radians(lua_el)
    cx = np.array([-math.sin(a0), 0, math.cos(a0)])
    lado = (DX * cx[0] + DZ * cx[2]) / math.radians(R)
    luzlua = sstep(-1.15, -0.55, -lado * 1.0)
    img = mixc(img, hexc(0xf4f0e2) * tom[..., None] * (0.35 + 0.65 * luzlua[..., None]) * 1.05, disco[..., None])
    img += hexc(0xb8c8f0)[None, None, :] * (np.exp(-d / 5) * 0.16 + np.exp(-d / 18) * 0.08)[..., None]
    # mar: escuro, com o caminho prateado da Lua
    img, hz = mar(img, hexc(0x030812), hexc(0x13213c), brilho_az=lua_az / 360, brilho_cor=hexc(0xc8d4f0), largura=3.2, forca=0.75, seed=9, nevoa=hexc(0x060b18))
    ilha = mixc(hexc(0x05080f)[None, None, :], hexc(0x101a30)[None, None, :], ilha_nev[..., None] ** 0.8)
    img = mixc(img, ilha, ilha_m[..., None])
    # luzinhas de vilas nas ilhas mais próximas (Moonshae)
    r = np.random.default_rng(12)
    vil = np.zeros((H, W))
    for (u0, lg, alt, dist, sd) in ILHAS[:4]:
        for _ in range(int(14 * (1 - dist) + 4)):
            uu = (u0 + r.uniform(-lg, lg) * 0.8) % 1; xx = int(uu * W)
            hh = perfil(u0, lg, alt, sd)[xx]
            if hh < 0.15: continue
            ee = HZ + r.uniform(0.05, 0.45) * hh
            yy = int((90 - ee) / 180 * H)
            vil[yy, xx] += r.uniform(0.6, 1.4)
    vil = ndimage.gaussian_filter(vil, 0.7) * 5 + ndimage.gaussian_filter(vil, 3) * 6
    img += hexc(0xffb860)[None, None, :] * vil[..., None]
    img += (hexc(0x3a5080) * 0.35)[None, None, :] * hz[..., None]
    salva(img, 'ceu_noite.webp')

if __name__ == '__main__':
    dia(); tarde(); noite()
