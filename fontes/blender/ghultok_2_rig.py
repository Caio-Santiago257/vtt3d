"""Etapa 2 do Ghult'ok (orc bárbaro): escala, esqueleto, pesos, animações e exportação.

Entrada: fontes/blender/ghultok_reduzido.blend (etapa 1).
Saída:   public/assets/characters/ghultok/char_ghultok.glb

Skills (blender-skills): blender-director (plano), character-artist (proporções de um orc pesado), rigging
(esqueleto humanoide com ossos extras de tanga, franjas e cabelo; até 4 influências por vértice; mãos soltas
das franjas) e animation (andar pesado com contato/descida/passagem/subida, sobreposição e laço sem emenda).

Mesmos nomes de ossos da Kaira e do Guy, para o jogo tratar todos do mesmo jeito.
"""
import math, os, sys
import numpy as np
import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib
from kaira import Pose, X, Y, Z
from guy_2_rig import smooth_weights, skin_mask, sn, cs, smooth, clamp01, win

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
SRC = os.path.join(ROOT, 'fontes', 'blender', 'ghultok_reduzido.blend')
OUT = os.path.join(ROOT, 'public', 'assets', 'characters', 'ghultok')
os.makedirs(OUT, exist_ok=True)

HEIGHT = float(os.environ.get('ALTURA', '2.1'))        # orc grande: 2,1 m
RAW_FLOOR, RAW_AXIS_Y, RAW_TOP = -0.954, -0.02, 0.95
SCALE = HEIGHT / (RAW_TOP - RAW_FLOOR)
def T(x, y, z): return Vector((x * SCALE, (y - RAW_AXIS_Y) * SCALE, (z - RAW_FLOOR) * SCALE))

J = {
    'hips': (0, 0.0, -0.02), 'spine': (0, 0.0, 0.14), 'spine1': (0, 0.0, 0.30), 'spine2': (0, 0.0, 0.44),
    'neck0': (0, -0.05, 0.60), 'neck1': (0, -0.10, 0.665), 'headtop': (0, -0.11, 0.92),
    'clav': (0.08, -0.02, 0.56), 'sh': (0.33, -0.06, 0.48), 'el': (0.40, -0.15, 0.22), 'wr': (0.44, -0.14, -0.02), 'hand': (0.46, -0.12, -0.15),
    'hip': (0.15, 0.0, -0.08), 'knee': (0.205, -0.03, -0.42), 'ankle': (0.25, -0.02, -0.84), 'ball': (0.26, -0.20, -0.92), 'toe': (0.265, -0.33, -0.945),
}
def jp(n, s=1):
    x, y, z = J[n]; return T(x * s, y, z)

