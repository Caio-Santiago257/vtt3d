"""Fundo panorâmico do mapa "Encruzilhada da Floresta", renderizado no Blender (Cycles).

Monta, em volta do lugar onde fica o mapa, o que se veria de lá:
  - de 170 a ~500 unidades: a mata de pinheiros continua (os mesmos pinheiros do kit), com árvores de outono;
  - depois a mata abre numa planície ondulada de capim, com bosques e fileiras de árvores espalhados;
  - bem longe, morros e uma serra azulada pela distância;
  - céu de fim de tarde (céu físico do Blender) com nuvens altas.
A névoa da distância é feita nos próprios materiais (pela distância até a câmera), o que fica leve no Cycles.

A câmera fica no centro do mapa e renderiza uma faixa equiretangular (360 graus de largura). Depois a imagem é
reprojetada para o cilindro do jogo (raio 300, faixa de -30 a +180 de altura) e a parte de cima vira transparente,
emendando com o céu do jogo. Saída: public/assets/maps/estrada/tex/fundo.webp

Rodar (depois de estrada_cenario.py): python3 fontes/blender/estrada_fundo.py      [AMOSTRAS=24 LARGURA=4096]
"""
import math, os
import numpy as np
import bpy
from mathutils import Vector

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
KIT = os.path.join(ROOT, 'fontes', 'blender', 'estrada_kit.blend')
OUTDIR = os.path.join(ROOT, 'public', 'assets', 'maps', 'estrada', 'tex')
SAMPLES = int(os.environ.get('AMOSTRAS', '24'))
WIDTH = int(os.environ.get('LARGURA', '4096'))
LAT0, LAT1 = -9.0, 36.0                 # faixa renderizada (graus)
EYE = 6.0                               # altura do olho (unidades do jogo; aqui 1 unidade do Blender = 1 do jogo)
HAZE = (0.50, 0.60, 0.72)

def sock(node, name, out=False):
    """socket visível com esse nome (o nó Mix tem A/B repetidos para cada tipo de dado)."""
    for x in (node.outputs if out else node.inputs):
        if x.name == name and x.enabled: return x
    raise KeyError(name)
rng = np.random.default_rng(5)

