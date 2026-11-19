"""Kaira com asas (Revelação Celestial): escala, esqueleto, pesos, animações e exportação.

Entrada: fontes/blender/kaira_asas_reduzido.blend (etapa 1, 60 mil triângulos).
Saída:   public/assets/characters/kaira/char_kaira_asas.glb

O modelo recebido está pairando (pés soltos, vestido esvoaçando, asas abertas, auréola de estrelas).
Esqueleto: corpo no padrão Mixamo, auréola, três correntes de cabelo, quatro de saia e as asas
(Wing1 = braço da asa até o "pulso", WingTip = penas longas de cima, WingLow = penas de baixo).
Animações:
  revelar   a transformação: começa encolhida com as asas minúsculas dobradas nas costas; se abre, as asas
            crescem e se desdobram, a auréola acende, e uma batida forte a lança para o alto
  fly_idle  pairando: batidas de asa, corpo sobe e desce, vestido e cabelo flutuando, auréola girando
  fly       voando para a frente: corpo inclinado, cabelo e vestido para trás, batidas largas
  recolher  aterrissando: as asas fecham e encolhem até sumir, a auréola apaga
O salto girando, a coluna de luz e o clarão da troca de modelo são feitos no jogo (public/js/revelacao.js),
sincronizados com estes clipes.
"""
import math, os, sys
import numpy as np
import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
SRC = os.path.join(ROOT, 'fontes', 'blender', 'kaira_asas_reduzido.blend')
OUT = os.path.join(ROOT, 'public', 'assets', 'characters', 'kaira')
X, Y, Z = (1, 0, 0), (0, 1, 0), (0, 0, 1)
TAU = 2 * math.pi

# ---------------------------------------------------------------- normalização (medido no modelo recebido)
FEET, HEAD_TOP, AXIS_Y = -0.92, 0.68, -0.07
SCALE = 1.80 / (HEAD_TOP - FEET)          # mesma altura da Kaira de chão (1,80 m)
def T(x, y, z): return Vector((x * SCALE, (y - AXIS_Y) * SCALE, (z - FEET) * SCALE))

def build_rig():
    ad = bpy.data.armatures.new('kaira_asas_rig')
    arm = lib.link(bpy.data.objects.new('kaira_asas_rig', ad))
    lib.activate(arm); bpy.ops.object.mode_set(mode='EDIT')
    eb = ad.edit_bones
    def bone(name, h, t, parent=None, connect=False, deform=True):
        b = eb.new(name); b.head = T(*h); b.tail = T(*t); b.use_deform = deform
        if parent: b.parent = eb[parent]; b.use_connect = connect
    spine = [(0, -0.07, 0.02), (0, -0.07, 0.15), (0, -0.07, 0.30), (0, -0.06, 0.43), (0, -0.05, 0.53), (0, -0.05, 0.70)]
    for i, n in enumerate(['Hips', 'Spine', 'Spine2', 'Neck', 'Head']):
        bone(n, spine[i], spine[i + 1], ['Hips', 'Spine', 'Spine2', 'Neck', 'Head'][i - 1] if i else None, i > 0)
    bone('Halo', (0, -0.03, 0.70), (0, -0.03, 0.80), 'Head')
    for s, P in ((1, 'Left'), (-1, 'Right')):
        sh, el, wr, hd = (0.09 * s, -0.07, 0.42), (0.20 * s, -0.06, 0.25), (0.29 * s, -0.05, 0.08), (0.33 * s, -0.05, 0.03)
        bone(P + 'Arm', sh, el, 'Spine2'); bone(P + 'ForeArm', el, wr, P + 'Arm', True); bone(P + 'Hand', wr, hd, P + 'ForeArm', True)
        hp, kn, an, to = (0.05 * s, -0.07, 0.0), (0.05 * s, -0.08, -0.42), (0.04 * s, -0.08, -0.82), (0.04 * s, -0.12, -0.92)
        bone(P + 'UpLeg', hp, kn, 'Hips'); bone(P + 'Leg', kn, an, P + 'UpLeg', True); bone(P + 'Foot', an, to, P + 'Leg', True)
        # asa: raiz nas costas, "pulso" no alto, penas longas até a ponta e penas de baixo
        root, wrist, tip, low = (0.06 * s, 0.06, 0.42), (0.33 * s, 0.12, 0.72), (0.58 * s, 0.16, 0.93), (0.48 * s, 0.14, 0.25)
        bone(P + 'Wing1', root, wrist, 'Spine2'); bone(P + 'WingTip', wrist, tip, P + 'Wing1', True); bone(P + 'WingLow', wrist, low, P + 'Wing1')
        hl = [(0.12 * s, 0.0, 0.55), (0.20 * s, 0.05, 0.30), (0.25 * s, 0.05, 0.05), (0.28 * s, 0.05, -0.25)]
        for i in range(3): bone(f'{P}Hair{i + 1}', hl[i], hl[i + 1], 'Head' if i == 0 else f'{P}Hair{i}', i > 0)
    hc = [(0, 0.05, 0.60), (0, 0.12, 0.40), (0, 0.15, 0.15), (0, 0.15, -0.15)]
    for i in range(3): bone(f'BackHair{i + 1}', hc[i], hc[i + 1], 'Head' if i == 0 else f'BackHair{i}', i > 0)
    for tag, x, y in (('F', 0, -0.2), ('B', 0, 0.1), ('L', 0.25, -0.06), ('R', -0.25, -0.06)):
        pts = [(x * 0.5, y * 0.8 - 0.01, 0.0), (x * 0.9, y, -0.3), (x * 1.15, y, -0.6), (x * 1.3, y * 0.9, -0.92)]
        for i in range(3): bone(f'Skirt{tag}{i + 1}', pts[i], pts[i + 1], 'Hips' if i == 0 else f'Skirt{tag}{i}', i > 0)
    bpy.ops.object.mode_set(mode='OBJECT')
    return arm