def build_rig():
    ad = bpy.data.armatures.new('ARM_Ghultok'); arm = lib.link(bpy.data.objects.new('ARM_Ghultok', ad))
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
    bone('Hair1', T(0, -0.04, 0.86), T(0, -0.03, 0.95), 'Head')                       # coque no alto da cabeça
    pts = [T(0, 0.10, 0.70), T(0, 0.24, 0.42), T(0, 0.32, 0.12), T(0, 0.38, -0.20)]  # cabelo comprido nas costas
    for i in range(3): bone(f'BackHair{i + 1}', pts[i], pts[i + 1], 'Head' if i == 0 else f'BackHair{i}', i > 0)
    for s, P in ((1, 'Left'), (-1, 'Right')):
        sh, el, wr, hd = jp('sh', s), jp('el', s), jp('wr', s), jp('hand', s)
        d = (hd - wr).normalized()
        bone(P + 'Shoulder', jp('clav', s), sh, 'Spine2')
        bone(P + 'Arm', sh, el, P + 'Shoulder', True)
        bone(P + 'ForeArm', el, wr, P + 'Arm', True)
        bone(P + 'Hand', wr, hd, P + 'ForeArm', True)
        for n, a, b_ in (('HandIndex1', 0.0, 0.5), ('HandIndex2', 0.5, 1.0), ('HandFingers1', 0.0, 0.5), ('HandFingers2', 0.5, 1.0), ('HandThumb1', 0.0, 0.5), ('HandThumb2', 0.5, 1.0)):
            parent = P + ('Hand' if n.endswith('1') else n[:-1] + '1')
            bone(P + n, hd + d * 0.03 * a, hd + d * 0.03 * b_ + Vector((0, 0, -0.001)), parent, n.endswith('2'), deform=False)
        bone(P + 'UpLeg', jp('hip', s), jp('knee', s), 'Hips')
        bone(P + 'Leg', jp('knee', s), jp('ankle', s), P + 'UpLeg', True)
        bone(P + 'Foot', jp('ankle', s), jp('ball', s), P + 'Leg', True)
        bone(P + 'ToeBase', jp('ball', s), jp('toe', s), P + 'Foot', True)
    # tanga da frente, pano de trás e franjas de pelo dos lados: três ossos cada
    for tag, top, bot in (('F', (0.05, -0.27, 0.10), (0.06, -0.30, -0.62)), ('B', (0, 0.20, 0.10), (0, 0.30, -0.45)),
                          ('L', (0.34, 0.0, 0.05), (0.46, 0.02, -0.32)), ('R', (-0.34, 0.0, 0.05), (-0.47, 0.02, -0.32))):
        a, b_ = Vector(top), Vector(bot)
        p = [T(*(a + (b_ - a) * k)) for k in (0, 1 / 3, 2 / 3, 1)]
        for i in range(3): bone(f'Skirt{tag}{i + 1}', p[i], p[i + 1], 'Hips' if i == 0 else f'Skirt{tag}{i}', i > 0)
    bone('socket_hand_r', jp('hand', -1), jp('hand', -1) + Vector((0, 0, -0.04)), 'RightHand', deform=False)
    bone('socket_hand_l', jp('hand', 1), jp('hand', 1) + Vector((0, 0, -0.04)), 'LeftHand', deform=False)
    bone('socket_back', T(0, 0.12, 0.35), T(0, 0.12, 0.45), 'Spine2', deform=False)
    bone('socket_head', jp('headtop'), jp('headtop') + Vector((0, 0, 0.04)), 'Head', deform=False)
    bpy.ops.object.mode_set(mode='OBJECT')
    return arm

def red_mask(obj):
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
    return (c[:, 0] > 0.42) & (c[:, 0] - c[:, 1] > 0.22) & (c[:, 0] - c[:, 2] > 0.2)

UPPER = ['Hips', 'Spine', 'Spine1', 'Spine2', 'Neck'] + [p + n for p in ('Left', 'Right') for n in ('Shoulder', 'Arm', 'ForeArm', 'Hand')]
def classify(v, x, y, z, segs, skin, force, red):
    ax = abs(x); S = 'Left' if x > 0 else 'Right'
    dh = lib.seg_dist(v.co, *segs[S + 'Hand']); df = lib.seg_dist(v.co, *segs[S + 'ForeArm'])
    u = SCALE / 0.53   # as distâncias abaixo foram pensadas em metros de 1 m; converte
    if force is not None and force[v.index]: return force[v.index]
    if ax > 0.36 and -0.25 < z < 0.04 and ((skin[v.index] and dh < 0.045 * u) or df < 0.02 * u):
        return 'mao'
    if z > 0.62 and y < 0.14: return 'topo' if z > 0.86 and ax < 0.09 else 'cabeca'
    if y > 0.13 and -0.3 < z <= 0.72 and ax < 0.3: return 'costas'
    # a capa de pelo das costas desce pelos lados, atrás dos braços: fica com as costas, não com o braço
    if ax >= 0.3 and y > 0.06 and -0.32 < z < 0.6 and not skin[v.index]: return 'costas'
    da = lib.seg_dist(v.co, *segs[S + 'Arm'])
    if ax > 0.32 and -0.08 < z < 0.34 and min(df, da if z < 0.3 else 9) < 0.075 * u: return 'braco'   # braço abaixo do manto, bracelete e punho
    if z > 0.08: return 'tronco'
    # panos soltos: pela cor (vermelho) ou por estarem bem afastados do corpo — a frente das coxas e o
    # traseiro também ficam à frente/atrás, e não podem seguir a tanga (senão esticam quando a perna anda)
    if z > -0.66 and y < -0.12 and (red[v.index] or (y < -0.27 and ax < 0.22 and z > -0.3)): return 'tangaF'
    if z > -0.6 and y > 0.12 and (red[v.index] or (y > 0.24 and z > -0.3)): return 'tangaB'
    if ax > 0.39 and z > -0.40: return 'franja'
    if z < -0.45 and ax < 0.12 and y < -0.12: return 'tangaF'      # ponta da tanga entre as pernas
    if z < -0.40 and ax < 0.11 and y > 0.06: return 'tangaB'       # ponta do pano de trás entre as pernas
    if z < -0.45: return 'perna'
    return 'quadril'

