"""Fundos panorâmicos dos biomas do terreno pintado (aba Construir > Terreno), renderizados no Blender (Cycles).

Cada bioma ganha uma paisagem em volta do mapa, para ele não parecer uma caixa flutuando no escuro:
  floresta  colinas verdes com mata de pinheiros e árvores de copa redonda, serra azulada, céu de meio-dia
  pantano   charco plano com espelhos d'água, árvores mortas e mata escura, névoa esverdeada, céu nublado
  deserto   dunas, mesas de rocha avermelhada e uma serra árida, céu limpo e quente
  neve      campo nevado, pinheiros e montanhas brancas, céu claro de inverno
  caverna   salão de caverna: paredões e teto de rocha, estalagmites e cristais azuis que brilham
  masmorra  salão de pedra: paredes de blocos, arcos, colunas e tochas acesas
(A Estrada na mata usa o fundo da Encruzilhada da Floresta, feito em estrada_fundo.py, e o Covil usa o fundo do covil.)

A câmera fica no meio, a 6 unidades do chão, e a faixa equiretangular é reprojetada para o cilindro do jogo
(raio 300, de -30 a +180 de altura), com o topo transparente para emendar com o céu do jogo.
A névoa de cada fundo usa a cor da névoa do bioma no jogo, para o chão do mapa emendar com o fundo.

Rodar: python3 fontes/blender/fundos_biomas.py [bioma ...]      (AMOSTRAS=24 LARGURA=4096; uns 3 min por bioma)
Saída: public/assets/terreno/fundos/<bioma>.webp
"""
import math, os, sys
import numpy as np
import bpy
from mathutils import Vector, noise

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
KIT = os.path.join(ROOT, 'fontes', 'blender', 'estrada_kit.blend')
TEX = os.path.join(ROOT, 'public', 'assets', 'maps', 'estrada', 'tex')
OUTDIR = os.path.join(ROOT, 'public', 'assets', 'terreno', 'fundos')
SAMPLES = int(os.environ.get('AMOSTRAS', '24'))
WIDTH = int(os.environ.get('LARGURA', '4096'))
LAT0, LAT1, EYE = -9.0, 36.0, 6.0

def hexc(h): return tuple(((h >> s) & 255) / 255 for s in (16, 8, 0))
def lin(c): return tuple(x ** 2.2 for x in c)

PRESETS = {
    'floresta': dict(haze=0xc4e6f2, near=250, far=3200, maxk=0.85, sky='sol', sun=42, rot=200, skyk=0.32,
                     g0=(0.03, 0.065, 0.012), g1=(0.08, 0.13, 0.025), hills=80, ridge=700, ridgecol=(0.06, 0.08, 0.06),
                     trees=[('pinho_a', 0.3), ('pinho_b', 0.25), ('verde', 0.45)], ring=(170, 650), dens=1.0, cones=(0.025, 0.07, 0.02), groves=260, hillwood=5000),
    'pantano': dict(haze=0x4f6a58, near=140, far=1800, maxk=0.86, sky='nublado', sun=14, rot=150, skyk=0.12,
                    g0=(0.05, 0.06, 0.025), g1=(0.12, 0.14, 0.05), hills=12, ridge=180, ridgecol=(0.05, 0.06, 0.04), water=-0.6,
                    trees=[('arvore_morta', 0.45), ('pinho_longe', 0.35), ('arbusto_verde', 0.2)], ring=(160, 520), dens=0.75, cones=(0.02, 0.035, 0.02), groves=180, hillwood=2500),
    'deserto': dict(haze=0xf3dcae, near=350, far=4000, maxk=0.8, sky='sol', sun=58, rot=120, skyk=0.38,
                    g0=(0.36, 0.24, 0.11), g1=(0.58, 0.42, 0.22), hills=30, dunes=True, ridge=520, ridgecol=(0.35, 0.18, 0.09),
                    trees=[('arvore_morta', 1.0)], ring=(200, 700), dens=0.05, mesas=70, cones=None, groves=0, hillwood=0),
    'neve': dict(haze=0xdbe7f2, near=220, far=2800, maxk=0.85, sky='sol', sun=18, rot=230, skyk=0.28,
                 g0=(0.62, 0.68, 0.76), g1=(0.86, 0.9, 0.95), hills=60, ridge=900, ridgecol=(0.8, 0.84, 0.9), rockpeaks=True,
                 trees=[('pinho_a', 0.35), ('pinho_b', 0.35), ('pinho_longe', 0.3)], ring=(170, 600), dens=0.7, cones=(0.02, 0.04, 0.035), groves=200, hillwood=3500, snowtrees=True),
    'caverna': dict(cave=True, haze=0x090812, near=90, far=520, maxk=0.75, rock=(0.13, 0.12, 0.16), crystal=(0.3, 0.75, 1.0), stal=900),
    'masmorra': dict(hall=True, haze=0x07070d, near=60, far=380, maxk=0.85, rock=(0.09, 0.085, 0.09), torch=(1.0, 0.55, 0.2)),
}

