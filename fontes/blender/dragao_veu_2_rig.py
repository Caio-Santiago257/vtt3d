"""Dragão do Véu Corrompido (modelo recebido do Meshy): esqueleto, pesos, animações e exportação.

Entrada: fontes/blender/dragao_veu_reduzido.blend (etapa 1: 40 mil triângulos).
Saída:   public/assets/characters/dragao_negro/char_dragao_negro.glb (substitui o dragão antigo no jogo)

Skills usadas (blender-skills): blender-director (plano), creature-artist (anatomia de quadrúpede e de asa),
rigging (cadeias FK de pescoço/cauda, mandíbula, asa com braço, antebraço e três dedos; até 4 influências
por vértice; teste em poses extremas) e animation (ciclos com contato/descida/passagem/subida, sobreposição,
arcos, antecipação, laço sem emenda, ações no NLA, 30 quadros por segundo, tudo no lugar, sem root motion).

Convenções do modelo: cabeça para -Y, Z para cima; tudo é medido nas vistas ortográficas (unidades originais).
"""
import math, os, sys
import numpy as np
import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
SRC = os.path.join(ROOT, 'fontes', 'blender', 'dragao_veu_reduzido.blend')
OUT = os.path.join(ROOT, 'public', 'assets', 'characters', 'dragao_negro')
X, Y, Z = (1, 0, 0), (0, 1, 0), (0, 0, 1)
TAU = 2 * math.pi; FPS = 30

# ---------------------------------------------------------------- normalização
CENTER = (0.0, -0.28)        # meio das quatro patas
FLOOR = -0.372
MIN_SIDE = 4.55              # no mínimo 3 x 3 quadrados e 3 de altura (como o dragão antigo)
SCALE = 1.0
def T(x, y, z): return Vector(((x - CENTER[0]) * SCALE, (y - CENTER[1]) * SCALE, (z - FLOOR) * SCALE))

# ---------------------------------------------------------------- articulações (unidades originais)
SPINE = [(0, 0.02, -0.08), (0, -0.18, -0.06), (0, -0.40, -0.06), (0, -0.55, -0.02), (0, -0.66, 0.0), (0, -0.75, -0.03), (0, -0.95, -0.15)]
SPINE_NAMES = ['Hips', 'Spine', 'Chest', 'Neck1', 'Neck2', 'Head']
TAIL = [(0, 0.04, -0.10), (0, 0.22, -0.18), (0, 0.40, -0.24), (-0.01, 0.56, -0.27), (-0.07, 0.70, -0.28), (-0.17, 0.81, -0.27), (-0.30, 0.89, -0.26), (-0.43, 0.86, -0.23)]
TAIL_NAMES = [f'Tail{i}' for i in range(1, 8)]
JAW = [(0, -0.80, -0.10), (0, -0.935, -0.175)]
LEGS = {   # ombro/quadril, cotovelo/joelho, pulso/jarrete, ponta dos dedos (lado esquerdo = +x)
    'Front': [(0.09, -0.45, -0.12), (0.14, -0.41, -0.24), (0.145, -0.52, -0.325), (0.15, -0.63, -0.365)],
    'Back':  [(0.11, -0.02, -0.10), (0.155, -0.11, -0.22), (0.15, 0.02, -0.30), (0.15, -0.10, -0.368)],
}
LEG_PARTS = ['Upper', 'Lower', 'Foot']
WING = {   # ombro, cotovelo, pulso; dedos a partir do pulso
    'Arm': (0.08, -0.30, -0.02), 'Elbow': (0.14, -0.40, 0.17), 'Wrist': (0.20, -0.46, 0.32),
    'F1a': (0.42, -0.12, 0.21), 'F1b': (0.62, 0.27, -0.08), 'F2': (0.40, 0.13, 0.04), 'F3': (0.21, 0.16, 0.0),
}
SIDES = (('Left', 1), ('Right', -1))
WING_BONES = ['Wing1', 'Wing2', 'WingF1a', 'WingF1b', 'WingF2', 'WingF3']

def mx(p, s): return (p[0] * s, p[1], p[2])