# ---------------------------------------------------------------- pesos
def classify(obj):
    me = obj.data
    bsdf = [n for n in obj.active_material.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'][0]
    img = bsdf.inputs['Base Color'].links[0].from_node.image; w, h = img.size
    px = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, 4)
    uv = me.uv_layers.active.data; nv = len(me.vertices)
    col = np.zeros((nv, 3)); cnt = np.zeros(nv)
    for p in me.polygons:
        for li, vi in zip(p.loop_indices, p.vertices):
            u, v = uv[li].uv; col[vi] += px[int(min(h - 1, max(0, v * h))), int(min(w - 1, max(0, u * w))), :3]; cnt[vi] += 1
    col = np.clip(col / np.maximum(cnt, 1)[:, None], 0, 1) ** (1 / 2.2)
    co = np.array([v.co[:] for v in me.vertices]); x, y, z = co.T; r, g, b = col.T
    hair = (r - g > 0.15) & (r - b > 0.05)
    # auréola: anel de estrelas em volta da cabeça, de frente (no plano x-z)
    ring = np.abs(np.hypot(x, z - 0.70) - 0.13)
    halo = (z > 0.58) & (ring < 0.045) & (y > -0.14) & (y < 0.06) & ~hair
    # asas: atrás do corpo e acima dos ombros, ou bem para fora (penas de baixo)
    wing = ~hair & ~halo & (((np.abs(x) > 0.14) & (z > 0.25) & (y > -0.02)) | ((np.abs(x) > 0.33) & (z > 0.14) & (y > -0.1)))
    return hair, halo, wing, x

