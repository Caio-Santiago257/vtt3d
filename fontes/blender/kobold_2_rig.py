"""Etapa 2 do Kobold (guerreiro kobold, monstro): escala, esqueleto, pesos, animações e exportação.

Entrada: fontes/blender/kobold_reduzido.blend (etapa 1: o modelo recebido do Meshy reduzido para 80 mil triângulos).
Saída:   public/assets/characters/kobold/char_kobold.glb

O modelo é uma peça só (escamas, chifres, cintos, tanga amarela, adagas na cintura) e sem esqueleto.
Esqueleto (mesmos nomes de ossos dos outros personagens, para o jogo tratar igual):
  - coluna, pescoço em duas partes (o pescoço do kobold é longo e curvo) e cabeça, com a mandíbula separada (Jaw)
  - braços com mão e garras
  - pernas digitígradas: coxa (UpLeg), canela (Leg), o "tornozelo alto" com o metatarso comprido (Foot) e os dedos (ToeBase)
  - cauda em cinco ossos (Tail1..Tail5), que dá o contrapeso do corpo
  - tanga em dois painéis (frente e trás) com dois ossos cada (SkirtF*, SkirtB*)
Partes que encostam umas nas outras no modelo (braço na cintura, tanga nas coxas, cauda nas pernas) são cortadas
antes dos pesos, para uma não esticar a outra.

Animações (30 quadros por segundo, amostradas quadro a quadro, com atraso de cada parte em relação à anterior):
  idle    agachado e alerta: respira, olha para os lados aos trancos (como um réptil), a cauda ondula, as garras abrem e
          fecham e de vez em quando arreganha os dentes
  walk    passada digitígrada de bicho pequeno: corpo inclinado à frente, cauda balançando ao contrário do quadril
  run     corrida baixa, quase rente ao chão, cauda esticada para trás, braços para trás
  attack  garrada: encolhe, salta à frente com a mão direita em arco e morde no fim
  cast    grito de guerra: estufa o peito, abre os braços e a boca e sacode a cauda
  hit     tranco para trás com a cabeça encolhida
  death   cambaleia, cai de lado e a cauda bate no chão por último
"""
import math, os, sys
import numpy as np
import bpy, bmesh
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib
from kaira import Pose, X, Y, Z
from guy_2_rig import smooth_weights

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
SRC = os.path.join(ROOT, 'fontes', 'blender', 'kobold_reduzido.blend')
OUT = os.path.join(ROOT, 'public', 'assets', 'characters', 'kobold')
os.makedirs(OUT, exist_ok=True)

# ---------------------------------------------------------------- normalização
HEIGHT = float(os.environ.get('ALTURA', '1.2'))       # kobold (Pequeno): 1,2 m até a ponta dos chifres
RAW_FLOOR, RAW_TOP, RAW_AXIS_Y = -0.952, 0.951, 0.0
SCALE = HEIGHT / (RAW_TOP - RAW_FLOOR)
def T(x, y, z): return Vector((x * SCALE, (y - RAW_AXIS_Y) * SCALE, (z - RAW_FLOOR) * SCALE))

# articulações medidas nas vistas ortográficas (coordenadas originais; frente = -y)
J = {
    'hips': (0, 0.02, -0.02), 'spine': (0, 0.03, 0.10), 'spine1': (0, 0.05, 0.22), 'spine2': (0, 0.05, 0.34),
    'neck0': (0, 0.02, 0.46), 'neck1': (0, -0.08, 0.56), 'neck2': (0, -0.17, 0.64), 'headtip': (0, -0.55, 0.70),
    'jaw0': (0, -0.26, 0.62), 'jaw1': (0, -0.66, 0.60),
    'clav': (0.06, 0.0, 0.42), 'sh': (0.31, -0.07, 0.36), 'el': (0.47, -0.17, 0.17), 'wr': (0.54, -0.31, -0.02), 'hand': (0.55, -0.40, -0.24),
    'hip': (0.13, 0.02, -0.12), 'knee': (0.20, -0.30, -0.40), 'ankle': (0.22, 0.05, -0.73), 'ball': (0.25, -0.22, -0.91), 'toe': (0.28, -0.42, -0.95),
}
TAIL = [(-0.02, 0.10, -0.05), (-0.03, 0.20, -0.28), (-0.10, 0.38, -0.48), (-0.20, 0.50, -0.62), (-0.33, 0.66, -0.76), (-0.39, 0.72, -0.95)]
TAIL_R = [0.10, 0.085, 0.07, 0.055, 0.04, 0.02]
def jp(n, s=1):
    x, y, z = J[n]; return T(x * s, y, z)

