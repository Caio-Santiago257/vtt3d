"""Etapa 2 do dragão negro adulto recebido (Meshy): posição, escala, esqueleto, pesos, animações e exportação.

Entrada: fontes/blender/dragao_reduzido.blend (etapa 1, 40 mil triângulos).
Saída:   public/assets/characters/dragao_negro/char_dragao_negro.glb

O modelo veio parado, numa peça só, sem esqueleto, com o corpo meio torto na diagonal.
Aqui ele é girado para andar para a frente (-Y no Blender, +Z no jogo), centrado entre as quatro patas
e escalado para ocupar no mínimo 3 x 3 quadrados (4,5 m de largura) e 3 quadrados de altura.
"""
import math, os, sys
import numpy as np
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
SRC = os.path.join(ROOT, 'fontes', 'blender', 'dragao_reduzido.blend')
OUT = os.path.join(ROOT, 'public', 'assets', 'characters', 'dragao_negro')

X, Y, Z = (1, 0, 0), (0, 1, 0), (0, 0, 1)
TAU = 2 * math.pi
FPS = 30

# ---------------------------------------------------------------- normalização
ROT = -20.1                  # graus em Z: a linha quadril -> cabeça passa a apontar para a frente
CENTER = (-0.14, -0.08)      # meio das quatro patas, no modelo já girado
FLOOR = -0.751
MIN_SIDE = 4.55              # metros: 3 quadrados de 1,5 m, com folga
SCALE = 1.0                  # calculado em main()

def T(x, y, z):
    return Vector(((x - CENTER[0]) * SCALE, (y - CENTER[1]) * SCALE, (z - FLOOR) * SCALE))

# ---------------------------------------------------------------- articulações (modelo girado, unidades originais)
SPINE = [(-0.20, 0.32, -0.14), (-0.08, 0.05, -0.12), (-0.03, -0.20, -0.12), (-0.05, -0.40, -0.13),
         (-0.10, -0.55, -0.14), (-0.15, -0.66, -0.18), (-0.10, -0.95, -0.33)]
TAIL = [(-0.20, 0.32, -0.14), (-0.24, 0.48, -0.20), (-0.25, 0.62, -0.30), (-0.18, 0.75, -0.37),
        (-0.10, 0.87, -0.43), (-0.08, 0.98, -0.46), (-0.20, 1.08, -0.52)]
LEGS = {  # ombro/quadril, cotovelo/joelho, pulso/tornozelo, ponta da pata
    'FrontLeft':  [(0.12, -0.25, -0.18), (0.17, -0.24, -0.42), (0.22, -0.33, -0.64), (0.25, -0.48, -0.72)],
    'FrontRight': [(-0.12, -0.36, -0.18), (-0.20, -0.38, -0.42), (-0.24, -0.56, -0.64), (-0.25, -0.72, -0.72)],
    'BackLeft':   [(-0.10, 0.24, -0.18), (-0.21, 0.17, -0.40), (-0.23, 0.23, -0.62), (-0.22, 0.05, -0.72)],
    'BackRight':  [(-0.26, 0.40, -0.18), (-0.26, 0.52, -0.38), (-0.30, 0.62, -0.62), (-0.32, 0.48, -0.72)],
}
WINGS = {  # raiz, pulso da asa, e as três pontas da membrana (alto, fora, atrás)
    'Left':  [(0.05, -0.15, 0.0), (0.40, -0.05, 0.60), (0.50, 0.02, 0.74), (0.55, -0.39, 0.53), (0.15, 0.42, 0.38)],
    'Right': [(-0.12, -0.05, 0.0), (-0.40, 0.05, 0.62), (-0.39, -0.03, 0.75), (-0.56, 0.31, 0.59), (-0.51, 0.45, 0.21)],
}
SPINE_NAMES = ['Hips', 'Spine', 'Chest', 'Neck1', 'Neck2', 'Head']
TAIL_NAMES = [f'Tail{i}' for i in range(1, 7)]
LEG_PARTS = ['Upper', 'Lower', 'Foot']
WING_PARTS = ['Wing1', 'WingTip', 'WingOut', 'WingBack']

