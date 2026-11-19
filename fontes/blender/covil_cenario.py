"""Modela as ruínas do laboratório e o covil do dragão negro a partir da planta (fontes/mapas/covil_plano.json).

Gera public/assets/maps/covil/covil.glb com:
  - paredes arruinadas (ameias quebradas, desmoronamentos), painéis de ossuário com crânios, canos;
  - altar em degraus na sala mais funda, portão desabado, colunas (de pé e caídas), entulho;
  - tanques de vidro (inteiros com líquido brilhante, quebrados, tombados), mesas, estantes com livros, gaiolas, frascos;
  - cabeça colossal tombada; esqueletos humanos, esqueletos de criaturas grandes, ossos soltos;
  - o tesouro do dragão (monte de ouro, baús, taças, gemas), cogumelos que brilham, agulhas de pedra e matacões.
As texturas não vão dentro do GLB: cada material leva em "extras" qual textura da pasta tex/ usar
e a escala, e o jogo monta o material (as mesmas texturas servem ao chão).
Coordenadas: o jogo usa x, altura, z; no Blender isso é (x, -z, altura).

Rodar (depois de fontes/mapas/covil_gerar.py): python3 fontes/blender/covil_cenario.py
"""
import base64, json, math, os, sys
import numpy as np
import bpy

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
PLAN = json.load(open(os.path.join(ROOT, 'fontes', 'mapas', 'covil_plano.json')))
OUT = os.path.join(ROOT, 'public', 'assets', 'maps', 'covil', 'covil.glb')
rng = np.random.default_rng(77)

# ---------------------------------------------------------------- relevo (para apoiar objetos no chão)
RV = PLAN['relevo']
HGRID = np.frombuffer(base64.b64decode(RV['b64']), dtype='<i2').reshape(RV['n'], RV['n']).astype(float) / 100
def ground(x, z):
    fx, fz = (x - RV['x0']) / RV['res'], (z - RV['x0']) / RV['res']
    i, j = int(np.clip(math.floor(fx), 0, RV['n'] - 2)), int(np.clip(math.floor(fz), 0, RV['n'] - 2))
    tx, tz = fx - i, fz - j
    a, b, c, d = HGRID[j, i], HGRID[j, i + 1], HGRID[j + 1, i], HGRID[j + 1, i + 1]
    return float(a * (1 - tx) * (1 - tz) + b * tx * (1 - tz) + c * (1 - tx) * tz + d * tx * tz)

# ---------------------------------------------------------------- geometria simples em numpy (x, y=altura, z) no espaço do jogo
def T(V, s=(1, 1, 1), ry=0.0, rx=0.0, rz=0.0, t=(0, 0, 0)):
    V = np.asarray(V, float) * np.asarray(s, float)
    if rz:
        c, n = math.cos(rz), math.sin(rz); V = V @ np.array([[c, n, 0], [-n, c, 0], [0, 0, 1]])
    if rx:
        c, n = math.cos(rx), math.sin(rx); V = V @ np.array([[1, 0, 0], [0, c, n], [0, -n, c]])
    if ry:  # mesma convenção do three.js: rotation.y
        c, n = math.cos(ry), math.sin(ry); V = V @ np.array([[c, 0, -n], [0, 1, 0], [n, 0, c]])
    return V + np.asarray(t, float)

def box(sx, sy, sz, y0=0.0):
    x, y, z = sx / 2, sy, sz / 2
    V = np.array([[-x, y0, -z], [x, y0, -z], [x, y0, z], [-x, y0, z], [-x, y0 + y, -z], [x, y0 + y, -z], [x, y0 + y, z], [-x, y0 + y, z]])
    F = [[0, 1, 2, 3][::-1], [4, 5, 6, 7], [0, 1, 5, 4], [1, 2, 6, 5], [2, 3, 7, 6], [3, 0, 4, 7]]
    return V, F

def cyl(r, h, n=12, r2=None, cap=True, y0=0.0, open_top=False):
    r2 = r if r2 is None else r2
    a = np.linspace(0, 2 * math.pi, n, endpoint=False)
    V = np.concatenate([np.stack([np.cos(a) * r, np.full(n, y0), np.sin(a) * r], 1), np.stack([np.cos(a) * r2, np.full(n, y0 + h), np.sin(a) * r2], 1)])
    F = [[k, (k + 1) % n, n + (k + 1) % n, n + k][::-1] for k in range(n)]
    if cap:
        F.append(list(range(n)))
        if not open_top: F.append(list(range(2 * n - 1, n - 1, -1)))
    return V, F

def sphere(r, nu=10, nv=7, sy=1.0, y0=0.0, top_only=False):
    V = [[0, y0 + r * sy, 0]]; F = []
    rows = nv if not top_only else nv // 2 + 1
    for i in range(1, rows):
        ph = math.pi * i / nv
        for k in range(nu):
            th = 2 * math.pi * k / nu
            V.append([math.sin(ph) * math.cos(th) * r, y0 + math.cos(ph) * r * sy, math.sin(ph) * math.sin(th) * r])
    for k in range(nu): F.append([0, 1 + (k + 1) % nu, 1 + k])
    for i in range(rows - 2):
        for k in range(nu):
            a, b = 1 + i * nu + k, 1 + i * nu + (k + 1) % nu
            F.append([a, b, b + nu, a + nu])
    if not top_only:
        V.append([0, y0 - r * sy, 0]); last = len(V) - 1; base = 1 + (rows - 2) * nu
        for k in range(nu): F.append([base + k, base + (k + 1) % nu, last])
    else:
        base = 1 + (rows - 2) * nu; F.append([base + k for k in range(nu)][::-1])
    return np.array(V, float), F