def haze_mix(mat, near=150.0, far=2600.0, maxk=0.9):
    """mistura a cor da névoa por cima do material conforme a distância até a câmera."""
    nt = mat.node_tree; out = [n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL'][0]
    src = out.inputs['Surface'].links[0].from_socket
    cam = nt.nodes.new('ShaderNodeCameraData')
    mr = nt.nodes.new('ShaderNodeMapRange'); mr.inputs['From Min'].default_value = near; mr.inputs['From Max'].default_value = far
    mr.inputs['To Max'].default_value = maxk
    em = nt.nodes.new('ShaderNodeEmission'); em.inputs['Color'].default_value = (*HAZE, 1); em.inputs['Strength'].default_value = 1.0
    # a névoa não pode deixar o recorte das folhas opaco: mistura só onde há folha
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

def noise2(x, y, scale, seed, oct=4):
    from mathutils import noise
    v = np.zeros_like(x); amp = 1.0; tot = 0
    for o in range(oct):
        f = 2 ** o / scale
        v += amp * np.vectorize(lambda a, b: noise.noise(Vector((a * f + seed, b * f - seed, seed * 0.37))))(x, y); tot += amp; amp *= 0.5
    return v / tot

def ground():
    """chão ondulado em anéis (mais detalhe perto, morros e serra longe)."""
    nr, na = 150, 360
    rs = np.concatenate([[0.0, 40.0, 90.0], 150 * (40 ** (np.linspace(0, 1, nr - 3) ** 1.0))])   # 0 .. 6000, espaçamento crescente
    th = np.linspace(0, 2 * math.pi, na, endpoint=False)
    R, TH = np.meshgrid(rs, th, indexing='ij')
    X, Y = R * np.cos(TH), R * np.sin(TH)
    hills = noise2(X, Y, 900, 3.1) * 70 * np.clip((R - 300) / 900, 0, 1)
    small = noise2(X, Y, 160, 7.7, 3) * 10
    ridge = np.clip((R - 2600) / 1400, 0, 1) ** 1.5 * (650 + 450 * noise2(X, Y, 1300, 1.9, 5))   # serra no fundo
    Z = hills + small + ridge - 2.0
    V = np.stack([X, Y, Z], -1).reshape(-1, 3)
    F = []
    for i in range(nr - 1):
        for j in range(na):
            a = i * na + j; b = i * na + (j + 1) % na
            F.append([a, b, b + na, a + na])
    me = bpy.data.meshes.new('chao'); me.from_pydata(V.tolist(), [], F); me.update()
    for p in me.polygons: p.use_smooth = True
    o = bpy.data.objects.new('chao', me); bpy.context.scene.collection.objects.link(o)
    # material: capim da planície em manchas, mata escura onde há floresta, rocha na serra
    m = bpy.data.materials.new('chao'); m.use_nodes = True; nt = m.node_tree; b = nt.nodes['Principled BSDF']
    tc = nt.nodes.new('ShaderNodeTexCoord'); ns = nt.nodes.new('ShaderNodeTexNoise'); ns.inputs['Scale'].default_value = 0.004; ns.inputs['Detail'].default_value = 6
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].color = (0.03, 0.06, 0.012, 1); ramp.color_ramp.elements[1].color = (0.13, 0.15, 0.03, 1)
    nt.links.new(tc.outputs['Object'], ns.inputs['Vector']); nt.links.new(ns.outputs['Fac'], ramp.inputs['Fac'])
    sep = nt.nodes.new('ShaderNodeSeparateXYZ'); nt.links.new(tc.outputs['Object'], sep.inputs['Vector'])
    mr = nt.nodes.new('ShaderNodeMapRange'); mr.inputs['From Min'].default_value = 180; mr.inputs['From Max'].default_value = 420
    nt.links.new(sep.outputs['Z'], mr.inputs['Value'])
    mx = nt.nodes.new('ShaderNodeMix'); mx.data_type = 'RGBA'; sock(mx, 'B').default_value = (0.08, 0.1, 0.07, 1)
    nt.links.new(mr.outputs['Result'], mx.inputs['Factor']); nt.links.new(ramp.outputs['Color'], sock(mx, 'A'))
    nt.links.new(sock(mx, 'Result', True), b.inputs['Base Color']); b.inputs['Roughness'].default_value = 1.0
    b.inputs['Specular IOR Level'].default_value = 0.0      # sem isso o capim rasante reflete o céu e fica branco
    o.data.materials.append(m); haze_mix(m, 500, 6000, 0.8)
    return o, (rs, th, Z)

def ground_z(x, y, G):
    rs, th, Z = G
    r = math.hypot(x, y); a = math.atan2(y, x) % (2 * math.pi)
    i = int(np.clip(np.searchsorted(rs, r) - 1, 0, len(rs) - 2)); j = int(a / (2 * math.pi) * len(th)) % len(th)
    t = (r - rs[i]) / (rs[i + 1] - rs[i])
    return float(Z[i, j] * (1 - t) + Z[i + 1, j] * t)

