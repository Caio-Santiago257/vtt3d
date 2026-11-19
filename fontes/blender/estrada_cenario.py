"""Kit do mapa "Encruzilhada da Floresta", modelado no Blender: cada peça vira um nó do GLB e o jogo espalha
cópias (instâncias) nas posições de fontes/mapas/estrada_gerar.py.

Peças (medidas em unidades do jogo: 1 unidade = 0,75 m; a base de cada peça fica no chão, em y = 0):
  pinho_a / pinho_b / pinho_c   pinheiros de 18, 14 e 10 m: tronco com casca e verticilos de ramos em cartões
                                dobrados em V (cheios vistos de cima e de lado), que pendem mais na base
  pinho_longe                   o mesmo pinheiro bem mais leve, para a mata ao redor do mapa
  arvore_outono                 árvore de copa redonda alaranjada (tronco, galhos e cartões de folhas)
  arbusto_amarelo / _verde      moitas de folhas
  arvore_morta                  árvore seca e branca, de galhos retorcidos
  pedra_1..4, seixo_1..2        pedras grandes e pequenas (deformadas por ruído, com musgo da textura)
  bloco_1..3, blocos_monte      blocos de pedra talhada do meio-fio, soltos e empilhados
  tronco_caido, toco            tronco caído com galhos quebrados e toco com raízes
  samambaia, flores, capim      plantas rasteiras em cartões
  placa                         placa de madeira da encruzilhada, com duas setas e uma escora
As texturas não vão dentro do GLB: cada material leva em "extras" qual textura da pasta tex/ usar e se é um
cartão (transparência recortada), se balança com o vento e se é copa (fica translúcida na vista do mestre).
Coordenadas: o jogo usa x, altura, z; no Blender isso é (x, -z, altura).

Rodar: python3 fontes/blender/estrada_cenario.py      (salva também fontes/blender/estrada_kit.blend)
"""
import math, os
import numpy as np
import bpy
from mathutils import noise, Vector

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
TEX = os.path.join(ROOT, 'public', 'assets', 'maps', 'estrada', 'tex')
OUT = os.path.join(ROOT, 'public', 'assets', 'maps', 'estrada', 'kit.glb')
BLEND = os.path.join(ROOT, 'fontes', 'blender', 'estrada_kit.blend')

def sock(node, name, out=False):
    """socket visível com esse nome (o nó Mix tem A/B repetidos para cada tipo de dado)."""
    for x in (node.outputs if out else node.inputs):
        if x.name == name and x.enabled: return x
    raise KeyError(name)
rng = np.random.default_rng(321)
TAU = 2 * math.pi

# ---------------------------------------------------------------- materiais (com a textura de verdade, para a prévia no Blender)
MATS = {}
def material(name, tex, card=False, color=(1, 1, 1), rough=0.9, **extras):
    if name in MATS: return MATS[name]
    m = bpy.data.materials.new('estrada_' + name); m.use_nodes = True
    nt = m.node_tree; bsdf = nt.nodes['Principled BSDF']
    ext = 'png' if card else 'jpg'
    img = bpy.data.images.load(os.path.join(TEX, f'{tex}.{ext}'), check_existing=True)
    tn = nt.nodes.new('ShaderNodeTexImage'); tn.image = img
    mix = nt.nodes.new('ShaderNodeMix'); mix.data_type = 'RGBA'; mix.blend_type = 'MULTIPLY'; mix.inputs['Factor'].default_value = 1.0
    sock(mix, 'B').default_value = (*color, 1)
    nt.links.new(tn.outputs['Color'], sock(mix, 'A')); nt.links.new(sock(mix, 'Result', True), bsdf.inputs['Base Color'])
    bsdf.inputs['Roughness'].default_value = rough
    if card:
        nt.links.new(tn.outputs['Alpha'], bsdf.inputs['Alpha'])
        try: m.surface_render_method = 'DITHERED'
        except Exception: pass
        m.use_backface_culling = False
    m['tex'] = tex; m['card'] = 1 if card else 0; m['tint'] = [round(c, 3) for c in color]
    for k, v in extras.items(): m[k] = v
    MATS[name] = m; return m