def sock(node, name, out=False):
    for x in (node.outputs if out else node.inputs):
        if x.name == name and x.enabled: return x
    raise KeyError(name)

def haze_mix(mat, P):
    """mistura a cor da névoa do bioma pela distância até a câmera (sem deixar opaco o recorte das folhas)."""
    nt = mat.node_tree; out = [n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL'][0]
    src = out.inputs['Surface'].links[0].from_socket
    cam = nt.nodes.new('ShaderNodeCameraData')
    mr = nt.nodes.new('ShaderNodeMapRange'); mr.inputs['From Min'].default_value = P['near']; mr.inputs['From Max'].default_value = P['far']; mr.inputs['To Max'].default_value = P['maxk']
    em = nt.nodes.new('ShaderNodeEmission'); em.inputs['Color'].default_value = (*lin(hexc(P['haze'])), 1); em.inputs['Strength'].default_value = 1.0
    mix = nt.nodes.new('ShaderNodeMixShader')
    nt.links.new(cam.outputs['View Distance'], mr.inputs['Value']); nt.links.new(mr.outputs['Result'], mix.inputs['Fac'])
    nt.links.new(src, mix.inputs[1]); nt.links.new(em.outputs['Emission'], mix.inputs[2])
    bsdf = [n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED']
    if bsdf and bsdf[0].inputs['Alpha'].links:
        tr = nt.nodes.new('ShaderNodeBsdfTransparent'); mx2 = nt.nodes.new('ShaderNodeMixShader')
        nt.links.new(bsdf[0].inputs['Alpha'].links[0].from_socket, mx2.inputs['Fac'])
        nt.links.new(tr.outputs['BSDF'], mx2.inputs[1]); nt.links.new(mix.outputs['Shader'], mx2.inputs[2])
        nt.links.new(mx2.outputs['Shader'], out.inputs['Surface'])
    else:
        nt.links.new(mix.outputs['Shader'], out.inputs['Surface'])

def flat_mat(name, color, P, rough=1.0, spec=0.0, emit=None, emit_k=0.0, tex=None, tex_scale=0.1):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; b = nt.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*color, 1); b.inputs['Roughness'].default_value = rough; b.inputs['Specular IOR Level'].default_value = spec
    if tex:
        tn = nt.nodes.new('ShaderNodeTexImage'); tn.image = bpy.data.images.load(os.path.join(TEX, tex), check_existing=True)
        tc = nt.nodes.new('ShaderNodeTexCoord'); mp = nt.nodes.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (tex_scale,) * 3
        nt.links.new(tc.outputs['Object'], mp.inputs['Vector']); nt.links.new(mp.outputs['Vector'], tn.inputs['Vector'])
        mx = nt.nodes.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.blend_type = 'MULTIPLY'; mx.inputs['Factor'].default_value = 1.0
        nt.links.new(tn.outputs['Color'], sock(mx, 'A')); sock(mx, 'B').default_value = (*[min(1, c * 4) for c in color], 1)
        nt.links.new(sock(mx, 'Result', True), b.inputs['Base Color'])
    if emit:
        b.inputs['Emission Color'].default_value = (*emit, 1); b.inputs['Emission Strength'].default_value = emit_k
    if P is not None: haze_mix(m, P)
    return m

def noise2(X, Y, scale, seed, oct=4):
    v = np.zeros_like(X); amp = 1.0; tot = 0
    f_ = np.vectorize(lambda a, b, f: noise.noise(Vector((a * f + seed, b * f - seed, seed * 0.37))))
    for o in range(oct):
        f = 2 ** o / scale; v += amp * f_(X, Y, f); tot += amp; amp *= 0.5
    return v / tot

def ring_mesh(name, rs, th, Z, mat, flip=False):
    nr, na = len(rs), len(th)
    R, TH = np.meshgrid(rs, th, indexing='ij')
    V = np.stack([R * np.cos(TH), R * np.sin(TH), Z], -1).reshape(-1, 3)
    F = []
    for i in range(nr - 1):
        for j in range(na):
            a = i * na + j; b = i * na + (j + 1) % na
            F.append([a, a + na, b + na, b] if flip else [a, b, b + na, a + na])
    me = bpy.data.meshes.new(name); me.from_pydata(V.tolist(), [], F); me.update()
    for p in me.polygons: p.use_smooth = True
    o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o); o.data.materials.append(mat)
    return o

