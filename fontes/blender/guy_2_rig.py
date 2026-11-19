"""Etapa 2 do Guy (halfling clérigo): escala, esqueleto, pesos, animações e exportação.

Entrada: fontes/blender/guy_reduzido.blend (etapa 1).
Saída:   public/assets/characters/guy/char_guy.glb

O modelo recebido é uma peça só (cabelo, rosto, manto, botas) e sem esqueleto. O esqueleto usa os mesmos
nomes de ossos da Kaira, mais ossos do manto (Skirt*), do capuz (Hood*) e do topete (Hair*).

Animações feitas para um halfling: passo curto e rápido, com quique, para acompanhar a velocidade do jogo.
Tudo é amostrado quadro a quadro (30 por segundo) e cada parte "atrasa" um pouco em relação à anterior
(quadril -> tronco -> ombros -> braços -> mãos; manto e capuz atrás das pernas e do corpo; topete por último),
que é o que dá a fluidez.
"""
import math, os, sys
import numpy as np
import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib
from kaira import Pose, X, Y, Z

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
SRC = os.path.join(ROOT, 'fontes', 'blender', 'guy_reduzido.blend')
OUT = os.path.join(ROOT, 'public', 'assets', 'characters', 'guy')
os.makedirs(OUT, exist_ok=True)

# ---------------------------------------------------------------- normalização
HEIGHT = float(os.environ.get('ALTURA', '1.0'))      # halfling: cerca de 1 m
RAW_FLOOR, RAW_AXIS_Y, RAW_TOP = -0.951, -0.06, 0.951
SCALE = HEIGHT / (RAW_TOP - RAW_FLOOR)
def T(x, y, z):
    return Vector((x * SCALE, (y - RAW_AXIS_Y) * SCALE, (z - RAW_FLOOR) * SCALE))

# articulações medidas nas vistas ortográficas (coordenadas originais)
J = {
    'hips': (0, -0.06, -0.10), 'spine': (0, -0.06, 0.02), 'spine1': (0, -0.06, 0.15), 'spine2': (0, -0.06, 0.28),
    'neck0': (0, -0.06, 0.46), 'neck1': (0, -0.05, 0.535), 'headc': (0, -0.05, 0.68), 'headtop': (0, -0.05, 0.86),
    'clav': (0.04, -0.06, 0.42), 'sh': (0.175, -0.07, 0.40), 'el': (0.255, -0.08, 0.15), 'wr': (0.315, -0.10, -0.06), 'hand': (0.335, -0.12, -0.19),
    'hip': (0.085, -0.06, -0.18), 'knee': (0.12, -0.09, -0.50), 'ankle': (0.165, -0.05, -0.84), 'ball': (0.165, -0.20, -0.92), 'toe': (0.165, -0.30, -0.945),
}
def jp(n, s=1):
    x, y, z = J[n]; return T(x * s, y, z)