def M():
    return dict(
        casca=material('casca', 'casca', rough=0.95),
        casca_morta=material('casca_morta', 'casca_morta', rough=0.9),
        ramo=material('ramo', 'ramo_pinho', card=True, vento=0.006, copa=1),
        ramo_longe=material('ramo_longe', 'ramo_pinho', card=True, color=(0.92, 0.95, 0.92), vento=0.004, copa=1),
        outono=material('outono', 'folhas_outono', card=True, vento=0.008, copa=1),
        amarelo=material('amarelo', 'folhas_amarelas', card=True, vento=0.035),
        verde=material('verde', 'folhas_verdes', card=True, vento=0.035),
        rocha=material('rocha', 'rocha', rough=0.85, normal='rocha_n'),
        bloco=material('bloco', 'rocha', color=(0.95, 0.9, 0.8), rough=0.85, normal='rocha_n'),
        madeira=material('madeira', 'madeira', rough=0.9),
        samambaia=material('samambaia', 'samambaia', card=True, vento=0.1),
        flores=material('flores', 'flores', card=True, vento=0.06),
        capim=material('capim', 'capim', card=True, vento=0.15),
    )

# ---------------------------------------------------------------- montagem de malhas (coordenadas do jogo)
class Part:
    def __init__(self): self.V, self.F, self.UV, self.MI = [], [], [], []; self.mats = []
    def mi(self, mat):
        if mat not in self.mats: self.mats.append(mat)
        return self.mats.index(mat)
    def add(self, V, F, UV, mat):
        b = len(self.V); k = self.mi(mat)
        self.V += [tuple(map(float, v)) for v in V]
        for f, uv in zip(F, UV): self.F.append([i + b for i in f]); self.UV.append(uv); self.MI.append(k)
    def tris(self): return sum(len(f) - 2 for f in self.F)

def to_obj(name, P, smooth=True):
    V = np.array(P.V)
    me = bpy.data.meshes.new(name)
    me.from_pydata(np.stack([V[:, 0], -V[:, 2], V[:, 1]], 1).tolist(), [], P.F); me.update()
    uvl = me.uv_layers.new(name='UVMap')
    for poly, uv in zip(me.polygons, P.UV):
        for li, (u, v) in zip(poly.loop_indices, uv): uvl.data[li].uv = (u, v)
    for m in P.mats: me.materials.append(m)
    for poly, k in zip(me.polygons, P.MI): poly.material_index = k; poly.use_smooth = smooth
    o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o)
    return o

def tube(P, pts, radii, n, mat, vscale=3.0, ustretch=1.0, cap=True, wob=0.0):
    """tubo por uma linha de pontos (troncos e galhos). UV: u em volta, v ao longo (em unidades / vscale)."""
    pts = [np.asarray(p, float) for p in pts]
    rings = []; L = 0.0; vs = []
    for i, p in enumerate(pts):
        t = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]); t /= np.linalg.norm(t) + 1e-9
        a = np.cross(t, [0, 1, 0] if abs(t[1]) < 0.95 else [1, 0, 0]); a /= np.linalg.norm(a); b = np.cross(t, a)
        if i: L += np.linalg.norm(p - pts[i - 1])
        ring = []
        for k in range(n + 1):
            th = TAU * k / n; rr = radii[i] * (1 + wob * (noise.noise(Vector((p[0] * 2 + math.cos(th), p[1] * 2, p[2] * 2 + math.sin(th)))) ))
            ring.append(p + (a * math.cos(th) + b * math.sin(th)) * rr)
        rings.append(ring); vs.append(L / vscale)
    V = [v for r in rings for v in r]; F = []; UV = []
    for i in range(len(rings) - 1):
        for k in range(n):
            a0 = i * (n + 1) + k
            F.append([a0, a0 + 1, a0 + n + 2, a0 + n + 1])
            UV.append([(k / n * ustretch, vs[i]), ((k + 1) / n * ustretch, vs[i]), ((k + 1) / n * ustretch, vs[i + 1]), (k / n * ustretch, vs[i + 1])])
    if cap and radii[-1] > 0.02:
        c = len(V); V.append(pts[-1] + (pts[-1] - pts[-2]) / (np.linalg.norm(pts[-1] - pts[-2]) + 1e-9) * radii[-1] * 0.3)
        last = (len(rings) - 1) * (n + 1)
        for k in range(n):
            F.append([last + k, last + k + 1, c]); UV.append([(k / n, vs[-1]), ((k + 1) / n, vs[-1]), ((k + 0.5) / n, vs[-1] + 0.05)])
    P.add(V, F, UV, mat)