def build_rig():
    ad = bpy.data.armatures.new('kobold_rig'); arm = lib.link(bpy.data.objects.new('kobold_rig', ad))
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
    bone('Neck1', jp('neck1'), jp('neck2'), 'Neck', True)
    bone('Head', jp('neck2'), jp('headtip'), 'Neck1', True)
    bone('Jaw', jp('jaw0'), jp('jaw1'), 'Head')
    for i in range(5):
        bone(f'Tail{i + 1}', T(*TAIL[i]), T(*TAIL[i + 1]), 'Hips' if i == 0 else f'Tail{i}', i > 0)
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
    # tanga: painel da frente e de trás, da cinta até a ponta
    bone('SkirtF1', T(0, -0.30, 0.06), T(0, -0.35, -0.18), 'Hips'); bone('SkirtF2', T(0, -0.35, -0.18), T(0, -0.34, -0.48), 'SkirtF1', True)
    bone('SkirtB1', T(0, 0.16, 0.08), T(0, 0.2, -0.12), 'Hips'); bone('SkirtB2', T(0, 0.2, -0.12), T(0, 0.22, -0.32), 'SkirtB1', True)
    bone('socket_hand_r', jp('hand', -1), jp('hand', -1) + Vector((0, 0, -0.03)), 'RightHand', deform=False)
    bone('socket_hand_l', jp('hand', 1), jp('hand', 1) + Vector((0, 0, -0.03)), 'LeftHand', deform=False)
    bone('socket_back', T(0, 0.08, 0.25), T(0, 0.08, 0.32), 'Spine2', deform=False)
    bone('socket_head', T(0, -0.1, 0.9), T(0, -0.1, 0.95), 'Head', deform=False)
    bpy.ops.object.mode_set(mode='OBJECT')
    return arm

def vertex_colors(obj):
    """cor da textura em cada vértice (média das quinas), em sRGB."""
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
    return np.clip(col / np.maximum(cnt, 1)[:, None], 0, 1) ** (1 / 2.2)

def tail_dist(p):
    best = (9.0, 0)
    for i in range(5):
        d = lib.seg_dist(p, T(*TAIL[i]), T(*TAIL[i + 1]))
        if d < best[0]: best = (d, i)
    return best

UPPER = ['Hips', 'Spine', 'Spine1', 'Spine2', 'Neck'] + [p + n for p in ('Left', 'Right') for n in ('Shoulder', 'Arm', 'ForeArm', 'Hand')]
def classify(obj, raw, col):
    """uma classe por vértice, pela região do corpo (e a cor amarela para a tanga)."""
    r, g, b = col[:, 0], col[:, 1], col[:, 2]
    yellow = (r > 0.7) & (g > 0.6) & (b < 0.65) & (r - b > 0.28)        # tanga: amarelo (0,9 0,82 0,48)
    red = (r - g > 0.2) & (r > 0.35)                                     # escamas (o couro, o metal e o pano não são vermelhos)
    out = []
    for v, (x, y, z) in zip(obj.data.vertices, raw):
        p = v.co; ax = abs(x)
        dt, ti = tail_dist(p)
        S = 'Left' if x > 0 else 'Right'
        dleg = min(lib.seg_dist(p, jp(a, 1 if x > 0 else -1), jp(b_, 1 if x > 0 else -1)) for a, b_ in (('hip', 'knee'), ('knee', 'ankle'), ('ankle', 'ball'), ('ball', 'toe')))
        if z > 0.5 or (z > 0.42 and ax < 0.2) or (z > 0.34 and ax < 0.18 and y < -0.2):
            c = 'mandibula' if (y < -0.32 and 0.56 < z < 0.625 + (y + 0.3) * -0.04 and ax < 0.12) else 'cabeca'
        elif (ax > 0.38 and y < -0.28 and -0.36 < z < 0.1) or (ax > 0.26 and -0.34 < z < 0.27 and min(lib.seg_dist(p, jp(a, 1 if x > 0 else -1), jp(b_, 1 if x > 0 else -1)) for a, b_ in (('sh', 'el'), ('el', 'wr'), ('wr', 'hand'))) < (0.14 if z < 0.0 else 0.1) * SCALE and (ax > 0.34 or z < 0.05)):
            c = 'braco'          # inclui a parte de dentro dos dedos e o polegar, que ficam encostados na cintura
        elif yellow[v.index] and -0.6 < z < 0.12 and ax < 0.3 and (y < -0.05 or (z > -0.25 and tail_dist(v.co)[0] > 0.06 * SCALE)):
            c = 'tangaF' if y < 0.0 else 'tangaB'
        elif z < 0.0 and y > 0.06 and dt < (TAIL_R[ti] * 1.9 + 0.02) * SCALE and dt < dleg * 0.85:
            c = 'cauda'
        elif -0.4 < z < 0.06 and ax > 0.12 and not red[v.index]:
            c = 'equip'          # bolsas, bainhas e adagas penduradas no cinto: vão com o quadril, não com a coxa
        elif z < -0.2:
            c = 'perna'
        elif z < 0.06:
            c = 'quadril'
        else:
            c = 'tronco'
        out.append(c)
    return out