def build_rig():
    ad = bpy.data.armatures.new('dragao_rig')
    arm = lib.link(bpy.data.objects.new('dragao_rig', ad))
    lib.activate(arm); bpy.ops.object.mode_set(mode='EDIT')
    eb = ad.edit_bones
    def bone(name, h, t, parent=None, connect=False, deform=True):
        b = eb.new(name); b.head = T(*h); b.tail = T(*t); b.use_deform = deform
        if parent: b.parent = eb[parent]; b.use_connect = connect
    for i, n in enumerate(SPINE_NAMES):
        bone(n, SPINE[i], SPINE[i + 1], SPINE_NAMES[i - 1] if i else None, i > 0)
    for i, n in enumerate(TAIL_NAMES):
        bone(n, TAIL[i], TAIL[i + 1], 'Hips' if i == 0 else TAIL_NAMES[i - 1], i > 0)
    for leg, pts in LEGS.items():
        parent = 'Chest' if leg.startswith('Front') else 'Hips'
        for i, part in enumerate(LEG_PARTS):
            bone(leg + part, pts[i], pts[i + 1], parent if i == 0 else leg + LEG_PARTS[i - 1], i > 0)
    for side, p in WINGS.items():
        bone(side + 'Wing1', p[0], p[1], 'Chest')
        bone(side + 'WingTip', p[1], p[2], side + 'Wing1', True)
        bone(side + 'WingOut', p[1], p[3], side + 'Wing1')
        bone(side + 'WingBack', p[1], p[4], side + 'Wing1')
    bone('socket_mouth', SPINE[-1], (SPINE[-1][0], SPINE[-1][1] - 0.04, SPINE[-1][2]), 'Head', deform=False)
    bpy.ops.object.mode_set(mode='OBJECT')
    return arm

# ---------------------------------------------------------------- pesos
def midline_x(y):
    """x do eixo do corpo em cada altura do comprimento (medido nas fatias do modelo girado)."""
    ys = [-0.95, -0.65, -0.45, -0.15, 0.15, 0.35, 0.55, 0.75, 0.95, 1.08]
    xs = [-0.10, -0.15, -0.03, 0.0, -0.16, -0.21, -0.25, -0.15, -0.07, -0.20]
    return float(np.interp(y, ys, xs))

def assign(obj, arm):
    segs = {b.name: (b.head_local.copy(), b.tail_local.copy()) for b in arm.data.bones if b.use_deform}
    for n in segs: obj.vertex_groups.new(name=n)
    body = SPINE_NAMES + TAIL_NAMES
    legs = [l + p for l in LEGS for p in LEG_PARTS]
    wings = [s + p for s in WINGS for p in WING_PARTS]
    sig = 0.05 * SCALE
    stats = {'asa': 0, 'perna': 0, 'corpo': 0}
    for v in obj.data.vertices:
        x, y, z = v.co.x / SCALE + CENTER[0], v.co.y / SCALE + CENTER[1], v.co.z / SCALE + FLOOR   # volta às unidades originais
        off = abs(x - midline_x(y))
        cand = list(body)
        if z < -0.25: cand += legs
        if z > 0.12 or (z > -0.02 and off > 0.15): cand += wings
        ds = [(lib.seg_dist(v.co, *segs[n]), n) for n in cand]
        dmin, nmin = min(ds)
        stats['asa' if nmin in wings else 'perna' if nmin in legs else 'corpo'] += 1
        for d, n in ds:
            w = math.exp(-((d - dmin) / sig) ** 2)
            if w > 0.01: obj.vertex_groups[n].add([v.index], w, 'REPLACE')
    print('vértices por parte:', stats)