class Ground:
    def __init__(self, P):
        nr, na = 150, 360
        self.rs = np.concatenate([[0.0, 40.0, 90.0], 150 * (40 ** np.linspace(0, 1, nr - 3))])
        self.th = np.linspace(0, 2 * math.pi, na, endpoint=False)
        R, TH = np.meshgrid(self.rs, self.th, indexing='ij'); X, Y = R * np.cos(TH), R * np.sin(TH)
        far = np.clip((R - 300) / 900, 0, 1)
        Z = noise2(X, Y, 900, 3.1) * P['hills'] * far + noise2(X, Y, 160, 7.7, 3) * min(10, P['hills'] * 0.3)
        if P.get('dunes'):
            Z += (np.abs(noise2(X, Y, 120, 5.5, 3)) * 2 - 0.5) * 22 * np.clip((R - 160) / 200, 0, 1)
        Z += np.clip((R - 2600) / 1400, 0, 1) ** 1.5 * (P['ridge'] + P['ridge'] * 0.7 * noise2(X, Y, 1300, 1.9, 5))
        if P.get('water') is not None:
            Z = np.where(noise2(X, Y, 90, 9.3, 3) < -0.12, np.minimum(Z, P['water'] - 1.0), Z)
        self.Z = Z - 2.0
        m = bpy.data.materials.new('chao'); m.use_nodes = True; nt = m.node_tree; b = nt.nodes['Principled BSDF']
        tc = nt.nodes.new('ShaderNodeTexCoord'); ns = nt.nodes.new('ShaderNodeTexNoise'); ns.inputs['Scale'].default_value = 0.004; ns.inputs['Detail'].default_value = 6
        ramp = nt.nodes.new('ShaderNodeValToRGB')
        ramp.color_ramp.elements[0].color = (*P['g0'], 1); ramp.color_ramp.elements[1].color = (*P['g1'], 1)
        nt.links.new(tc.outputs['Object'], ns.inputs['Vector']); nt.links.new(ns.outputs['Fac'], ramp.inputs['Fac'])
        sep = nt.nodes.new('ShaderNodeSeparateXYZ'); nt.links.new(tc.outputs['Object'], sep.inputs['Vector'])
        mr = nt.nodes.new('ShaderNodeMapRange'); mr.inputs['From Min'].default_value = 180; mr.inputs['From Max'].default_value = 420
        nt.links.new(sep.outputs['Z'], mr.inputs['Value'])
        mx = nt.nodes.new('ShaderNodeMix'); mx.data_type = 'RGBA'; sock(mx, 'B').default_value = (*P['ridgecol'], 1)
        nt.links.new(mr.outputs['Result'], mx.inputs['Factor']); nt.links.new(ramp.outputs['Color'], sock(mx, 'A'))
        if P.get('rockpeaks'):          # rocha escura aparecendo nas encostas íngremes da serra nevada
            geo = nt.nodes.new('ShaderNodeNewGeometry'); sz = nt.nodes.new('ShaderNodeSeparateXYZ'); nt.links.new(geo.outputs['Normal'], sz.inputs['Vector'])
            mr2 = nt.nodes.new('ShaderNodeMapRange'); mr2.inputs['From Min'].default_value = 0.8; mr2.inputs['From Max'].default_value = 0.6
            nt.links.new(sz.outputs['Z'], mr2.inputs['Value'])
            mx2 = nt.nodes.new('ShaderNodeMix'); mx2.data_type = 'RGBA'; sock(mx2, 'B').default_value = (0.08, 0.08, 0.09, 1)
            nt.links.new(mr2.outputs['Result'], mx2.inputs['Factor']); nt.links.new(sock(mx, 'Result', True), sock(mx2, 'A'))
            nt.links.new(sock(mx2, 'Result', True), b.inputs['Base Color'])
        else:
            nt.links.new(sock(mx, 'Result', True), b.inputs['Base Color'])
        b.inputs['Roughness'].default_value = 1.0; b.inputs['Specular IOR Level'].default_value = 0.0
        haze_mix(m, dict(P, near=P['near'] * 2, far=P['far'] * 1.8))
        ring_mesh('chao', self.rs, self.th, self.Z, m)
        if P.get('water') is not None:
            bpy.ops.mesh.primitive_plane_add(size=6000, location=(0, 0, P['water'] - 2.0)); w = bpy.context.active_object
            wm = flat_mat('agua', (0.03, 0.05, 0.04), dict(P, near=P['near'] * 1.5), rough=0.08, spec=0.5); w.data.materials.append(wm)

    def z(self, x, y):
        r = math.hypot(x, y); a = math.atan2(y, x) % (2 * math.pi)
        i = int(np.clip(np.searchsorted(self.rs, r) - 1, 0, len(self.rs) - 2)); j = int(a / (2 * math.pi) * len(self.th)) % len(self.th)
        t = (r - self.rs[i]) / (self.rs[i + 1] - self.rs[i])
        return float(self.Z[i, j] * (1 - t) + self.Z[i + 1, j] * t)

