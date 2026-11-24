"""Observatório de Letarion: modela tudo do zero no Blender a partir da planta (fontes/mapas/letarion_plano.json).

Rodar aqui:            python3 fontes/blender/letarion_cenario.py
No Blender do Caio:    abra este arquivo no editor de texto do Blender e rode (ele acha a pasta do projeto pelo caminho do arquivo)

Versão 2: arquitetura com soco, cornija, cunhais, janelas de vitral e portas abertas; livros em 3D nas estantes;
frascos, alambique, ervas, lareira, relógio de pêndulo, lustres, árvores, arbustos, hera, estandartes ao vento;
cascata em camadas com bacia, ponte, calha de madeira e roda d'água (a água cai por cima, como num moinho de verdade).

Unidades do jogo: 1 unidade = 0,75 m; piso do platô em y = 40.
Objetos no GLB:
  letarion_estatico   tudo o que não se mexe (um objeto, um material por textura: poucas chamadas de desenho)
  TELHADO_*           telhados, andar de cima, forros, cúpula, torre e bandeira (o jogo esconde na visão de cima)
  GIRA_*              roda d'água, planetas, esfera armilar, globos, espumas, caldo (giram no jogo)
  BALANCA_barco       o barco balança na água
  PENDULO_*           o pêndulo do relógio e a placa pendurada
  CASCATA             faixas de água que correm (textura que desliza no jogo)
Saídas: public/assets/maps/letarion/letarion.glb, public/assets/maps/letarion/vida.json (fumaça, névoa, gaivotas)
        e fontes/blender/letarion.blend
"""
import array, base64, json, math, os, random
import bpy, bmesh
from mathutils import Vector, Matrix

if '__file__' in globals() and os.path.exists(__file__):
    ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
else:
    _t = getattr(bpy.context.space_data, 'text', None) if bpy.context.space_data else None
    ROOT = os.path.abspath(os.path.join(os.path.dirname(bpy.path.abspath(_t.filepath)), '..', '..')) if _t and _t.filepath else os.getcwd()
ROOT = os.environ.get('LETARION_ROOT') or ROOT
PLANO = os.path.join(ROOT, 'fontes', 'mapas', 'letarion_plano.json')
PASTA = os.path.join(ROOT, 'public', 'assets', 'maps', 'letarion')
OUT = os.path.join(PASTA, 'letarion.glb')
BLEND = os.path.join(ROOT, 'fontes', 'blender', 'letarion.blend')
PL = json.load(open(PLANO))
PH = PL['ph']; RP = PL['rp']; C = PL['c']; PW = PL['pw']
RND = random.Random(5)
VIDA = {'gaivotas': {'n': 9, 'c': C, 'r': [26, 48], 'y': [PH - 8, PH + 22]}, 'fumaca': []}

# ---------------------------------------------------------------- relevo (para assentar as peças no chão)
_raw = base64.b64decode(PL['relevo']); _n = PL['n']; _x0 = PL['x0']; _res = PL['res']
_H = array.array('h'); _H.frombytes(_raw)
def ground(x, z):
    fx = min(_n - 1.001, max(0, (x - _x0) / _res)); fz = min(_n - 1.001, max(0, (z - _x0) / _res))
    i, j = int(fx), int(fz); tx, tz = fx - i, fz - j; k = j * _n + i
    h = lambda q: _H[q] / 100
    return (h(k) * (1 - tx) + h(k + 1) * tx) * (1 - tz) + (h(k + _n) * (1 - tx) + h(k + _n + 1) * tx) * tz

# ---------------------------------------------------------------- materiais (os "extras" dizem ao jogo qual textura e efeito usar)
MATS = {}
def mat(name, color=(1, 1, 1), **ex):
    if name in MATS: return MATS[name]
    m = bpy.data.materials.get('let_' + name) or bpy.data.materials.new('let_' + name)
    for k in list(m.keys()): del m[k]
    m.use_nodes = True
    b = m.node_tree.nodes.get('Principled BSDF')
    if b:
        b.inputs['Base Color'].default_value = (*color, 1); b.inputs['Roughness'].default_value = 0.8
        if ex.get('spec'): b.inputs['Metallic'].default_value = 0.7; b.inputs['Roughness'].default_value = 0.35
        if ex.get('glow'):
            b.inputs['Emission Color'].default_value = (*color, 1); b.inputs['Emission Strength'].default_value = ex.get('brilho', 2)
    for k, v in ex.items(): m[k] = v
    MATS[name] = m; return m
def T(tex, normal=None, **kw):
    d = dict(tex=tex, **kw)
    if normal: d['normal'] = normal
    return d
M = dict(
    pedra=mat('pedra', **T('pedra', 'pedra_n')),
    pedra_base=mat('pedra_base', **T('pedra_base', 'pedra_base_n')),
    lajes=mat('lajes', **T('lajes', 'lajes_n')),
    reboco=mat('reboco', **T('reboco', 'reboco_n')),
    viga=mat('viga', **T('madeira', 'madeira_n')),
    moveis=mat('moveis', **T('moveis', 'moveis_n')),
    tabuas=mat('tabuas', **T('tabuas', 'tabuas_n')),
    telha=mat('telha', **T('telha', 'telha_n')),
    cobre=mat('cobre', **T('cobre', 'cobre_n', rim=0.25, spec=0.25)),
    domo_in=mat('domo_in', **T('carta_b', dupla=1)),
    latao=mat('latao', (0.8, 0.62, 0.3), **T('latao', spec=0.9, rim=0.35)),
    ferro=mat('ferro', (0.2, 0.2, 0.22), **T('ferro', spec=0.35)),
    janela=mat('janela', (1, 0.8, 0.5), glow=1, brilho=2.3, tex='janela', tex_noite='janela_noite'),
    vidro=mat('vidro', (0.62, 0.8, 0.86), glass=1, opacity=0.32),
    lombadas=mat('lombadas', **T('lombadas')),
    globo=mat('globo', **T('globo', spec=0.4)),
    mapa=mat('mapa', **T('mapa')), pergaminho=mat('pergaminho', **T('pergaminho')),
    papel=mat('papel', (0.93, 0.88, 0.74)),
    quadro=mat('quadro', **T('quadro')), pintura=mat('pintura', **T('pintura')),
    carta_a=mat('carta_a', **T('carta_a')), carta_b=mat('carta_b', **T('carta_b')),
    t_vermelho=mat('t_vermelho', **T('tapete_vermelho')), t_azul=mat('t_azul', **T('tapete_azul')),
    t_verde=mat('t_verde', **T('tapete_verde')), t_estrelas=mat('t_estrelas', **T('tapete_estrelas')),
    estandarte=mat('estandarte', **T('estandarte', onda=0.16, dupla=1)),
    bandeira=mat('bandeira', **T('estandarte', onda=0.3, onda_eixo='u', dupla=1)),
    tapecaria=mat('tapecaria', **T('tapecaria', onda=0.03)),
    couro=mat('couro', **T('couro')), saco=mat('saco', **T('saco')),
    tecido_azul=mat('tecido_azul', **T('tecido_azul')), tecido_vermelho=mat('tecido_vermelho', **T('tecido_vermelho')),
    tecido_creme=mat('tecido_creme', **T('tecido_creme')),
    folha=mat('folha', **T('arbusto', recorte=1, vento=0.05)),
    copa=mat('copa', **T('copa', recorte=1, vento=0.09)),
    hera=mat('hera', **T('hera', recorte=1, vento=0.02)),
    flores=mat('flores', **T('flores_canteiro', recorte=1, vento=0.04)),
    casca=mat('casca', **T('casca')),
    terracota=mat('terracota', (0.66, 0.34, 0.22)),
    terra_vaso=mat('terra_vaso', (0.24, 0.16, 0.1)),
    agua=mat('agua', (0.42, 0.66, 0.78), glass=1, opacity=0.62),
    cascata=mat('cascata', glass=1, opacity=0.9, **T('cascata', cascata=0.55)),
    cascata2=mat('cascata2', glass=1, opacity=0.8, **T('cascata2', cascata=1.1)),
    espuma=mat('espuma', glass=1, opacity=0.95, **T('espuma')),
    caldo=mat('caldo', glow=1, brilho=1.5, tex='caldo'),
    vela=mat('vela', (0.95, 0.9, 0.78)),
    corda=mat('corda', (0.66, 0.54, 0.34)),
    gato=mat('gato', (0.9, 0.88, 0.84)), olho=mat('olho', (0.4, 0.95, 0.5), glow=1, brilho=1.6),
    nariz=mat('nariz', (0.85, 0.55, 0.55)),
    planeta1=mat('planeta1', (0.76, 0.44, 0.32)), planeta2=mat('planeta2', (0.42, 0.64, 0.76)), planeta3=mat('planeta3', (0.88, 0.74, 0.52)),
    planeta4=mat('planeta4', (0.58, 0.48, 0.74)), sol=mat('sol', (1.0, 0.82, 0.4), glow=1, brilho=2.2),
    pocao_v=mat('pocao_v', (0.3, 0.92, 0.42), glow=1, brilho=1.5), pocao_r=mat('pocao_r', (0.95, 0.28, 0.34), glow=1, brilho=1.3),
    pocao_a=mat('pocao_a', (0.36, 0.52, 1.0), glow=1, brilho=1.4), pocao_l=mat('pocao_l', (0.75, 0.4, 0.95), glow=1, brilho=1.4),
    pocao_o=mat('pocao_o', (1.0, 0.7, 0.25), glow=1, brilho=1.3),
    cristal=mat('cristal', (0.5, 0.92, 1.0), glow=1, brilho=1.8),
    estatua=mat('estatua', **T('pedra_base', cor=[0.85, 0.85, 0.83])),
    marmore=mat('marmore', (0.9, 0.88, 0.84)),
    preto=mat('preto', (0.08, 0.07, 0.07)), mostrador=mat('mostrador', (0.94, 0.9, 0.78)),
    brasa=mat('brasa', (1.0, 0.45, 0.15), glow=1, brilho=2.0), cinza=mat('cinza', (0.25, 0.23, 0.22)),
    porcelana=mat('porcelana', (0.95, 0.95, 0.98), spec=0.4), erva=mat('erva', (0.4, 0.55, 0.25)), erva2=mat('erva2', (0.55, 0.42, 0.25)),
)
POCOES = ['pocao_v', 'pocao_r', 'pocao_a', 'pocao_l', 'pocao_o']

# ---------------------------------------------------------------- construtor: geometria em coordenadas do jogo (y para cima)
CONV = Matrix(((1, 0, 0, 0), (0, 0, -1, 0), (0, 1, 0, 0), (0, 0, 0, 1)))      # jogo (x, y, z) -> Blender (x, -z, y)
def rot(rx=0, ry=0, rz=0): return Matrix.Rotation(ry, 4, 'Y') @ Matrix.Rotation(rx, 4, 'X') @ Matrix.Rotation(rz, 4, 'Z')
class B:
    def __init__(self, name):
        self.name = name; self.bm = bmesh.new(); self.uv = self.bm.loops.layers.uv.new('UVMap'); self.mats = []; self.tris = 0
    def mi(self, m):
        if m not in self.mats: self.mats.append(m)
        return self.mats.index(m)
    def fin(self, verts, m, uvs=2.0):
        faces = list({f for v in verts for f in v.link_faces})
        idx = self.mi(m)
        for f in faces:
            f.material_index = idx
            n = f.normal; ax = max(range(3), key=lambda i: abs(n[i]))
            for l in f.loops:
                c = l.vert.co
                u, v = ((c.z, -c.y) if ax == 0 else (c.x, c.z) if ax == 1 else (c.x, -c.y))
                l[self.uv].uv = (u / uvs, v / uvs)
        return faces
    def xform(self, verts, Mx): bmesh.ops.transform(self.bm, matrix=Mx, verts=verts)
    def box(self, size, loc, m, ry=0, rx=0, rz=0, uvs=2.0):
        r = bmesh.ops.create_cube(self.bm, size=1.0); vs = r['verts']
        self.xform(vs, Matrix.Translation(loc) @ rot(rx, ry, rz) @ Matrix.Diagonal((*size, 1)))
        bmesh.ops.recalc_face_normals(self.bm, faces=list({f for v in vs for f in v.link_faces}))
        return self.fin(vs, m, uvs)
    def cyl(self, r1, r2, h, loc, m, seg=12, ry=0, rx=0, rz=0, uvs=2.0, caps=True, uvcyl=False):
        r = bmesh.ops.create_cone(self.bm, cap_ends=caps, segments=seg, radius1=r1, radius2=r2, depth=h); vs = r['verts']
        if uvcyl:   # UV em volta (u = ângulo, v = altura): para a casca das árvores
            idx = self.mi(m); rep = max(1, round(2 * math.pi * max(r1, r2) / uvs * 4))
            for f in {f for v in vs for f in v.link_faces}:
                f.material_index = idx
                us = [((math.atan2(l.vert.co.y, l.vert.co.x) / (2 * math.pi)) % 1) for l in f.loops]
                if max(us) - min(us) > 0.5: us = [u + 1 if u < 0.5 else u for u in us]
                for l, u in zip(f.loops, us): l[self.uv].uv = (u * rep, -(l.vert.co.z + h / 2) / uvs)
            self.xform(vs, Matrix.Translation(loc) @ rot(rx, ry, rz) @ Matrix.Rotation(-math.pi / 2, 4, 'X'))
            return
        self.xform(vs, Matrix.Translation(loc) @ rot(rx, ry, rz) @ Matrix.Rotation(-math.pi / 2, 4, 'X'))   # eixo do cone vira o y do jogo
        return self.fin(vs, m, uvs)
    def sphere(self, r, loc, m, seg=14, rings=8, sc=(1, 1, 1), uvs=2.0, uvsph=False, rx=0, ry=0, rz=0):
        res = bmesh.ops.create_uvsphere(self.bm, u_segments=seg, v_segments=rings, radius=r); vs = res['verts']
        if uvsph:   # mapa equirretangular (globos)
            idx = self.mi(m)
            for f in {f for v in vs for f in v.link_faces}:
                f.material_index = idx
                us = [((math.atan2(l.vert.co.y, l.vert.co.x) / (2 * math.pi)) % 1) for l in f.loops]
                if max(us) - min(us) > 0.5: us = [u + 1 if u < 0.5 else u for u in us]
                for l, u in zip(f.loops, us):
                    l[self.uv].uv = (u, 0.5 - math.asin(max(-1, min(1, l.vert.co.z / r))) / math.pi)
            self.xform(vs, Matrix.Translation(loc) @ rot(rx, ry, rz) @ Matrix.Diagonal((*sc, 1)) @ Matrix.Rotation(-math.pi / 2, 4, 'X'))
            return
        self.xform(vs, Matrix.Translation(loc) @ rot(rx, ry, rz) @ Matrix.Diagonal((*sc, 1)))
        return self.fin(vs, m, uvs)
    def torus(self, R, r, loc, m, rx=0, ry=0, rz=0, seg=32, tseg=6, a0=0.0, a1=2 * math.pi):
        vs = []; full = abs(a1 - a0 - 2 * math.pi) < 1e-6
        ns = seg if full else seg + 1
        for i in range(ns):
            a = a0 + (a1 - a0) * i / seg
            for j in range(tseg):
                b = 2 * math.pi * j / tseg
                vs.append(self.bm.verts.new(((R + r * math.cos(b)) * math.cos(a), r * math.sin(b), (R + r * math.cos(b)) * math.sin(a))))
        for i in range(seg):
            i2 = (i + 1) % ns if full else i + 1
            for j in range(tseg):
                a, b2, c, d = i * tseg + j, i * tseg + (j + 1) % tseg, i2 * tseg + (j + 1) % tseg, i2 * tseg + j
                self.bm.faces.new((vs[a], vs[b2], vs[c], vs[d]))
        self.xform(vs, Matrix.Translation(loc) @ rot(rx, ry, rz))
        return self.fin(vs, m, 1.0)
    def poly(self, pts, m, uv=None):
        vs = [self.bm.verts.new(p) for p in pts]
        f = self.bm.faces.new(vs); f.material_index = self.mi(m)
        if uv:
            for l, q in zip(f.loops, uv): l[self.uv].uv = q
        else: self.fin(vs, m)
        return f
    def grade(self, c, ex, ey, nu, nv, m, uv=(0, 0, 1, 1)):
        """placa subdividida (para estandartes ondularem): centro c, vetores ex (largura) e ey (altura, para cima)"""
        c, ex, ey = Vector(c), Vector(ex), Vector(ey)
        vs = [[self.bm.verts.new(c + ex * (i / nu - 0.5) + ey * (j / nv - 0.5)) for i in range(nu + 1)] for j in range(nv + 1)]
        idx = self.mi(m); u0, v0, u1, v1 = uv
        for j in range(nv):
            for i in range(nu):
                f = self.bm.faces.new((vs[j][i], vs[j][i + 1], vs[j + 1][i + 1], vs[j + 1][i])); f.material_index = idx
                for l, (a, b) in zip(f.loops, [(i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1)]):
                    l[self.uv].uv = (u0 + (u1 - u0) * a / nu, v1 - (v1 - v0) * b / nv)   # v = 0 é o alto da imagem
    def strip(self, rows, m, vscale=1.0, uscale=1.0):
        """faixa: lista de (esquerda, direita) em sequência; UV ao longo (v) e através (u)"""
        vs = [(self.bm.verts.new(a), self.bm.verts.new(b)) for a, b in rows]
        acc = 0; idx = self.mi(m)
        for i in range(len(rows) - 1):
            a, b = vs[i]; c, d = vs[i + 1]
            f = self.bm.faces.new((a, b, d, c)); f.material_index = idx
            seg = (Vector(rows[i + 1][0]) - Vector(rows[i][0])).length
            for l, q in zip(f.loops, [(0, acc), (uscale, acc), (uscale, acc + seg * vscale), (0, acc + seg * vscale)]): l[self.uv].uv = q
            acc += seg * vscale
    def done(self, col, extras=None, loc=None, ry=0):
        bmesh.ops.transform(self.bm, matrix=CONV, verts=self.bm.verts[:])
        me = bpy.data.meshes.new(self.name); self.bm.to_mesh(me); self.bm.free()
        for m in self.mats: me.materials.append(m)
        o = bpy.data.objects.new(self.name, me); col.objects.link(o)
        if loc is not None: o.location = (loc[0], -loc[2], loc[1])
        o.rotation_euler = (0, 0, ry)
        for k, v in (extras or {}).items(): o[k] = v
        self.tris = sum(len(p.vertices) - 2 for p in me.polygons)
        return o