def build_rig():
    ad = bpy.data.armatures.new('ARM_Dragao'); arm = lib.link(bpy.data.objects.new('ARM_Dragao', ad))
    lib.activate(arm); bpy.ops.object.mode_set(mode='EDIT'); eb = ad.edit_bones
    def bone(name, h, t, parent=None, connect=False, deform=True):
        b = eb.new(name); b.head = T(*h); b.tail = T(*t); b.use_deform = deform
        if parent: b.parent = eb[parent]; b.use_connect = connect
    for i, n in enumerate(SPINE_NAMES):
        bone(n, SPINE[i], SPINE[i + 1], SPINE_NAMES[i - 1] if i else None, i > 0)
    bone('Jaw', JAW[0], JAW[1], 'Head')
    for i, n in enumerate(TAIL_NAMES):
        bone(n, TAIL[i], TAIL[i + 1], 'Hips' if i == 0 else TAIL_NAMES[i - 1], i > 0)
    for side, s in SIDES:
        for leg, pts in LEGS.items():
            parent = 'Chest' if leg == 'Front' else 'Hips'
            for i, part in enumerate(LEG_PARTS):
                bone(f'{leg}{side}{part}', mx(pts[i], s), mx(pts[i + 1], s), parent if i == 0 else f'{leg}{side}{LEG_PARTS[i - 1]}', i > 0)
        W = {k: mx(v, s) for k, v in WING.items()}
        bone(side + 'Wing1', W['Arm'], W['Elbow'], 'Chest')
        bone(side + 'Wing2', W['Elbow'], W['Wrist'], side + 'Wing1', True)
        bone(side + 'WingF1a', W['Wrist'], W['F1a'], side + 'Wing2', True)
        bone(side + 'WingF1b', W['F1a'], W['F1b'], side + 'WingF1a', True)
        bone(side + 'WingF2', W['Wrist'], W['F2'], side + 'Wing2')
        bone(side + 'WingF3', W['Wrist'], W['F3'], side + 'Wing2')
    bone('socket_mouth', SPINE[-1], (0, -1.0, -0.16), 'Head', deform=False)
    bpy.ops.object.mode_set(mode='OBJECT')
    return arm

# ---------------------------------------------------------------- pesos por classe
BODY = SPINE_NAMES + TAIL_NAMES
def classify(x, y, z):
    ax = abs(x)
    if y < -0.79 and ax < 0.055:
        line = -0.07 + (-0.08) * (y + 0.80) / (-0.15)       # a boca: do canto até a ponta do focinho
        if z < line: return 'jaw'
    if -0.62 < y < 0.36 and ((ax > 0.165 and z > -0.13) or (ax > 0.10 and z > 0.10 and y > -0.5)):
        return 'wing'
    return 'body'

def assign(obj, arm, raw):
    segs = {b.name: (b.head_local.copy(), b.tail_local.copy()) for b in arm.data.bones if b.use_deform}
    for n in segs: obj.vertex_groups.new(name=n)
    stats = {}; out = []
    leg_segs = {f'{w}{sd}': [segs[f'{w}{sd}{p}'] for p in LEG_PARTS] for w in LEGS for sd in ('Left', 'Right')}
    body_segs = [segs[n] for n in BODY]
    for v, (x, y, z) in zip(obj.data.vertices, raw):
        c = classify(x, y, z); S = 'Left' if x > 0 else 'Right'
        if c == 'body' and z < -0.02:
            # pata: mais perto da cadeia da pata do que do corpo (com folga para o corpo nas costas e na barriga)
            dl = min(min(lib.seg_dist(v.co, *sg) for sg in leg_segs[f'{w}{S}']) for w in LEGS)
            db = min(lib.seg_dist(v.co, *sg) for sg in body_segs)
            if dl < db * 0.85: c = 'leg'
        if c == 'jaw': cand = ['Jaw', 'Head']
        elif c == 'wing': cand = [S + b for b in WING_BONES] + ['Chest', 'Spine']
        elif c == 'leg':
            leg = min(LEGS, key=lambda w: min(lib.seg_dist(v.co, *segs[f'{w}{S}{p}']) for p in LEG_PARTS))
            cand = [f'{leg}{S}{p}' for p in LEG_PARTS] + (['Chest', 'Spine'] if leg == 'Front' else ['Hips', 'Tail1'])
        else: cand = BODY
        bias = {'Head': 0.8, 'Chest': 1.25 if c == 'wing' else 1.0, 'Spine': 1.3 if c == 'wing' else 1.0}
        ds = [(lib.seg_dist(v.co, *segs[n]) * bias.get(n, 1.0), n) for n in cand]
        dmin = min(d for d, _ in ds)
        sig = (0.03 if c in ('jaw', 'leg') else 0.045 if c == 'wing' else 0.05) * SCALE
        for d, n in ds:
            w = math.exp(-((d - dmin) / sig) ** 2)
            if w > 0.01: obj.vertex_groups[n].add([v.index], w, 'REPLACE')
        stats[c] = stats.get(c, 0) + 1; out.append(c)
    print('classes:', stats)
    return out