CAND = {
    'cabeca': ['Spine2', 'Neck', 'Neck1', 'Head', 'LeftShoulder', 'RightShoulder'], 'mandibula': ['Head', 'Jaw'],
    'cauda': ['Hips', 'Tail1', 'Tail2', 'Tail3', 'Tail4', 'Tail5'],
    'tangaF': ['Hips', 'SkirtF1', 'SkirtF2'], 'equip': ['Hips'], 'tangaB': ['Hips', 'SkirtB1', 'SkirtB2'],
    'tronco': UPPER,
}
def assign(obj, arm, raw, cls):
    segs = {b.name: (b.head_local.copy(), b.tail_local.copy()) for b in arm.data.bones if b.use_deform}
    for n in segs: obj.vertex_groups.new(name=n)
    stats = {}
    for v, (x, y, z), c in zip(obj.data.vertices, raw, cls):
        p = v.co; S = 'Left' if x > 0 else 'Right'
        stats[c] = stats.get(c, 0) + 1
        if c == 'tronco' and z < 0.2 and abs(x) < 0.34: cand = ['Hips', 'Spine', 'Spine1']   # cintura e adagas: não seguem o braço
        elif c == 'quadril' and z > -0.06: cand = ['Hips', 'Spine']                            # cinto e bolsas: não seguem a coxa
        else: cand = CAND.get(c) or {'braco': [S + 'Arm', S + 'ForeArm', S + 'Hand'], 'perna': [S + 'UpLeg', S + 'Leg', S + 'Foot', S + 'ToeBase'],
                               'quadril': ['Hips', 'Spine', S + 'UpLeg']}[c]
        sig = {'tronco': 0.02, 'quadril': 0.025, 'cauda': 0.025, 'tangaF': 0.04, 'tangaB': 0.04, 'cabeca': 0.035}.get(c, 0.02)
        bias = {'Hips': 1.0, 'Spine2': 0.9}
        ds = [(lib.seg_dist(p, *segs[n]) * bias.get(n, 1.0), n) for n in cand]
        dmin = min(d for d, _ in ds)
        for d, n in ds:
            w = math.exp(-((d - dmin) / sig) ** 2)
            if w > 0.01: obj.vertex_groups[n].add([v.index], w, 'REPLACE')
    print('classes:', stats)

# pares de classes que se encostam no modelo mas se mexem separados: a costura entre elas é cortada
SOLTO = {frozenset(p) for p in (('equip', 'perna'), ('equip', 'quadril'), ('equip', 'braco'), ('equip', 'tangaF'), ('tangaF', 'quadril'), ('tangaB', 'quadril'), ('braco', 'quadril'), ('braco', 'tronco'), ('braco', 'tangaF'), ('braco', 'perna'), ('cauda', 'perna'), ('tangaF', 'perna'),
                                ('tangaB', 'perna'), ('tangaB', 'cauda'), ('tangaF', 'cauda'), ('mandibula', 'tronco'), ('mandibula', 'cabeca'))}