def build_rig():
    ad = bpy.data.armatures.new('guy_rig'); arm = lib.link(bpy.data.objects.new('guy_rig', ad))
    lib.activate(arm); bpy.ops.object.mode_set(mode='EDIT'); eb = ad.edit_bones
    def bone(name, head, tail, parent=None, connect=False, deform=True):
        b = eb.new(name); b.head = head; b.tail = tail
        if parent: b.parent = eb[parent]; b.use_connect = connect
        b.use_deform = deform
    bone('Hips', jp('hips'), jp('spine'))
    bone('Spine', jp('spine'), jp('spine1'), 'Hips', True)
    bone('Spine1', jp('spine1'), jp('spine2'), 'Spine', True)
    bone('Spine2', jp('spine2'), jp('neck0'), 'Spine1', True)
    bone('Neck', jp('neck0'), jp('neck1'), 'Spine2', True)
    bone('Head', jp('neck1'), jp('headtop'), 'Neck', True)
    # topete (o cacho que sobe do alto da cabeça)
    bone('Hair1', T(0, -0.03, 0.84), T(0, -0.03, 0.90), 'Head')
    bone('Hair2', T(0, -0.03, 0.90), T(-0.03, -0.06, 0.955), 'Hair1', True)
    # capuz caído nas costas
    bone('Hood1', T(0, 0.08, 0.47), T(0, 0.15, 0.33), 'Spine2')
    bone('Hood2', T(0, 0.15, 0.33), T(0, 0.15, 0.17), 'Hood1', True)
    for s, P in ((1, 'Left'), (-1, 'Right')):
        sh, el, wr, hd = jp('sh', s), jp('el', s), jp('wr', s), jp('hand', s)
        d = (hd - wr).normalized()
        bone(P + 'Shoulder', jp('clav', s), sh, 'Spine2')
        bone(P + 'Arm', sh, el, P + 'Shoulder', True)
        bone(P + 'ForeArm', el, wr, P + 'Arm', True)
        bone(P + 'Hand', wr, hd, P + 'ForeArm', True)
        for n, a, b_ in (('HandIndex1', 0.0, 0.5), ('HandIndex2', 0.5, 1.0), ('HandFingers1', 0.0, 0.5), ('HandFingers2', 0.5, 1.0), ('HandThumb1', 0.0, 0.5), ('HandThumb2', 0.5, 1.0)):
            parent = P + ('Hand' if n.endswith('1') else n[:-1] + '1')
            bone(P + n, hd + d * 0.02 * a, hd + d * 0.02 * b_ + Vector((0, 0, -0.001)), parent, n.endswith('2'), deform=False)
        bone(P + 'UpLeg', jp('hip', s), jp('knee', s), 'Hips')
        bone(P + 'Leg', jp('knee', s), jp('ankle', s), P + 'UpLeg', True)
        bone(P + 'Foot', jp('ankle', s), jp('ball', s), P + 'Leg', True)
        bone(P + 'ToeBase', jp('ball', s), jp('toe', s), P + 'Foot', True)
    # manto: quatro painéis de três ossos, da cintura até a barra
    for tag, x0, x1, y0, y1 in (('F', 0, 0, -0.25, -0.30), ('B', 0, 0, 0.14, 0.30), ('L', 0.22, 0.40, -0.06, -0.04), ('R', -0.22, -0.40, -0.06, -0.04)):
        pts = [T(x0 * 0.7, y0 * 0.8 + RAW_AXIS_Y * 0.2, -0.04), T(x0 + (x1 - x0) * 0.33, y0 + (y1 - y0) * 0.33, -0.24),
               T(x0 + (x1 - x0) * 0.66, y0 + (y1 - y0) * 0.66, -0.43), T(x1, y1, -0.63)]
        for i in range(3):
            bone(f'Skirt{tag}{i + 1}', pts[i], pts[i + 1], 'Hips' if i == 0 else f'Skirt{tag}{i}', i > 0)
    bone('socket_hand_r', jp('hand', -1), jp('hand', -1) + Vector((0, 0, -0.03)), 'RightHand', deform=False)
    bone('socket_hand_l', jp('hand', 1), jp('hand', 1) + Vector((0, 0, -0.03)), 'LeftHand', deform=False)
    bone('socket_back', T(0, 0.05, 0.25), T(0, 0.05, 0.32), 'Spine2', deform=False)
    bone('socket_head', jp('headtop'), jp('headtop') + Vector((0, 0, 0.03)), 'Head', deform=False)
    bpy.ops.object.mode_set(mode='OBJECT')
    return arm

def smooth_weights(obj, cls, iters=3, k=10, radius=0.018, keep=4):
    from scipy.spatial import cKDTree
    me = obj.data; nv = len(me.vertices); ng = len(obj.vertex_groups)
    W = np.zeros((nv, ng), np.float32)
    for v in me.vertices:
        for g in v.groups: W[v.index, g.group] = g.weight
    W /= np.maximum(W.sum(1, keepdims=True), 1e-6)
    co = np.array([v.co[:] for v in me.vertices])
    cls = np.array(cls); d = np.full((nv, k), np.inf); idx = np.tile(np.arange(nv)[:, None], (1, k))
    for c in set(cls.tolist()):   # vizinhos só da mesma classe
        sel = np.where(cls == c)[0]
        dd, ii = cKDTree(co[sel]).query(co[sel], k=min(k, len(sel)), distance_upper_bound=radius)
        dd = dd.reshape(len(sel), -1); ii = ii.reshape(len(sel), -1)
        okc = np.isfinite(dd); m = dd.shape[1]
        d[sel, :m] = dd; idx[sel, :m] = np.where(okc, sel[np.minimum(ii, len(sel) - 1)], sel[:, None])
    ok = np.isfinite(d); idx = np.where(ok, idx, np.arange(nv)[:, None])
    wt = np.where(ok, np.exp(-(d / (radius * 0.6)) ** 2), 0.0).astype(np.float32); wt /= wt.sum(1, keepdims=True)
    for _ in range(iters): W = np.einsum('nk,nkg->ng', wt, W[idx])
    for gi in range(ng): obj.vertex_groups[gi].remove(list(range(nv)))
    top = np.argsort(-W, axis=1)[:, :keep]
    for vi in range(nv):
        ws = W[vi, top[vi]]; ws = ws / max(ws.sum(), 1e-6)
        for gi, w in zip(top[vi], ws):
            if w > 0.01: obj.vertex_groups[int(gi)].add([vi], float(w), 'REPLACE')

