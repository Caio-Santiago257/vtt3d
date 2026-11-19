"""Etapa 2 do modelo recebido da Kaira: escala, rig, pesos por cor da textura, animações e exportação.

Entrada: fontes/blender/kaira_glb_reduzido.blend (gerado pela etapa 1).
Saída:   public/assets/characters/kaira/char_kaira_modelo.glb

O modelo recebido é uma peça só (corpo, cabelo, vestido e mangas fundidos), sem esqueleto.
O esqueleto é o mesmo da Kaira feita por script (mesmos nomes de ossos), então as animações de
fontes/blender/kaira.py servem aqui sem mudança, só sem a descida de braço da A-pose.
"""
import math, os, sys
import numpy as np
import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib
import kaira as K
from kaira import X, Y, Z

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
SRC = os.path.join(ROOT, 'fontes', 'blender', 'kaira_glb_reduzido.blend')
OUT = os.path.join(ROOT, 'public', 'assets', 'characters', 'kaira')

# ---------------------------------------------------------------- normalização
# medido nas vistas ortográficas do modelo recebido (coordenadas originais, metros)
RAW_FLOOR, RAW_AXIS_Y, RAW_TOP = -0.952, -0.15, 0.951
SCALE = 1.80 / (RAW_TOP - RAW_FLOOR)
def T(x, y, z):
    """coordenada original -> coordenada final (pés no chão, eixo do corpo em y = 0, 1,80 m)."""
    return Vector((x * SCALE, (y - RAW_AXIS_Y) * SCALE, (z - RAW_FLOOR) * SCALE))

# ---------------------------------------------------------------- articulações (coordenadas originais)
J = {
    'hips': (0, -0.15, 0.10), 'spine': (0, -0.15, 0.22), 'spine1': (0, -0.15, 0.36), 'spine2': (0, -0.14, 0.48),
    'neck0': (0, -0.13, 0.635), 'neck1': (0, -0.12, 0.725), 'headtop': (0, -0.12, 0.93), 'headc': (0, -0.12, 0.81),
    'clav': (0.035, -0.13, 0.60), 'sh': (0.160, -0.13, 0.585), 'el': (0.215, -0.12, 0.320), 'wr': (0.282, -0.15, 0.040), 'hand': (0.300, -0.16, -0.065),
    'hip': (0.085, -0.15, 0.065), 'knee': (0.065, -0.19, -0.450), 'ankle': (0.055, -0.21, -0.860), 'ball': (0.055, -0.31, -0.930), 'toe': (0.055, -0.38, -0.950),
}
def jp(name, s=1):
    x, y, z = J[name]; return T(x * s, y, z)