def card_strip(P, base, d_h, up, L, W, pitch0, droop, segs, fold, mat, u0=0.0, u1=1.0):
    """cartão de ramo: sai da base na direção horizontal d_h, inclinado pitch0 e pendendo (droop) até a ponta.
    Dobrado em V ao longo do meio (fold = altura da dobra, proporcional à largura)."""
    side = np.cross(up, d_h); side /= np.linalg.norm(side)
    rows = []; p = np.array(base, float)
    for s in range(segs + 1):
        t = s / segs
        if s:
            pitch = pitch0 - droop * (t - 0.5 / segs)
            p = p + (d_h * math.cos(pitch) + up * math.sin(pitch)) * (L / segs)
        w = W * (0.35 + 0.65 * math.sin(math.pi * min(1, 0.15 + t * 0.95))) * 0.5
        c = p + up * fold * w
        rows.append([p - side * w, c, p + side * w])
    V = [v for r in rows for v in r]; F = []; UV = []
    for s in range(segs):
        v0, v1 = s / segs, (s + 1) / segs
        for k in range(2):
            a = s * 3 + k
            F.append([a, a + 1, a + 4, a + 3])
            ua, ub = u0 + (u1 - u0) * k / 2, u0 + (u1 - u0) * (k + 1) / 2
            UV.append([(ua, v0), (ub, v0), (ub, v1), (ua, v1)])
    P.add(V, F, UV, mat)

def quad(P, c, a, b, mat, uv=((0, 0), (1, 0), (1, 1), (0, 1))):
    """quadrado centrado em c com meias-direções a e b."""
    c, a, b = map(np.asarray, (c, a, b))
    P.add([c - a - b, c + a - b, c + a + b, c - a + b], [[0, 1, 2, 3]], [list(uv)], mat)

def rnd_dir():
    v = rng.normal(size=3); return v / np.linalg.norm(v)

UP = np.array([0.0, 1.0, 0.0])