def assign(obj, arm, raw, skin, force=None):
    red = red_mask(obj)
    segs = {b.name: (b.head_local.copy(), b.tail_local.copy()) for b in arm.data.bones if b.use_deform}
    for n in segs: obj.vertex_groups.new(name=n)
    stats = {}; out = []
    for v, (x, y, z) in zip(obj.data.vertices, raw):
        cls = classify(v, x, y, z, segs, skin, force, red); S = 'Left' if x > 0 else 'Right'
        cand = {
            'cabeca': ['Head', 'Neck'], 'topo': ['Head', 'Hair1'],
            'costas': ['Spine1', 'Spine2', 'Neck', 'Head', 'BackHair1', 'BackHair2', 'BackHair3', 'LeftShoulder', 'RightShoulder'],
            'mao': [S + 'ForeArm', S + 'Hand'], 'tronco': UPPER, 'braco': [S + 'Arm', S + 'ForeArm', S + 'Hand'],
            'tangaF': ['Hips', 'SkirtF1', 'SkirtF2', 'SkirtF3'], 'tangaB': ['Hips', 'SkirtB1', 'SkirtB2', 'SkirtB3'],
            'franja': ['Hips', S + 'UpLeg'] + [f'Skirt{S[0]}{i}' for i in (1, 2, 3)],
            'perna': [S + 'UpLeg', S + 'Leg', S + 'Foot', S + 'ToeBase'],
            'quadril': ['Hips', 'Spine', 'LeftUpLeg', 'RightUpLeg', 'LeftLeg', 'RightLeg'],
        }[cls]
        if cls == 'tronco' and z < 0.22:
            # cinto e barriga ficam com o corpo; o que está do lado de fora do corpo (pelo do braço) fica com o braço
            cand = ['Hips', 'Spine', 'Spine1'] if (abs(x) < 0.35 or y > 0.0) else [S + 'Shoulder', S + 'Arm', S + 'ForeArm', S + 'Hand']
        sig = {'tronco': 0.022, 'quadril': 0.03, 'costas': 0.045, 'franja': 0.045, 'tangaF': 0.045, 'tangaB': 0.045}.get(cls, 0.03) * SCALE / 0.53
        bias = {'Head': 0.75, 'Spine2': 0.9, 'Hips': 1.4 if cls in ('tangaF', 'tangaB', 'franja') else 1.0,
                'LeftUpLeg': 0.9 if cls == 'quadril' else 1.6, 'RightUpLeg': 0.9 if cls == 'quadril' else 1.6}
        ds = [(lib.seg_dist(v.co, *segs[n]) * bias.get(n, 1.0), n) for n in cand]
        dmin = min(d for d, _ in ds)
        for d, n in ds:
            w = math.exp(-((d - dmin) / sig) ** 2)
            if w > 0.01: obj.vertex_groups[n].add([v.index], w, 'REPLACE')
        stats[cls] = stats.get(cls, 0) + 1; out.append(cls)
    print('classes:', stats)
    return out

# ================================================================ animações
FPS = 30; TAU = 2 * math.pi