def skin_mask(obj):
    """pele pela cor da textura (as mãos ficam encostadas no manto: a cor separa uma do outro)."""
    me = obj.data
    bsdf = [n for n in obj.active_material.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'][0]
    img = bsdf.inputs['Base Color'].links[0].from_node.image
    w, h = img.size; px = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, 4)
    uv = me.uv_layers.active.data
    col = np.zeros((len(me.vertices), 3)); cnt = np.zeros(len(me.vertices))
    for poly in me.polygons:
        for li, vi in zip(poly.loop_indices, poly.vertices):
            u, vv = uv[li].uv
            col[vi] += px[int(min(h - 1, max(0, vv * h))), int(min(w - 1, max(0, u * w))), :3]; cnt[vi] += 1
    c = np.clip(col / np.maximum(cnt, 1)[:, None], 0, 1) ** (1 / 2.2)
    r, g, b = c[:, 0], c[:, 1], c[:, 2]
    # pele inclusive na sombra entre os dedos: tom quente (vermelho > verde > azul); o manto é branco ou azul
    # medido: pele ≈ (0,99 0,86 0,78); manto branco ≈ (0,99 0,94 0,92); dourado ≈ (0,91 0,80 0,64)
    return (r > 0.75) & (r - b > 0.13) & (r - g > 0.08) & (g - b < 0.13)

UPPER = ['Hips', 'Spine', 'Spine1', 'Spine2', 'Neck'] + [p + n for p in ('Left', 'Right') for n in ('Shoulder', 'Arm', 'ForeArm', 'Hand')]
def assign(obj, arm, raw, skin, force=None):
    segs = {b.name: (b.head_local.copy(), b.tail_local.copy()) for b in arm.data.bones if b.use_deform}
    for n in segs: obj.vertex_groups.new(name=n)
    side = lambda x: 'Left' if x > 0 else 'Right'
    stats = {}; out = []
    for v, (x, y, z) in zip(obj.data.vertices, raw):
        p = v.co
        ax = abs(x)
        if z > 0.50 and not (y > 0.06 and z < 0.56):
            cls = 'topete' if z > 0.83 and ax < 0.10 and y > -0.12 else 'cabeca'
        elif y > 0.05 and 0.12 < z <= 0.56 and ax < 0.25 and z > 0.12:
            cls = 'capuz'
        elif z < -0.635:
            cls = 'perna'
        elif force is not None and force[v.index]:
            cls = 'mao'
        elif force is None and ax > 0.22 and -0.26 < z < 0.0 and ((skin[v.index] and lib.seg_dist(p, *segs[side(x) + 'Hand']) < 0.045) or lib.seg_dist(p, *segs[side(x) + 'Hand']) < 0.014 or lib.seg_dist(p, *segs[side(x) + 'ForeArm']) < 0.016):
            cls = 'mao'
        elif z > -0.02:
            cls = 'tronco'
        else:
            cls = 'manto'
        stats[cls] = stats.get(cls, 0) + 1; out.append(cls)
        S = side(x)
        cand = {
            'cabeca': ['Head', 'Neck'], 'topete': ['Head', 'Hair1', 'Hair2'], 'capuz': ['Spine2', 'Hood1', 'Hood2'],
            'perna': [S + 'UpLeg', S + 'Leg', S + 'Foot', S + 'ToeBase'], 'mao': [S + 'ForeArm', S + 'Hand'],
            'tronco': UPPER, 'manto': ['Hips', 'LeftUpLeg', 'RightUpLeg'] + [f'Skirt{t}{i}' for t in 'FBLR' for i in (1, 2, 3)],
        }[cls]
        sig = {'manto': 0.05, 'tronco': 0.02, 'capuz': 0.04}.get(cls, 0.03)
        bias = {'Head': 0.7, 'LeftUpLeg': 2.2, 'RightUpLeg': 2.2, 'Hips': 1.4 if cls == 'manto' else 1.0, 'Spine2': 0.9}
        ds = [(lib.seg_dist(p, *segs[n]) * bias.get(n, 1.0), n) for n in cand]
        dmin = min(d for d, _ in ds)
        for d, n in ds:
            w = math.exp(-((d - dmin) / sig) ** 2)
            if w > 0.01: obj.vertex_groups[n].add([v.index], w, 'REPLACE')
    print('classes:', stats)
    return out

