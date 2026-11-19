"""Objetos de cena para o terreno "Estrada na mata" (mapas desenhados pelo mestre).
Modelados no Blender do Caio (pela ponte do Blender) e também rodam aqui:  python3 fontes/blender/estrada_props.py

Peças (unidades do jogo; 1 unidade = 0,75 m; base no chão):
  carroca     carroça quebrada: caçamba de tábuas tombada sobre um eixo partido, uma roda caída ao lado e o cabeçalho no chão
  cerca       trecho de cerca rústica de 6 unidades (3 mourões tortos e 2 travessas)
  fogueira    roda de pedras com lenha cruzada e cinzas (acampamento na beira da estrada)
  marco       marco de pedra da estrada, com o topo arredondado e uma seta gravada
  caixotes    pilha de caixotes de madeira e um saco
Os materiais levam em "extras" a textura da pasta tex/ do mapa (madeira, casca, rocha), como o resto do kit.
Saída: public/assets/maps/estrada/props.glb (ou o caminho em ESTRADA_PROPS_OUT)
"""
import math, os
import bpy, bmesh
from mathutils import Vector, Matrix

OUT = os.environ.get('ESTRADA_PROPS_OUT') or (os.path.join(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')), 'public', 'assets', 'maps', 'estrada', 'props.glb') if '__file__' in globals() else os.path.join(os.path.expanduser('~'), 'estrada_props.glb'))
COL = 'COL_Estrada_Props'

def mat(name, tex, color):
    m = bpy.data.materials.get('estrada_' + name) or bpy.data.materials.new('estrada_' + name)
    m.use_nodes = True
    b = m.node_tree.nodes.get('Principled BSDF')
    if b: b.inputs['Base Color'].default_value = (*color, 1); b.inputs['Roughness'].default_value = 0.9
    m['tex'] = tex; m['card'] = 0; m['tint'] = [1, 1, 1]
    return m

def collection():
    c = bpy.data.collections.get(COL)
    if c:
        for o in list(c.objects): bpy.data.objects.remove(o, do_unlink=True)
    else:
        c = bpy.data.collections.new(COL); bpy.context.scene.collection.children.link(c)
    return c

class Build:
    """junta caixas e cilindros num bmesh só, cada um com o seu material e UV pelo tamanho (a textura não estica)."""
    def __init__(self, name):
        self.name = name; self.bm = bmesh.new(); self.uv = self.bm.loops.layers.uv.new('UVMap'); self.mats = []
    def mi(self, m):
        if m not in self.mats: self.mats.append(m)
        return self.mats.index(m)
    def _uv(self, faces, scale):
        for f in faces:
            n = f.normal; ax = max(range(3), key=lambda i: abs(n[i]))
            for l in f.loops:
                co = l.vert.co
                u, v = ((co.y, co.z) if ax == 0 else (co.x, co.z) if ax == 1 else (co.x, co.y))
                l[self.uv].uv = (u / scale, v / scale)
    def box(self, size, loc, rot=(0, 0, 0), m=None, scale=2.0):
        r = bmesh.ops.create_cube(self.bm, size=1.0)
        vs = r['verts']
        M = Matrix.Translation(loc) @ Matrix.Rotation(rot[2], 4, 'Z') @ Matrix.Rotation(rot[1], 4, 'Y') @ Matrix.Rotation(rot[0], 4, 'X') @ Matrix.Diagonal((*size, 1))
        bmesh.ops.transform(self.bm, matrix=M, verts=vs)
        faces = list({f for v in vs for f in v.link_faces})
        bmesh.ops.recalc_face_normals(self.bm, faces=faces)
        for f in faces: f.material_index = self.mi(m)
        self._uv(faces, scale)
    def cyl(self, r1, r2, depth, loc, rot=(0, 0, 0), m=None, seg=10, scale=2.0):
        res = bmesh.ops.create_cone(self.bm, cap_ends=True, segments=seg, radius1=r1, radius2=r2, depth=depth)
        vs = res['verts']
        M = Matrix.Translation(loc) @ Matrix.Rotation(rot[2], 4, 'Z') @ Matrix.Rotation(rot[1], 4, 'Y') @ Matrix.Rotation(rot[0], 4, 'X')
        bmesh.ops.transform(self.bm, matrix=M, verts=vs)
        faces = list({f for v in vs for f in v.link_faces})
        for f in faces: f.material_index = self.mi(m)
        self._uv(faces, scale)
    def rock(self, r, loc, m, seed):
        res = bmesh.ops.create_icosphere(self.bm, subdivisions=1, radius=r)
        vs = res['verts']; k = seed * 1.7
        for i, v in enumerate(vs):
            f = 1 + 0.22 * math.sin(i * 2.3 + k) + 0.12 * math.cos(i * 1.1 + k * 2)
            v.co = Vector((v.co.x * f, v.co.y * f * 0.9, max(v.co.z * f * 0.7, -r * 0.2)))
        bmesh.ops.translate(self.bm, vec=Vector(loc), verts=vs)
        faces = list({f for v in vs for f in v.link_faces})
        for f in faces: f.material_index = self.mi(m)
        self._uv(faces, 1.5)
    def done(self, col):
        bmesh.ops.recalc_face_normals(self.bm, faces=self.bm.faces[:])
        me = bpy.data.meshes.new(self.name); self.bm.to_mesh(me); self.bm.free()
        for m in self.mats: me.materials.append(m)
        o = bpy.data.objects.new(self.name, me); col.objects.link(o)
        return o

def wheel(B, loc, rot, m_wood, r=1.15):
    """roda de madeira com aro, cubo e 8 raios. rot gira a roda (o eixo da roda é o x local antes de girar)."""
    R = Matrix.Rotation(rot[2], 4, 'Z') @ Matrix.Rotation(rot[1], 4, 'Y') @ Matrix.Rotation(rot[0], 4, 'X')
    loc = Vector(loc)
    n = 14
    for k in range(n):       # aro em segmentos
        a0, a1 = 2 * math.pi * k / n, 2 * math.pi * (k + 1) / n; am = (a0 + a1) / 2
        p = Vector((0, math.cos(am) * r, math.sin(am) * r)); L = 2 * r * math.sin(math.pi / n) + 0.04
        e = R.to_euler()
        seg_rot = (R @ Matrix.Rotation(am + math.pi / 2, 4, 'X')).to_euler()
        B.box((0.22, L, 0.16), loc + (R @ p.to_4d()).to_3d(), (seg_rot.x, seg_rot.y, seg_rot.z), m_wood, 1.0)
    for k in range(8):       # raios
        a = 2 * math.pi * k / 8; p = Vector((0, math.cos(a) * r * 0.5, math.sin(a) * r * 0.5))
        sr = (R @ Matrix.Rotation(a, 4, 'X')).to_euler()
        B.box((0.08, r, 0.08), loc + (R @ p.to_4d()).to_3d(), (sr.x, sr.y, sr.z), m_wood, 1.0)
    hr = (R @ Matrix.Rotation(math.pi / 2, 4, 'Y')).to_euler()
    B.cyl(0.2, 0.2, 0.34, loc, (hr.x, hr.y, hr.z), m_wood, 8, 1.0)

def carroca(col, M):
    B = Build('carroca'); w, c = M['madeira'], M['casca']
    tilt = math.radians(14)          # a caçamba tomba para o lado da roda quebrada
    T = Matrix.Translation((0, 0, 1.25)) @ Matrix.Rotation(tilt, 4, 'X')
    def at(p): return (T @ Vector(p).to_4d()).to_3d()
    for k in range(7):               # fundo de tábuas
        B.box((6.0, 0.42, 0.12), at((0, -1.35 + k * 0.45, 0)), (tilt, 0, 0), w, 2.0)
    for s in (-1, 1):                # laterais
        B.box((6.0, 0.1, 0.9), at((0, s * 1.55, 0.5)), (tilt, 0, 0), w, 2.0)
        for x in (-2.8, -1.0, 1.0, 2.8): B.box((0.16, 0.16, 1.1), at((x, s * 1.6, 0.45)), (tilt, 0, 0), w, 1.0)
    B.box((0.1, 3.2, 0.9), at((-3.0, 0, 0.5)), (tilt, 0, 0), w, 2.0)
    B.box((0.1, 2.0, 0.9), at((3.0, -0.6, 0.5)), (tilt + 0.3, 0.15, 0.1), w, 2.0)        # tampa de trás meio solta
    B.cyl(0.13, 0.13, 3.6, at((-1.8, 0, -0.35)), (math.pi / 2, 0, 0), c, 8)              # eixo da frente
    wheel(B, at((-1.8, 1.95, -0.35)), (0, 0, math.pi / 2), w)                            # rodas de pé
    wheel(B, at((-1.8, -1.95, -0.35)), (0, 0, math.pi / 2), w)
    wheel(B, at((1.9, 1.95, -0.35)), (0, 0, math.pi / 2), w)
    wheel(B, (2.6, -3.6, 0.15), (0, math.pi / 2, 0.4), w)                                 # a quarta roda caída no chão
    B.cyl(0.11, 0.11, 2.2, (1.7, -1.2, 0.3), (math.pi / 2, 0.3, 0.2), c, 8)               # pedaço do eixo partido
    for s in (-1, 1): B.box((4.2, 0.14, 0.14), (-5.0, s * 0.55, 0.25), (0, 0.18, s * 0.06), w, 2.0)   # cabeçalho no chão
    B.box((0.12, 1.3, 0.12), (-6.8, 0, 0.12), (0, 0, 0), w, 1.0)
    for k, (x, y) in enumerate(((1.0, 3.0), (-0.6, 3.3), (3.6, 1.8))):                     # tábuas soltas
        B.box((1.8, 0.4, 0.08), (x, y, 0.05), (0, 0, 0.7 * k + 0.3), w, 2.0)
    return B.done(col)

def cerca(col, M):
    B = Build('cerca'); w, c = M['madeira'], M['casca']
    for k, x in enumerate((-3, 0, 3)):
        lean = (0.06, -0.04, 0.08)[k]
        B.cyl(0.17, 0.13, 3.0, (x, 0, 1.25), (lean, lean * 0.5, 0), c, 7)
    B.box((6.4, 0.14, 0.28), (0, 0.18, 2.1), (0.02, 0.0, 0.02), w, 2.0)
    B.box((6.4, 0.14, 0.28), (0.1, 0.18, 1.1), (-0.02, 0.0, -0.03), w, 2.0)
    return B.done(col)

def fogueira(col, M):
    B = Build('fogueira'); r, c, w = M['rocha'], M['casca'], M['cinza']
    for k in range(9):
        a = 2 * math.pi * k / 9
        B.rock(0.36 + 0.06 * math.sin(k * 3), (math.cos(a) * 1.15, math.sin(a) * 1.15, 0.12), r, k)
    B.cyl(0.95, 0.9, 0.06, (0, 0, 0.03), (0, 0, 0), w, 14, 2.0)
    for k in range(4):
        a = k * math.pi / 2 + 0.3
        B.cyl(0.12, 0.08, 1.7, (math.cos(a) * 0.35, math.sin(a) * 0.35, 0.45), (math.cos(a + math.pi / 2) * 0.9, math.sin(a + math.pi / 2) * 0.9, 0), c, 7)
    for k in range(3):                                                                    # lenha empilhada ao lado
        B.cyl(0.14, 0.14, 1.6, (2.2, -0.4 + k * 0.3, 0.14 + (0.24 if k == 1 else 0)), (0, math.pi / 2, 0.1), c, 7)
    return B.done(col)

def marco(col, M):
    B = Build('marco'); r, w = M['rocha'], M['madeira']
    B.box((0.7, 0.45, 2.1), (0, 0, 1.0), (0, 0, 0), r, 1.5)
    B.box((0.5, 0.45, 0.22), (0, 0, 2.15), (0, 0, 0), r, 1.5)          # topo em degrau
    B.box((0.3, 0.45, 0.14), (0, 0, 2.32), (0, 0, 0), r, 1.5)
    B.box((0.5, 0.06, 0.12), (0.0, -0.24, 1.55), (0, 0, 0), M['cinza'], 1.0)               # seta gravada
    for s in (-1, 1): B.box((0.2, 0.06, 0.12), (0.18, -0.24, 1.55 + s * 0.08), (0, s * 0.7, 0), M['cinza'], 1.0)
    for k in range(3): B.rock(0.3, (0.5 * math.cos(k * 2.1), 0.5 * math.sin(k * 2.1), 0.1), r, k + 20)
    return B.done(col)

def caixotes(col, M):
    B = Build('caixotes'); w = M['madeira']
    for (x, y, z, s, rz) in ((0, 0, 0.55, 1.1, 0.1), (1.2, 0.1, 0.45, 0.9, -0.25), (0.4, 0.05, 1.6, 0.95, 0.4)):
        B.box((s, s, s), (x, y, z), (0, 0, rz), w, 1.5)
        for d in (-1, 1): B.box((s * 1.02, 0.06, 0.12), (x, y + d * s * 0.5, z), (0, 0, rz), M['casca'], 1.0)
    B.rock(0.55, (-1.1, 0.4, 0.3), M['saco'], 7)
    return B.done(col)

def main():
    col = collection()
    M = dict(madeira=mat('madeira', 'madeira', (0.45, 0.32, 0.2)), casca=mat('casca', 'casca', (0.25, 0.18, 0.12)),
             rocha=mat('rocha', 'rocha', (0.45, 0.45, 0.43)), cinza=mat('cinza', 'terra', (0.12, 0.1, 0.09)), saco=mat('saco', 'terra', (0.55, 0.45, 0.3)))
    M['cinza']['tint'] = [0.25, 0.22, 0.2]; M['saco']['tint'] = [1.15, 1.05, 0.9]
    objs = [carroca(col, M), cerca(col, M), fogueira(col, M), marco(col, M), caixotes(col, M)]
    info = {}
    for i, o in enumerate(objs):
        o.location = (i * 12.0, 30.0, 0)
        info[o.name] = sum(len(p.vertices) - 2 for p in o.data.polygons)
    bpy.context.view_layer.update()
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs: o.select_set(True)
    saved = [o.location.copy() for o in objs]
    for o in objs: o.location = (0, 0, 0)
    bpy.ops.export_scene.gltf(filepath=OUT, export_format='GLB', use_selection=True, export_extras=True, export_materials='EXPORT',
                              export_image_format='NONE', export_apply=True, export_yup=True)
    for o, p in zip(objs, saved): o.location = p          # na cena do Blender ficam lado a lado, para ver
    return dict(triangulos=info, glb=OUT, bytes=os.path.getsize(OUT))

if __name__ == '__main__':
    print(main())