def load_kit(P):
    names = {n for n, _ in P['trees']} | {'pinho_longe'}
    load = set(n for n in names if n != 'verde') | ({'arvore_outono'} if 'verde' in names else set())
    with bpy.data.libraries.load(KIT) as (src, dst):
        dst.objects = [n for n in src.objects if n in load]
    col = {}
    for ob in dst.objects:
        c = bpy.data.collections.new('c_' + ob.name); c.objects.link(ob); ob.location = (0, 0, 0); col[ob.name] = c
    if 'verde' in names:             # árvore de copa redonda verde: a de outono com as folhas verdes
        src_o = bpy.data.objects['arvore_outono']; o = src_o.copy(); o.data = src_o.data.copy(); o.name = 'verde'
        for k, m in enumerate(o.data.materials):
            if m and m.get('tex') == 'folhas_outono':
                m2 = m.copy(); o.data.materials[k] = m2
                for nd in m2.node_tree.nodes:
                    if nd.type == 'TEX_IMAGE': nd.image = bpy.data.images.load(os.path.join(TEX, 'folhas_verdes.png'), check_existing=True)
        c = bpy.data.collections.new('c_verde'); c.objects.link(o); col['verde'] = c
    done = set()
    for c in col.values():
        for ob in c.objects:
            for m in ob.data.materials:
                if not m or m.name in done: continue
                done.add(m.name)
                if P.get('snowtrees') and m.get('tex') == 'ramo_pinho':      # neve nas copas: clareia os ramos
                    for nd in m.node_tree.nodes:
                        if nd.type == 'MIX' and nd.data_type == 'RGBA': sock(nd, 'B').default_value = (1.6, 1.7, 1.75, 1)
                haze_mix(m, P)
    return col

def cone_col(P):
    bpy.ops.mesh.primitive_cone_add(vertices=7, radius1=5.5, depth=20, location=(0, 0, 10)); cone = bpy.context.active_object; cone.name = 'cone'
    cone.data.materials.append(flat_mat('cone', P['cones'], P))
    for uc in list(cone.users_collection): uc.objects.unlink(cone)
    c = bpy.data.collections.new('c_cone'); c.objects.link(cone); return c