# ================================================================ animações
FPS = 30; TAU = 2 * math.pi
sn = lambda t: math.sin(TAU * t)
cs = lambda t: math.cos(TAU * t)
smooth = lambda x: x * x * (3 - 2 * x)
clamp01 = lambda x: max(0.0, min(1.0, x))
def win(t, a, b): return smooth(clamp01((t - a) / (b - a)))

def arms(P, low=0.0, swing=(0.0, 0.0), elbow=(-12.0, -12.0), out=(0.0, 0.0), hand=(-4.0, -4.0), wrist_twist=(0.0, 0.0)):
    """braços: swing negativo = para a frente; elbow negativo = dobra; out positivo = abre para o lado."""
    for k, s in enumerate((1, -1)):
        P.side(s, 'Arm', (Y, low + out[k]), (X, swing[k]))
        P.side(s, 'ForeArm', (X, elbow[k]), (Z, wrist_twist[k]))
        P.side(s, 'Hand', (X, hand[k]))
        P.side(s, 'HandFingers1', (X, -20)); P.side(s, 'HandFingers2', (X, -28))
        P.side(s, 'HandIndex1', (X, -12)); P.side(s, 'HandIndex2', (X, -16)); P.side(s, 'HandThumb1', (Z, -10))

def robe(P, f=0.0, b=0.0, l=0.0, r=0.0, wave=0.0):
    """manto: f/b/l/r = quanto cada painel abre (graus); wave = ondulação que desce pelo tecido."""
    for i in (1, 2, 3):
        k = (0.45, 0.8, 1.0)[i - 1]; w = wave * (i - 1) * 0.5
        P.add(f'SkirtF{i}', (X, -(f * k + w))); P.add(f'SkirtB{i}', (X, b * k + w))
        P.add(f'SkirtL{i}', (Y, l * k + w * 0.5)); P.add(f'SkirtR{i}', (Y, -(r * k + w * 0.5)))

def hair(P, t, base=0.0, amp=4.0, freq=1.0, lag=0.12):
    P.add('Hair1', (X, base + amp * sn(freq * t - lag)), (Z, amp * 0.6 * sn(freq * t - lag + 0.25)))
    P.add('Hair2', (X, base * 1.4 + amp * 1.6 * sn(freq * t - lag * 2)), (Z, amp * sn(freq * t - lag * 2 + 0.25)))

def hood(P, t, base=0.0, amp=2.0, freq=1.0):
    P.add('Hood1', (X, base + amp * sn(freq * t - 0.15))); P.add('Hood2', (X, base * 1.3 + amp * 1.5 * sn(freq * t - 0.3)))

