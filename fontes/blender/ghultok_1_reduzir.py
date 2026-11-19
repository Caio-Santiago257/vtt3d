"""Etapa 1 do Ghult'ok (orc bárbaro): importa o GLB (5,3 mi de triângulos), reduz para jogo e salva um .blend.

Reduzir 5 milhões de triângulos de uma vez estoura a memória (8 GB). Então a malha é cortada em fatias
horizontais (em numpy, sem o modo de edição), cada fatia é reduzida separada, e as fatias são juntadas.
Os vértices da costura entre fatias ficam fora do grupo de redução, assim continuam iguais nas duas fatias
e se fundem de novo na junção (sem rachaduras).
"""
import bpy, os, sys, time, gc
import numpy as np
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
SRC = os.path.join(ROOT, 'fontes', 'recebidos', 'ghultok_recebido.glb')
OUT = os.path.join(ROOT, 'fontes', 'blender', 'ghultok_reduzido.blend')
TARGET = int(os.environ.get('TRIS', '60000'))
SLICES = int(os.environ.get('FATIAS', '6'))
bpy.ops.wm.read_factory_settings(use_empty=True)
t0 = time.time()
bpy.ops.import_scene.gltf(filepath=SRC)
src = [o for o in bpy.context.scene.objects if o.type == 'MESH'][0]
me = src.data; mat = src.active_material
print('importado em %.0fs, polígonos %d' % (time.time() - t0, len(me.polygons)))

# ---- dados em numpy (já em triângulos)
nv = len(me.vertices); nl = len(me.loops); npoly = len(me.polygons)
co = np.empty(nv * 3, np.float32); me.vertices.foreach_get('co', co); co = co.reshape(-1, 3)
M = np.array(src.matrix_world, dtype=np.float32)
co = co @ M[:3, :3].T + M[:3, 3]
lv = np.empty(nl, np.int32); me.loops.foreach_get('vertex_index', lv)
ls = np.empty(npoly, np.int32); me.polygons.foreach_get('loop_start', ls)
lt = np.empty(npoly, np.int32); me.polygons.foreach_get('loop_total', lt)
assert (lt == 3).all(), 'malha não está toda em triângulos'
uv = np.empty(nl * 2, np.float32); me.uv_layers.active.data.foreach_get('uv', uv); uv = uv.reshape(-1, 2)
tri_v = lv.reshape(-1, 3); tri_uv = uv.reshape(-1, 3, 2)
bpy.data.objects.remove(src); bpy.data.meshes.remove(me); gc.collect()
zc = co[tri_v].mean(1)[:, 2]
edges = np.quantile(zc, np.linspace(0, 1, SLICES + 1)); edges[-1] += 1
print('fatias em z:', np.round(edges, 3))

parts = []
for k in range(SLICES):
    sel = np.where((zc >= edges[k]) & (zc < edges[k + 1]))[0]
    tv = tri_v[sel]
    used, inv = np.unique(tv, return_inverse=True)
    inv = inv.reshape(-1, 3)
    # vértices de costura: também usados por triângulos de outra fatia
    other = np.zeros(nv, bool); other[tri_v[(zc < edges[k]) | (zc >= edges[k + 1])].ravel()] = True
    seam = other[used]
    m = bpy.data.meshes.new(f'fatia{k}')
    m.vertices.add(len(used)); m.vertices.foreach_set('co', co[used].ravel())
    m.loops.add(len(sel) * 3); m.loops.foreach_set('vertex_index', inv.ravel().astype(np.int32))
    m.polygons.add(len(sel)); m.polygons.foreach_set('loop_start', np.arange(0, len(sel) * 3, 3, dtype=np.int32))
    m.update(calc_edges=True)
    uvl = m.uv_layers.new(name='UVMap'); uvl.data.foreach_set('uv', tri_uv[sel].reshape(-1))
    m.materials.append(mat)
    o = bpy.data.objects.new(f'fatia{k}', m); bpy.context.scene.collection.objects.link(o)
    vg = o.vertex_groups.new(name='reduz'); vg.add(np.where(~seam)[0].tolist(), 1.0, 'REPLACE')
    dec = o.modifiers.new('dec', 'DECIMATE'); dec.decimate_type = 'COLLAPSE'
    dec.ratio = TARGET / len(tri_v); dec.vertex_group = 'reduz'; dec.use_collapse_triangulate = True
    bpy.context.view_layer.objects.active = o; o.select_set(True)
    bpy.ops.object.modifier_apply(modifier='dec'); o.select_set(False)
    o.vertex_groups.clear()
    parts.append(o); gc.collect()
    print('fatia %d: %d -> %d triângulos (%d na costura)' % (k, len(sel), sum(len(p.vertices) - 2 for p in o.data.polygons), seam.sum()))

for o in parts: o.select_set(True)
bpy.context.view_layer.objects.active = parts[0]
bpy.ops.object.join()
obj = bpy.context.view_layer.objects.active; obj.name = 'ghultok_src'
bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.mesh.remove_doubles(threshold=1e-6)       # funde as costuras das fatias
bpy.ops.object.mode_set(mode='OBJECT')
c = np.array([v.co[:] for v in obj.data.vertices])
print('final: %d triângulos em %.0fs' % (sum(len(p.vertices) - 2 for p in obj.data.polygons), time.time() - t0))
print('min', c.min(0).round(3), 'max', c.max(0).round(3))
bpy.ops.wm.save_as_mainfile(filepath=OUT)