def smooth_weights(obj, cls, iters=3, k=10, radius=0.08, keep=4):
    """suaviza só entre vizinhos da mesma classe (a asa não puxa o corpo, a mandíbula não puxa os chifres)."""
    from scipy.spatial import cKDTree
    me = obj.data; nv = len(me.vertices); ng = len(obj.vertex_groups)
    W = np.zeros((nv, ng), np.float32)
    for v in me.vertices:
        for g in v.groups: W[v.index, g.group] = g.weight
    W /= np.maximum(W.sum(1, keepdims=True), 1e-6)
    co = np.array([v.co[:] for v in me.vertices]); cls = np.array(['body' if c == 'leg' else c for c in cls])
    d = np.full((nv, k), np.inf); idx = np.tile(np.arange(nv)[:, None], (1, k))
    for c in set(cls.tolist()):
        sel = np.where(cls == c)[0]
        dd, ii = cKDTree(co[sel]).query(co[sel], k=min(k, len(sel)), distance_upper_bound=radius)
        dd = dd.reshape(len(sel), -1); ii = ii.reshape(len(sel), -1); m = dd.shape[1]
        d[sel, :m] = dd; idx[sel, :m] = np.where(np.isfinite(dd), sel[np.minimum(ii, len(sel) - 1)], sel[:, None])
    ok = np.isfinite(d); idx = np.where(ok, idx, np.arange(nv)[:, None])
    wt = np.where(ok, np.exp(-(d / (radius * 0.6)) ** 2), 0.0).astype(np.float32); wt /= wt.sum(1, keepdims=True)
    for _ in range(iters): W = np.einsum('nk,nkg->ng', wt, W[idx])
    for gi in range(ng): obj.vertex_groups[gi].remove(list(range(nv)))
    top = np.argsort(-W, axis=1)[:, :keep]
    for vi in range(nv):
        ws = W[vi, top[vi]]; ws = ws / max(ws.sum(), 1e-6)
        for gi, w in zip(top[vi], ws):
            if w > 0.01: obj.vertex_groups[int(gi)].add([vi], float(w), 'REPLACE')

# ================================================================ animações
class Pose:
    def __init__(self): self.r = {}; self.loc = {}
    def add(self, b, *rots): self.r.setdefault(b, []).extend(rots); return self
    def move(self, v): self.loc['Hips'] = self.loc.get('Hips', Vector((0, 0, 0))) + Vector(v); return self

sn = lambda t: math.sin(TAU * t)
cs = lambda t: math.cos(TAU * t)
def sm(x): x = max(0.0, min(1.0, x)); return x * x * (3 - 2 * x)
def win(t, a, b): return sm((t - a) / (b - a))
def M(m): return m * SCALE   # metros no modelo final

def tail(P, t, amp=4.0, lag=0.09, freq=1.0, lift=0.0, yaw=0.0):
    """cauda em onda: cada segmento repete o anterior com atraso (sobreposição), amplitude crescendo na ponta."""
    for i, n in enumerate(TAIL_NAMES):
        k = 0.45 + i * 0.16
        P.add(n, (Z, yaw * (i + 1) / 7 + amp * k * sn(freq * t - lag * i)), (X, lift * (0.5 + i * 0.1) + amp * 0.25 * k * sn(freq * t - lag * i + 0.25)))