def scatter(G):
    """mata perto (cartões do kit) e bosques na planície (cones simples, já borrados pela névoa)."""
    with bpy.data.libraries.load(KIT) as (src, dst):
        dst.objects = [n for n in src.objects if n in ('pinho_a', 'pinho_b', 'pinho_longe', 'arvore_outono', 'arbusto_verde')]
    col = {}
    for ob in dst.objects:
        c = bpy.data.collections.new('c_' + ob.name); c.objects.link(ob); ob.location = (0, 0, 0); col[ob.name] = c
        for m in ob.data.materials:
            if m and 'haze' not in m: haze_mix(m, 300, 3000, 0.85); m['haze'] = 1
    # cone de árvore distante (sem cartões)
    bpy.ops.mesh.primitive_cone_add(vertices=7, radius1=5.5, depth=20, location=(0, 0, 10)); cone = bpy.context.active_object; cone.name = 'cone'
    cm = bpy.data.materials.new('cone'); cm.use_nodes = True; cm.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.03, 0.07, 0.04, 1); cm.node_tree.nodes['Principled BSDF'].inputs['Specular IOR Level'].default_value = 0.0
    cone.data.materials.append(cm); haze_mix(cm, 400, 5500, 0.85)
    for uc in list(cone.users_collection): uc.objects.unlink(cone)
    cc = bpy.data.collections.new('c_cone'); cc.objects.link(cone); col['cone'] = cc
    sc = bpy.context.scene.collection
    n = 0
    def inst(name, x, y, s, rz):
        nonlocal n
        e = bpy.data.objects.new('i', None); e.instance_type = 'COLLECTION'; e.instance_collection = col[name]
        e.location = (x, y, ground_z(x, y, G) - 0.3); e.scale = (s, s, s); e.rotation_euler = (0, 0, rz); sc.objects.link(e); n += 1
    from mathutils import noise
    # anel de mata fechada (170-480) que vai rareando; ao sul e a leste abre mais cedo (como no mapa)
    for k in range(9000):
        r = 170 + (rng.random() ** 1.6) * 520; a = rng.uniform(0, 2 * math.pi)
        x, y = r * math.cos(a), r * math.sin(a)
        dens = 0.5 + 0.5 * noise.noise(Vector((x / 160, y / 160, 1.3)))
        open_side = 0.5 + 0.5 * math.cos(a - math.radians(-40))
        keep = dens * (0.95 - (r - 170) / 520 * (0.9 + 0.9 * open_side)) - 0.12 * open_side
        if rng.random() > keep: continue
        name = 'pinho_longe' if r > 260 else ('pinho_a' if rng.random() < 0.5 else 'pinho_b')
        if rng.random() < 0.03: name = 'arvore_outono'
        inst(name, x, y, rng.uniform(0.8, 1.3), rng.uniform(0, 6.28))
    # bosques e fileiras de árvores na planície (cones)
    for k in range(260):
        r = rng.uniform(650, 2600); a = rng.uniform(0, 2 * math.pi); cx, cy = r * math.cos(a), r * math.sin(a)
        if rng.random() < 0.3:      # fileira (cerca viva)
            d = rng.uniform(0, math.pi); L = rng.uniform(80, 260)
            for t in np.linspace(-0.5, 0.5, int(L / 9)):
                inst('cone', cx + math.cos(d) * L * t + rng.normal(0, 3), cy + math.sin(d) * L * t + rng.normal(0, 3), rng.uniform(0.6, 1.0), 0)
        else:
            for _ in range(int(rng.integers(6, 40))):
                rr = rng.uniform(0, 60) ** 1.0
                aa = rng.uniform(0, 2 * math.pi)
                inst('cone', cx + rr * math.cos(aa), cy + rr * math.sin(aa), rng.uniform(0.7, 1.3), 0)
    # matas escuras nos morros
    for k in range(5000):
        r = rng.uniform(1500, 3800); a = rng.uniform(0, 2 * math.pi); x, y = r * math.cos(a), r * math.sin(a)
        if noise.noise(Vector((x / 500, y / 500, 4.2))) < 0.15: continue
        inst('cone', x, y, rng.uniform(1.4, 2.4), 0)
    print('árvores no fundo:', n)

