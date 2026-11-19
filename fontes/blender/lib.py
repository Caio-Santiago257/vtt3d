"""Biblioteca comum dos scripts de assets (Blender 5.x rodando como módulo Python, sem janela).

Padrão de todo asset exportado:
- unidade em metros; o jogo multiplica por 4/3 (1 quadrado = 1,5 m = 2 unidades);
- pivô no chão, no centro da base; o modelo olha para -Y no Blender (vira +Z no glTF / three.js);
- materiais Principled simples + propriedades extras lidas pelo jogo:
  ramp ('soft'), rim, spec, specSize, noOutline.
"""
import math
import bpy
import bmesh
import numpy as np
from mathutils import Vector, Matrix, Quaternion, Euler


# ---------------------------------------------------------------- cena
def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    for c in (bpy.data.meshes, bpy.data.materials, bpy.data.images, bpy.data.armatures, bpy.data.actions):
        for x in list(c):
            c.remove(x)


def link(obj):
    bpy.context.scene.collection.objects.link(obj)
    return obj


def mesh_obj(name, verts, faces, uvs=None, smooth=True, recalc=True):
    """Cria um objeto a partir de vértices, faces e (opcional) uv por canto de face."""
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], [tuple(f) for f in faces])
    me.validate()
    if uvs is not None:
        uvl = me.uv_layers.new(name='UVMap')
        for poly in me.polygons:
            for li, vi in zip(poly.loop_indices, poly.vertices):
                uvl.data[li].uv = uvs[vi]
    for p in me.polygons:
        p.use_smooth = smooth
    if recalc:  # normais para fora (lofts e tampas saem com a ordem que for)
        bm = bmesh.new(); bm.from_mesh(me)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.to_mesh(me); bm.free()
    me.update()
    return link(bpy.data.objects.new(name, me))


def activate(obj):
    for o in bpy.context.scene.objects:
        o.select_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


def apply_mods(obj):
    activate(obj)
    for m in list(obj.modifiers):
        bpy.ops.object.modifier_apply(modifier=m.name)


def tri_count(obj):
    return sum(len(p.vertices) - 2 for p in obj.data.polygons)


# ---------------------------------------------------------------- materiais e texturas
def image_from_array(name, arr):
    """arr: float32 HxWx4 em 0..1, origem no canto superior esquerdo (como PIL)."""
    h, w = arr.shape[:2]
    img = bpy.data.images.new(name, w, h, alpha=True)
    img.pixels.foreach_set(np.ascontiguousarray(arr[::-1]).astype(np.float32).ravel())
    img.pack()
    return img


def material(name, color=(1, 1, 1, 1), image=None, alpha=None, double=False, emission=None,
             emission_strength=1.0, roughness=0.6, metallic=0.0, **extras):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes.get('Principled BSDF')
    bsdf.inputs['Base Color'].default_value = color
    bsdf.inputs['Roughness'].default_value = roughness
    bsdf.inputs['Metallic'].default_value = metallic
    if image is not None:
        tex = nt.nodes.new('ShaderNodeTexImage')
        tex.image = image
        nt.links.new(tex.outputs['Color'], bsdf.inputs['Base Color'])
        if alpha == 'image':
            nt.links.new(tex.outputs['Alpha'], bsdf.inputs['Alpha'])
    if isinstance(alpha, (int, float)):
        bsdf.inputs['Alpha'].default_value = alpha
    if alpha is not None:
        m.surface_render_method = 'BLENDED'
    if emission is not None:
        bsdf.inputs['Emission Color'].default_value = emission
        bsdf.inputs['Emission Strength'].default_value = emission_strength
    m.use_backface_culling = not double
    for k, v in extras.items():
        m[k] = v
    return m


def set_material(obj, mat):
    obj.data.materials.clear()
    obj.data.materials.append(mat)


# ---------------------------------------------------------------- malhas geradas
def loft(rings, closed=True, cap_top=False, cap_bottom=False):
    """rings: lista de anéis (cada um lista de (x,y,z)), todos com o mesmo número de pontos.
    Retorna verts, faces, uvs (u ao longo do anel, v ao longo da sequência)."""
    n = len(rings[0])
    verts, uvs = [], []
    for j, ring in enumerate(rings):
        for i, p in enumerate(ring):
            verts.append(p)
            uvs.append((i / (n if closed else n - 1), j / (len(rings) - 1)))
    faces = []
    seg = n if closed else n - 1
    for j in range(len(rings) - 1):
        for i in range(seg):
            a = j * n + i
            b = j * n + (i + 1) % n
            faces.append((a, b, b + n, a + n))
    if cap_bottom:
        faces.append(tuple(reversed(range(n))))
    if cap_top:
        faces.append(tuple(range((len(rings) - 1) * n, len(rings) * n)))
    return verts, faces, uvs