def neck(P, pitch=(0, 0, 0), yaw=(0, 0, 0)):
    for n, p, y in zip(('Neck1', 'Neck2', 'Head'), pitch, yaw): P.add(n, (X, p), (Z, y))

def wings_folded(P, t=0.0, breathe=0.0, open_=0.0, twitch=0.0):
    """asas no repouso (meio abertas, como o modelo veio): só respiram e se ajeitam."""
    for side, s in SIDES:
        P.add(side + 'Wing1', (Y, s * (-4 * breathe - 18 * open_ + twitch)), (Z, s * 6 * open_))
        P.add(side + 'Wing2', (Y, s * (-3 * breathe - 10 * open_)))
        for b, k in (('WingF1a', 1.0), ('WingF1b', 0.6), ('WingF2', 0.8), ('WingF3', 0.5)):
            P.add(side + b, (Y, s * (-6 * open_ * k + 2 * breathe * k)), (Z, -s * 8 * open_ * k))

def leg(P, side, which, swing, lift, plant=0.0):
    """swing: negativo = pata vai à frente. lift 0..1: dobra para tirar do chão.
    plant: o pé compensa o ângulo da perna para ficar apoiado (sem 'patinar' a ponta)."""
    rear = which == 'Back'
    up, lo, ft = f'{which}{side}Upper', f'{which}{side}Lower', f'{which}{side}Foot'
    if rear:   # joelho para a frente, jarrete para trás
        P.add(up, (X, swing - 22 * lift)); P.add(lo, (X, 40 * lift + swing * 0.2)); P.add(ft, (X, -swing * 0.9 - 30 * lift * (1 - plant)))
    else:      # cotovelo para trás, "joelho" da frente é o pulso
        P.add(up, (X, swing + 10 * lift)); P.add(lo, (X, -38 * lift - swing * 0.15)); P.add(ft, (X, -swing * 0.85 + 55 * lift))

def gait(ph, duty):
    """apoio: a pata vai da frente (-1) para trás (+1) em linha; balanço: volta à frente num arco."""
    if ph < duty: return -1 + 2 * ph / duty, 0.0
    u = (ph - duty) / (1 - duty)
    return 1 - 2 * sm(u), math.sin(math.pi * u) ** 0.8

def pose_idle(t):
    """respira devagar (2 ciclos), olha em volta (1), ajeita as asas e a cauda; a mandíbula solta fumaça (entreabre)."""
    P = Pose(); br = sn(2 * t); look = sn(t)
    P.move((0, 0, M(0.012) * br))
    P.add('Hips', (X, 0.6 * br)); P.add('Spine', (X, 1.0 * br), (Y, 0.8 * look)); P.add('Chest', (X, 1.6 * br))
    neck(P, pitch=(-2.5 * br, -1.5 * br + 3 * sn(t + 0.3), 2 * sn(2 * t - 0.2)), yaw=(5 * look, 6 * sn(t - 0.06), 8 * sn(t - 0.12)))
    P.add('Jaw', (X, 3 + 3 * max(0, sn(2 * t - 0.35))))
    tail(P, t, amp=3.5, lag=0.07, freq=1, yaw=4 * sn(t + 0.2))
    twitch = 4 * math.exp(-((t - 0.62) / 0.05) ** 2)          # um ajuste rápido de asa no meio do ciclo
    wings_folded(P, t, breathe=br, twitch=twitch)
    for side, s in SIDES:
        P.add(f'Front{side}Upper', (X, -0.8 * br)); P.add(f'Back{side}Upper', (X, 0.6 * br), (Y, s * 0.6 * look))
    return P