def split_classes(obj, cls):
    """corta as arestas entre faces de classes 'soltas' e devolve a classe de cada vértice (a da maioria das faces dele)."""
    from collections import Counter
    bm = bmesh.new(); bm.from_mesh(obj.data); bm.verts.ensure_lookup_table(); bm.faces.ensure_lookup_table()
    fcls = {}
    for f in bm.faces:
        fcls[f.index] = Counter(cls[v.index] for v in f.verts).most_common(1)[0][0]
    cut = [e for e in bm.edges if len(e.link_faces) == 2 and frozenset((fcls[e.link_faces[0].index], fcls[e.link_faces[1].index])) in SOLTO]
    # braço x tronco só se corta abaixo do ombro (no ombro a pele é contínua)
    cut = [e for e in cut if not ({fcls[e.link_faces[0].index], fcls[e.link_faces[1].index]} == {'braco', 'tronco'} and min(v.co.z for v in e.verts) > T(0, 0, 0.2).z)]
    bmesh.ops.split_edges(bm, edges=cut)
    bm.verts.index_update(); bm.verts.ensure_lookup_table(); bm.faces.ensure_lookup_table()
    new = []
    for v in bm.verts:
        c = Counter(fcls.get(f.index, 'tronco') for f in v.link_faces).most_common(1)
        new.append(c[0][0] if c else 'tronco')
    bm.to_mesh(obj.data); bm.free(); obj.data.update()
    print('arestas cortadas:', len(cut))
    return new

# ================================================================ animações
FPS = 30; TAU = 2 * math.pi
sn = lambda t: math.sin(TAU * t)
cs = lambda t: math.cos(TAU * t)
smooth = lambda x: x * x * (3 - 2 * x)
clamp01 = lambda x: max(0.0, min(1.0, x))
def win(t, a, b): return smooth(clamp01((t - a) / (b - a)))

def claws(P, close=0.0):
    """garras: close 0 = abertas, 1 = fechadas."""
    for s in (1, -1):
        P.side(s, 'HandFingers1', (X, -10 - 50 * close)); P.side(s, 'HandFingers2', (X, -14 - 50 * close))
        P.side(s, 'HandIndex1', (X, -8 - 45 * close)); P.side(s, 'HandIndex2', (X, -10 - 45 * close)); P.side(s, 'HandThumb1', (Z, -8 - 20 * close))

def arms(P, swing=(0.0, 0.0), elbow=(-20.0, -20.0), out=(0.0, 0.0), hand=(-6.0, -6.0)):
    for k, s in enumerate((1, -1)):
        P.side(s, 'Arm', (Y, out[k]), (X, swing[k]))
        P.side(s, 'ForeArm', (X, elbow[k]))
        P.side(s, 'Hand', (X, hand[k]))

def tail(P, t, base=0.0, side=0.0, amp=6.0, freq=1.0, up=0.0, lag=0.09):
    """cauda: a onda desce da base até a ponta com atraso (side = curva para o lado, up = levanta)."""
    for i in range(1, 6):
        k = 0.6 + 0.2 * i
        P.add(f'Tail{i}', (Z, side * k * 0.5 + amp * k * sn(freq * t - lag * i)), (X, -(up * (1.1 - 0.15 * i)) + base * 0.4))

def skirt(P, f=0.0, b=0.0, wave=0.0):
    P.add('SkirtF1', (X, -f * 0.6)); P.add('SkirtF2', (X, -f * 0.5 - wave))
    P.add('SkirtB1', (X, b * 0.6)); P.add('SkirtB2', (X, b * 0.5 + wave))

def crouch(P, k=1.0):
    """postura base do kobold: joelhos dobrados, tronco à frente, cabeça erguida para olhar."""
    P.move('Hips', (0, 0, -0.035 * k))
    for s in (1, -1):
        P.side(s, 'UpLeg', (X, -14 * k)); P.side(s, 'Leg', (X, 18 * k)); P.side(s, 'Foot', (X, -6 * k))
    P.add('Hips', (X, -6 * k)); P.add('Spine', (X, -4 * k)); P.add('Spine1', (X, -3 * k))
    P.add('Neck', (X, 5 * k)); P.add('Head', (X, 6 * k))

