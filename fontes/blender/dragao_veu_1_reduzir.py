"""Etapa 1 do dragão novo (Corrupted Veil Dragon, Meshy): importa o GLB, reduz para jogo e salva um .blend."""
import bpy, os, sys, time
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
SRC = os.path.join(ROOT, 'fontes', 'recebidos', 'dragao_veu_recebido.glb')
OUT = os.path.join(ROOT, 'fontes', 'blender', 'dragao_veu_reduzido.blend')
TARGET = int(os.environ.get('TRIS', '40000'))
bpy.ops.wm.read_factory_settings(use_empty=True)
t0 = time.time()
bpy.ops.import_scene.gltf(filepath=SRC)
obj = [o for o in bpy.context.scene.objects if o.type == 'MESH'][0]
obj.name = 'dragao_src'
print('importado em %.0fs, tris %d' % (time.time() - t0, sum(len(p.vertices) - 2 for p in obj.data.polygons)))
bpy.context.view_layer.objects.active = obj; obj.select_set(True)
# junta vértices coincidentes (geradores costumam separar as costuras de UV), mantendo as UVs
t0 = time.time()
tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
dec = obj.modifiers.new('dec', 'DECIMATE'); dec.decimate_type = 'COLLAPSE'; dec.ratio = TARGET / tris
dec.use_collapse_triangulate = True
bpy.ops.object.modifier_apply(modifier='dec')
print('reduzido em %.0fs, tris %d' % (time.time() - t0, sum(len(p.vertices) - 2 for p in obj.data.polygons)))
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
import numpy as np
co = np.array([v.co[:] for v in obj.data.vertices])
print('min', co.min(0).round(3), 'max', co.max(0).round(3))
bpy.ops.wm.save_as_mainfile(filepath=OUT)