def pose_walk(t, run=False):
    """andar de quadrúpede em sequência lateral (traseira esq., dianteira esq., traseira dir., dianteira dir.).
    O corpo cai no apoio e sobe na passagem; a coluna faz um S de lado; o pescoço segura a cabeça estável
    (desfaz o balanço do peito); a cauda segue com atraso e amplitude crescente; as asas quicam fechadas."""
    P = Pose()
    duty = 0.5 if run else 0.68; stride = 26 if run else 18
    phases = {('Back', 'Left'): 0.0, ('Front', 'Left'): 0.25, ('Back', 'Right'): 0.5, ('Front', 'Right'): 0.75} if not run else \
             {('Back', 'Left'): 0.0, ('Back', 'Right'): 0.1, ('Front', 'Left'): 0.5, ('Front', 'Right'): 0.6}
    lifts = {}
    for (which, side), ph0 in phases.items():
        s, lift = gait((t + ph0) % 1.0, duty)
        leg(P, side, which, s * stride, lift * (1.25 if run else 1.0))
        lifts[(which, side)] = lift
    a = sn(t); b2 = cs(2 * t)
    bob = M(0.05 if run else 0.022)
    P.move((M(0.01) * a, 0, -bob * 0.5 + bob * 0.5 * b2))
    # ombros e quadril rolam para o lado da pata que levanta
    roll_front = 5 * (lifts[('Front', 'Right')] - lifts[('Front', 'Left')]); roll_back = 4 * (lifts[('Back', 'Right')] - lifts[('Back', 'Left')])
    lean = -7 if run else -1.5
    P.add('Hips', (Z, 5 * a), (Y, roll_back), (X, lean * 0.3))
    P.add('Spine', (Z, -3 * sn(t - 0.04)), (Y, (roll_front - roll_back) * 0.4))
    P.add('Chest', (Z, -4 * sn(t - 0.08)), (Y, roll_front * 0.6), (X, lean * 0.4 + 1.2 * b2))
    neck(P, pitch=(-lean * 0.4 - 1.5 * b2, -1.0 * b2, 1.5 * cs(2 * t - 0.15)), yaw=(4 * sn(t - 0.12), 3 * sn(t - 0.18), 2 * sn(t - 0.24)))
    P.add('Jaw', (X, 3 + (6 if run else 0) * max(0, sn(2 * t))))
    tail(P, t, amp=7 if run else 5, lag=0.08, freq=1, lift=-2 if run else 0)
    for side, s in SIDES:
        P.add(side + 'Wing1', (Y, s * (-2 * b2 - (6 if run else 2))), (X, 2 * b2))
        P.add(side + 'Wing2', (Y, s * -2 * cs(2 * t - 0.12)))
        P.add(side + 'WingF1b', (Y, s * -3 * cs(2 * t - 0.25)))
    return P

def pose_attack(t):
    """mordida: antecipa (recolhe pescoço e abre a boca), avança num arco para baixo e fecha; garra da frente junto."""
    P = Pose()
    wind = win(t, 0.0, 0.34) * (1 - win(t, 0.36, 0.46))
    hit = win(t, 0.36, 0.46) * (1 - win(t, 0.68, 1.0))
    snap = win(t, 0.44, 0.5)
    P.move((0, M(0.06) * wind - M(0.16) * hit, M(0.04) * wind - M(0.05) * hit))
    P.add('Chest', (X, -6 * wind + 8 * hit)); P.add('Spine', (X, -3 * wind + 4 * hit))
    neck(P, pitch=(-22 * wind + 20 * hit, -16 * wind + 18 * hit, -14 * wind + 22 * hit), yaw=(4 * wind, 3 * wind, -4 * hit))
    P.add('Jaw', (X, 32 * wind * (1 - snap) + 30 * (hit * (1 - snap)) + 4))
    leg(P, 'Left', 'Front', -30 * wind + 18 * hit, 0.9 * wind)
    tail(P, t, amp=4, lag=0.1, yaw=-10 * wind + 12 * hit)
    wings_folded(P, open_=0.55 * wind + 0.2 * hit)
    return P