# ---- pés no chão: cinemática direta das pernas no plano de lado (y, z). Cada pose calcula onde o pé de cada perna
# fica e desce/sobe o quadril para o pé mais baixo encostar no chão (sem isso, a perna dobrada levanta o corpo).
def _vec(a, b): A, B = jp(a), jp(b); return (B.y - A.y, B.z - A.z)
LEG_V = None
def _rot(v, deg):
    a = math.radians(deg); c, s_ = math.cos(a), math.sin(a)
    return (v[0] * c - v[1] * s_, v[0] * s_ + v[1] * c)
def _xsum(P, bone): return sum(d for ax, d in P.r.get(bone, []) if ax == X)
def ground(P, extra=0.0):
    global LEG_V
    if LEG_V is None: LEG_V = [_vec('hip', 'knee'), _vec('knee', 'ankle'), _vec('ankle', 'ball'), _vec('ball', 'toe')]
    hp = _xsum(P, 'Hips')
    lows = []
    for S in ('Left', 'Right'):
        acc = hp; py = pz = 0.0; low = 0.0; rest_low = 0.0; ry = rz = 0.0
        for v, b in zip(LEG_V, ('UpLeg', 'Leg', 'Foot', 'ToeBase')):
            acc += _xsum(P, S + b)
            dy, dz = _rot(v, acc); py += dy; pz += dz; low = min(low, pz)
            ry += v[0]; rz += v[1]; rest_low = min(rest_low, rz)
        lows.append(low - rest_low)          # quanto o ponto mais baixo do pé subiu (+) ou desceu (-)
    loc = P.loc.get('Hips', Vector((0, 0, 0)))
    P.move('Hips', (loc.x, loc.y, -min(lows) + extra))     # o pé mais baixo (o de apoio) fica no chão
    return P

def pose_idle(t):
    P = Pose(); crouch(P)
    br = sn(2 * t); sh = sn(t)
    # olhar aos trancos: a cabeça vai rápido para um lado, para, e volta (como um lagarto)
    def jerk(u):
        u = u % 1.0
        return (win(u, 0.05, 0.12) - win(u, 0.4, 0.47)) - (win(u, 0.55, 0.62) - win(u, 0.85, 0.92))
    look = jerk(t)
    P.move('Hips', (0.005 * sh, 0, -0.035 + 0.003 * br))
    P.add('Hips', (Y, 2 * sh))
    P.add('Spine1', (X, -1.5 * br)); P.add('Spine2', (X, -1.5 * br))
    P.add('Neck', (Z, 14 * look), (X, 2 * br)); P.add('Neck1', (Z, 10 * look)); P.add('Head', (Z, 8 * look), (Y, -6 * look))
    snarl = win(t, 0.62, 0.66) * (1 - win(t, 0.78, 0.84))
    P.add('Jaw', (X, 16 * snarl + 2 * max(0, br)))
    for s in (1, -1):
        P.side(s, 'Shoulder', (X, -1.2 * br))
        P.side(s, 'UpLeg', (X, -1.5 * s * sh)); P.side(s, 'Leg', (X, 2.5 * s * sh))
    arms(P, swing=(-12 + 2 * sn(t + 0.2), -12 - 2 * sn(t + 0.2)), elbow=(-30 + 3 * br, -30 + 3 * br), out=(4, 4))
    claws(P, 0.2 + 0.35 * (0.5 + 0.5 * sn(2 * t + 0.3)))
    tail(P, t, side=4 * sh, amp=5, freq=1, up=4)
    skirt(P, f=1.5 * br, b=1.5 * br)
    return P

def leg(ph, stride, lift, push):
    """perna digitígrada numa fase 0..1 (0 = pé tocando à frente): no apoio a coxa vai de frente para trás e o
    tornozelo alto cede; no balanço o joelho e o tornozelo dobram juntos e o pé sobe rente."""
    thigh = -stride * cs(ph)
    if ph < 0.5:
        u = ph / 0.5
        knee = 8 + 10 * math.sin(math.pi * u)
        foot = -6 * math.sin(math.pi * u) + push * smooth(clamp01((u - 0.6) / 0.4))
        toe = -push * 0.8 * smooth(clamp01((u - 0.65) / 0.35))
    else:
        u = (ph - 0.5) / 0.5
        knee = 10 + lift * math.sin(math.pi * u) ** 0.9
        foot = push * (1 - smooth(clamp01(u / 0.3))) - lift * 0.55 * math.sin(math.pi * u)
        toe = -push * 0.8 * (1 - smooth(clamp01(u / 0.25))) + 10 * math.sin(math.pi * u)
    return thigh, knee, foot, toe