# ---------------------------------------------------------------- pinheiros
def pinho(name, H, R, mats, lod=False, seed=0):
    global rng
    rng = np.random.default_rng(seed)
    P = Part()
    rb = 0.018 * H + 0.12
    n = 5 if lod else 8
    bend = rng.normal(0, 0.012, 2) * H
    zs = np.linspace(0, H, 6)
    pts = [(bend[0] * (z / H) ** 2, z, bend[1] * (z / H) ** 2) for z in zs]
    tube(P, [(0, -0.5, 0)] + pts, [rb * 1.25] + [rb * (1 - 0.9 * (z / H)) + 0.04 for z in zs], n, mats['casca'], vscale=5.0, ustretch=3.0, wob=0.0 if lod else 0.12)
    mat = mats['ramo_longe' if lod else 'ramo']
    step = 2.0 if lod else 0.85
    z0 = 0.2 * H if lod else 0.32 * H        # na mata o tronco fica limpo embaixo (dá para andar e ver por baixo das copas)
    z = z0; az0 = rng.uniform(0, TAU)
    while z < H * 0.97:
        t = (z - z0) / (H - z0)
        L = R * (1 - t) ** 0.9 + 0.7
        nb = (5 if lod else (8 if t < 0.55 else 6))
        az0 += 2.39996
        for k in range(nb):
            az = az0 + TAU * k / nb + rng.normal(0, 0.18)
            d = np.array([math.cos(az), 0, math.sin(az)])
            cz = bend[0] * (z / H) ** 2, bend[1] * (z / H) ** 2
            base = np.array([cz[0], z, cz[1]]) + d * rb * (1 - 0.9 * z / H) * 0.6
            pitch0 = math.radians(rng.uniform(4, 18) - 22 * (1 - t))
            droop = math.radians(14 + 16 * (1 - t))
            Lk = L * rng.uniform(0.85, 1.12)
            card_strip(P, base, d, UP, Lk, Lk * (1.25 if lod else 1.05), pitch0, droop, 1 if lod else 2, 0.0 if lod else 0.3, mat)
        z += step * (0.8 + 0.4 * rng.random()) * (1.0 - 0.35 * t)
    # ponta: dois cartões cruzados para cima
    top = np.array([bend[0], H * 0.94, bend[1]])
    for a in (0, math.pi / 2):
        d = np.array([math.cos(a), 0, math.sin(a)])
        P.add([top - d * 0.55, top + d * 0.55, top + d * 0.4 + UP * 2.2, top - d * 0.4 + UP * 2.2], [[0, 1, 2, 3]], [[(0, 0), (1, 0), (1, 1), (0, 1)]], mat)
    return to_obj(name, P)

# ---------------------------------------------------------------- copas de folhas (árvore de outono, arbustos)
def crown(P, center, radii, count, size, mat):
    for _ in range(count):
        d = rnd_dir(); r = rng.uniform(0.45, 1.0) ** 0.5
        p = np.asarray(center) + d * np.asarray(radii) * r
        nrm = d * 0.7 + rnd_dir() * 0.5; nrm /= np.linalg.norm(nrm)
        a = np.cross(nrm, UP if abs(nrm[1]) < 0.9 else [1, 0, 0]); a /= np.linalg.norm(a); b = np.cross(nrm, a)
        rot = rng.uniform(0, TAU); a, b = a * math.cos(rot) + b * math.sin(rot), -a * math.sin(rot) + b * math.cos(rot)
        s = size * rng.uniform(0.75, 1.2) * 0.5
        quad(P, p, a * s, b * s, mat)

def arvore_outono(mats):
    global rng
    rng = np.random.default_rng(11); P = Part()
    tube(P, [(0, -0.4, 0), (0, 0, 0), (0.1, 3, 0.05), (0.2, 6, -0.1)], [0.75, 0.6, 0.48, 0.38], 9, mats['casca'], vscale=3.0, ustretch=2, wob=0.15)
    for k in range(5):
        az = k * TAU / 5 + rng.normal(0, 0.3); d = np.array([math.cos(az), 0, math.sin(az)])
        b0 = np.array([0.2, 5.0 + k * 0.3, -0.1])
        tube(P, [b0, b0 + d * 1.6 + UP * 2.0, b0 + d * 3.0 + UP * 3.4], [0.32, 0.2, 0.08], 6, mats['casca'], vscale=3.0)
    crown(P, (0.2, 10.2, 0), (5.4, 4.4, 5.4), 230, 2.5, mats['outono'])
    crown(P, (0.2, 10.0, 0), (3.2, 3.0, 3.2), 50, 2.6, mats['outono'])
    return to_obj('arvore_outono', P)

def arbusto(name, mat, seed):
    global rng
    rng = np.random.default_rng(seed); P = Part()
    crown(P, (0, 1.5, 0), (2.7, 1.7, 2.7), 70, 1.9, mat)
    crown(P, (0, 1.1, 0), (1.5, 1.0, 1.5), 16, 1.8, mat)
    return to_obj(name, P)