def mesa_col(P):
    """mesa de rocha do deserto: cilindro largo com o topo plano e as paredes irregulares."""
    bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=40, depth=60, location=(0, 0, 30)); o = bpy.context.active_object; o.name = 'mesa'
    for v in o.data.vertices:
        a = math.atan2(v.co.y, v.co.x); k = 1 + 0.25 * math.sin(a * 3 + 1) + 0.12 * math.sin(a * 7)
        if v.co.z > 0: k *= 0.85
        v.co.x *= k; v.co.y *= k
    o.data.materials.append(flat_mat('mesa', (0.3, 0.14, 0.07), P))
    for uc in list(o.users_collection): uc.objects.unlink(o)
    c = bpy.data.collections.new('c_mesa'); c.objects.link(o); return c

def scatter(P, G, rng):
    col = load_kit(P)
    if P.get('cones'): col['cone'] = cone_col(P)
    if P.get('mesas'): col['mesa'] = mesa_col(P)
    sc = bpy.context.scene.collection; n = 0
    def inst(name, x, y, s, rz=None):
        nonlocal n
        e = bpy.data.objects.new('i', None); e.instance_type = 'COLLECTION'; e.instance_collection = col[name]
        e.location = (x, y, G.z(x, y) - 0.3); e.scale = (s, s, s); e.rotation_euler = (0, 0, rng.uniform(0, 6.28) if rz is None else rz); sc.objects.link(e); n += 1
    names = [t for t, _ in P['trees']]; probs = np.array([p for _, p in P['trees']]); probs /= probs.sum()
    r0, r1 = P['ring']
    for k in range(int(9000 * P['dens'])):
        r = r0 + (rng.random() ** 1.6) * (r1 - r0); a = rng.uniform(0, 2 * math.pi); x, y = r * math.cos(a), r * math.sin(a)
        d = 0.5 + 0.5 * noise.noise(Vector((x / 160, y / 160, 1.3)))
        if rng.random() > d * (1.1 - (r - r0) / (r1 - r0) * 0.9): continue
        name = names[rng.choice(len(names), p=probs)]
        if name in ('pinho_a', 'pinho_b') and r > r0 + 120: name = 'pinho_longe' if 'pinho_longe' in col else name
        inst(name, x, y, rng.uniform(0.8, 1.35))
    if P.get('cones'):
        for k in range(P['groves']):
            r = rng.uniform(650, 2600); a = rng.uniform(0, 2 * math.pi); cx, cy = r * math.cos(a), r * math.sin(a)
            for _ in range(int(rng.integers(6, 40))):
                rr = rng.uniform(0, 60); aa = rng.uniform(0, 2 * math.pi)
                inst('cone', cx + rr * math.cos(aa), cy + rr * math.sin(aa), rng.uniform(0.7, 1.3), 0)
        for k in range(P['hillwood']):
            r = rng.uniform(1500, 3800); a = rng.uniform(0, 2 * math.pi); x, y = r * math.cos(a), r * math.sin(a)
            if noise.noise(Vector((x / 500, y / 500, 4.2))) < 0.15: continue
            inst('cone', x, y, rng.uniform(1.4, 2.4), 0)
    for k in range(P.get('mesas', 0)):
        r = rng.uniform(900, 3400); a = rng.uniform(0, 2 * math.pi)
        inst('mesa', r * math.cos(a), r * math.sin(a), rng.uniform(0.8, 2.4) * (1 + r / 2500))
    print('  instâncias:', n)