BODY = ['Hips', 'Spine', 'Spine2', 'Neck', 'Head']
def assign(obj, arm, hair, halo, wing, xs):
    segs = {b.name: (b.head_local.copy(), b.tail_local.copy()) for b in arm.data.bones if b.use_deform}
    for n in segs: obj.vertex_groups.new(name=n)
    limbs = [p + n for p in ('Left', 'Right') for n in ('Arm', 'ForeArm', 'Hand', 'UpLeg', 'Leg', 'Foot')]
    skirt = [f'Skirt{t}{i}' for t in 'FBLR' for i in (1, 2, 3)]
    hairb = [f'{p}Hair{i}' for p in ('Left', 'Right', 'Back') for i in (1, 2, 3)]
    sig = 0.04 * SCALE; stats = {}
    for v in obj.data.vertices:
        i = v.index
        if halo[i]: cand, cls = ['Halo'], 'auréola'
        elif wing[i]:
            P = 'Left' if xs[i] > 0 else 'Right'
            cand, cls = ['Spine2', P + 'Wing1', P + 'WingTip', P + 'WingLow'], 'asa'
        elif hair[i]: cand, cls = ['Head', 'Neck'] + hairb, 'cabelo'
        else: cand, cls = BODY + limbs + skirt, 'corpo'
        stats[cls] = stats.get(cls, 0) + 1
        ds = [(lib.seg_dist(v.co, *segs[n]), n) for n in cand]; dmin = min(d for d, _ in ds)
        for d, n in ds:
            wgt = math.exp(-((d - dmin) / sig) ** 2)
            if wgt > 0.01: obj.vertex_groups[n].add([i], wgt, 'REPLACE')
    print('vértices por parte:', stats)

def smooth_weights(obj, iters=3, k=10, radius=0.025, keep=4):
    from scipy.spatial import cKDTree
    me = obj.data; nv = len(me.vertices); ng = len(obj.vertex_groups)
    W = np.zeros((nv, ng), np.float32)
    for v in me.vertices:
        for g in v.groups: W[v.index, g.group] = g.weight
    W /= np.maximum(W.sum(1, keepdims=True), 1e-6)
    co = np.array([v.co[:] for v in me.vertices])
    d, idx = cKDTree(co).query(co, k=k, distance_upper_bound=radius)
    ok = np.isfinite(d); idx = np.where(ok, idx, np.arange(nv)[:, None])
    wt = np.where(ok, np.exp(-(d / (radius * 0.6)) ** 2), 0.0).astype(np.float32); wt /= wt.sum(1, keepdims=True)
    for _ in range(iters): W = np.einsum('nk,nkg->ng', wt, W[idx])
    for gi in range(ng): obj.vertex_groups[gi].remove(list(range(nv)))
    top = np.argsort(-W, axis=1)[:, :keep]
    for vi in range(nv):
        ws = W[vi, top[vi]]; ws = ws / max(ws.sum(), 1e-6)
        for gi, w in zip(top[vi], ws):
            if w > 0.01: obj.vertex_groups[int(gi)].add([vi], float(w), 'REPLACE')

# ---------------------------------------------------------------- animações
SCALED = ['LeftWing1', 'RightWing1', 'Halo']   # ossos com escala animada (sempre gravada, em todo clipe)

class Pose:
    def __init__(self, arm):
        self.r = {b.name: [] for b in arm.data.bones if b.use_deform}
        self.s = {n: 1.0 for n in SCALED}; self.loc = {'Hips': Vector((0, 0, 0))}
    def add(self, bone, *rots): self.r[bone].extend(rots); return self
    def move(self, v): self.loc['Hips'] = self.loc['Hips'] + Vector(v); return self

def sm(x): x = max(0.0, min(1.0, x)); return x * x * (3 - 2 * x)
def back_out(x, k=1.6):  # cresce passando um pouco do ponto e volta (efeito de "brotar")
    x = max(0.0, min(1.0, x)); x -= 1; return 1 + x * x * ((k + 1) * x + k)

def wings(P, flap=0.0, fold=0.0, sweep=0.0, tip=None, low=None, scale=1.0):
    """flap: + = asa para baixo (graus); fold 0..1: dobrada nas costas; sweep: + = para trás."""
    tip = flap * 0.45 if tip is None else tip; low = flap * 0.3 if low is None else low
    for s, sg in (('Left', 1), ('Right', -1)):
        P.add(s + 'Wing1', (Z, sg * (sweep + fold * 70)), (Y, sg * (flap + fold * 75)), (X, -fold * 10))
        P.add(s + 'WingTip', (Y, sg * (tip + fold * 60)))
        P.add(s + 'WingLow', (Y, sg * (low - fold * 30)), (Z, sg * fold * 25))
        P.s[s + 'Wing1'] = scale