def pose_move(t, run=False):
    P = Pose(); crouch(P, 1.4 if run else 1.0)
    stride = 24 if run else 18; lift = 36 if run else 22; push = 20 if run else 12
    lean = -20 if run else -8
    for s, off in ((1, 0.0), (-1, 0.5)):
        a, k, f, toe = leg((t + off) % 1.0, stride, lift, push)
        P.side(s, 'UpLeg', (X, a), (Y, -2 * s)); P.side(s, 'Leg', (X, k)); P.side(s, 'Foot', (X, f)); P.side(s, 'ToeBase', (X, toe))
    bounce = 0.5 + 0.5 * cs(2 * t - 0.12)
    P.move('Hips', (0.006 * sn(t - 0.1), 0, -(0.06 if run else 0.035) - (0.02 if run else 0.012) * bounce))
    P.add('Hips', (Z, 10 * cs(t)), (Y, 4 * sn(t)), (X, lean * 0.6))
    P.add('Spine', (Z, -5 * cs(t - 0.03)), (X, lean * 0.3)); P.add('Spine1', (Z, -4 * cs(t - 0.06)), (X, lean * 0.2)); P.add('Spine2', (Z, -3 * cs(t - 0.08)))
    # cabeça mantém o olhar à frente, compensando a inclinação
    P.add('Neck', (X, -lean * 0.45), (Z, 3 * cs(t - 0.1))); P.add('Neck1', (X, -lean * 0.3)); P.add('Head', (X, -lean * 0.3 - 2 * bounce), (Z, 3 * cs(t - 0.12)))
    aw = 26 if run else 16
    if run: arms(P, swing=(25 + aw * cs(t - 0.06), 25 - aw * cs(t - 0.06)), elbow=(-55, -55), out=(8, 8), hand=(10, 10))
    else: arms(P, swing=(-10 + aw * cs(t - 0.06), -10 - aw * cs(t - 0.06)), elbow=(-32 - 10 * max(0, -cs(t - 0.14)), -32 - 10 * max(0, cs(t - 0.14))), out=(5, 5))
    claws(P, 0.55 if run else 0.35)
    # cauda: contrapeso, balança ao contrário do quadril; na corrida fica mais esticada e alta
    tail(P, t, side=0, amp=(5 if run else 8), freq=1, up=(14 if run else 6), lag=0.1)
    skirt(P, f=4 + 6 * max(0, -cs(t)), b=(10 if run else 5), wave=3 * cs(2 * t - 0.3))
    P.add('Jaw', (X, 6 if run else 0))
    return P

def pose_attack(t):
    """garrada: encolhe (antecipação), avança com a mão direita num arco de cima para baixo e morde no fim."""
    P = Pose(); crouch(P)
    wind = win(t, 0.0, 0.3) * (1 - win(t, 0.34, 0.44))
    hit = win(t, 0.34, 0.46) * (1 - win(t, 0.72, 1.0))
    bite = win(t, 0.44, 0.5) * (1 - win(t, 0.58, 0.68))
    P.move('Hips', (0, 0.03 * wind - 0.09 * hit, -0.035 - 0.03 * wind - 0.01 * hit))
    P.add('Hips', (Z, -12 * wind + 16 * hit), (X, -6 * hit))
    P.add('Spine1', (Z, -12 * wind + 14 * hit), (X, 6 * wind - 10 * hit)); P.add('Spine2', (Z, -8 * wind + 10 * hit), (X, -6 * hit))
    P.add('Neck', (X, -6 * wind + 8 * hit)); P.add('Head', (Z, 10 * wind - 10 * hit), (X, -4 * wind + 10 * bite))
    P.add('Jaw', (X, 8 * wind + 30 * bite))
    P.side(-1, 'Arm', (X, -40 * wind - 25 * hit), (Y, 30 * wind + 10 * hit)); P.side(-1, 'ForeArm', (X, -70 * wind + 30 * hit)); P.side(-1, 'Hand', (X, 20 * wind - 30 * hit))
    P.side(1, 'Arm', (X, -25 * wind + 10 * hit), (Y, 10 * wind)); P.side(1, 'ForeArm', (X, -45 * wind - 20 * hit))
    claws(P, 0.1 * (1 - hit) + 0.0)
    P.side(-1, 'UpLeg', (X, -22 * hit)); P.side(-1, 'Leg', (X, 14 * hit)); P.side(1, 'UpLeg', (X, 14 * hit)); P.side(1, 'Leg', (X, 10 * hit + 10 * wind))
    tail(P, t, side=-14 * wind + 18 * hit, amp=3, freq=1, up=6 + 10 * hit)
    skirt(P, f=6 * hit, b=4 * hit + 3 * wind, wave=3 * hit)
    return P

