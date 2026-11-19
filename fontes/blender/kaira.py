"""Kaira — elfa etérea (folha: fontes/recebidos/conceito_kaira_elfa-eterea.png).

Gera a personagem inteira por script: corpo, cabeça e rosto pintado, orelhas, cabelo, vestido,
mangas, joias, esqueleto, pesos e animações; exporta public/assets/characters/kaira/char_kaira_script.glb
(a Kaira jogável hoje é o modelo recebido, rigado por kaira_glb_2_rig.py).

Rodar:  python3 fontes/blender/kaira.py
Medidas em metros. Altura 1,77 m (≈7,5 cabeças). Modelo olha para -Y; esquerda dela = +X.
"""
import math, os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
import bpy, bmesh
from mathutils import Vector, Matrix, Quaternion

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib
from lib import mesh_obj, material, set_material, loft, apply_mods, activate

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
OUT = os.path.join(ROOT, 'public', 'assets', 'characters', 'kaira')
os.makedirs(OUT, exist_ok=True)
STAGE = int(os.environ.get('STAGE', '9'))  # até que etapa construir (para conferir em partes)

# ---------------------------------------------------------------- paleta (da folha)
def hexc(h, a=1.0):
    h = h.lstrip('#'); return (int(h[0:2], 16) / 255, int(h[2:4], 16) / 255, int(h[4:6], 16) / 255, a)
def lin(c):  # sRGB -> linear para cores de material
    f = lambda x: x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4
    return (f(c[0]), f(c[1]), f(c[2]), c[3])
SKIN = '#cfd8a2'
HAIR = '#f37aaa'; HAIR_DARK = '#d65a8c'; HAIR_LIGHT = '#ffb2d0'
DRESS = '#f6dcd6'; DRESS_SHADE = '#e9c4c2'; UNDER = '#aebd8c'
GOLD = '#e2b25a'; GEM = '#ff5c9a'; SLEEVE = '#f8d4dc'

# ---------------------------------------------------------------- medidas
H = 1.77
SH_L = Vector((0.158, 0.012, 1.405))          # ombro (articulação)
ARM_DIR = Vector((math.cos(math.radians(45)), 0, -math.sin(math.radians(45))))  # A-pose 45°
UPPER, FORE, HAND = 0.275, 0.24, 0.17
HIP_L = Vector((0.088, 0.0, 0.885))
KNEE_L = Vector((0.094, -0.008, 0.475))
ANKLE_L = Vector((0.098, 0.022, 0.095))
def mirror(v): return Vector((-v.x, v.y, v.z))
def arm_pts(side=1):
    sh = SH_L if side > 0 else mirror(SH_L)
    d = ARM_DIR.copy(); d.x *= side
    el = sh + d * UPPER
    wr = el + d * FORE
    return sh, el, wr, d


# ================================================================ CORPO (modificador Skin + subdivisão)
RS = float(os.environ.get('RS', '1.25'))  # calibração do raio do Skin
def build_body():
    V, E, R = [], [], []
    def add(p, r, parent=None):
        r = r if isinstance(r, tuple) else (r, r)
        V.append(tuple(p)); R.append((r[0] * RS, r[1] * RS))
        i = len(V) - 1
        if parent is not None: E.append((parent, i))
        return i
    pel = add((0, 0.010, 0.93), (0.186, 0.126))
    wst = add((0, 0.010, 1.06), (0.098, 0.074), pel)
    rib = add((0, 0.004, 1.16), (0.124, 0.086), wst)
    chs = add((0, 0.004, 1.27), (0.160, 0.098), rib)
    upc = add((0, 0.012, 1.365), (0.134, 0.100), chs)
    nk0 = add((0, 0.024, 1.44), (0.040, 0.037), upc)
    nk1 = add((0, 0.024, 1.51), (0.032, 0.033), nk0)
    add((0, 0.030, 1.59), (0.027, 0.028), nk1)
    for s in (1, -1):
        sh, el, wr, d = arm_pts(s)
        cl = add((0.085 * s, 0.006, 1.405), 0.050, upc)
        a0 = add(sh, 0.047, cl)
        a1 = add(sh + d * UPPER * 0.5, 0.040, a0)
        a2 = add(el, 0.032, a1)
        a3 = add(el + d * FORE * 0.45, 0.031, a2)
        a4 = add(wr, 0.022, a3)
        # mão: palma achatada; dedos para baixo, polegar para a frente
        side = Vector((0, -1, 0))                       # frente
        palm = add(wr + d * 0.05, (0.030, 0.012), a4)
        kn = wr + d * 0.092
        for k, off in enumerate((-0.021, -0.007, 0.007, 0.020)):  # indicador..mínimo (frente->trás)
            base = kn + Vector((0, off, 0)) + d * (0.004 if k in (1, 2) else 0)
            f0 = add(base, 0.0085, palm)
            ln = (0.040, 0.046, 0.043, 0.034)[k]
            f1 = add(base + d * ln * 0.55 + Vector((-0.004 * s, 0, 0)), 0.0078, f0)
            add(base + d * ln + Vector((-0.010 * s, 0, 0)), 0.0068, f1)
        t0 = add(wr + d * 0.03 + Vector((-0.010 * s, -0.022, 0)), 0.010, palm)
        t1 = add(wr + d * 0.055 + Vector((-0.016 * s, -0.038, 0)), 0.0085, t0)
        add(wr + d * 0.075 + Vector((-0.018 * s, -0.048, 0)), 0.0072, t1)
        hp = HIP_L if s > 0 else mirror(HIP_L)
        kn_ = KNEE_L if s > 0 else mirror(KNEE_L)
        an = ANKLE_L if s > 0 else mirror(ANKLE_L)
        l0 = add(hp, 0.080, pel)
        l1 = add(hp.lerp(kn_, 0.45) + Vector((0, 0.004, 0)), 0.066, l0)
        l2 = add(kn_, 0.047, l1)
        l3 = add(kn_.lerp(an, 0.33) + Vector((0, 0.018, 0)), 0.054, l2)
        l4 = add(an + Vector((0, 0, 0.03)), 0.030, l3)
        # pé em salto: calcanhar alto, apoio na ponta
        heel = add(an + Vector((0, 0.035, -0.02)), (0.026, 0.024), l4)
        ball = add(Vector((an.x, -0.085, 0.022)), (0.030, 0.016), l4)
        add(Vector((an.x, -0.135, 0.014)), (0.024, 0.010), ball)
    me = bpy.data.meshes.new('body_cage')
    me.from_pydata(V, E, [])
    obj = lib.link(bpy.data.objects.new('kaira_body', me))
    sk = obj.modifiers.new('skin', 'SKIN')
    sk.branch_smoothing = 0.75
    sk.use_smooth_shade = True
    for i, r in enumerate(R):
        me.skin_vertices[0].data[i].radius = r
    me.skin_vertices[0].data[pel].use_root = True
    apply_mods(obj)
    sub = obj.modifiers.new('sub', 'SUBSURF'); sub.levels = 2; sub.render_levels = 2
    apply_mods(obj)
    # formas: busto, quadril, glúteos, clavículas
    def bump(center, radius, push, axis):
        c = Vector(center)
        for v in obj.data.vertices:
            dd = (v.co - c).length
            if dd < radius:
                w = (1 - (dd / radius) ** 2) ** 2
                v.co += Vector(axis) * push * w
    for s in (1, -1):
        bump((0.072 * s, -0.075, 1.262), 0.085, 0.068, (0.18 * s, -1, 0.08))
        bump((0.075 * s, 0.07, 0.87), 0.10, 0.022, (0, 1, 0))
        bump((0.13 * s, 0.0, 0.90), 0.10, 0.012, (s, 0, 0))
    fit_torso(obj)
    bpy.ops.object.shade_smooth()
    return obj

# contorno-alvo do tronco: z -> (meia-largura, frente, costas)
TORSO = [(1.33, 0.150, 0.085, 0.078), (1.29, 0.146, 0.112, 0.078), (1.255, 0.150, 0.132, 0.080), (1.205, 0.138, 0.104, 0.084),
         (1.13, 0.124, 0.088, 0.086), (1.065, 0.116, 0.082, 0.086), (0.99, 0.150, 0.090, 0.108), (0.93, 0.172, 0.098, 0.128), (0.86, 0.178, 0.100, 0.138)]
def torso_target(z):
    for i in range(len(TORSO) - 1):
        z0, *a = TORSO[i]; z1, *b = TORSO[i + 1]
        if z1 <= z <= z0:
            t = (z0 - z) / (z0 - z1); return [x + (y - x) * t for x, y in zip(a, b)]
    return None

def fit_torso(obj):
    """Escala cada faixa do tronco até o contorno-alvo, medindo a faixa na própria malha."""
    arms = [arm_pts(1), arm_pts(-1)]
    def is_limb(c):
        if c.z < 0.86 and abs(c.x) > 0.02: return True
        for sh, el, wr, d in arms:
            if lib.seg_dist(c, sh + d * 0.02, wr) < 0.06: return True
        return False
    verts = [v for v in obj.data.vertices if 0.84 < v.co.z < 1.35 and abs(v.co.x) < 0.22 and not is_limb(v.co)]
    band = {}
    for v in verts:
        k = round(v.co.z / 0.02)
        hw, fr, bk = band.get(k, (0.0, 0.0, 0.0))
        band[k] = (max(hw, abs(v.co.x)), max(fr, -v.co.y), max(bk, v.co.y))
    for v in verts:
        tgt = torso_target(v.co.z)
        cur = band.get(round(v.co.z / 0.02))
        if not tgt or not cur or min(cur) <= 0.01: continue
        # some suave perto dos ombros (z > 1.30) e das pernas (z < 0.88)
        w = min(1.0, max(0.0, (1.35 - v.co.z) / 0.05)) * min(1.0, max(0.0, (v.co.z - 0.84) / 0.04))
        sx = 1 + (tgt[0] / cur[0] - 1) * w
        sy = 1 + ((tgt[1] / cur[1] if v.co.y < 0 else tgt[2] / cur[2]) - 1) * w
        v.co.x *= sx; v.co.y *= sy


