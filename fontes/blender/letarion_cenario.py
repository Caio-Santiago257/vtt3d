"""Observatório de Letarion: modela tudo do zero no Blender a partir da planta (fontes/mapas/letarion_plano.json).

Rodar aqui:            python3 fontes/blender/letarion_cenario.py
No Blender do Caio:    cole no editor de texto e rode (LETARION_ROOT aponta para a pasta do projeto)

Peças (unidades do jogo; 1 unidade = 0,75 m; piso do platô em y = 40):
  escadaria   degraus de pedra ao longo da espiral, meio-fio e guarda-corpo de madeira com corda
  cascata     fonte no pátio, canal, queda pela encosta, bacia, roda d'água (gira), ponte e a segunda queda até o mar
  píer        deque de tábuas sobre estacas, barco a remo, barris
  prédios     paredes de pedra com janelas acesas, andar de cima em enxaimel, telhados de telha, torre alta,
              cúpula de cobre com a fresta aberta e o grande telescópio saindo por ela
  cômodos     recepção (balcão, gato, poltronas, estantes), biblioteca (estantes, o grande livro aberto, globo),
              cúpula (plataforma com degraus, telescópio, planetas pendurados que giram, esfera armilar, cartas estelares),
              laboratório (bancada de frascos, caldeirão, lente), varanda (luneta), pátio (fonte, estátua, bancos, arco)
Objetos no GLB:
  letarion_estatico   tudo o que não se mexe (um objeto, um material por textura: poucas chamadas de desenho)
  TELHADO_*           telhados, andar de cima, forros, cúpula e torre (o jogo esconde na visão de cima)
  GIRA_*              roda d'água, planetas e anéis da esfera armilar (giram no jogo)
  CASCATA             faixas de água que correm (textura que desliza no jogo)
Saída: public/assets/maps/letarion/letarion.glb  (e fontes/blender/letarion.blend)
"""
import base64, json, math, os, random
import bpy, bmesh
from mathutils import Vector, Matrix