def sky():
    w = bpy.data.worlds.new('ceu'); bpy.context.scene.world = w; w.use_nodes = True; nt = w.node_tree
    bg = nt.nodes['Background']
    sk = nt.nodes.new('ShaderNodeTexSky')
    for t in ('NISHITA', 'MULTIPLE_SCATTERING', 'SINGLE_SCATTERING', 'HOSEK_WILKIE'):
        try: sk.sky_type = t; break
        except Exception: continue
    try:
        sk.sun_elevation = math.radians(24); sk.sun_rotation = math.radians(215); sk.air_density = 1.4; sk.dust_density = 2.5
    except Exception: pass
    nt.links.new(sk.outputs['Color'], bg.inputs['Color']); bg.inputs['Strength'].default_value = 0.32
    print('céu:', sk.sky_type)
    # sol (para as sombras nas árvores e nos morros)
    sun = bpy.data.objects.new('sol', bpy.data.lights.new('sol', 'SUN')); bpy.context.scene.collection.objects.link(sun)
    sun.data.energy = 2.2; sun.data.color = (1.0, 0.9, 0.75); sun.data.angle = math.radians(2)
    sun.rotation_euler = (math.radians(90 - 24), 0, math.radians(215 - 90))
    # nuvens: plano alto com ruído (transparente fora das nuvens)
    bpy.ops.mesh.primitive_plane_add(size=30000, location=(0, 0, 1400)); cl = bpy.context.active_object
    m = bpy.data.materials.new('nuvens'); m.use_nodes = True; nt = m.node_tree; out = nt.nodes['Material Output']
    for nd in list(nt.nodes):
        if nd.type == 'BSDF_PRINCIPLED': nt.nodes.remove(nd)
    tc = nt.nodes.new('ShaderNodeTexCoord'); ns = nt.nodes.new('ShaderNodeTexNoise'); ns.inputs['Scale'].default_value = 0.00022; ns.inputs['Detail'].default_value = 8; ns.inputs['Roughness'].default_value = 0.62
    mr = nt.nodes.new('ShaderNodeMapRange'); mr.inputs['From Min'].default_value = 0.52; mr.inputs['From Max'].default_value = 0.75
    em = nt.nodes.new('ShaderNodeEmission'); em.inputs['Color'].default_value = (1.0, 0.96, 0.9, 1); em.inputs['Strength'].default_value = 0.9
    tr = nt.nodes.new('ShaderNodeBsdfTransparent'); mx = nt.nodes.new('ShaderNodeMixShader')
    nt.links.new(tc.outputs['Object'], ns.inputs['Vector']); nt.links.new(ns.outputs['Fac'], mr.inputs['Value'])
    nt.links.new(mr.outputs['Result'], mx.inputs['Fac']); nt.links.new(tr.outputs['BSDF'], mx.inputs[1]); nt.links.new(em.outputs['Emission'], mx.inputs[2])
    nt.links.new(mx.outputs['Shader'], out.inputs['Surface'])
    cl.data.materials.append(m); cl.visible_shadow = False

def render():
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'; sc.cycles.samples = SAMPLES; sc.cycles.use_denoising = True
    sc.cycles.max_bounces = 4; sc.cycles.transparent_max_bounces = 24
    try: sc.cycles.device = 'CPU'
    except Exception: pass
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
    sc.render.film_transparent = False
    sc.view_settings.view_transform = 'AgX'; sc.view_settings.exposure = -0.6
    try: sc.view_settings.look = 'AgX - Medium High Contrast'
    except Exception: pass
    sc.render.image_settings.file_format = 'PNG'
    sc.render.filepath = '/tmp/estrada_equi.png'
    bpy.ops.render.render(write_still=True)

def to_cylinder():
    """equiretangular -> cilindro do jogo: a linha da imagem vale a altura y = 300*tan(elevação) + olho;
    a imagem cobre de y=-30 a y=+180 (faixa 210) e a parte de cima some aos poucos (o céu do jogo aparece)."""
    from PIL import Image
    eq = np.asarray(Image.open('/tmp/estrada_equi.png').convert('RGB'), float) / 255
    h, w = eq.shape[:2]
    RAD, BASE, BAND = 300.0, -30.0, 210.0
    H2 = 1024
    ys = BASE + (1 - (np.arange(H2) + 0.5) / H2) * BAND           # linha 0 = topo da faixa
    el = np.degrees(np.arctan2(ys - EYE, RAD))
    rows = (LAT1 - el) / (LAT1 - LAT0) * (h - 1)
    r0 = np.clip(np.floor(rows).astype(int), 0, h - 2); t = np.clip(rows - r0, 0, 1)[:, None, None]
    cyl = eq[r0] * (1 - t) + eq[r0 + 1] * t
    alpha = np.clip((LAT1 - 3 - el) / 8.0, 0, 1)                      # some nos últimos graus de cima
    out = np.concatenate([cyl, alpha[:, None, None].repeat(w, 1)], -1)
    img = Image.fromarray((np.clip(out, 0, 1) * 255).astype(np.uint8), 'RGBA').resize((4096, H2), Image.LANCZOS)
    img.save(os.path.join(OUTDIR, 'fundo.webp'), quality=86, method=5)
    img.convert('RGB').resize((1024, 256)).save('/tmp/estrada_fundo_prev.jpg')
    print('fundo.webp: %.0f KB' % (os.path.getsize(os.path.join(OUTDIR, 'fundo.webp')) / 1024))

def main():
    for o in list(bpy.data.objects): bpy.data.objects.remove(o)
    G = ground()[1]
    scatter(G)
    sky()
    render()
    to_cylinder()

if __name__ == '__main__':
    main()