def build_rig():
    arm_data = bpy.data.armatures.new('kaira_rig')
    arm = lib.link(bpy.data.objects.new('kaira_rig', arm_data))
    lib.activate(arm); bpy.ops.object.mode_set(mode='EDIT')
    eb = arm_data.edit_bones
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
    for s, P in ((1, 'Left'), (-1, 'Right')):
        sh, el, wr, hd = jp('sh', s), jp('el', s), jp('wr', s), jp('hand', s)
        d = (hd - wr).normalized()
        bone(P + 'Shoulder', jp('clav', s), sh, 'Spine2')
        bone(P + 'Arm', sh, el, P + 'Shoulder', True)
        bone(P + 'ForeArm', el, wr, P + 'Arm', True)
        bone(P + 'Hand', wr, hd, P + 'ForeArm', True)
        # dedos: existem para manter os nomes do esqueleto, mas não deformam (a mão segue rígida)
        for n, a, b_ in (('HandIndex1', 0.0, 0.5), ('HandIndex2', 0.5, 1.0), ('HandFingers1', 0.0, 0.5), ('HandFingers2', 0.5, 1.0), ('HandThumb1', 0.0, 0.5), ('HandThumb2', 0.5, 1.0)):
            parent = P + ('Hand' if n.endswith('1') else n[:-1] + '1')
            bone(P + n, hd + d * 0.04 * a, hd + d * 0.04 * b_ + Vector((0, 0, -0.001)), parent, n.endswith('2'), deform=False)
        hp, kn, an, ba, to = jp('hip', s), jp('knee', s), jp('ankle', s), jp('ball', s), jp('toe', s)
        bone(P + 'UpLeg', hp, kn, 'Hips')
        bone(P + 'Leg', kn, an, P + 'UpLeg', True)
        bone(P + 'Foot', an, ba, P + 'Leg', True)
        bone(P + 'ToeBase', ba, to, P + 'Foot', True)
        # manga: do braço até o chão, por fora da saia
        sl = [T(0.205 * s, -0.12, 0.45), T(0.290 * s, -0.11, -0.05), T(0.340 * s, -0.08, -0.50), T(0.420 * s, -0.05, -0.92)]
        for i in range(3):
            # a manga larga pende do ombro, não do braço: assim não vira um lençol quando o braço sobe
            bone(f'{P}Sleeve{i + 1}', sl[i], sl[i + 1], P + 'Shoulder' if i == 0 else f'{P}Sleeve{i}', i > 0)
        bone(P + 'Earring', T(0.075 * s, -0.11, 0.79), T(0.077 * s, -0.11, 0.74), 'Head')
        fr = [T(0.085 * s, -0.16, 0.78), T(0.100 * s, -0.20, 0.62), T(0.110 * s, -0.22, 0.48), T(0.110 * s, -0.22, 0.36), T(0.110 * s, -0.21, 0.25)]
        for i in range(4):
            bone(f'{P}HairFront{i + 1}', fr[i], fr[i + 1], 'Head' if i == 0 else f'{P}HairFront{i}', i > 0)
    for tag, x in (('C', 0.0), ('L', 0.07), ('R', -0.07)):
        pts = [T(x * 0.6, -0.03, 0.80), T(x, 0.03, 0.60), T(x, 0.07, 0.35), T(x, 0.09, 0.10), T(x, 0.10, -0.12), T(x, 0.11, -0.33)]
        for i in range(5):
            bone(f'HairBack{tag}{i + 1}', pts[i], pts[i + 1], 'Head' if i == 0 else f'HairBack{tag}{i}', i > 0)
    for tag, dx, y0, y1 in (('F', 0, -0.27, -0.34), ('B', 0, -0.03, 0.30), ('L', 1, -0.15, -0.12), ('R', -1, -0.15, -0.12)):
        pts = [T(dx * 0.15, y0 * 0.6 + RAW_AXIS_Y * 0.4, 0.05), T(dx * 0.20, (y0 + y1) / 2, -0.30), T(dx * 0.25, y1 * 0.8 + y0 * 0.2, -0.62), T(dx * 0.30, y1, -0.94)]
        for i in range(3):
            bone(f'Skirt{tag}{i + 1}', pts[i], pts[i + 1], 'Hips' if i == 0 else f'Skirt{tag}{i}', i > 0)
    bone('socket_hand_r', jp('hand', -1), jp('hand', -1) + Vector((0, 0, -0.06)), 'RightHand', deform=False)
    bone('socket_hand_l', jp('hand', 1), jp('hand', 1) + Vector((0, 0, -0.06)), 'LeftHand', deform=False)
    bone('socket_back', T(0, -0.04, 0.40), T(0, -0.04, 0.52), 'Spine2', deform=False)
    bone('socket_head', jp('headtop'), jp('headtop') + Vector((0, 0, 0.06)), 'Head', deform=False)
    bpy.ops.object.mode_set(mode='OBJECT')
    return arm