def arms(P, swing=(0.0, 0.0), elbow=(-14.0, -14.0), out=(0.0, 0.0), hand=(0.0, 0.0), twist=(0.0, 0.0)):
    """swing negativo = para a frente; elbow negativo = dobra; out positivo = abre para o lado."""
    for k, s in enumerate((1, -1)):
        P.side(s, 'Arm', (Y, out[k]), (X, swing[k]))
        P.side(s, 'ForeArm', (X, elbow[k]), (Z, twist[k]))
        P.side(s, 'Hand', (X, hand[k]))

def flaps(P, f=0.0, b=0.0, l=0.0, r=0.0, wave=0.0):
    for i in (1, 2, 3):
        k = (0.45, 0.8, 1.0)[i - 1]; w = wave * (i - 1) * 0.5
        P.add(f'SkirtF{i}', (X, -(f * k + w))); P.add(f'SkirtB{i}', (X, b * k + w))
        P.add(f'SkirtL{i}', (Y, l * k + w * 0.5)); P.add(f'SkirtR{i}', (Y, -(r * k + w * 0.5)))

def hair(P, t, base=0.0, amp=3.0, freq=1.0, lag=0.12):
    for i in (1, 2, 3): P.add(f'BackHair{i}', (X, base * (0.5 + 0.3 * i) + amp * (0.6 + 0.3 * i) * sn(freq * t - lag * i)), (Z, amp * 0.5 * sn(freq * t * 0.5 - lag * i)))
    P.add('Hair1', (X, amp * 0.8 * sn(freq * t - 0.2)))

def pose_idle(t):
    """respiração funda e lenta (o peito largo sobe), peso trocando de perna, ombros soltos, olhar de vigia."""
    P = Pose()
    br = sn(2 * t); sh = sn(t); look = sn(t + 0.1)
    P.move('Hips', (0.012 * sh, 0, -0.004 + 0.004 * br))
    P.add('Hips', (Y, 2.4 * sh), (Z, 1.6 * sn(t - 0.1)))
    P.add('Spine', (Y, -1.4 * sh), (X, -1.0 * br)); P.add('Spine1', (Y, -0.8 * sh), (X, -1.8 * br)); P.add('Spine2', (X, -1.6 * br))
    P.add('Neck', (X, 1.0 * br), (Z, 3 * look)); P.add('Head', (Z, 7 * sn(t + 0.05)), (X, 1 + 1.5 * sn(2 * t + 0.3)), (Y, -1.5 * sh))
    for s in (1, -1):
        P.side(s, 'Shoulder', (X, -1.2 * br), (Y, 1.4 * br))
        P.side(s, 'UpLeg', (Y, -2.2 * sh * s), (X, -1.5 - 1.5 * s * sh))
        P.side(s, 'Leg', (X, 4 + 3 * s * sh)); P.side(s, 'Foot', (X, -2 - 1.5 * s * sh))
    arms(P, swing=(-4 + 1.5 * sn(t + 0.2), -4 - 1.5 * sn(t + 0.2)), elbow=(-18 + 3 * br, -18 + 3 * br), out=(4 + 1.5 * br, 4 + 1.5 * br))
    hair(P, t, amp=1.5, freq=2, lag=0.15)
    flaps(P, f=0.8 * br, b=0.8 * br, l=1.5 * sh, r=-1.5 * sh)
    return P

def leg(ph, stride, knee_max, lift, push, absorb=16):
    """apoio (0..0.5): calcanhar toca à frente, o joelho cede bastante (absorve o peso) e estica; o pé rola até a ponta.
    balanço (0.5..1): joelho dobra, o pé sobe baixo (passo pesado, sem levantar muito) e volta à frente."""
    thigh = -stride * cs(ph)
    if ph < 0.5:
        u = ph / 0.5
        knee = absorb * math.sin(math.pi * min(1, u / 0.42)) * (1 - u * 0.8) + 5
        foot = -10 * (1 - smooth(clamp01(u / 0.16))) + push * smooth(clamp01((u - 0.6) / 0.4))
        toe = -push * 0.9 * smooth(clamp01((u - 0.65) / 0.35))
    else:
        u = (ph - 0.5) / 0.5
        knee = 7 + knee_max * math.sin(math.pi * u) ** 0.9
        foot = push * (1 - smooth(clamp01(u / 0.35))) + lift * math.sin(math.pi * u) - 10 * smooth(clamp01((u - 0.7) / 0.3))
        toe = -push * 0.9 * (1 - smooth(clamp01(u / 0.25)))
    return thigh, knee, foot, toe