# ---------------------------------------------------------------- árvore morta
def arvore_morta(mats):
    global rng
    rng = np.random.default_rng(23); P = Part()
    def branch(p0, d, L, r, depth):
        pts = [np.array(p0, float)]; rad = [r]
        segs = 5
        for s in range(segs):
            d = d + rnd_dir() * 0.35 + UP * (0.15 if depth < 2 else -0.05); d /= np.linalg.norm(d)
            pts.append(pts[-1] + d * L / segs); rad.append(r * (1 - 0.8 * (s + 1) / segs) + 0.02)
        tube(P, pts, rad, 7 if depth == 0 else 5, mats['casca_morta'], vscale=2.5, wob=0.2 if depth == 0 else 0.0)
        if depth < 3:
            for k in range(2 if depth else 3):
                i = rng.integers(2, segs)
                nd = d + rnd_dir() * 0.9 + UP * 0.2; nd /= np.linalg.norm(nd)
                branch(pts[i], nd, L * rng.uniform(0.45, 0.65), rad[i] * 0.65, depth + 1)
    # raízes que agarram o chão
    for k in range(4):
        az = k * TAU / 4 + rng.normal(0, 0.3); d = np.array([math.cos(az), 0, math.sin(az)])
        tube(P, [UP * 1.2, d * 0.9 + UP * 0.3, d * 2.0 - UP * 0.25], [0.45, 0.3, 0.06], 6, mats['casca_morta'], vscale=2.5)
    branch((0, -0.3, 0), np.array([0.1, 1, 0.05]), 9.5, 0.7, 0)
    return to_obj('arvore_morta', P)

# ---------------------------------------------------------------- pedras
def pedra(name, size, seed, mat, detail=4, flat=0.6):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=detail, radius=1.0)
    o = bpy.context.active_object; o.name = name
    off = Vector((seed * 7.1, seed * 3.3, seed * 1.7))
    sx, sy, sz = size
    for v in o.data.vertices:
        p = v.co.copy()
        n1 = noise.fractal(p * 1.1 + off, 0.5, 2.0, 4) * 0.32
        n2 = noise.ridged_multi_fractal(p * 2.2 + off, 0.8, 2.2, 3, 1.0, 2.0) * 0.06
        q = p * (1 + n1 + n2)
        # facetas: achata em alguns planos (pedra partida)
        for pl in range(3):
            nn = Vector(noise.random_unit_vector()) if False else Vector((math.cos(seed + pl * 2.1), math.sin(seed + pl * 2.1), 0.3 * pl - 0.2)).normalized()
            dd = q.dot(nn) - 0.78
            if dd > 0: q -= nn * dd * 0.85
        v.co = Vector((q.x * sx, q.y * sy, max(q.z * sz, -sz * flat)))
    for v in o.data.vertices: v.co.z += sz * flat * 0.8
    mod = o.modifiers.new('dec', 'DECIMATE'); mod.ratio = 0.35
    bpy.ops.object.modifier_apply(modifier='dec')
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=1.15, island_margin=0.01, scale_to_bounds=False)
    bpy.ops.object.mode_set(mode='OBJECT')
    # UV em escala de mundo (textura repete a cada ~3 unidades)
    me = o.data
    uvl = me.uv_layers.active
    k = max(sx, sy, sz) / 1.6
    for l in uvl.data: l.uv = (l.uv[0] * k * 2, l.uv[1] * k * 2)
    me.materials.append(mat)
    for poly in me.polygons: poly.use_smooth = True
    return o