def smooth_weights(obj, iters=3, k=10, radius=0.12, keep=4):
    """suaviza pelos vizinhos no espaço: a malha decimada tem ilhas soltas (espinhos, garras)."""
    from scipy.spatial import cKDTree
    me = obj.data; nv = len(me.vertices); ng = len(obj.vertex_groups)
    W = np.zeros((nv, ng), np.float32)
    for v in me.vertices:
        for g in v.groups: W[v.index, g.group] = g.weight
    W /= np.maximum(W.sum(1, keepdims=True), 1e-6)
    co = np.array([v.co[:] for v in me.vertices])
    d, idx = cKDTree(co).query(co, k=k, distance_upper_bound=radius)
    ok = np.isfinite(d); idx = np.where(ok, idx, np.arange(nv)[:, None])
    wt = np.where(ok, np.exp(-(d / (radius * 0.6)) ** 2), 0.0).astype(np.float32)
    wt /= wt.sum(1, keepdims=True)
    for _ in range(iters):
        W = np.einsum('nk,nkg->ng', wt, W[idx])
    for gi in range(ng): obj.vertex_groups[gi].remove(list(range(nv)))
    top = np.argsort(-W, axis=1)[:, :keep]
    for vi in range(nv):
        ws = W[vi, top[vi]]; ws = ws / max(ws.sum(), 1e-6)
        for gi, w in zip(top[vi], ws):
            if w > 0.01: obj.vertex_groups[int(gi)].add([vi], float(w), 'REPLACE')

# ---------------------------------------------------------------- animações
ALL = SPINE_NAMES + TAIL_NAMES + [l + p for l in LEGS for p in LEG_PARTS] + [s + p for s in WINGS for p in WING_PARTS]

class Pose:
    def __init__(self): self.r = {n: [] for n in ALL}; self.loc = {'Hips': Vector((0, 0, 0))}
    def add(self, bone, *rots): self.r[bone].extend(rots); return self
    def move(self, v): self.loc['Hips'] = self.loc['Hips'] + Vector(v); return self

def sm(x):  # suaviza 0..1
    x = max(0.0, min(1.0, x)); return x * x * (3 - 2 * x)

def wave(P, names, t, amp, lag, axis=Z, base=0.0, freq=1.0):
    for i, n in enumerate(names):
        P.add(n, (axis, base * (i + 1) / len(names) + amp * (0.5 + i * 0.25) * math.sin(TAU * (freq * t - lag * i))))

def wings_rest(P, fold=0.0, flap=0.0, spread=0.0):
    """fold > 0 recolhe a asa para perto do corpo; flap sobe/desce; spread abre a membrana."""
    for s, sg in (('Left', 1), ('Right', -1)):
        P.add(s + 'Wing1', (Y, sg * (-fold * 18 + flap * 22 + spread * 10)), (X, fold * 6))
        P.add(s + 'WingTip', (Y, sg * (-fold * 10 + flap * 10 + spread * 12)))
        P.add(s + 'WingOut', (Y, sg * (flap * 14 + spread * 16)), (Z, sg * spread * 8))
        P.add(s + 'WingBack', (Y, sg * flap * 8))

def leg(P, name, swing, lift, rear):
    """swing em graus (negativo = para a frente); lift 0..1 tira a pata do chão."""
    P.add(name + 'Upper', (X, swing))
    P.add(name + 'Lower', (X, lift * (38 if rear else 44) - (swing * 0.15)))
    P.add(name + 'Foot', (X, -swing * 0.6 - lift * 30))

def gait(ph, duty=0.62):
    """fase da pata: no chão vai de -1 (frente) a +1 (trás); no ar volta, levantando."""
    if ph < duty:
        return -1 + 2 * ph / duty, 0.0
    u = (ph - duty) / (1 - duty)
    return 1 - 2 * sm(u), math.sin(math.pi * u)

def pose_idle(t):
    P = Pose(); br = math.sin(TAU * t)
    P.move((0, 0, 0.03 * br))
    P.add('Spine', (X, 1.2 * br)); P.add('Chest', (X, 1.5 * br))
    P.add('Neck1', (X, -2 * br), (Z, 4 * math.sin(TAU * t * 0.5)))
    P.add('Neck2', (X, -1.5 * br), (Z, 3 * math.sin(TAU * (t * 0.5 - 0.1))))
    P.add('Head', (X, 2 * math.sin(TAU * (t - 0.15))), (Z, 4 * math.sin(TAU * (0.5 * t - 0.2))))
    wave(P, TAIL_NAMES, t, 3.0, 0.08)
    wings_rest(P, fold=0.0, flap=0.08 * br)
    for n, rear in (('FrontLeft', 0), ('FrontRight', 0), ('BackLeft', 1), ('BackRight', 1)):
        P.add(n + 'Upper', (X, -1.0 * br))
    return P