def pose_cast(t):
    """grito de guerra: encolhe e estufa o peito, abre os braços e a boca, ergue a cabeça e sacode a cauda."""
    P = Pose(); crouch(P, 1.0 - 0.5 * win(t, 0.3, 0.45))
    gather = win(t, 0.0, 0.3) * (1 - win(t, 0.36, 0.48)); roar = win(t, 0.36, 0.48) * (1 - win(t, 0.82, 1.0)); shake = sn(9 * t) * roar
    P.add('Spine1', (X, 8 * gather - 10 * roar)); P.add('Spine2', (X, 6 * gather - 8 * roar + shake))
    P.add('Neck', (X, 6 * gather - 14 * roar)); P.add('Neck1', (X, -8 * roar)); P.add('Head', (X, 8 * gather - 12 * roar + 2 * shake))
    P.add('Jaw', (X, 34 * roar + 3 * shake))
    arms(P, swing=(-30 * gather - 20 * roar, -30 * gather - 20 * roar), elbow=(-70 * gather - 40 * roar, -70 * gather - 40 * roar), out=(-10 * gather + 30 * roar, -10 * gather + 30 * roar), hand=(10 * roar, 10 * roar))
    claws(P, 0.8 * gather)
    tail(P, t, side=0, amp=4 + 10 * roar, freq=4, up=8 + 10 * roar, lag=0.12)
    skirt(P, f=3 * roar, b=4 * roar, wave=2 * shake)
    return P

def pose_hit(t):
    k = math.exp(-((t - 0.2) / 0.17) ** 2)
    P = Pose(); crouch(P)
    P.move('Hips', (0, 0.05 * k, -0.035 - 0.015 * k))
    P.add('Spine', (X, 8 * k)); P.add('Spine1', (X, 10 * k)); P.add('Spine2', (X, 8 * k)); P.add('Neck', (X, -10 * k)); P.add('Head', (X, 14 * k), (Z, 10 * k))
    P.add('Jaw', (X, 14 * k))
    arms(P, swing=(-28 * k - 10, -20 * k - 10), elbow=(-30 - 40 * k, -30 - 30 * k), out=(10 * k + 4, 10 * k + 4))
    claws(P, 0.6 * k)
    for s in (1, -1): P.side(s, 'UpLeg', (X, -6 * k)); P.side(s, 'Leg', (X, 12 * k))
    tail(P, t, side=-12 * k, amp=3, freq=2, up=4 - 6 * k)
    skirt(P, f=-5 * k, b=-3 * k, wave=3 * k)
    return P

def pose_death(t):
    buckle = win(t, 0.0, 0.3); fall = win(t, 0.26, 0.66); slap = win(t, 0.66, 0.76) * (1 - win(t, 0.76, 0.9))
    P = Pose(); crouch(P, 1 - fall)
    for s in (1, -1):
        P.side(s, 'UpLeg', (X, -40 * buckle + 30 * fall), (Y, -6 * fall)); P.side(s, 'Leg', (X, 60 * buckle - 40 * fall)); P.side(s, 'Foot', (X, -20 * buckle + 30 * fall))
    P.add('Spine1', (X, 12 * buckle - 6 * fall)); P.add('Neck', (X, -10 * fall)); P.add('Head', (X, 10 * buckle), (Z, 30 * fall))
    P.add('Jaw', (X, 20 * fall))
    P.add('Hips', (Y, 80 * fall), (X, 10 * buckle))
    P.move('Hips', (0.18 * fall, 0.04 * fall, -0.15 * buckle - 0.24 * fall))
    arms(P, swing=(-10 - 30 * fall, -10 - 50 * fall), elbow=(-30 + 20 * fall, -30 + 10 * fall), out=(10 + 40 * fall, 20 * fall))
    claws(P, 0.3 * (1 - fall))
    tail(P, t, side=-25 * fall, amp=2 * (1 - fall), freq=1, up=6 - 14 * fall - 6 * slap)
    skirt(P, f=-10 * fall, b=-10 * fall)
    return P