def pose_cast(t):
    """sopro: ergue a cabeça e o peito puxando ar (antecipação), abre as asas, baixa a cabeça e solta o sopro com a boca aberta."""
    P = Pose()
    up = win(t, 0.0, 0.32) * (1 - win(t, 0.38, 0.5))
    blow = win(t, 0.38, 0.5) * (1 - win(t, 0.82, 1.0))
    P.move((0, M(0.05) * up - M(0.06) * blow, M(0.10) * up))
    P.add('Hips', (X, 6 * up)); P.add('Spine', (X, -6 * up + 2 * blow)); P.add('Chest', (X, -10 * up + 4 * blow))
    neck(P, pitch=(-24 * up + 14 * blow, -12 * up + 10 * blow, -14 * up + 16 * blow), yaw=(0, 0, 3 * sn(4 * t) * blow))
    P.add('Jaw', (X, 6 * up + 34 * blow))
    for side, s in SIDES: leg(P, side, 'Front', -12 * up + 6 * blow, 0.4 * up)
    tail(P, t, amp=5, lag=0.1, lift=6 * up)
    wings_folded(P, open_=0.9 * max(up, blow), breathe=sn(6 * t) * blow * 0.6)
    return P

def pose_roar(t):
    """rugido: recua, ergue o pescoço, abre bem a boca e as asas, treme; volta."""
    P = Pose()
    a = win(t, 0.0, 0.25) * (1 - win(t, 0.8, 1.0)); shake = sn(9 * t) * a
    P.move((0, M(0.08) * a, M(0.06) * a))
    P.add('Chest', (X, -12 * a)); P.add('Spine', (X, -5 * a))
    neck(P, pitch=(-26 * a, -10 * a, 8 * a + 2 * shake), yaw=(0, 2 * shake, 3 * shake))
    P.add('Jaw', (X, 40 * a))
    wings_folded(P, open_=1.0 * a, breathe=0.8 * shake)
    tail(P, t, amp=6 * a + 2, lag=0.08, freq=2, lift=4 * a)
    return P

def pose_hit(t):
    k = math.exp(-((t - 0.2) / 0.16) ** 2)
    P = Pose()
    P.move((0, M(0.06) * k, -M(0.02) * k))
    P.add('Chest', (X, 6 * k), (Z, 5 * k)); neck(P, pitch=(10 * k, 8 * k, 6 * k), yaw=(-8 * k, -6 * k, -8 * k))
    P.add('Jaw', (X, 18 * k))
    wings_folded(P, open_=0.3 * k)
    tail(P, t, amp=6 * k, lag=0.1, freq=2)
    return P

def pose_death(t):
    buckle = win(t, 0.0, 0.3); fall = win(t, 0.25, 0.7); settle = win(t, 0.7, 1.0)
    P = Pose()
    P.move((0, 0, -M(0.20) * fall))
    P.add('Hips', (Y, 18 * fall)); P.add('Spine', (Y, 8 * fall)); P.add('Chest', (Y, 10 * fall))
    for side, s in SIDES:
        leg(P, side, 'Front', -10 * buckle + 30 * fall, 0.8 * buckle)
        leg(P, side, 'Back', 20 * fall, 0.6 * buckle)
    neck(P, pitch=(14 * fall, 18 * fall, 10 * fall - 4 * settle), yaw=(16 * fall, 12 * fall, 10 * fall))
    P.add('Jaw', (X, 20 * fall - 10 * settle))
    for side, s in SIDES:
        P.add(side + 'Wing1', (Y, s * (-30 * fall * (1 if s > 0 else -0.4)))); P.add(side + 'Wing2', (Y, s * 10 * fall))
    for i, n in enumerate(TAIL_NAMES): P.add(n, (Z, 7 * fall), (X, 2 * fall))
    return P