def pose_loco(t, run=False):
    P = Pose()
    stride = 26 if run else 17
    phases = {'FrontLeft': 0.0, 'BackRight': 0.0 + (0.08 if not run else 0), 'FrontRight': 0.5, 'BackLeft': 0.5 + (0.08 if not run else 0)}
    for n, ph0 in phases.items():
        s, lift = gait((t + ph0) % 1.0, 0.55 if run else 0.62)
        leg(P, n, s * stride, lift * (1.3 if run else 1.0), n.startswith('Back'))
    a = math.sin(TAU * t); b2 = math.cos(TAU * 2 * t)
    P.move((0, 0, (0.10 if run else 0.06) * b2))
    lean = -6 if run else -2
    P.add('Hips', (Z, 4 * a), (X, lean * 0.3)); P.add('Spine', (Z, -3 * a)); P.add('Chest', (Z, -3 * a), (X, lean * 0.4))
    P.add('Neck1', (Z, 3 * a), (X, -lean * 0.5)); P.add('Neck2', (Z, 2 * a)); P.add('Head', (Z, 2 * a), (X, 2 * b2))
    wave(P, TAIL_NAMES, t, 6 if run else 4, 0.09)
    wings_rest(P, fold=0.0 if run else 0.05, flap=(0.35 if run else 0.12) * math.sin(TAU * 2 * t), spread=0.2 if run else 0)
    return P

def pose_attack(t):
    """mordida: recua o pescoço, lança a cabeça para a frente e para baixo, garra dianteira junto."""
    P = Pose()
    wind = sm(t / 0.35) * (1 - sm((t - 0.38) / 0.12))
    hit = sm((t - 0.38) / 0.12) * (1 - sm((t - 0.65) / 0.35))
    P.move((0, -0.25 * hit * SCALE / 4 + 0.15 * wind * SCALE / 4, 0.08 * wind))
    P.add('Chest', (X, -6 * wind + 8 * hit))
    P.add('Neck1', (X, -18 * wind + 22 * hit)); P.add('Neck2', (X, -14 * wind + 16 * hit))
    P.add('Head', (X, -10 * wind + 14 * hit))
    leg(P, 'FrontLeft', -28 * wind + 10 * hit, 0.8 * wind, False)
    leg(P, 'FrontRight', 0, 0, False)
    wave(P, TAIL_NAMES, t, 3, 0.1)
    wings_rest(P, flap=0.4 * wind - 0.1 * hit, spread=0.5 * wind)
    return P

def pose_cast(t):
    """sopro de ácido: ergue a cabeça, abre as asas e solta o sopro para a frente."""
    P = Pose()
    up = sm(t / 0.3) * (1 - sm((t - 0.45) / 0.15))
    blow = sm((t - 0.42) / 0.12) * (1 - sm((t - 0.8) / 0.2))
    P.add('Chest', (X, -8 * up + 3 * blow))
    P.add('Neck1', (X, -20 * up + 10 * blow)); P.add('Neck2', (X, -12 * up + 8 * blow)); P.add('Head', (X, -15 * up + 12 * blow))
    wings_rest(P, flap=0.5 * up, spread=0.9 * max(up, blow))
    wave(P, TAIL_NAMES, t, 4, 0.1)
    return P

def pose_hit(t):
    k = math.sin(math.pi * min(1.0, t * 1.3)) * (1 - t * 0.3)
    P = Pose()
    P.move((0, 0.12 * k * SCALE / 4, -0.04 * k))
    P.add('Chest', (X, -7 * k), (Z, 4 * k)); P.add('Neck1', (X, -10 * k), (Z, -8 * k)); P.add('Head', (X, -8 * k), (Z, -10 * k))
    wings_rest(P, flap=0.3 * k)
    wave(P, TAIL_NAMES, t, 5 * k, 0.1)
    return P