def bake(arm, name, fn, frames, loop=True, grounded=True):
    act = lib.new_action(arm, name)
    for f in range(frames + 1):
        t = f / frames
        P = fn(t % 1.0 if loop else t)
        if grounded: ground(P)
        lib.key_pose(arm, f + 1, P.r, P.loc)
    lib.push_nla(arm, act)

def build_animations(arm):
    bpy.context.scene.render.fps = FPS
    bake(arm, 'idle', pose_idle, 120)                         # 4 s
    bake(arm, 'walk', lambda t: pose_move(t, False), 20)
    bake(arm, 'run', lambda t: pose_move(t, True), 14)
    bake(arm, 'attack', pose_attack, 26, loop=False)
    bake(arm, 'cast', pose_cast, 44, loop=False)
    bake(arm, 'hit', pose_hit, 18, loop=False)
    bake(arm, 'death', pose_death, 50, loop=False, grounded=False)

def main():
    bpy.ops.wm.open_mainfile(filepath=SRC)
    obj = bpy.data.objects['kobold_src']; obj.name = 'kobold'
    # o Meshy entrega a malha cortada em ~1100 pedaços nas costuras de UV; soldar as costuras deixa os pesos contínuos
    # (sem isso aparecem rachaduras e lascas soltas nos dedos dos pés quando a perna dobra). As UVs continuam por quina.
    bm = bmesh.new(); bm.from_mesh(obj.data); n0 = len(bm.verts)
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=0.0008)
    bm.to_mesh(obj.data); bm.free(); obj.data.update()
    print('costuras soldadas: %d -> %d vértices' % (n0, len(obj.data.vertices)))
    col = vertex_colors(obj)
    raw = [tuple(v.co) for v in obj.data.vertices]
    for v in obj.data.vertices: v.co = T(*v.co)
    obj.data.update()
    arm = build_rig()
    cls = classify(obj, raw, col)
    cls = split_classes(obj, cls)
    raw = [(v.co.x / SCALE, v.co.y / SCALE + RAW_AXIS_Y, v.co.z / SCALE + RAW_FLOOR) for v in obj.data.vertices]
    names = sorted(set(cls))
    obj.data.attributes.new('classe', 'INT', 'POINT').data.foreach_set('value', [names.index(c) for c in cls]); obj['classes'] = ','.join(names)
    assign(obj, arm, raw, cls)
    smooth_weights(obj, cls, radius=0.02)
    lib.bind(obj, arm)
    mat = obj.active_material; mat.name = 'kobold'
    mat['ramp'] = 'soft'; mat['rim'] = 0.2; mat['noOutline'] = True
    bsdf = [n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'][0]
    for inp in ('Metallic', 'Roughness'):
        for l in list(bsdf.inputs[inp].links): mat.node_tree.links.remove(l)
    bsdf.inputs['Metallic'].default_value = 0.0; bsdf.inputs['Roughness'].default_value = 0.7
    for img in bpy.data.images:
        if img.size[0] > 2048: img.scale(2048, 2048)
    build_animations(arm)
    print('triângulos', lib.tri_count(obj))
    for o in bpy.context.scene.objects: o.select_set(o in (obj, arm))
    bpy.ops.export_scene.gltf(
        filepath=os.path.join(OUT, 'char_kobold.glb'), export_format='GLB', use_selection=True,
        export_extras=True, export_animations=True, export_animation_mode='NLA_TRACKS', export_force_sampling=True,
        export_skins=True, export_def_bones=False, export_image_format='JPEG', export_jpeg_quality=88)
    print('GLB: %.1f MB' % (os.path.getsize(os.path.join(OUT, 'char_kobold.glb')) / 1e6))
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT, 'fontes', 'blender', 'kobold_rig.blend'))

if __name__ == '__main__':
    main()