def pose_idle(t):
    """respira (2 ciclos), muda o peso de perna (1 ciclo), olha em volta devagar; o topete balança com atraso."""
    P = Pose()
    br = sn(2 * t); sh = sn(t); look = sn(t + 0.1)
    P.move('Hips', (0.006 * sh, 0, -0.002 + 0.0025 * br))
    P.add('Hips', (Y, 2.0 * sh), (Z, 1.2 * sn(t - 0.1)))
    P.add('Spine', (Y, -1.2 * sh), (X, -0.8 * br)); P.add('Spine1', (Y, -0.6 * sh), (X, -1.4 * br)); P.add('Spine2', (X, -1.2 * br))
    P.add('Neck', (X, 0.8 * br), (Z, 3 * look)); P.add('Head', (Z, 6 * sn(t + 0.05) * abs(sn(t + 0.05)) ** 0.3), (X, -2 + 1.5 * sn(2 * t + 0.3)), (Y, -1.5 * sh))
    for s in (1, -1):
        P.side(s, 'Shoulder', (X, -0.8 * br), (Y, 0.6 * br))
        P.side(s, 'UpLeg', (Y, -2.0 * sh * s), (X, -1.5 - 1.5 * s * sh))
        P.side(s, 'Leg', (X, 3 + 3 * s * sh)); P.side(s, 'Foot', (X, -1.5 - 1.5 * s * sh))
    arms(P, low=0, swing=(-3 + 1.2 * sn(t + 0.2), -3 - 1.2 * sn(t + 0.2)), elbow=(-16 + 2 * br, -16 + 2 * br), out=(2 + 0.8 * br, 2 + 0.8 * br))
    hair(P, t, base=0, amp=3.0, freq=2, lag=0.18)
    hood(P, t, amp=1.0, freq=2)
    robe(P, f=0.8 * br, b=0.8 * br, l=1.5 * sh, r=-1.5 * sh)
    return P

def leg(ph, stride, knee_max, lift, push):
    """uma perna numa fase 0..1 (0 = calcanhar tocando à frente).
    apoio (0..0.5): a coxa vai de frente para trás, joelho cede no impacto e estica; pé rola do calcanhar à ponta.
    balanço (0.5..1): joelho dobra forte, pé sobe e vai à frente; ponta do pé desce de novo antes de tocar."""
    thigh = -stride * cs(ph)                                      # frente (neg.) -> trás (pos.)
    stance = ph < 0.5
    if stance:
        u = ph / 0.5
        knee = 14 * math.sin(math.pi * min(1, u / 0.45)) * (1 - u) + 4      # absorve o impacto
        foot = -12 * (1 - smooth(clamp01(u / 0.18))) + push * smooth(clamp01((u - 0.6) / 0.4))   # calcanhar -> chão -> empurra
        toe = -push * 0.9 * smooth(clamp01((u - 0.65) / 0.35))
    else:
        u = (ph - 0.5) / 0.5
        knee = 6 + knee_max * math.sin(math.pi * u) ** 0.9
        foot = push * (1 - smooth(clamp01(u / 0.35))) + lift * math.sin(math.pi * u) - 12 * smooth(clamp01((u - 0.7) / 0.3))
        toe = -push * 0.9 * (1 - smooth(clamp01(u / 0.25)))
    return thigh, knee, foot, toe