def hide_covered_skin(body):
    """Apaga faces do corpo que o vestido cobre sempre (economiza triângulos e evita a pele atravessar o tecido).
    Fica a pele do decote, dos braços e da perna direita (a da fenda)."""
    bm = bmesh.new(); bm.from_mesh(body.data)
    arms = [arm_pts(1), arm_pts(-1)]
    def keep(c):
        for sh, el, wr, d in arms:
            if lib.seg_dist(c, sh - d * 0.02, wr + d * 0.2) < 0.07: return True
        if c.z > neckline(c.x, c.y) - 0.02: return True          # decote e ombros
        if c.z < 0.86 and c.x < -0.02 and c.z > 0.30: return True  # perna da fenda
        if c.z < 0.42: return True                                 # canelas e pés aparecem ao andar
        return False
    kill = [f for f in bm.faces if not keep(f.calc_center_median())]
    bmesh.ops.delete(bm, geom=kill, context='FACES')
    bm.to_mesh(body.data); bm.free()

# ================================================================ CABEÇA, ROSTO, ORELHAS
HEAD_DZ = -0.012                                  # cabeça um pouco mais baixa: pescoço mais curto
HEAD_C = Vector((0, 0.014, 1.664 + HEAD_DZ))
def build_head():
    """Cabeça em proporção anime: crânio arredondado, rosto plano, maxilar afinando até um queixo redondo."""
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=64, v_segments=44, radius=1.0)
    for v in bm.verts:
        x, y, z = v.co
        fw = fd = 1.0
        if z < -0.05:
            t = (-0.05 - z) / 0.95
            fw = 1 - 0.40 * t ** 1.7                        # maxilar
            if y < 0: fd = 1 - 0.18 * t ** 2                 # o rosto desce reto na frente
            else: fd = 1 - 0.55 * t ** 1.2                   # nuca recolhe para o pescoço
        if z > 0.25: fw *= 1 + 0.06 * min(1.0, (z - 0.25) / 0.45)   # crânio mais largo em cima
        X = x * 0.0765 * fw
        Y = y * (0.094 if y > 0 else 0.080) * fd
        Z = z * (0.094 if z > 0 else 0.101)
        if y < 0 and -0.1 < z < 0.45: Y *= 0.97              # testa e bochechas planas
        if z < -0.75 and y < 0: Y -= 0.003 * (-0.75 - z) * 4  # queixo levemente à frente
        v.co = Vector((X, Y, Z)) + HEAD_C
    me = bpy.data.meshes.new('head'); bm.to_mesh(me); bm.free()
    obj = lib.link(bpy.data.objects.new('kaira_head', me))
    for v in me.vertices:                                     # nariz pequeno, órbitas rasas
        p = v.co - HEAD_C
        dn = (p - Vector((0, -0.080, -0.036))).length
        if dn < 0.022: v.co.y -= 0.0045 * (1 - dn / 0.022) ** 2
    uvl = me.uv_layers.new(name='UVMap')
    for poly in me.polygons:
        for li, vi in zip(poly.loop_indices, poly.vertices):
            co = me.vertices[vi].co
            uvl.data[li].uv = (0.5 + co.x / 0.26, (co.z - 1.522 - HEAD_DZ) / 0.26)
    for p in me.polygons: p.use_smooth = True
    # normais do rosto vindas de um elipsoide liso: a luz corre num degradê limpo, sem manchas de polígono
    ns = []
    for v in me.vertices:
        p = v.co - HEAD_C
        ell = Vector((p.x / 0.0765 ** 2, p.y / 0.088 ** 2, p.z / 0.10 ** 2)).normalized()
        ns.append(tuple(ell.lerp(v.normal, 0.15).normalized()))
    me.normals_split_custom_set_from_vertices(ns)
    return obj

FACE_M = 0.26  # metros cobertos pela textura do rosto (nos dois eixos)
def bez(p0, p1, p2, p3, n=24):
    return [tuple((1 - t) ** 3 * a + 3 * (1 - t) ** 2 * t * b + 3 * (1 - t) * t * t * c + t ** 3 * d for a, b, c, d in zip(p0, p1, p2, p3)) for t in (i / (n - 1) for i in range(n))]