# ---------------------------------------------------------------- voo
def flap(P, ph, amp=1.0, base=0.0, glide=0.0, ext=34.0):
    """uma batida de asa (ph 0..1): descida rápida (0..0.42) com a asa toda aberta; subida mais lenta
    com o pulso dobrado e os dedos recolhidos (menos arrasto), e a ponta atrasada (chicotada)."""
    # ângulo do braço: senoide assimétrica (desce em 42% do ciclo, sobe em 58%)
    u = ph % 1.0
    arm = math.cos(math.pi * u / 0.42) if u < 0.42 else -math.cos(math.pi * (u - 0.42) / 0.58)   # +1 alto -> -1 baixo -> +1
    up = max(0.0, (u - 0.42) / 0.58) if u >= 0.42 else 0.0
    fold = math.sin(math.pi * up) * (1 - glide)                       # dobra no meio da subida
    tipd = math.cos(TAU * (u - 0.1))                                  # ponta atrasada
    # ext: no voo, o antebraço e o dedo maior se esticam para fora (no modelo eles vêm dobrados para baixo)
    for side, s in SIDES:
        P.add(side + 'Wing1', (Y, s * (base - 36 * amp * arm * (1 - glide * 0.85))), (Z, s * (-14 * fold)), (X, -6 * fold))
        P.add(side + 'Wing2', (Y, s * (-12 - ext * 0.35 - 10 * amp * tipd * (1 - glide))), (Z, s * 26 * fold))
        P.add(side + 'WingF1a', (Y, s * (-ext * 0.6 - 10 * amp * tipd)), (Z, s * 14 * fold))
        P.add(side + 'WingF1b', (Y, s * (-ext * 0.7 - 12 * amp * math.cos(TAU * (u - 0.18)))), (Z, s * 10 * fold))
        P.add(side + 'WingF2', (Z, s * 16 * fold), (Y, s * -6 * tipd))
        P.add(side + 'WingF3', (Z, s * 10 * fold))
    return arm

def pose_fly_idle(t):
    """pairando: corpo inclinado de nariz para cima, duas batidas fortes por ciclo; a cada descida o corpo sobe
    (e afunda na subida); patas penduradas balançando com atraso; cauda de leme."""
    P = Pose()
    ph = (2 * t) % 1.0
    arm = flap(P, ph, amp=1.0, base=24)
    lift = -arm
    heave = math.sin(TAU * (ph - 0.12))   # o corpo responde depois da asa
    P.move((0, 0, M(0.06) * -heave))
    P.add('Hips', (X, -22)); P.add('Spine', (X, -4 + 1.5 * heave)); P.add('Chest', (X, -5 + 2 * heave))
    neck(P, pitch=(8 - 3 * heave, 2 - 2 * heave, 6 + 2 * sn(t)), yaw=(4 * sn(t), 3 * sn(t - 0.1), 4 * sn(t - 0.2)))
    P.add('Jaw', (X, 4))
    for side, s in SIDES:
        sw = 6 * math.sin(TAU * (ph - 0.25))
        P.add(f'Front{side}Upper', (X, -16 + sw)); P.add(f'Front{side}Lower', (X, -34 + sw * 0.6)); P.add(f'Front{side}Foot', (X, 28))
        P.add(f'Back{side}Upper', (X, 16 + sw * 0.7)); P.add(f'Back{side}Lower', (X, 8 + sw * 0.5)); P.add(f'Back{side}Foot', (X, 34))
    for i, n in enumerate(TAIL_NAMES):
        P.add(n, (X, 4 + 3 * math.sin(TAU * (ph - 0.1 * i))), (Z, 5 * math.sin(TAU * (t - 0.08 * i))))
    return P

def pose_fly(t):
    """voando para a frente: corpo esticado e horizontal, batidas mais largas e mais lentas com um trecho de planeio
    (asas abertas paradas) a cada ciclo; patas recolhidas; a cauda dá estabilidade (onda pequena)."""
    P = Pose()
    # 1 batida forte + meio ciclo de planeio: a batida acontece em 0..0.6, o resto é planeio com as asas abertas
    if t < 0.6:
        ph = t / 0.6; g = 0.0
    else:
        ph = 0.0; g = math.sin(math.pi * (t - 0.6) / 0.4)
    arm = flap(P, ph, amp=1.05, base=26, glide=g if t >= 0.6 else 0.0)
    heave = math.sin(TAU * (ph - 0.12)) if t < 0.6 else 0.0
    P.move((0, 0, M(0.05) * -heave))
    P.add('Hips', (X, -2 + 2 * heave)); P.add('Spine', (X, -1.5 * heave)); P.add('Chest', (X, -3 - 2 * heave))
    neck(P, pitch=(6, 2, 4 + 3 * heave), yaw=(3 * sn(t), 2 * sn(t - 0.1), 3 * sn(t - 0.2)))
    P.add('Jaw', (X, 3))
    for side, s in SIDES:
        P.add(f'Front{side}Upper', (X, 26)); P.add(f'Front{side}Lower', (X, -48)); P.add(f'Front{side}Foot', (X, 34))
        P.add(f'Back{side}Upper', (X, 32)); P.add(f'Back{side}Lower', (X, -10)); P.add(f'Back{side}Foot', (X, 40))
    for i, n in enumerate(TAIL_NAMES):
        P.add(n, (X, -2 + 1.5 * math.sin(TAU * (t - 0.1 * i))), (Z, 4 * math.sin(TAU * (t - 0.09 * i))))
    return P