def sky(P):
    w = bpy.data.worlds.new('ceu'); bpy.context.scene.world = w; w.use_nodes = True; nt = w.node_tree; bg = nt.nodes['Background']
    if P['sky'] == 'nublado':
        bg.inputs['Color'].default_value = (*lin(hexc(0x8fa595)), 1); bg.inputs['Strength'].default_value = 1.0
    else:
        sk = nt.nodes.new('ShaderNodeTexSky')
        for t in ('NISHITA', 'MULTIPLE_SCATTERING', 'SINGLE_SCATTERING', 'HOSEK_WILKIE'):
            try: sk.sky_type = t; break
            except Exception: continue
        try: sk.sun_elevation = math.radians(P['sun']); sk.sun_rotation = math.radians(P['rot']); sk.air_density = 1.4; sk.dust_density = 2.5
        except Exception: pass
        nt.links.new(sk.outputs['Color'], bg.inputs['Color']); bg.inputs['Strength'].default_value = P['skyk']
    sun = bpy.data.objects.new('sol', bpy.data.lights.new('sol', 'SUN')); bpy.context.scene.collection.objects.link(sun)
    sun.data.energy = 2.2 if P['sky'] != 'nublado' else 0.5; sun.data.color = (1.0, 0.92, 0.8); sun.data.angle = math.radians(2 if P['sky'] != 'nublado' else 20)
    sun.rotation_euler = (math.radians(90 - P['sun']), 0, math.radians(P['rot'] - 90))
    # nuvens
    bpy.ops.mesh.primitive_plane_add(size=30000, location=(0, 0, 1400)); cl = bpy.context.active_object
    m = bpy.data.materials.new('nuvens'); m.use_nodes = True; nt = m.node_tree; out = nt.nodes['Material Output']
    for nd in list(nt.nodes):
        if nd.type == 'BSDF_PRINCIPLED': nt.nodes.remove(nd)
    tc = nt.nodes.new('ShaderNodeTexCoord'); ns = nt.nodes.new('ShaderNodeTexNoise'); ns.inputs['Scale'].default_value = 0.00022; ns.inputs['Detail'].default_value = 8; ns.inputs['Roughness'].default_value = 0.62
    mr = nt.nodes.new('ShaderNodeMapRange'); mr.inputs['From Min'].default_value = 0.4 if P['sky'] == 'nublado' else 0.52; mr.inputs['From Max'].default_value = 0.75
    em = nt.nodes.new('ShaderNodeEmission'); em.inputs['Color'].default_value = (1.0, 0.97, 0.92, 1) if P['sky'] != 'nublado' else (*lin(hexc(0x9fb4a4)), 1); em.inputs['Strength'].default_value = 0.9
    tr = nt.nodes.new('ShaderNodeBsdfTransparent'); mx = nt.nodes.new('ShaderNodeMixShader')
    nt.links.new(tc.outputs['Object'], ns.inputs['Vector']); nt.links.new(ns.outputs['Fac'], mr.inputs['Value'])
    nt.links.new(mr.outputs['Result'], mx.inputs['Fac']); nt.links.new(tr.outputs['BSDF'], mx.inputs[1]); nt.links.new(em.outputs['Emission'], mx.inputs[2])
    nt.links.new(mx.outputs['Shader'], out.inputs['Surface'])
    cl.data.materials.append(m); cl.visible_shadow = False