def pose_move(t, run=False):
    """andar de orc bárbaro, refeito com calma (skill animation: contato, descida, passagem, subida, duas vezes por ciclo).
    Pesado mas limpo: o corpo desce logo depois de cada contato e sobe na passagem; o quadril vai para o lado da
    perna de apoio e gira com as pernas; tronco e ombros giram ao contrário com um pouco de atraso; a cabeça fica
    estável; braços balançam naturais, cotovelo e mão atrasados; cabelo e panos só acompanham (sem abrir para trás)."""
    P = Pose()
    stride = 34 if run else 22; knee_max = 85 if run else 50; lift = 16 if run else 8; push = 22 if run else 14
    lean = -12 if run else -2
    th = []
    for s, off in ((1, 0.0), (-1, 0.5)):
        ph = (t + off) % 1.0
        a, k, f, toe = leg(ph, stride, knee_max, lift, push, absorb=10 if run else 12)
        th.append(a)
        P.side(s, 'UpLeg', (X, a), (Y, -2.0 * s)); P.side(s, 'Leg', (X, k)); P.side(s, 'Foot', (X, f)); P.side(s, 'ToeBase', (X, toe))
    bounce = 0.5 + 0.5 * cs(2 * t - 0.14)
    drop = 0.04 if run else 0.022
    P.move('Hips', (0.014 * sn(t - 0.1), 0.0, -drop * bounce))
    P.add('Hips', (Z, 6 * cs(t)), (Y, 3.5 * sn(t)), (X, lean * 0.4 - 1.2 * bounce))
    P.add('Spine', (Z, -3.5 * cs(t - 0.04)), (X, lean * 0.25 + 0.8 * bounce), (Y, -1.6 * sn(t - 0.04)))
    P.add('Spine1', (Z, -3.5 * cs(t - 0.07)), (X, lean * 0.2 + 0.6 * bounce), (Y, -1.0 * sn(t - 0.07)))
    P.add('Spine2', (Z, -3.0 * cs(t - 0.1)), (X, lean * 0.15 + 0.5 * bounce))
    for s in (1, -1): P.side(s, 'Shoulder', (X, 2.5 * s * cs(t - 0.08)), (Y, -1.2 * bounce))
    P.add('Neck', (Z, 2.8 * cs(t - 0.12)), (X, -lean * 0.3)); P.add('Head', (Z, 3 * cs(t - 0.14)), (X, -lean * 0.4 - 1.0 * bounce), (Y, -1.0 * sn(t - 0.12)))
    aw = 12 if run else 16
    swL = aw * cs(t - 0.07); swR = -aw * cs(t - 0.07)
    elL = (-26 if run else -20) - 12 * max(0, -cs(t - 0.16)); elR = (-26 if run else -20) - 12 * max(0, cs(t - 0.16))
    arms(P, swing=(swL - (4 if run else 3), swR - (4 if run else 3)), elbow=(elL, elR), out=(7 + 1.5 * bounce, 7 + 1.5 * bounce),
         hand=(-3 + 4 * cs(t - 0.22), -3 - 4 * cs(t - 0.22)))
    lag = [leg((t - 0.07 + off) % 1.0, stride, knee_max, lift, push)[0] for off in (0.0, 0.5)]
    front = max(0.0, -lag[0], -lag[1]); back = max(0.0, lag[0], lag[1])
    flaps(P, f=2 + front * 0.5, b=(6 if run else 2) + back * 0.35, l=-lag[0] * 0.2 + 1.5 * bounce, r=-lag[1] * 0.2 + 1.5 * bounce, wave=2.5 * cs(2 * t - 0.3))
    hair(P, t, base=6 if run else 0, amp=3 if run else 1.6, freq=2, lag=0.14)
    return P