def pose_move(t, run=False):
    P = Pose()
    stride = 40 if run else 33; knee_max = 95 if run else 72; lift = 22 if run else 14; push = 26 if run else 20
    lean = -12 if run else -5
    th = []
    for s, off in ((1, 0.0), (-1, 0.5)):
        ph = (t + off) % 1.0
        a, k, f, toe = leg(ph, stride, knee_max, lift, push)
        th.append(a)
        P.side(s, 'UpLeg', (X, a), (Y, -2.5 * s)); P.side(s, 'Leg', (X, k)); P.side(s, 'Foot', (X, f)); P.side(s, 'ToeBase', (X, toe))
    # quique: o corpo desce no impacto de cada pé e sobe no meio do passo (duas vezes por ciclo)
    bounce = 0.5 + 0.5 * cs(2 * t - 0.12)
    drop = (0.022 if run else 0.013)
    P.move('Hips', (0.004 * sn(t - 0.1), 0.0, -drop * bounce))
    # quadril gira com as pernas e inclina para o lado da perna de apoio
    P.add('Hips', (Z, 9 * cs(t)), (Y, 3.5 * sn(t)), (X, lean * 0.5 - 2 * bounce))
    P.add('Spine', (Z, -5 * cs(t - 0.03)), (X, lean * 0.25 + 1.2 * bounce), (Y, -2 * sn(t - 0.04)))
    P.add('Spine1', (Z, -4 * cs(t - 0.06)), (X, lean * 0.2 + 1.0 * bounce))
    P.add('Spine2', (Z, -3 * cs(t - 0.08)), (X, lean * 0.15 + 0.8 * bounce))
    # a cabeça segura o olhar à frente (desfaz a torção e o quique do tronco)
    P.add('Neck', (Z, 2.5 * cs(t - 0.1)), (X, -lean * 0.3)); P.add('Head', (Z, 2.5 * cs(t - 0.12)), (X, -lean * 0.45 - 1.5 * bounce), (Y, -1.5 * sn(t - 0.1)))
    for s in (1, -1): P.side(s, 'Shoulder', (X, 2.5 * s * cs(t - 0.05)), (Y, -1.5 * bounce))
    # braços contrários às pernas, cotovelo e mão com atraso (sem isso o movimento fica duro)
    aw = 34 if run else 19
    swL = aw * cs(t - 0.06); swR = -aw * cs(t - 0.06)
    elL = (-75 if run else -30) - 14 * max(0, -cs(t - 0.14)); elR = (-75 if run else -30) - 14 * max(0, cs(t - 0.14))
    arms(P, low=0, swing=(swL - 4, swR - 4), elbow=(elL, elR), out=(5 + 2 * bounce, 5 + 2 * bounce),
         hand=(-4 + 5 * cs(t - 0.2), -4 - 5 * cs(t - 0.2)))
    # manto: o painel da frente é empurrado pela coxa da frente; o de trás pela de trás; ondula com atraso
    # o manto segue as coxas com atraso (sobreposição): sem isso o tecido parece colado na perna
    lag = [leg((t - 0.07 + off) % 1.0, stride, knee_max, lift, push)[0] for off in (0.0, 0.5)]
    front = max(0.0, -lag[0], -lag[1]); back = max(0.0, lag[0], lag[1])
    robe(P, f=4 + front * 0.85, b=(10 if run else 6) + back * 0.8, l=-lag[0] * 0.3 + 2, r=-lag[1] * 0.3 + 2, wave=4 * cs(2 * t - 0.3))
    hood(P, t, base=8 if run else 4, amp=4 if run else 2.5, freq=2)
    hair(P, t, base=-8 if run else -4, amp=9 if run else 6, freq=2, lag=0.16)
    return P

def pose_cast(t):
    """clérigo: junta as mãos em prece no peito, ergue a mão direita aberta para o alto e lança a bênção à frente."""
    P = pose_idle(0.0)
    P = Pose()
    pray = win(t, 0.0, 0.25) * (1 - win(t, 0.36, 0.5))
    raise_ = win(t, 0.34, 0.52) * (1 - win(t, 0.78, 1.0))
    push = win(t, 0.52, 0.62) * (1 - win(t, 0.78, 1.0))
    up = win(t, 0.3, 0.5) * (1 - win(t, 0.75, 0.95))
    P.move('Hips', (0, 0, 0.012 * up - 0.01 * pray))
    P.add('Hips', (X, 3 * pray - 2 * push))
    P.add('Spine1', (X, 6 * pray - 6 * raise_), (Z, 6 * raise_)); P.add('Spine2', (X, 4 * pray - 5 * raise_), (Z, 4 * raise_))
    P.add('Head', (X, 12 * pray - 10 * raise_ + 4 * push), (Z, -3 * raise_))
    # prece: os dois braços vêm à frente e para dentro, cotovelos dobrados, mãos se encontram no peito
    for k, s in enumerate((1, -1)):
        right = s < 0
        sw = -38 * pray + (-105 * raise_ + 40 * push if right else -20 * raise_)
        el = -95 * pray + (-20 * raise_ + 10 * push if right else -40 * raise_)
        P.side(s, 'Arm', (X, sw), (Z, 28 * pray * s * 0 + 0), (Y, -18 * pray + (14 * raise_ if right else 8 * raise_)))
        P.side(s, 'ForeArm', (X, el), (Z, -30 * pray))
        P.side(s, 'Hand', (X, 10 * pray + (-30 * push if right else 0)))
    for s in (1, -1):
        P.side(s, 'UpLeg', (X, -2 * up)); P.side(s, 'Foot', (X, 10 * up))
    robe(P, f=2 * pray, b=4 * raise_, wave=3 * sn(2 * t))
    hood(P, t, base=-2 * pray + 3 * raise_, amp=1.5, freq=2)
    hair(P, t, base=-4 * raise_, amp=5, freq=2, lag=0.2)
    return P