def collection():
    c = bpy.data.collections.get('COL_Letarion')
    if c:
        for o in list(c.objects): bpy.data.objects.remove(o, do_unlink=True)
        bpy.data.collections.remove(c)
    c = bpy.data.collections.new('COL_Letarion'); bpy.context.scene.collection.children.link(c); return c

def lerp(a, b, t): return a + (b - a) * t
class Loc:
    """referencial de um móvel: L(dx, dy, dz) vira coordenada do mundo (frente = +z local)"""
    def __init__(self, x, z, ry, y=None): self.x, self.z, self.a, self.y = x, z, math.radians(ry), PH if y is None else y
    def __call__(self, dx, dy, dz): return (self.x + math.cos(self.a) * dx + math.sin(self.a) * dz, self.y + dy, self.z - math.sin(self.a) * dx + math.cos(self.a) * dz)
    def v(self, dx, dz): return (math.cos(self.a) * dx + math.sin(self.a) * dz, 0, -math.sin(self.a) * dx + math.cos(self.a) * dz)
def sub(L, dx, dz, dy=0.0, dry=0.0):
    p = L(dx, 0, dz); return Loc(p[0], p[2], math.degrees(L.a) + dry, y=L.y + dy)

# ================================================================ ARQUITETURA
HW = 6.5          # altura do térreo (pedra)
def janela_pedra(S, x, z, a, y0, th, larg=1.4, alt=2.4, lados=(-1, 1)):
    """janela no plano da parede (ângulo a): vitral dos dois lados, moldura de pedra, peitoril e verga"""
    nx, nz = -math.sin(a), math.cos(a); tx, tz = math.cos(a), math.sin(a)
    yc = y0 + 1.2 + alt / 2
    for s in lados:
        o = th / 2 + 0.02
        cs = [(-larg / 2, -alt / 2), (larg / 2, -alt / 2), (larg / 2, alt / 2), (-larg / 2, alt / 2)]
        if s < 0: cs = [(larg / 2, -alt / 2), (-larg / 2, -alt / 2), (-larg / 2, alt / 2), (larg / 2, alt / 2)]
        S.poly([(x + nx * s * o + tx * w, yc + hh, z + nz * s * o + tz * w) for (w, hh) in cs], M['janela'], uv=[(0, 1), (1, 1), (1, 0), (0, 0)])
        o2 = th / 2 + 0.12
        S.box((larg + 0.7, 0.22, 0.32), (x + nx * s * o2, yc - alt / 2 - 0.08, z + nz * s * o2), M['pedra_base'], ry=-a)     # peitoril
        S.box((larg + 0.6, 0.42, 0.26), (x + nx * s * o2, yc + alt / 2 + 0.2, z + nz * s * o2), M['pedra_base'], ry=-a)      # verga
        for d in (-1, 1): S.box((0.26, alt, 0.22), (x + nx * s * o2 + tx * d * (larg / 2 + 0.13), yc, z + nz * s * o2 + tz * d * (larg / 2 + 0.13)), M['pedra_base'], ry=-a)
def parede(S, x1, z1, x2, z2, y0, h, th=0.6, janelas=(), soco=True, cornija=True, lados=(-1, 1)):
    L = math.hypot(x2 - x1, z2 - z1); a = math.atan2(z2 - z1, x2 - x1)
    if L < 0.05: return
    S.box((L, h, th), ((x1 + x2) / 2, y0 + h / 2, (z1 + z2) / 2), M['pedra'], ry=-a, uvs=3.0)
    if soco: S.box((L, 0.8, th + 0.24), ((x1 + x2) / 2, y0 + 0.4, (z1 + z2) / 2), M['pedra_base'], ry=-a, uvs=3.0)
    if cornija: S.box((L + 0.1, 0.32, th + 0.3), ((x1 + x2) / 2, y0 + h - 0.16, (z1 + z2) / 2), M['pedra_base'], ry=-a, uvs=3.0)
    for t in janelas: janela_pedra(S, lerp(x1, x2, t), lerp(z1, z2, t), a, y0, th, lados=lados)
def cunhais(S, x, z, y0, h):
    for k in range(int(h / 0.62)):
        w = 0.95 if k % 2 == 0 else 0.7
        S.box((w, 0.56, 0.7 if k % 2 == 0 else 0.95), (x, y0 + 0.31 + k * 0.62, z), M['pedra_base'], uvs=1.5)
def porta_aberta(S, x, z, horiz, larg, y0, sentido=1, alt=3.7):
    """batentes de pedra, verga e a folha de madeira aberta (com ferragens)"""
    for g in (-1, 1):
        px, pz = (x + g * (larg / 2 + 0.18), z) if horiz else (x, z + g * (larg / 2 + 0.18))
        S.box((0.42, alt, 0.86), (px, y0 + alt / 2, pz), M['pedra_base'], ry=0 if horiz else math.pi / 2)
    S.box((larg + 1.1, 0.5, 0.86), (x, y0 + alt + 0.2, z), M['pedra_base'], ry=0 if horiz else math.pi / 2)
    hx, hz = (x - larg / 2, z) if horiz else (x, z - larg / 2)
    w = larg / 2 - 0.05
    ang = (math.radians(100) * sentido) if horiz else (-math.pi / 2 + math.radians(100) * sentido)
    cx, cz = hx + math.cos(ang) * w / 2, hz - math.sin(ang) * w / 2
    S.box((w, alt - 0.1, 0.14), (cx, y0 + (alt - 0.1) / 2, cz), M['moveis'], ry=ang, uvs=1.5)
    for yy in (0.6, alt - 0.8): S.box((w * 0.9, 0.12, 0.18), (cx, y0 + yy, cz), M['ferro'], ry=ang)

def card(S, c, w, h, ry, m, uv=(0, 0, 1, 1)):
    """cartão vertical (folhagem), base em c"""
    dx, dz = math.cos(ry) * w / 2, -math.sin(ry) * w / 2
    x, y, z = c
    u0, v0, u1, v1 = uv
    S.poly([(x - dx, y, z - dz), (x + dx, y, z + dz), (x + dx, y + h, z + dz), (x - dx, y + h, z - dz)], m, uv=[(u0, v1), (u1, v1), (u1, v0), (u0, v0)])
def moita(S, c, r, h, m=None, n=3):
    """arbusto: cartões cruzados e um chapéu de cartões deitados"""
    m = m or M['folha']
    for k in range(n): card(S, (c[0], c[1] - 0.05, c[2]), r * 2, h, k * math.pi / n + RND.random() * 0.4, m)
    for k in range(3):
        a = k * 2 * math.pi / 3 + RND.random()
        x, z = c[0] + math.cos(a) * r * 0.35, c[2] + math.sin(a) * r * 0.35
        p = [(x - r * 0.7, c[1] + h * 0.75, z - r * 0.7), (x + r * 0.7, c[1] + h * 0.75, z - r * 0.7), (x + r * 0.7, c[1] + h * 0.95, z + r * 0.7), (x - r * 0.7, c[1] + h * 0.95, z + r * 0.7)]
        S.poly(p, m, uv=[(0, 1), (1, 1), (1, 0), (0, 0)])

def andar_de_cima(T, rect, h=4.5, roof=3.4, eixo='x', win=4, y0=PH):
    x0, z0, x1, z1 = rect; ov = 0.4; yb = y0 + HW
    X0, Z0, X1, Z1 = x0 - ov, z0 - ov, x1 + ov, z1 + ov
    lados = [(X0, Z0, X1, Z0), (X1, Z0, X1, Z1), (X1, Z1, X0, Z1), (X0, Z1, X0, Z0)]
    for (a, b, c, d) in lados:   # mísulas de madeira sob o balanço
        L = math.hypot(c - a, d - b); ang = math.atan2(d - b, c - a); nx, nz = -math.sin(ang), math.cos(ang)
        for i in range(1, int(L / 1.8)):
            t = i / int(L / 1.8); px, pz = lerp(a, c, t), lerp(b, d, t)
            T.box((0.22, 0.6, 0.7), (px - nx * 0.1, yb - 0.25, pz - nz * 0.1), M['viga'], ry=-ang)
    T.box((X1 - X0, 0.32, Z1 - Z0), ((X0 + X1) / 2, yb + 0.16, (Z0 + Z1) / 2), M['viga'], uvs=3.0)
    T.box((x1 - x0 - 0.7, 0.15, z1 - z0 - 0.7), ((x0 + x1) / 2, yb - 0.08, (z0 + z1) / 2), M['tabuas'], uvs=3.0)  # forro (visto de dentro)
    for i in range(int((x1 - x0) / 2.2)):   # barrotes do forro
        xx = x0 + 1.1 + i * 2.2
        if xx < x1 - 0.5: T.box((0.28, 0.36, z1 - z0 - 0.7), (xx, yb - 0.3, (z0 + z1) / 2), M['viga'])
    for (a, b, c, d) in lados:
        L = math.hypot(c - a, d - b); ang = math.atan2(d - b, c - a)
        T.box((L, h, 0.4), ((a + c) / 2, yb + 0.32 + h / 2, (b + d) / 2), M['reboco'], ry=-ang, uvs=4.0)
        nx, nz = -math.sin(ang), math.cos(ang)
        k = max(2, int(L / 2.2))
        for i in range(k + 1):   # vigas verticais e diagonais (cruz de santo andré) do enxaimel
            t = i / k; px, pz = lerp(a, c, t), lerp(b, d, t)
            T.box((0.24, h, 0.12), (px - nx * 0.23, yb + 0.32 + h / 2, pz - nz * 0.23), M['viga'], ry=-ang, uvs=1.5)
            if i < k and i % 2 == 0:
                qx, qz = lerp(a, c, (i + 0.5) / k), lerp(b, d, (i + 0.5) / k)
                dl = math.hypot(L / k, h * 0.44)
                for sgn in (1, -1):
                    T.box((0.16, dl, 0.1), (qx - nx * 0.23, yb + 0.32 + h * 0.25, qz - nz * 0.23), M['viga'], ry=-ang, rz=math.atan2(L / k, h * 0.44) * sgn, uvs=1.5)
        for yy in (yb + 0.42, yb + h * 0.56, yb + h + 0.22): T.box((L, 0.22, 0.12), ((a + c) / 2 - nx * 0.23, yy, (b + d) / 2 - nz * 0.23), M['viga'], ry=-ang, uvs=1.5)
        for i in range(win):
            if i % 2 == 1 and win > 2: continue
            t = (i + 0.5) / win; px, pz = lerp(a, c, t), lerp(b, d, t)
            o = 0.25; yc = yb + 0.32 + h * 0.52
            T.poly([(px - nx * o + math.cos(ang) * w, yc + hh, pz - nz * o + math.sin(ang) * w) for (w, hh) in [(0.55, -0.8), (-0.55, -0.8), (-0.55, 0.8), (0.55, 0.8)]],
                   M['janela'], uv=[(0, 1), (1, 1), (1, 0), (0, 0)])
            T.box((1.4, 0.16, 0.3), (px - nx * 0.3, yc - 0.9, pz - nz * 0.3), M['viga'], ry=-ang)
            T.box((1.3, 0.3, 0.36), (px - nx * 0.48, yc - 1.1, pz - nz * 0.48), M['moveis'], ry=-ang)   # floreira na janela
            for q in (-0.4, 0, 0.4):
                cxx, czz = px - nx * 0.5 + math.cos(ang) * q, pz - nz * 0.5 + math.sin(ang) * q
                for r2 in (0, 1): card(T, (cxx, yc - 1.0, czz), 0.55, 0.5, -ang + r2 * math.pi / 2, M['flores'])
    yt = yb + 0.32 + h
    # telhado de duas águas com beiral, cumeeira e testeiras
    if eixo == 'x':
        Lx = X1 - X0 + 1.4; dz = (Z1 - Z0) / 2 + 0.9; slope = math.atan2(roof, dz)
        for s in (-1, 1):
            T.box((Lx, 0.28, math.hypot(dz, roof)), ((X0 + X1) / 2, yt + roof / 2, (Z0 + Z1) / 2 + s * dz / 2), M['telha'], rx=s * slope, uvs=2.5)
            T.box((Lx, 0.3, 0.16), ((X0 + X1) / 2, yt - 0.05, (Z0 + Z1) / 2 + s * dz), M['viga'])
        for xx in (X0, X1):
            T.poly([(xx, yt, Z0), (xx, yt, Z1), (xx, yt + roof, (Z0 + Z1) / 2)], M['reboco'])
            T.poly([(xx, yt + roof, (Z0 + Z1) / 2), (xx, yt, Z1), (xx, yt, Z0)], M['reboco'])
            for s in (-1, 1):
                T.box((0.16, 0.3, math.hypot(dz, roof) + 0.2), (xx + (0.7 if xx == X1 else -0.7), yt + roof / 2, (Z0 + Z1) / 2 + s * dz / 2), M['viga'], rx=s * slope)
        T.cyl(0.26, 0.26, Lx, ((X0 + X1) / 2, yt + roof + 0.08, (Z0 + Z1) / 2), M['telha'], seg=8, rz=math.pi / 2)
    else:
        Lz = Z1 - Z0 + 1.4; dx = (X1 - X0) / 2 + 0.9; slope = math.atan2(roof, dx)
        for s in (-1, 1):
            T.box((math.hypot(dx, roof), 0.28, Lz), ((X0 + X1) / 2 + s * dx / 2, yt + roof / 2, (Z0 + Z1) / 2), M['telha'], rz=-s * slope, uvs=2.5)
            T.box((0.16, 0.3, Lz), ((X0 + X1) / 2 + s * dx, yt - 0.05, (Z0 + Z1) / 2), M['viga'])
        for zz in (Z0, Z1):
            T.poly([(X0, yt, zz), (X1, yt, zz), ((X0 + X1) / 2, yt + roof, zz)], M['reboco'])
            T.poly([((X0 + X1) / 2, yt + roof, zz), (X1, yt, zz), (X0, yt, zz)], M['reboco'])
        T.cyl(0.26, 0.26, Lz, ((X0 + X1) / 2, yt + roof + 0.08, (Z0 + Z1) / 2), M['telha'], seg=8, rx=math.pi / 2)
    # chaminé com capelo; a fumaça sai daqui
    chx, chz = x1 - 1.6, z0 + 1.6
    T.box((1.0, roof + 2.4, 1.0), (chx, yt + (roof + 2.4) / 2, chz), M['pedra'], uvs=2.0)
    T.box((1.3, 0.25, 1.3), (chx, yt + roof + 2.5, chz), M['pedra_base'])
    for d in (-0.4, 0.4): T.box((0.2, 0.45, 0.95), (chx + d, yt + roof + 2.83, chz), M['pedra_base'])
    T.box((1.2, 0.16, 1.2), (chx, yt + roof + 3.12, chz), M['pedra_base'])
    VIDA['fumaca'].append([round(chx, 2), round(yt + roof + 3.3, 2), round(chz, 2), 'chamine'])

