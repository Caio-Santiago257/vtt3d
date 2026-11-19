"""Texturas do chão dos mapas desenhados pelo mestre (aba Construir > Terreno).

Cada tipo de chão ganha uma textura que emenda nas bordas, misturada no jogo pelo tipo de cada quadrado:
  g grama, m chão da mata, t terra, l lama, b brejo, s areia, r rocha, n neve, e estrada de lajes
Reaproveita as texturas da Encruzilhada da Floresta e do Covil e gera areia e neve.
Saída: public/assets/terreno/tex/

Rodar (depois de estrada_texturas.py e covil_texturas.py): python3 fontes/mapas/terreno_texturas.py
"""
import math, os, shutil, sys
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(__file__))
from covil_texturas import fbm, lerp, sstep, col, mix
import estrada_texturas as E

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
OUT = os.path.join(ROOT, 'public', 'assets', 'terreno', 'tex')
os.makedirs(OUT, exist_ok=True)
N = 1024

def save(name, c): Image.fromarray((np.clip(c, 0, 1) * 255).astype(np.uint8)).save(os.path.join(OUT, name), quality=86)

def areia():
    """areia de deserto: ondulações do vento, grãos e pedrinhas escuras."""
    yy, xx = np.mgrid[0:N, 0:N] / N
    w = fbm(N, 4, 1301)
    rip = 0.5 + 0.5 * np.sin((yy * 22 + xx * 6 + w * 2.5) * 2 * math.pi)
    big = fbm(N, 3, 1302); f = fbm(N, 120, 1303, 2)
    c = mix(col('#b8945a'), col('#ead09a'), big * 0.6 + rip * 0.25 + f * 0.15)
    rng = np.random.default_rng(1304)
    peb = E.dots(rng, 500, 1.2, 3.0)
    c = lerp(c, col('#7a6448')[None, None, :], (peb * 0.6)[..., None])
    c *= (0.9 + 0.12 * rip)[..., None]
    save('areia.jpg', c)

def neve():
    """neve: branco azulado, montinhos suaves, rastros e gelo aparecendo."""
    big = fbm(N, 4, 1401); mid = fbm(N, 14, 1402, 4); f = fbm(N, 100, 1403, 2)
    c = mix(col('#b9c9da'), col('#f4f8fc'), big * 0.5 + mid * 0.5)
    ice = sstep(0.68, 0.82, fbm(N, 6, 1404))
    c = lerp(c, col('#9fbad0')[None, None, :], (ice * 0.4)[..., None])
    rng = np.random.default_rng(1405)
    spark = E.dots(rng, 1800, 0.5, 1.0)
    c = lerp(c, np.ones(3)[None, None, :], (spark * 0.5)[..., None])
    c *= (0.94 + 0.08 * f)[..., None]
    save('neve.jpg', c)

def copia():
    est = os.path.join(ROOT, 'public', 'assets', 'maps', 'estrada', 'tex')
    cov = os.path.join(ROOT, 'public', 'assets', 'maps', 'covil', 'tex')
    for src, dst in ((os.path.join(est, 'grama.jpg'), 'grama.jpg'), (os.path.join(est, 'folhas.jpg'), 'folhas.jpg'), (os.path.join(est, 'terra.jpg'), 'terra.jpg'),
                     (os.path.join(est, 'calcada.jpg'), 'calcada.jpg'), (os.path.join(est, 'rocha.jpg'), 'rocha.jpg'),
                     (os.path.join(cov, 'lama.jpg'), 'lama.jpg'), (os.path.join(cov, 'musgo.jpg'), 'musgo.jpg')):
        shutil.copyfile(src, os.path.join(OUT, dst))

if __name__ == '__main__':
    copia(); areia(); neve()
    print(sorted(os.listdir(OUT)))