def underground(P, rng, hall=False):
    """caverna / salão subterrâneo: paredões em volta (anel de malha com ruído) e teto, com luzes próprias."""
    w = bpy.data.worlds.new('escuro'); bpy.context.scene.world = w; w.use_nodes = True
    w.node_tree.nodes['Background'].inputs['Color'].default_value = (*lin(hexc(P['haze'])), 1); w.node_tree.nodes['Background'].inputs['Strength'].default_value = 1.0
    rock = flat_mat('rocha', P['rock'], P, tex='rocha.jpg', tex_scale=0.06)
    # chão
    rs = np.concatenate([[0.0, 30.0], np.linspace(60, 520, 60)]); th = np.linspace(0, 2 * math.pi, 240, endpoint=False)
    R, TH = np.meshgrid(rs, th, indexing='ij'); X, Y = R * np.cos(TH), R * np.sin(TH)
    floor = noise2(X, Y, 60, 2.2, 3) * (0.5 if hall else 4) - 2
    ring_mesh('chao', rs, th, floor, flat_mat('piso', tuple(c * 1.1 for c in P['rock']), P, tex='calcada.jpg' if hall else 'rocha.jpg', tex_scale=0.08))
    # paredes e teto: um "tubo" de raio ~ 200-320 que se fecha em cúpula a 160-230 de altura
    na, nz = 240, 40
    th = np.linspace(0, 2 * math.pi, na, endpoint=False); hz = np.linspace(-4, 1, nz)
    V = []
    for k in range(nz):
        t = k / (nz - 1)
        for j in range(na):
            a = th[j]; x0, y0 = math.cos(a), math.sin(a)
            base = 230 if hall else 250 + 70 * noise.noise(Vector((x0 * 2, y0 * 2, 0.7)))
            if hall: base += 12 * (1 if (j // 10) % 2 == 0 else 0)          # nichos/arcos nas paredes do salão
            rough = 0 if hall else 35 * noise.noise(Vector((x0 * 6, y0 * 6, t * 6)))
            if t < 0.6: rr, zz = base + rough, t / 0.6 * (150 if hall else 190)
            else:
                u = (t - 0.6) / 0.4; rr = (base + rough) * math.cos(u * math.pi / 2); zz = (150 if hall else 190) + (base * 0.45) * math.sin(u * math.pi / 2)
            V.append((rr * x0, rr * y0, zz - 2))
    F = []
    for k in range(nz - 1):
        for j in range(na):
            a = k * na + j; b = k * na + (j + 1) % na; F.append([a, a + na, b + na, b])
    me = bpy.data.meshes.new('paredes'); me.from_pydata(V, [], F); me.update()
    for p in me.polygons: p.use_smooth = True
    o = bpy.data.objects.new('paredes', me); bpy.context.scene.collection.objects.link(o); o.data.materials.append(rock)
    sc = bpy.context.scene.collection
    if hall:
        # colunas, arcos e tochas
        col_m = flat_mat('coluna', tuple(c * 1.3 for c in P['rock']), P, tex='rocha.jpg', tex_scale=0.1)
        for ring_r, n in ((150, 16), (205, 24)):
            for k in range(n):
                a = 2 * math.pi * (k + 0.5 * (ring_r == 205)) / n; x, y = ring_r * math.cos(a), ring_r * math.sin(a)
                bpy.ops.mesh.primitive_cube_add(size=1, location=(x, y, 60)); c = bpy.context.active_object; c.scale = (9, 9, 124); c.rotation_euler = (0, 0, a); c.data.materials.append(col_m)
                bpy.ops.mesh.primitive_cube_add(size=1, location=(x, y, 2)); c = bpy.context.active_object; c.scale = (13, 13, 8); c.rotation_euler = (0, 0, a); c.data.materials.append(col_m)
                if ring_r == 205 or k % 2 == 0:       # tocha na coluna, virada para o centro
                    tx, ty = (ring_r - 6) * math.cos(a), (ring_r - 6) * math.sin(a)
                    bpy.ops.mesh.primitive_uv_sphere_add(radius=1.6, location=(tx, ty, 34)); f = bpy.context.active_object
                    fm = bpy.data.materials.new('chama'); fm.use_nodes = True; fb = fm.node_tree.nodes['Principled BSDF']
                    fb.inputs['Emission Color'].default_value = (*P['torch'], 1); fb.inputs['Emission Strength'].default_value = 40; f.data.materials.append(fm)
                    L = bpy.data.objects.new('luz', bpy.data.lights.new('luz', 'POINT')); L.data.energy = 60000; L.data.color = P['torch']; L.data.shadow_soft_size = 2
                    L.location = (tx * 0.97, ty * 0.97, 34); sc.objects.link(L)
    else:
        # estalagmites, estalactites e cristais que brilham
        stal_m = flat_mat('estal', tuple(c * 1.2 for c in P['rock']), P, tex='rocha.jpg', tex_scale=0.15)
        cry = bpy.data.materials.new('cristal'); cry.use_nodes = True; cb = cry.node_tree.nodes['Principled BSDF']
        cb.inputs['Base Color'].default_value = (*P['crystal'], 1); cb.inputs['Emission Color'].default_value = (*P['crystal'], 1); cb.inputs['Emission Strength'].default_value = 14
        for k in range(P['stal']):
            r = rng.uniform(110, 300); a = rng.uniform(0, 2 * math.pi); x, y = r * math.cos(a), r * math.sin(a)
            h = rng.uniform(8, 45) * (1 + (r - 110) / 300); top = rng.random() < 0.35
            bpy.ops.mesh.primitive_cone_add(vertices=7, radius1=h * 0.22, depth=h, location=(x, y, (230 - h / 2) if top else h / 2 - 2))
            c = bpy.context.active_object; c.data.materials.append(stal_m)
            if top: c.rotation_euler = (math.pi, 0, 0)
        for k in range(160):
            r = rng.uniform(120, 290); a = rng.uniform(0, 2 * math.pi); x, y = r * math.cos(a), r * math.sin(a)
            for q in range(int(rng.integers(3, 7))):
                h = rng.uniform(3, 11)
                bpy.ops.mesh.primitive_cone_add(vertices=5, radius1=h * 0.18, depth=h, location=(x + rng.normal(0, 2), y + rng.normal(0, 2), h / 2 - 2))
                c = bpy.context.active_object; c.rotation_euler = (rng.normal(0, 0.35), rng.normal(0, 0.35), 0); c.data.materials.append(cry)
            if k % 4 == 0:
                L = bpy.data.objects.new('luz', bpy.data.lights.new('luz', 'POINT')); L.data.energy = 90000; L.data.color = P['crystal']
                L.location = (x * 0.97, y * 0.97, 8); sc.objects.link(L)

def render(out_png):
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'; sc.cycles.samples = SAMPLES; sc.cycles.use_denoising = True
    sc.cycles.max_bounces = 4; sc.cycles.transparent_max_bounces = 24
    cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); sc.collection.objects.link(cam); sc.camera = cam
    cam.location = (0, 0, EYE); cam.rotation_euler = (math.radians(90), 0, math.radians(-90))
    cd = cam.data; cd.type = 'PANO'; cd.clip_end = 20000
    try: cd.panorama_type = 'EQUIRECTANGULAR'
    except Exception: cd.cycles.panorama_type = 'EQUIRECTANGULAR'
    for obj in (cd, getattr(cd, 'cycles', None)):
        if obj is None: continue
        for k, v in (('latitude_min', math.radians(LAT0)), ('latitude_max', math.radians(LAT1)), ('longitude_min', -math.pi), ('longitude_max', math.pi)):
            try: setattr(obj, k, v)
            except Exception: pass
    sc.render.resolution_x = WIDTH; sc.render.resolution_y = int(round(WIDTH * (LAT1 - LAT0) / 360))
    sc.view_settings.view_transform = 'AgX'; sc.view_settings.exposure = -0.6
    try: sc.view_settings.look = 'AgX - Medium High Contrast'
    except Exception: pass
    sc.render.image_settings.file_format = 'PNG'; sc.render.filepath = out_png
    bpy.ops.render.render(write_still=True)

def to_cylinder(src, dst, fade=True):
    from PIL import Image
    eq = np.asarray(Image.open(src).convert('RGB'), float) / 255
    h, w = eq.shape[:2]
    RAD, BASE, BAND, H2 = 300.0, -30.0, 210.0, 1024
    ys = BASE + (1 - (np.arange(H2) + 0.5) / H2) * BAND
    el = np.degrees(np.arctan2(ys - EYE, RAD))
    rows = (LAT1 - el) / (LAT1 - LAT0) * (h - 1)
    r0 = np.clip(np.floor(rows).astype(int), 0, h - 2); t = np.clip(rows - r0, 0, 1)[:, None, None]
    cyl = eq[r0] * (1 - t) + eq[r0 + 1] * t
    alpha = np.clip((LAT1 - 3 - el) / 8.0, 0, 1) if fade else np.ones_like(el)
    out = np.concatenate([cyl, alpha[:, None, None].repeat(w, 1)], -1)
    img = Image.fromarray((np.clip(out, 0, 1) * 255).astype(np.uint8), 'RGBA').resize((4096, H2), Image.LANCZOS)
    img.save(dst, quality=86, method=5)
    print('  %s: %.0f KB' % (os.path.basename(dst), os.path.getsize(dst) / 1024))

def build(name):
    P = PRESETS[name]; rng = np.random.default_rng(sum(map(ord, name)))
    bpy.ops.wm.read_factory_settings(use_empty=True)
    if P.get('cave') or P.get('hall'):
        underground(P, rng, hall=bool(P.get('hall')))
    else:
        G = Ground(P); scatter(P, G, rng); sky(P)
    tmp = f'/tmp/fundo_{name}_equi.png'
    render(tmp)
    to_cylinder(tmp, os.path.join(OUTDIR, f'{name}.webp'), fade=not (P.get('cave') or P.get('hall')))

if __name__ == '__main__':
    os.makedirs(OUTDIR, exist_ok=True)
    names = [a for a in sys.argv[1:] if a in PRESETS] or list(PRESETS)
    for n in names:
        print('fundo:', n); build(n)