def predios(S, T):
    R = PL['rooms']; y0 = PH
    for k, mt in [('recepcao', 'tabuas'), ('biblioteca', 'tabuas'), ('laboratorio', 'lajes'), ('varanda', 'tabuas')]:
        x0, z0, x1, z1 = R[k]
        S.box((x1 - x0, 0.12, z1 - z0), ((x0 + x1) / 2, y0 + 0.06, (z0 + z1) / 2), M[mt], uvs=2.8)
    x0, z0, x1, z1 = R['patio']
    S.box((x1 - x0, 0.06, z1 - z0), ((x0 + x1) / 2, y0 + 0.03, (z0 + z1) / 2), M['lajes'], uvs=3.2)
    dc, dr = PL['dome']['c'], PL['dome']['r']
    S.cyl(dr, dr, 0.12, (dc[0], y0 + 0.06, dc[1]), M['lajes'], seg=40, uvs=2.8)
    # ---- recepção
    rx0, rz0, rx1, rz1 = R['recepcao']
    parede(S, rx0, rz1, 46.4, rz1, y0, HW, janelas=[0.42]); parede(S, 49.6, rz1, rx1, rz1, y0, HW, janelas=[0.58])
    S.box((3.4, HW - 3.9, 0.6), (48, y0 + 3.9 + (HW - 3.9) / 2, rz1), M['pedra'], uvs=3.0)
    parede(S, rx0, rz0, 46.4, rz0, y0, HW); parede(S, 49.6, rz0, rx1, rz0, y0, HW)
    S.box((3.4, HW - 3.9, 0.6), (48, y0 + 3.9 + (HW - 3.9) / 2, rz0), M['pedra'], uvs=3.0)
    for xx, (g0, g1) in ((rx0, (49.3, 52.3)), (rx1, (48.0, 51.0))):
        parede(S, xx, rz0, xx, g0, y0, HW, soco=False); parede(S, xx, g1, xx, rz1, y0, HW, soco=False)
        S.box((0.6, HW - 3.9, g1 - g0 + 0.2), (xx, y0 + 3.9 + (HW - 3.9) / 2, (g0 + g1) / 2), M['pedra'], uvs=3.0)
    # ---- biblioteca
    bx0, bz0, bx1, bz1 = R['biblioteca']
    parede(S, bx0, bz0, bx0, bz1, y0, HW, janelas=[0.25, 0.75]); parede(S, bx0, bz0, bx1, bz0, y0, HW, janelas=[0.7]); parede(S, bx0, bz1, bx1, bz1, y0, HW, janelas=[0.7])
    parede(S, bx1, bz0, bx1, rz0, y0, HW)
    # ---- laboratório
    lx0, lz0, lx1, lz1 = R['laboratorio']
    parede(S, lx0, lz0, lx1, lz0, y0, HW, janelas=[0.25, 0.75]); parede(S, lx0, lz1, lx1, lz1, y0, HW, janelas=[0.35])
    parede(S, lx0, lz0, lx0, rz0, y0, HW)
    parede(S, lx1, lz0, lx1, 47.5, y0, HW); parede(S, lx1, 50.5, lx1, lz1, y0, HW)
    S.box((0.6, HW - 3.9, 3.2), (lx1, y0 + 3.9 + (HW - 3.9) / 2, 49.0), M['pedra'], uvs=3.0)
    for (x, z) in [(bx0, bz0), (bx0, bz1), (bx1, bz1), (lx1, lz0), (lx1, lz1), (lx0, lz1), (rx0, rz1), (rx1, rz1)]: cunhais(S, x, z, y0, HW)
    porta_aberta(S, 48.0, rz1, True, 3.2, y0, 1); porta_aberta(S, 48.0, rz0, True, 3.2, y0, -1)
    porta_aberta(S, rx0, 50.8, False, 3.0, y0, 1); porta_aberta(S, rx1, 49.5, False, 3.0, y0, -1); porta_aberta(S, lx1, 49.0, False, 3.0, y0, 1)
    # ---- tambor da cúpula
    n = 40; HD = 8.0
    for i in range(n):
        a0 = 2 * math.pi * i / n; a1 = 2 * math.pi * (i + 1) / n; am = (a0 + a1) / 2
        seglen = 2 * math.pi * dr / n + 0.06
        if math.radians(80) < am < math.radians(100):
            S.box((seglen, HD - 3.9, 0.7), (dc[0] + dr * math.cos(am), y0 + 3.9 + (HD - 3.9) / 2, dc[1] + dr * math.sin(am)), M['pedra'], ry=-am + math.pi / 2, uvs=3.0)
            continue
        S.box((seglen, HD, 0.7), (dc[0] + dr * math.cos(am), y0 + HD / 2, dc[1] + dr * math.sin(am)), M['pedra'], ry=-am + math.pi / 2, uvs=3.0)
        S.box((seglen, 0.8, 0.94), (dc[0] + dr * math.cos(am), y0 + 0.4, dc[1] + dr * math.sin(am)), M['pedra_base'], ry=-am + math.pi / 2, uvs=3.0)
        if i % 5 == 0:
            S.box((0.7, HD, 0.4), (dc[0] + (dr + 0.45) * math.cos(am), y0 + HD / 2, dc[1] + (dr + 0.45) * math.sin(am)), M['pedra_base'], ry=-am + math.pi / 2, uvs=2.0)
        if i % 5 == 2:
            janela_pedra(S, dc[0] + dr * math.cos(am), dc[1] + dr * math.sin(am), am + math.pi / 2, y0 + 1.6, 0.7, larg=1.2, alt=2.8)
    porta_aberta(S, dc[0], dc[1] + dr, True, 3.0, y0, 1)
    S.torus(dr + 0.45, 0.34, (dc[0], y0 + HD, dc[1]), M['pedra_base'], seg=48, tseg=6)
    # ---- cúpula de cobre com a fresta (forro pintado de céu por dentro)
    slit = math.radians(-40)
    def domo(B_, r, m, inner=False):
        rings, segs = 12, 48
        for j in range(rings):
            p0 = j / rings * math.pi / 2; p1 = (j + 1) / rings * math.pi / 2
            for i in range(segs):
                a0 = 2 * math.pi * i / segs; a1 = 2 * math.pi * (i + 1) / segs; am = (a0 + a1) / 2
                da = (am - slit + math.pi) % (2 * math.pi) - math.pi
                if abs(da) < math.radians(9) and j >= 3: continue
                q = lambda a, p: (dc[0] + r * math.cos(p) * math.cos(a), y0 + HD + r * math.sin(p), dc[1] + r * math.cos(p) * math.sin(a))
                pts = [q(a0, p0), q(a1, p0), q(a1, p1), q(a0, p1)]
                uv = [(i / segs * 8, 1 - j / rings * 3), ((i + 1) / segs * 8, 1 - j / rings * 3), ((i + 1) / segs * 8, 1 - (j + 1) / rings * 3), (i / segs * 8, 1 - (j + 1) / rings * 3)]
                if inner: pts = pts[::-1]; uv = uv[::-1]
                B_.poly(pts, m, uv=uv)
    domo(T, dr + 0.35, M['cobre'])
    domo(T, dr + 0.05, M['domo_in'], inner=True)
    for i in range(12):
        a = 2 * math.pi * i / 12
        if abs(((a - slit + math.pi) % (2 * math.pi)) - math.pi) < math.radians(12): continue
        for j in range(10):
            p0 = j / 10 * math.pi / 2; p1 = (j + 1) / 10 * math.pi / 2; pm = (p0 + p1) / 2
            for r, m, sz in ((dr - 0.1, M['viga'], 0.22), (dr + 0.42, M['cobre'], 0.16)):
                T.box((sz, (p1 - p0) * r + 0.05, sz), (dc[0] + r * math.cos(pm) * math.cos(a), y0 + HD + r * math.sin(pm), dc[1] + r * math.cos(pm) * math.sin(a)), m, ry=-a, rz=pm)
    for s in (-1, 1):
        a = slit + s * math.radians(9)
        for j in range(3, 12):
            p0 = j / 12 * math.pi / 2; p1 = (j + 1) / 12 * math.pi / 2; pm = (p0 + p1) / 2; r = dr + 0.2
            T.box((0.35, (p1 - p0) * r + 0.1, 0.5), (dc[0] + r * math.cos(pm) * math.cos(a), y0 + HD + r * math.sin(pm), dc[1] + r * math.cos(pm) * math.sin(a)), M['latao'], ry=-a, rz=pm)
    T.sphere(0.5, (dc[0], y0 + HD + dr + 0.6, dc[1]), M['latao'], seg=12, rings=8)
    T.cyl(0.05, 0.05, 2.5, (dc[0], y0 + HD + dr + 1.8, dc[1]), M['ferro'], seg=5)
    for k in range(4): T.box((1.0 if k % 2 else 0.12, 0.12, 0.12 if k % 2 else 1.0), (dc[0], y0 + HD + dr + 2.8, dc[1]), M['latao'])
    # ---- andar de cima em enxaimel com telhados
    andar_de_cima(T, R['recepcao'], eixo='x', win=4); andar_de_cima(T, R['biblioteca'], eixo='z', win=3, h=4.0); andar_de_cima(T, R['laboratorio'], eixo='z', win=3, h=3.8, roof=3.0)
    # ---- torre alta sobre o canto da biblioteca, com bandeira no alto
    tx0, tz0, tx1, tz1 = 29.4, 42.4, 35.4, 48.4; tb = y0 + HW
    for lvl in range(4):
        yb = tb + lvl * 4.0
        for (a, b, c, d) in [(tx0, tz0, tx1, tz0), (tx1, tz0, tx1, tz1), (tx1, tz1, tx0, tz1), (tx0, tz1, tx0, tz0)]:
            L = math.hypot(c - a, d - b); ang = math.atan2(d - b, c - a)
            T.box((L + 0.55, 4.0, 0.55), ((a + c) / 2, yb + 2.0, (b + d) / 2), M['pedra'], ry=-ang, uvs=3.0)
            if lvl >= 1: janela_pedra(T, (a + c) / 2, (b + d) / 2, ang, yb - 0.6, 0.55, larg=1.1, alt=1.9, lados=(-1,))
        T.box((tx1 - tx0 + 0.9, 0.3, tz1 - tz0 + 0.9), ((tx0 + tx1) / 2, yb + 0.15, (tz0 + tz1) / 2), M['pedra_base'])
    for (x, z) in [(tx0, tz0), (tx1, tz0), (tx0, tz1), (tx1, tz1)]: cunhais(T, x, z, tb, 16)
    yt = tb + 16
    T.box((tx1 - tx0 + 1.2, 0.5, tz1 - tz0 + 1.2), ((tx0 + tx1) / 2, yt + 0.25, (tz0 + tz1) / 2), M['pedra_base'])
    T.cyl(4.7, 0.12, 7.0, ((tx0 + tx1) / 2, yt + 3.9, (tz0 + tz1) / 2), M['telha'], seg=4, ry=math.pi / 4, uvs=2.0)
    T.cyl(0.06, 0.06, 3.0, ((tx0 + tx1) / 2, yt + 8.4, (tz0 + tz1) / 2), M['ferro'], seg=5)
    F = B('TELHADO_bandeira')
    F.grade(((tx0 + tx1) / 2 + 0.9, yt + 9.2, (tz0 + tz1) / 2), (1.8, 0, 0), (0, 1.1, 0), 8, 3, M['bandeira'])
    F.done(COL, {'telhado': 1})
    # ---- varanda: guarda-corpo com balaústres e escoras descendo pelo penhasco
    x0, z0, x1, z1 = R['varanda']
    for (a, b, c, d) in [(x0, z0, x1, z0), (x1, z0, x1, z1), (x1, z1, x0, z1)]:
        L = math.hypot(c - a, d - b); ang = math.atan2(d - b, c - a)
        S.box((L + 0.2, 0.2, 0.3), ((a + c) / 2, y0 + 1.6, (b + d) / 2), M['moveis'], ry=-ang)
        S.box((L, 0.14, 0.2), ((a + c) / 2, y0 + 0.3, (b + d) / 2), M['moveis'], ry=-ang)
        for i in range(int(L / 0.6) + 1):
            t = i / max(1, int(L / 0.6)); S.cyl(0.07, 0.09, 1.3, (lerp(a, c, t), y0 + 0.95, lerp(b, d, t)), M['viga'], seg=6)
    for zz in (z0 + 0.5, (z0 + z1) / 2, z1 - 0.5):
        S.box((0.4, 9.0, 0.4), (x1 - 2.2, y0 - 4.2, zz), M['viga'], rz=math.radians(32))
        S.box((x1 - x0 + 0.6, 0.45, 0.45), ((x0 + x1) / 2, y0 - 0.25, zz), M['viga'])
    # ---- mureta em volta do platô
    n = 90
    for i in range(n):
        am = 2 * math.pi * (i + 0.5) / n
        deg = math.degrees(am)
        if 94 < deg < 106 or deg > 340 or deg < 20 or abs(deg - math.degrees(PL['th_cascata'])) < 2.5: continue
        r = RP - 0.3
        S.box((2 * math.pi * r / n + 0.08, 1.0, 0.6), (C[0] + r * math.cos(am), y0 + 0.5, C[1] + r * math.sin(am)), M['pedra'], ry=-am + math.pi / 2, uvs=2.0)
        S.box((2 * math.pi * r / n + 0.12, 0.18, 0.78), (C[0] + r * math.cos(am), y0 + 1.09, C[1] + r * math.sin(am)), M['pedra_base'], ry=-am + math.pi / 2, uvs=2.0)
        if i % 6 == 0:
            S.box((0.85, 1.55, 0.85), (C[0] + r * math.cos(am), y0 + 0.77, C[1] + r * math.sin(am)), M['pedra_base'], ry=-am + math.pi / 2)
            S.sphere(0.32, (C[0] + r * math.cos(am), y0 + 1.8, C[1] + r * math.sin(am)), M['pedra_base'], seg=8, rings=5)
    # ---- hera subindo algumas paredes de fora
    for (x, z, vert, h) in [(bx0 - 0.42, 45.0, True, 5.0), (bx0 - 0.42, 52.5, True, 3.8), (35.0, bz1 + 0.42, False, 4.5), (lx1 + 0.42, 52.6, True, 4.2), (61.0, lz1 + 0.42, False, 3.5)]:
        for k in range(3):
            if vert: card(S, (x, y0, z + (k - 1) * 0.9), 1.6, h - k * 0.6, math.pi / 2, M['hera'])
            else: card(S, (x + (k - 1) * 0.9, y0, z), 1.6, h - k * 0.6, 0, M['hera'])