ROOT = os.environ.get('LETARION_ROOT') or (os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')) if '__file__' in globals() else os.getcwd())
PLANO = os.path.join(ROOT, 'fontes', 'mapas', 'letarion_plano.json')
OUT = os.environ.get('LETARION_OUT') or os.path.join(ROOT, 'public', 'assets', 'maps', 'letarion', 'letarion.glb')
BLEND = os.path.join(ROOT, 'fontes', 'blender', 'letarion.blend')
PL = json.load(open(PLANO))
PH = PL['ph']; RP = PL['rp']; C = PL['c']; PW = PL['pw']
random.seed(5)

# ---------------------------------------------------------------- relevo (para assentar as peças no chão)
_raw = base64.b64decode(PL['relevo']); _n = PL['n']; _x0 = PL['x0']; _res = PL['res']
import array
_H = array.array('h'); _H.frombytes(_raw)
def ground(x, z):
    fx = min(_n - 1.001, max(0, (x - _x0) / _res)); fz = min(_n - 1.001, max(0, (z - _x0) / _res))
    i, j = int(fx), int(fz); tx, tz = fx - i, fz - j; k = j * _n + i
    h = lambda q: _H[q] / 100
    return (h(k) * (1 - tx) + h(k + 1) * tx) * (1 - tz) + (h(k + _n) * (1 - tx) + h(k + _n + 1) * tx) * tz

# ---------------------------------------------------------------- materiais (os "extras" dizem ao jogo qual textura usar)
MATS = {}
def mat(name, color, **ex):
    if name in MATS: return MATS[name]
    m = bpy.data.materials.get('let_' + name) or bpy.data.materials.new('let_' + name)
    m.use_nodes = True
    b = m.node_tree.nodes.get('Principled BSDF')
    if b:
        b.inputs['Base Color'].default_value = (*color, 1); b.inputs['Roughness'].default_value = ex.pop('rough', 0.85)
        if ex.get('metal'): b.inputs['Metallic'].default_value = 0.8
        if ex.get('glow'):
            b.inputs['Emission Color'].default_value = (*color, 1); b.inputs['Emission Strength'].default_value = ex.get('brilho', 2)
    for k, v in ex.items(): m[k] = v
    MATS[name] = m; return m
M = dict(
    pedra=mat('pedra', (1, 1, 1), tex='pedra', normal='pedra_n'),
    pedra_esc=mat('pedra_esc', (0.42, 0.4, 0.38)),
    degrau=mat('degrau', (0.9, 0.88, 0.85), tex='lajes'),
    reboco=mat('reboco', (1, 1, 1), tex='reboco'),
    viga=mat('viga', (0.24, 0.15, 0.09)),
    madeira=mat('madeira', (1, 1, 1), tex='madeira'),
    tabuas=mat('tabuas', (1, 1, 1), tex='tabuas'),
    telha=mat('telha', (1, 1, 1), tex='telha'),
    lajes=mat('lajes', (1, 1, 1), tex='lajes'),
    cobre=mat('cobre', (1, 1, 1), tex='cobre', rim=0.25),
    domo_in=mat('domo_in', (0.1, 0.15, 0.3), dupla=1),
    latao=mat('latao', (0.78, 0.6, 0.28), metal=1, rough=0.35, rim=0.45),
    ferro=mat('ferro', (0.16, 0.16, 0.18), metal=1, rough=0.5),
    janela=mat('janela', (1.0, 0.74, 0.38), glow=1, brilho=2.4),
    vidro=mat('vidro', (0.55, 0.75, 0.85), glass=1, opacity=0.35),
    livros=mat('livros', (1, 1, 1), tex='livros'),
    carta_a=mat('carta_a', (1, 1, 1), tex='carta_a'), carta_b=mat('carta_b', (1, 1, 1), tex='carta_b'),
    quadro=mat('quadro', (1, 1, 1), tex='quadro'),
    t_vermelho=mat('t_vermelho', (1, 1, 1), tex='tapete_vermelho'), t_azul=mat('t_azul', (1, 1, 1), tex='tapete_azul'), t_verde=mat('t_verde', (1, 1, 1), tex='tapete_verde'),
    couro=mat('couro', (0.45, 0.13, 0.1)), papel=mat('papel', (0.93, 0.88, 0.74)), tecido_azul=mat('tecido_azul', (0.2, 0.28, 0.5)),
    folha=mat('folha', (0.22, 0.42, 0.2)), terracota=mat('terracota', (0.62, 0.32, 0.2)),
    agua=mat('agua', (0.35, 0.6, 0.75), glass=1, opacity=0.6),
    cascata=mat('cascata', (1, 1, 1), tex='cascata', cascata=0.9, glass=1, opacity=0.85),
    espuma=mat('espuma', (1, 1, 1), tex='espuma', glass=1, opacity=0.9),
    corda=mat('corda', (0.62, 0.5, 0.32)),
    gato=mat('gato', (0.86, 0.84, 0.8)), olho=mat('olho', (0.4, 0.9, 0.5), glow=1, brilho=1.5),
    planeta1=mat('planeta1', (0.72, 0.42, 0.32)), planeta2=mat('planeta2', (0.42, 0.62, 0.72)), planeta3=mat('planeta3', (0.86, 0.72, 0.5)),
    planeta4=mat('planeta4', (0.55, 0.45, 0.7)), sol=mat('sol', (1.0, 0.82, 0.4), glow=1, brilho=2.2),
    oceano=mat('oceano', (0.2, 0.36, 0.6)), pocao_v=mat('pocao_v', (0.3, 0.9, 0.4), glow=1, brilho=1.4),
    pocao_r=mat('pocao_r', (0.9, 0.25, 0.3), glow=1, brilho=1.2), pocao_a=mat('pocao_a', (0.35, 0.5, 1.0), glow=1, brilho=1.3),
    estatua=mat('estatua', (0.72, 0.72, 0.7)),
)

# ---------------------------------------------------------------- construtor: geometria em coordenadas do jogo (y para cima)
CONV = Matrix(((1, 0, 0, 0), (0, 0, -1, 0), (0, 1, 0, 0), (0, 0, 0, 1)))      # jogo (x, y, z) -> Blender (x, -z, y)
def rot(rx=0, ry=0, rz=0): return Matrix.Rotation(ry, 4, 'Y') @ Matrix.Rotation(rx, 4, 'X') @ Matrix.Rotation(rz, 4, 'Z')
class B:
    def __init__(self, name):
        self.name = name; self.bm = bmesh.new(); self.uv = self.bm.loops.layers.uv.new('UVMap'); self.mats = []; self.tris = 0
    def mi(self, m):
        if m not in self.mats: self.mats.append(m)
        return self.mats.index(m)
    def fin(self, verts, m, uvs=2.0, uvmode='box'):
        faces = list({f for v in verts for f in v.link_faces})
        idx = self.mi(m)
        for f in faces:
            f.material_index = idx
            if uvmode == 'box':
                n = f.normal; ax = max(range(3), key=lambda i: abs(n[i]))
                for l in f.loops:
                    c = l.vert.co
                    u, v = ((c.z, c.y) if ax == 0 else (c.x, c.z) if ax == 1 else (c.x, c.y))
                    l[self.uv].uv = (u / uvs, v / uvs)
        return faces
    def xform(self, verts, Mx): bmesh.ops.transform(self.bm, matrix=Mx, verts=verts)
    def box(self, size, loc, m, ry=0, rx=0, rz=0, uvs=2.0):
        r = bmesh.ops.create_cube(self.bm, size=1.0); vs = r['verts']
        self.xform(vs, Matrix.Translation(loc) @ rot(rx, ry, rz) @ Matrix.Diagonal((*size, 1)))
        bmesh.ops.recalc_face_normals(self.bm, faces=list({f for v in vs for f in v.link_faces}))
        return self.fin(vs, m, uvs)
    def cyl(self, r1, r2, h, loc, m, seg=12, ry=0, rx=0, rz=0, uvs=2.0, caps=True):
        r = bmesh.ops.create_cone(self.bm, cap_ends=caps, segments=seg, radius1=r1, radius2=r2, depth=h); vs = r['verts']
        self.xform(vs, Matrix.Translation(loc) @ rot(rx, ry, rz) @ Matrix.Rotation(-math.pi / 2, 4, 'X'))   # eixo do cone vira o y do jogo
        return self.fin(vs, m, uvs)
    def sphere(self, r, loc, m, seg=14, rings=8, sc=(1, 1, 1), uvs=2.0):
        res = bmesh.ops.create_uvsphere(self.bm, u_segments=seg, v_segments=rings, radius=r); vs = res['verts']
        self.xform(vs, Matrix.Translation(loc) @ Matrix.Diagonal((*sc, 1)))
        return self.fin(vs, m, uvs)
    def torus(self, R, r, loc, m, rx=0, ry=0, rz=0, seg=32, tseg=6):
        vs = []
        for i in range(seg):
            a = 2 * math.pi * i / seg
            for j in range(tseg):
                b = 2 * math.pi * j / tseg
                vs.append(self.bm.verts.new(((R + r * math.cos(b)) * math.cos(a), r * math.sin(b), (R + r * math.cos(b)) * math.sin(a))))
        for i in range(seg):
            for j in range(tseg):
                a, b2, c, d = i * tseg + j, i * tseg + (j + 1) % tseg, ((i + 1) % seg) * tseg + (j + 1) % tseg, ((i + 1) % seg) * tseg + j
                self.bm.faces.new((vs[a], vs[b2], vs[c], vs[d]))
        self.xform(vs, Matrix.Translation(loc) @ rot(rx, ry, rz))
        return self.fin(vs, m)
    def poly(self, pts, m, uv=None):
        vs = [self.bm.verts.new(p) for p in pts]
        f = self.bm.faces.new(vs); f.material_index = self.mi(m)
        if uv:
            for l, q in zip(f.loops, uv): l[self.uv].uv = q
        else: self.fin(vs, m)
        return f
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
    for name in ('COL_Letarion',):
        c = bpy.data.collections.get(name)
        if c:
            for o in list(c.objects): bpy.data.objects.remove(o, do_unlink=True)
            bpy.data.collections.remove(c)
    c = bpy.data.collections.new('COL_Letarion'); bpy.context.scene.collection.children.link(c); return c

# ---------------------------------------------------------------- utilidades de layout
def lerp(a, b, t): return a + (b - a) * t
def seg_walls(S, x1, z1, x2, z2, y0, h, m, th=0.6, windows=(), lintel=None):
    """parede reta entre (x1,z1)-(x2,z2); janelas = lista de t (0..1) ao longo da parede"""
    L = math.hypot(x2 - x1, z2 - z1); a = math.atan2(z2 - z1, x2 - x1)
    cx, cz = (x1 + x2) / 2, (z1 + z2) / 2
    S.box((L + th, h, th), (cx, y0 + h / 2, cz), m, ry=-a)
    for t in windows:
        wx, wz = lerp(x1, x2, t), lerp(z1, z2, t)
        nx, nz = -math.sin(a), math.cos(a)
        for s in (-1, 1):
            S.box((1.3, 2.0, 0.08), (wx + nx * s * (th / 2 + 0.03), y0 + h * 0.55, wz + nz * s * (th / 2 + 0.03)), M['janela'], ry=-a)
            for dy in (-1.05, 1.05): S.box((1.6, 0.18, 0.2), (wx + nx * s * (th / 2 + 0.06), y0 + h * 0.55 + dy, wz + nz * s * (th / 2 + 0.06)), M['viga'], ry=-a)
            for dx in (-0.72, 0.72): S.box((0.16, 2.2, 0.18), (wx + nx * s * (th / 2 + 0.06) + math.cos(a) * dx, y0 + h * 0.55, wz + nz * s * (th / 2 + 0.06) + math.sin(a) * dx), M['viga'], ry=-a)
            S.box((0.08, 2.0, 0.12), (wx + nx * s * (th / 2 + 0.07), y0 + h * 0.55, wz + nz * s * (th / 2 + 0.07)), M['viga'], ry=-a)
def rect_walls(S, rect, doors, y0, h, m, th=0.6, win=(), door_h=3.8, skip=()):
    x0, z0, x1, z1 = rect
    for k, (a, b, c, d) in enumerate([(x0, z0, x1, z0), (x1, z0, x1, z1), (x1, z1, x0, z1), (x0, z1, x0, z0)]):
        if k in skip: continue
        horiz = abs(b - d) < 1e-6
        lo, hi = (min(a, c), max(a, c)) if horiz else (min(b, d), max(b, d))
        cuts = []
        for (p, q, r, s) in doors:
            if horiz and abs(q - b) < 0.05 and abs(s - b) < 0.05: cuts.append((min(p, r), max(p, r)))
            if not horiz and abs(p - a) < 0.05 and abs(r - a) < 0.05: cuts.append((min(q, s), max(q, s)))
        pts = [lo]
        for g0, g1 in sorted(cuts):
            if g0 > lo and g1 < hi: pts += [g0, g1]
        pts.append(hi)
        for i in range(0, len(pts), 2):
            u, v = pts[i], pts[i + 1]
            ws = [t for t in win if (k, ) == (t[0], ) and u + 1 < lo + (hi - lo) * t[1] < v - 1]
            tw = [((lo + (hi - lo) * t[1]) - u) / (v - u) for t in ws]
            if horiz: seg_walls(S, u, b, v, d, y0, h, m, th, tw)
            else: seg_walls(S, a, u, c, v, y0, h, m, th, tw)
        for g0, g1 in sorted(cuts):   # verga sobre as portas e batentes
            if horiz:
                S.box((g1 - g0 + th, h - door_h, th), ((g0 + g1) / 2, y0 + door_h + (h - door_h) / 2, b), m)
                for g in (g0, g1): S.box((0.25, door_h, th + 0.2), (g, y0 + door_h / 2, b), M['viga'])
                S.box((g1 - g0 + 0.5, 0.3, th + 0.2), ((g0 + g1) / 2, y0 + door_h, b), M['viga'])
            else:
                S.box((th, h - door_h, g1 - g0 + th), (a, y0 + door_h + (h - door_h) / 2, (g0 + g1) / 2), m)
                for g in (g0, g1): S.box((th + 0.2, door_h, 0.25), (a, y0 + door_h / 2, g), M['viga'])
                S.box((th + 0.2, 0.3, g1 - g0 + 0.5), (a, y0 + door_h, (g0 + g1) / 2), M['viga'])

# ---------------------------------------------------------------- escadaria
def escadaria(S):
    P = PL['path']
    # comprimento acumulado
    acc = [0]
    for i in range(1, len(P)): acc.append(acc[-1] + math.hypot(P[i][0] - P[i - 1][0], P[i][1] - P[i - 1][1]))
    L = acc[-1]
    def at(s):
        i = max(1, min(len(P) - 1, next((k for k in range(1, len(P)) if acc[k] >= s), len(P) - 1)))
        t = (s - acc[i - 1]) / max(1e-6, acc[i] - acc[i - 1])
        x = lerp(P[i - 1][0], P[i][0], t); z = lerp(P[i - 1][1], P[i][1], t); h = lerp(P[i - 1][2], P[i][2], t)
        tx, tz = P[i][0] - P[i - 1][0], P[i][1] - P[i - 1][1]; n = math.hypot(tx, tz) or 1
        return x, z, h, tx / n, tz / n
    STEP = 0.62; s = 0.0; k = 0
    while s < L - 0.3:
        x, z, h, tx, tz = at(s + STEP / 2)
        x2, z2, h2, *_ = at(min(L, s + STEP))
        a = math.atan2(tz, tx)
        top = max(h, h2) + 0.04
        S.box((STEP + 0.04, 0.7, PW * 2 + 0.3), (x, top - 0.35, z), M['degrau'], ry=-a, uvs=1.6)
        s += STEP; k += 1
    # meio-fio e guarda-corpo do lado de fora; pedras soltas por dentro (pé do barranco)
    post = 0
    s = 0.6
    while s < L - 2:
        x, z, h, tx, tz = at(s)
        nx, nz = -tz, tx
        if math.hypot(x + nx - C[0], z + nz - C[1]) < math.hypot(x - nx - C[0], z - nz - C[1]): nx, nz = -nx, -nz
        ox, oz = x + nx * (PW + 0.05), z + nz * (PW + 0.05)
        a = math.atan2(tz, tx)
        S.box((1.25, 0.55, 0.45), (ox, h + 0.2, oz), M['pedra'], ry=-a, uvs=1.5)
        if post % 3 == 0:
            S.cyl(0.11, 0.13, 1.6, (ox, h + 0.95, oz), M['madeira'], seg=6)
            x2, z2, h2, tx2, tz2 = at(s + 3.6)
            nx2, nz2 = -tz2, tx2
            if math.hypot(x2 + nx2 - C[0], z2 + nz2 - C[1]) < math.hypot(x2 - nx2 - C[0], z2 - nz2 - C[1]): nx2, nz2 = -nx2, -nz2
            px2, pz2 = x2 + nx2 * (PW + 0.05), z2 + nz2 * (PW + 0.05)
            # corda/corrimão entre os postes
            ll = math.hypot(px2 - ox, pz2 - oz); aa = math.atan2(pz2 - oz, px2 - ox)
            dy = h2 - h
            S.box((ll, 0.09, 0.09), ((ox + px2) / 2, h + 1.6 + dy / 2, (oz + pz2) / 2), M['madeira'], ry=-aa, rz=math.atan2(dy, ll))
            S.box((ll, 0.05, 0.05), ((ox + px2) / 2, h + 1.0 + dy / 2, (oz + pz2) / 2), M['corda'], ry=-aa, rz=math.atan2(dy, ll))
        post += 1
        s += 1.2
    return L

# ---------------------------------------------------------------- cascata, bacia, roda d'água e ponte
def cascata(S, W):
    th = PL['th_cascata']; fx, fz = PL['fonte']
    ux, uz = math.cos(th), math.sin(th)
    ex, ez = C[0] + RP * ux, C[1] + RP * uz                # borda do platô
    # canal de pedra da fonte até a borda
    a = math.atan2(ez - fz, ex - fx); L = math.hypot(ex - fx, ez - fz)
    for s in (-1, 1): S.box((L, 0.5, 0.3), ((fx + ex) / 2 - math.sin(a) * 0.55 * s, PH + 0.2, (fz + ez) / 2 + math.cos(a) * 0.55 * s), M['pedra'], ry=-a)
    W.strip([((fx + math.sin(a) * 0.4, PH + 0.25, fz - math.cos(a) * 0.4), (fx - math.sin(a) * 0.4, PH + 0.25, fz + math.cos(a) * 0.4)),
             ((ex + math.sin(a) * 0.4, PH + 0.22, ez - math.cos(a) * 0.4), (ex - math.sin(a) * 0.4, PH + 0.22, ez + math.cos(a) * 0.4))], M['cascata'], vscale=0.25)
    # a queda: segue a encosta para fora até a bacia ao lado da escadaria
    P = PL['path']; best = min(P, key=lambda p: (p[0] - (C[0] + 40 * ux)) ** 2 + (p[1] - (C[1] + 40 * uz)) ** 2)
    hb = best[2]; rb = math.hypot(best[0] - C[0], best[1] - C[1]) - PW - 1.4          # bacia por dentro do caminho
    rows = []; r = RP - 0.2
    while r < rb:
        # a água corre um pouco acima da rocha (a encosta é íngreme e tem ressaltos)
        y = max(max(ground(C[0] + r * ux + sx * uz, C[1] + r * uz - sx * ux) for sx in (-1.2, 0, 1.2)) + 0.6, hb + 0.4)
        wd = 1.5 + (r - RP) * 0.06
        rows.append(((C[0] + r * ux - uz * wd, y, C[1] + r * uz + ux * wd), (C[0] + r * ux + uz * wd, y, C[1] + r * uz - ux * wd)))
        r += 0.5
    W.strip(rows, M['cascata'], vscale=0.18)
    bx, bz = C[0] + rb * ux, C[1] + rb * uz
    # bacia redonda de pedra com água e espuma
    for i in range(14):
        ang = i / 14 * 2 * math.pi
        S.box((1.0, 0.8, 0.5), (bx + math.cos(ang) * 1.9, hb + 0.3, bz + math.sin(ang) * 1.9), M['pedra'], ry=-ang + math.pi / 2, uvs=1.5)
    S.cyl(1.9, 1.9, 0.1, (bx, hb + 0.55, bz), M['agua'], seg=18)
    S.cyl(1.2, 1.2, 0.05, (bx, hb + 0.62, bz), M['espuma'], seg=14)
    # roda d'água: gira em volta do eixo (tangente à encosta), apoiada na beira da bacia
    R = PL['rp']
    wx, wz = bx - ux * 1.1, bz - uz * 1.1          # a água da queda bate nas pás
    Wh = B('GIRA_roda')
    for k in range(12):
        ang = k / 12 * 2 * math.pi
        Wh.box((0.12, 2.2, 0.18), (0, math.sin(ang) * 1.1, math.cos(ang) * 1.1), M['madeira'], rx=ang)
        Wh.box((0.9, 0.12, 0.55), (0, math.sin(ang) * 2.05, math.cos(ang) * 2.05), M['tabuas'], rx=-ang)
    Wh.torus(2.2, 0.08, (0.4, 0, 0), M['madeira'], rz=math.pi / 2, seg=24, tseg=4)
    Wh.torus(2.2, 0.08, (-0.4, 0, 0), M['madeira'], rz=math.pi / 2, seg=24, tseg=4)
    Wh.cyl(0.18, 0.18, 1.6, (0, 0, 0), M['ferro'], seg=8, rz=math.pi / 2)
    ang_t = math.atan2(ux, -uz)   # eixo da roda ao longo da direção radial
    rd = Wh.done(COL, {'gira_eixo': 'x', 'gira_vel': -0.9}, loc=(wx, hb + 2.4, wz), ry=math.atan2(-ux, -uz))
    # suportes da roda
    for s in (-1, 1):
        px, pz = wx - uz * 0.95 * s, wz + ux * 0.95 * s   # dos dois lados do eixo
        S.box((0.3, 2.6, 0.3), (px, hb + 1.2, pz), M['viga'])
    # água sai da bacia, cruza a escadaria por baixo de uma ponte de tábuas e cai de novo até o mar
    cx2, cz2 = best[0], best[1]
    a2 = math.atan2(uz, ux)
    W.strip([((bx + ux * 1.6 - uz * 0.5, hb + 0.3, bz + uz * 1.6 + ux * 0.5), (bx + ux * 1.6 + uz * 0.5, hb + 0.3, bz + uz * 1.6 - ux * 0.5)),
             ((cx2 + ux * (PW + 0.6) - uz * 0.5, hb + 0.15, cz2 + uz * (PW + 0.6) + ux * 0.5), (cx2 + ux * (PW + 0.6) + uz * 0.5, hb + 0.15, cz2 + uz * (PW + 0.6) - ux * 0.5))], M['cascata'], vscale=0.3)
    for k in range(-3, 4):   # ponte de tábuas sobre o canal (no nível do caminho)
        S.box((0.42, 0.12, PW * 2 + 0.6), (cx2 + ux * k * 0.45, hb + 0.2, cz2 + uz * k * 0.45), M['tabuas'], ry=-a2)
    rows = []; r = math.hypot(cx2 - C[0], cz2 - C[1]) + PW + 0.6
    while True:
        gx, gz = C[0] + r * ux, C[1] + r * uz
        y = max(0.05, ground(gx, gz) + 0.3)
        rows.append(((gx - uz * 0.7, y, gz + ux * 0.7), (gx + uz * 0.7, y, gz - ux * 0.7)))
        if y <= 0.06 or r > 70: break
        r += 0.5
    W.strip(rows, M['cascata'], vscale=0.2)
    S.cyl(1.6, 1.6, 0.05, (rows[-1][0][0] + uz * 0.7, 0.08, rows[-1][0][2] - ux * 0.7), M['espuma'], seg=12)
    return (bx, hb, bz)

# ---------------------------------------------------------------- píer e barco
def pier(S, x, z):
    P0 = PL['path'][0]; sx, sz = P0[0], P0[1]
    for k in range(16):
        zz = sz + 0.3 + k * 0.55
        S.box((3.4, 0.14, 0.5), (sx, 0.62, zz), M['tabuas'], uvs=1.2)
    for zz in (sz + 1, sz + 4.5, sz + 8.3):
        for s in (-1.55, 1.55): S.cyl(0.16, 0.18, 3.2, (sx + s, -0.8, zz), M['madeira'], seg=7)
        S.box((3.6, 0.2, 0.25), (sx, 0.4, zz), M['viga'])
    # barco a remo
    bx, bz = sx + 3.6, sz + 7.2
    Bt = B('barco')
    for i, (w, y) in enumerate([(1.2, 0.0), (1.0, -0.25), (0.6, -0.42)]):
        Bt.box((w * 2, 0.25, 4.2 - i * 0.6), (0, y + 0.3, 0), M['tabuas'], uvs=1.5)
    Bt.box((1.9, 0.08, 0.4), (0, 0.55, 0.6), M['madeira']); Bt.box((1.9, 0.08, 0.4), (0, 0.55, -0.9), M['madeira'])
    for s in (-1, 1): Bt.box((0.06, 0.06, 2.6), (s * 0.55, 0.62, 0.2), M['madeira'], rx=0.15, ry=s * 0.4)
    o = Bt.done(COL, loc=(bx, 0.0, bz), ry=math.radians(10))
    S.cyl(0.04, 0.04, 3.6, (sx + 1.6, 0.65, sz + 6.0), M['corda'], rz=math.pi / 2.2)

# ---------------------------------------------------------------- prédios
def predios(S, T):
    R = PL['rooms']; D = PL['doors']; y0 = PH; HW = 6.5
    # pisos
    for k, mt in [('recepcao', 'tabuas'), ('biblioteca', 'tabuas'), ('laboratorio', 'lajes'), ('varanda', 'tabuas')]:
        x0, z0, x1, z1 = R[k]
        S.box((x1 - x0, 0.1, z1 - z0), ((x0 + x1) / 2, y0 + 0.05, (z0 + z1) / 2), M[mt], uvs=3.0)
    dc, dr = PL['dome']['c'], PL['dome']['r']
    S.cyl(dr, dr, 0.1, (dc[0], y0 + 0.05, dc[1]), M['lajes'], seg=40, uvs=3.0)
    # paredes de pedra (térreo), com janelas acesas
    rect_walls(S, R['recepcao'], D, y0, HW, M['pedra'], win=[(2, 0.2), (2, 0.8)], skip=(0,))
    rect_walls(S, R['biblioteca'], D, y0, HW, M['pedra'], win=[(3, 0.3), (3, 0.7), (0, 0.5), (2, 0.5)], skip=(1,))
    rect_walls(S, R['laboratorio'], D, y0, HW, M['pedra'], win=[(0, 0.4), (2, 0.6)], skip=(3,))
    seg_walls(S, 40.0, 42.0, 40.0, 46.6, y0, HW, M['pedra']); seg_walls(S, 56.0, 44.0, 56.0, 46.6, y0, HW, M['pedra'])   # cantos que a recepção não cobre
    # parede da recepção que encosta na cúpula: só os trechos ao lado da porta
    x0, z0, x1, z1 = R['recepcao']
    seg_walls(S, x0, z0, 46.4, z0, y0, HW, M['pedra']); seg_walls(S, 49.6, z0, x1, z0, y0, HW, M['pedra'])
    S.box((3.8, HW - 3.8, 0.6), (48, y0 + 3.8 + (HW - 3.8) / 2, z0), M['pedra'])
    # tambor da cúpula: parede redonda com janelas e a porta ao sul
    n = 40; HD = 8.0
    for i in range(n):
        a0 = 2 * math.pi * i / n; a1 = 2 * math.pi * (i + 1) / n; am = (a0 + a1) / 2
        if math.radians(80) < am < math.radians(100):
            S.box((2 * math.pi * dr / n + 0.05, HD - 3.8, 0.7), (dc[0] + dr * math.cos(am), y0 + 3.8 + (HD - 3.8) / 2, dc[1] + dr * math.sin(am)), M['pedra'], ry=-am + math.pi / 2)
            continue
        S.box((2 * math.pi * dr / n + 0.05, HD, 0.7), (dc[0] + dr * math.cos(am), y0 + HD / 2, dc[1] + dr * math.sin(am)), M['pedra'], ry=-am + math.pi / 2)
        if i % 5 == 2:
            for s in (-1, 1):
                S.box((0.9, 2.2, 0.08), (dc[0] + (dr + s * 0.39) * math.cos(am), y0 + 4.4, dc[1] + (dr + s * 0.39) * math.sin(am)), M['janela'], ry=-am + math.pi / 2)
    S.torus(dr + 0.4, 0.3, (dc[0], y0 + HD, dc[1]), M['pedra_esc'], seg=48, tseg=5)
    # cúpula de cobre com a fresta (e o forro azul por dentro)
    slit = math.radians(-40)   # direção da fresta (nordeste)
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
                if inner: pts = pts[::-1]
                f = B_.poly(pts, m, uv=[(i / segs * 8, j / rings * 3), ((i + 1) / segs * 8, j / rings * 3), ((i + 1) / segs * 8, (j + 1) / rings * 3), (i / segs * 8, (j + 1) / rings * 3)])
    domo(T, dr + 0.35, M['cobre'])
    domo(T, dr + 0.05, M['domo_in'], inner=True)
    # costelas de madeira por dentro do forro e as bordas da fresta
    for i in range(12):
        a = 2 * math.pi * i / 12
        if abs(((a - slit + math.pi) % (2 * math.pi)) - math.pi) < math.radians(12): continue
        for j in range(10):
            p0 = j / 10 * math.pi / 2; p1 = (j + 1) / 10 * math.pi / 2
            r = dr - 0.1; pm = (p0 + p1) / 2
            T.box((0.2, (p1 - p0) * r + 0.05, 0.2), (dc[0] + r * math.cos(pm) * math.cos(a), y0 + HD + r * math.sin(pm), dc[1] + r * math.cos(pm) * math.sin(a)), M['viga'], ry=-a, rz=pm)
    for s in (-1, 1):
        a = slit + s * math.radians(9)
        for j in range(3, 12):
            p0 = j / 12 * math.pi / 2; p1 = (j + 1) / 12 * math.pi / 2; pm = (p0 + p1) / 2; r = dr + 0.2
            T.box((0.35, (p1 - p0) * r + 0.1, 0.5), (dc[0] + r * math.cos(pm) * math.cos(a), y0 + HD + r * math.sin(pm), dc[1] + r * math.cos(pm) * math.sin(a)), M['latao'], ry=-a, rz=pm)
    T.sphere(0.5, (dc[0], y0 + HD + dr + 0.6, dc[1]), M['latao'], seg=10, rings=6)
    T.cyl(0.05, 0.05, 2.5, (dc[0], y0 + HD + dr + 1.8, dc[1]), M['ferro'], seg=5)
    for k in range(4): T.box((1.0 if k % 2 else 0.12, 0.12, 0.12 if k % 2 else 1.0), (dc[0], y0 + HD + dr + 2.8, dc[1]), M['latao'])
    # andar de cima em enxaimel sobre a recepção, a biblioteca e o laboratório, com telhado
    def andar(rect, h=4.5, roof=3.4, eixo='x', win=4):
        x0, z0, x1, z1 = rect; ov = 0.35; yb = y0 + HW
        X0, Z0, X1, Z1 = x0 - ov, z0 - ov, x1 + ov, z1 + ov
        T.box((X1 - X0, 0.3, Z1 - Z0), ((X0 + X1) / 2, yb + 0.15, (Z0 + Z1) / 2), M['viga'])
        T.box((x1 - x0 - 0.7, 0.15, z1 - z0 - 0.7), ((x0 + x1) / 2, yb - 0.08, (z0 + z1) / 2), M['tabuas'], uvs=3.0)  # forro por dentro
        for (a, b, c, d) in [(X0, Z0, X1, Z0), (X1, Z0, X1, Z1), (X1, Z1, X0, Z1), (X0, Z1, X0, Z0)]:
            L = math.hypot(c - a, d - b); ang = math.atan2(d - b, c - a)
            T.box((L, h, 0.4), ((a + c) / 2, yb + 0.3 + h / 2, (b + d) / 2), M['reboco'], ry=-ang, uvs=3.0)
            nx, nz = -math.sin(ang), math.cos(ang)
            k = max(2, int(L / 2.2))
            for i in range(k + 1):   # vigas verticais e diagonais do enxaimel
                t = i / k; px, pz = lerp(a, c, t), lerp(b, d, t)
                T.box((0.22, h, 0.1), (px - nx * 0.22, yb + 0.3 + h / 2, pz - nz * 0.22), M['viga'], ry=-ang)
                if i < k and i % 2 == 0:
                    qx, qz = lerp(a, c, (i + 0.5) / k), lerp(b, d, (i + 0.5) / k)
                    T.box((0.16, math.hypot(L / k, h * 0.8), 0.1), (qx - nx * 0.22, yb + 0.3 + h * 0.45, qz - nz * 0.22), M['viga'], ry=-ang, rz=math.atan2(L / k, h * 0.8) * (1 if i % 4 == 0 else -1))
            for yy in (yb + 0.4, yb + h * 0.55, yb + h + 0.2): T.box((L, 0.2, 0.1), ((a + c) / 2 - nx * 0.22, yy, (b + d) / 2 - nz * 0.22), M['viga'], ry=-ang)
            for i in range(win):
                t = (i + 0.5) / win; px, pz = lerp(a, c, t), lerp(b, d, t)
                T.box((1.0, 1.5, 0.1), (px - nx * 0.25, yb + 0.3 + h * 0.5, pz - nz * 0.25), M['janela'], ry=-ang)
        # telhado de duas águas
        yt = yb + 0.3 + h
        if eixo == 'x':
            Lx = X1 - X0 + 1.2; dz = (Z1 - Z0) / 2 + 0.8; slope = math.atan2(roof, dz)
            for s in (-1, 1):
                T.box((Lx, 0.25, math.hypot(dz, roof)), ((X0 + X1) / 2, yt + roof / 2, (Z0 + Z1) / 2 + s * dz / 2), M['telha'], rx=s * slope, uvs=2.0)
            for xx in (X0, X1):
                T.poly([(xx, yt, Z0), (xx, yt, Z1), (xx, yt + roof, (Z0 + Z1) / 2)], M['reboco'])
                T.poly([(xx, yt + roof, (Z0 + Z1) / 2), (xx, yt, Z1), (xx, yt, Z0)], M['reboco'])
            T.box((Lx, 0.35, 0.35), ((X0 + X1) / 2, yt + roof + 0.05, (Z0 + Z1) / 2), M['viga'])
        else:
            Lz = Z1 - Z0 + 1.2; dx = (X1 - X0) / 2 + 0.8; slope = math.atan2(roof, dx)
            for s in (-1, 1):
                T.box((math.hypot(dx, roof), 0.25, Lz), ((X0 + X1) / 2 + s * dx / 2, yt + roof / 2, (Z0 + Z1) / 2), M['telha'], rz=-s * slope, uvs=2.0)
            for zz in (Z0, Z1):
                T.poly([(X0, yt, zz), (X1, yt, zz), ((X0 + X1) / 2, yt + roof, zz)], M['reboco'])
                T.poly([((X0 + X1) / 2, yt + roof, zz), (X1, yt, zz), (X0, yt, zz)], M['reboco'])
            T.box((0.35, 0.35, Lz), ((X0 + X1) / 2, yt + roof + 0.05, (Z0 + Z1) / 2), M['viga'])
        # chaminé
        T.box((0.9, 2.5, 0.9), (x1 - 1.5, yt + roof * 0.7, z0 + 1.6), M['pedra'])
    andar(R['recepcao'], eixo='x', win=4); andar(R['biblioteca'], eixo='z', win=3, h=4.0); andar(R['laboratorio'], eixo='z', win=3, h=3.8, roof=3.0)
    # torre alta sobre o canto da biblioteca, com janelas acesas e telhado pontudo
    tx0, tz0, tx1, tz1 = 29.4, 42.4, 35.4, 48.4; tb = y0 + HW
    for lvl in range(4):
        yb = tb + lvl * 4.0
        for (a, b, c, d) in [(tx0, tz0, tx1, tz0), (tx1, tz0, tx1, tz1), (tx1, tz1, tx0, tz1), (tx0, tz1, tx0, tz0)]:
            seg_walls(T, a, b, c, d, yb, 4.0, M['pedra'], th=0.55, windows=[0.5] if lvl >= 1 else [])
    yt = tb + 16
    T.box((tx1 - tx0 + 1.0, 0.5, tz1 - tz0 + 1.0), ((tx0 + tx1) / 2, yt + 0.25, (tz0 + tz1) / 2), M['viga'])
    T.cyl(4.6, 0.12, 7.0, ((tx0 + tx1) / 2, yt + 3.9, (tz0 + tz1) / 2), M['telha'], seg=4, ry=math.pi / 4, uvs=2.0)
    T.cyl(0.06, 0.06, 2.0, ((tx0 + tx1) / 2, yt + 8.0, (tz0 + tz1) / 2), M['ferro'], seg=5)
    # varanda: guarda-corpo e escoras descendo pelo penhasco
    x0, z0, x1, z1 = R['varanda']
    for (a, b, c, d) in [(x0, z0, x1, z0), (x1, z0, x1, z1), (x1, z1, x0, z1)]:
        L = math.hypot(c - a, d - b); ang = math.atan2(d - b, c - a)
        S.box((L, 0.18, 0.18), ((a + c) / 2, y0 + 1.6, (b + d) / 2), M['madeira'], ry=-ang)
        for i in range(int(L / 1.2) + 1):
            t = i / max(1, int(L / 1.2)); S.box((0.12, 1.5, 0.12), (lerp(a, c, t), y0 + 0.8, lerp(b, d, t)), M['madeira'])
    for zz in (z0 + 0.5, (z0 + z1) / 2, z1 - 0.5):
        S.box((0.35, 9.0, 0.35), (x1 - 2.2, y0 - 4.2, zz), M['viga'], rz=math.radians(32))
        S.box((x1 - x0 + 0.6, 0.4, 0.4), ((x0 + x1) / 2, y0 - 0.25, zz), M['viga'])
    # mureta em volta do platô (com as aberturas da escadaria e da varanda)
    n = 90
    for i in range(n):
        am = 2 * math.pi * (i + 0.5) / n
        deg = math.degrees(am)
        if 94 < deg < 106 or deg > 340 or deg < 20 or abs(deg - math.degrees(PL['th_cascata'])) < 2.5: continue
        r = RP - 0.3
        S.box((2 * math.pi * r / n + 0.08, 1.1, 0.6), (C[0] + r * math.cos(am), y0 + 0.55, C[1] + r * math.sin(am)), M['pedra'], ry=-am + math.pi / 2, uvs=1.5)
        if i % 6 == 0: S.box((0.8, 1.5, 0.8), (C[0] + r * math.cos(am), y0 + 0.75, C[1] + r * math.sin(am)), M['pedra_esc'])

# ---------------------------------------------------------------- móveis e enfeites
def estante(S, x, z, ry, w=2.4, h=3.3, d=0.7):
    a = math.radians(ry)
    def P(dx, dy, dz): return (x + math.cos(a) * dx + math.sin(a) * dz, PH + dy, z - math.sin(a) * dx + math.cos(a) * dz)
    S.box((w, h, 0.08), P(0, h / 2, -d / 2), M['madeira'], ry=a)
    for s in (-1, 1): S.box((0.1, h, d), P(s * w / 2, h / 2, 0), M['madeira'], ry=a)
    for k in range(5):
        S.box((w, 0.08, d), P(0, 0.1 + k * (h - 0.2) / 4, 0), M['madeira'], ry=a)
        if k < 4: S.box((w - 0.25, (h - 0.2) / 4 - 0.12, d - 0.25), P(0, 0.14 + k * (h - 0.2) / 4 + ((h - 0.2) / 4 - 0.12) / 2, 0.04), M['livros'], ry=a, uvs=w)
def mesa(S, x, z, w, d, h=1.05, ry=0, m='madeira'):
    a = math.radians(ry)
    def P(dx, dy, dz): return (x + math.cos(a) * dx + math.sin(a) * dz, PH + dy, z - math.sin(a) * dx + math.cos(a) * dz)
    S.box((w, 0.12, d), P(0, h, 0), M[m], ry=a)
    for sx in (-1, 1):
        for sz in (-1, 1): S.box((0.12, h, 0.12), P(sx * (w / 2 - 0.15), h / 2, sz * (d / 2 - 0.15)), M['madeira'], ry=a)
def moveis(S, G):
    pc = PL['plataforma']['c']; pr = PL['plataforma']['r']; ph = PL['plataforma']['h']
    # plataforma do telescópio (pedra e madeira) e os degraus da rampa
    S.cyl(pr, pr, ph, (pc[0], PH + ph / 2, pc[1]), M['pedra'], seg=28, uvs=2)
    # base em rampa de pedra: cobre o declive do relevo em volta da plataforma
    S.cyl(pr + 1.75, pr - 0.02, ph + 0.03, (pc[0], PH + ph / 2 - 0.02, pc[1]), M['pedra'], seg=28, uvs=2)
    S.cyl(pr + 0.05, pr + 0.05, 0.12, (pc[0], PH + ph + 0.04, pc[1]), M['tabuas'], seg=28, uvs=3)
    for i in range(24):   # balaústres e corrimão de latão
        a = 2 * math.pi * i / 24
        if math.radians(66) < a < math.radians(114): continue
        S.cyl(0.05, 0.05, 1.1, (pc[0] + (pr - 0.1) * math.cos(a), PH + ph + 0.6, pc[1] + (pr - 0.1) * math.sin(a)), M['latao'], seg=5)
    S.torus(pr - 0.1, 0.05, (pc[0], PH + ph + 1.15, pc[1]), M['latao'], seg=28, tseg=4)
    a0, b0, c0, d0 = PL['rampa']; nst = 7
    for k in range(nst):
        zz = lerp(d0, b0, (k + 0.5) / nst); hh = ph * (k + 1) / nst
        S.box((c0 - a0, hh, (d0 - b0) / nst + 0.02), ((a0 + c0) / 2, PH + hh / 2, zz), M['degrau'], uvs=1.5)
        for sx in (a0 - 0.75, c0 + 0.75):   # muretas dos lados da escada (escondem o declive do relevo)
            S.box((1.5, hh + 0.12, (d0 - b0) / nst + 0.02), (sx, PH + (hh + 0.12) / 2, zz), M['pedra'], uvs=1.5)
    for s in (a0, c0):
        S.box((0.12, 0.08, d0 - b0 + 0.4), (s, PH + ph / 2 + 1.0, (b0 + d0) / 2), M['latao'], rx=math.atan2(ph, d0 - b0))
    for f in PL['moveis']:
        t, x, z, ry = f['t'], f['x'], f['z'], f.get('ry', 0)
        a = math.radians(ry)
        def P(dx, dy, dz): return (x + math.cos(a) * dx + math.sin(a) * dz, PH + dy, z - math.sin(a) * dx + math.cos(a) * dz)
        if t == 'telescopio':
            # base giratória, garfo e o tubo apontado pela fresta (nordeste, 50° acima do horizonte)
            S.cyl(0.9, 1.2, 0.6, (x, PH + ph + 0.3, z), M['ferro'], seg=16)
            for s in (-1, 1): S.box((0.25, 2.6, 0.4), (x + s * 0.7 * math.sin(math.radians(-40)), PH + ph + 1.8, z - s * 0.7 * math.cos(math.radians(-40))), M['latao'], ry=math.radians(40))
            az = math.radians(-40); el = math.radians(50); Ltub = 12.5
            dx, dy, dz = math.cos(el) * math.cos(az), math.sin(el), math.cos(el) * math.sin(az)
            cx, cy, cz = x + dx * 2.5, PH + ph + 3.0 + dy * 2.5, z + dz * 2.5
            # tubo: segmentos de latão e madeira, mais grosso no fim
            for k, (r1, r2, L, m) in enumerate([(0.55, 0.62, 3.0, 'latao'), (0.62, 0.68, 4.0, 'madeira'), (0.68, 0.8, 4.0, 'latao'), (0.8, 0.85, 1.5, 'latao')]):
                off = sum(q[2] for q in [(0, 0, 3.0), (0, 0, 4.0), (0, 0, 4.0)][:k]) - 3.0
                mx, my, mz = cx + dx * (off + L / 2), cy + dy * (off + L / 2), cz + dz * (off + L / 2)
                S.cyl(r1, r2, L, (mx, my, mz), M[m], seg=18, ry=-az + math.pi / 2, rx=math.pi / 2 - el)
            for k in (-2.0, 1.0, 5.0, 8.6): S.torus(0.72 if k > 0 else 0.6, 0.07, (cx + dx * k, cy + dy * k, cz + dz * k), M['latao'], rx=math.pi / 2 - el, ry=-az + math.pi / 2, rz=0, seg=18, tseg=4)
            S.cyl(0.08, 0.08, 1.2, (cx - dx * 3.4, cy - dy * 3.4, cz - dz * 3.4), M['latao'], seg=6, ry=-az + math.pi / 2, rx=math.pi / 2 - el)
            S.cyl(0.25, 0.3, 2.0, (cx + dx * 1.2 + 0.6, cy + dy * 1.2 + 0.5, cz + dz * 1.2), M['latao'], seg=10, ry=-az + math.pi / 2, rx=math.pi / 2 - el)   # luneta buscadora
        elif t == 'orrery':
            # planetas pendurados do teto: giram devagar em volta do sol
            O = B('GIRA_orrery'); hy = 9.5
            O.cyl(0.04, 0.04, 3.0, (0, hy + 1.5, 0), M['latao'], seg=5)
            O.sphere(0.6, (0, hy, 0), M['sol'], seg=16, rings=10)
            for k, (r, s, m, ph2) in enumerate([(1.8, 0.28, 'planeta2', 0.3), (3.0, 0.45, 'planeta1', 2.1), (4.2, 0.6, 'planeta3', 4.0), (5.4, 0.38, 'planeta4', 5.2)]):
                px, pz = r * math.cos(ph2), r * math.sin(ph2)
                O.box((r, 0.04, 0.04), (px / 2, hy - 0.05 * k, pz / 2), M['latao'], ry=-ph2)
                O.cyl(0.02, 0.02, 1.0 + k * 0.4, (px, hy - 0.5 - k * 0.2, pz), M['latao'], seg=4)
                O.sphere(s, (px, hy - 1.0 - k * 0.4, pz), M[m], seg=14, rings=9)
                if k == 2: O.torus(s * 1.7, 0.04, (px, hy - 1.0 - k * 0.4, pz), M['planeta3'], rx=0.4, seg=24, tseg=4)
            O.done(COL, {'gira_eixo': 'y', 'gira_vel': 0.12}, loc=(x, PH, z))
        elif t == 'armilar':
            S.cyl(0.6, 0.8, 0.9, (x, PH + 0.45, z), M['madeira'], seg=10); S.cyl(0.12, 0.12, 1.4, (x, PH + 1.6, z), M['latao'], seg=6)
            A = B('GIRA_armilar'); yy = 3.2
            A.torus(1.4, 0.06, (0, yy, 0), M['latao'], rx=math.pi / 2, seg=32, tseg=5)
            A.torus(1.4, 0.06, (0, yy, 0), M['latao'], rz=math.pi / 2, seg=32, tseg=5)
            A.torus(1.25, 0.05, (0, yy, 0), M['latao'], rx=math.pi / 2, rz=0.4, seg=32, tseg=5)
            A.torus(1.1, 0.05, (0, yy, 0), M['latao'], seg=32, tseg=5)
            A.sphere(0.35, (0, yy, 0), M['oceano'], seg=12, rings=8)
            A.cyl(0.03, 0.03, 3.4, (0, yy, 0), M['latao'], seg=4, rz=0.4)
            A.done(COL, {'gira_eixo': 'y', 'gira_vel': 0.35}, loc=(x, PH, z))
        elif t in ('mesa_mapas', 'mesa_globo', 'mesa_leitura', 'mesa_lente'):
            mesa(S, x, z, 2.6 if t != 'mesa_globo' else 1.6, 1.4 if t != 'mesa_globo' else 1.2, ry=ry)
            if t == 'mesa_mapas':
                S.box((1.4, 0.02, 1.0), P(-0.3, 1.13, 0), M['carta_b'], ry=a, uvs=1.4)
                S.box((0.8, 0.02, 0.6), P(0.7, 1.13, 0.2), M['papel'], ry=a + 0.3)
                S.cyl(0.08, 0.08, 0.6, P(0.9, 1.4, -0.3), M['latao'], seg=6, rz=1.2, ry=a)
            if t == 'mesa_leitura':
                for k in range(3): S.box((0.7, 0.16, 0.5), P(-0.8, 1.2 + k * 0.17, 0.2), M['livros'], ry=a + k * 0.2, uvs=0.8)
                S.box((0.9, 0.03, 0.6), P(0.3, 1.13, 0), M['papel'], ry=a)
            if t == 'mesa_lente':
                S.cyl(0.55, 0.55, 0.6, P(0.2, 1.5, 0), M['latao'], seg=18, rz=math.pi / 2, ry=a)    # lente grande (referência 4)
                S.cyl(0.48, 0.48, 0.62, P(0.2, 1.5, 0), M['vidro'], seg=18, rz=math.pi / 2, ry=a)
                for k in range(3): S.cyl(0.1, 0.12, 0.35 + k * 0.1, P(-0.8 + k * 0.25, 1.3, -0.3), M[['pocao_v', 'pocao_a', 'pocao_r'][k]], seg=8)
        elif t == 'globo' or t == 'globo_pe':
            base = 1.1 if t == 'globo' else 0.0
            if t == 'globo_pe':
                for k in range(3): S.box((0.08, 1.3, 0.08), P(math.cos(k * 2.1) * 0.35, 0.65, math.sin(k * 2.1) * 0.35), M['madeira'], ry=a)
            S.sphere(0.55, (x, PH + base + 1.0 + (0.4 if t == 'globo_pe' else 0), z), M['oceano'], seg=16, rings=10)
            S.torus(0.66, 0.035, (x, PH + base + 1.0 + (0.4 if t == 'globo_pe' else 0), z), M['latao'], rx=math.pi / 2, rz=0.4, seg=28, tseg=4)
            S.cyl(0.25, 0.3, 0.3, (x, PH + base + 0.3 + (0.4 if t == 'globo_pe' else 0), z), M['latao'], seg=10)
        elif t == 'estante':
            estante(S, x, z, ry)
        elif t == 'estante_curva':
            estante(S, x, z, ry, w=2.8, h=3.6)
        elif t == 'carta_estelar':
            S.box((2.0, 2.6, 0.06), P(0, 3.6, 0), M['carta_a' if f.get('seed', 0) % 2 else 'carta_b'], ry=a, uvs=2.6)
            S.box((2.2, 0.12, 0.1), P(0, 4.95, 0.02), M['latao'], ry=a); S.box((2.2, 0.12, 0.1), P(0, 2.25, 0.02), M['latao'], ry=a)
        elif t == 'pergaminhos':
            for k in range(3):
                S.cyl(0.08, 0.08, 0.9, P(k * 0.3 - 0.3, 0.09, k * 0.2), M['papel'], seg=6, rz=math.pi / 2, ry=a + k * 0.7)
            S.box((0.9, 0.02, 0.6), P(0.4, 0.02, -0.4), M['carta_a'], ry=a + 0.5, uvs=0.9)
        elif t == 'tapete':
            mt = {'azul': 't_azul', 'vermelho': 't_vermelho', 'verde': 't_verde'}[f.get('cor', 'vermelho')]
            w, d = f.get('w', 4), f.get('d', 3)
            S.poly([P(-w / 2, 0.12, -d / 2), P(w / 2, 0.12, -d / 2), P(w / 2, 0.12, d / 2), P(-w / 2, 0.12, d / 2)][::-1], M[mt], uv=[(0, 0), (0, 1), (1, 1), (1, 0)])
        elif t == 'luneta':
            for k in range(3): S.box((0.07, 1.8, 0.07), P(math.cos(k * 2.1) * 0.4, 0.85, math.sin(k * 2.1) * 0.4), M['madeira'], ry=a, rx=math.cos(k * 2.1) * 0.2, rz=math.sin(k * 2.1) * 0.2)
            S.cyl(0.14, 0.2, 2.0, P(0, 1.9, 0), M['latao'], seg=10, rx=0.9, ry=a)
        elif t == 'cadeira':
            S.box((0.9, 0.12, 0.9), P(0, 0.85, 0), M['madeira'], ry=a); S.box((0.9, 1.1, 0.12), P(0, 1.45, -0.4), M['couro'], ry=a)
            for sx in (-1, 1):
                for sz in (-1, 1): S.box((0.1, 0.85, 0.1), P(sx * 0.38, 0.42, sz * 0.38), M['madeira'], ry=a)
        elif t == 'balcao':
            # balcão curvo da recepção, de madeira com tampo
            for i in range(9):
                u = (i - 4) / 4; ang = u * 0.7
                px, pz = x + math.sin(ang) * 3.4, z - 2.2 + math.cos(ang) * 3.0
                S.box((0.8, 1.2, 0.6), (px, PH + 0.6, pz), M['madeira'], ry=-ang)
                S.box((0.85, 0.1, 0.8), (px, PH + 1.25, pz), M['viga'], ry=-ang)
        elif t == 'gato':
            # gato sentado (referência 4)
            S.sphere(0.32, (x, PH + 1.62, z), M['gato'], sc=(0.8, 1.1, 1.0), seg=10, rings=8)
            S.sphere(0.22, (x, PH + 2.05, z + 0.08), M['gato'], seg=10, rings=7)
            for s in (-1, 1):
                S.cyl(0.07, 0.0, 0.2, (x + s * 0.12, PH + 2.28, z + 0.08), M['gato'], seg=4)
                S.sphere(0.035, (x + s * 0.08, PH + 2.08, z + 0.27), M['olho'], seg=6, rings=4)
            S.cyl(0.05, 0.04, 0.8, (x - 0.3, PH + 1.45, z - 0.2), M['gato'], seg=5, rz=1.2)
        elif t == 'livro_aberto':
            for s in (-1, 1): S.box((0.42, 0.06, 0.55), P(s * 0.22, 1.32, 0), M['papel'], ry=a, rz=s * 0.08)
            S.box((0.95, 0.04, 0.6), P(0, 1.29, 0), M['couro'], ry=a)
        elif t == 'atril_livro':
            # o grande livro aberto sobre o atril (referência 4)
            S.box((0.5, 1.3, 0.5), P(0, 0.65, 0), M['madeira'], ry=a)
            S.box((1.8, 0.1, 1.3), P(0, 1.4, 0), M['madeira'], ry=a, rx=-0.25)
            for s in (-1, 1):
                S.box((0.85, 0.18, 1.15), P(s * 0.43, 1.55, 0.02), M['papel'], ry=a, rx=-0.25, rz=s * 0.12)
            S.box((1.85, 0.05, 1.25), P(0, 1.47, 0), M['couro'], ry=a, rx=-0.25)
        elif t == 'vaso_planta':
            S.cyl(0.35, 0.45, 0.8, (x, PH + 0.4, z), M['terracota'], seg=10)
            for k in range(7):
                aa = k * 0.9
                S.sphere(0.45, (x + math.cos(aa) * 0.3, PH + 1.2 + (k % 3) * 0.25, z + math.sin(aa) * 0.3), M['folha'], sc=(1, 0.7, 1), seg=8, rings=6)
        elif t == 'poltrona':
            S.box((1.3, 0.55, 1.2), P(0, 0.4, 0), M['couro'], ry=a); S.box((1.3, 1.2, 0.3), P(0, 1.0, -0.5), M['couro'], ry=a)
            for s in (-1, 1): S.box((0.25, 0.8, 1.2), P(s * 0.6, 0.65, 0), M['couro'], ry=a)
        elif t == 'banquinho':
            S.cyl(0.45, 0.45, 0.2, (x, PH + 0.9, z), M['couro'], seg=12)
            for k in range(3): S.cyl(0.05, 0.05, 0.85, (x + math.cos(k * 2.1) * 0.32, PH + 0.42, z + math.sin(k * 2.1) * 0.32), M['madeira'], seg=5)
        elif t == 'mesinha':
            S.cyl(0.6, 0.6, 0.1, (x, PH + 1.0, z), M['madeira'], seg=14); S.cyl(0.1, 0.25, 1.0, (x, PH + 0.5, z), M['madeira'], seg=8)
        elif t == 'ampulheta':
            S.cyl(0.2, 0.02, 0.3, (x, PH + 1.4, z), M['vidro'], seg=10); S.cyl(0.02, 0.2, 0.3, (x, PH + 1.7, z), M['vidro'], seg=10)
            for yy in (1.22, 1.88): S.cyl(0.25, 0.25, 0.05, (x, PH + yy, z), M['latao'], seg=10)
        elif t == 'cabideiro':
            S.cyl(0.06, 0.06, 3.0, (x, PH + 1.5, z), M['madeira'], seg=6)
            S.box((0.8, 1.6, 0.3), (x + 0.2, PH + 2.1, z), M['tecido_azul'])
        elif t == 'quadro_lua':
            S.box((2.4, 1.4, 0.06), (x, PH + 3.6, z + 0.33), M['quadro'], uvs=2.4)
        elif t == 'escada_mao':
            for s in (-1, 1): S.box((0.08, 3.6, 0.08), P(s * 0.35, 1.8, 0), M['madeira'], ry=a, rx=0.15)
            for k in range(8): S.box((0.7, 0.06, 0.06), P(0, 0.3 + k * 0.42, 0.04 * k), M['madeira'], ry=a)
        elif t == 'pilha_livros':
            for k in range(5): S.box((0.7 - k * 0.04, 0.16, 0.5), P(0, 0.08 + k * 0.17, 0), M['livros'], ry=a + k * 0.25, uvs=0.8)
        elif t == 'bancada':
            mesa(S, x, z, 6.2, 1.2, h=1.1, ry=ry)
            S.box((6.2, 2.0, 0.1), P(0, 2.5, -0.55), M['madeira'], ry=a)
            for k in range(14):
                mm = ['pocao_v', 'pocao_a', 'pocao_r', 'vidro'][k % 4]
                S.cyl(0.12, 0.16, 0.35 + (k % 3) * 0.1, P(-2.8 + k * 0.42, 1.35 + (k % 3) * 0.05, -0.2 + (k % 2) * 0.25), M[mm], seg=8)
            for k in range(6): S.cyl(0.1, 0.12, 0.4, P(-2.6 + k * 1.0, 2.75, -0.35), M[['pocao_a', 'vidro', 'pocao_v'][k % 3]], seg=8)
            S.box((6.2, 0.08, 0.4), P(0, 2.5, -0.35), M['madeira'], ry=a)
        elif t == 'caldeirao':
            S.sphere(0.85, (x, PH + 0.95, z), M['ferro'], sc=(1, 0.8, 1), seg=14, rings=8)
            S.cyl(0.7, 0.7, 0.05, (x, PH + 1.45, z), M['pocao_v'], seg=14)
            for k in range(3): S.box((0.1, 0.7, 0.1), (x + math.cos(k * 2.1) * 0.65, PH + 0.3, z + math.sin(k * 2.1) * 0.65), M['ferro'])
        elif t == 'prateleira_frascos':
            for k in range(3):
                S.box((2.6, 0.08, 0.55), P(0, 1.2 + k * 0.9, 0), M['madeira'], ry=a)
                for j in range(6): S.cyl(0.1, 0.13, 0.3 + (j % 2) * 0.15, P(-1.1 + j * 0.44, 1.4 + k * 0.9, 0), M[['pocao_v', 'pocao_a', 'pocao_r', 'vidro'][(j + k) % 4]], seg=7)
        elif t == 'caixotes':
            S.box((1.1, 1.0, 1.1), P(0, 0.5, 0), M['tabuas'], ry=a, uvs=1.1); S.box((0.9, 0.8, 0.9), P(0.2, 1.4, 0.1), M['tabuas'], ry=a + 0.4, uvs=1.0)
        elif t == 'banco':
            S.box((2.4, 0.15, 0.7), P(0, 0.75, 0), M['madeira'], ry=a)
            for s in (-1, 1): S.box((0.15, 0.75, 0.6), P(s * 1.0, 0.37, 0), M['pedra_esc'], ry=a)
        elif t == 'arco':
            # arco de pedra no alto da escadaria
            for s in (-1, 1): S.box((0.9, 5.0, 0.9), P(s * 2.4, 2.5, 0), M['pedra'], ry=a)
            for k in range(9):
                u = k / 8 * math.pi
                S.box((0.8, 0.9, 0.9), P(-math.cos(u) * 2.4, 5.0 + math.sin(u) * 1.4, 0), M['pedra'], ry=a, rz=u - math.pi / 2)
            S.box((0.6, 0.6, 0.6), P(0, 6.7, 0), M['latao'], ry=a)
        elif t == 'estatua':
            # um sábio olhando as estrelas, com um astrolábio na mão
            S.box((1.6, 1.0, 1.6), P(0, 0.5, 0), M['pedra'], ry=a)
            S.cyl(0.55, 0.75, 2.4, P(0, 2.2, 0), M['estatua'], seg=10)
            S.sphere(0.35, P(0, 3.7, 0.05), M['estatua'], seg=10, rings=7)
            S.cyl(0.15, 0.12, 1.4, P(0.45, 3.4, 0.2), M['estatua'], seg=6, rz=-0.9, ry=a)
            S.torus(0.35, 0.05, P(0.9, 4.1, 0.3), M['latao'], rx=0.3, seg=18, tseg=4)
        elif t == 'canteiro':
            S.box((1.8, 0.6, 1.8), P(0, 0.3, 0), M['pedra'], ry=a)
            for k in range(9): S.sphere(0.35, P((k % 3 - 1) * 0.5, 0.75, (k // 3 - 1) * 0.5), M['folha'], seg=7, rings=5, sc=(1, 0.8, 1))
        elif t == 'fonte':
            S.cyl(1.4, 1.5, 0.8, (x, PH + 0.4, z), M['pedra'], seg=18)
            S.cyl(1.25, 1.25, 0.05, (x, PH + 0.75, z), M['agua'], seg=18)
            S.cyl(0.25, 0.35, 1.6, (x, PH + 1.4, z), M['pedra'], seg=10)
            S.cyl(0.6, 0.4, 0.3, (x, PH + 2.2, z), M['pedra'], seg=12)
        elif t == 'relogio_sol':
            S.cyl(0.5, 0.6, 1.0, (x, PH + 0.5, z), M['pedra'], seg=12); S.cyl(0.7, 0.7, 0.08, (x, PH + 1.05, z), M['latao'], seg=18)
            S.box((0.05, 0.5, 0.6), (x, PH + 1.3, z), M['latao'], rx=0.6)
        elif t == 'pier':
            pier(S, x, z)
        elif t == 'barris':
            for k in range(3): S.cyl(0.42, 0.42, 1.0, (x + (k % 2) * 0.9, 0.6 + (k // 2) * 1.0 + ground(x, z) - 0.1, z + (k % 2) * 0.3), M['madeira'], seg=10)
        elif t == 'barco': pass

def main():
    global COL
    for o in list(bpy.data.objects):
        if o.name.startswith(('letarion', 'TELHADO', 'GIRA_', 'CASCATA', 'barco')): bpy.data.objects.remove(o, do_unlink=True)
    COL = collection()
    S = B('letarion_estatico'); T = B('TELHADO_predios'); W = B('CASCATA')
    L = escadaria(S); print('escadaria: %.0f unidades' % L)
    cascata(S, W)
    predios(S, T)
    moveis(S, None)
    info = {}
    for b_, ex in [(S, None), (T, {'telhado': 1}), (W, None)]:
        o = b_.done(COL, ex); info[o.name] = b_.tris
    print('triângulos:', info)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    bpy.ops.object.select_all(action='DESELECT')
    for o in COL.objects: o.select_set(True)
    bpy.ops.export_scene.gltf(filepath=OUT, export_format='GLB', use_selection=True, export_extras=True, export_materials='EXPORT',
                              export_image_format='NONE', export_apply=True, export_yup=True)
    print('GLB: %.1f MB' % (os.path.getsize(OUT) / 1e6))
    try: bpy.ops.wm.save_as_mainfile(filepath=BLEND)
    except Exception as e: print('blend não salvo:', e)
    return dict(tris=info, glb=OUT)

if __name__ == '__main__':
    print(main())