def float_body(P, t, amp=1.0, trail=0.0):
    """vestido, cabelo e braços flutuando (trail > 0: tudo puxado para trás, voando para a frente)."""
    for i, (tag, ph) in enumerate((('F', 0.0), ('B', 0.3), ('L', 0.15), ('R', 0.45))):
        for k in (1, 2, 3):
            a = (4 + 3 * k) * amp * math.sin(TAU * (t - ph - 0.08 * k))
            P.add(f'Skirt{tag}{k}', (X, -trail * (5 + 4 * k) + a), (Y, 0.5 * a if tag in 'LR' else 0))
    for P_, sg in (('Left', 1), ('Right', -1)):
        for k in (1, 2, 3): P.add(f'{P_}Hair{k}', (X, -trail * (4 + 3 * k) + 4 * amp * math.sin(TAU * (t - 0.1 - 0.1 * k))), (Y, sg * 3 * amp * math.sin(TAU * (t * 0.5 - 0.1 * k))))
    for k in (1, 2, 3): P.add(f'BackHair{k}', (X, -trail * (5 + 4 * k) + 5 * amp * math.sin(TAU * (t - 0.15 * k))))
    for s, sg in (('Left', 1), ('Right', -1)):
        P.add(s + 'Arm', (X, -trail * 30 + 4 * amp * math.sin(TAU * (t + 0.2))), (Y, sg * (-trail * 15)))
        P.add(s + 'ForeArm', (X, -trail * 10 + 3 * amp * math.sin(TAU * (t + 0.3))))

def stroke(ph, down_frac=0.4):
    """uma batida (skill animation: tempo e arcos): a descida é rápida (empurra o ar), a subida mais lenta.
    devolve s (-1 no alto, +1 embaixo) e up (0..1, quanto a asa está no meio da subida, quando se dobra)."""
    u = ph % 1.0
    if u < down_frac: return -math.cos(math.pi * u / down_frac), 0.0
    v = (u - down_frac) / (1 - down_frac)
    return math.cos(math.pi * v), math.sin(math.pi * v)

def pose_fly_idle(arm, t):
    """pairando: duas batidas por ciclo. A ponta e as penas de baixo vêm atrasadas (chicotada); na subida a asa
    dobra um pouco e varre para trás; o corpo sobe logo depois de cada descida; pernas soltas, alternadas."""
    P = Pose(arm)
    ph = (t * 2) % 1.0
    s, up = stroke(ph); s_tip, _ = stroke(ph - 0.08); s_low, _ = stroke(ph - 0.16)
    wings(P, flap=6 + 36 * s, fold=0.16 * up, sweep=4 + 10 * up, tip=-6 + 20 * s_tip, low=-2 + 12 * s_low)
    heave, _ = stroke(ph - 0.22)
    P.move((0, 0, -0.035 * heave))
    P.add('Hips', (X, 3)); P.add('Spine', (X, 1.5 * heave)); P.add('Spine2', (X, 1.2 * stroke(ph - 0.3)[0]))
    P.add('Neck', (X, -0.8 * heave)); P.add('Head', (X, -3 + 1.5 * math.sin(TAU * t)), (Z, 5 * math.sin(TAU * t * 0.5 + 0.4)))
    P.add('Halo', (Y, 6 * math.sin(TAU * t)))
    for side, sg in (('Left', 1), ('Right', -1)):
        o = 0 if sg > 0 else 0.5
        P.add(side + 'UpLeg', (X, -5 + 4 * math.sin(TAU * (t + o))), (Y, -sg * 2))
        P.add(side + 'Leg', (X, 12 + 7 * math.sin(TAU * (t + o - 0.12))))
        P.add(side + 'Foot', (X, 18 + 6 * math.sin(TAU * (t + o - 0.22))))     # ponta do pé estendida
    float_body(P, t, 1.0)
    return P