def pose_death(t):
    fall = sm(t / 0.7)
    P = Pose()
    P.move((0, 0, -0.42 * fall * SCALE / 4 * 3))
    P.add('Hips', (Y, 10 * fall)); P.add('Chest', (Y, 6 * fall))
    for n, rear in (('FrontLeft', 0), ('FrontRight', 0), ('BackLeft', 1), ('BackRight', 1)):
        P.add(n + 'Upper', (X, (-30 if not rear else 25) * fall))
        P.add(n + 'Lower', (X, (60 if not rear else -40) * fall))
    P.add('Neck1', (X, 12 * fall), (Z, 18 * fall)); P.add('Neck2', (X, 14 * fall), (Z, 10 * fall)); P.add('Head', (X, 10 * fall), (Z, 12 * fall))
    wings_rest(P, fold=-0.4 * fall, flap=-0.6 * fall)
    for i, n in enumerate(TAIL_NAMES): P.add(n, (Z, 6 * fall), (X, 3 * fall))
    return P

# ---------------------------------------------------------------- voo
def wing_beat(P, ph, amp=1.0, base=10.0, sweep=1.0):
    """bate as asas: ph 0..1 é um ciclo inteiro; desce rápido (empurra o ar) e sobe mais devagar.
    Y abre/fecha a asa para cima e para baixo; a ponta vem atrasada, como uma chicotada."""
    down = math.sin(TAU * ph)                   # +1 no alto da batida, -1 embaixo
    tip = math.sin(TAU * (ph - 0.12))
    for s, sg in (('Left', 1), ('Right', -1)):
        P.add(s + 'Wing1', (Y, sg * (base + 42 * amp * down)), (Z, sg * 10 * sweep * math.cos(TAU * ph)))
        P.add(s + 'WingTip', (Y, sg * (18 * amp * tip + 6)))
        P.add(s + 'WingOut', (Y, sg * (22 * amp * tip + 8)), (Z, sg * 6 * amp * math.sin(TAU * (ph - 0.2))))
        P.add(s + 'WingBack', (Y, sg * 12 * amp * tip))
    return down

def pose_fly_idle(t):
    """pairando no lugar: corpo de nariz para cima, patas penduradas, asas batendo forte."""
    P = Pose()
    down = wing_beat(P, t * 2, amp=1.0, base=12, sweep=1.3)    # duas batidas por ciclo
    lift = -down                                              # a batida para baixo levanta o corpo
    P.move((0, 0, 0.18 * lift))
    P.add('Hips', (X, -16))
    P.add('Spine', (X, -4 + 1.5 * lift)); P.add('Chest', (X, -4 + 2 * lift))
    P.add('Neck1', (X, 14 - 3 * lift)); P.add('Neck2', (X, 6 - 2 * lift)); P.add('Head', (X, 8 + 2 * math.sin(TAU * t)))
    # patas: dianteiras soltas para a frente, traseiras penduradas
    for n, rear in (('FrontLeft', 0), ('FrontRight', 0), ('BackLeft', 1), ('BackRight', 1)):
        sw = 8 * math.sin(TAU * (t * 2 + (0.1 if rear else 0.25)))
        P.add(n + 'Upper', (X, (-10 if not rear else 22) + sw * 0.5))
        P.add(n + 'Lower', (X, (35 if not rear else -15) + sw * 0.3))
        P.add(n + 'Foot', (X, 30 if not rear else 40))
    for i, n in enumerate(TAIL_NAMES):
        P.add(n, (X, 6 + 2 * math.sin(TAU * (t * 2 - 0.1 * i))), (Z, 4 * math.sin(TAU * (t - 0.08 * i))))
    return P