def bloco(name, dims, seed, mat):
    bpy.ops.mesh.primitive_cube_add(size=1.0)
    o = bpy.context.active_object; o.name = name
    o.scale = dims; bpy.ops.object.transform_apply(scale=True)
    mod = o.modifiers.new('bev', 'BEVEL'); mod.width = min(dims) * 0.12; mod.segments = 2
    bpy.ops.object.modifier_apply(modifier='bev')
    r = np.random.default_rng(seed)
    for v in o.data.vertices:
        v.co += Vector(r.normal(0, 0.025, 3)); v.co.z += dims[2] * 0.42
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.cube_project(cube_size=2.5); bpy.ops.object.mode_set(mode='OBJECT')
    o.data.materials.append(mat)
    return o

def blocos_monte(mat):
    objs = []
    spots = [((0, 0, 0), (1.1, 0.75, 0.55), 0.2), ((0.9, 0.3, 0), (0.9, 0.6, 0.5), -0.4), ((0.35, 0.1, 0.5), (0.95, 0.65, 0.5), 0.6),
             ((-0.7, 0.5, 0), (0.7, 0.55, 0.45), 1.1), ((0.3, 0.9, 0), (0.6, 0.5, 0.4), 0.3)]
    for i, (p, d, rz) in enumerate(spots):
        o = bloco('bm%d' % i, d, 50 + i, mat); o.location = p; o.rotation_euler = (rng.normal(0, 0.12), rng.normal(0, 0.12), rz); objs.append(o)
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs: o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    bpy.ops.object.join(); o = bpy.context.active_object; o.name = 'blocos_monte'
    return o

# ---------------------------------------------------------------- troncos, toco, placa
def tronco_caido(mats):
    global rng
    rng = np.random.default_rng(31); P = Part()
    L = 7.5
    pts = [(-L / 2, 0.42, 0), (-L / 6, 0.45, 0.1), (L / 6, 0.42, -0.05), (L / 2, 0.38, 0.05)]
    tube(P, pts, [0.5, 0.48, 0.44, 0.4], 9, mats['casca'], vscale=2.5, cap=False, wob=0.1)
    for x, r in ((-L / 2, 0.5), (L / 2, 0.4)):     # pontas serradas/quebradas com a madeira à mostra
        c = np.array([x, pts[0][1] if x < 0 else pts[-1][1], 0 if x < 0 else 0.05]); V = [c]; F = []; UV = []
        for k in range(9):
            th = TAU * k / 9; V.append(c + np.array([0, math.cos(th), math.sin(th)]) * r)
        for k in range(9): F.append([0, 1 + k, 1 + (k + 1) % 9] if x > 0 else [0, 1 + (k + 1) % 9, 1 + k]); UV.append([(0.5, 0.5), (0.5 + 0.4 * math.cos(TAU * k / 9), 0.5 + 0.4 * math.sin(TAU * k / 9)), (0.5 + 0.4 * math.cos(TAU * (k + 1) / 9), 0.5 + 0.4 * math.sin(TAU * (k + 1) / 9))])
        P.add(V, F, UV, mats['madeira'])
    for k in range(4):                               # galhos quebrados
        x = rng.uniform(-L / 2.5, L / 2.5); b0 = np.array([x, 0.6, 0]); d = np.array([rng.normal(0, 0.3), rng.uniform(0.4, 1), rng.choice([-1, 1]) * rng.uniform(0.4, 1)]); d /= np.linalg.norm(d)
        tube(P, [b0, b0 + d * rng.uniform(0.8, 1.6)], [0.13, 0.05], 5, mats['casca'], vscale=2.0)
    return to_obj('tronco_caido', P)