def pose_attack(t):
    """investida de ombro com cabeçada (o golpe do bárbaro). Os braços do modelo nascem colados no manto de pelo e
    as franjas das braçadeiras se misturam com as do quadril, então braço alto rasga a malha. O golpe vem do corpo
    inteiro: recua o peso e gira o tronco para trás, explode para a frente com o ombro e a cabeça, punhos cerrados
    junto ao corpo, e volta. Os braços mexem no máximo uns 25 graus."""
    P = Pose()
    wind = win(t, 0.0, 0.3) * (1 - win(t, 0.34, 0.44))
    hit = win(t, 0.34, 0.46) * (1 - win(t, 0.68, 1.0))
    P.move('Hips', (0, 0.05 * wind - 0.12 * hit, -0.04 * wind - 0.03 * hit))
    P.add('Hips', (Z, -10 * wind + 14 * hit), (X, -4 * wind + 6 * hit))
    P.add('Spine', (X, -4 * wind + 8 * hit))
    P.add('Spine1', (Z, -10 * wind + 12 * hit), (X, -6 * wind + 12 * hit)); P.add('Spine2', (Z, -6 * wind + 8 * hit), (X, -4 * wind + 8 * hit))
    P.add('Neck', (X, -6 * wind + 10 * hit)); P.add('Head', (X, -8 * wind + 16 * hit), (Z, 6 * wind - 8 * hit))
    for s in (1, -1):
        P.side(s, 'Arm', (X, 10 * wind - 14 * hit)); P.side(s, 'ForeArm', (X, -12 * wind - 20 * hit)); P.side(s, 'Hand', (X, -8 * (wind + hit)))
    P.side(1, 'UpLeg', (X, 10 * wind - 26 * hit)); P.side(1, 'Leg', (X, 14 * wind + 24 * hit)); P.side(1, 'Foot', (X, -8 * wind))
    P.side(-1, 'UpLeg', (X, -8 * wind + 18 * hit)); P.side(-1, 'Leg', (X, 16 * wind + 6 * hit))
    flaps(P, f=-3 * wind + 6 * hit, b=4 * wind + 6 * hit, wave=3 * hit)
    hair(P, t, base=6 * wind - 8 * hit, amp=3, freq=2)
    return P

def pose_cast(t):
    """grito de fúria (o 'cast' do bárbaro: a Fúria): encolhe juntando força, depois estufa o peito, joga a
    cabeça para trás e ruge, tremendo, com os ombros abertos e os punhos cerrados ao lado do corpo."""
    P = Pose()
    crouch = win(t, 0.0, 0.3) * (1 - win(t, 0.36, 0.5))
    roar = win(t, 0.36, 0.5) * (1 - win(t, 0.82, 1.0)); shake = sn(10 * t) * roar
    P.move('Hips', (0, 0.01 * roar, -0.07 * crouch - 0.015 * roar))
    P.add('Hips', (X, 6 * crouch)); P.add('Spine', (X, 6 * crouch - 4 * roar))
    P.add('Spine1', (X, 10 * crouch - 10 * roar)); P.add('Spine2', (X, 8 * crouch - 8 * roar + shake))
    P.add('Neck', (X, 6 * crouch - 8 * roar)); P.add('Head', (X, 10 * crouch - 16 * roar + 2 * shake))
    for s in (1, -1):
        P.side(s, 'Shoulder', (X, 4 * roar))
        P.side(s, 'Arm', (X, -10 * crouch + 6 * roar)); P.side(s, 'ForeArm', (X, -22 * crouch - 18 * roar + 2 * shake)); P.side(s, 'Hand', (X, -10 * (crouch + roar)))
        P.side(s, 'UpLeg', (X, -18 * crouch - 6 * roar)); P.side(s, 'Leg', (X, 32 * crouch + 10 * roar)); P.side(s, 'Foot', (X, -14 * crouch - 4 * roar))
    flaps(P, f=-3 * crouch + 4 * roar, b=3 * roar, wave=3 * shake)
    # o cabelo comprido cai com a gravidade: compensa a cabeça jogada para trás (senão a ponta varre o quadril)
    for i in (1, 2, 3): P.add(f'BackHair{i}', (X, (14 if i == 1 else 4) * roar))
    hair(P, t, base=0, amp=2 * roar + 1, freq=4)
    return P