def pose_fly(t):
    """voando para a frente: corpo esticado, patas recolhidas, asas em batidas largas."""
    P = Pose()
    down = wing_beat(P, t * 2, amp=1.15, base=6, sweep=0.6)
    lift = -down
    P.move((0, 0, 0.14 * lift))
    P.add('Hips', (X, 4 + 2 * lift))
    P.add('Spine', (X, -1 * lift)); P.add('Chest', (X, -2 - 1.5 * lift))
    P.add('Neck1', (X, 6)); P.add('Neck2', (X, 2)); P.add('Head', (X, 4 + 2 * lift), (Z, 3 * math.sin(TAU * t)))
    # patas recolhidas: dianteiras dobradas junto ao peito, traseiras esticadas para trás
    for n in ('FrontLeft', 'FrontRight'):
        P.add(n + 'Upper', (X, 38)); P.add(n + 'Lower', (X, 75)); P.add(n + 'Foot', (X, 40))
    for n in ('BackLeft', 'BackRight'):
        P.add(n + 'Upper', (X, 55)); P.add(n + 'Lower', (X, -25)); P.add(n + 'Foot', (X, 60))
    for i, n in enumerate(TAIL_NAMES):
        P.add(n, (X, -3), (Z, 5 * math.sin(TAU * (t - 0.09 * i))))
    return P

def bake(arm, name, fn, frames, loop=True, step=2):
    act = lib.new_action(arm, name)
    keys = list(range(0, frames + 1, step))
    if keys[-1] != frames: keys.append(frames)
    for f in keys:
        t = f / frames
        P = fn(t % 1.0 if loop else t)
        lib.key_pose(arm, f + 1, P.r, P.loc)
    if loop:
        P = fn(0.0); lib.key_pose(arm, frames + 1, P.r, P.loc)
    lib.push_nla(arm, act)

def build_animations(arm):
    bpy.context.scene.render.fps = FPS
    bake(arm, 'idle', pose_idle, 90)
    bake(arm, 'walk', lambda t: pose_loco(t, False), 40)
    bake(arm, 'run', lambda t: pose_loco(t, True), 24)
    bake(arm, 'attack', pose_attack, 32, loop=False)
    bake(arm, 'cast', pose_cast, 48, loop=False)
    bake(arm, 'hit', pose_hit, 18, loop=False)
    bake(arm, 'death', pose_death, 60, loop=False)
    bake(arm, 'fly_idle', pose_fly_idle, 40)
    bake(arm, 'fly', pose_fly, 32)

# ---------------------------------------------------------------- montagem
def main():
    global SCALE
    bpy.ops.wm.open_mainfile(filepath=SRC)
    obj = bpy.data.objects['dragao_src']; obj.name = 'dragao'
    obj.data.transform(Matrix.Rotation(math.radians(ROT), 4, 'Z'))
    co = np.array([v.co[:] for v in obj.data.vertices])
    w, h = np.ptp(co[:, 0]), np.ptp(co[:, 2])
    SCALE = MIN_SIDE / min(w, h)
    for v in obj.data.vertices:
        v.co = T(*v.co)
    obj.data.update()
    co = np.array([v.co[:] for v in obj.data.vertices])
    print('escala %.3f -> largura %.2f m, comprimento %.2f m, altura %.2f m' % (SCALE, np.ptp(co[:, 0]), np.ptp(co[:, 1]), np.ptp(co[:, 2])))
    arm = build_rig()
    assign(obj, arm)
    smooth_weights(obj)
    lib.bind(obj, arm)
    mat = obj.active_material; mat.name = 'dragao_negro'
    mat['ramp'] = 'soft'; mat['rim'] = 0.45; mat['noOutline'] = True
    bsdf = [n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'][0]
    for inp in ('Metallic', 'Roughness'):
        for l in list(bsdf.inputs[inp].links): mat.node_tree.links.remove(l)
    bsdf.inputs['Metallic'].default_value = 0.0; bsdf.inputs['Roughness'].default_value = 0.7
    for img in bpy.data.images:
        if img.size[0] > 2048: img.scale(2048, 2048)
    build_animations(arm)
    os.makedirs(OUT, exist_ok=True)
    for o in bpy.context.scene.objects: o.select_set(o in (obj, arm))
    bpy.ops.export_scene.gltf(
        filepath=os.path.join(OUT, 'char_dragao_negro.glb'), export_format='GLB', use_selection=True,
        export_extras=True, export_animations=True, export_animation_mode='NLA_TRACKS', export_force_sampling=True,
        export_skins=True, export_def_bones=False, export_image_format='JPEG', export_jpeg_quality=88)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT, 'fontes', 'blender', 'dragao_rig.blend'))

if __name__ == '__main__':
    main()