# ---------------------------------------------------------------- pesos por proximidade de osso
def seg_dist(p, a, b):
    ab = b - a
    t = max(0.0, min(1.0, (p - a).dot(ab) / max(ab.length_squared, 1e-12)))
    return (p - (a + ab * t)).length


def weight_by_bones(obj, arm, bone_names, power=4.0, keep=3, bias=None):
    """Pesa cada vértice pelos ossos mais próximos (segmento cabeça-cauda), com queda 1/d^power.
    bias: dict nome -> multiplicador de distância (<1 atrai, >1 repele)."""
    bias = bias or {}
    segs = []
    for n in bone_names:
        b = arm.data.bones[n]
        segs.append((n, arm.matrix_world @ b.head_local, arm.matrix_world @ b.tail_local))
    groups = {n: obj.vertex_groups.get(n) or obj.vertex_groups.new(name=n) for n in bone_names}
    mw = obj.matrix_world
    for v in obj.data.vertices:
        p = mw @ v.co
        ds = sorted(((seg_dist(p, a, b) * bias.get(n, 1.0) + 1e-4, n) for n, a, b in segs))[:keep]
        ws = [(1.0 / d ** power, n) for d, n in ds]
        tot = sum(w for w, _ in ws)
        for w, n in ws:
            if w / tot > 0.01:
                groups[n].add([v.index], w / tot, 'REPLACE')


def weight_all(obj, bone):
    g = obj.vertex_groups.get(bone) or obj.vertex_groups.new(name=bone)
    g.add([v.index for v in obj.data.vertices], 1.0, 'REPLACE')


def limit_and_normalize(obj, limit=4):
    activate(obj)
    bpy.ops.object.mode_set(mode='OBJECT')
    me = obj.data
    for v in me.vertices:
        gs = sorted(((g.weight, g.group) for g in v.groups), reverse=True)
        drop = gs[limit:]
        for _, gi in drop:
            obj.vertex_groups[gi].remove([v.index])
        keep = gs[:limit]
        tot = sum(w for w, _ in keep) or 1.0
        for w, gi in keep:
            obj.vertex_groups[gi].add([v.index], w / tot, 'REPLACE')


def bind(obj, arm):
    obj.parent = arm
    mod = obj.modifiers.new('Armature', 'ARMATURE')
    mod.object = arm


# ---------------------------------------------------------------- animação
def rest_q(arm, bone):
    return arm.data.bones[bone].matrix_local.to_quaternion()


def local_rot(arm, bone, axis, deg):
    """Rotação de 'deg' graus em torno de um eixo do espaço do armature (pose de repouso),
    convertida para o espaço local do osso."""
    r = rest_q(arm, bone)
    q = Quaternion(Vector(axis).normalized(), math.radians(deg))
    return r.inverted() @ q @ r


def combine(arm, bone, rots):
    """rots: lista de (eixo, graus) aplicados em ordem."""
    q = Quaternion()
    for axis, deg in rots:
        q = local_rot(arm, bone, axis, deg) @ q
    return q


def new_action(arm, name):
    act = bpy.data.actions.new(name)
    act.use_fake_user = True
    arm.animation_data_create()
    arm.animation_data.action = act
    return act


def key_pose(arm, frame, pose, loc=None):
    """pose: dict osso -> lista de (eixo, graus). loc: dict osso -> Vector (deslocamento no espaço do armature)."""
    for pb in arm.pose.bones:
        pb.rotation_mode = 'QUATERNION'
    for name, rots in pose.items():
        pb = arm.pose.bones[name]
        pb.rotation_quaternion = combine(arm, name, rots)
        pb.keyframe_insert('rotation_quaternion', frame=frame)
    for name, d in (loc or {}).items():
        pb = arm.pose.bones[name]
        r = rest_q(arm, name)
        pb.location = r.inverted() @ Vector(d)
        pb.keyframe_insert('location', frame=frame)


def push_nla(arm, act):
    tr = arm.animation_data.nla_tracks.new()
    tr.name = act.name
    tr.strips.new(act.name, int(act.frame_range[0]), act)
    arm.animation_data.action = None


# ---------------------------------------------------------------- exportação
def export_glb(path, objects):
    for o in bpy.context.scene.objects:
        o.select_set(o in objects)
    bpy.ops.export_scene.gltf(
        filepath=path, export_format='GLB', use_selection=True,
        export_apply=False, export_yup=True, export_extras=True,
        export_animations=True, export_animation_mode='NLA_TRACKS', export_force_sampling=True,
        export_skins=True, export_all_influences=False, export_def_bones=False,
        export_image_format='AUTO', export_texcoords=True, export_normals=True,
        export_morph=True, export_frame_range=False, export_vertex_color='ACTIVE',
    )