# ---------------------------------------------------------------- classes de vértice pela cor da textura
def classify(obj):
    me = obj.data
    bsdf = [n for n in obj.active_material.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'][0]
    img = bsdf.inputs['Base Color'].links[0].from_node.image
    w, h = img.size; px = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, 4)
    uv = me.uv_layers.active.data
    col = np.zeros((len(me.vertices), 3)); cnt = np.zeros(len(me.vertices))
    for poly in me.polygons:
        for li, vi in zip(poly.loop_indices, poly.vertices):
            u, v = uv[li].uv
            col[vi] += px[int(min(h - 1, max(0, v * h))), int(min(w - 1, max(0, u * w))), :3]; cnt[vi] += 1
    col /= np.maximum(cnt, 1)[:, None]
    srgb = np.clip(col, 0, 1) ** (1 / 2.2)
    r, g, b = srgb[:, 0], srgb[:, 1], srgb[:, 2]
    # medido na textura: pele r-g ≈ +0,05 e g-b ≈ +0,075; tecido g-b ≈ +0,01; cabelo r-g ≈ +0,21
    hair = (r - g > 0.15) & (r - b > 0.08)
    skin = (~hair) & (g - b > 0.045) & (r - g < 0.075)
    return hair, skin

def smooth_weights(obj, iters=3, k=10, radius=0.03, keep=4):
    """suaviza os pesos pelos vizinhos no espaço (não pela malha): a malha decimada tem ilhas soltas
    (camadas do tecido, mechas de cabelo) que precisam se mover juntas com quem está do lado."""
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

def skirt_half(z):          # meia-largura da saia (sem as mangas), em coordenada final
    zr = z / SCALE + RAW_FLOOR
    return SCALE * (0.20 if zr > -0.30 else 0.20 + (0.30 - 0.20) * min(1.0, (-0.30 - zr) / 0.65))

BODY = ['Hips', 'Spine', 'Spine1', 'Spine2', 'Neck', 'Head'] + [p + n for p in ('Left', 'Right') for n in ('Shoulder', 'Arm', 'ForeArm', 'Hand', 'UpLeg', 'Leg', 'Foot', 'ToeBase')]

def assign(obj, arm, hair, skin):
    segs = {b.name: (b.head_local.copy(), b.tail_local.copy()) for b in arm.data.bones if b.use_deform}
    for n in segs: obj.vertex_groups.new(name=n)
    hc = jp('headc')
    groups = {
        'hair_head': ['Head'],
        'hair': ['Head'] + [f'HairBack{t}{i}' for t in 'CLR' for i in range(1, 6)] + [f'{p}HairFront{i}' for p in ('Left', 'Right') for i in range(1, 5)],
        'skin': BODY,
        'torso': ['Hips', 'Spine', 'Spine1', 'Spine2', 'Neck', 'LeftShoulder', 'RightShoulder'],
        'skirt': ['Hips'] + [f'Skirt{t}{i}' for t in 'FBLR' for i in (1, 2, 3)],
        'sleeve_l': ['LeftArm', 'LeftForeArm', 'LeftHand', 'LeftSleeve1', 'LeftSleeve2', 'LeftSleeve3'],
        'sleeve_r': ['RightArm', 'RightForeArm', 'RightHand', 'RightSleeve1', 'RightSleeve2', 'RightSleeve3'],
    }
    bias = {'Head': 0.6, 'LeftUpLeg': 1.3, 'RightUpLeg': 1.3, 'LeftLeg': 1.3, 'RightLeg': 1.3, 'Spine2': 0.8, 'Spine1': 0.8}
    stats = {}; vcls = []
    for v in obj.data.vertices:
        p = v.co
        if hair[v.index]:
            cls = 'hair_head' if (p - hc).length < 0.14 * SCALE / 0.946 and p.z > jp('neck1').z else 'hair'
        elif skin[v.index]:
            cls = 'skin'
        else:
            if p.z > jp('hips').z + 0.02:
                # tecido acima do quadril: corpete (tronco) ou manga (perto do braço, por fora do tronco)
                cls = 'torso' if abs(p.x) < 0.165 * SCALE else ('sleeve_l' if p.x > 0 else 'sleeve_r')
            else:
                cls = ('sleeve_l' if p.x > 0 else 'sleeve_r') if abs(p.x) > skirt_half(p.z) else 'skirt'
        stats[cls] = stats.get(cls, 0) + 1; vcls.append(hash(cls) % 1000)
        cand = groups[cls]
        # todos os ossos candidatos com queda gaussiana (sem corte nos 3 mais próximos, que criava degraus)
        sig = 0.10 if cls == 'skirt' else 0.045
        ds = [(lib.seg_dist(p, *segs[n]) * bias.get(n, 1.0), n) for n in cand]
        dmin = min(d for d, _ in ds)
        for d, n in ds:
            w = math.exp(-((d - dmin) / sig) ** 2)
            if w > 0.01: obj.vertex_groups[n].add([v.index], w, 'REPLACE')
    print('classes:', stats)
    return np.array(vcls)