def pose_fly(arm, t):
    """voando para a frente: corpo quase deitado, olhando adiante; batidas largas (descida rápida, subida
    dobrando e varrendo para trás); pernas juntas e estendidas para trás, com um joelho dobrado (pose clássica);
    cabelo, vestido e braços puxados pelo vento com onda atrasada."""
    P = Pose(arm)
    ph = (t * 2) % 1.0
    s, up = stroke(ph, 0.38); s_tip, _ = stroke(ph - 0.09, 0.38); s_low, _ = stroke(ph - 0.18, 0.38)
    wings(P, flap=8 + 42 * s, fold=0.2 * up, sweep=16 + 12 * up, tip=-6 + 24 * s_tip, low=-2 + 14 * s_low)
    heave, _ = stroke(ph - 0.24, 0.38)
    P.move((0, 0, -0.045 * heave))
    P.add('Hips', (X, 20)); P.add('Spine', (X, 4 + 1.5 * heave)); P.add('Spine2', (X, 2 + 1.0 * stroke(ph - 0.3, 0.38)[0]))
    P.add('Neck', (X, -10)); P.add('Head', (X, -20 - 1.5 * heave), (Z, 3 * math.sin(TAU * t)))
    P.add('LeftUpLeg', (X, 10 + 2 * math.sin(TAU * (t - 0.1)))); P.add('LeftLeg', (X, 10 + 4 * math.sin(TAU * (t - 0.2)))); P.add('LeftFoot', (X, 30))
    P.add('RightUpLeg', (X, 2 + 2 * math.sin(TAU * (t - 0.15)))); P.add('RightLeg', (X, 42 + 5 * math.sin(TAU * (t - 0.25)))); P.add('RightFoot', (X, 32))
    float_body(P, t * 2, 0.55, trail=0.9)
    return P

def pose_revelar(arm, t):
    """0-0,25 encolhida (o jogo faz o salto girando); 0,25-0,6 se abre e as asas brotam; 0,6-0,85 batida forte; fim = pairando."""
    P = Pose(arm)
    curl = 1 - sm((t - 0.18) / 0.22)                     # 1 encolhida -> 0 aberta
    arch = sm((t - 0.25) / 0.15) * (1 - sm((t - 0.55) / 0.3))   # arqueia para trás no momento da revelação
    grow = back_out((t - 0.28) / 0.3) if t > 0.28 else 0.0
    unfold = sm((t - 0.32) / 0.28)
    beat = math.sin(math.pi * min(1, max(0, (t - 0.6) / 0.25)))  # a batida forte
    idle = pose_fly_idle(arm, 0.0)
    settle = sm((t - 0.85) / 0.15)
    P.move((0, 0, -0.15 * curl + 0.12 * beat))
    P.add('Hips', (X, 10 * curl - 4 * arch)); P.add('Spine', (X, 8 * curl - 9 * arch)); P.add('Spine2', (X, 6 * curl - 8 * arch))
    P.add('Neck', (X, 6 * curl - 6 * arch)); P.add('Head', (X, 14 * curl - 16 * arch))
    for s, sg in (('Left', 1), ('Right', -1)):
        # encolhida: joelhos no peito, braços cruzados; aberta: braços para o alto e para os lados
        # (movimentos contidos: o cabelo e os panos do vestido presos aos braços e às pernas esticam se for muito)
        P.add(s + 'UpLeg', (X, -28 * curl)); P.add(s + 'Leg', (X, 40 * curl)); P.add(s + 'Foot', (X, 15 * curl))
        P.add(s + 'Arm', (Z, sg * 18 * curl), (X, -15 * curl), (Y, sg * -28 * arch))
        P.add(s + 'ForeArm', (Z, sg * 30 * curl), (Y, sg * -12 * arch))
    wings(P, flap=lerp(-40, 55, beat) * (1 - settle) + (-12) * settle, fold=1 - unfold, sweep=10 * beat, scale=max(0.02, min(1.1, grow)))
    P.s['Halo'] = max(0.0, back_out((t - 0.45) / 0.25, 2.2)) if t > 0.45 else 0.0
    float_body(P, t, 0.6 + 0.6 * beat)
    # emenda com o pairando no fim
    if settle > 0:
        for n, rots in idle.r.items():
            if n.endswith('Wing1') or n.endswith('WingTip') or n.endswith('WingLow'): continue
            P.r[n] = [(a, d * (1 - settle)) for a, d in P.r[n]] + [(a, d * settle) for a, d in rots]
    return P