def rock(r, seed, sy=0.7, n=10, rough=0.35):
    V, F = sphere(r, n, max(5, n * 2 // 3), sy)
    g = np.random.default_rng(seed)
    d = 1 + rough * (g.random(len(V)) - 0.5) * 2
    V = V * d[:, None]; V[:, 1] = np.maximum(V[:, 1], -r * sy * 0.3)
    return V, F

def tube(points, r, n=6):
    """tubo pelos pontos (ossos curvos, costelas, canos)."""
    P = np.asarray(points, float); V, F = [], []
    for i, p in enumerate(P):
        tng = P[min(i + 1, len(P) - 1)] - P[max(i - 1, 0)]; tng /= (np.linalg.norm(tng) + 1e-9)
        up = np.array([0, 1, 0]) if abs(tng[1]) < 0.9 else np.array([1, 0, 0])
        a = np.cross(tng, up); a /= np.linalg.norm(a); b = np.cross(tng, a)
        rr = r[i] if hasattr(r, '__len__') else r
        for k in range(n):
            th = 2 * math.pi * k / n; V.append(p + (a * math.cos(th) + b * math.sin(th)) * rr)
    for i in range(len(P) - 1):
        for k in range(n):
            F.append([i * n + k, i * n + (k + 1) % n, (i + 1) * n + (k + 1) % n, (i + 1) * n + k])
    F.append(list(range(n))[::-1]); F.append([(len(P) - 1) * n + k for k in range(n)])
    return np.array(V), F

# ---------------------------------------------------------------- grupos (um objeto por material)
class Grp:
    def __init__(self, mat, uv=3.0):
        self.mat, self.uv = mat, uv; self.V = []; self.F = []; self.UV = []; self.n = 0
    def add(self, V, F, uv=None):
        V = np.asarray(V, float)
        self.V.append(V); self.F += [[i + self.n for i in f] for f in F]
        self.UV += uv if uv is not None else [None] * len(F)
        self.n += len(V)
        return self

MATS = {}
def material(name, **extras):
    if name in MATS: return MATS[name]
    m = bpy.data.materials.new(name); m.use_nodes = True
    bsdf = m.node_tree.nodes['Principled BSDF']
    c = extras.pop('color', '#ffffff').lstrip('#'); col = [int(c[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    bsdf.inputs['Base Color'].default_value = (*[v ** 2.2 for v in col], 1)
    bsdf.inputs['Roughness'].default_value = 0.85
    for k, v in extras.items(): m[k] = v
    MATS[name] = m; return m

def to_blender(V):
    V = np.asarray(V, float); return np.stack([V[:, 0], -V[:, 2], V[:, 1]], 1)

def make_mesh(name, grp):
    if not grp.V: return None
    V = np.concatenate(grp.V)
    me = bpy.data.meshes.new(name)
    me.from_pydata(to_blender(V).tolist(), [], grp.F)
    me.update()
    uvl = me.uv_layers.new(name='UVMap')
    s = grp.uv
    for poly, fuv in zip(me.polygons, grp.UV):
        if fuv is not None:
            for li, (u, v) in zip(poly.loop_indices, fuv): uvl.data[li].uv = (u, v)
            continue
        nx, ny, nz = poly.normal            # (blender) projeção pela direção da face, em unidades do mundo
        ax = max(range(3), key=lambda i: abs(poly.normal[i]))
        for li in poly.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            if ax == 2: u, v = co.x / s, co.y / s
            elif ax == 0: u, v = co.y / s, co.z / s
            else: u, v = co.x / s, co.z / s
            uvl.data[li].uv = (u, v)
    me.materials.append(grp.mat)
    return me

ROOT_OBJ = None
def link(name, me, loc=(0, 0, 0), ry=0.0, s=1.0, parent=None):
    o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o)
    x, y, z = loc
    o.location = (x, -z, y); o.rotation_euler = (0, 0, ry); o.scale = (s, s, s)
    o.parent = parent or ROOT_OBJ
    return o

def group_parent(name):
    e = bpy.data.objects.new(name, None); bpy.context.scene.collection.objects.link(e); e.parent = ROOT_OBJ; return e

# ---------------------------------------------------------------- materiais
def mats():
    return dict(
        tijolo=material('covil_tijolo', tex='tijolo', normal='tijolo_n', ramp='soft', rim=0.15),
        pedra=material('covil_pedra', tex='piso', normal='piso_n', ramp='soft', rim=0.15),
        ossuario=material('covil_ossuario', tex='ossuario', normal='ossuario_n', ramp='soft', rim=0.2),
        rocha=material('covil_rocha', tex='rocha', normal='rocha_n', ramp='soft', rim=0.12),
        madeira=material('covil_madeira', tex='madeira', ramp='soft'),
        metal=material('covil_metal', tex='metal', ramp='soft', rim=0.35),
        vidro=material('covil_vidro', glass=True, color='#a8e6cf', opacity=0.32),
        liquido=material('covil_liquido', glow=True, color='#79ff5c'),
        osso=material('covil_osso', color='#d9ccad', ramp='soft', rim=0.2),
        ouro=material('covil_ouro', tex='ouro', ramp='soft', rim=0.6, color='#ffffff'),
        gema=material('covil_gema', glow=True, color='#ff3a6e'),
        livros=material('covil_livros', color='#7a3b2c', ramp='soft'),
        vela=material('covil_vela', glow=True, color='#ffd27a'),
        cog_haste=material('covil_cogumelo_haste', color='#cfc6a8', ramp='soft'),
        cog0=material('covil_cogumelo_ciano', glow=True, color='#5ef2ff'),
        cog1=material('covil_cogumelo_verde', glow=True, color='#8dff8a'),
        cog2=material('covil_cogumelo_magenta', glow=True, color='#ff5ad8'),
        cog3=material('covil_cogumelo_azul', glow=True, color='#5a8cff'),
    )

# ---------------------------------------------------------------- paredes do laboratório
def walls(M, G):
    gw, gm = G['tijolo'], G['tijolo']
    for w in PLAN['walls']:
        (x1, z1), (x2, z2) = w['a'], w['b']
        L = math.hypot(x2 - x1, z2 - z1); ang = -math.atan2(z2 - z1, x2 - x1)
        g = np.random.default_rng(w['seed'])
        base, top = w['base'], w['top']
        # corpo em blocos de ~1,3 com topo erodido; de vez em quando um desmoronamento fundo
        n = max(1, int(round(L / 1.3))); seg = L / n
        collapse = g.random() < 0.45; cpos = g.uniform(0.2, 0.8); cw = g.uniform(0.12, 0.22)
        for k in range(n):
            t0 = k * seg; tc = (k + 0.5) / n
            hk = top - (g.random() ** 3) * 1.2
            if collapse and abs(tc - cpos) < cw: hk = top - g.uniform(1.6, 2.6)
            th = 1.0 + (0.06 if k % 2 else 0)
            V, F = box(seg + 0.02, hk - base, th, base)
            V = T(V, t=(t0 + seg / 2, 0, 0)); V = T(V, ry=ang, t=(x1, 0, z1)); gw.add(V, F)
            # ameias nos trechos inteiros
            if hk > top - 0.15 and k % 2 == 0 and g.random() < 0.85:
                V, F = box(0.75, 0.7, 1.12, hk)
                V = T(V, t=(t0 + seg / 2, 0, 0)); V = T(V, ry=ang, t=(x1, 0, z1)); gm.add(V, F)
            # cornija (faixa saliente) a 3,4
            if hk > 3.5:
                V, F = box(seg + 0.02, 0.22, th + 0.3, 3.3)
                V = T(V, t=(t0 + seg / 2, 0, 0)); V = T(V, ry=ang, t=(x1, 0, z1)); gw.add(V, F)
        # pilar nas pontas
        for (px, pz) in ((x1, z1), (x2, z2)):
            V, F = box(1.5, top + 0.5 - base, 1.5, base); gw.add(T(V, ry=ang, t=(px, 0, pz)), F)
            V, F = box(1.75, 0.35, 1.75, top + 0.5); gw.add(T(V, ry=ang, t=(px, 0, pz)), F)

def panels(M, G):
    """nichos de ossuário: placa saliente com o painel de crânios na face (dos dois lados da parede)."""
    for x, z, a in PLAN['panels']:
        ry = -a
        for side in (1, -1):
            V, F = box(1.5, 2.25, 0.16, 1.15)
            V = T(V, t=(0, 0, side * 0.58)); V = T(V, ry=ry, t=(x, 0, z))
            uv = [None] * 6
            # face da frente recebe o painel inteiro (0..1)
            front = 4 if side == 1 else 2   # índices de face do box: 2 = -z, 4 = +z
            uv[front] = [(0, 0), (1, 0), (1, 1), (0, 1)] if side == 1 else [(0, 0), (1, 0), (1, 1), (0, 1)]
            G['ossuario'].add(V, F, uv)
            # moldura de pedra em volta
            for (fx, fy, fw, fh) in ((0, 3.45, 1.8, 0.2), (0, 0.98, 1.8, 0.2), (-0.83, 1.15, 0.16, 2.3), (0.83, 1.15, 0.16, 2.3)):
                V, F = box(fw, fh, 0.24, fy); V = T(V, t=(fx, 0, side * 0.58)); G['pedra'].add(T(V, ry=ry, t=(x, 0, z)), F)

def pipes(M, G):
    for p in PLAN['pipes']:
        (x1, z1), (x2, z2) = p['a'], p['b']
        L = math.hypot(x2 - x1, z2 - z1); dx, dz = (x2 - x1) / L, (z2 - z1) / L; nx, nz = -dz, dx
        g = np.random.default_rng(p['seed']); side = 1 if g.random() < 0.5 else -1
        y = p['y']; off = p['off'] * side
        pts = [(x1 + dx * t + nx * off, y + (0.0 if t < L * 0.6 else -0.25 * (g.random() < 0.3)), z1 + dz * t + nz * off) for t in np.linspace(1.2, L - 1.2, 8)]
        V, F = tube(pts, 0.13, 8); G['metal'].add(V, F)
        for t in np.linspace(1.5, L - 1.5, max(2, int(L / 3))):
            V, F = box(0.4, 0.4, 0.5, y - 0.2); G['metal'].add(T(V, ry=-math.atan2(dz, dx), t=(x1 + dx * t + nx * off * 0.8, 0, z1 + dz * t + nz * off * 0.8)), F)
        # válvula
        t = L * g.uniform(0.3, 0.7); cx, cz = x1 + dx * t + nx * off, z1 + dz * t + nz * off
        V, F = cyl(0.3, 0.08, 10); G['metal'].add(T(V, rx=math.pi / 2, ry=-math.atan2(dz, dx) + math.pi / 2, t=(cx + nx * 0.2 * side, y, cz + nz * 0.2 * side)), F)

def altar(M, G):
    a = PLAN['altar']; x0, z0, x1, z1 = a['x0'], a['z0'], a['x1'], a['z1']
    cx, cz, w, d = (x0 + x1) / 2, (z0 + z1) / 2, x1 - x0, z1 - z0
    # degraus
    for k, (inset, top) in enumerate(((0.0, a['top'] - 0.6), (0.6, a['top'] - 0.3), (1.2, a['top']))):
        V, F = box(w - inset * 2, top - a['base'], d - inset * 2, a['base']); G['pedra'].add(T(V, t=(cx, 0, cz)), F)
    # painéis de crânios nos lados do degrau de baixo (acima da água)
    for side in (-1, 1):
        for k in range(int(w / 2.2)):
            px = x0 + 1.1 + k * 2.2
            V, F = box(1.6, 0.0001 + 0.6, 0.05, a['top'] - 0.6 - 0.62)
            uv = [None] * 6; uv[4 if side > 0 else 2] = [(0, 0.3), (1, 0.3), (1, 0.7), (0, 0.7)]
            G['ossuario'].add(T(V, t=(px, 0, cz + side * (d / 2 + 0.03))), F, uv)
    # sarcófago/mesa de pedra em cima, com velas e crânios
    V, F = box(3.2, 1.0, 1.6, a['top']); G['pedra'].add(T(V, t=(cx, 0, cz)), F)
    V, F = box(3.5, 0.18, 1.9, a['top'] + 1.0); G['pedra'].add(T(V, t=(cx, 0, cz)), F)
    for k in range(9):
        px, pz = cx + rng.uniform(-1.6, 1.6), cz + rng.choice([-1, 1]) * rng.uniform(1.2, 1.8)
        h = rng.uniform(0.2, 0.55)
        V, F = cyl(0.07, h, 6); G['osso'].add(T(V, t=(px, a['top'], pz)), F)
        V, F = sphere(0.06, 5, 4, 1.6); G['vela'].add(T(V, t=(px, a['top'] + h + 0.06, pz)), F)
    for k in range(6):
        add_skull(G, (cx + rng.uniform(-1.4, 1.4), a['top'] + 1.18, cz + rng.uniform(-0.6, 0.6)), rng.uniform(0, 6.28), 0.16)

def gate(M, G):
    a = PLAN['gate']; (x1, z1), (x2, z2) = a['a'], a['b']
    L = math.hypot(x2 - x1, z2 - z1); ang = -math.atan2(z2 - z1, x2 - x1); cx, cz = (x1 + x2) / 2, (z1 + z2) / 2
    for s in (-1, 1):
        V, F = box(1.6, 6.5 - a['base'], 1.6, a['base']); G['tijolo'].add(T(T(V, t=(s * (L / 2 - 0.4), 0, 0)), ry=ang, t=(cx, 0, cz)), F)
    # arco quebrado: meia volta em blocos, faltando um pedaço
    for k in range(9):
        th = math.pi * (k + 0.5) / 9
        if 3 <= k <= 4: continue
        px, py = math.cos(th) * (L / 2 - 0.6), 3.6 + math.sin(th) * (L / 2 - 0.6) * 0.85
        V, F = box(1.0, 0.8, 1.3, -0.4); V = T(V, rz=th - math.pi / 2, t=(px, py, 0)); G['tijolo'].add(T(V, ry=ang, t=(cx, 0, cz)), F)

# ---------------------------------------------------------------- equipamento do laboratório
def vats(M, G):
    for v in PLAN['vats']:
        x, z, y, ry = v['x'], v['z'], v['y'], v['ry']
        parts = []
        if v['state'] == 'tombado':
            base = (x, y + 0.85, z); rx = math.pi / 2
        else:
            base = (x, y, z); rx = 0
        def put(grp, V, F):
            V = T(V, rx=rx); G[grp].add(T(V, ry=ry, t=base), F)
        V, F = cyl(0.95, 0.35, 14); put('metal', V, F)                      # base
        V, F = cyl(1.0, 0.18, 14, y0=0.35); put('metal', V, F)
        hgl = 2.7 if v['state'] == 'inteiro' else rng.uniform(0.9, 1.7)
        V, F = cyl(0.82, hgl, 14, y0=0.5, cap=False); put('vidro', V, F)
        if v['state'] != 'inteiro':
            # cacos: pontas de vidro irregulares no topo quebrado
            for k in range(7):
                th = 2 * math.pi * k / 7 + rng.uniform(-0.2, 0.2); hh = rng.uniform(0.3, 0.9)
                Vt = np.array([[math.cos(th - 0.25) * 0.82, 0.5 + hgl, math.sin(th - 0.25) * 0.82], [math.cos(th + 0.25) * 0.82, 0.5 + hgl, math.sin(th + 0.25) * 0.82], [math.cos(th) * 0.82, 0.5 + hgl + hh, math.sin(th) * 0.82]])
                put('vidro', Vt, [[0, 1, 2]])
        else:
            V, F = cyl(1.0, 0.25, 14, y0=3.2); put('metal', V, F)            # tampa
            V, F = cyl(0.25, 0.9, 8, y0=3.45); put('metal', V, F)
            for k in range(4):                                                # aros
                th = math.pi / 2 * k
                V, F = box(0.12, 2.7, 0.12, 0.5); put('metal', T(V, t=(math.cos(th) * 0.86, 0, math.sin(th) * 0.86)), F)
        if v['glow'] and v['state'] != 'tombado':
            lh = hgl * (0.85 if v['state'] == 'inteiro' else 0.4)
            V, F = cyl(0.76, lh, 14, y0=0.52); put('liquido', V, F)
        if v['state'] != 'inteiro':  # cacos no chão em volta
            for k in range(5):
                a = rng.uniform(0, 6.28); r = rng.uniform(1.0, 2.0)
                Vt = np.array([[0, 0, 0], [rng.uniform(0.2, 0.5), 0, rng.uniform(-0.1, 0.1)], [rng.uniform(0, 0.3), 0.02, rng.uniform(0.15, 0.4)]])
                G['vidro'].add(T(Vt, ry=rng.uniform(0, 6.28), t=(x + math.cos(a) * r, ground(x + math.cos(a) * r, z + math.sin(a) * r) + 0.02, z + math.sin(a) * r)), [[0, 1, 2]])

def tables(M, G):
    for t in PLAN['tables']:
        parts = []
        V, F = box(2.6, 0.14, 1.2, 1.0); parts.append(('madeira', V, F))
        for sx in (-1.15, 1.15):
            for sz in (-0.48, 0.48):
                V, F = box(0.14, 1.0, 0.14); parts.append(('madeira', T(V, t=(sx, 0, sz)), F))
        V, F = box(2.3, 0.08, 1.0, 0.25); parts.append(('madeira', V, F))
        if not t['tipped']:
            for k in range(4):  # frascos e livros em cima
                V, F = cyl(0.09, rng.uniform(0.2, 0.4), 6, r2=0.04); parts.append(('vidro', T(V, t=(rng.uniform(-1.1, 1.1), 1.14, rng.uniform(-0.4, 0.4))), F))
            V, F = box(0.5, 0.12, 0.35, 1.14); parts.append(('livros', T(V, ry=0.3, t=(0.6, 0, 0.1)), F))
        for g, V, F in parts:
            if t['tipped']: V = T(T(V, t=(0, -0.6, 0)), rz=math.pi / 2 * 0.95, t=(0, 0.62, 0))
            G[g].add(T(V, ry=t['ry'], t=(t['x'], t['y'], t['z'])), F)

def shelves(M, G):
    for s in PLAN['shelves']:
        parts = []
        for sx in (-1.1, 1.1):
            V, F = box(0.12, 2.9, 0.65); parts.append(('madeira', T(V, t=(sx, 0, 0)), F))
        V, F = box(2.32, 2.9, 0.06); parts.append(('madeira', T(V, t=(0, 0, -0.3)), F))
        for k in range(5):
            y = 0.1 + k * 0.68
            V, F = box(2.2, 0.08, 0.6, y); parts.append(('madeira', V, F))
            if k < 4:
                x = -1.0
                while x < 0.95:
                    w = rng.uniform(0.08, 0.16); hh = rng.uniform(0.38, 0.56)
                    if rng.random() < 0.82:
                        V, F = box(w, hh, 0.42, y + 0.08); parts.append(('livros', T(V, rz=rng.uniform(-0.12, 0.12) if rng.random() < 0.3 else 0, t=(x + w / 2, 0, 0.02)), F))
                    x += w + 0.01
        for g, V, F in parts:
            if s['fallen']: V = T(V, rx=-math.pi / 2 * 0.97, t=(0, 0.35, 1.2))
            G[g].add(T(V, ry=s['ry'], t=(s['x'], s['y'], s['z'])), F)

def cages(M, G):
    for c in PLAN['cages']:
        n = 14
        for k in range(n):
            if c['broken'] and k in (2, 3, 4): continue
            th = 2 * math.pi * k / n
            pts = [(math.cos(th) * 0.95, y, math.sin(th) * 0.95) for y in np.linspace(0, 2.3, 4)]
            if c['broken'] and k in (1, 5): pts = [(p[0] * (1 + 0.25 * i), p[1] - 0.2 * i, p[2] * (1 + 0.25 * i)) for i, p in enumerate(pts)]
            V, F = tube(pts, 0.04, 5); G['metal'].add(T(V, ry=c['ry'], t=(c['x'], c['y'], c['z'])), F)
        for y in (0.05, 1.2, 2.3):
            V, F = cyl(1.0, 0.1, n, y0=y, cap=False); G['metal'].add(T(V, ry=c['ry'], t=(c['x'], c['y'], c['z'])), F)
        V, F = sphere(1.0, n, 8, 0.55, top_only=True); G['metal'].add(T(V, t=(c['x'], c['y'] + 2.35, c['z'])), F)
        if rng.random() < 0.7:  # restos dentro
            add_human(G, (c['x'], c['y'] + 0.05, c['z']), rng.uniform(0, 6.28), int(rng.integers(3)), 0.85)

def pillars(M, G):
    for p in PLAN['pillars']:
        parts = []
        V, F = box(1.2, 0.5, 1.2); parts.append(('pedra', V, F))
        V, F = cyl(0.45, p['h'], 12, y0=0.5); parts.append(('pedra', V, F))
        V, F = box(1.2, 0.4, 1.2, 0.5 + p['h']); parts.append(('pedra', V, F))
        if p['fallen']:
            # quebrada em três pedaços deitados
            segs = [0.0, p['h'] * 0.4, p['h'] * 0.75, p['h']]
            for k in range(3):
                l = segs[k + 1] - segs[k]
                V, F = cyl(0.45, l * 0.97, 12)
                V = T(V, rz=math.pi / 2, t=(segs[k] + 0.6 + k * 0.25, 0.45, (k - 1) * 0.3))
                G['pedra'].add(T(V, ry=p['ry'], t=(p['x'], p['y'], p['z'])), F)
            V, F = box(1.2, 0.5, 1.2); G['pedra'].add(T(V, ry=p['ry'], t=(p['x'], p['y'], p['z'])), F)
            continue
        for g, V, F in parts: G[g].add(T(V, ry=p['ry'], t=(p['x'], p['y'], p['z'])), F)

# ---------------------------------------------------------------- ossos e esqueletos
def add_skull(G, at, ry, s=0.18, horns=False):
    x, y, z = at
    V, F = sphere(1.0, 9, 7, 0.85); G['osso'].add(T(V, s=(s, s, s * 1.15), ry=ry, t=(x, y + s * 0.8, z)), F)
    V, F = box(1.1, 0.6, 0.9); V = T(V, s=(s, s, s), t=(0, 0, s * 0.85))           # maxila, na frente
    G['osso'].add(T(V, ry=ry, t=(x, y + s * 0.05, z)), F)

def add_human(G, at, ry, pose=0, s=1.0):
    """esqueleto humano deitado (três poses)."""
    x, y, z = at; y += 0.06 * s
    P = lambda px, pz, h=0.0: T(np.array([[px, h, pz]]), s=(s, s, s), ry=ry, t=(x, y, z))[0]
    def bone(a, b, r=0.035):
        V, F = tube([a, b], r * s, 5); G['osso'].add(V, F)
        for e in (a, b):
            Vs, Fs = sphere(r * 1.6 * s, 5, 4); G['osso'].add(Vs + e, Fs)
    def ribs(c, n=5):
        for k in range(n):
            zz = 0.12 * k
            for sd in (-1, 1):
                pts = [P(c[0] + sd * (0.05 + 0.18 * math.sin(t * math.pi / 2) ), c[1] + zz, 0.02 + 0.12 * math.sin(t * math.pi)) for t in np.linspace(0, 1, 5)]
                V, F = tube(pts, 0.02 * s, 4); G['osso'].add(V, F)
    bend = [0.0, 0.5, -0.4][pose]
    head = P(0, -0.35); add_skull(G, (head[0], y - 0.05 * s, head[2]), ry + bend, 0.13 * s)
    bone(P(0, -0.15), P(0, 0.75), 0.03)                       # coluna
    ribs((0, -0.05))
    bone(P(-0.2, 0.75), P(0.2, 0.75), 0.05)                   # bacia
    arm = [(0.35, 0.35), (0.6, 0.1), (-0.1, 0.5)][pose]
    bone(P(-0.22, 0.0), P(-0.35, 0.45)); bone(P(-0.35, 0.45), P(-0.3 - arm[1], 0.9))
    bone(P(0.22, 0.0), P(0.35 + arm[0] * 0.3, 0.4)); bone(P(0.35 + arm[0] * 0.3, 0.4), P(0.4 + arm[0], 0.75 - arm[1]))
    leg = [0.0, 0.3, -0.25][pose]
    bone(P(-0.12, 0.8), P(-0.18 - leg, 1.35), 0.04); bone(P(-0.18 - leg, 1.35), P(-0.2 - leg * 1.4, 1.85))
    bone(P(0.12, 0.8), P(0.2, 1.35), 0.04); bone(P(0.2, 1.35), P(0.18 + leg, 1.85))

def beast(G, b):
    """esqueleto de criatura grande: coluna curva, caixa de costelas, crânio alongado (com chifres ou não)."""
    x, z, y, ry, s = b['x'], b['z'], b['y'] + 0.1, b['ry'], b['s']
    L = 7.0 if b['kind'] != 'serpente' else 13.0
    n = 18 if b['kind'] != 'serpente' else 34
    spine = []
    for k in range(n):
        t = k / (n - 1)
        if b['kind'] == 'serpente': px, pz, py = t * L, math.sin(t * 9) * 1.4, 0.3
        else: px, pz, py = t * L, math.sin(t * 2.5) * 0.6, 0.35 + 1.1 * math.sin(min(1, t * 1.6) * math.pi) * (t < 0.62)
        spine.append(T(np.array([[px - L / 2, py, pz]]), s=(s, s, s), ry=ry, t=(x, y, z))[0])
    V, F = tube(spine, 0.12 * s, 6); G['osso'].add(V, F)
    for k, p in enumerate(spine):  # vértebras
        Vs, Fs = sphere(0.2 * s, 6, 4, 0.7); G['osso'].add(Vs + p, Fs)
    # costelas
    r0, r1 = (2, 11) if b['kind'] != 'serpente' else (3, 31)
    for k in range(r0, r1):
        p = spine[k]; t = (k - r0) / (r1 - r0)
        size = (1.6 * math.sin(t * math.pi) + 0.5) if b['kind'] != 'serpente' else 0.9
        for sd in (-1, 1):
            if rng.random() < 0.12: continue
            pts = []
            for u in np.linspace(0, 1, 7):
                a = u * math.pi * 0.95
                q = np.array([0.0, math.cos(a) * size * s * 0.9 - 0.1, sd * math.sin(a) * size * s * 0.75])
                pts.append(T(q[None], ry=ry)[0] + np.array([p[0], y + max(0.1, (q[1] + size * s * 0.9) * 0.5), p[2]]))
            V, F = tube(pts, 0.07 * s, 5); G['osso'].add(V, F)
    # crânio
    head = spine[-1]
    sk = 1.4 * s
    V, F = sphere(1.0, 10, 7, 0.6); G['osso'].add(T(V, s=(sk * 1.6, sk * 0.9, sk * 0.9), ry=ry, t=(head[0], y + sk * 0.5, head[2])), F)
    V, F = box(1.0, 0.4, 0.9); fwd = T(np.array([[sk * 1.6, 0, 0]]), ry=ry)[0]
    G['osso'].add(T(V, s=(sk * 1.5, sk, sk), ry=ry, t=(head[0] + fwd[0] * 0.8, y + sk * 0.1, head[2] + fwd[2] * 0.8)), F)
    for sd in (-1, 1):  # órbitas escuras não dá; põe as maxilas e dentes
        for k in range(5):
            tp = T(np.array([[sk * (0.9 + k * 0.25), 0.0, sd * sk * 0.35]]), ry=ry)[0] + np.array([head[0], y + sk * 0.05, head[2]])
            V, F = cyl(0.06 * sk, 0.35 * sk, 5, r2=0.0); G['osso'].add(V + tp, F)
    if b['kind'] == 'chifrudo':
        for sd in (-1, 1):
            pts = [T(np.array([[-0.3 * sk - u * 1.3 * sk, sk * 0.6 + u * u * 1.6 * sk, sd * (0.5 + u * 0.8) * sk]]), ry=ry)[0] + np.array([head[0], y, head[2]]) for u in np.linspace(0, 1, 6)]
            V, F = tube(pts, np.linspace(0.22, 0.03, 6) * sk, 6); G['osso'].add(V, F)
    # patas (quadrúpede e chifrudo)
    if b['kind'] != 'serpente':
        for k, sd in ((4, 1), (4, -1), (12, 1), (12, -1)):
            p = spine[k]
            a = T(np.array([[0, 0, sd * 0.6 * s]]), ry=ry)[0] + np.array([p[0], y + 0.4, p[2]])
            bb = T(np.array([[rng.uniform(-1, 1) * s, 0, sd * 2.2 * s]]), ry=ry)[0] + np.array([p[0], y + 0.15, p[2]])
            c = bb + T(np.array([[1.2 * s, 0, sd * 0.6 * s]]), ry=ry)[0] + [0, -0.05, 0]
            for e1, e2 in ((a, bb), (bb, c)):
                V, F = tube([e1, e2], 0.12 * s, 6); G['osso'].add(V, F)

def bone_variants(M):
    """cinco ossos soltos (instanciados aos milhares no chão do covil)."""
    vs = []
    for k in range(5):
        G = {'osso': Grp(M['osso'])}
        if k == 0:
            V, F = tube([(-0.35, 0.05, 0), (0.35, 0.05, 0)], 0.045, 6); G['osso'].add(V, F)
            for e in (-0.38, 0.38):
                for sd in (-1, 1): Vs, Fs = sphere(0.06, 6, 4); G['osso'].add(Vs + [e, 0.05, sd * 0.04], Fs)
        elif k == 1: add_skull(G, (0, -0.02, 0), 0.0, 0.14)
        elif k == 2:
            pts = [(math.cos(a) * 0.4, 0.04 + math.sin(a) * 0.08, math.sin(a) * 0.4) for a in np.linspace(0, 2.4, 7)]
            V, F = tube(pts, 0.03, 5); G['osso'].add(V, F)
        elif k == 3:
            V, F = sphere(0.22, 8, 5, 0.45); G['osso'].add(V + [0, 0.05, 0], F)
            for sd in (-1, 1): Vb, Fb = tube([(sd * 0.1, 0.05, 0), (sd * 0.3, 0.05, 0.25)], 0.05, 5); G['osso'].add(Vb, Fb)
        else:
            for j in range(4):
                Vs, Fs = sphere(0.07, 6, 4, 0.7); G['osso'].add(Vs + [j * 0.13, 0.05, math.sin(j) * 0.05], Fs)
        vs.append(G['osso'])
    return vs

# ---------------------------------------------------------------- tesouro, cogumelos, rochas, estátua
def hoard(M, G):
    h = PLAN['hoard']; x, z, y, r = h['x'], h['z'], h['y'], h['r']
    V, F = sphere(1.0, 22, 12, 1.0, top_only=True)
    V = V * [r, 1.7, r * 0.8]
    g = np.random.default_rng(3); V[:, 1] *= (0.85 + 0.3 * g.random(len(V))); V[:, 1] = np.maximum(V[:, 1], 0)
    G['ouro'].add(T(V, ry=0.4, t=(x, y - 0.1, z)), F)
    for k in range(9):  # montes menores em volta
        a = rng.uniform(0, 6.28); d = rng.uniform(r * 0.7, r * 1.25); rr = rng.uniform(0.9, 2.0)
        V, F = sphere(1.0, 10, 6, 1.0, top_only=True); V = V * [rr, rr * 0.35, rr]
        G['ouro'].add(T(V, t=(x + math.cos(a) * d, ground(x + math.cos(a) * d, z + math.sin(a) * d) - 0.05, z + math.sin(a) * d)), F)
    for k in range(7):  # baús
        a = rng.uniform(0, 6.28); d = rng.uniform(r * 0.6, r * 1.2); px, pz = x + math.cos(a) * d, z + math.sin(a) * d
        ry = rng.uniform(0, 6.28); py = ground(px, pz) + rng.uniform(0, 0.6)
        V, F = box(1.3, 0.75, 0.8); G['madeira'].add(T(V, ry=ry, t=(px, py, pz)), F)
        V, F = cyl(0.4, 1.3, 8); G['madeira'].add(T(T(V, rz=math.pi / 2, t=(0.65, 0.75, 0)), s=(1, 0.6, 1), ry=ry, t=(px, py, pz)), F)   # tampa arredondada
        for sx in (-0.45, 0.45):
            V, F = box(0.1, 0.95, 0.84); G['metal'].add(T(T(V, t=(sx, 0, 0)), ry=ry, t=(px, py, pz)), F)                        # cintas de ferro
    for k in range(18):  # taças, coroas e gemas
        a = rng.uniform(0, 6.28); d = rng.uniform(0, r * 1.1); px, pz = x + math.cos(a) * d, z + math.sin(a) * d
        py = y + 1.7 * max(0, 1 - (d / r) ** 2) ** 0.5 - 0.1 if d < r else ground(px, pz)
        if k % 3 == 0:
            V, F = cyl(0.16, 0.35, 8, r2=0.24, y0=0.18); G['ouro'].add(V + [px, py, pz], F); V, F = cyl(0.04, 0.2, 6); G['ouro'].add(V + [px, py, pz], F)
        elif k % 3 == 1:
            V, F = sphere(0.14, 6, 4, 1.3); G['gema'].add(V + [px, py + 0.1, pz], F)
        else:
            V, F = cyl(0.3, 0.22, 10, cap=False); G['ouro'].add(T(V, rx=rng.uniform(-0.4, 0.4), t=(px, py, pz)), F)
    # esqueletos de aventureiros que tentaram roubar
    for k in range(3):
        a = rng.uniform(0, 6.28); d = r * rng.uniform(1.1, 1.4); px, pz = x + math.cos(a) * d, z + math.sin(a) * d
        add_human(G, (px, ground(px, pz), pz), rng.uniform(0, 6.28), k % 3)

def mushroom_variants(M):
    out = []
    for k in range(4):
        stem, cap = Grp(M['cog_haste']), Grp(M['cog%d' % k])
        lean = [(0.0, 0.0), (0.15, 0.05), (-0.1, 0.12), (0.05, -0.15)][k]
        pts = [(lean[0] * t * t, t, lean[1] * t * t) for t in np.linspace(0, 1, 5)]
        V, F = tube(pts, np.linspace(0.11, 0.07, 5), 7); stem.add(V, F)
        top = np.array(pts[-1])
        shape = [(0.5, 0.42), (0.42, 0.62), (0.6, 0.3), (0.38, 0.8)][k]   # (raio, achatamento) — o de topo pontudo vira "sino"
        V, F = sphere(shape[0], 12, 8, shape[1], top_only=True); cap.add(V + top - [0, 0.05, 0], F)
        V, F = cyl(shape[0] * 1.02, 0.05, 12, r2=shape[0] * 0.75, y0=-0.05); cap.add(V + top, F)  # aba
        for j in range(5):  # pintas
            a = 2 * math.pi * j / 5 + k; rr = shape[0] * 0.55
            Vs, Fs = sphere(0.05, 5, 3, 0.5); cap.add(Vs + top + [math.cos(a) * rr, shape[0] * shape[1] * 0.75, math.sin(a) * rr], Fs)
        out.append((stem, cap))
    return out

def rubble_variants(M):
    out = []
    for k in range(4):
        g = Grp(M['tijolo'], 3.0)
        if k < 2:
            V, F = box(1.0, 0.55, 0.7); V = V + np.random.default_rng(k).normal(0, 0.06, V.shape); V[:, 1] = np.maximum(V[:, 1], 0); g.add(V, F)
        elif k == 2:
            for j in range(3):
                V, F = box(0.6, 0.4, 0.5); g.add(T(V, ry=j * 0.7, t=(j * 0.35 - 0.35, 0.0 if j != 1 else 0.38, j * 0.1)), F)
        else:
            V, F = rock(0.6, 9, 0.6, 7, 0.4); g.add(V, F)
        out.append(g)
    return out

def jar_variants(M):
    out = []
    for k in range(3):
        g = Grp(M['vidro'] if k != 2 else M['madeira'])
        if k == 0: V, F = cyl(0.18, 0.45, 8, r2=0.06); g.add(V, F)
        elif k == 1:
            V, F = sphere(0.2, 8, 6, 1.0); g.add(V + [0, 0.2, 0], F); V, F = cyl(0.06, 0.25, 6, y0=0.35); g.add(V, F)
        else: V, F = cyl(0.3, 0.6, 8, r2=0.25); g.add(V, F)      # barrilete
        out.append(g)
    return out

def statue(M, G):
    s = PLAN['statue']; x, z, y, ry, sc = s['x'], s['z'], s['y'], s['ry'], 3.2
    parts = []
    # cabeça deitada de lado: elipsoide com testa, nariz, boca e um toucado em leque
    V, F = sphere(1.0, 20, 14, 1.0); V = V * [1.15, 1.0, 1.35]
    g = np.random.default_rng(8); V *= (1 + 0.04 * (g.random(len(V)) - 0.5))[:, None]
    parts.append(('rocha', V, F))
    V, F = box(0.5, 0.9, 0.6); parts.append(('rocha', T(V, rx=0.2, t=(0, -0.15, 1.3)), F))       # nariz
    V, F = box(1.6, 0.25, 0.4, 0.35); parts.append(('rocha', T(V, t=(0, 0, 1.2)), F))            # sobrancelha
    for sd in (-1, 1):
        V, F = sphere(0.24, 8, 6, 0.6); parts.append(('rocha', V * [1.4, 1, 0.5] + [sd * 0.45, 0.15, 1.3], F))  # pálpebras
    V, F = box(0.9, 0.14, 0.25, -0.75); parts.append(('rocha', T(V, t=(0, 0, 1.2)), F))           # lábios
    for k in range(9):  # toucado: placas em leque atrás da cabeça
        a = -1.2 + k * 0.3
        V, F = box(0.5, 1.6, 0.18, 0.6); parts.append(('pedra', T(V, rz=a, t=(0, 0.2, -0.6)), F))
    V, F = cyl(1.25, 0.35, 16, y0=0.6); parts.append(('pedra', T(V, rx=0.25, t=(0, 0, -0.1)), F))
    for k in range(2):  # orelhas/brincos
        V, F = cyl(0.25, 0.6, 8); parts.append(('pedra', T(V, rz=math.pi / 2, t=(-1.4 if k else 0.8, -0.4, 0.1)), F))
    for grp, V, F in parts:
        V = T(V, rz=1.25, rx=-0.15)           # tombada de lado, meio afundada
        G[grp].add(T(V, s=(sc, sc, sc), ry=ry, t=(x, y + 1.4, z)), F)
    # cacos do corpo da estátua em volta
    for k in range(6):
        a = ry + rng.uniform(-1.0, 1.0) + math.pi; d = rng.uniform(5, 9); px, pz = x + math.cos(a) * d, z + math.sin(a) * d
        V, F = box(rng.uniform(1.2, 2.4), rng.uniform(0.8, 1.5), rng.uniform(1.0, 2.0)); G['pedra'].add(T(V, ry=rng.uniform(0, 6), rx=rng.uniform(-0.2, 0.2), t=(px, ground(px, pz) - 0.2, pz)), F)

def rocks(M, G):
    for x, z, y, h, s, ry in PLAN['spires']:
        V, F = cyl(0.7 * s, h, 7, r2=0.08 * s); g = np.random.default_rng(abs(int(x * 7 + z * 3)) + 1)
        V = V + g.normal(0, 0.08 * s, V.shape); G['rocha'].add(T(V, ry=ry, t=(x, y - 0.3, z)), F)
    for x, z, y, s, ry in PLAN['boulders']:
        V, F = rock(s, abs(int(x * 13 + z * 7)) + 1, 0.65, 9, 0.45); G['rocha'].add(T(V, ry=ry, t=(x, y - 0.2 * s, z)), F)

# ---------------------------------------------------------------- montagem
def main():
    global ROOT_OBJ
    bpy.ops.wm.read_factory_settings(use_empty=True)
    ROOT_OBJ = bpy.data.objects.new('covil', None); bpy.context.scene.collection.objects.link(ROOT_OBJ)
    M = mats()
    G = {k: Grp(v, {'tijolo': 4.0, 'pedra': 4.0, 'rocha': 6.0, 'madeira': 2.0, 'metal': 2.0, 'ouro': 3.0}.get(k, 3.0)) for k, v in M.items()}
    for fn in (walls, panels, pipes, altar, gate, vats, tables, shelves, cages, pillars, hoard, statue, rocks):
        fn(M, G); print('  ', fn.__name__)
    for s in PLAN['skeletons']: add_human(G, (s['x'], s['y'], s['z']), s['ry'], s['pose'])
    for b in PLAN['beasts']: beast(G, b)
    tris = 0
    for k, g in G.items():
        me = make_mesh('covil_' + k, g)
        if me: link('covil_' + k, me); tris += sum(len(p.vertices) - 2 for p in me.polygons)
    print('   fixos: %d triângulos' % tris)
    # instanciados: entulho, frascos, ossos, cogumelos
    def instances(name, variants, items, place):
        par = [group_parent(f'{name}_{k}') for k in range(len(variants))]
        meshes = []
        for k, v in enumerate(variants):
            if isinstance(v, tuple):  # cogumelo: haste + chapéu numa malha só (dois materiais)
                gg = Grp(v[0].mat); gg.V = v[0].V + v[1].V; nst = sum(len(a) for a in v[0].V)
                gg.F = v[0].F + [[i + nst for i in f] for f in v[1].F]; gg.UV = v[0].UV + v[1].UV; gg.n = nst + v[1].n
                me = make_mesh(f'{name}_{k}', gg); me.materials.append(v[1].mat)
                nf0 = len(v[0].F)
                for pi, poly in enumerate(me.polygons): poly.material_index = 0 if pi < nf0 else 1
            else: me = make_mesh(f'{name}_{k}', v)
            meshes.append(me)
        count = 0
        for it in items:
            k, loc, ry, s = place(it)
            link(f'{name}_{k}_{count}', meshes[k], loc, ry, s, par[k]); count += 1
        print('   %s: %d cópias' % (name, count))
    instances('entulho', rubble_variants(M), PLAN['rubble'], lambda r: (r[5] % 4, (r[0], r[2] - 0.1, r[1]), r[4], r[3]))
    instances('frasco', jar_variants(M), PLAN['jars'], lambda r: (r[5] % 3, (r[0], r[2], r[1]), r[4], r[3]))
    instances('osso', bone_variants(M), PLAN['bones'], lambda r: (r[5] % 5, (r[0], r[2] - 0.02, r[1]), r[4], r[3]))
    instances('cogumelo', mushroom_variants(M), PLAN['mushrooms'], lambda r: (r[4] % 4, (r[0], r[2] - 0.05, r[1]), r[5], r[3]))
    for o in bpy.context.scene.objects: o.select_set(True)
    bpy.ops.export_scene.gltf(filepath=OUT, export_format='GLB', export_extras=True, export_gpu_instances=True,
                              export_materials='EXPORT', export_image_format='NONE', export_apply=False)
    print('GLB: %.1f MB' % (os.path.getsize(OUT) / 1e6))

if __name__ == '__main__':
    main()