def pose_hit(t):
    k = math.exp(-((t - 0.2) / 0.17) ** 2)
    P = Pose()
    P.move('Hips', (0, 0.04 * k, -0.02 * k))
    P.add('Spine', (X, 5 * k)); P.add('Spine1', (X, 9 * k)); P.add('Spine2', (X, 7 * k)); P.add('Neck', (X, 6 * k)); P.add('Head', (X, 12 * k), (Z, -8 * k))
    for s in (1, -1): P.side(s, 'UpLeg', (X, -8 * k)); P.side(s, 'Leg', (X, 14 * k))
    arms(P, swing=(-18 * k, -12 * k), elbow=(-18 - 40 * k, -18 - 30 * k), out=(12 * k, 12 * k))
    flaps(P, f=-6 * k, b=-4 * k, wave=4 * k)
    hair(P, t, base=-6 * k, amp=2, freq=2)
    return P

def pose_death(t):
    buckle = win(t, 0.0, 0.32); fall = win(t, 0.28, 0.66); settle = win(t, 0.64, 0.78) * (1 - win(t, 0.78, 1.0))
    P = Pose()
    for s in (1, -1):
        P.side(s, 'UpLeg', (X, -55 * buckle + 36 * fall), (Y, -6 * fall))
        P.side(s, 'Leg', (X, 100 * buckle - 76 * fall)); P.side(s, 'Foot', (X, 20 * fall))
    P.add('Spine1', (X, 16 * buckle - 6 * fall)); P.add('Head', (X, 14 * buckle - 4 * settle), (Z, 25 * fall))
    P.add('Hips', (X, 82 * fall), (Z, 8 * fall))
    P.move('Hips', (0, 0.14 * fall, -0.34 * buckle - 0.5 * fall + 0.015 * settle))
    arms(P, swing=(-10 - 40 * fall, -10 - 30 * fall), elbow=(-18 - 30 * buckle + 30 * fall, -18 - 20 * buckle + 20 * fall), out=(20 * fall, 30 * fall))
    flaps(P, f=-25 * fall, b=-30 * fall)
    hair(P, t, base=-15 * fall, amp=1)
    return P

def bake(arm, name, fn, frames, loop=True):
    act = lib.new_action(arm, name)
    for f in range(frames + 1):
        t = f / frames
        P = fn(t % 1.0 if loop else t)
        lib.key_pose(arm, f + 1, P.r, P.loc)
    lib.push_nla(arm, act)

def build_animations(arm):
    bpy.context.scene.render.fps = FPS
    bake(arm, 'idle', pose_idle, 120)                       # 4 s
    bake(arm, 'walk', lambda t: pose_move(t, False), 30)    # passada pesada de 1 s
    bake(arm, 'run', lambda t: pose_move(t, True), 20)
    bake(arm, 'attack', pose_attack, 28, loop=False)
    bake(arm, 'cast', pose_cast, 48, loop=False)
    bake(arm, 'hit', pose_hit, 18, loop=False)
    bake(arm, 'death', pose_death, 50, loop=False)