def bake(arm, name, fn, frames, loop=True):
    act = lib.new_action(arm, name)
    for f in range(frames + 1):     # quadro a quadro
        t = f / frames
        P = fn(t % 1.0 if loop else t)
        lib.key_pose(arm, f + 1, P.r, P.loc)
    lib.push_nla(arm, act)

def build_animations(arm):
    bpy.context.scene.render.fps = FPS
    bake(arm, 'idle', pose_idle, 150)                               # 5 s
    bake(arm, 'walk', lambda t: pose_walk(t, False), 48)           # 1,6 s por passada
    bake(arm, 'run', lambda t: pose_walk(t, True), 24)
    bake(arm, 'attack', pose_attack, 34, loop=False)
    bake(arm, 'cast', pose_cast, 54, loop=False)
    bake(arm, 'roar', pose_roar, 60, loop=False)
    bake(arm, 'hit', pose_hit, 20, loop=False)
    bake(arm, 'death', pose_death, 64, loop=False)
    bake(arm, 'fly_idle', pose_fly_idle, 36)                       # 2 batidas em 1,2 s
    bake(arm, 'fly', pose_fly, 48)                                 # batida + planeio em 1,6 s

def main():
    global SCALE
    bpy.ops.wm.open_mainfile(filepath=SRC)
    obj = bpy.data.objects['dragao_src']; obj.name = 'SM_Dragao'
    raw = [tuple(v.co) for v in obj.data.vertices]
    co = np.array(raw)
    SCALE = MIN_SIDE / min(np.ptp(co[:, 0]), np.ptp(co[:, 2]))
    for v in obj.data.vertices: v.co = T(*v.co)
    obj.data.update()
    co = np.array([v.co[:] for v in obj.data.vertices])
    print('escala %.3f -> envergadura %.2f m, comprimento %.2f m, altura %.2f m' % (SCALE, np.ptp(co[:, 0]), np.ptp(co[:, 1]), np.ptp(co[:, 2])))
    arm = build_rig()
    cls = assign(obj, arm, raw)
    smooth_weights(obj, cls)
    lib.bind(obj, arm)
    mat = obj.active_material; mat.name = 'MAT_Dragao'
    mat['ramp'] = 'soft'; mat['rim'] = 0.45; mat['noOutline'] = True
    bsdf = [n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'][0]
    for inp in ('Metallic', 'Roughness'):
        for l in list(bsdf.inputs[inp].links): mat.node_tree.links.remove(l)
    bsdf.inputs['Metallic'].default_value = 0.0; bsdf.inputs['Roughness'].default_value = 0.7
    for img in bpy.data.images:
        if img.size[0] > 2048: img.scale(2048, 2048)
    if os.environ.get('SO_RIG'):
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT, 'fontes', 'blender', 'dragao_veu_rig.blend')); return
    build_animations(arm)
    os.makedirs(OUT, exist_ok=True)
    for o in bpy.context.scene.objects: o.select_set(o in (obj, arm))
    bpy.ops.export_scene.gltf(
        filepath=os.path.join(OUT, 'char_dragao_negro.glb'), export_format='GLB', use_selection=True,
        export_extras=True, export_animations=True, export_animation_mode='NLA_TRACKS', export_force_sampling=True,
        export_skins=True, export_def_bones=False, export_image_format='JPEG', export_jpeg_quality=88)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT, 'fontes', 'blender', 'dragao_veu_rig.blend'))

if __name__ == '__main__':
    main()