def toco(mats):
    global rng
    rng = np.random.default_rng(41); P = Part()
    tube(P, [(0, -0.3, 0), (0, 0.4, 0), (0, 0.9, 0)], [0.85, 0.62, 0.58], 10, mats['casca'], vscale=2.0, cap=False, wob=0.15)
    c = np.array([0, 0.9, 0]); V = [c]; F = []; UV = []
    for k in range(10):
        th = TAU * k / 10; V.append(c + np.array([math.cos(th), rng.uniform(-0.06, 0.06), math.sin(th)]) * 0.58)
    for k in range(10):
        F.append([0, 1 + (k + 1) % 10, 1 + k]); UV.append([(0.5, 0.5), (0.5 + 0.45 * math.cos(TAU * (k + 1) / 10), 0.5 + 0.45 * math.sin(TAU * (k + 1) / 10)), (0.5 + 0.45 * math.cos(TAU * k / 10), 0.5 + 0.45 * math.sin(TAU * k / 10))])
    P.add(V, F, UV, mats['madeira'])
    for k in range(5):
        az = k * TAU / 5 + rng.normal(0, 0.3); d = np.array([math.cos(az), 0, math.sin(az)])
        tube(P, [UP * 0.5 + d * 0.4, d * 1.0 + UP * 0.1, d * 1.6 - UP * 0.25], [0.3, 0.18, 0.04], 6, mats['casca'], vscale=2.0)
    return to_obj('toco', P)

def caixa(P, c, size, mat, ry=0.0, rz=0.0, vscale=2.0):
    """bloco de madeira (x = comprimento) com UV pela madeira; ry gira em volta do eixo vertical, rz inclina."""
    sx, sy, sz = [s / 2 for s in size]
    pts = np.array([[x, y, z] for x in (-sx, sx) for y in (-sy, sy) for z in (-sz, sz)])
    cz, sz_ = math.cos(rz), math.sin(rz)
    pts = pts @ np.array([[cz, sz_, 0], [-sz_, cz, 0], [0, 0, 1]])
    cy, sy_ = math.cos(ry), math.sin(ry)
    pts = pts @ np.array([[cy, 0, -sy_], [0, 1, 0], [sy_, 0, cy]]) + np.asarray(c)
    faces = [[0, 1, 3, 2], [4, 6, 7, 5], [0, 4, 5, 1], [2, 3, 7, 6], [0, 2, 6, 4], [1, 5, 7, 3]]
    L = size[0] / vscale
    P.add(pts, faces, [[(0, 0), (0.25, 0), (0.25, L), (0, L)]] * 6, mat)

def placa(mats):
    P = Part(); m = mats['madeira']
    caixa(P, (0, 2.4, 0), (5.4, 0.32, 0.32), m, rz=math.pi / 2)          # poste (deitado no x e girado para cima)
    caixa(P, (0.9, 4.25, 0), (2.9, 0.62, 0.12), m, ry=0.0)                # seta 1
    caixa(P, (-0.6, 3.5, 0.12), (2.6, 0.58, 0.12), m, ry=2.4)             # seta 2, para outro lado
    caixa(P, (0.0, 1.6, 0.0), (2.6, 0.22, 0.16), m, ry=1.2, rz=0.75)      # escora inclinada (como na referência)
    # pontas das setas
    for (x, y, z, ry) in ((2.35, 4.25, 0, 0.0), (-1.55, 3.5, 0.95, 2.4)):
        d = np.array([math.cos(ry), 0, -math.sin(ry)]); s = np.array([0, 0.38, 0]); c = np.array([x, y, z])
        n_ = np.cross(d, UP) * 0.065
        for off in (n_, -n_):
            P.add([c - s + off, c + d * 0.45 + off, c + s + off], [[0, 1, 2]], [[(0, 0), (0.2, 0.1), (0, 0.2)]], m)
    return to_obj('placa', P, smooth=False)

# ---------------------------------------------------------------- plantas rasteiras
def samambaia(mats):
    global rng
    rng = np.random.default_rng(61); P = Part()
    for k in range(7):
        az = k * TAU / 7 + rng.normal(0, 0.2); d = np.array([math.cos(az), 0, math.sin(az)])
        L = rng.uniform(1.3, 1.8)
        card_strip(P, d * 0.05, d, UP, L, L * 0.62, math.radians(rng.uniform(40, 60)), math.radians(rng.uniform(90, 120)), 3, 0.15, mats['samambaia'])
    return to_obj('samambaia', P)