def main():
    bpy.ops.wm.open_mainfile(filepath=SRC)
    obj = bpy.data.objects['ghultok_src']; obj.name = 'SM_Ghultok'
    for poly in obj.data.polygons: poly.use_smooth = True   # sombreado suave (facetado parecia serrilhado)
    raw = [tuple(v.co) for v in obj.data.vertices]
    for v in obj.data.vertices: v.co = T(*v.co)
    obj.data.update()
    arm = build_rig()
    cls = assign(obj, arm, raw, skin_mask(obj))
    # O modelo recebido vem com os panos e o cabelo grudados no corpo (mesmas arestas): a mão na franja, a tanga
    # nas coxas, o cabelo comprido no traseiro. Cada parte solta precisa ser separada das outras, senão o pano
    # estica junto com a perna. Cada face fica com a classe da maioria dos seus vértices e as arestas entre
    # classes que se mexem diferente são cortadas; depois os pesos são refeitos na malha separada.
    import bmesh
    SOLTO = {'mao': None, 'costas': {'quadril', 'perna', 'tangaB', 'franja', 'tronco', 'braco'}, 'tangaF': {'quadril', 'perna', 'franja', 'braco'},
             'tangaB': {'quadril', 'perna', 'franja', 'braco'}, 'franja': {'quadril', 'perna', 'mao', 'braco', 'tronco'},
             'braco': {'quadril', 'perna', 'franja', 'tangaF', 'tangaB', 'costas', 'tronco'}}
    def separa(a, b):
        if a == b: return False
        if 'mao' in (a, b): return True
        return (a in SOLTO and b in SOLTO[a]) or (b in SOLTO and a in SOLTO[b])
    bm = bmesh.new(); bm.from_mesh(obj.data)
    fcls = {}
    for f in bm.faces:
        cnt = {}
        for v in f.verts: cnt[cls[v.index]] = cnt.get(cls[v.index], 0) + 1
        fcls[f.index] = max(cnt, key=cnt.get)
    cut = [e for e in bm.edges if len(e.link_faces) == 2 and separa(fcls[e.link_faces[0].index], fcls[e.link_faces[1].index])]
    bmesh.ops.split_edges(bm, edges=cut)
    bm.verts.index_update(); bm.verts.ensure_lookup_table()   # os vértices novos do corte precisam de índice
    force = [None] * len(bm.verts)
    for v in bm.verts:   # cada vértice fica com a classe da maioria das suas faces (assim uma face não mistura partes soltas)
        cnt = {}
        for f in v.link_faces: cnt[fcls[f.index]] = cnt.get(fcls[f.index], 0) + 1
        if cnt: force[v.index] = max(cnt, key=cnt.get)
    bm.to_mesh(obj.data); bm.free(); obj.data.update()
    print('arestas cortadas entre partes soltas:', len(cut))
    for g in list(obj.vertex_groups): obj.vertex_groups.remove(g)
    raw = [(v.co.x / SCALE, v.co.y / SCALE + RAW_AXIS_Y, v.co.z / SCALE + RAW_FLOOR) for v in obj.data.vertices]
    cls = assign(obj, arm, raw, skin_mask(obj), force)
    NOMES = sorted(set(cls)); at = obj.data.attributes.new('classe', 'INT', 'POINT'); at.data.foreach_set('value', [NOMES.index(c) for c in cls]); obj['classes'] = ','.join(NOMES)
    smooth_weights(obj, ['quadril' if c == 'perna' else c for c in cls], radius=0.035)   # coxa e perna suavizadas juntas
    lib.bind(obj, arm)
    mat = obj.active_material; mat.name = 'MAT_Ghultok'
    mat['ramp'] = 'soft'; mat['rim'] = 0.25; mat['noOutline'] = True
    bsdf = [n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'][0]
    for inp in ('Metallic', 'Roughness'):
        for l in list(bsdf.inputs[inp].links): mat.node_tree.links.remove(l)
    bsdf.inputs['Metallic'].default_value = 0.0; bsdf.inputs['Roughness'].default_value = 0.8
    for img in bpy.data.images:
        if img.size[0] > 2048: img.scale(2048, 2048)
    build_animations(arm)
    for o in bpy.context.scene.objects: o.select_set(o in (obj, arm))
    bpy.ops.export_scene.gltf(
        filepath=os.path.join(OUT, 'char_ghultok.glb'), export_format='GLB', use_selection=True,
        export_extras=True, export_animations=True, export_animation_mode='NLA_TRACKS', export_force_sampling=True,
        export_skins=True, export_def_bones=False, export_image_format='JPEG', export_jpeg_quality=88)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT, 'fontes', 'blender', 'ghultok_rig.blend'))

if __name__ == '__main__':
    main()