def pose_recolher(arm, t):
    """pousando: as asas param, fecham nas costas e encolhem até sumir; a auréola apaga; pernas descem."""
    P = Pose(arm)
    fold = sm(t / 0.6); shrink = 1 - sm((t - 0.45) / 0.45)
    wings(P, flap=-12 * (1 - fold) + 10 * math.sin(math.pi * min(1, t / 0.3)), fold=fold, scale=max(0.02, shrink))
    P.s['Halo'] = max(0.0, 1 - sm((t - 0.2) / 0.5))
    land = sm(t / 0.7)
    for s in ('Left', 'Right'):
        P.add(s + 'UpLeg', (X, -6 * (1 - land))); P.add(s + 'Leg', (X, 10 * (1 - land)))
    float_body(P, t, 0.6 * (1 - land))
    return P

def lerp(a, b, t): return a + (b - a) * t

def bake(arm, name, fn, frames, loop=True, step=1):
    act = lib.new_action(arm, name)
    keys = list(range(0, frames + 1, step))
    if keys[-1] != frames: keys.append(frames)
    for f in keys:
        t = (f / frames) % 1.0 if loop else f / frames
        P = fn(arm, t)
        lib.key_pose(arm, f + 1, P.r, P.loc)
        for n, s in P.s.items():
            pb = arm.pose.bones[n]; pb.scale = (s, s, s); pb.keyframe_insert('scale', frame=f + 1)
    lib.push_nla(arm, act)
    for pb in arm.pose.bones: pb.scale = (1, 1, 1)

def main():
    bpy.ops.wm.open_mainfile(filepath=SRC)
    obj = bpy.data.objects['kaira_asas_src']; obj.name = 'kaira_asas'
    hair, halo, wing, xs = classify(obj)
    for v in obj.data.vertices: v.co = T(*v.co)
    obj.data.update()
    arm = build_rig()
    assign(obj, arm, hair, halo, wing, xs)
    smooth_weights(obj)
    lib.bind(obj, arm)
    mat = obj.active_material; mat.name = 'kaira_asas'
    mat['ramp'] = 'soft'; mat['rim'] = 0.35; mat['noOutline'] = True
    bsdf = [n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'][0]
    for inp in ('Metallic', 'Roughness'):
        for l in list(bsdf.inputs[inp].links): mat.node_tree.links.remove(l)
    bsdf.inputs['Metallic'].default_value = 0.0; bsdf.inputs['Roughness'].default_value = 0.8
    for img in bpy.data.images:
        if img.size[0] > 2048: img.scale(2048, 2048)
    bpy.context.scene.render.fps = 30
    bake(arm, 'revelar', pose_revelar, 60, loop=False)
    bake(arm, 'fly_idle', pose_fly_idle, 48)
    bake(arm, 'fly', pose_fly, 40)
    bake(arm, 'recolher', pose_recolher, 36, loop=False)
    print('triângulos', lib.tri_count(obj))
    for o in bpy.context.scene.objects: o.select_set(o in (obj, arm))
    bpy.ops.export_scene.gltf(
        filepath=os.path.join(OUT, 'char_kaira_asas.glb'), export_format='GLB', use_selection=True,
        export_extras=True, export_animations=True, export_animation_mode='NLA_TRACKS', export_force_sampling=True,
        export_skins=True, export_def_bones=False, export_image_format='JPEG', export_jpeg_quality=88)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT, 'fontes', 'blender', 'kaira_asas_rig.blend'))

if __name__ == '__main__':
    main()