def pose_attack(t):
    """golpe de maça com a mão direita: prepara por cima do ombro, desce em arco e volta."""
    P = Pose()
    wind = win(t, 0.0, 0.32) * (1 - win(t, 0.36, 0.48))
    hit = win(t, 0.36, 0.5) * (1 - win(t, 0.7, 1.0))
    P.add('Hips', (Z, -10 * wind + 14 * hit), (X, -4 * hit)); P.move('Hips', (0, -0.02 * hit, -0.012 * hit))
    P.add('Spine1', (Z, -14 * wind + 16 * hit), (X, 4 * wind - 10 * hit)); P.add('Spine2', (Z, -8 * wind + 10 * hit), (X, -6 * hit))
    P.add('Head', (Z, 10 * wind - 12 * hit), (X, 4 * hit))
    P.side(-1, 'Arm', (X, -95 * wind - 45 * hit), (Y, 18 * wind + 8 * hit)); P.side(-1, 'ForeArm', (X, -60 * wind - 10 * hit)); P.side(-1, 'Hand', (X, 25 * wind - 30 * hit))
    P.side(1, 'Arm', (X, -25 * wind + 15 * hit), (Y, 12 * wind)); P.side(1, 'ForeArm', (X, -50 * wind - 30 * hit))
    P.side(-1, 'UpLeg', (X, -18 * hit)); P.side(-1, 'Leg', (X, 16 * hit)); P.side(1, 'UpLeg', (X, 10 * hit)); P.side(1, 'Leg', (X, 6 * hit))
    for s in (1, -1):
        P.side(s, 'HandFingers1', (X, -60)); P.side(s, 'HandFingers2', (X, -60)); P.side(s, 'HandIndex1', (X, -55)); P.side(s, 'HandIndex2', (X, -55))
    robe(P, f=8 * hit, b=6 * hit + 3 * wind, l=4 * hit, wave=4 * hit)
    hood(P, t, base=6 * hit, amp=2, freq=2)
    hair(P, t, base=-10 * hit + 4 * wind, amp=5, freq=2)
    return P

def pose_hit(t):
    k = math.exp(-((t - 0.2) / 0.17) ** 2)
    P = Pose()
    P.move('Hips', (0, 0.035 * k, -0.012 * k))
    P.add('Spine', (X, 6 * k)); P.add('Spine1', (X, 10 * k)); P.add('Spine2', (X, 8 * k)); P.add('Neck', (X, 6 * k)); P.add('Head', (X, 12 * k), (Z, 8 * k))
    for s in (1, -1): P.side(s, 'UpLeg', (X, -8 * k)); P.side(s, 'Leg', (X, 14 * k))
    arms(P, swing=(-20 * k, -14 * k), elbow=(-16 - 40 * k, -16 - 30 * k), out=(10 * k, 10 * k))
    robe(P, f=-6 * k, b=-4 * k, wave=4 * k)
    hood(P, t, base=-6 * k, amp=1)
    hair(P, t, base=14 * k, amp=3, freq=2)
    return P

def pose_death(t):
    buckle = win(t, 0.0, 0.32); fall = win(t, 0.28, 0.68); settle = win(t, 0.66, 0.8) * (1 - win(t, 0.8, 1.0))
    P = Pose()
    for s in (1, -1):
        P.side(s, 'UpLeg', (X, -50 * buckle + 34 * fall), (Y, -6 * fall))
        P.side(s, 'Leg', (X, 95 * buckle - 72 * fall))
        P.side(s, 'Foot', (X, 20 * fall))
    P.add('Spine1', (X, 14 * buckle - 6 * fall)); P.add('Head', (X, 12 * buckle - 4 * settle), (Z, 25 * fall))
    P.add('Hips', (X, 82 * fall), (Z, 10 * fall))
    P.move('Hips', (0, 0.12 * fall, -0.17 * buckle - 0.26 * fall + 0.01 * settle))
    arms(P, swing=(-10 - 40 * fall, -10 - 30 * fall), elbow=(-16 - 30 * buckle + 30 * fall, -16 - 20 * buckle + 20 * fall), out=(20 * fall, 30 * fall))
    robe(P, f=-25 * fall, b=-35 * fall)
    hood(P, t, base=-20 * fall, amp=0.5)
    hair(P, t, base=10 * fall, amp=2)
    return P