def flores(mats):
    global rng
    rng = np.random.default_rng(71); P = Part()
    for k in range(4):
        az = k * TAU / 4 + 0.3; d = np.array([math.cos(az), 0, math.sin(az)]); s = np.cross(UP, d)
        c = d * 0.5 + UP * 0.28
        a = d * 0.95 * math.cos(0.35) + UP * 0.95 * math.sin(0.35); b = s * 0.95
        quad(P, c, a, b, mats['flores'])
    quad(P, UP * 0.3, np.array([0.6, 0, 0]), np.array([0, 0, 0.6]), mats['flores'])
    return to_obj('flores', P)

def capim(mats):
    P = Part()
    for k in range(3):
        az = k * math.pi / 3; d = np.array([math.cos(az), 0, math.sin(az)])
        quad(P, UP * 0.55, d * 0.6, UP * 0.6, mats['capim'])
    return to_obj('capim', P)

# ---------------------------------------------------------------- tudo
def main():
    for o in list(bpy.data.objects): bpy.data.objects.remove(o)
    mats = M()
    objs = []
    objs.append(pinho('pinho_a', 24, 6.6, mats, seed=1))
    objs.append(pinho('pinho_b', 19, 5.4, mats, seed=2))
    objs.append(pinho('pinho_c', 14, 4.2, mats, seed=3))
    objs.append(pinho('pinho_longe', 22, 6.4, mats, lod=True, seed=4))
    objs.append(arvore_outono(mats))
    objs.append(arbusto('arbusto_amarelo', mats['amarelo'], 81))
    objs.append(arbusto('arbusto_verde', mats['verde'], 82))
    objs.append(arvore_morta(mats))
    for i, (sz, fl) in enumerate([((2.0, 1.6, 1.3), 0.55), ((1.6, 1.4, 1.6), 0.5), ((2.4, 1.5, 1.0), 0.6), ((1.5, 1.7, 1.2), 0.5)]):
        objs.append(pedra('pedra_%d' % (i + 1), sz, i * 13 + 5, mats['rocha'], 4, fl))
    for i, sz in enumerate([(0.55, 0.45, 0.32), (0.4, 0.5, 0.28)]):
        objs.append(pedra('seixo_%d' % (i + 1), sz, i * 17 + 9, mats['rocha'], 2, 0.5))
    for i, d in enumerate([(1.0, 0.7, 0.5), (0.8, 0.6, 0.45), (1.2, 0.5, 0.45)]):
        objs.append(bloco('bloco_%d' % (i + 1), d, 40 + i, mats['bloco']))
    objs.append(blocos_monte(mats['bloco']))
    objs.append(tronco_caido(mats)); objs.append(toco(mats))
    objs.append(placa(mats))
    objs += [samambaia(mats), flores(mats), capim(mats)]
    total = 0
    for i, o in enumerate(objs):
        o.location = ((i % 6) * 14.0, -(i // 6) * 14.0, 0)       # lado a lado na cena (o jogo usa só a forma)
        bpy.context.view_layer.update()
        t = sum(len(p.vertices) - 2 for p in o.data.polygons); total += t
        print('  %-16s %6d triângulos' % (o.name, t))
    print('kit: %d peças, %d triângulos' % (len(objs), total))
    bpy.ops.wm.save_as_mainfile(filepath=BLEND)
    for o in objs: o.location = (0, 0, 0)
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs: o.select_set(True)
    bpy.ops.export_scene.gltf(filepath=OUT, export_format='GLB', use_selection=True, export_extras=True, export_materials='EXPORT',
                              export_image_format='NONE', export_apply=True, export_yup=True)
    print('GLB: %.2f MB' % (os.path.getsize(OUT) / 1e6))

if __name__ == '__main__':
    main()