# ---------------------------------------------------------------- andar novo (skill animation)
# contato -> descida -> passagem -> subida, duas vezes por ciclo; o pé rola do calcanhar à ponta; o quadril gira,
# rola para o lado da perna de apoio e cai do lado da perna que balança; o passo cruza um pouco à frente (andar
# elegante de vestido longo); tronco e ombros giram ao contrário com atraso; a cabeça segura o olhar; braços
# com o cotovelo e a mão atrasados; cabelo, brincos, mangas e saia seguem com atraso crescente.
def _sm(x): x = max(0.0, min(1.0, x)); return x * x * (3 - 2 * x)
def _leg(ph, stride, knee_max, lift, push):
    thigh = -stride * math.cos(2 * math.pi * ph)
    if ph < 0.5:
        u = ph / 0.5
        knee = 10 * math.sin(math.pi * min(1, u / 0.45)) * (1 - u) + 3
        foot = -10 * (1 - _sm(u / 0.18)) + push * _sm((u - 0.6) / 0.4)
        toe = -push * 0.8 * _sm((u - 0.65) / 0.35)
    else:
        u = (ph - 0.5) / 0.5
        knee = 5 + knee_max * math.sin(math.pi * u) ** 0.9
        foot = push * (1 - _sm(u / 0.35)) + lift * math.sin(math.pi * u) - 10 * _sm((u - 0.7) / 0.3)
        toe = -push * 0.8 * (1 - _sm(u / 0.25))
    return thigh, knee, foot, toe