def bake(arm, name, fn, frames, loop=True):
    act = lib.new_action(arm, name)
    for f in range(frames + 1):   # quadro a quadro: nada de interpolação entre chaves espaçadas
        t = f / frames
        P = fn(t % 1.0 if loop else t)
        lib.key_pose(arm, f + 1, P.r, P.loc)
    lib.push_nla(arm, act)

def build_animations(arm):
    bpy.context.scene.render.fps = FPS
    bake(arm, 'idle', pose_idle, 108)                         # 3,6 s
    bake(arm, 'walk', lambda t: pose_move(t, False), 16)      # passo curto e rápido de halfling
    bake(arm, 'run', lambda t: pose_move(t, True), 12)
    bake(arm, 'cast', pose_cast, 42, loop=False)
    bake(arm, 'attack', pose_attack, 26, loop=False)
    bake(arm, 'hit', pose_hit, 18, loop=False)
    bake(arm, 'death', pose_death, 46, loop=False)

def main():
    bpy.ops.wm.open_mainfile(filepath=SRC)
    obj = bpy.data.objects['guy_src']; obj.name = 'guy'
    raw = [tuple(v.co) for v in obj.data.vertices]
    for v in obj.data.vertices: v.co = T(*v.co)
    obj.data.update()
    arm = build_rig()
    cls = assign(obj, arm, raw, skin_mask(obj))
    # o modelo recebido tem as mãos grudadas no manto (mesmas arestas): solta as faces da mão do resto,
    # senão o tecido estica junto quando o braço balança. Depois refaz os pesos na malha já separada.
    import bmesh
    bm = bmesh.new(); bm.from_mesh(obj.data); bm.verts.ensure_lookup_table()
    hand_face = {f.index: sum(cls[v.index] == 'mao' for v in f.verts) * 2 > len(f.verts) for f in bm.faces}
    cut = [e for e in bm.edges if len(e.link_faces) == 2 and hand_face[e.link_faces[0].index] != hand_face[e.link_faces[1].index]]
    bmesh.ops.split_edges(bm, edges=cut)
    bm.verts.index_update(); bm.verts.ensure_lookup_table()   # os vértices novos do corte precisam de índice
    force = [False] * len(bm.verts)
    for f in bm.faces:
        if hand_face.get(f.index, False):
            for v in f.verts: force[v.index] = True
    for v in bm.verts:   # vértice só de faces de manto não é mão, mesmo que estivesse marcado
        if v.link_faces and not any(hand_face.get(f.index, False) for f in v.link_faces): force[v.index] = False
    bm.to_mesh(obj.data); bm.free(); obj.data.update()
    print('arestas cortadas entre mão e manto:', len(cut))
    for g in list(obj.vertex_groups): obj.vertex_groups.remove(g)
    raw = [((v.co.x / SCALE), v.co.y / SCALE + RAW_AXIS_Y, v.co.z / SCALE + RAW_FLOOR) for v in obj.data.vertices]
    cls = assign(obj, arm, raw, skin_mask(obj), force)
    smooth_weights(obj, cls)
    lib.bind(obj, arm)
    mat = obj.active_material; mat.name = 'guy'
    mat['ramp'] = 'soft'; mat['rim'] = 0.25; mat['noOutline'] = True
    bsdf = [n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'][0]
    for inp in ('Metallic', 'Roughness'):
        for l in list(bsdf.inputs[inp].links): mat.node_tree.links.remove(l)
    bsdf.inputs['Metallic'].default_value = 0.0; bsdf.inputs['Roughness'].default_value = 0.8
    for img in bpy.data.images:
        if img.size[0] > 2048: img.scale(2048, 2048)
    build_animations(arm)
    print('triângulos', lib.tri_count(obj))
    for o in bpy.context.scene.objects: o.select_set(o in (obj, arm))
    bpy.ops.export_scene.gltf(
        filepath=os.path.join(OUT, 'char_guy.glb'), export_format='GLB', use_selection=True,
        export_extras=True, export_animations=True, export_animation_mode='NLA_TRACKS', export_force_sampling=True,
        export_skins=True, export_def_bones=False, export_image_format='JPEG', export_jpeg_quality=88)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT, 'fontes', 'blender', 'guy_rig.blend'))

if __name__ == '__main__':
    main()