# ================================================================ ESCADARIA
def escadaria(S, skip):
    P = PL['path']
    acc = [0]
    for i in range(1, len(P)): acc.append(acc[-1] + math.hypot(P[i][0] - P[i - 1][0], P[i][1] - P[i - 1][1]))
    L = acc[-1]
    def at(s):
        i = max(1, min(len(P) - 1, next((k for k in range(1, len(P)) if acc[k] >= s), len(P) - 1)))
        t = (s - acc[i - 1]) / max(1e-6, acc[i] - acc[i - 1])
        x = lerp(P[i - 1][0], P[i][0], t); z = lerp(P[i - 1][1], P[i][1], t); h = lerp(P[i - 1][2], P[i][2], t)
        tx, tz = P[i][0] - P[i - 1][0], P[i][1] - P[i - 1][1]; n = math.hypot(tx, tz) or 1
        return x, z, h, tx / n, tz / n
    def fora(x, z, nx, nz):
        return (-nx, -nz) if math.hypot(x + nx - C[0], z + nz - C[1]) < math.hypot(x - nx - C[0], z - nz - C[1]) else (nx, nz)
    STEP = 0.62; s = 0.0
    while s < L - 0.3:
        x, z, h, tx, tz = at(s + STEP / 2)
        x2, z2, h2, *_ = at(min(L, s + STEP))
        a = math.atan2(tz, tx)
        top = max(h, h2) + 0.04
        S.box((STEP + 0.04, 0.7, PW * 2 + 0.3), (x, top - 0.35, z), M['lajes'], ry=-a, uvs=2.2)
        s += STEP
    post = 0; s = 0.6
    while s < L - 2:
        x, z, h, tx, tz = at(s)
        nx, nz = fora(x, z, -tz, tx)
        ox, oz = x + nx * (PW + 0.05), z + nz * (PW + 0.05)
        a = math.atan2(tz, tx)
        if skip(x, z): s += 1.2; post += 1; continue
        S.box((1.25, 0.55, 0.45), (ox, h + 0.2, oz), M['pedra_base'], ry=-a, uvs=1.5)
        if post % 3 == 0:
            S.cyl(0.11, 0.13, 1.7, (ox, h + 0.95, oz), M['viga'], seg=6)
            S.sphere(0.15, (ox, h + 1.85, oz), M['viga'], seg=6, rings=4)
            x2, z2, h2, tx2, tz2 = at(s + 3.6)
            nx2, nz2 = fora(x2, z2, -tz2, tx2)
            px2, pz2 = x2 + nx2 * (PW + 0.05), z2 + nz2 * (PW + 0.05)
            if not skip(x2, z2):
                ll = math.hypot(px2 - ox, pz2 - oz); aa = math.atan2(pz2 - oz, px2 - ox); dy = h2 - h
                S.box((ll, 0.1, 0.1), ((ox + px2) / 2, h + 1.65 + dy / 2, (oz + pz2) / 2), M['viga'], ry=-aa, rz=math.atan2(dy, ll))
                for k in range(4):   # corda que pende entre os postes
                    t0, t1 = k / 4, (k + 1) / 4
                    sag = lambda t: -0.25 * math.sin(math.pi * t)
                    p0 = (lerp(ox, px2, t0), h + 1.05 + dy * t0 + sag(t0), lerp(oz, pz2, t0)); p1 = (lerp(ox, px2, t1), h + 1.05 + dy * t1 + sag(t1), lerp(oz, pz2, t1))
                    sl = math.dist(p0, p1)
                    S.box((sl, 0.06, 0.06), ((p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2, (p0[2] + p1[2]) / 2), M['corda'], ry=-aa, rz=math.atan2(p1[1] - p0[1], math.hypot(p1[0] - p0[0], p1[2] - p0[2])))
        if post % 11 == 5 and h > 2:   # arbustos no pé do barranco (por dentro)
            ix, iz = x - nx * (PW + 0.6), z - nz * (PW + 0.6)
            moita(S, (ix, max(h, ground(ix, iz)) - 0.05, iz), 0.8, 1.1)
        post += 1
        s += 1.2
    return L

# ================================================================ CASCATA, BACIA, PONTE, CALHA E RODA D'ÁGUA
def cascata(S, W):
    th = PL['th_cascata']; fx, fz = PL['fonte']
    ux, uz = math.cos(th), math.sin(th); tx_, tz_ = -uz, ux
    ex, ez = C[0] + RP * ux, C[1] + RP * uz
    # canal de pedra da fonte até a borda do platô
    a = math.atan2(ez - fz, ex - fx); L = math.hypot(ex - fx, ez - fz)
    for s in (-1, 1):
        S.box((L + 0.6, 0.55, 0.32), ((fx + ex) / 2 - math.sin(a) * 0.62 * s, PH + 0.27, (fz + ez) / 2 + math.cos(a) * 0.62 * s), M['pedra_base'], ry=-a, uvs=2.0)
    S.box((L, 0.1, 1.2), ((fx + ex) / 2, PH + 0.06, (fz + ez) / 2), M['pedra_base'], ry=-a)
    W.strip([((fx + math.sin(a) * 0.46, PH + 0.32, fz - math.cos(a) * 0.46), (fx - math.sin(a) * 0.46, PH + 0.32, fz + math.cos(a) * 0.46)),
             ((ex + math.sin(a) * 0.46, PH + 0.3, ez - math.cos(a) * 0.46), (ex - math.sin(a) * 0.46, PH + 0.3, ez + math.cos(a) * 0.46))], M['cascata'], vscale=0.35)
    # bica: laje de pedra que avança sobre o penhasco
    bx_, bz_ = ex + ux * 0.6, ez + uz * 0.6
    S.box((1.6, 0.3, 1.8), (bx_, PH + 0.1, bz_), M['pedra_base'], ry=-th)
    for s in (-1, 1): S.box((1.6, 0.5, 0.25), (bx_ + tx_ * 0.8 * s, PH + 0.4, bz_ + tz_ * 0.8 * s), M['pedra_base'], ry=-th)
    # bacia ao lado da escadaria (mesma conta do gerador)
    P = PL['path']; k = min(range(len(P)), key=lambda i: (P[i][0] - (C[0] + 40 * ux)) ** 2 + (P[i][1] - (C[1] + 40 * uz)) ** 2)
    best = P[k]; hb = best[2]; rpath = math.hypot(best[0] - C[0], best[1] - C[1]); rb = rpath - PW - 1.4
    bx, bz = C[0] + rb * ux, C[1] + rb * uz
    # a queda em camadas: a de trás larga e lenta, a da frente fina e rápida, e fios soltos dos lados
    def queda(r0, r1, w0, w1, off, mat_, vs, alt=0.0):
        rows = []; r = r0
        while r < r1:
            t = (r - r0) / max(0.01, r1 - r0)
            gy = max(ground(C[0] + r * ux + sx * tx_, C[1] + r * uz + sx * tz_) for sx in (-1.4, 0, 1.4))
            y = max(gy + 0.7 + off, hb + 0.45)
            if r < RP + 1.2: y = max(y, PH + 0.25 - (r - RP) * 0.6)      # sai da bica em arco
            w = lerp(w0, w1, t)
            cx, cz = C[0] + r * ux + tx_ * alt, C[1] + r * uz + tz_ * alt
            rows.append(((cx - tx_ * w, y, cz - tz_ * w), (cx + tx_ * w, y, cz + tz_ * w)))
            r += 0.45
        cx, cz = bx + tx_ * alt, bz + tz_ * alt
        rows.append(((cx - tx_ * w1, hb + 0.5, cz - tz_ * w1), (cx + tx_ * w1, hb + 0.5, cz + tz_ * w1)))
        W.strip(rows, mat_, vscale=vs)
    queda(RP + 0.3, rb - 0.2, 0.75, 1.5, 0.0, M['cascata'], 0.16)
    queda(RP + 0.3, rb - 0.2, 0.55, 1.1, 0.18, M['cascata2'], 0.22)
    queda(RP + 1.0, rb - 0.2, 0.18, 0.3, 0.12, M['cascata2'], 0.3, alt=1.3)
    queda(RP + 1.4, rb - 0.2, 0.15, 0.25, 0.1, M['cascata2'], 0.3, alt=-1.25)
    # bacia: muro redondo com capeamento, água e espuma girando onde a queda bate
    for i in range(18):
        ang = i / 18 * 2 * math.pi
        S.box((0.85, 0.9, 0.55), (bx + math.cos(ang) * 2.05, hb + 0.35, bz + math.sin(ang) * 2.05), M['pedra'], ry=-ang + math.pi / 2, uvs=1.5)
        S.box((0.9, 0.16, 0.7), (bx + math.cos(ang) * 2.05, hb + 0.86, bz + math.sin(ang) * 2.05), M['pedra_base'], ry=-ang + math.pi / 2, uvs=1.5)
    S.cyl(1.85, 1.85, 0.08, (bx, hb + 0.58, bz), M['agua'], seg=20)
    for k, (rr, vel, yy) in enumerate([(1.5, 0.5, 0.64), (1.0, -0.8, 0.68)]):
        E = B('GIRA_espuma%d' % k); E.cyl(rr, rr, 0.02, (0, 0, 0), M['espuma'], seg=16, uvs=rr * 2)
        E.done(COL, {'gira_eixo': 'y', 'gira_vel': vel}, loc=(bx - ux * 0.5, hb + yy, bz - uz * 0.5))
    VIDA['fumaca'].append([round(bx - ux * 0.5, 2), round(hb + 0.8, 2), round(bz - uz * 0.5, 2), 'nevoa'])
    # canal atravessando o caminho, sob uma ponte de tábuas com corrimão
    cx2, cz2 = best[0], best[1]
    a2 = math.atan2(uz, ux)
    out_r = rpath + PW + 0.35
    ox, oz = C[0] + out_r * ux, C[1] + out_r * uz
    W.strip([((bx + ux * 1.7 - tx_ * 0.45, hb + 0.22, bz + uz * 1.7 - tz_ * 0.45), (bx + ux * 1.7 + tx_ * 0.45, hb + 0.22, bz + uz * 1.7 + tz_ * 0.45)),
             ((ox - tx_ * 0.45, hb + 0.12, oz - tz_ * 0.45), (ox + tx_ * 0.45, hb + 0.12, oz + tz_ * 0.45))], M['cascata'], vscale=0.4)
    for s in (-1, 1):
        S.box((out_r - rb - 1.6, 0.4, 0.25), ((bx + ox) / 2 + ux * 0.8 + tx_ * 0.62 * s, hb + 0.1, (bz + oz) / 2 + uz * 0.8 + tz_ * 0.62 * s), M['pedra_base'], ry=-a2)
    for k in range(-4, 5):   # tábuas atravessadas no caminho (de uma beira à outra)
        px, pz = cx2 + tx_ * (k * 0.46), cz2 + tz_ * (k * 0.46)
        S.box((PW * 2 + 0.3, 0.14, 0.42), (px, hb + 0.3, pz), M['tabuas'], ry=-a2, uvs=1.2)
    for s in (-1, 1):   # corrimãos dos dois lados da ponte
        rr_ = rpath + s * (PW + 0.05)
        for k in (-1.9, 1.9):
            px, pz = C[0] + rr_ * ux + tx_ * k, C[1] + rr_ * uz + tz_ * k
            S.cyl(0.08, 0.09, 1.2, (px, hb + 0.9, pz), M['viga'], seg=6)
        S.box((0.1, 0.1, 4.0), (C[0] + rr_ * ux, hb + 1.45, C[1] + rr_ * uz), M['viga'], ry=-a2)
        S.box((0.08, 0.08, 4.0), (C[0] + rr_ * ux, hb + 0.95, C[1] + rr_ * uz), M['viga'], ry=-a2)
    # calha de madeira sobre cavaletes: leva a água do caminho até o alto da roda
    R = 1.95
    wr = out_r + 2.3; wx, wz = C[0] + wr * ux, C[1] + wr * uz
    wy = hb - 0.35 - R
    cal_end = wr + 0.35
    c0x, c0z = ox, oz; c1x, c1z = C[0] + cal_end * ux, C[1] + cal_end * uz
    Lc = math.hypot(c1x - c0x, c1z - c0z); ycal0, ycal1 = hb + 0.05, hb - 0.2
    mcx, mcz = (c0x + c1x) / 2, (c0z + c1z) / 2; slope = math.atan2(ycal0 - ycal1, Lc)
    S.box((Lc, 0.08, 0.95), (mcx, (ycal0 + ycal1) / 2 - 0.2, mcz), M['tabuas'], ry=-a2, rz=-slope)
    for s in (-1, 1): S.box((Lc, 0.4, 0.08), (mcx + tx_ * 0.48 * s, (ycal0 + ycal1) / 2, mcz + tz_ * 0.48 * s), M['tabuas'], ry=-a2, rz=-slope)
    W.strip([((c0x - tx_ * 0.4, ycal0 - 0.08, c0z - tz_ * 0.4), (c0x + tx_ * 0.4, ycal0 - 0.08, c0z + tz_ * 0.4)),
             ((c1x - tx_ * 0.4, ycal1 - 0.08, c1z - tz_ * 0.4), (c1x + tx_ * 0.4, ycal1 - 0.08, c1z + tz_ * 0.4))], M['cascata'], vscale=0.5)
    for t in (0.35, 0.85):
        px, pz = lerp(c0x, c1x, t), lerp(c0z, c1z, t); top = lerp(ycal0, ycal1, t) - 0.25; g = ground(px, pz)
        for s in (-1, 1): S.box((0.16, top - g + 0.3, 0.16), (px + tx_ * 0.5 * s, (top + g) / 2, pz + tz_ * 0.5 * s), M['viga'], ry=-a2)
        S.box((0.16, 0.16, 1.2), (px, top, pz), M['viga'], ry=-a2)
    W.strip([((c1x - tx_ * 0.38, ycal1 - 0.1, c1z - tz_ * 0.38), (c1x + tx_ * 0.38, ycal1 - 0.1, c1z + tz_ * 0.38)),
             ((c1x + ux * 0.25 - tx_ * 0.42, wy + R * 0.55, c1z + uz * 0.25 - tz_ * 0.42), (c1x + ux * 0.25 + tx_ * 0.42, wy + R * 0.55, c1z + uz * 0.25 + tz_ * 0.42))], M['cascata2'], vscale=0.4)
    # roda d'água de baldes (eixo ao longo da tangente); gira com a água caindo do lado de fora
    Wh = B('GIRA_roda')
    nsp = 10; nb = 16
    for side in (-0.48, 0.48):
        Wh.torus(R, 0.09, (side, 0, 0), M['viga'], rz=math.pi / 2, seg=32, tseg=5)
        Wh.torus(R * 0.62, 0.07, (side, 0, 0), M['viga'], rz=math.pi / 2, seg=24, tseg=4)
        for k in range(nsp):
            ang = k / nsp * 2 * math.pi
            Wh.box((0.1, R, 0.14), (side, math.sin(ang) * R / 2, math.cos(ang) * R / 2), M['viga'], rx=-ang)
    for k in range(nb):
        ang = k / nb * 2 * math.pi
        Wh.box((1.0, 0.07, 0.42), (0, math.sin(ang) * (R - 0.18), math.cos(ang) * (R - 0.18)), M['tabuas'], rx=-ang + 0.35, uvs=1.0)
        Wh.box((1.0, 0.36, 0.06), (0, math.sin(ang) * (R - 0.04), math.cos(ang) * (R - 0.04)), M['tabuas'], rx=-ang, uvs=1.0)
    Wh.cyl(0.32, 0.32, 1.1, (0, 0, 0), M['viga'], seg=10, rz=math.pi / 2)
    Wh.cyl(0.1, 0.1, 2.4, (0, 0, 0), M['ferro'], seg=8, rz=math.pi / 2)
    Wh.done(COL, {'gira_eixo': 'x', 'gira_vel': -0.75}, loc=(wx, wy, wz), ry=math.atan2(-ux, -uz))
    for s in (-1, 1):   # pilares de pedra sob o eixo, com mancal de ferro
        px, pz = wx + tx_ * 1.25 * s, wz + tz_ * 1.25 * s
        g = min(ground(px, pz), wy - 0.5) - 0.8
        S.box((0.7, wy - g, 0.9), (px, (wy + g) / 2 - 0.05, pz), M['pedra'], ry=-a2, uvs=2.0)
        S.box((0.85, 0.25, 1.05), (px, wy - 0.1, pz), M['pedra_base'], ry=-a2)
        S.box((0.4, 0.35, 0.4), (px, wy + 0.08, pz), M['ferro'], ry=-a2)
    # a água sai por baixo da roda e desce até o mar
    rows = []; r = wr + 0.4; first = True
    while True:
        gx, gz = C[0] + r * ux, C[1] + r * uz
        y = wy - R * 0.55 if first else max(0.05, ground(gx, gz) + 0.45, wy - R * 0.55 - (r - wr - 0.4) * 4.0)   # cai quase a prumo e depois segue a encosta
        first = False
        w = 0.8 + (r - wr) * 0.03
        rows.append(((gx - tx_ * w, y, gz - tz_ * w), (gx + tx_ * w, y, gz + tz_ * w)))
        if y <= 0.06 or r > 72: break
        r += 0.5
    W.strip(rows, M['cascata'], vscale=0.18)
    W.strip([((p[0][0], p[0][1] + 0.12, p[0][2]), (p[1][0], p[1][1] + 0.12, p[1][2])) for p in rows], M['cascata2'], vscale=0.26)
    sea = rows[-1]; sx_, sz_ = (sea[0][0] + sea[1][0]) / 2, (sea[0][2] + sea[1][2]) / 2
    E = B('GIRA_espuma_mar'); E.cyl(1.8, 1.8, 0.02, (0, 0, 0), M['espuma'], seg=16, uvs=3.6); E.done(COL, {'gira_eixo': 'y', 'gira_vel': 0.3}, loc=(sx_, 0.1, sz_))
    VIDA['fumaca'].append([round(sx_, 2), 0.4, round(sz_, 2), 'nevoa'])
    VIDA['fumaca'].append([round(wx, 2), round(wy - R, 2), round(wz, 2), 'nevoa'])
    return dict(best=best, rb=rb, out_r=out_r, wr=wr)

# ================================================================ PÍER E BARCO
def pier(S, x, z):
    P0 = PL['path'][0]; sx, sz = P0[0], P0[1]
    for k in range(17):
        zz = sz + 0.3 + k * 0.53
        S.box((3.4, 0.14, 0.48), (sx + RND.uniform(-0.04, 0.04), 0.62, zz), M['tabuas'], ry=RND.uniform(-0.02, 0.02), uvs=1.4)
    for zz in (sz + 1, sz + 4.6, sz + 8.4):
        for s in (-1.6, 1.6):
            S.cyl(0.17, 0.2, 3.4, (sx + s, -0.9, zz), M['viga'], seg=8)
            S.cyl(0.19, 0.19, 0.12, (sx + s, 0.85, zz), M['ferro'], seg=8)
        S.box((3.7, 0.22, 0.26), (sx, 0.42, zz), M['viga'])
    S.cyl(0.14, 0.16, 1.2, (sx + 1.6, 1.0, sz + 6.2), M['viga'], seg=8)
    Bt = B('BALANCA_barco')
    for i, (w, y) in enumerate([(1.2, 0.0), (1.02, -0.24), (0.66, -0.42)]):
        Bt.box((w * 2, 0.24, 4.3 - i * 0.6), (0, y + 0.3, 0), M['tabuas'], uvs=1.5)
    for s in (-1, 1): Bt.box((0.12, 0.42, 4.1), (s * 1.18, 0.62, 0), M['moveis'], uvs=1.5)
    Bt.box((2.3, 0.42, 0.14), (0, 0.62, 2.05), M['moveis']); Bt.box((2.3, 0.42, 0.14), (0, 0.62, -2.05), M['moveis'])
    Bt.box((1.9, 0.08, 0.4), (0, 0.55, 0.6), M['moveis']); Bt.box((1.9, 0.08, 0.4), (0, 0.55, -0.9), M['moveis'])
    for s in (-1, 1): Bt.box((0.07, 0.07, 2.7), (s * 0.6, 0.66, 0.2), M['viga'], rx=0.12, ry=s * 0.35)
    Bt.box((0.6, 0.3, 0.5), (0, 0.6, -1.5), M['saco'])
    Bt.done(COL, {'balanca': 0.05}, loc=(sx + 3.7, 0.0, sz + 7.0), ry=math.radians(10))
    S.box((1.9, 0.05, 0.05), (sx + 2.6, 0.95, sz + 6.5), M['corda'], ry=-0.3, rz=-0.25)

# ================================================================ MÓVEIS E OBJETOS
def livro(S, L, dx, dz, w, h, d, cell=None, inclina=0.0, deitado=False):
    """livro em 3D: lombada com a arte do atlas (16 x 3 lombadas no alto, páginas embaixo).
    Em pé: grossura w no eixo x, altura h, profundidade d, lombada para a frente (+z).
    Deitado: comprimento h ao longo de +x a partir de dx, grossura w para cima."""
    cell = RND.randrange(48) if cell is None else cell
    ci, cj = divmod(cell, 16)
    su0, su1 = cj / 16 + 0.004, (cj + 1) / 16 - 0.004
    sv0, sv1 = ci * 0.25 + 0.005, (ci + 1) * 0.25 - 0.005
    pu = RND.uniform(0.05, 0.9)
    pg = (pu, 0.78, pu + 0.04, 0.97)
    cv = (su0 + 0.002, sv0 + 0.06, su0 + 0.006, sv1 - 0.06)
    hw, hd = w / 2, d / 2
    ca, sa = math.cos(inclina), math.sin(inclina)
    def P(x, y, z):
        if deitado: x, y = y, x + hw          # deita: a altura vira o comprimento (x) e a grossura sobe
        x, y = x * ca - y * sa, x * sa + y * ca
        return L(dx + x, y, dz + z)
    def q(pts, uvr):
        uv = [(uvr[0], uvr[3]), (uvr[2], uvr[3]), (uvr[2], uvr[1]), (uvr[0], uvr[1])]
        vs = [P(*p) for p in pts]
        if deitado: vs = vs[::-1]; uv = uv[::-1]          # deitar espelha: desvira as faces
        S.poly(vs, M['lombadas'], uv=uv)
    q([(-hw, 0, hd), (hw, 0, hd), (hw, h, hd), (-hw, h, hd)], (su0, sv0, su1, sv1))                 # lombada
    q([(-hw, h, hd), (hw, h, hd), (hw, h, -hd), (-hw, h, -hd)], pg)                                  # páginas (em cima)
    q([(hw, 0, hd), (hw, 0, -hd), (hw, h, -hd), (hw, h, hd)], cv)                                    # capa
    q([(-hw, 0, -hd), (-hw, 0, hd), (-hw, h, hd), (-hw, h, -hd)], cv)                                # contracapa
    if deitado: q([(-hw, 0, -hd), (hw, 0, -hd), (hw, h, -hd), (-hw, h, -hd)][::-1], pg)            # páginas do outro lado
def prateleira_livros(S, L, x0, x1, alt, prof, zf):
    """enche uma prateleira com livros de alturas e grossuras variadas; às vezes um caído, uma pilha deitada ou um enfeite"""
    x = x0; zc = zf - prof / 2
    while x < x1 - 0.06:
        r = RND.random()
        if r < 0.05 and x1 - x > 0.6:          # pilha deitada
            ln = RND.uniform(0.36, 0.46)
            for k in range(RND.randint(2, 4)):
                livro(S, sub(L, x + 0.03, zc, dy=k * 0.085, dry=RND.uniform(-6, 6)), 0, 0, 0.08, ln - k * 0.02, prof * 0.85, deitado=True)
            x += ln + 0.08; continue
        if r < 0.08 and x1 - x > 0.4:          # enfeite: vela, frasco ou esfera de latão
            p = L(x + 0.15, 0, zc)
            k = RND.randrange(3)
            if k == 0: vela(S, p, h=0.22, r=0.05)
            elif k == 1: frasco(S, p, 0.08, M[RND.choice(POCOES)])
            else: S.sphere(0.12, (p[0], p[1] + 0.12, p[2]), M['latao'], seg=8, rings=5)
            x += 0.32; continue
        if r < 0.11: x += RND.uniform(0.1, 0.25); continue   # vão
        w = RND.uniform(0.055, 0.11); h = alt * RND.uniform(0.6, 0.93); d = prof * RND.uniform(0.75, 0.95)
        if RND.random() < 0.05 and x1 - x > 0.5:          # livro tombado, encostado no vizinho
            inc = RND.uniform(0.25, 0.4)
            livro(S, L, x + w / 2 + h * math.sin(inc), zc + (prof - d) / 2, w, h, d, inclina=inc)
            x += w + h * math.sin(inc) + 0.02
        else:
            livro(S, L, x + w / 2, zc + (prof - d) / 2, w, h, d)
            x += w + RND.uniform(0.0, 0.012)
def estante(S, x, z, ry, w=2.4, h=3.6, d=0.75, prateleiras=6):
    L = Loc(x, z, ry)
    S.box((w, h, 0.08), L(0, h / 2, -d / 2 + 0.04), M['moveis'], ry=L.a, uvs=2.0)
    for s in (-1, 1): S.box((0.12, h, d), L(s * (w / 2 - 0.06), h / 2, 0), M['moveis'], ry=L.a, uvs=2.0)
    S.box((w + 0.24, 0.22, d + 0.14), L(0, h + 0.11, 0.02), M['moveis'], ry=L.a)            # coroa
    S.box((w + 0.1, 0.18, d + 0.06), L(0, 0.09, 0.02), M['moveis'], ry=L.a)                 # rodapé
    gap = (h - 0.3) / prateleiras
    for k in range(prateleiras + 1):
        yy = 0.18 + k * gap
        S.box((w - 0.12, 0.07, d - 0.04), L(0, yy, 0), M['moveis'], ry=L.a)
        if k < prateleiras:
            prateleira_livros(S, Loc(x, z, ry, y=PH + yy + 0.035), -w / 2 + 0.14, w / 2 - 0.14, gap - 0.1, d - 0.12, d / 2 - 0.02)
def frasco(S, base, r, liq, tipo=None):
    """frasco de vidro com líquido que brilha: redondo, alto ou em pera"""
    x, y, z = base
    tipo = tipo or RND.choice(['redondo', 'alto', 'pera'])
    if tipo == 'redondo':
        S.sphere(r, (x, y + r, z), liq, seg=8, rings=6, sc=(1, 0.95, 1))
        S.cyl(r * 0.35, r * 0.3, r * 1.1, (x, y + r * 2.3, z), M['vidro'], seg=6)
        S.cyl(r * 0.38, r * 0.38, r * 0.35, (x, y + r * 2.9, z), M['moveis'], seg=6)
    elif tipo == 'alto':
        S.cyl(r * 0.8, r * 0.8, r * 2.6, (x, y + r * 1.3, z), liq, seg=7)
        S.cyl(r * 0.8, r * 0.3, r * 0.6, (x, y + r * 2.9, z), M['vidro'], seg=7)
        S.cyl(r * 0.32, r * 0.32, r * 0.35, (x, y + r * 3.35, z), M['moveis'], seg=6)
    else:
        S.cyl(r * 1.05, r * 0.55, r * 1.6, (x, y + r * 0.8, z), liq, seg=8)
        S.cyl(r * 0.3, r * 0.25, r * 1.2, (x, y + r * 2.2, z), M['vidro'], seg=6)
        S.sphere(r * 0.28, (x, y + r * 2.9, z), M['moveis'], seg=6, rings=4)
def vela(S, p, h=0.3, r=0.06):
    S.cyl(r, r, h, (p[0], p[1] + h / 2, p[2]), M['vela'], seg=6)
    S.cyl(r * 1.8, r * 1.4, 0.05, (p[0], p[1] + 0.02, p[2]), M['latao'], seg=8)
def mesa(S, L, w, d, h=1.05, m='moveis', torneada=True):
    S.box((w, 0.12, d), L(0, h, 0), M[m], ry=L.a, uvs=2.0)
    S.box((w - 0.25, 0.18, d - 0.25), L(0, h - 0.14, 0), M[m], ry=L.a)
    for sx in (-1, 1):
        for sz in (-1, 1):
            if torneada:
                S.cyl(0.07, 0.09, h - 0.1, L(sx * (w / 2 - 0.18), (h - 0.1) / 2, sz * (d / 2 - 0.18)), M[m], seg=6)
                S.sphere(0.11, L(sx * (w / 2 - 0.18), h * 0.45, sz * (d / 2 - 0.18)), M[m], seg=6, rings=4)
            else: S.box((0.12, h, 0.12), L(sx * (w / 2 - 0.18), h / 2, sz * (d / 2 - 0.18)), M[m], ry=L.a)
def cadeira(S, L):
    S.box((0.9, 0.1, 0.85), L(0, 0.85, 0), M['moveis'], ry=L.a); S.box((0.8, 0.08, 0.75), L(0, 0.92, 0), M['tecido_vermelho'], ry=L.a)
    S.box((0.9, 1.2, 0.1), L(0, 1.5, -0.4), M['moveis'], ry=L.a); S.box((0.7, 0.8, 0.04), L(0, 1.45, -0.34), M['tecido_vermelho'], ry=L.a)
    for sx in (-1, 1):
        for sz in (-1, 1): S.cyl(0.05, 0.06, 0.85, L(sx * 0.37, 0.42, sz * 0.36), M['moveis'], seg=6)
def bau(S, L):
    S.box((1.4, 0.75, 0.85), L(0, 0.38, 0), M['moveis'], ry=L.a, uvs=1.5)
    S.cyl(0.43, 0.43, 1.4, L(0, 0.75, 0), M['moveis'], seg=10, ry=L.a, rz=math.pi / 2)
    for dx in (-0.5, 0.5):
        S.box((0.1, 0.8, 0.9), L(dx, 0.4, 0), M['ferro'], ry=L.a)
        S.torus(0.44, 0.04, L(dx, 0.75, 0), M['ferro'], rz=math.pi / 2, ry=L.a, seg=10, tseg=4, a0=0, a1=math.pi)
    S.box((0.22, 0.26, 0.06), L(0, 0.72, 0.44), M['latao'], ry=L.a)
def barril(S, p, r=0.48, h=1.15):
    S.cyl(r * 0.88, r, h / 2, (p[0], p[1] + h / 4, p[2]), M['moveis'], seg=12, uvs=1.0)
    S.cyl(r, r * 0.88, h / 2, (p[0], p[1] + h * 3 / 4, p[2]), M['moveis'], seg=12, uvs=1.0)
    for yy in (0.12, 0.5, 0.88): S.cyl(r * (0.92 if yy != 0.5 else 1.01), r * (0.92 if yy != 0.5 else 1.01), 0.07, (p[0], p[1] + h * yy, p[2]), M['ferro'], seg=12)
    S.cyl(r * 0.85, r * 0.85, 0.02, (p[0], p[1] + h + 0.005, p[2]), M['tabuas'], seg=12)
def caixote(S, p, s=1.0, ry=0):
    S.box((s, s * 0.85, s), (p[0], p[1] + s * 0.425, p[2]), M['tabuas'], ry=ry, uvs=s)
    for dy in (0.08, s * 0.77): S.box((s + 0.04, 0.1, s + 0.04), (p[0], p[1] + dy, p[2]), M['viga'], ry=ry)
def saco(S, p, ry=0):
    S.sphere(0.42, (p[0], p[1] + 0.42, p[2]), M['saco'], seg=8, rings=6, sc=(1, 1.15, 0.85), ry=ry)
    S.cyl(0.14, 0.2, 0.25, (p[0], p[1] + 0.98, p[2]), M['saco'], seg=6); S.cyl(0.16, 0.16, 0.05, (p[0], p[1] + 0.92, p[2]), M['corda'], seg=6)
def vaso(S, p, r=0.4, flores=False, alto=0.8):
    S.cyl(r * 0.75, r, alto, (p[0], p[1] + alto / 2, p[2]), M['terracota'], seg=10)
    S.torus(r, 0.06, (p[0], p[1] + alto, p[2]), M['terracota'], seg=12, tseg=4)
    S.cyl(r * 0.9, r * 0.9, 0.04, (p[0], p[1] + alto - 0.05, p[2]), M['terra_vaso'], seg=10)
    moita(S, (p[0], p[1] + alto - 0.05, p[2]), r * 1.3, 1.1 + r, M['flores'] if flores else M['folha'])
def arvore(S, p, ry, h=6.5):
    x, y, z = p
    S.cyl(1.25, 1.3, 0.7, (x, y + 0.35, z), M['pedra_base'], seg=14, uvs=2)
    S.cyl(1.05, 1.05, 0.06, (x, y + 0.7, z), M['terra_vaso'], seg=14)
    S.cyl(0.26, 0.17, h * 0.55, (x, y + 0.7 + h * 0.27, z), M['casca'], seg=8, uvcyl=True, uvs=1.2)
    for (a, l, e) in [(0.3, 1.8, 0.7), (2.4, 1.6, 0.8), (4.3, 1.5, 0.6)]:
        a += ry
        bx, bz = math.cos(a) * l * 0.45, math.sin(a) * l * 0.45
        S.cyl(0.12, 0.06, l, (x + bx, y + 0.7 + h * 0.45 + 0.4, z + bz), M['casca'], seg=6, ry=-a + math.pi / 2, rx=e)
    for (dx, dy, dz, r) in [(0, 0.78, 0, 1.8), (0.9, 0.62, 0.4, 1.3), (-0.8, 0.6, -0.5, 1.3), (0.2, 0.62, -1.0, 1.2), (-0.4, 0.66, 0.9, 1.2), (0, 0.95, 0, 1.2)]:
        cx, cy, cz = x + dx, y + 0.7 + h * dy, z + dz
        for k in range(3): card(S, (cx, cy - r * 0.8, cz), r * 2.1, r * 1.8, k * math.pi / 3 + RND.random() * 0.5, M['copa'])
        S.poly([(cx - r, cy, cz - r), (cx + r, cy, cz - r), (cx + r, cy + 0.1, cz + r), (cx - r, cy + 0.1, cz + r)], M['copa'], uv=[(0, 1), (1, 1), (1, 0), (0, 0)])
def lustre(S, x, z):
    y = PH + 5.2
    S.cyl(0.03, 0.03, HW - 5.2 - 0.1, (x, y + (HW - 5.2) / 2, z), M['ferro'], seg=4)
    S.torus(1.0, 0.07, (x, y, z), M['ferro'], seg=20, tseg=4)
    S.torus(0.55, 0.05, (x, y + 0.35, z), M['ferro'], seg=14, tseg=4)
    for k in range(4):
        a = k * math.pi / 2; S.box((1.0, 0.05, 0.05), (x + math.cos(a) * 0.5, y + 0.18, z + math.sin(a) * 0.5), M['ferro'], ry=-a, rz=0.35)
    for k in range(8):
        a = k * math.pi / 4; vela(S, (x + math.cos(a) * 1.0, y + 0.05, z + math.sin(a) * 1.0), h=0.28, r=0.05)
def quadro(S, L, tex, w=2.2, h=1.5, y=3.6):
    S.box((w + 0.25, h + 0.25, 0.1), L(0, y, 0.0), M['moveis'], ry=L.a)
    S.poly([L(-w / 2, y - h / 2, 0.06), L(w / 2, y - h / 2, 0.06), L(w / 2, y + h / 2, 0.06), L(-w / 2, y + h / 2, 0.06)], M[tex], uv=[(0, 1), (1, 1), (1, 0), (0, 0)])
def pano(S, L, mat_, w, h, y_top, nu=4, nv=8, haste=True):
    """estandarte ou tapeçaria pendurado numa haste (ondula no jogo)"""
    S.grade(L(0, y_top - h / 2, 0.05), L.v(w, 0), (0, h, 0), nu, nv, mat_)
    if haste:
        S.cyl(0.05, 0.05, w + 0.4, L(0, y_top + 0.04, 0.05), M['latao'], seg=6, ry=L.a, rz=math.pi / 2)
        for s in (-1, 1): S.sphere(0.09, L(s * (w / 2 + 0.22), y_top + 0.04, 0.05), M['latao'], seg=6, rings=4)

def moveis(S, WT):
    pc = PL['plataforma']['c']; pr = PL['plataforma']['r']; ph = PL['plataforma']['h']
    a0, b0, c0, d0 = PL['rampa']
    # plataforma do telescópio: pedra com base em rampa, piso de tábuas, balaústres e corrimão em arco (abre na escada)
    S.cyl(pr, pr, ph, (pc[0], PH + ph / 2, pc[1]), M['pedra'], seg=28, uvs=3)
    S.cyl(pr + 1.75, pr - 0.02, ph + 0.03, (pc[0], PH + ph / 2 - 0.02, pc[1]), M['pedra'], seg=28, uvs=3)
    S.cyl(pr + 0.12, pr + 0.12, 0.16, (pc[0], PH + ph + 0.02, pc[1]), M['pedra_base'], seg=28)
    S.cyl(pr, pr, 0.04, (pc[0], PH + ph + 0.11, pc[1]), M['tabuas'], seg=28, uvs=3)
    g0, g1 = math.radians(44), math.radians(136)
    for i in range(28):
        a = 2 * math.pi * i / 28
        if g0 < a < g1: continue
        S.cyl(0.05, 0.06, 1.05, (pc[0] + (pr - 0.12) * math.cos(a), PH + ph + 0.62, pc[1] + (pr - 0.12) * math.sin(a)), M['latao'], seg=5)
    S.torus(pr - 0.12, 0.055, (pc[0], PH + ph + 1.15, pc[1]), M['latao'], seg=26, tseg=5, a0=g1, a1=g0 + 2 * math.pi)
    nst = 8
    for k in range(nst):
        zz = lerp(d0, b0, (k + 0.5) / nst); hh = ph * (k + 1) / nst
        S.box((c0 - a0, hh, (d0 - b0) / nst + 0.02), ((a0 + c0) / 2, PH + hh / 2, zz), M['lajes'], uvs=2.0)
        S.box((c0 - a0 + 0.1, 0.06, 0.14), ((a0 + c0) / 2, PH + hh, zz + (d0 - b0) / nst / 2 - 0.05), M['latao'])
        for sx in (a0 - 0.6, c0 + 0.6):
            S.box((1.2, hh + 0.14, (d0 - b0) / nst + 0.02), (sx, PH + (hh + 0.14) / 2, zz), M['pedra'], uvs=2.5)
    for s in (a0 + 0.1, c0 - 0.1):   # corrimãos de latão que sobem com a escada
        S.cyl(0.05, 0.06, 1.2, (s, PH + 0.6, d0 - 0.2), M['latao'], seg=5)
        S.cyl(0.05, 0.06, 1.2, (s, PH + ph + 0.6, b0 + 0.3), M['latao'], seg=5)
        Lr = math.hypot(d0 - b0 - 0.5, ph)
        S.cyl(0.05, 0.05, Lr, (s, PH + ph / 2 + 1.15, (b0 + d0) / 2 + 0.05), M['latao'], seg=6, rx=-(math.pi / 2 - math.atan2(ph, d0 - b0 - 0.5)))

    for f in PL['moveis']:
        t, x, z, ry = f['t'], f['x'], f['z'], f.get('ry', 0)
        L = Loc(x, z, ry); a = L.a
        if t == 'telescopio':
            S.cyl(0.95, 1.25, 0.6, (x, PH + ph + 0.3, z), M['ferro'], seg=18)
            S.torus(1.1, 0.06, (x, PH + ph + 0.62, z), M['latao'], seg=24, tseg=4)
            for k in range(24):   # engrenagem da base
                aa = k * math.pi / 12; S.box((0.12, 0.2, 0.16), (x + math.cos(aa) * 1.22, PH + ph + 0.3, z + math.sin(aa) * 1.22), M['latao'], ry=-aa)
            for s in (-1, 1): S.box((0.28, 2.6, 0.45), (x + s * 0.72 * math.sin(math.radians(-40)), PH + ph + 1.85, z - s * 0.72 * math.cos(math.radians(-40))), M['latao'], ry=math.radians(40))
            az = math.radians(-40); el = math.radians(50)
            dx, dy, dz = math.cos(el) * math.cos(az), math.sin(el), math.cos(el) * math.sin(az)
            cx, cy, cz = x + dx * 2.5, PH + ph + 3.0 + dy * 2.5, z + dz * 2.5
            rr = dict(ry=-az + math.pi / 2, rx=math.pi / 2 - el)
            pos = -3.0
            for (r1, r2, Lg, m) in [(0.52, 0.6, 3.0, 'latao'), (0.6, 0.66, 4.0, 'moveis'), (0.66, 0.78, 4.0, 'latao'), (0.78, 0.86, 1.5, 'latao')]:
                mx, my, mz = cx + dx * (pos + Lg / 2), cy + dy * (pos + Lg / 2), cz + dz * (pos + Lg / 2)
                S.cyl(r1, r2, Lg, (mx, my, mz), M[m], seg=20, **rr); pos += Lg
            for k in (-2.9, 0.0, 4.0, 8.0, 9.5):
                S.torus(0.62 + max(0, k) * 0.022 + 0.06, 0.08, (cx + dx * k, cy + dy * k, cz + dz * k), M['latao'], rx=math.pi / 2 - el, ry=-az + math.pi / 2, seg=20, tseg=5)
            S.cyl(0.88, 0.88, 0.05, (cx + dx * 9.48, cy + dy * 9.48, cz + dz * 9.48), M['vidro'], seg=20, **rr)
            S.cyl(0.09, 0.12, 1.0, (cx - dx * 3.4, cy - dy * 3.4, cz - dz * 3.4), M['latao'], seg=8, **rr)
            S.cyl(0.25, 0.3, 2.2, (cx + dx * 1.2 + 0.62, cy + dy * 1.2 + 0.55, cz + dz * 1.2), M['latao'], seg=10, **rr)
            S.cyl(0.28, 0.28, 1.4, (cx - dx * 1.6, cy - dy * 1.6 - 0.75, cz - dz * 1.6), M['ferro'], seg=10)
        elif t == 'orrery':
            O = B('GIRA_orrery'); hy = 9.5
            O.cyl(0.04, 0.04, 3.0, (0, hy + 1.5, 0), M['latao'], seg=5)
            O.sphere(0.62, (0, hy, 0), M['sol'], seg=16, rings=10)
            O.torus(0.8, 0.04, (0, hy, 0), M['latao'], seg=20, tseg=4)
            for k, (r, s, m, ph2) in enumerate([(1.8, 0.28, 'planeta2', 0.3), (3.0, 0.45, 'planeta1', 2.1), (4.2, 0.6, 'planeta3', 4.0), (5.4, 0.38, 'planeta4', 5.2)]):
                px, pz = r * math.cos(ph2), r * math.sin(ph2)
                O.box((r, 0.05, 0.05), (px / 2, hy - 0.05 * k, pz / 2), M['latao'], ry=-ph2)
                O.cyl(0.025, 0.025, 1.0 + k * 0.4, (px, hy - 0.5 - k * 0.2, pz), M['latao'], seg=4)
                O.sphere(s, (px, hy - 1.0 - k * 0.4, pz), M[m], seg=14, rings=9)
                if k == 2: O.torus(s * 1.7, 0.05, (px, hy - 1.0 - k * 0.4, pz), M['planeta3'], rx=0.4, seg=24, tseg=4)
                if k == 1: O.sphere(0.1, (px + 0.7, hy - 1.4, pz), M['marmore'], seg=6, rings=4)
            O.done(COL, {'gira_eixo': 'y', 'gira_vel': 0.12}, loc=(x, PH, z))
        elif t == 'armilar':
            S.cyl(0.6, 0.85, 0.9, (x, PH + 0.45, z), M['moveis'], seg=12); S.cyl(0.14, 0.14, 1.4, (x, PH + 1.6, z), M['latao'], seg=6)
            S.torus(0.7, 0.05, (x, PH + 0.9, z), M['latao'], seg=16, tseg=4)
            A = B('GIRA_armilar'); yy = 3.2
            A.torus(1.4, 0.06, (0, yy, 0), M['latao'], rx=math.pi / 2, seg=32, tseg=5)
            A.torus(1.4, 0.06, (0, yy, 0), M['latao'], rz=math.pi / 2, seg=32, tseg=5)
            A.torus(1.25, 0.05, (0, yy, 0), M['latao'], rx=math.pi / 2, rz=0.4, seg=32, tseg=5)
            A.torus(1.1, 0.05, (0, yy, 0), M['latao'], seg=32, tseg=5)
            A.sphere(0.35, (0, yy, 0), M['globo'], seg=14, rings=8, uvsph=True)
            A.cyl(0.03, 0.03, 3.4, (0, yy, 0), M['latao'], seg=4, rz=0.4)
            A.done(COL, {'gira_eixo': 'y', 'gira_vel': 0.35}, loc=(x, PH, z))
        elif t in ('mesa_mapas', 'mesa_globo', 'mesa_leitura', 'mesa_instrumentos'):
            w_, d_ = (1.7, 1.3) if t == 'mesa_globo' else (2.6, 1.4)
            mesa(S, L, w_, d_)
            if t == 'mesa_mapas':
                S.box((1.4, 0.02, 1.0), L(-0.3, 1.13, 0), M['carta_a'], ry=a + 0.1, uvs=1.4)
                S.box((0.9, 0.02, 0.7), L(0.75, 1.14, 0.15), M['mapa'], ry=a - 0.2, uvs=0.9)
                S.cyl(0.06, 0.06, 0.7, L(0.9, 1.2, -0.4), M['pergaminho'], seg=6, rz=math.pi / 2, ry=a + 0.4)
                vela(S, L(1.1, 1.12, 0.5)); S.torus(0.16, 0.025, L(-0.9, 1.15, 0.4), M['latao'], seg=14, tseg=4)
            if t == 'mesa_leitura':
                for k in range(3): livro(S, sub(L, -1.0, 0.15, dy=1.12 + k * 0.1, dry=k * 12), 0, 0, 0.09, 0.42, 0.32, deitado=True)
                S.box((0.9, 0.03, 0.62), L(0.3, 1.13, 0), M['pergaminho'], ry=a + 0.15)
                vela(S, L(0.95, 1.12, -0.35)); vela(S, L(1.05, 1.12, -0.15), h=0.2)
                S.cyl(0.08, 0.1, 0.18, L(-0.2, 1.21, -0.45), M['preto'], seg=6)
                S.box((0.02, 0.02, 0.45), L(-0.12, 1.32, -0.42), M['papel'], ry=a + 0.6, rx=0.5)
            if t == 'mesa_instrumentos':
                S.box((1.3, 0.02, 0.9), L(0.4, 1.13, 0), M['carta_b'], ry=a, uvs=1.3)
                S.torus(0.32, 0.03, L(-0.7, 1.45, 0), M['latao'], rx=math.pi / 2, ry=a, seg=20, tseg=4)
                S.cyl(0.32, 0.32, 0.03, L(-0.7, 1.45, 0.0), M['latao'], seg=16, rx=math.pi / 2, ry=a)
                S.box((0.06, 0.45, 0.06), L(-0.7, 1.28, 0), M['latao'], ry=a)
                S.torus(0.3, 0.025, L(0.5, 1.2, 0.2), M['latao'], seg=12, tseg=4, a0=0, a1=1.1)
                for k in range(2): livro(S, sub(L, 0.75, -0.3, dy=1.12 + k * 0.1, dry=k * 9), 0, 0, 0.09, 0.4, 0.3, deitado=True)
        elif t == 'globo' or t == 'globo_pe':
            base = 1.12 if t == 'globo' else 0.0
            if t == 'globo_pe':
                for k in range(3): S.box((0.08, 1.4, 0.08), L(math.cos(k * 2.1) * 0.35, 0.7, math.sin(k * 2.1) * 0.35), M['moveis'], ry=a, rx=math.sin(k * 2.1) * 0.15, rz=-math.cos(k * 2.1) * 0.15)
                S.torus(0.42, 0.04, (x, PH + 0.5, z), M['moveis'], seg=14, tseg=4)
            yy = PH + base + (1.45 if t == 'globo_pe' else 0.75)
            Gl = B('GIRA_globo_%d' % int(x * 10))
            Gl.sphere(0.55 if t == 'globo_pe' else 0.42, (0, 0, 0), M['globo'], seg=20, rings=12, uvsph=True, rz=0.41)
            Gl.done(COL, {'gira_eixo': 'y', 'gira_vel': 0.25}, loc=(x, yy, z))
            rg = 0.66 if t == 'globo_pe' else 0.52
            S.torus(rg, 0.035, (x, yy, z), M['latao'], rx=math.pi / 2, rz=0.41, ry=a, seg=28, tseg=4)
            S.cyl(0.22, 0.3, 0.25, (x, yy - rg - 0.1, z), M['latao'], seg=10)
        elif t in ('estante', 'estante_curva'):
            estante(S, x, z, ry, w=2.4 if t == 'estante' else 2.6, h=3.6 if t == 'estante' else 3.8)
        elif t == 'carta_estelar':
            S.box((2.1, 2.7, 0.08), L(0, 3.6, 0), M['moveis'], ry=a)
            S.poly([L(-0.95, 2.35, 0.05), L(0.95, 2.35, 0.05), L(0.95, 4.85, 0.05), L(-0.95, 4.85, 0.05)], M['carta_a' if f.get('seed', 0) % 2 else 'carta_b'], uv=[(0, 1), (1, 1), (1, 0), (0, 0)])
            S.cyl(0.05, 0.05, 2.3, L(0, 4.98, 0.06), M['latao'], seg=6, ry=a, rz=math.pi / 2)
        elif t == 'pergaminhos':
            for k in range(3): S.cyl(0.08, 0.08, 0.9, L(k * 0.3 - 0.3, 0.09, k * 0.2), M['pergaminho'], seg=8, rz=math.pi / 2, ry=a + k * 0.7)
            S.box((0.9, 0.02, 0.6), L(0.4, 0.02, -0.4), M['carta_a'], ry=a + 0.5, uvs=0.9)
        elif t == 'tapete_redondo':
            rr = 1.7; nseg = 24
            for k in range(nseg):
                a1_, a2_ = 2 * math.pi * k / nseg, 2 * math.pi * (k + 1) / nseg
                S.poly([(x, PH + 0.14, z), (x + rr * math.cos(a2_), PH + 0.14, z + rr * math.sin(a2_)), (x + rr * math.cos(a1_), PH + 0.14, z + rr * math.sin(a1_))], M['t_estrelas'],
                       uv=[(0.5, 0.5), (0.5 + 0.5 * math.cos(a2_), 0.5 + 0.5 * math.sin(a2_)), (0.5 + 0.5 * math.cos(a1_), 0.5 + 0.5 * math.sin(a1_))])
        elif t == 'tapete':
            mt = {'azul': 't_azul', 'vermelho': 't_vermelho', 'verde': 't_verde'}[f.get('cor', 'vermelho')]
            w, d = f.get('w', 4), f.get('d', 3)
            S.poly([L(-w / 2, 0.14, -d / 2), L(-w / 2, 0.14, d / 2), L(w / 2, 0.14, d / 2), L(w / 2, 0.14, -d / 2)], M[mt], uv=[(0, 0), (0, 1), (1, 1), (1, 0)])
        elif t == 'luneta':
            for k in range(3): S.box((0.07, 1.8, 0.07), L(math.cos(k * 2.1) * 0.4, 0.85, math.sin(k * 2.1) * 0.4), M['moveis'], ry=a, rx=math.cos(k * 2.1) * 0.2, rz=math.sin(k * 2.1) * 0.2)
            S.cyl(0.14, 0.2, 2.0, L(0, 1.9, 0), M['latao'], seg=10, rx=0.9, ry=a)
        elif t == 'cadeira': cadeira(S, L)
        elif t == 'balcao':
            for i in range(11):
                u = (i - 5) / 5; ang = u * 0.75
                px, pz = x + math.sin(ang) * 3.4, z - 2.2 + math.cos(ang) * 3.0
                S.box((0.66, 1.2, 0.62), (px, PH + 0.6, pz), M['moveis'], ry=-ang, uvs=1.5)
                S.box((0.4, 0.9, 0.05), (px + math.sin(ang) * 0.33, PH + 0.6, pz + math.cos(ang) * 0.33), M['viga'], ry=-ang)
                S.box((0.72, 0.1, 0.86), (px, PH + 1.25, pz), M['viga'], ry=-ang)
            for k in range(3): livro(S, Loc(x + 1.3, z - 0.3, 20 + k * 10, y=PH + 1.3 + k * 0.1), 0, 0, 0.09, 0.4, 0.3, deitado=True)
            vela(S, (x - 2.0, PH + 1.3, z - 0.2)); S.box((0.6, 0.02, 0.4), (x - 0.6, PH + 1.31, z), M['pergaminho'], ry=0.2)
        elif t == 'gato':
            S.sphere(0.32, (x, PH + 1.62, z), M['gato'], sc=(0.8, 1.1, 1.0), seg=12, rings=8)
            S.sphere(0.23, (x, PH + 2.07, z + 0.08), M['gato'], seg=12, rings=8)
            for s in (-1, 1):
                S.cyl(0.08, 0.0, 0.22, (x + s * 0.13, PH + 2.3, z + 0.06), M['gato'], seg=4)
                S.sphere(0.04, (x + s * 0.085, PH + 2.1, z + 0.28), M['olho'], seg=6, rings=4)
                S.sphere(0.07, (x + s * 0.12, PH + 1.32, z + 0.24), M['gato'], seg=6, rings=4)
            S.sphere(0.03, (x, PH + 2.04, z + 0.31), M['nariz'], seg=5, rings=3)
            S.cyl(0.05, 0.035, 0.9, (x - 0.34, PH + 1.4, z - 0.1), M['gato'], seg=6, rz=1.3)
        elif t == 'livro_aberto':
            for s in (-1, 1): S.box((0.42, 0.06, 0.55), L(s * 0.22, 1.33, 0), M['pergaminho'], ry=a, rz=s * 0.08)
            S.box((0.95, 0.04, 0.6), L(0, 1.3, 0), M['couro'], ry=a)
        elif t == 'sino':
            S.cyl(0.18, 0.12, 0.08, L(0, 1.32, 0), M['moveis'], seg=8); S.sphere(0.14, L(0, 1.42, 0), M['latao'], seg=10, rings=6, sc=(1, 0.8, 1))
            S.sphere(0.03, L(0, 1.55, 0), M['latao'], seg=5, rings=3)
        elif t == 'atril_livro':
            S.cyl(0.18, 0.28, 1.3, L(0, 0.65, 0), M['moveis'], seg=8)
            S.cyl(0.5, 0.6, 0.12, L(0, 0.06, 0), M['moveis'], seg=10)
            S.box((1.9, 0.1, 1.35), L(0, 1.42, 0), M['moveis'], ry=a, rx=-0.28)
            for s in (-1, 1): S.box((0.88, 0.18, 1.18), L(s * 0.44, 1.57, 0.02), M['pergaminho'], ry=a, rx=-0.28, rz=s * 0.1)
            S.box((1.92, 0.05, 1.27), L(0, 1.49, 0), M['couro'], ry=a, rx=-0.28)
            S.box((0.05, 0.01, 0.9), L(0.05, 1.68, 0.15), M['tecido_vermelho'], ry=a, rx=-0.28)
            for s in (-1, 1):
                S.cyl(0.08, 0.08, 1.3, L(s * 1.1, 0.65, 0.3), M['ferro'], seg=6); vela(S, L(s * 1.1, 1.3, 0.3), h=0.45)
        elif t == 'vaso_planta': vaso(S, (x, PH, z), r=0.42)
        elif t == 'vaso_flores': vaso(S, (x, PH, z), r=0.35, flores=True, alto=0.6)
        elif t == 'poltrona':
            S.box((1.35, 0.5, 1.25), L(0, 0.45, 0), M['tecido_vermelho'], ry=a); S.box((1.35, 1.35, 0.3), L(0, 1.05, -0.5), M['tecido_vermelho'], ry=a)
            S.box((1.25, 0.18, 1.0), L(0, 0.78, 0.05), M['tecido_vermelho'], ry=a)
            for s in (-1, 1):
                S.box((0.26, 0.75, 1.25), L(s * 0.62, 0.7, 0), M['tecido_vermelho'], ry=a)
                for sz in (-1, 1): S.cyl(0.06, 0.04, 0.22, L(s * 0.55, 0.1, sz * 0.5), M['moveis'], seg=6)
            S.box((1.45, 0.08, 0.36), L(0, 1.75, -0.5), M['moveis'], ry=a)
        elif t == 'banquinho':
            S.cyl(0.45, 0.45, 0.2, (x, PH + 0.9, z), M['tecido_vermelho'], seg=12)
            for k in range(3): S.cyl(0.05, 0.05, 0.85, (x + math.cos(k * 2.1) * 0.32, PH + 0.42, z + math.sin(k * 2.1) * 0.32), M['moveis'], seg=5)
        elif t in ('mesinha', 'mesinha_cha'):
            S.cyl(0.62, 0.62, 0.1, (x, PH + 1.0, z), M['moveis'], seg=16); S.cyl(0.1, 0.25, 1.0, (x, PH + 0.5, z), M['moveis'], seg=8)
            S.cyl(0.4, 0.45, 0.08, (x, PH + 0.04, z), M['moveis'], seg=10)
            if t == 'mesinha_cha':
                S.sphere(0.18, (x, PH + 1.22, z), M['porcelana'], seg=10, rings=6, sc=(1, 0.85, 1)); S.cyl(0.03, 0.05, 0.22, (x + 0.2, PH + 1.26, z), M['porcelana'], seg=5, rz=-0.9)
                for k in range(2): S.cyl(0.08, 0.06, 0.1, (x + math.cos(k * 2.5 + 1) * 0.38, PH + 1.1, z + math.sin(k * 2.5 + 1) * 0.38), M['porcelana'], seg=8)
            else:
                livro(S, Loc(x - 0.2, z, 30, y=PH + 1.05), 0, 0, 0.08, 0.38, 0.28, deitado=True)
        elif t == 'ampulheta':
            S.cyl(0.2, 0.02, 0.3, (x, PH + 1.4, z), M['vidro'], seg=10); S.cyl(0.02, 0.2, 0.3, (x, PH + 1.7, z), M['vidro'], seg=10)
            S.cyl(0.14, 0.02, 0.18, (x, PH + 1.34, z), M['pocao_o'], seg=8)
            for yy in (1.22, 1.88): S.cyl(0.25, 0.25, 0.05, (x, PH + yy, z), M['latao'], seg=10)
            for k in range(3): S.cyl(0.02, 0.02, 0.66, (x + math.cos(k * 2.1) * 0.21, PH + 1.55, z + math.sin(k * 2.1) * 0.21), M['latao'], seg=4)
        elif t == 'cabideiro':
            S.cyl(0.06, 0.06, 3.0, (x, PH + 1.5, z), M['moveis'], seg=6)
            for k in range(3): S.box((0.06, 0.8, 0.06), (x + math.cos(k * 2.1) * 0.25, PH + 0.3, z + math.sin(k * 2.1) * 0.25), M['moveis'], rx=math.sin(k * 2.1) * 0.5, rz=-math.cos(k * 2.1) * 0.5)
            S.box((0.9, 1.7, 0.35), (x + 0.15, PH + 2.0, z), M['tecido_azul'], uvs=1.0)
            S.sphere(0.28, (x - 0.2, PH + 2.95, z), M['tecido_vermelho'], seg=8, rings=5, sc=(1, 0.6, 1))
        elif t == 'quadro': quadro(S, L, f.get('tex', 'quadro'), w=2.2, h=1.6 if f.get('tex') == 'quadro' else 1.5)
        elif t == 'mapa_parede':
            S.box((2.8, 2.1, 0.06), L(0, 3.5, 0), M['moveis'], ry=a)
            S.poly([L(-1.3, 2.55, 0.05), L(1.3, 2.55, 0.05), L(1.3, 4.45, 0.05), L(-1.3, 4.45, 0.05)], M['mapa'], uv=[(0, 1), (1, 1), (1, 0), (0, 0)])
        elif t == 'estandarte_parede': pano(S, L, M['estandarte'], 1.3, 2.6, 5.4, nu=3, nv=8)
        elif t == 'tapecaria': pano(S, Loc(x + 0.1, z, ry), M['tapecaria'], 2.2, 2.6, 6.0, nu=4, nv=6)
        elif t == 'escada_mao':
            for s in (-1, 1): S.box((0.08, 3.8, 0.08), L(s * 0.35, 1.9, 0.2), M['moveis'], ry=a, rx=0.17)
            for k in range(9): S.box((0.7, 0.06, 0.06), L(0, 0.3 + k * 0.4, 0.2 + 0.07 * k), M['moveis'], ry=a)
        elif t == 'pilha_livros':
            for k in range(6): livro(S, Loc(x, z, ry + k * 17, y=PH + k * 0.1), -0.24, 0, 0.1, 0.5 - k * 0.02, 0.38, deitado=True)
        elif t == 'cesto_pergaminhos':
            S.cyl(0.45, 0.5, 0.9, (x, PH + 0.45, z), M['saco'], seg=10)
            for k in range(7):
                aa = k * 0.9; S.cyl(0.06, 0.06, 1.2, (x + math.cos(aa) * 0.2, PH + 0.9, z + math.sin(aa) * 0.2), M['pergaminho'], seg=6, rx=math.sin(aa) * 0.25, rz=math.cos(aa) * 0.25)
        elif t == 'lareira':
            S.box((3.0, 0.32, 1.3), L(0, 3.2, 0.4), M['pedra_base'], ry=a)
            for s in (-1, 1): S.box((0.5, 3.0, 1.0), L(s * 1.2, 1.5, 0.35), M['pedra_base'], ry=a)
            S.box((2.0, 0.6, 0.9), L(0, 2.75, 0.3), M['pedra'], ry=a)
            S.box((2.0, 2.5, 0.2), L(0, 1.25, -0.1), M['cinza'], ry=a)
            S.box((2.6, 0.2, 1.4), L(0, 0.1, 0.6), M['pedra_base'], ry=a)
            for k in range(3): S.cyl(0.13, 0.13, 1.3, L(-0.1 + k * 0.08, 0.3 + (k % 2) * 0.18, 0.3 + k * 0.12), M['casca'], seg=6, ry=a + 0.2 * k, rz=math.pi / 2)
            S.cyl(0.6, 0.5, 0.12, L(0, 0.24, 0.3), M['brasa'], seg=8)
            for k in range(2): vela(S, L(-0.9 + k * 1.8, 3.37, 0.5), h=0.35)
            S.box((0.5, 0.5, 0.3), L(0, 3.6, 0.4), M['latao'], ry=a)
        elif t == 'bancada':
            mesa(S, L, 6.2, 1.2, h=1.1, torneada=False)
            S.box((6.2, 2.0, 0.1), L(0, 2.55, -0.55), M['moveis'], ry=a)
            S.box((6.2, 0.08, 0.4), L(0, 2.5, -0.35), M['moveis'], ry=a); S.box((6.2, 0.08, 0.4), L(0, 3.2, -0.35), M['moveis'], ry=a)
            for k in range(16): frasco(S, L(-2.8 + k * 0.37, 1.16, -0.15 + (k % 2) * 0.3), 0.12, M[POCOES[k % 5]])
            for k in range(8): frasco(S, L(-2.7 + k * 0.75, 2.54, -0.35), 0.1, M[POCOES[(k + 2) % 5]])
            for k in range(8): frasco(S, L(-2.4 + k * 0.7, 3.24, -0.35), 0.09, M[POCOES[(k + 4) % 5]], tipo='alto')
            S.cyl(0.25, 0.18, 0.25, L(1.9, 1.28, 0.25), M['pedra_base'], seg=8); S.cyl(0.04, 0.05, 0.4, L(1.95, 1.42, 0.25), M['moveis'], seg=5, rz=0.5)
            S.box((0.8, 0.03, 0.55), L(-1.4, 1.17, 0.25), M['pergaminho'], ry=a + 0.2)
        elif t == 'caldeirao':
            S.sphere(0.9, (x, PH + 1.0, z), M['ferro'], sc=(1, 0.78, 1), seg=16, rings=10)
            S.torus(0.78, 0.07, (x, PH + 1.62, z), M['ferro'], seg=18, tseg=5)
            Cd = B('GIRA_caldo'); Cd.cyl(0.74, 0.74, 0.03, (0, 0, 0), M['caldo'], seg=16, uvs=1.48); Cd.done(COL, {'gira_eixo': 'y', 'gira_vel': 0.8}, loc=(x, PH + 1.55, z))
            for k in range(3): S.box((0.12, 0.7, 0.12), (x + math.cos(k * 2.1) * 0.7, PH + 0.3, z + math.sin(k * 2.1) * 0.7), M['ferro'], rx=math.sin(k * 2.1) * 0.2, rz=-math.cos(k * 2.1) * 0.2)
            S.cyl(0.04, 0.05, 1.6, (x + 0.3, PH + 1.9, z), M['moveis'], seg=5, rz=0.35)
            VIDA['fumaca'].append([round(x, 2), round(PH + 1.7, 2), round(z, 2), 'vapor'])
        elif t == 'prateleira_frascos':
            for k in range(4):
                S.box((2.4, 0.08, 0.55), L(0, 1.0 + k * 0.85, 0), M['moveis'], ry=a)
                for j in range(6): frasco(S, L(-1.0 + j * 0.4, 1.04 + k * 0.85, 0.02), 0.1 + RND.random() * 0.03, M[POCOES[(j + k) % 5]])
            for s in (-1, 1): S.box((0.08, 3.5, 0.55), L(s * 1.2, 2.0, 0), M['moveis'], ry=a)
        elif t == 'alambique':
            mesa(S, L, 2.4, 1.3)
            S.cyl(0.35, 0.35, 0.3, L(-0.6, 1.27, 0), M['latao'], seg=10); S.sphere(0.4, L(-0.6, 1.72, 0), M['vidro'], seg=12, rings=8)
            S.sphere(0.32, L(-0.6, 1.66, 0), M['pocao_l'], seg=10, rings=6, sc=(1, 0.7, 1))
            S.cyl(0.05, 0.05, 1.3, L(-0.1, 2.15, 0), M['vidro'], seg=6, rz=1.25, ry=a)
            S.torus(0.18, 0.035, L(0.45, 1.7, 0), M['latao'], seg=12, tseg=4); S.torus(0.18, 0.035, L(0.45, 1.85, 0), M['latao'], seg=12, tseg=4)
            frasco(S, L(0.75, 1.12, 0.1), 0.17, M['pocao_l'], tipo='redondo'); vela(S, L(-0.6, 1.12, 0.0), h=0.12, r=0.1)
            S.box((0.7, 0.04, 0.5), L(0.6, 1.14, -0.4), M['couro'], ry=a - 0.2)
        elif t == 'barril': barril(S, (x, PH, z))
        elif t == 'sacos':
            yb = PH if z < 80 else 0.62
            for k, (dx, dz) in enumerate([(0, 0), (0.6, 0.3), (-0.5, 0.35)]): saco(S, (x + dx, yb, z + dz), ry=k)
        elif t == 'caixotes':
            yb = PH if z < 80 else 0.62
            caixote(S, (x, yb, z), 1.0, a); caixote(S, (x + 0.25, yb + 0.85, z + 0.1), 0.8, a + 0.4)
        elif t == 'ervas':
            for k in range(7):
                px = x - 3 + k
                S.cyl(0.015, 0.015, 0.6, (px, PH + HW - 0.6, z), M['corda'], seg=3)
                for j in range(4): S.cyl(0.0, 0.09, 0.5, (px + (j - 1.5) * 0.06, PH + HW - 1.15, z + (j % 2) * 0.05), M['erva' if (k + j) % 3 else 'erva2'], seg=5, rz=(j - 1.5) * 0.12)
            S.box((7.2, 0.08, 0.08), (x, PH + HW - 0.32, z), M['viga'])
        elif t == 'cristais':
            for k in range(5):
                aa = k * 1.3; S.cyl(0.12, 0.0, 0.5 + (k % 3) * 0.18, (x + math.cos(aa) * 0.18, PH + 1.35, z + math.sin(aa) * 0.12), M['cristal'], seg=5, rx=math.sin(aa) * 0.3, rz=math.cos(aa) * 0.3)
        elif t == 'banco':
            S.box((2.4, 0.16, 0.7), L(0, 0.75, 0), M['moveis'], ry=a); S.box((2.4, 0.6, 0.1), L(0, 1.15, -0.32), M['moveis'], ry=a)
            for s in (-1, 1): S.box((0.16, 0.75, 0.62), L(s * 1.0, 0.37, 0), M['pedra_base'], ry=a)
        elif t == 'arco':
            for s in (-1, 1):
                S.box((1.0, 5.2, 1.0), L(s * 2.4, 2.6, 0), M['pedra'], ry=a, uvs=2.5); S.box((1.3, 0.6, 1.3), L(s * 2.4, 0.3, 0), M['pedra_base'], ry=a)
                S.box((1.25, 0.3, 1.25), L(s * 2.4, 5.1, 0), M['pedra_base'], ry=a)
                for side in (-1, 1): pano(S, sub(L, s * 2.4, side * 0.56, dry=0 if side > 0 else 180), M['estandarte'], 0.9, 2.4, 4.7, nu=3, nv=8)
            for k in range(11):
                u = k / 10 * math.pi
                S.box((0.8, 0.95, 1.0), L(-math.cos(u) * 2.4, 5.2 + math.sin(u) * 1.5, 0), M['pedra'], ry=a, rz=u - math.pi / 2, uvs=1.5)
            S.box((0.9, 1.0, 1.1), L(0, 6.85, 0), M['pedra_base'], ry=a)
            S.sphere(0.45, L(0, 7.6, 0), M['latao'], seg=10, rings=6)
            for k in range(8): S.box((0.08, 0.7 if k % 2 == 0 else 0.4, 0.08), L(0, 7.6, 0), M['latao'], ry=a, rz=k * math.pi / 4)
        elif t == 'estatua':
            S.box((1.7, 0.9, 1.7), L(0, 0.45, 0), M['pedra_base'], ry=a); S.box((1.4, 0.35, 1.4), L(0, 1.07, 0), M['pedra_base'], ry=a)
            S.cyl(0.62, 0.42, 2.3, L(0, 2.4, 0), M['estatua'], seg=12)
            S.cyl(0.45, 0.5, 0.5, L(0, 3.65, 0), M['estatua'], seg=10)
            S.sphere(0.32, L(0, 4.12, 0.05), M['estatua'], seg=12, rings=8)
            S.cyl(0.36, 0.05, 0.9, L(0, 4.2, -0.05), M['estatua'], seg=8, rx=-0.3, ry=a)
            S.cyl(0.12, 0.1, 1.3, L(0.48, 4.0, 0.2), M['estatua'], seg=6, rz=-0.6, ry=a)
            S.torus(0.32, 0.04, L(0.9, 4.75, 0.3), M['latao'], rx=0.3, ry=a, seg=16, tseg=4)
            S.cyl(0.07, 0.07, 3.6, L(-0.55, 2.4, 0.2), M['estatua'], seg=6)
            S.sphere(0.16, L(-0.55, 4.25, 0.2), M['estatua'], seg=6, rings=4)
            moita(S, L(0, 0.9, 0.95), 0.6, 0.6, M['flores'])
        elif t == 'canteiro':
            S.box((2.0, 0.6, 2.0), L(0, 0.3, 0), M['pedra_base'], ry=a); S.box((1.8, 0.04, 1.8), L(0, 0.6, 0), M['terra_vaso'], ry=a)
            for k in range(4): moita(S, L((k % 2 - 0.5) * 0.8, 0.6, (k // 2 - 0.5) * 0.8), 0.5, 0.8, M['flores'])
        elif t == 'fonte':
            S.cyl(1.6, 1.7, 0.85, (x, PH + 0.42, z), M['pedra'], seg=20, uvs=2.5)
            S.torus(1.62, 0.14, (x, PH + 0.86, z), M['pedra_base'], seg=24, tseg=5)
            S.cyl(1.45, 1.45, 0.05, (x, PH + 0.76, z), M['agua'], seg=20)
            S.cyl(0.28, 0.38, 1.7, (x, PH + 1.5, z), M['pedra_base'], seg=10)
            S.cyl(0.9, 0.4, 0.4, (x, PH + 2.35, z), M['pedra_base'], seg=14)
            S.cyl(0.8, 0.8, 0.04, (x, PH + 2.52, z), M['agua'], seg=14)
            S.cyl(0.14, 0.2, 0.9, (x, PH + 2.95, z), M['pedra_base'], seg=8)
            S.sphere(0.25, (x, PH + 3.45, z), M['latao'], seg=8, rings=5)
            for k in range(8):   # véus de água caindo da taça para a bacia
                aa = k * math.pi / 4
                p0 = (x + math.cos(aa) * 0.88, PH + 2.5, z + math.sin(aa) * 0.88); p1 = (x + math.cos(aa) * 1.12, PH + 0.78, z + math.sin(aa) * 1.12)
                tx2, tz2 = -math.sin(aa) * 0.3, math.cos(aa) * 0.3
                WT.strip([((p0[0] - tx2, p0[1], p0[2] - tz2), (p0[0] + tx2, p0[1], p0[2] + tz2)), ((p1[0] - tx2, p1[1], p1[2] - tz2), (p1[0] + tx2, p1[1], p1[2] + tz2))], M['cascata2'], vscale=0.5)
            E = B('GIRA_espuma_fonte'); E.cyl(1.3, 1.3, 0.02, (0, 0, 0), M['espuma'], seg=16, uvs=2.6); E.done(COL, {'gira_eixo': 'y', 'gira_vel': 0.4}, loc=(x, PH + 0.8, z))
        elif t == 'relogio_sol':
            S.cyl(0.5, 0.6, 1.0, (x, PH + 0.5, z), M['pedra_base'], seg=12); S.cyl(0.72, 0.72, 0.08, (x, PH + 1.05, z), M['latao'], seg=20)
            S.box((0.05, 0.5, 0.6), (x, PH + 1.3, z), M['latao'], rx=0.6)
            for k in range(12): S.box((0.04, 0.02, 0.18), (x + math.cos(k * math.pi / 6) * 0.55, PH + 1.1, z + math.sin(k * math.pi / 6) * 0.55), M['preto'], ry=-k * math.pi / 6 + math.pi / 2)
        elif t == 'relogio':
            S.box((1.0, 0.5, 0.65), L(0, 0.25, 0), M['moveis'], ry=a); S.box((0.8, 3.0, 0.5), L(0, 2.0, 0), M['moveis'], ry=a)
            S.box((1.0, 1.1, 0.6), L(0, 3.95, 0), M['moveis'], ry=a); S.box((1.1, 0.2, 0.7), L(0, 4.6, 0), M['moveis'], ry=a)
            S.cyl(0.38, 0.38, 0.05, L(0, 3.95, 0.31), M['mostrador'], seg=16, rx=math.pi / 2, ry=a)
            S.torus(0.39, 0.04, L(0, 3.95, 0.32), M['latao'], rx=math.pi / 2, ry=a, seg=16, tseg=4)
            S.box((0.04, 0.26, 0.02), L(0, 4.05, 0.35), M['preto'], ry=a); S.box((0.2, 0.03, 0.02), L(0.08, 3.95, 0.35), M['preto'], ry=a)
            S.box((0.5, 2.3, 0.02), L(0, 2.0, 0.26), M['vidro'], ry=a)
            Pd = B('PENDULO_relogio')
            Pd.box((0.04, 1.8, 0.03), (0, -0.9, 0), M['latao']); Pd.cyl(0.2, 0.2, 0.05, (0, -1.8, 0), M['latao'], seg=14, rx=math.pi / 2)
            Pd.done(COL, {'pendulo': 0.22}, loc=L(0, 3.3, 0.12), ry=a)
        elif t == 'lustre': lustre(S, x, z)
        elif t == 'bau': bau(S, L)
        elif t == 'arvore': arvore(S, (x, PH, z), a)
        elif t == 'arbusto': moita(S, (x, PH - 0.05, z), 0.9, 1.3)
        elif t == 'barris':
            yb = PH if z < 80 else 0.62
            barril(S, (x, yb, z)); barril(S, (x + 1.0, yb, z + 0.3)); barril(S, (x + 0.45, yb, z - 0.85), r=0.42, h=1.0)
        elif t == 'placa':
            S.box((0.08, 0.08, 1.2), (x, PH + 4.2, z + 0.6), M['ferro'])
            S.box((0.06, 0.6, 0.06), (x, PH + 3.9, z + 0.25), M['ferro'], rx=0.8)
            Pl = B('PENDULO_placa')
            Pl.box((0.9, 1.0, 0.06), (0, -0.6, 0), M['moveis'])
            Pl.poly([(-0.38, -1.05, 0.04), (0.38, -1.05, 0.04), (0.38, -0.15, 0.04), (-0.38, -0.15, 0.04)], M['estandarte'], uv=[(0.05, 0.6), (0.95, 0.6), (0.95, 0.05), (0.05, 0.05)])
            Pl.poly([(0.38, -1.05, -0.04), (-0.38, -1.05, -0.04), (-0.38, -0.15, -0.04), (0.38, -0.15, -0.04)], M['estandarte'], uv=[(0.05, 0.6), (0.95, 0.6), (0.95, 0.05), (0.05, 0.05)])
            Pl.done(COL, {'pendulo': 0.06}, loc=(x, PH + 4.15, z + 1.0), ry=math.pi / 2)
        elif t == 'rolo_corda':
            for k in range(4): S.torus(0.38 - k * 0.06, 0.06, (x, 0.75 + k * 0.08, z), M['corda'], seg=14, tseg=4)
        elif t == 'pier': pier(S, x, z)

def main():
    global COL
    for o in list(bpy.data.objects):
        if o.name.startswith(('letarion', 'TELHADO', 'GIRA_', 'CASCATA', 'barco', 'BALANCA', 'PENDULO')): bpy.data.objects.remove(o, do_unlink=True)
    COL = collection()
    S = B('letarion_estatico'); T_ = B('TELHADO_predios'); W = B('CASCATA')
    info_c = cascata(S, W)
    best = info_c['best']
    near = lambda x, z: math.hypot(x - best[0], z - best[1]) < 3.2
    L = escadaria(S, near); print('escadaria: %.0f unidades' % L)
    predios(S, T_)
    moveis(S, W)
    info = {}
    for b_, ex in [(S, None), (T_, {'telhado': 1}), (W, None)]:
        o = b_.done(COL, ex); info[o.name] = b_.tris
    print('triângulos:', info, 'total ~', sum(info.values()))
    os.makedirs(PASTA, exist_ok=True)
    bpy.ops.object.select_all(action='DESELECT')
    for o in COL.objects: o.select_set(True)
    bpy.ops.export_scene.gltf(filepath=OUT, export_format='GLB', use_selection=True, export_extras=True, export_materials='EXPORT',
                              export_image_format='NONE', export_apply=True, export_yup=True)
    print('GLB: %.1f MB' % (os.path.getsize(OUT) / 1e6))
    json.dump(VIDA, open(os.path.join(PASTA, 'vida.json'), 'w'))
    try: bpy.ops.wm.save_as_mainfile(filepath=BLEND)
    except Exception as e: print('blend não salvo:', e)
    return dict(tris=info, glb=OUT)

if __name__ == '__main__':
    print(main())