def paint_face(S=1024):
    """Rosto pintado em estilo anime (olhos verdes, cílios com asa, sobrancelhas finas, boca pequena, blush)."""
    SS = 3; W = S * SS
    k = W / FACE_M                                            # pixels por metro
    P = lambda x, z: ((0.5 + x / FACE_M) * W, (1 - (z - 1.522) / FACE_M) * W)
    skin = tuple(int(c * 255) for c in hexc(SKIN)[:3])
    base = Image.new('RGBA', (W, W), skin + (255,))
    def layer(): return Image.new('RGBA', (W, W), (0, 0, 0, 0))
    def comp(img, blur=0):
        nonlocal base
        base = Image.alpha_composite(base, img.filter(ImageFilter.GaussianBlur(blur)) if blur else img)
    def poly(dr, pts, **kw): dr.polygon([P(x, z) for x, z in pts], **kw)
    def strip(dr, curve, w0, w1, fill):
        """traço que afina: polígono entre a curva e a curva deslocada na vertical."""
        n = len(curve); up = [(x, z + (w0 + (w1 - w0) * i / (n - 1)) / 2) for i, (x, z) in enumerate(curve)]
        dn = [(x, z - (w0 + (w1 - w0) * i / (n - 1)) / 2) for i, (x, z) in enumerate(curve)]
        poly(dr, up + dn[::-1], fill=fill)
    EZ = 1.657
    # blush e sombra rosada nas pálpebras
    L = layer(); d = ImageDraw.Draw(L)
    for s in (1, -1):
        x, y = P(0.041 * s, 1.623); d.ellipse([x - 0.012 * k, y - 0.006 * k, x + 0.012 * k, y + 0.006 * k], fill=(255, 110, 150, 60))
        x, y = P(0.036 * s, EZ + 0.008); d.ellipse([x - 0.014 * k, y - 0.004 * k, x + 0.014 * k, y + 0.004 * k], fill=(240, 100, 150, 22))
    comp(L, 9 * SS)
    for s in (1, -1):
        cx = 0.0335 * s
        inn, out = (cx - 0.0165 * s, EZ - 0.0015), (cx + 0.0170 * s, EZ + 0.0035)
        upper = bez(inn, (cx - 0.010 * s, EZ + 0.0105), (cx + 0.007 * s, EZ + 0.0118), out)
        lower = bez(out, (cx + 0.010 * s, EZ - 0.0050), (cx - 0.006 * s, EZ - 0.0082), inn)
        eye = upper + lower
        # esclera com sombra da pálpebra em cima
        L = layer(); d = ImageDraw.Draw(L); poly(d, eye, fill=(248, 245, 240, 255)); comp(L)
        L = layer(); d = ImageDraw.Draw(L); strip(d, upper, 0.0050, 0.0050, (170, 150, 150, 120))
        mask = layer(); ImageDraw.Draw(mask).polygon([P(x, z) for x, z in eye], fill=(255, 255, 255, 255))
        iris = layer(); di = ImageDraw.Draw(iris)
        ix, iy = P(cx - 0.0006 * s, EZ + 0.0008); RX, RY = 0.0074 * k, 0.0086 * k
        for i in range(40):                                   # íris: verde escuro em cima, claro embaixo
            t = i / 39
            col = tuple(int(a + (b - a) * t) for a, b in zip((44, 74, 26), (168, 212, 90)))
            di.ellipse([ix - RX, iy - RY + 2 * RY * t * 0.92, ix + RX, iy + RY], fill=col + (255,))
        di.ellipse([ix - RX, iy - RY, ix + RX, iy + RY], outline=(28, 44, 20, 255), width=int(0.0009 * k))
        for a in range(14):                                   # raios finos da íris
            ang = a / 14 * 2 * math.pi
            di.line([(ix + math.cos(ang) * RX * 0.45, iy + math.sin(ang) * RY * 0.45), (ix + math.cos(ang) * RX * 0.9, iy + math.sin(ang) * RY * 0.9)], fill=(110, 160, 60, 55), width=max(1, SS // 2))
        di.ellipse([ix - RX * 0.42, iy - RY * 0.46, ix + RX * 0.42, iy + RY * 0.46], fill=(18, 26, 12, 255))
        di.ellipse([ix - RX * 0.7 - RX * 0.15 * s, iy - RY * 0.78, ix - RX * 0.05 - RX * 0.15 * s, iy - RY * 0.14], fill=(255, 255, 255, 250))
        di.ellipse([ix + RX * 0.2, iy + RY * 0.32, ix + RX * 0.52, iy + RY * 0.6], fill=(255, 255, 255, 210))
        L.paste(iris, (0, 0), iris)
        L2 = layer(); L2.paste(L, (0, 0), Image.fromarray(np.minimum(np.array(mask.split()[3]), np.array(L.split()[3]))))
        comp(L2)
        d = ImageDraw.Draw(base, 'RGBA')
        # cílio superior: grosso, engrossa no canto externo, com asa
        lash_curve = bez((inn[0] - 0.0006 * s, inn[1] + 0.0003), (cx - 0.010 * s, EZ + 0.0112), (cx + 0.007 * s, EZ + 0.0125), (out[0] + 0.001 * s, out[1] + 0.0008))
        strip(d, lash_curve, 0.0010, 0.0030, (52, 26, 36, 255))
        wing = bez((out[0] - 0.003 * s, out[1] + 0.002), (out[0] + 0.002 * s, out[1] + 0.003), (out[0] + 0.005 * s, out[1] + 0.006), (out[0] + 0.0065 * s, out[1] + 0.0085), 10)
        strip(d, wing, 0.0022, 0.0004, (52, 26, 36, 255))
        for j, (tx, tz) in enumerate(((0.62, 0.0045), (0.80, 0.0055), (0.92, 0.006))):   # pontas de cílio
            i0 = int(tx * (len(lash_curve) - 1)); x0, z0 = lash_curve[i0]
            strip(d, [(x0, z0), (x0 + 0.0025 * s, z0 + tz * 0.5), (x0 + 0.0045 * s, z0 + tz)], 0.0012, 0.0002, (52, 26, 36, 255))
        # cílio inferior fino no terço externo e dobra da pálpebra
        lo = bez((cx + 0.002 * s, EZ - 0.0080), (cx + 0.008 * s, EZ - 0.0070), (cx + 0.013 * s, EZ - 0.0045), (out[0] - 0.0005 * s, out[1] - 0.0005), 12)
        strip(d, lo, 0.0003, 0.0009, (120, 64, 76, 220))
        crease = bez((cx - 0.010 * s, EZ + 0.0140), (cx - 0.002 * s, EZ + 0.0170), (cx + 0.010 * s, EZ + 0.0168), (out[0] + 0.0015 * s, out[1] + 0.0080), 16)
        strip(d, crease, 0.0004, 0.0007, (150, 120, 100, 150))
        # sobrancelha fina, rosa, afinando para fora
        brow = bez((cx - 0.0160 * s, EZ + 0.0205), (cx - 0.004 * s, EZ + 0.0270), (cx + 0.011 * s, EZ + 0.0272), (cx + 0.0215 * s, EZ + 0.0195), 20)
        strip(d, brow, 0.0015, 0.0004, (206, 110, 142, 215))
    d = ImageDraw.Draw(base, 'RGBA')
    # nariz: sombra pequena embaixo da ponta
    L = layer(); dl = ImageDraw.Draw(L); x, y = P(0.0, 1.6225); dl.ellipse([x - 0.0045 * k, y - 0.0012 * k, x + 0.0045 * k, y + 0.0012 * k], fill=(140, 140, 90, 110)); comp(L, 2 * SS)
    # boca: lábio inferior suave e linha do meio
    MZ = 1.592
    L = layer(); dl = ImageDraw.Draw(L)
    poly(dl, bez((-0.0090, MZ), (-0.004, MZ - 0.0062), (0.004, MZ - 0.0062), (0.0090, MZ), 16), fill=(232, 136, 146, 190)); comp(L, 1.5 * SS)
    d = ImageDraw.Draw(base, 'RGBA')
    strip(d, bez((-0.0105, MZ + 0.0010), (-0.004, MZ - 0.0002), (0.004, MZ - 0.0002), (0.0105, MZ + 0.0010), 20), 0.0005, 0.0005, (150, 62, 80, 235))
    strip(d, bez((-0.0040, MZ + 0.0040), (-0.0015, MZ + 0.0028), (0.0015, MZ + 0.0028), (0.0040, MZ + 0.0040), 10), 0.0003, 0.0003, (190, 110, 120, 120))
    img = base.resize((S, S), Image.LANCZOS)
    img.save(os.path.join(OUT, 'tx_kaira_face_col.png'))
    return np.asarray(img).astype(np.float32) / 255.0

def build_ears():
    objs = []
    for s in (1, -1):
        root = HEAD_C + Vector((0.070 * s, 0.010, -0.004))
        dirv = Vector((0.80 * s, 0.30, 0.52)).normalized()
        up = Vector((0, 0, 1)); side = dirv.cross(up).normalized(); upv = side.cross(dirv).normalized()
        L = 0.112; rings = []; N = 10
        for j in range(12):
            t = j / 11
            c = root + dirv * L * t + upv * 0.012 * math.sin(t * math.pi) * 0.6
            hh = 0.024 * (1 - t) ** 0.75 + 0.0012
            th = 0.0075 * (1 - t) + 0.0012
            ring = []
            for i in range(N):
                a = 2 * math.pi * i / N
                cup = -0.25 * hh * max(0, math.cos(a))      # concha: face interna côncava
                ring.append(tuple(c + upv * math.sin(a) * hh + side * s * (math.cos(a) * th + cup * 0.2)))
            rings.append(ring)
        tip = root + dirv * (L + 0.006)
        v, f, uv = loft(rings, closed=True, cap_bottom=True)
        v.append(tuple(tip)); ti = len(v) - 1; base = (len(rings) - 1) * N
        for i in range(N): f.append((base + i, base + (i + 1) % N, ti))
        objs.append(mesh_obj('kaira_ear_' + ('l' if s > 0 else 'r'), v, f))
    return objs


# ================================================================ CABELO
# Couro cabeludo aproximado por um elipsoide um pouco maior que o crânio.
def scalp(phi, th, off=0.0):
    """phi: azimute a partir da frente (-Y) girando para a esquerda dela (+X); th: elevação. Graus."""
    ph, t = math.radians(phi), math.radians(th)
    front = math.cos(ph) > 0
    a = 0.0805 + off
    b = (0.079 if front else 0.096) + off
    c = (0.096 if th > 0 else 0.108) + off
    return HEAD_C + Vector((a * math.cos(t) * math.sin(ph), -b * math.cos(t) * math.cos(ph), c * math.sin(t)))

# silhueta do corpo + vestido (meia-largura, meia-profundidade frente/trás) por altura, com folga
CLEAR = [(1.60, 0.055, 0.050, 0.060), (1.52, 0.060, 0.055, 0.070), (1.46, 0.150, 0.085, 0.095), (1.40, 0.205, 0.105, 0.105),
         (1.30, 0.180, 0.150, 0.110), (1.20, 0.160, 0.130, 0.105), (1.08, 0.150, 0.115, 0.110), (0.95, 0.190, 0.140, 0.165),
         (0.82, 0.205, 0.165, 0.185), (0.60, 0.225, 0.200, 0.215), (0.30, 0.260, 0.240, 0.250), (0.00, 0.300, 0.280, 0.280)]
def clear_r(z, phi):
    for i in range(len(CLEAR) - 1):
        z0, *r0 = CLEAR[i]; z1, *r1 = CLEAR[i + 1]
        if z1 <= z <= z0:
            t = (z0 - z) / (z0 - z1); rx, rf, rb = [a + (b - a) * t for a, b in zip(r0, r1)]; break
    else:
        rx, rf, rb = CLEAR[0][1:] if z > CLEAR[0][0] else CLEAR[-1][1:]
    ph = math.radians(phi); ry = rf if math.cos(ph) > 0 else rb
    c, s_ = math.cos(ph), math.sin(ph)
    return 1.0 / math.sqrt((s_ / rx) ** 2 + (c / ry) ** 2)       # raio da elipse na direção phi

def ribbon(path, widths, thick, side_of=None, N=8):
    """Fita de seção em lente ao longo de path. side_of(i) devolve o vetor 'para fora' (normal da fita)."""
    rings, uvs = [], []
    L = len(path)
    for i, p in enumerate(path):
        t_ = (path[min(i + 1, L - 1)] - path[max(i - 1, 0)]).normalized()
        out = side_of(i) if side_of else Vector((0, 0, 1))
        out = (out - t_ * out.dot(t_)).normalized()
        across = t_.cross(out).normalized()
        w, th = widths[i], thick[i]
        ring = []
        for k in range(N):
            a = 2 * math.pi * k / N
            ring.append(tuple(p + across * math.cos(a) * w / 2 + out * math.sin(a) * th / 2))
        rings.append(ring)
    v, f, uv = loft(rings, closed=True)
    # ponta fechada
    v.append(tuple(path[-1] + (path[-1] - path[-2]).normalized() * 0.004)); ti = len(v) - 1; base = (L - 1) * N
    for k in range(N): f.append((base + k, base + (k + 1) % N, ti))
    uv.append((0.5, 1.0))
    return v, f, uv

def hang(phi, z0, z1, p_exit, n, layer=0.0, sway=0.0, swing=0.0):
    """Trecho que cai: do ponto de saída do couro cabeludo até z1, por fora do corpo e do vestido."""
    pts = []; r_prev = Vector((p_exit.x, p_exit.y, 0)).length
    for i in range(1, n + 1):
        t = i / n; z = z0 + (z1 - z0) * t
        r = max(clear_r(z, phi) + 0.012 + layer, r_prev * 0.97)
        r_prev = r
        ph = math.radians(phi + swing * t + sway * math.sin(t * math.pi * 1.5))
        pts.append(Vector((r * math.sin(ph), -r * math.cos(ph), z)))
    # junta suave entre o couro cabeludo e a queda
    pts[0] = pts[0].lerp(p_exit, 0.35)
    return pts

def build_hair():
    rnd = np.random.default_rng(7)
    V, F, UV = [], [], []
    def add(v, f, uv):
        o = len(V); V.extend(v); UV.extend(uv); F.extend([tuple(i + o for i in face) for face in f])
    def radial_out(pts):
        return lambda i: Vector((pts[i].x, pts[i].y, 0)).normalized() + Vector((0, 0, 0.15))
    # --- cortina de trás e laterais: contorna o crânio e cai
    strands = []
    for k in range(22):
        phi = 78 + k * (204 / 21)                                    # de 78° (lado esq.) a 282° (lado dir.), passando por trás
        back = abs(((phi - 180) + 180) % 360 - 180) < 60
        th_exit = -38 if back else -12
        zend = 0.56 + rnd.uniform(-0.05, 0.05) if back else 0.78 + rnd.uniform(-0.06, 0.06)
        strands.append((phi, th_exit, zend, 0.010 + 0.004 * (k % 2)))
    for k in range(10):                                              # segunda camada, por baixo, mais curta
        phi = 100 + k * (160 / 9)
        strands.append((phi, -40, 0.70 + rnd.uniform(-0.05, 0.05), 0.0))
    for phi, th_exit, zend, layer in strands:
        scalp_pts = [scalp(phi, th, 0.010 + layer * 0.5) for th in np.linspace(48, th_exit, 7)]
        p_exit = scalp_pts[-1]
        fall = hang(phi, p_exit.z - 0.03, zend, p_exit, 14, layer=layer, sway=rnd.uniform(-3, 3), swing=rnd.uniform(-2, 2))
        path = scalp_pts + fall
        L = len(path)
        # largura acompanha o espaço entre mechas (que cresce conforme o corpo alarga), com sobreposição
        spacing = math.radians(204 / 21) if layer > 0 or True else 0
        def wid(i):
            r = Vector((path[i].x, path[i].y, 0)).length
            w = max(0.034, r * spacing * 2.3)
            if i < 7: return max(w, 0.046)
            t = (i - 7) / (L - 8)
            return w * (1.0 if t < 0.7 else 1 - 0.85 * ((t - 0.7) / 0.3) ** 1.3)
        widths = [wid(i) for i in range(L)]
        thick = [0.011 if i < 7 else 0.011 * (1 - 0.45 * (i - 7) / (L - 7)) for i in range(L)]
        add(*ribbon(path, widths, thick, radial_out(path)))
    # --- mechas da frente: caem pela frente dos ombros até a cintura
    for s in (1, -1):
        for j, (phi, zend, w) in enumerate(((72, 1.00, 0.046), (82, 1.04, 0.044), (64, 1.10, 0.036))):
            ph = phi * s
            scalp_pts = [scalp(ph, th, 0.011) for th in np.linspace(44, -10, 6)]
            p_exit = scalp_pts[-1]
            fall = hang(ph, p_exit.z - 0.03, zend, p_exit, 12, layer=0.004 * j, sway=2 * s)
            path = scalp_pts + fall; L = len(path)
            widths = [w * (1.0 if i < 6 else (1.15 if (i - 6) / (L - 6) < 0.65 else 1.15 * (1 - 0.85 * (((i - 6) / (L - 6) - 0.65) / 0.35) ** 1.3))) for i in range(L)]
            thick = [0.009 if i < 6 else 0.009 * (1 - 0.6 * (i - 6) / (L - 6)) for i in range(L)]
            add(*ribbon(path, widths, thick, radial_out(path)))
    # --- franja: risca no meio, pontas varrendo para os lados, as de fora emolduram o rosto
    for s in (1, -1):
        for j, (phi0, sweep, th_end, w) in enumerate(((4, 14, 18, 0.034), (14, 16, 16, 0.034), (24, 14, 12, 0.032), (34, 10, 2, 0.030), (44, 6, -30, 0.026))):
            pts = []
            n = 10
            for i in range(n):
                t = i / (n - 1)
                th = 50 + (th_end - 50) * t
                ph = (phi0 + sweep * t ** 1.3) * s
                off = 0.010 + 0.006 * math.sin(t * math.pi) + 0.004 * t
                pts.append(scalp(ph, th, off))
            widths = [w * (1 - 0.88 * ((i / (n - 1)) ** 2.2)) for i in range(n)]
            thick = [0.008 * (1 - 0.5 * i / (n - 1)) for i in range(n)]
            add(*ribbon(pts, widths, thick, lambda i, pts=pts: (pts[i] - HEAD_C).normalized()))
    strands_obj = mesh_obj('kaira_hair', V, F, UV)
    # --- calota sobre o crânio (linha do cabelo: testa, acima das orelhas, nuca)
    rows, cols = 14, 48
    cv, cf, cuv = [], [], []
    for j in range(rows + 1):
        for i in range(cols):
            phi = 360 * i / cols
            c = math.cos(math.radians(phi))
            th_min = (52 if c > 0.5 else 22) * max(c, 0) + (-46) * max(-c, 0) + 6 * (1 - abs(c))
            th = th_min + (90 - th_min) * j / rows
            cv.append(tuple(scalp(phi, th, 0.009 + 0.004 * j / rows)))
            cuv.append((i / cols, j / rows))
    for j in range(rows):
        for i in range(cols):
            a_ = j * cols + i; b_ = j * cols + (i + 1) % cols
            cf.append((a_, b_, b_ + cols, a_ + cols))
    cap = mesh_obj('kaira_hair_cap', cv, cf, cuv)
    # --- normais suavizadas: o cabelo sombreia como uma massa só (alto da cabeça = esfera; queda = cilindro)
    for obj in (strands_obj, cap):
        me = obj.data; ns = []
        for v in me.vertices:
            sph = (v.co - HEAD_C).normalized()
            cyl = Vector((v.co.x, v.co.y - 0.02, 0.0)); cyl = (cyl.normalized() if cyl.length > 1e-4 else Vector((0, 1, 0))) + Vector((0, 0, 0.25))
            w = min(1.0, max(0.0, (v.co.z - 1.45) / 0.12))
            n = cyl.normalized().lerp(sph, w).normalized()
            ns.append(tuple(n.lerp(v.normal, 0.2).normalized()))
        me.normals_split_custom_set_from_vertices(ns)
    # --- cor por vértice: raiz mais escura, pontas claras, faixa de brilho em halo no alto da cabeça
    base_c, dark_c, light_c = np.array(hexc(HAIR)[:3]), np.array(hexc(HAIR_DARK)[:3]), np.array(hexc(HAIR_LIGHT)[:3])
    for obj in (strands_obj, cap):
        me = obj.data
        col = me.color_attributes.new('Col', 'FLOAT_COLOR', 'POINT')
        for v in me.vertices:
            z = v.co.z
            c = base_c.copy()
            if z < 1.3: c = base_c + (light_c - base_c) * min(1.0, (1.3 - z) / 0.7) * 0.75
            rel = (v.co - HEAD_C)
            if z > 1.55 and rel.length < 0.105: c = c * 0.86 + dark_c * 0.14
            halo = math.exp(-((z - 1.725) / 0.012) ** 2) * (1.0 if rel.y > -0.06 else 0.6)
            c = c + (np.array([1.0, 0.86, 0.92]) - c) * 0.55 * halo
            col.data[v.index].color = (*[float(x) ** 2.2 for x in c], 1.0)
    return [strands_obj, cap]

def hair_texture(S=256):
    """Fios: listras finas ao longo do comprimento (multiplica a cor por vértice)."""
    rnd = np.random.default_rng(3)
    u = np.linspace(0, 1, S, endpoint=False)
    stripes = np.ones(S)
    for _ in range(26):
        c = rnd.uniform(0, 1); w = rnd.uniform(0.004, 0.012); a = rnd.uniform(0.06, 0.16)
        stripes -= a * np.exp(-((((u - c) + 0.5) % 1 - 0.5) / w) ** 2)
    img = np.ones((S, S, 4), np.float32)
    img[..., :3] = np.clip(stripes, 0.7, 1.0)[None, :, None]
    return img

# ================================================================ VESTIDO, MANGAS, JOIAS
def dress_texture(S=1024):
    """Atlas do vestido: faixa de cima (v 0..0.3) = corpete; resto = saia. Pérola com bordado dourado."""
    SS = 2; W = S * SS
    base_rgb = np.array([int(c * 255) for c in hexc(DRESS)[:3]])
    img = Image.new('RGBA', (W, W), tuple(base_rgb) + (255,))
    # sombreado vertical suave (pregas) só na saia
    arr = np.asarray(img).astype(np.float32)
    u = np.linspace(0, 1, W)
    folds = 1 - 0.05 * (0.5 + 0.5 * np.sin(u * 2 * np.pi * 9)) - 0.02 * (0.5 + 0.5 * np.sin(u * 2 * np.pi * 23 + 1))
    arr[int(0.3 * W):, :, :3] *= folds[None, :, None]
    img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(img, 'RGBA')
    gold = (214, 168, 78, 255); gold2 = (236, 196, 110, 255)
    def vy(v): return v * W
    def vine(x0, y0, y1, amp, leaves=True, width=3):
        pts = []
        for i in range(60):
            t = i / 59; y = y0 + (y1 - y0) * t
            pts.append((x0 + amp * math.sin(t * 6.0), y))
        d.line(pts, fill=gold, width=width * SS, joint='curve')
        if leaves:
            for i in range(4, 60, 7):
                x, y = pts[i]; sgn = 1 if (i // 7) % 2 else -1
                leaf = [(x, y), (x + sgn * 10 * SS, y - 9 * SS), (x + sgn * 22 * SS, y - 6 * SS), (x + sgn * 10 * SS, y + 1 * SS)]
                d.polygon(leaf, fill=gold2)
    # saia: 12 trepadeiras verticais, mais densas em cima
    for k in range(12):
        x = (k + 0.5) / 12 * W
        vine(x, vy(0.30), vy(0.30 + 0.70 * (0.55 if k % 2 else 0.80)), 7 * SS)
    # barra dourada no fim da saia
    d.rectangle([0, vy(0.965), W, vy(0.975)], fill=gold)
    d.rectangle([0, vy(0.985), W, vy(0.990)], fill=gold)
    for k in range(48):
        x = (k + 0.5) / 48 * W; y = vy(0.978)
        d.polygon([(x - 10 * SS, y), (x, y - 5 * SS), (x + 10 * SS, y), (x, y + 5 * SS)], fill=gold2)
    # bordas da fenda (as pontas do anel aberto da saia: u = 0 e u = 1)
    for x in (4 * SS, W - 4 * SS):
        d.line([(x, vy(0.30)), (x, vy(0.99))], fill=gold, width=5 * SS)
    # corpete: linhas em V do busto até a cintura (frente = u 0,5) e faixa no alto e embaixo
    for k, off in enumerate((0.05, 0.085, 0.12)):
        for sgn in (1, -1):
            d.line([(W * (0.5 + sgn * off), vy(0.02)), (W * (0.5 + sgn * off * 0.25), vy(0.27))], fill=gold, width=3 * SS)
    d.rectangle([0, vy(0.0), W, vy(0.012)], fill=gold)
    d.rectangle([0, vy(0.282), W, vy(0.30)], fill=gold)
    img = img.resize((S, S), Image.LANCZOS)
    img.save(os.path.join(OUT, 'tx_kaira_dress_col.png'))
    return np.asarray(img).astype(np.float32) / 255.0

def neckline(x, y):
    """altura da borda de cima do corpete: decote em coração, mais baixo nas costas."""
    if y > 0.03: return 1.245
    ax = abs(x)
    return 1.262 + 0.030 * math.exp(-((ax - 0.072) / 0.036) ** 2)

def build_bodice(body):
    """Corpete = cópia da pele do tronco, afastada 6 mm, com espessura. Herda os pesos do corpo."""
    me = body.data.copy(); obj = lib.link(bpy.data.objects.new('kaira_bodice', me))
    for g in body.vertex_groups: obj.vertex_groups.new(name=g.name)
    bm = bmesh.new(); bm.from_mesh(me)
    arms = [arm_pts(1), arm_pts(-1)]
    def is_arm(c):
        for sh, el, wr, d in arms:
            if lib.seg_dist(c, sh - d * 0.03, wr) < 0.075 and abs(c.x) > 0.13: return True
        return False
    kill = [f for f in bm.faces if not (0.95 < f.calc_center_median().z < neckline(f.calc_center_median().x, f.calc_center_median().y)) or is_arm(f.calc_center_median()) or abs(f.calc_center_median().x) > 0.24]
    bmesh.ops.delete(bm, geom=kill, context='FACES')
    bm.normal_update()
    for v in bm.verts: v.co += v.normal * 0.006
    bm.to_mesh(me); bm.free()
    # UV cilíndrico na faixa de cima do atlas
    uvl = me.uv_layers.new(name='UVMap')
    for poly in me.polygons:
        for li, vi in zip(poly.loop_indices, poly.vertices):
            co = me.vertices[vi].co
            uvl.data[li].uv = ((math.atan2(co.x, -co.y) / (2 * math.pi)) % 1.0, 1 - (1.29 - co.z) / 0.45 * 0.30)
    sol = obj.modifiers.new('sol', 'SOLIDIFY'); sol.thickness = 0.004; sol.offset = 1
    apply_mods(obj)
    return obj

SKIRT = [(1.00, 0.150, 0.110, 0.125), (0.95, 0.190, 0.135, 0.165), (0.86, 0.205, 0.160, 0.185), (0.74, 0.220, 0.185, 0.200), (0.55, 0.238, 0.215, 0.228),
         (0.35, 0.260, 0.240, 0.250), (0.15, 0.285, 0.262, 0.275), (0.02, 0.305, 0.282, 0.295)]
def skirt_r(z, phi, scale=1.0):
    for i in range(len(SKIRT) - 1):
        z0, *r0 = SKIRT[i]; z1, *r1 = SKIRT[i + 1]
        if z1 <= z <= z0:
            t = (z0 - z) / (z0 - z1); rx, rf, rb = [a + (b - a) * t for a, b in zip(r0, r1)]; break
    else: rx, rf, rb = SKIRT[-1][1:]
    ph = math.radians(phi); ry = rf if math.cos(ph) > 0 else rb
    return scale / math.sqrt((math.sin(ph) / rx) ** 2 + (math.cos(ph) / ry) ** 2)

def build_skirt():
    """Saia em A com pregas e fenda na frente da perna direita (anel aberto que se abre para baixo)."""
    NU, NV = 56, 22
    SLIT_PHI, SLIT_TOP = -32.0, 0.80
    rings = []
    for j in range(NV + 1):
        t = j / NV; z = 1.00 + (0.02 - 1.00) * t
        gap = 0.0 if z > SLIT_TOP else 46.0 * ((SLIT_TOP - z) / SLIT_TOP) ** 0.8
        ring = []
        for i in range(NU + 1):
            u = i / NU
            phi = SLIT_PHI + gap / 2 + u * (360 - gap)
            r = skirt_r(z, phi)
            r *= 1 + 0.035 * t * math.sin(math.radians(phi) * 9) + 0.012 * t * math.sin(math.radians(phi) * 23)
            zz = z - 0.012 * t * (0.5 + 0.5 * math.sin(math.radians(phi) * 5))      # barra levemente irregular
            ph = math.radians(phi)
            ring.append((r * math.sin(ph), -r * math.cos(ph), zz))
        rings.append(ring)
    v, f, uv = loft(rings, closed=False)
    uv = [(a_, 1 - (0.30 + 0.70 * b_)) for a_, b_ in uv]
    sk = mesh_obj('kaira_skirt', v, f, uv)
    sol = sk.modifiers.new('sol', 'SOLIDIFY'); sol.thickness = 0.004; sol.offset = -1
    apply_mods(sk)
    # saia de baixo, verde-sálvia (aparece pela fenda e atrás)
    rings = []
    for j in range(13):
        t = j / 12; z = 0.86 + (0.03 - 0.86) * t
        rings.append([(skirt_r(z, 360 * i / 36, 0.95) * math.sin(math.radians(360 * i / 36)), -skirt_r(z, 360 * i / 36, 0.95) * math.cos(math.radians(360 * i / 36)), z) for i in range(36)])
    v, f, uv = loft(rings, closed=True)
    under = mesh_obj('kaira_underskirt', v, f, uv)
    return sk, under

def build_sleeve(side):
    """Manga em sino translúcida: envolve o braço do bracelete ao pulso e cai num drapeado longo por baixo."""
    sh, el, wr, d = arm_pts(side)
    a0 = sh + d * UPPER * 0.42
    L = (wr - a0).length + 0.06
    upv = Vector((0, 0, 1)); upv = (upv - d * upv.dot(d)).normalized(); sidev = d.cross(upv).normalized()
    NU, NV = 26, 16
    rings = []
    for j in range(NV + 1):
        a = j / NV
        r = 0.052 + 0.085 * a ** 1.1
        ring = []
        for i in range(NU + 1):
            th = 2 * math.pi * i / NU
            dirv = upv * math.cos(th) + sidev * math.sin(th)
            p = a0 + d * L * a + dirv * r
            down = max(0.0, -math.cos(th))
            p.z -= 0.80 * a ** 0.85 * down ** 1.5                    # drapeado caindo
            p += Vector((0.05 * side, 0.02, 0)) * a * down             # um pouco para fora do corpo
            ring.append(tuple(p))
        rings.append(ring)
    v, f, uv = loft(rings, closed=False)
    return mesh_obj('kaira_sleeve_' + ('l' if side > 0 else 'r'), v, f, uv)

def sleeve_texture(S=256):
    img = np.zeros((S, S, 4), np.float32)
    c = np.array(hexc(SLEEVE)[:3]); g = np.array(hexc(GOLD)[:3])
    img[..., :3] = c; img[..., 3] = 1
    img[int(S * 0.94):int(S * 0.97), :, :3] = g                       # barra dourada
    img[:int(S * 0.04), :, :3] = g
    u = np.linspace(0, 1, S)
    img[:, :, :3] *= (1 - 0.07 * (0.5 + 0.5 * np.sin(u * 2 * np.pi * 7)))[None, :, None]
    return img

def tube(path, r, N=8, closed_path=False):
    pts = list(path) + ([path[0]] if closed_path else [])
    rings = []
    for i, p in enumerate(pts):
        t_ = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
        a = t_.cross(Vector((0, 0, 1)) if abs(t_.z) < 0.9 else Vector((1, 0, 0))).normalized(); b = t_.cross(a)
        rings.append([tuple(p + (a * math.cos(2 * math.pi * k / N) + b * math.sin(2 * math.pi * k / N)) * r) for k in range(N)])
    return loft(rings, closed=True)

def merge(parts):
    V, F, UV = [], [], []
    for v, f, uv in parts:
        o = len(V); V.extend(v); UV.extend(uv); F.extend([tuple(i + o for i in fc) for fc in f])
    return V, F, UV

def flower(center, normal, R, petals=5, depth=0.003):
    """Flor achatada de ouro (pétalas pontudas), virada para 'normal'."""
    n = normal.normalized(); a = n.cross(Vector((0, 0, 1)) if abs(n.z) < 0.9 else Vector((1, 0, 0))).normalized(); b = n.cross(a)
    V = [tuple(center + n * depth)]; F = []
    M = petals * 4
    for i in range(M):
        ang = 2 * math.pi * i / M
        rr = R * (1.0 if i % 4 == 0 else 0.55 if i % 2 == 0 else 0.42)
        V.append(tuple(center + (a * math.cos(ang) + b * math.sin(ang)) * rr))
    for i in range(M): F.append((0, 1 + i, 1 + (i + 1) % M))
    V.append(tuple(center - n * depth)); bi = len(V) - 1
    for i in range(M): F.append((bi, 1 + (i + 1) % M, 1 + i))
    return V, F, [(0.5, 0.5)] * len(V)

def gem_drop(top, size):
    V, F = [], []
    N = 8
    V.append(tuple(top))
    for i in range(N):
        a = 2 * math.pi * i / N; V.append(tuple(top + Vector((math.cos(a) * size * 0.55, math.sin(a) * size * 0.35, -size * 0.45))))
    V.append(tuple(top + Vector((0, 0, -size * 1.4))))
    for i in range(N):
        F.append((0, 1 + i, 1 + (i + 1) % N)); F.append((N + 1, 1 + (i + 1) % N, 1 + i))
    return V, F, [(0.5, 0.5)] * len(V)

def build_jewelry():
    gold, gems = [], []
    # tiara: faixa atrás da cabeça + flor na nuca
    path = [scalp(ph, 6 + 4 * math.cos(math.radians(ph - 180)), 0.017) for ph in np.linspace(96, 264, 30)]
    gold.append(tube(path, 0.0028))
    back = scalp(180, 4, 0.020)
    gold.append(flower(back, Vector((0, 1, 0.1)), 0.024, 6, 0.004))
    for s in (1, -1):
        gold.append(flower(scalp(180 + 20 * s, 2, 0.019), Vector((0.35 * s, 1, 0)), 0.012, 4, 0.003))
    gems.append(gem_drop(back + Vector((0, 0.006, 0.004)), 0.008))
    # brincos: corrente com pedra rosa, pendurados do lóbulo
    for s in (1, -1):
        ear = HEAD_C + Vector((0.080 * s, 0.006, -0.020))
        chain = [ear + Vector((0.004 * s, 0, -0.012 * i)) for i in range(5)]
        gold.append(tube(chain, 0.0016, 6))
        gems.append(gem_drop(chain[-1], 0.007))
    # colar: gargantilha + duas correntes em V até o pingente
    neck_path = [Vector((0.0545 * math.sin(math.radians(a)), 0.0184 - 0.0505 * math.cos(math.radians(a)), 1.468 - 0.006 * math.cos(math.radians(a)))) for a in np.linspace(0, 360, 33)[:-1]]
    gold.append(tube(neck_path, 0.0026, 8, closed_path=True))
    pend = Vector((0, -0.088, 1.355))
    for s in (1, -1):
        p0 = Vector((0.040 * s, -0.016, 1.460))
        ctrl = Vector((0.035 * s, -0.080, 1.40))
        chain = [(p0 * (1 - t) ** 2 + ctrl * 2 * t * (1 - t) + pend * t * t) for t in np.linspace(0, 1, 14)]
        gold.append(tube(chain, 0.0016, 6))
    gold.append(flower(pend + Vector((0, -0.004, 0.006)), Vector((0, -1, 0.15)), 0.014, 5, 0.003))
    gems.append(gem_drop(pend + Vector((0, -0.006, 0.0)), 0.016))
    # braceletes no braço (com flor) e pulseiras
    for s in (1, -1):
        sh, el, wr, d = arm_pts(s)
        for c, r, w in ((sh + d * UPPER * 0.42, 0.045, 0.004), (wr - d * 0.02, 0.027, 0.003)):
            up = Vector((0, 0, 1)); up = (up - d * up.dot(d)).normalized(); sd = d.cross(up)
            ring = [c + (up * math.cos(a) + sd * math.sin(a)) * r for a in np.linspace(0, 2 * math.pi, 25)[:-1]]
            gold.append(tube(ring, w, 6, closed_path=True))
        c = sh + d * UPPER * 0.42; out = Vector((s, 0, 0.6)).normalized()
        gold.append(flower(c + out * 0.047, out, 0.018, 5, 0.003))
    # cinto fino na cintura
    belt = [Vector((skirt_r(1.075, a, 1.0) * 0 + 0.118 * math.sin(math.radians(a)) * 1.05, -0.088 * math.cos(math.radians(a)) * 1.08 + 0.008, 1.075)) for a in np.linspace(0, 360, 41)[:-1]]
    gold.append(tube(belt, 0.004, 6, closed_path=True))
    # sandálias: tiras subindo pela canela, tira no peito do pé e salto fino
    for s in (1, -1):
        an = ANKLE_L if s > 0 else mirror(ANKLE_L)
        for z, r in ((0.12, 0.036), (0.19, 0.040), (0.26, 0.044)):
            c = Vector((an.x, an.y + 0.006, z))
            gold.append(tube([c + Vector((r * math.cos(a), r * 0.95 * math.sin(a), 0)) for a in np.linspace(0, 2 * math.pi, 17)[:-1]], 0.0028, 6, closed_path=True))
        for z0, z1 in ((0.12, 0.19), (0.19, 0.26)):          # tiras cruzadas na frente
            gold.append(tube([Vector((an.x - 0.03 * s, an.y - 0.03, z0)), Vector((an.x + 0.03 * s, an.y - 0.035, z1))], 0.0024, 6))
            gold.append(tube([Vector((an.x + 0.03 * s, an.y - 0.03, z0)), Vector((an.x - 0.03 * s, an.y - 0.035, z1))], 0.0024, 6))
        foot = [Vector((an.x + 0.030 * math.cos(a), -0.065 + 0.012 * math.sin(a), 0.040 + 0.016 * max(0, math.sin(a)))) for a in np.linspace(0, math.pi, 9)]
        gold.append(tube(foot, 0.003, 6))
        heel = [Vector((an.x, an.y + 0.035, 0.065)), Vector((an.x, an.y + 0.042, 0.0))]
        gold.append(tube(heel, 0.006, 8))
        sole = [Vector((an.x, an.y + 0.03, 0.068)), Vector((an.x, -0.02, 0.040)), Vector((an.x, -0.09, 0.012)), Vector((an.x, -0.13, 0.006))]
        gold.append(tube(sole, 0.012, 6))
    g = mesh_obj('kaira_jewelry', *merge(gold))
    gm = mesh_obj('kaira_gems', *merge(gems), smooth=False)
    return g, gm

# ================================================================ ESQUELETO
def build_rig():
    arm_data = bpy.data.armatures.new('kaira_rig')
    arm = lib.link(bpy.data.objects.new('kaira_rig', arm_data))
    activate(arm); bpy.ops.object.mode_set(mode='EDIT')
    eb = arm_data.edit_bones
    def bone(name, head, tail, parent=None, connect=False, deform=True):
        b = eb.new(name); b.head = Vector(head); b.tail = Vector(tail)
        if parent: b.parent = eb[parent]; b.use_connect = connect
        b.use_deform = deform
        return b
    bone('Hips', (0, 0.005, 0.93), (0, 0.006, 1.02))
    bone('Spine', (0, 0.006, 1.02), (0, 0.006, 1.13), 'Hips', True)
    bone('Spine1', (0, 0.006, 1.13), (0, 0.003, 1.26), 'Spine', True)
    bone('Spine2', (0, 0.003, 1.26), (0, 0.016, 1.42), 'Spine1', True)
    bone('Neck', (0, 0.020, 1.43), (0, 0.020, 1.53), 'Spine2')
    bone('Head', (0, 0.020, 1.53), (0, 0.020, 1.76), 'Neck', True)
    for s, P in ((1, 'Left'), (-1, 'Right')):
        sh, el, wr, d = arm_pts(s)
        bone(P + 'Shoulder', (0.025 * s, 0.006, 1.40), sh, 'Spine2')
        bone(P + 'Arm', sh, el, P + 'Shoulder', True)
        bone(P + 'ForeArm', el, wr, P + 'Arm', True)
        bone(P + 'Hand', wr, wr + d * 0.085, P + 'ForeArm', True)
        kn = wr + d * 0.092
        bone(P + 'HandIndex1', kn + Vector((0, -0.021, 0)), kn + Vector((0, -0.021, 0)) + d * 0.022, P + 'Hand')
        bone(P + 'HandIndex2', kn + Vector((0, -0.021, 0)) + d * 0.022, kn + Vector((-0.010 * s, -0.021, 0)) + d * 0.042, P + 'HandIndex1', True)
        bone(P + 'HandFingers1', kn + Vector((0, 0.004, 0)), kn + Vector((0, 0.004, 0)) + d * 0.025, P + 'Hand')
        bone(P + 'HandFingers2', kn + Vector((0, 0.004, 0)) + d * 0.025, kn + Vector((-0.010 * s, 0.004, 0)) + d * 0.046, P + 'HandFingers1', True)
        t0 = wr + d * 0.03 + Vector((-0.010 * s, -0.022, 0)); t1 = wr + d * 0.055 + Vector((-0.016 * s, -0.038, 0)); t2 = wr + d * 0.077 + Vector((-0.018 * s, -0.049, 0))
        bone(P + 'HandThumb1', t0, t1, P + 'Hand')
        bone(P + 'HandThumb2', t1, t2, P + 'HandThumb1', True)
        hp = HIP_L if s > 0 else mirror(HIP_L); kn_ = KNEE_L if s > 0 else mirror(KNEE_L); an = ANKLE_L if s > 0 else mirror(ANKLE_L)
        bone(P + 'UpLeg', hp, kn_, 'Hips')
        bone(P + 'Leg', kn_, an, P + 'UpLeg', True)
        bone(P + 'Foot', an, Vector((an.x, -0.085, 0.022)), P + 'Leg', True)
        bone(P + 'ToeBase', Vector((an.x, -0.085, 0.022)), Vector((an.x, -0.14, 0.014)), P + 'Foot', True)
        # véu da manga: pendurado do braço, cai reto
        a0 = sh + d * UPPER * 0.42
        bone(P + 'Sleeve1', a0, a0 + Vector((0.03 * s, 0.02, -0.30)), P + 'Arm')
        bone(P + 'Sleeve2', a0 + Vector((0.03 * s, 0.02, -0.30)), a0 + Vector((0.06 * s, 0.03, -0.62)), P + 'Sleeve1', True)
        bone(P + 'Sleeve3', a0 + Vector((0.06 * s, 0.03, -0.62)), a0 + Vector((0.08 * s, 0.04, -0.98)), P + 'Sleeve2', True)
        bone(P + 'Earring', HEAD_C + Vector((0.082 * s, 0.004, -0.018)), HEAD_C + Vector((0.084 * s, 0.004, -0.07)), 'Head')
        # mecha frontal (por cima do ombro)
        pf = [Vector((0.070 * s, -0.030, 1.62)), Vector((0.105 * s, -0.050, 1.42)), Vector((0.120 * s, -0.075, 1.24)), Vector((0.120 * s, -0.085, 1.06)), Vector((0.115 * s, -0.085, 0.90))]
        for i in range(4):
            bone(f'{P}HairFront{i + 1}', pf[i], pf[i + 1], 'Head' if i == 0 else f'{P}HairFront{i}', i > 0)
    # cabelo de trás: três correntes até os joelhos
    for tag, x in (('C', 0.0), ('L', 0.075), ('R', -0.075)):
        pts = [Vector((x * 0.6, 0.095, 1.64)), Vector((x, 0.125, 1.45)), Vector((x * 1.05, 0.115, 1.22)), Vector((x * 1.1, 0.120, 0.98)), Vector((x * 1.1, 0.130, 0.76)), Vector((x * 1.1, 0.14, 0.54))]
        for i in range(5):
            bone(f'HairBack{tag}{i + 1}', pts[i], pts[i + 1], 'Head' if i == 0 else f'HairBack{tag}{i}', i > 0)
    # saia: quatro correntes (frente, trás, lados)
    for tag, dx, dy in (('F', 0, -1), ('B', 0, 1), ('L', 1, 0), ('R', -1, 0)):
        r0, r1 = 0.15, 0.30
        pts = [Vector((dx * r0, dy * 0.11 + 0.005, 1.0)), Vector((dx * 0.19, dy * 0.16, 0.70)), Vector((dx * 0.24, dy * 0.21, 0.38)), Vector((dx * r1, dy * 0.27, 0.04))]
        for i in range(3):
            bone(f'Skirt{tag}{i + 1}', pts[i], pts[i + 1], 'Hips' if i == 0 else f'Skirt{tag}{i}', i > 0)
    # pontos de ancoragem (não deformam)
    sh, el, wr, d = arm_pts(-1)
    bone('socket_hand_r', wr + d * 0.06, wr + d * 0.12, 'RightHand', deform=False)
    sh, el, wr, d = arm_pts(1)
    bone('socket_hand_l', wr + d * 0.06, wr + d * 0.12, 'LeftHand', deform=False)
    bone('socket_back', (0, 0.12, 1.30), (0, 0.12, 1.42), 'Spine2', deform=False)
    bone('socket_head', (0, 0.02, 1.78), (0, 0.02, 1.84), 'Head', deform=False)
    bpy.ops.object.mode_set(mode='OBJECT')
    return arm

BODY_BONES = ['Hips', 'Spine', 'Spine1', 'Spine2', 'Neck', 'Head'] + [p + n for p in ('Left', 'Right') for n in (
    'Shoulder', 'Arm', 'ForeArm', 'Hand', 'HandIndex1', 'HandIndex2', 'HandFingers1', 'HandFingers2', 'HandThumb1', 'HandThumb2',
    'UpLeg', 'Leg', 'Foot', 'ToeBase')]

def skin_body(body, arm):
    """Pesos automáticos (calor dos ossos) só com os ossos do corpo."""
    saved = {}
    for b in arm.data.bones:
        saved[b.name] = b.use_deform
        b.use_deform = b.name in BODY_BONES
    for o in bpy.context.scene.objects: o.select_set(False)
    body.select_set(True); arm.select_set(True)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.parent_set(type='ARMATURE_AUTO')
    for n, v in saved.items(): arm.data.bones[n].use_deform = v
    lib.limit_and_normalize(body, 4)


# ================================================================ ANIMAÇÕES (por chaves, geradas por funções)
X, Y, Z = (1, 0, 0), (0, 1, 0), (0, 0, 1)
FPS = 30
TAU = 2 * math.pi
LOWER = 38          # quanto os braços descem a partir da A-pose

def mirror_rots(rots, s):
    """espelha para o lado direito: rotações em Y e Z trocam de sinal."""
    return [(ax, deg * (s if ax != X else 1)) for ax, deg in rots]

class Pose:
    def __init__(self): self.r = {}; self.loc = {}
    def add(self, bone, *rots): self.r.setdefault(bone, []).extend(rots); return self
    def side(self, s, bone, *rots):
        P = 'Left' if s > 0 else 'Right'
        return self.add(P + bone, *mirror_rots(rots, s))
    def move(self, bone, v): self.loc[bone] = Vector(v); return self

SLEEVE_K = 0.8    # quanto a manga desfaz o balanço do braço para continuar caindo reta
def base_arms(P, low=None, fwd=-4, elbow=-14, swing=(0, 0), elbow_extra=(0, 0), sleeve_sway=(0, 0)):
    if low is None: low = LOWER
    for k, s in enumerate((1, -1)):
        P.side(s, 'Arm', (Y, low), (X, fwd + swing[k]))
        P.side(s, 'ForeArm', (X, elbow + elbow_extra[k]))
        P.side(s, 'Hand', (X, -6))
        P.side(s, 'HandFingers1', (X, -18)); P.side(s, 'HandFingers2', (X, -22))
        P.side(s, 'HandIndex1', (X, -10)); P.side(s, 'HandIndex2', (X, -14))
        P.side(s, 'HandThumb1', (Z, -8))
        # o drapeado da manga continua caindo reto quando o braço desce
        P.side(s, 'Sleeve1', (Y, -low * 0.92), (X, -(fwd + swing[k]) * SLEEVE_K + sleeve_sway[k]))
        P.side(s, 'Sleeve2', (X, sleeve_sway[k] * 0.6)); P.side(s, 'Sleeve3', (X, sleeve_sway[k] * 0.4))

HAIR_K = 1.0      # amplitude do balanço do cabelo
def hair(P, t, back=0.0, amp=1.5, freq=1, side_amp=1.0):
    back *= HAIR_K; amp *= HAIR_K; side_amp *= HAIR_K
    for c, ph in (('C', 0.0), ('L', 0.11), ('R', -0.09)):
        for i in range(1, 6):
            lag = i * 0.07
            P.add(f'HairBack{c}{i}', (X, back * (0.4 + i * 0.15) + amp * math.sin(TAU * (freq * t - lag + ph))), (Y, side_amp * 0.8 * math.sin(TAU * (freq * t - lag + ph + 0.25))))
    for s in (1, -1):
        for i in range(1, 5):
            P.side(s, f'HairFront{i}', (X, back * 0.5 * i / 4 + amp * 0.8 * math.sin(TAU * (freq * t - i * 0.08))))
        P.side(s, 'Earring', (X, amp * 2 * math.sin(TAU * (freq * t - 0.2))))

SKIRT_K = 1.0     # quanto a saia acompanha as pernas (o modelo recebido usa menos: o tecido tem várias camadas)
def skirt(P, t, f=0.0, b=0.0, l=0.0, r=0.0):
    for i in (1, 2, 3):
        k = (0.5, 0.8, 1.0)[i - 1] * SKIRT_K
        P.add(f'SkirtF{i}', (X, -f * k)); P.add(f'SkirtB{i}', (X, b * k))
        P.add(f'SkirtL{i}', (X, -l * k)); P.add(f'SkirtR{i}', (X, -r * k))

def pose_idle(t):
    P = Pose(); br = math.sin(TAU * t); sw = math.sin(TAU * t + 0.6)
    base_arms(P, sleeve_sway=(1.5 * sw, -1.5 * sw))
    P.add('Hips', (Y, 1.2 * sw)).move('Hips', (0.006 * sw, 0, 0.003 * br))
    P.add('Spine', (Y, -0.8 * sw)); P.add('Spine1', (X, -1.4 * br)); P.add('Spine2', (X, -1.0 * br))
    P.add('Neck', (X, 0.6 * br)); P.add('Head', (Z, 1.8 * math.sin(TAU * t * 0.5 + 1)), (X, -1.5))
    for s in (1, -1):
        P.side(s, 'UpLeg', (Y, -1.2 * sw * s), (X, -1 if s > 0 else 2))
        P.side(s, 'Leg', (X, 2 if s > 0 else 4))
        P.side(s, 'Shoulder', (X, -0.6 * br))
    hair(P, t, back=1.0, amp=1.2)
    skirt(P, t, f=0.8 * br, b=0.6 * br)
    return P

def leg_cycle(ph, stride, knee_max, lift):
    """ângulos de coxa/joelho/pé para uma fase 0..1 (0 = calcanhar tocando à frente)."""
    thigh = -stride * math.cos(TAU * ph)
    swing = max(0.0, math.sin(TAU * (ph - 0.5)))       # fase de balanço (pé no ar)
    knee = 6 + knee_max * swing ** 1.2 + 10 * max(0.0, math.sin(TAU * ph)) * 0.3
    foot = -8 * math.cos(TAU * ph) + lift * swing
    return thigh, knee, foot

STRIDE_K = 1.0    # tamanho do passo (vestido longo e fechado pede passo curto)
def pose_locomotion(t, run=False):
    P = Pose()
    stride = (38 if run else 26) * STRIDE_K; knee_max = (85 if run else 52) * STRIDE_K; arm_sw = 34 if run else 20
    lean = -9 if run else -2; bob = 0.035 if run else 0.018
    ths = []
    for k, s in enumerate((1, -1)):
        ph = (t + (0.0 if s > 0 else 0.5)) % 1.0
        th, kn, ft = leg_cycle(ph, stride, knee_max, 20 if run else 10)
        ths.append(th)
        P.side(s, 'UpLeg', (X, th)); P.side(s, 'Leg', (X, kn)); P.side(s, 'Foot', (X, ft)); P.side(s, 'ToeBase', (X, -6 * max(0, math.cos(TAU * ph))))
    a = math.cos(TAU * t)
    base_arms(P, low=LOWER - (10 if run else 2), fwd=-6, elbow=-55 if run else -20, swing=(arm_sw * a, -arm_sw * a),
              elbow_extra=(-10 * max(0, -a), -10 * max(0, a)), sleeve_sway=(14 + 6 * a, 14 - 6 * a))
    up = math.cos(TAU * 2 * t)
    P.move('Hips', (0, 0, -bob * 0.5 + bob * 0.5 * -up))
    P.add('Hips', (Z, 6 * a), (Y, 2.5 * math.sin(TAU * t)), (X, lean * 0.4))
    P.add('Spine', (Z, -4 * a), (X, lean * 0.3)); P.add('Spine1', (Z, -3 * a), (X, lean * 0.3)); P.add('Spine2', (X, lean * 0.2))
    P.add('Neck', (Z, 2 * a)); P.add('Head', (Z, 2 * a), (X, -lean * 0.6))
    hair(P, t * 2, back=14 if run else 7, amp=3 if run else 2, freq=1, side_amp=2)
    # a saia acompanha as pernas: a de trás empurra o painel de trás, a da frente o da frente
    back = max(0.0, *ths); front = max(0.0, *(-x for x in ths))
    skirt(P, t, f=4 + front * 0.85, b=6 + back * 1.15, l=-ths[0] * 0.7, r=-ths[1] * 0.7)
    return P

def pose_cast(t):
    """conjurar: puxa a mão direita, gira o tronco e lança à frente com a palma aberta."""
    P = pose_idle(0.25)
    w = lambda a, b: max(0.0, min(1.0, (t - a) / (b - a)))
    ease = lambda x: x * x * (3 - 2 * x)
    wind = ease(w(0.0, 0.28)) * (1 - ease(w(0.30, 0.45)))
    thrust = ease(w(0.30, 0.45)) * (1 - ease(w(0.75, 1.0)))
    P = Pose(); base_arms(P, sleeve_sway=(6 * thrust, 18 * thrust))
    P.add('RightArm', (X, -22 * wind - 70 * thrust), (Y, 14 * wind + 30 * thrust))
    P.add('RightForeArm', (X, -40 * wind + 26 * thrust))
    P.add('RightHand', (X, 30 * thrust), (Z, 25 * thrust))
    P.add('LeftArm', (X, -12 * thrust), (Y, -10 * thrust))
    P.add('Spine1', (Z, 14 * wind - 10 * thrust)); P.add('Spine2', (Z, 8 * wind - 6 * thrust), (X, -4 * thrust))
    P.add('Head', (Z, -6 * wind + 4 * thrust))
    P.add('Hips', (Z, 6 * wind - 4 * thrust))
    P.side(1, 'UpLeg', (X, 4 * thrust)); P.side(-1, 'UpLeg', (X, -10 * thrust)); P.side(-1, 'Leg', (X, 8 * thrust))
    hair(P, t * 1.5, back=4 + 10 * thrust, amp=2)
    skirt(P, t, f=4 * thrust, b=8 * thrust)
    return P

def pose_hit(t):
    w = math.sin(math.pi * min(1.0, t / 0.6)) * (1 if t < 0.6 else 0) + (0 if t < 0.6 else 0)
    k = math.exp(-((t - 0.18) / 0.16) ** 2)
    P = Pose(); base_arms(P, low=LOWER - 14 * k, fwd=-4 + 16 * k, elbow=-14 - 20 * k, sleeve_sway=(-10 * k, -10 * k))
    P.add('Spine', (X, 6 * k)); P.add('Spine1', (X, 10 * k)); P.add('Spine2', (X, 6 * k)); P.add('Neck', (X, 8 * k)); P.add('Head', (X, 10 * k), (Z, 6 * k))
    P.move('Hips', (0, 0.05 * k, -0.02 * k))
    for s in (1, -1): P.side(s, 'UpLeg', (X, -8 * k)); P.side(s, 'Leg', (X, 14 * k))
    hair(P, t, back=-8 * k, amp=1)
    skirt(P, t, f=-6 * k, b=-6 * k)
    return P

def pose_death(t):
    w = lambda a, b: max(0.0, min(1.0, (t - a) / (b - a)))
    ease = lambda x: x * x * (3 - 2 * x)
    buckle = ease(w(0.0, 0.35)); fall = ease(w(0.30, 0.70))
    P = Pose(); base_arms(P, low=LOWER + 10 * fall, fwd=-4 - 30 * fall, elbow=-14 - 30 * buckle + 20 * fall, sleeve_sway=(-30 * fall, -30 * fall))
    for s in (1, -1):
        P.side(s, 'UpLeg', (X, -45 * buckle + 30 * fall), (Y, -6 * fall))
        P.side(s, 'Leg', (X, 90 * buckle - 70 * fall))
    P.add('Spine1', (X, 12 * buckle - 6 * fall)); P.add('Head', (X, 10 * buckle), (Z, 25 * fall))
    P.add('Hips', (X, 82 * fall), (Z, 10 * fall))
    P.move('Hips', (0, 0.25 * fall, -0.30 * buckle - 0.50 * fall))
    hair(P, t, back=-25 * fall, amp=0.5)
    skirt(P, t, f=-20 * fall, b=-30 * fall)
    return P

def bake(arm, name, fn, frames, loop=True, step=2):
    act = lib.new_action(arm, name)
    keys = list(range(0, frames + 1, step))
    if keys[-1] != frames: keys.append(frames)
    for f in keys:
        t = f / frames
        P = fn(t % 1.0 if loop else t)
        lib.key_pose(arm, f + 1, P.r, P.loc)
    if loop:  # o último quadro repete o primeiro: volta sem emenda
        P = fn(0.0); lib.key_pose(arm, frames + 1, P.r, P.loc)
    lib.push_nla(arm, act)
    return act

def build_animations(arm):
    bpy.context.scene.render.fps = FPS
    # todos os ossos animáveis começam no repouso em cada clipe (sem herdar pose do clipe anterior)
    bake(arm, 'idle', pose_idle, 72)
    bake(arm, 'walk', lambda t: pose_locomotion(t, False), 28)
    bake(arm, 'run', lambda t: pose_locomotion(t, True), 20)
    bake(arm, 'cast', pose_cast, 36, loop=False)
    bake(arm, 'hit', pose_hit, 18, loop=False)
    bake(arm, 'death', pose_death, 48, loop=False)

# ================================================================ MONTAGEM
def main():
    lib.reset()
    face_px = paint_face()
    skin_mat = material('pele', lin(hexc(SKIN)), ramp='anime', rim=0.35, outline=0.0032)
    face_img = lib.image_from_array('tx_kaira_face_col', face_px)
    face_mat = material('rosto', (1, 1, 1, 1), image=face_img, ramp='anime', rim=0.25, outline=0.0032)

    body = build_body(); set_material(body, skin_mat)
    head = build_head(); set_material(head, face_mat)
    ears = build_ears()
    ear_mat = material('pele_orelha', lin(hexc(SKIN)), ramp='anime', rim=0.35, outline=0.0015)
    for e in ears: set_material(e, ear_mat)
    arm = build_rig()
    skin_body(body, arm)
    for o in [head] + ears:
        lib.weight_all(o, 'Head'); lib.bind(o, arm)
    parts = [body, head] + ears
    if STAGE >= 2:
        hair_img = lib.image_from_array('tx_kaira_hair', hair_texture())
        hair_mat = material('cabelo', (1, 1, 1, 1), image=hair_img, ramp='anime', rim=0.25, spec=0.35, specSize=0.94, outline=0.0012)
        strands, cap = build_hair()
        for o in (strands, cap): set_material(o, hair_mat)
        lib.weight_all(cap, 'Head'); lib.bind(cap, arm)
        hb = ['Head'] + [f'HairBack{t}{i}' for t in 'CLR' for i in range(1, 6)] + [f'{p}HairFront{i}' for p in ('Left', 'Right') for i in range(1, 5)]
        lib.weight_by_bones(strands, arm, hb, power=4, keep=3, bias={'Head': 0.6})
        # tudo o que está colado à cabeça segue só a cabeça
        g = strands.vertex_groups
        for v in strands.data.vertices:
            if (v.co - HEAD_C).length < 0.125 and v.co.z > 1.55:
                for gr in list(v.groups): g[gr.group].remove([v.index])
                g['Head'].add([v.index], 1.0, 'REPLACE')
        lib.limit_and_normalize(strands, 4); lib.bind(strands, arm)
        parts += [strands, cap]
    if STAGE >= 3:
        dress_img = lib.image_from_array('tx_kaira_dress', dress_texture())
        dress_mat = material('vestido', (1, 1, 1, 1), image=dress_img, ramp='anime', rim=0.3, outline=0.0025)
        under_mat = material('saia_verde', lin(hexc(UNDER)), ramp='anime', rim=0.3, outline=0.002, double=True)
        sleeve_img = lib.image_from_array('tx_kaira_sleeve', sleeve_texture())
        sleeve_mat = material('manga', (1, 1, 1, 1), image=sleeve_img, alpha=0.55, double=True, ramp='anime', rim=0.5, noOutline=True)
        gold_mat = material('ouro', lin(hexc(GOLD)), ramp='anime', spec=0.9, specSize=0.88, rim=0.3, outline=0.0012, metallic=1.0, roughness=0.3)
        gem_mat = material('pedra', lin(hexc(GEM)), emission=lin(hexc(GEM)), emission_strength=0.6, ramp='soft', spec=1.0, specSize=0.85, noOutline=True)
        bodice = build_bodice(body); set_material(bodice, dress_mat)
        lib.limit_and_normalize(bodice, 4); lib.bind(bodice, arm)
        skirt, under = build_skirt(); set_material(skirt, dress_mat); set_material(under, under_mat)
        sb = ['Hips', 'LeftUpLeg', 'RightUpLeg'] + [f'Skirt{t}{i}' for t in 'FBLR' for i in (1, 2, 3)]
        for o in (skirt, under):
            lib.weight_by_bones(o, arm, sb, power=3, keep=3, bias={'Hips': 0.8, 'LeftUpLeg': 1.25, 'RightUpLeg': 1.25})
            lib.limit_and_normalize(o, 4); lib.bind(o, arm)
        sleeves = []
        for s_, P in ((1, 'Left'), (-1, 'Right')):
            sl = build_sleeve(s_); set_material(sl, sleeve_mat)
            lib.weight_by_bones(sl, arm, [P + 'Arm', P + 'ForeArm', P + 'Hand', P + 'Sleeve1', P + 'Sleeve2', P + 'Sleeve3'], power=3, keep=3, bias={P + 'ForeArm': 0.7})
            lib.limit_and_normalize(sl, 4); lib.bind(sl, arm); sleeves.append(sl)
        jew, gems = build_jewelry(); set_material(jew, gold_mat); set_material(gems, gem_mat)
        jb = ['Head', 'Neck', 'Spine2', 'Spine1', 'Spine', 'LeftArm', 'RightArm', 'LeftForeArm', 'RightForeArm', 'LeftHand', 'RightHand', 'LeftLeg', 'RightLeg', 'LeftFoot', 'RightFoot', 'LeftEarring', 'RightEarring', 'LeftToeBase', 'RightToeBase']
        for o in (jew, gems):
            lib.weight_by_bones(o, arm, jb, power=6, keep=2, bias={'LeftEarring': 0.5, 'RightEarring': 0.5})
            lib.limit_and_normalize(o, 4); lib.bind(o, arm)
        parts += [bodice, skirt, under] + sleeves + [jew, gems]
        hide_covered_skin(body)                     # depois de copiar o corpete da pele

    build_animations(arm)

    for o in parts: print(o.name, lib.tri_count(o), 'tris')
    print('total', sum(lib.tri_count(o) for o in parts))
    lib.export_glb(os.path.join(OUT, 'char_kaira_script.glb'), [arm] + parts)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT, 'fontes', 'blender', 'kaira.blend'))

if __name__ == '__main__':
    main()