def walk_v2(t, run=False):
    TAU = 2 * math.pi; sn = lambda x: math.sin(TAU * x); cs = lambda x: math.cos(TAU * x)
    P = K.Pose()
    stride = 30 if run else 21; knee_max = 70 if run else 44; lift = 16 if run else 9; push = 20 if run else 15
    th = []
    for s_, off in ((1, 0.0), (-1, 0.5)):
        ph = (t + off) % 1.0
        a_, k_, f_, toe = _leg(ph, stride, knee_max, lift, push)
        th.append(a_)
        stance = 1.0 if ph < 0.5 else 0.0
        P.side(s_, 'UpLeg', (X, a_), (Y, 2.0 * stance - 1.0))            # cruza um pouco no apoio
        P.side(s_, 'Leg', (X, k_)); P.side(s_, 'Foot', (X, f_)); P.side(s_, 'ToeBase', (X, toe))
    bounce = 0.5 + 0.5 * cs(2 * t - 0.12)
    drop = 0.03 if run else 0.016
    P.move('Hips', (0.012 * sn(t - 0.08), 0, -drop * bounce))
    lean = -8 if run else -1.5
    P.add('Hips', (Z, 7 * cs(t)), (Y, 4.5 * sn(t)), (X, lean * 0.4))
    P.add('Spine', (Z, -3.5 * cs(t - 0.04)), (Y, -2.2 * sn(t - 0.04)), (X, lean * 0.3 + 0.8 * bounce))
    P.add('Spine1', (Z, -3.0 * cs(t - 0.07)), (Y, -1.2 * sn(t - 0.07)), (X, lean * 0.2 + 0.6 * bounce))
    P.add('Spine2', (Z, -2.5 * cs(t - 0.1)), (X, lean * 0.15 + 0.5 * bounce))
    P.add('Neck', (Z, 1.8 * cs(t - 0.12)), (X, -lean * 0.3)); P.add('Head', (Z, 2.2 * cs(t - 0.14)), (X, -lean * 0.45 - 1.0 * bounce), (Y, -1.2 * sn(t - 0.12)))
    for s_ in (1, -1): P.side(s_, 'Shoulder', (X, 2 * s_ * cs(t - 0.06)), (Y, -1.2 * bounce))
    aw = 30 if run else 15
    a = cs(t - 0.06); el = cs(t - 0.14)
    K.base_arms(P, low=K.LOWER, fwd=-5, elbow=-50 if run else -18, swing=(aw * a, -aw * a),
                elbow_extra=(-10 * max(0, -el), -10 * max(0, el)), sleeve_sway=(10 + 5 * cs(t - 0.2), 10 - 5 * cs(t - 0.2)))
    K.hair(P, t * 2 - 0.15, back=12 if run else 6, amp=2.6 if run else 1.8, freq=1, side_amp=1.6)
    lagged = [-_leg((t - 0.06 + off) % 1.0, stride, 0, 0, 0)[0] for off in (0.0, 0.5)]
    front = max(0.0, *lagged); back = max(0.0, *(-x for x in lagged))
    K.skirt(P, t, f=2 + front * 0.6, b=3 + back * 0.55, l=lagged[0] * 0.4, r=lagged[1] * 0.4)
    return P

def main():
    bpy.ops.wm.open_mainfile(filepath=SRC)
    obj = bpy.data.objects['kaira_src']; obj.name = 'kaira'
    hair, skin = classify(obj)
    # normaliza: pés no chão, eixo do corpo na origem, 1,80 m
    for v in obj.data.vertices:
        v.co = T(*v.co)
    obj.data.update()
    arm = build_rig()
    assign(obj, arm, hair, skin)
    smooth_weights(obj)
    lib.bind(obj, arm)
    # material: rampa anime, contorno fino; texturas em 2048 (a de rugosidade/metal não é usada pelo jogo)
    mat = obj.active_material; mat.name = 'kaira'
    # o tecido é fino e de lado duplo: o contorno por casco invertido gera manchas pretas nele
    mat['ramp'] = 'soft'; mat['rim'] = 0.25; mat['noOutline'] = True
    bsdf = [n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'][0]
    for inp in ('Metallic', 'Roughness'):
        for l in list(bsdf.inputs[inp].links): mat.node_tree.links.remove(l)
    bsdf.inputs['Metallic'].default_value = 0.0; bsdf.inputs['Roughness'].default_value = 0.8
    for img in bpy.data.images:
        if img.size[0] > 2048: img.scale(2048, 2048)
    # animações: as mesmas da Kaira por script; os braços já estão abaixados no repouso
    K.LOWER = 0; K.SKIRT_K = 0.55; K.SLEEVE_K = 0.0; K.STRIDE_K = 0.65; K.HAIR_K = 0.55
    K.pose_locomotion = walk_v2; K.bake.__defaults__ = (True, 1)   # andar novo, gravado quadro a quadro
    K.build_animations(arm)
    print('triângulos', lib.tri_count(obj))
    for o in bpy.context.scene.objects: o.select_set(o in (obj, arm))
    bpy.ops.export_scene.gltf(
        filepath=os.path.join(OUT, 'char_kaira_modelo.glb'), export_format='GLB', use_selection=True,
        export_extras=True, export_animations=True, export_animation_mode='NLA_TRACKS', export_force_sampling=True,
        export_skins=True, export_def_bones=False, export_image_format='JPEG', export_jpeg_quality=88)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT, 'fontes', 'blender', 'kaira_glb_rig.blend'))

if __name__ == '__main__':
    main()
