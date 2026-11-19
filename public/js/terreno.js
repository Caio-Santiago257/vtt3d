// Terreno pintável: tipos de chão por quadrado, biomas, água animada e vegetação automática.
import * as THREE from 'three';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';
import { toonSoft as toon, windify, outlineMaterial } from './gfx.js';
import { loadKit, instanceKit, kitWind } from './kit.js';

const G = 2; // unidades de mundo por quadrado

// ---------------------------------------------------------------- catálogo
export const TERRAINS = [
  { id: 'p', nome: 'Piso de pedra', cor: '#77726b' },
  { id: 'g', nome: 'Grama', cor: '#55803c' },
  { id: 'm', nome: 'Mata (árvores)', cor: '#3d6631' },
  { id: 't', nome: 'Terra', cor: '#7d5d3e' },
  { id: 'l', nome: 'Lama', cor: '#4e4233' },
  { id: 'b', nome: 'Brejo (juncos)', cor: '#47552f' },
  { id: 'a', nome: 'Água / rio', cor: '#2f6f8f' },
  { id: 's', nome: 'Areia', cor: '#d3b87d' },
  { id: 'r', nome: 'Rocha', cor: '#6c6c72' },
  { id: 'n', nome: 'Neve', cor: '#e6edf2' },
  { id: 'v', nome: 'Lava', cor: '#e2571b' },
  { id: 'e', nome: 'Estrada de pedra', cor: '#6f6d6a' },
];
const GROUND = { p: '#6a665f', g: '#62b34c', m: '#3f8f48', t: '#a0744a', l: '#5c4a38', b: '#566c30', a: '#1d4a58', s: '#ecd391', r: '#7c8090', n: '#f2f7fb', v: '#3a1409', e: '#6d6a66' };
export const TERRAIN_IDS = TERRAINS.map((t) => t.id).join('');
// quanto cada chão atrasa quem anda nele
const SLOW = { a: 0.55, l: 0.8, b: 0.75, v: 0.6, n: 0.9 };
export const DIFFICULT = new Set(['a', 'l', 'b', 'm']);

// Biomas: clima (para o jogador) + regra de preenchimento automático.
export const BIOMES = [
  { id: 'masmorra', nome: 'Masmorra', fog: 0x07070d, zenith: 0x07070d, density: 0.03, sky: 0x9aa4d0, ground: 0x1e1c2a, hemi: 0.9, sun: 0, sunColor: 0xffffff, torch: 9, far: 0x0c0c10, water: 0x49b6d8,
    part: { color: 0xffd9a0, size: 0.07, n: 60, vy: 0.03, glow: true } },
  { id: 'floresta', nome: 'Floresta', fog: 0xc4e6f2, zenith: 0x3f9bff, density: 0.011, sky: 0xe6f1ff, ground: 0x5a7a3a, hemi: 1.5, sun: 2.0, sunColor: 0xfff0cc, torch: 0, far: 0x58a646, water: 0x4fc3e8,
    part: { color: 0xfff3b8, size: 0.09, n: 110, vy: -0.08, glow: true } },
  { id: 'pantano', nome: 'Pântano', fog: 0x4f6a58, zenith: 0x2c4a52, density: 0.03, sky: 0x9fc0a0, ground: 0x2c3a26, hemi: 1.05, sun: 0.6, sunColor: 0xc8e0a8, torch: 3, far: 0x47602c, water: 0x6f9a4c,
    part: { color: 0xd2ff6a, size: 0.16, n: 90, vy: 0.0, glow: true } },
  { id: 'deserto', nome: 'Deserto', fog: 0xf3dcae, zenith: 0x58aef5, density: 0.011, sky: 0xfff4d8, ground: 0xa07a48, hemi: 1.6, sun: 2.2, sunColor: 0xfff0c8, torch: 0, far: 0xe6cd8c, water: 0x49c0d0,
    part: { color: 0xf5deb0, size: 0.05, n: 70, vy: 0.0, glow: false } },
  { id: 'neve', nome: 'Neve', fog: 0xdbe7f2, zenith: 0x8fbfee, density: 0.016, sky: 0xeef4ff, ground: 0x8a9ab0, hemi: 1.5, sun: 1.2, sunColor: 0xffffff, torch: 0, far: 0xeef4f9, water: 0x7fc0e6,
    part: { color: 0xffffff, size: 0.11, n: 260, vy: -1.3, glow: false } },
  { id: 'caverna', nome: 'Caverna', fog: 0x090812, zenith: 0x090812, density: 0.03, sky: 0x7a78a8, ground: 0x17132a, hemi: 0.7, sun: 0, sunColor: 0xffffff, torch: 10, far: 0x0b0a0d, water: 0x3aa0d8,
    part: { color: 0x7ad7ff, size: 0.11, n: 70, vy: 0.08, glow: true } },
];
export const biomeById = (id) => BIOMES.find((b) => b.id === id) || BIOMES[0];

// ---------------------------------------------------------------- ruído
function hash(x, y, s) {
  let h = (Math.imul(x, 374761393) + Math.imul(y, 668265263) + Math.imul(s, 362437)) | 0;
  h = Math.imul(h ^ (h >>> 13), 1274126177);
  return ((h ^ (h >>> 16)) >>> 0) / 4294967296;
}
function vnoise(x, y, s) {
  const xi = Math.floor(x), yi = Math.floor(y);
  let fx = x - xi, fy = y - yi;
  fx = fx * fx * (3 - 2 * fx); fy = fy * fy * (3 - 2 * fy);
  const a = hash(xi, yi, s), b = hash(xi + 1, yi, s), c = hash(xi, yi + 1, s), d = hash(xi + 1, yi + 1, s);
  return a + (b - a) * fx + (c - a) * fy + (a - b - c + d) * fx * fy;
}
const fbm = (x, y, s) => vnoise(x, y, s) * 0.6 + vnoise(x * 2.1, y * 2.1, s + 7) * 0.3 + vnoise(x * 4.3, y * 4.3, s + 13) * 0.1;
function rng(seed) {
  let a = seed >>> 0;
  return () => { a = (a + 0x6d2b79f5) >>> 0; let t = a; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
}

// ---------------------------------------------------------------- biomas prontos
// Cada bioma monta uma paisagem com forma: trilhas e estradas que cruzam o mapa, rios, lagos, clareiras para a luta e
// bordas mais fechadas. Retorna uma letra por quadrado.
function meander(r, from, to, W, H, wig = 0.22) {
  // linha sinuosa entre duas bordas: pontos de controle com desvio aleatório e suavização (em quadrados)
  const P = [], n = 7;
  for (let k = 0; k <= n; k++) {
    const t = k / n, x = from[0] + (to[0] - from[0]) * t, y = from[1] + (to[1] - from[1]) * t;
    const nx = -(to[1] - from[1]), ny = to[0] - from[0], L = Math.hypot(nx, ny) || 1;
    const off = k === 0 || k === n ? 0 : (r() - 0.5) * 2 * wig * Math.max(W, H);
    P.push([x + nx / L * off, y + ny / L * off]);
  }
  const out = [];
  for (let k = 0; k < P.length - 1; k++) {
    const p0 = P[Math.max(0, k - 1)], p1 = P[k], p2 = P[k + 1], p3 = P[Math.min(P.length - 1, k + 2)];
    for (let s = 0; s < 12; s++) {
      const t = s / 12, t2 = t * t, t3 = t2 * t;
      out.push([0, 1].map((i) => 0.5 * (2 * p1[i] + (-p0[i] + p2[i]) * t + (2 * p0[i] - 5 * p1[i] + 4 * p2[i] - p3[i]) * t2 + (-p0[i] + 3 * p1[i] - 3 * p2[i] + p3[i]) * t3)));
    }
  }
  out.push(P[P.length - 1]);
  return out;
}
function distField(W, H, lines) {
  const D = new Float32Array(W * H).fill(1e9);
  for (const L of lines) for (let j = 0; j < H; j++) for (let i = 0; i < W; i++) {
    const x = i + 0.5, y = j + 0.5; let best = D[j * W + i];
    for (let k = 0; k < L.length - 1; k++) {
      const [ax, ay] = L[k], [bx, by] = L[k + 1], vx = bx - ax, vy = by - ay;
      const t = Math.max(0, Math.min(1, ((x - ax) * vx + (y - ay) * vy) / (vx * vx + vy * vy || 1)));
      const d = Math.hypot(x - ax - vx * t, y - ay - vy * t); if (d < best) best = d;
    }
    D[j * W + i] = best;
  }
  return D;
}
const edgePt = (r, side, W, H) => side === 0 ? [0, H * (0.25 + r() * 0.5)] : side === 1 ? [W, H * (0.25 + r() * 0.5)] : side === 2 ? [W * (0.25 + r() * 0.5), 0] : [W * (0.25 + r() * 0.5), H];

export function generateBiome(id, W, H, seed = 1) {
  const r = rng(seed), N = W * H, out = new Array(N).fill('p');
  const nz = (i, j, sc, s = 0) => fbm(i / sc, j / sc, seed + s);
  const cx = W / 2, cy = H / 2, S = Math.min(W, H);
  const dc = (i, j) => Math.hypot((i + 0.5 - cx) / (W / 2), (j + 0.5 - cy) / (H / 2));   // 0 no centro, 1 na borda
  const horiz = W >= H;
  const across = () => horiz ? [edgePt(r, 0, W, H), edgePt(r, 1, W, H)] : [edgePt(r, 2, W, H), edgePt(r, 3, W, H)];
  const down = () => horiz ? [edgePt(r, 2, W, H), edgePt(r, 3, W, H)] : [edgePt(r, 0, W, H), edgePt(r, 1, W, H)];
  if (id === 'masmorra') return out.join('');

  if (id === 'estrada') {
    // estrada de lajes cruzando a mata de ponta a ponta, às vezes com uma segunda estrada que cruza (encruzilhada);
    // beiras de terra, uma clareira em volta do cruzamento, clareirinhas na mata e poças
    const [a, b] = across(); const main = meander(r, a, b, W, H, 0.12);
    const lines = [main], cross = r() < 0.7;
    let jx = cx, jy = cy;
    if (cross) { const m = main[Math.floor(main.length * (0.4 + r() * 0.2))]; jx = m[0]; jy = m[1]; const [c] = down(); lines.push(meander(r, c, [jx, jy], W, H, 0.08)); }
    const D = distField(W, H, lines);
    const half = Math.max(1.0, Math.min(1.7, S / 18));
    for (let j = 0; j < H; j++) for (let i = 0; i < W; i++) {
      const k = j * W + i, d = D[k] + (nz(i, j, 3, 5) - 0.5) * 0.9;
      const dj = Math.hypot(i + 0.5 - jx, j + 0.5 - jy), clear = dj < S * 0.24 + nz(i, j, 4, 9) * 3;
      const glade = nz(i, j, 7, 3) > 0.66;
      let c = 'm';
      if (d < half) c = 'e';
      else if (d < half + 1.1) c = r() < 0.75 ? 't' : 'g';
      else if (clear || glade || d < half + 2.2) c = 'g';
      if (c === 'g' && nz(i, j, 2.2, 11) > 0.78 && d > half + 1.5) c = 'a';
      if (c === 'e' && nz(i, j, 2.5, 13) > 0.8) c = 't';                    // lajes arrancadas
      out[k] = c;
    }
    return out.join('');
  }
  if (id === 'floresta') {
    // mata com uma trilha de terra e um riacho; clareira no meio para a luta; bordas mais fechadas
    const trail = meander(r, ...across(), W, H, 0.2), river = meander(r, ...down(), W, H, 0.18);
    const T = distField(W, H, [trail]), R = distField(W, H, [river]);
    const bend = 0.7 + r() * 0.6;
    for (let j = 0; j < H; j++) for (let i = 0; i < W; i++) {
      const k = j * W + i, n = nz(i, j, 6), e = dc(i, j);
      let c = n + e * 0.35 > 0.62 ? 'm' : nz(i, j, 3.5, 50) > 0.72 ? 't' : 'g';
      if (e < 0.35 * bend && c === 'm') c = 'g';
      if (R[k] < 1.0 + nz(i, j, 3, 7) * 0.8) c = 'a';
      else if (R[k] < 2.0) c = r() < 0.4 ? 'b' : 'g';
      if (T[k] < 0.9 && c !== 'a') c = 't';
      out[k] = c;
    }
    return out.join('');
  }
  if (id === 'pantano' || id === 'covil') {
    // canais de água parada, margens de lama, ilhas de brejo e mata alagada
    const A = distField(W, H, [meander(r, ...across(), W, H, 0.3), meander(r, ...down(), W, H, 0.3)]);
    for (let j = 0; j < H; j++) for (let i = 0; i < W; i++) {
      const k = j * W + i, n = nz(i, j, 6), n2 = nz(i, j, 3.5, 50), w = A[k] - n * 2.2;
      let c = w < 0.2 ? 'a' : w < 1.2 ? 'l' : n2 > 0.6 ? 'b' : n2 < 0.34 ? 'm' : 'g';
      if (n < 0.22) c = 'a'; else if (n < 0.27 && c !== 'a') c = 'l';
      out[k] = c;
    }
    return out.join('');
  }
  if (id === 'deserto') {
    // dunas de areia, mesas de rocha, um leito seco de rio e um oásis
    const bed = distField(W, H, [meander(r, ...across(), W, H, 0.25)]);
    const ox = W * (0.2 + r() * 0.6), oy = H * (0.2 + r() * 0.6), orad = Math.max(2, S * 0.09);
    for (let j = 0; j < H; j++) for (let i = 0; i < W; i++) {
      const k = j * W + i, n = nz(i, j, 6), d = Math.hypot(i + 0.5 - ox, j + 0.5 - oy) - nz(i, j, 2.5, 4) * 1.4;
      let c = n > 0.67 ? 'r' : bed[k] < 1.3 + nz(i, j, 3, 8) ? 't' : 's';
      if (d < orad) c = 'a'; else if (d < orad + 1.6) c = 'g'; else if (d < orad + 2.6 && r() < 0.5) c = 'm';
      out[k] = c;
    }
    return out.join('');
  }
  if (id === 'neve') {
    // campo nevado com um lago congelado, bosques de pinheiro, afloramentos de rocha e uma trilha pisada
    const trail = distField(W, H, [meander(r, ...across(), W, H, 0.2)]);
    const lx = W * (0.25 + r() * 0.5), ly = H * (0.25 + r() * 0.5), lr = Math.max(2, S * 0.13);
    for (let j = 0; j < H; j++) for (let i = 0; i < W; i++) {
      const k = j * W + i, n = nz(i, j, 6), d = Math.hypot(i + 0.5 - lx, j + 0.5 - ly) - nz(i, j, 3, 4) * 1.8;
      let c = n + dc(i, j) * 0.25 > 0.8 ? 'm' : nz(i, j, 3.5, 50) > 0.76 ? 'r' : 'n';
      if (d < lr) c = 'a';
      if (trail[k] < 0.8 && c !== 'a') c = 't';
      out[k] = c;
    }
    return out.join('');
  }
  if (id === 'caverna') {
    // salão de caverna: paredões irregulares na borda, chão de terra e rocha, um rio subterrâneo e um bolsão de lava
    const riv = distField(W, H, [meander(r, ...down(), W, H, 0.2)]);
    const vx = W * (0.2 + r() * 0.6), vy = H * (0.2 + r() * 0.6);
    for (let j = 0; j < H; j++) for (let i = 0; i < W; i++) {
      const k = j * W + i, n = nz(i, j, 5), e = dc(i, j) + (n - 0.5) * 0.5;
      let c = e > 0.88 ? 'r' : nz(i, j, 3, 50) > 0.6 ? 'r' : 't';
      if (riv[k] < 0.9 + n * 0.7 && e < 0.95) c = 'a';
      if (Math.hypot(i + 0.5 - vx, j + 0.5 - vy) < 1.6 + n * 1.5 && c !== 'a') c = 'v';
      out[k] = c;
    }
    return out.join('');
  }
  return out.join('');
}

// ---------------------------------------------------------------- modelos de vegetação (gerados em código)
// Formas arredondadas, com normais suaves e cor em degradê (escuro embaixo, claro em cima).
const _ca = new THREE.Color(), _cb = new THREE.Color();
function part(geo, low, high, { p = [0, 0, 0], r = [0, 0, 0], s = [1, 1, 1] } = {}) {
  geo.computeBoundingBox();
  const y0 = geo.boundingBox.min.y, y1 = geo.boundingBox.max.y;
  const g = geo.index ? geo.toNonIndexed() : geo;
  _ca.set(low); _cb.set(high || low);
  const pos = g.attributes.position, arr = new Float32Array(pos.count * 3);
  for (let i = 0; i < pos.count; i++) {
    const t = y1 > y0 ? (pos.getY(i) - y0) / (y1 - y0) : 1;
    arr[i * 3] = _ca.r + (_cb.r - _ca.r) * t; arr[i * 3 + 1] = _ca.g + (_cb.g - _ca.g) * t; arr[i * 3 + 2] = _ca.b + (_cb.b - _ca.b) * t;
  }
  g.setAttribute('color', new THREE.BufferAttribute(arr, 3));
  g.applyMatrix4(new THREE.Matrix4().compose(new THREE.Vector3(...p), new THREE.Quaternion().setFromEuler(new THREE.Euler(...r)), new THREE.Vector3(...s)));
  g.deleteAttribute('uv');
  return g;
}
const cyl = (rt, rb, h, seg = 12) => new THREE.CylinderGeometry(rt, rb, h, seg);
const cone = (r, h, seg = 16) => new THREE.ConeGeometry(r, h, seg, 3);
// esfera "amassada" para copas, arbustos e pedras
function blob(r, seed, amount = 0.2, ws = 14, hs = 10) {
  const g = new THREE.SphereGeometry(r, ws, hs), pos = g.attributes.position, v = new THREE.Vector3();
  for (let i = 0; i < pos.count; i++) {
    v.fromBufferAttribute(pos, i);
    const n = fbm(v.x / r * 1.3 + 9, v.y / r * 1.3 + v.z / r * 1.3 + 5, seed);
    v.multiplyScalar(1 + (n - 0.5) * 2 * amount);
    pos.setXYZ(i, v.x, v.y, v.z);
  }
  g.computeVertexNormals();
  // corrige a emenda da esfera: normal radial fica lisa
  const nrm = g.attributes.normal;
  for (let i = 0; i < pos.count; i++) { v.fromBufferAttribute(pos, i).normalize(); nrm.setXYZ(i, v.x, v.y, v.z); }
  return g;
}
function leafy(low, high, trunkLow = '#5a3a26', trunkHigh = '#8a5e3c') {
  return mergeGeometries([
    part(cyl(0.14, 0.26, 2.0), trunkLow, trunkHigh, { p: [0, 1.0, 0] }),
    part(blob(1.35, 1), low, high, { p: [0, 2.9, 0], s: [1, 0.9, 1] }),
    part(blob(0.95, 2), low, high, { p: [0.85, 2.45, 0.3] }),
    part(blob(0.9, 3), low, high, { p: [-0.75, 2.55, -0.4] }),
    part(blob(0.85, 4), low, high, { p: [0.1, 3.65, -0.15] }),
  ]);
}
function pine(low, high) {
  return mergeGeometries([
    part(cyl(0.12, 0.2, 1.3), '#5a3a26', '#7d5536', { p: [0, 0.65, 0] }),
    part(cone(1.2, 1.9), low, high, { p: [0, 1.95, 0] }),
    part(cone(0.95, 1.6), low, high, { p: [0, 2.95, 0] }),
    part(cone(0.62, 1.35), low, high, { p: [0, 3.9, 0] }),
  ]);
}
// tufo de grama: lâminas curvas; a normal aponta para cima para a luz ficar uniforme
function grassClump(seed, low, high) {
  const r = rng(seed), P = [], C = [], N = [];
  _ca.set(low); _cb.set(high);
  for (let b = 0; b < 6; b++) {
    const ang = r() * Math.PI * 2, ox = (r() - 0.5) * 0.5, oz = (r() - 0.5) * 0.5, h = 0.45 + r() * 0.4, w = 0.05 + r() * 0.03, bend = 0.12 + r() * 0.22;
    const dx = Math.cos(ang), dz = Math.sin(ang), SEG = 3, pts = [];
    for (let k = 0; k <= SEG; k++) {
      const t = k / SEG, ww = w * (1 - t), fwd = bend * t * t;
      pts.push([ox - dz * ww + dx * fwd, h * t, oz + dx * ww + dz * fwd, ox + dz * ww + dx * fwd, h * t, oz - dx * ww + dz * fwd, t]);
    }
    for (let k = 0; k < SEG; k++) {
      const a = pts[k], c = pts[k + 1];
      const quad = [[a[0], a[1], a[2], a[6]], [a[3], a[4], a[5], a[6]], [c[0], c[1], c[2], c[6]], [a[3], a[4], a[5], a[6]], [c[3], c[4], c[5], c[6]], [c[0], c[1], c[2], c[6]]];
      for (const q of quad) {
        P.push(q[0], q[1], q[2]); N.push(0, 1, 0);
        C.push(_ca.r + (_cb.r - _ca.r) * q[3], _ca.g + (_cb.g - _ca.g) * q[3], _ca.b + (_cb.b - _ca.b) * q[3]);
      }
    }
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(P, 3));
  g.setAttribute('normal', new THREE.Float32BufferAttribute(N, 3));
  g.setAttribute('color', new THREE.Float32BufferAttribute(C, 3));
  return g;
}
const MODELS = {
  pine: () => pine('#1d6a4a', '#58c27a'),
  pine_snow: () => pine('#9fc4d8', '#ffffff'),
  round: () => leafy('#2c8a44', '#8fe060'),
  blossom: () => leafy('#d85a98', '#ffc9e2', '#4f3a34', '#7a5a50'),
  swamp: () => mergeGeometries([
    part(cyl(0.1, 0.32, 2.7, 8), '#33291f', '#5a4a36', { p: [0, 1.35, 0], r: [0, 0, 0.08] }),
    part(blob(1.3, 5), '#3d5226', '#8aa23e', { p: [0, 3.0, 0], s: [1.2, 0.5, 1.2] }),
    part(blob(0.8, 6), '#3d5226', '#7a9238', { p: [0.9, 2.6, 0.3], s: [1, 0.55, 1] }),
    part(cone(0.3, 1.5, 7), '#6f8a34', '#34481f', { p: [0.7, 2.0, 0.2], r: [Math.PI, 0, 0] }),
    part(cone(0.25, 1.2, 7), '#6f8a34', '#34481f', { p: [-0.6, 2.2, -0.4], r: [Math.PI, 0, 0] }),
    part(cone(0.22, 1.0, 7), '#6f8a34', '#34481f', { p: [0.1, 2.3, 0.7], r: [Math.PI, 0, 0] }),
  ]),
  dead: () => mergeGeometries([
    part(cyl(0.07, 0.22, 3.2, 7), '#3f352e', '#7a6a5c', { p: [0, 1.6, 0] }),
    part(cyl(0.03, 0.07, 1.3, 6), '#5a4c42', '#7a6a5c', { p: [0.45, 2.2, 0], r: [0, 0, -0.9] }),
    part(cyl(0.03, 0.06, 1.0, 6), '#5a4c42', '#7a6a5c', { p: [-0.35, 2.7, 0.1], r: [0.2, 0, 0.85] }),
    part(cyl(0.02, 0.05, 0.8, 6), '#5a4c42', '#7a6a5c', { p: [0.05, 3.0, -0.3], r: [-0.8, 0, 0] }),
  ]),
  rock: () => mergeGeometries([
    part(blob(0.6, 7, 0.28, 9, 6), '#5d6072', '#b4b8c6', { p: [0, 0.25, 0], s: [1, 0.65, 0.85] }),
    part(blob(0.3, 8, 0.28, 8, 5), '#5d6072', '#a4a8b6', { p: [0.5, 0.12, 0.25], s: [1, 0.7, 1] }),
  ]),
  bush: () => mergeGeometries([
    part(blob(0.5, 9, 0.2, 9, 6), '#2c8a44', '#8fe060', { p: [0, 0.32, 0], s: [1, 0.8, 1] }),
    part(blob(0.34, 10, 0.2, 8, 5), '#2c8a44', '#9ae86a', { p: [0.38, 0.24, 0.18] }),
    part(blob(0.3, 11, 0.2, 8, 5), '#2c8a44', '#84d658', { p: [-0.3, 0.2, -0.2] }),
  ]),
  tuft: () => grassClump(1, '#2f8a3c', '#b4f070'),
  tuft2: () => grassClump(2, '#2f8a3c', '#9ee860'),
  tuft_dry: () => grassClump(3, '#6a6a30', '#c8c870'),
  flower: () => mergeGeometries([
    part(cyl(0.012, 0.012, 0.3, 4), '#5aa84a', '#5aa84a', { p: [0, 0.15, 0] }),
    part(new THREE.SphereGeometry(0.075, 7, 5), '#ffffff', '#ffffff', { p: [0, 0.33, 0], s: [1, 0.6, 1] }),
    part(new THREE.SphereGeometry(0.03, 5, 4), '#ffd84a', '#ffd84a', { p: [0, 0.37, 0] }),
  ]),
  reed: () => mergeGeometries([
    part(cone(0.035, 1.3, 5), '#5a7a30', '#b4c860', { p: [0, 0.65, 0] }),
    part(cone(0.035, 1.1, 5), '#5a7a30', '#a4b858', { p: [0.14, 0.55, 0.08], r: [0, 0, -0.12] }),
    part(cone(0.035, 1.2, 5), '#5a7a30', '#bcd068', { p: [-0.12, 0.6, 0.1], r: [0.1, 0, 0.1] }),
    part(cone(0.035, 0.9, 5), '#5a7a30', '#a4b858', { p: [0.04, 0.45, -0.15], r: [-0.15, 0, 0] }),
    part(new THREE.CapsuleGeometry(0.05, 0.16, 3, 7), '#5a3a22', '#7a5030', { p: [0, 1.15, 0] }),
  ]),
  cactus: () => mergeGeometries([
    part(new THREE.CapsuleGeometry(0.22, 1.4, 4, 10), '#2f7a4a', '#7fd070', { p: [0, 0.9, 0] }),
    part(new THREE.CapsuleGeometry(0.11, 0.3, 3, 8), '#3a8a52', '#7fd070', { p: [0.36, 0.9, 0], r: [0, 0, Math.PI / 2] }),
    part(new THREE.CapsuleGeometry(0.11, 0.45, 3, 8), '#3a8a52', '#8fdc7a', { p: [0.55, 1.25, 0] }),
    part(new THREE.CapsuleGeometry(0.1, 0.25, 3, 8), '#3a8a52', '#7fd070', { p: [-0.33, 1.15, 0], r: [0, 0, Math.PI / 2] }),
    part(new THREE.CapsuleGeometry(0.1, 0.35, 3, 8), '#3a8a52', '#8fdc7a', { p: [-0.5, 1.42, 0] }),
  ]),
  stalagmite: () => mergeGeometries([part(cone(0.34, 1.6, 9), '#3f3d52', '#9a98b4', { p: [0, 0.8, 0] }), part(cone(0.2, 0.9, 8), '#3f3d52', '#8a88a4', { p: [0.32, 0.45, 0.15] })]),
  mushroom: () => mergeGeometries([
    part(cyl(0.05, 0.08, 0.32, 7), '#d8ccb0', '#fff4dc', { p: [0, 0.16, 0] }),
    part(new THREE.SphereGeometry(0.24, 10, 5, 0, Math.PI * 2, 0, Math.PI / 2), '#c23a3a', '#ff7a6a', { p: [0, 0.3, 0], s: [1, 0.75, 1] }),
  ]),
  lily: () => mergeGeometries([
    part(cyl(0.3, 0.3, 0.03, 12), '#3f9a4a', '#6fd070', { p: [0, 0.09, 0] }),
    part(new THREE.SphereGeometry(0.08, 7, 5), '#ffb0d0', '#ffffff', { p: [0.08, 0.15, 0.05], s: [1, 0.7, 1] }),
  ]),
  // cristais: sem sombreamento, para brilharem no escuro
  crystal: () => mergeGeometries([
    part(new THREE.OctahedronGeometry(0.28, 0), '#3a8cff', '#b8f4ff', { p: [0, 0.6, 0], s: [1, 2.4, 1] }),
    part(new THREE.OctahedronGeometry(0.18, 0), '#6a5cff', '#d0c8ff', { p: [0.3, 0.35, 0.1], s: [1, 2.1, 1], r: [0, 0, -0.4] }),
    part(new THREE.OctahedronGeometry(0.15, 0), '#3a8cff', '#b8f4ff', { p: [-0.25, 0.3, -0.12], s: [1, 2.0, 1], r: [0.3, 0, 0.35] }),
  ]),
};
const TALL = new Set(['pine', 'pine_snow', 'round', 'blossom', 'swamp', 'dead']);
const GRASS = new Set(['tuft', 'tuft2', 'tuft_dry', 'flower', 'reed']);
const OUTLINED = new Set(['pine', 'pine_snow', 'round', 'blossom', 'swamp', 'rock', 'bush', 'cactus', 'stalagmite', 'mushroom']);
const FLOWER_COLORS = [0xffffff, 0xffe066, 0xff9ac8, 0xb49cff, 0xff7a6a];
const geoCache = new Map();
const modelGeo = (name) => { if (!geoCache.has(name)) geoCache.set(name, MODELS[name]()); return geoCache.get(name); };

// ---------------------------------------------------------------- texturas geradas
let noiseCanvas = null;
function noiseTile() {
  if (noiseCanvas) return noiseCanvas;
  const S = 256, c = document.createElement('canvas'); c.width = c.height = S;
  const g = c.getContext('2d'), img = g.createImageData(S, S), r = rng(77);
  for (let y = 0; y < S; y++) for (let x = 0; x < S; x++) {
    // ruído que emenda nas bordas, mais granulado fino
    const u = x / S, v = y / S;
    const a = fbm(u * 8, v * 8, 3), b = fbm((u - 1) * 8, v * 8, 3), cc = fbm(u * 8, (v - 1) * 8, 3), d = fbm((u - 1) * 8, (v - 1) * 8, 3);
    const n = (a * (1 - u) + b * u) * (1 - v) + (cc * (1 - u) + d * u) * v;
    const val = Math.max(0, Math.min(255, 128 + (n - 0.5) * 190 + (r() - 0.5) * 46));
    const i = (y * S + x) * 4; img.data[i] = img.data[i + 1] = img.data[i + 2] = val; img.data[i + 3] = 255;
  }
  g.putImageData(img, 0, 0);
  return (noiseCanvas = c);
}
function rippleTexture(lava) {
  const S = 128, c = document.createElement('canvas'); c.width = c.height = S;
  const g = c.getContext('2d'), img = g.createImageData(S, S);
  for (let y = 0; y < S; y++) for (let x = 0; x < S; x++) {
    const u = x / S, v = y / S;
    const f = (uu, vv) => fbm(uu * 5, vv * 5, 21);
    let n = (f(u, v) * (1 - u) + f(u - 1, v) * u) * (1 - v) + (f(u, v - 1) * (1 - u) + f(u - 1, v - 1) * u) * v;
    n = Math.abs(n - 0.5) * 2; // veios
    const i = (y * S + x) * 4;
    if (lava) { const k = 1 - Math.min(1, n * 2.4); img.data[i] = 150 + 105 * k; img.data[i + 1] = 40 + 170 * k * k; img.data[i + 2] = 10 + 40 * k * k; }
    else { const k = 1 - Math.min(1, n * 3.2); const b = 150 + 105 * k * k; img.data[i] = img.data[i + 1] = img.data[i + 2] = b; }
    img.data[i + 3] = 255;
  }
  g.putImageData(img, 0, 0);
  const t = new THREE.CanvasTexture(c);
  t.wrapS = t.wrapT = THREE.RepeatWrapping; t.colorSpace = THREE.SRGBColorSpace;
  return t;
}

// ---------------------------------------------------------------- chão com texturas
// cada quadrado escolhe uma textura; a mistura entre quadrados vizinhos tem a borda tremida por ruído
const SPLAT = { g: [0, 0], m: [0, 1], t: [0, 2], p: [0, 2], l: [1, 0], a: [1, 0], b: [1, 1], s: [1, 2], r: [2, 0], v: [2, 0], n: [2, 1], e: [2, 2] };
const GTEX = ['grama', 'folhas', 'terra', 'lama', 'musgo', 'areia', 'rocha', 'neve', 'calcada'];
let groundTexPromise = null;
function groundTextures() {
  if (!groundTexPromise) {
    const L = new THREE.TextureLoader();
    groundTexPromise = Promise.all(GTEX.map((n) => L.loadAsync(`/assets/terreno/tex/${n}.jpg`).then((t) => {
      t.colorSpace = THREE.SRGBColorSpace; t.wrapS = t.wrapT = THREE.RepeatWrapping; t.anisotropy = 4; return t;
    }))).then((list) => {
      const nt = new THREE.CanvasTexture(noiseTile()); nt.wrapS = nt.wrapT = THREE.RepeatWrapping;
      return { list, noise: nt };
    });
  }
  return groundTexPromise;
}
function groundMaterial(T, splat, shade, w, h) {
  const m = new THREE.MeshLambertMaterial({ color: 0xffffff });
  m.onBeforeCompile = (sh) => {
    sh.uniforms.tA = { value: splat[0] }; sh.uniforms.tB = { value: splat[1] }; sh.uniforms.tC = { value: splat[2] };
    sh.uniforms.tShade = { value: shade }; sh.uniforms.tNoise = { value: T.noise }; sh.uniforms.uSize = { value: new THREE.Vector2(w, h) };
    T.list.forEach((t, i) => { sh.uniforms['t' + i] = { value: t }; });
    sh.vertexShader = sh.vertexShader.replace('#include <common>', '#include <common>\nvarying vec3 vWPos;')
      .replace('#include <begin_vertex>', '#include <begin_vertex>\nvWPos = (modelMatrix * vec4(transformed, 1.0)).xyz;');
    sh.fragmentShader = sh.fragmentShader.replace('#include <common>', `#include <common>
varying vec3 vWPos;
uniform sampler2D tA, tB, tC, tShade, tNoise, t0, t1, t2, t3, t4, t5, t6, t7, t8; uniform vec2 uSize;
vec3 two(sampler2D t, vec2 w, float s) { return mix(texture2D(t, w / s).rgb, texture2D(t, w / (s * 3.7) + 0.37).rgb, 0.35); }`)
      .replace('#include <map_fragment>', `
vec2 w = vWPos.xz;
vec2 nn = texture2D(tNoise, w / 19.0).rg - 0.5;
vec2 suv = (w + nn * 1.4) / uSize;
vec3 a = pow(texture2D(tA, suv).rgb, vec3(2.2)), b = pow(texture2D(tB, suv).rgb, vec3(2.2)), c = pow(texture2D(tC, suv).rgb, vec3(2.2));
float tot = dot(a, vec3(1.0)) + dot(b, vec3(1.0)) + dot(c, vec3(1.0)) + 1e-4;
vec3 col = two(t0, w, 5.0) * a.r + two(t1, w, 5.5) * a.g + two(t2, w, 6.0) * a.b
         + two(t3, w, 7.0) * b.r + two(t4, w, 6.0) * b.g + two(t5, w, 8.0) * b.b
         + two(t6, w, 7.0) * c.r + two(t7, w, 9.0) * c.g + texture2D(t8, w / 9.0).rgb * c.b;
col /= tot;
col *= texture2D(tShade, w / uSize).r;
diffuseColor.rgb *= col;`);
  };
  return m;
}

// fundos panorâmicos de cada bioma (fontes/blender/fundos_biomas.py; a estrada e o covil usam os dos mapas prontos)
const FUNDOS = {
  floresta: { img: '/assets/terreno/fundos/floresta.webp', alpha: true }, pantano: { img: '/assets/terreno/fundos/pantano.webp', alpha: true },
  deserto: { img: '/assets/terreno/fundos/deserto.webp', alpha: true }, neve: { img: '/assets/terreno/fundos/neve.webp', alpha: true },
  caverna: { img: '/assets/terreno/fundos/caverna.webp' }, masmorra: { img: '/assets/terreno/fundos/masmorra.webp' },
  estrada: { img: '/assets/maps/estrada/tex/fundo.webp', alpha: true },
  covil: { img: '/assets/maps/covil/tex/fundo.jpg', rad: 230, base: -35, band: 130, rep: 2 },
};
// chão em volta do mapa: [textura do chão (índice em GTEX), cor que multiplica]
const FAR_GROUND = { floresta: [0, 0xb8c0a8], pantano: [4, 0x9aa58a], deserto: [5, 0xffffff], neve: [7, 0xffffff], caverna: [6, 0x5a5560],
  masmorra: [6, 0x45434a], estrada: [1, 0xb8b8a8], covil: [3, 0x8a9480] };

// kit da mata feito no Blender (pinheiros, plantas, pedras) e os objetos da estrada (carroça, fogueira, marco...)
let estradaKit = null, estradaKitTop = null, estradaKitLoading = null;
function loadEstradaKit(topDown) {
  const base = '/assets/maps/estrada/';
  return loadKit([base + 'kit.glb', base + 'props.glb'], { texBase: base + 'tex/', topDown }).then((k) => { if (topDown) estradaKitTop = k; else estradaKit = k; return k; });
}

// Estrada na mata: decide onde vai cada peça do kit. Primeiro os objetos de cena (placa na encruzilhada, carroça
// quebrada na beira da estrada com caixotes caídos, marco de pedra, fogueira apagada na maior clareira, um trecho de
// cerca), depois a mata (pinheiros, alguns quase pretos), as plantas rasteiras e as pedras soltas do meio-fio.
function decorateEstrada(cells, W, H, spawn, wallDist) {
  const inst = {}, obstacles = [], shadows = [], blocked = [];
  let hsh = 7; for (let k = 0; k < cells.length; k += 7) hsh = (Math.imul(hsh, 31) + cells.charCodeAt(k)) | 0;
  const r = rng(hsh ^ 0x5eed);
  const put = (m, x, z, s, ry = r() * 6.283, tint = 1) => (inst[m] || (inst[m] = [])).push([x, 0, z, ry, s, tint]);
  const at = (i, j) => (i < 0 || j < 0 || i >= W || j >= H ? '' : cells[j * W + i]);
  const C = (i) => (i + 0.5) * G;
  const free = (x, z, pad = 0) => blocked.every(([bx, bz, br]) => Math.hypot(x - bx, z - bz) > br + pad) && wallDist(x, z) > 1.2 && !(spawn && Math.hypot(x - spawn.x, z - spawn.z) < 2.5);
  const prop = (m, x, z, ry, rad, solid = rad * 0.8) => { put(m, x, z, 1, ry); blocked.push([x, z, rad]); if (solid) obstacles.push({ x, z, r: solid }); };
  // estrada: quadrados de laje e quantos vizinhos de laje cada um tem
  const road = [];
  for (let j = 0; j < H; j++) for (let i = 0; i < W; i++) if (at(i, j) === 'e') {
    let n = 0; for (let dj = -2; dj <= 2; dj++) for (let di = -2; di <= 2; di++) if (at(i + di, j + dj) === 'e') n++;
    road.push([i, j, n]);
  }
  const besideRoad = (i, j) => { for (const [di, dj] of [[1, 0], [-1, 0], [0, 1], [0, -1], [2, 0], [-2, 0], [0, 2], [0, -2]]) if ('tg'.includes(at(i + di, j + dj)) && !'e'.includes(at(i + di * 2, j + dj * 2)) ) return [i + di, j + dj, Math.atan2(dj, di)]; return null; };
  if (road.length > 6) {
    const horiz = W >= H;
    const sorted = [...road].sort((a, b) => horiz ? a[0] - b[0] : a[1] - b[1]);
    // encruzilhada: o quadrado com mais laje em volta (ou o do meio)
    const junction = road.reduce((a, b) => (b[2] > a[2] ? b : a));
    const jc = junction[2] >= 19 ? junction : sorted[Math.floor(sorted.length / 2)];
    for (let tries = 0, rad = 2; tries < 40; tries++, rad += 0.25) {
      const a = r() * 6.283, x = C(jc[0]) + Math.cos(a) * rad * G, z = C(jc[1]) + Math.sin(a) * rad * G;
      const ch = at(Math.floor(x / G), Math.floor(z / G));
      if ((ch === 't' || ch === 'g') && free(x, z)) { prop('placa', x, z, r() * 6.283, 1.2, 0.45); break; }
    }
    const spot = (frac) => { const c = sorted[Math.floor(sorted.length * frac)]; return besideRoad(c[0], c[1]); };
    const s1 = spot(0.22 + r() * 0.1);
    if (s1) {
      const x = C(s1[0]), z = C(s1[1]);
      if (free(x, z, 1)) {
        prop('carroca', x, z, -s1[2] + Math.PI / 2 + (r() - 0.5) * 0.5, 6.5, 0); obstacles.push({ x, z, r: 2.6 });
        prop('caixotes', x + 3.5 * Math.cos(s1[2]), z + 3.5 * Math.sin(s1[2]), r() * 6.283, 2.0, 1.3);
      }
    }
    const s2 = spot(0.82);
    if (s2) { const x = C(s2[0]), z = C(s2[1]); if (free(x, z)) prop('marco', x, z, -s2[2] + Math.PI / 2, 1.2, 0.5); }
    const s3 = spot(0.6);
    if (s3 && r() < 0.8) { const x = C(s3[0]) + Math.cos(s3[2]) * 2.5, z = C(s3[1]) + Math.sin(s3[2]) * 2.5; if (free(x, z)) prop('cerca', x, z, -s3[2] + Math.PI / 2, 3.4, 0); }
  }
  // fogueira na maior clareira, longe da estrada
  let best = null;
  for (let j = 2; j < H - 2; j++) for (let i = 2; i < W - 2; i++) {
    if (at(i, j) !== 'g') continue;
    let n = 0, e = 0; for (let dj = -3; dj <= 3; dj++) for (let di = -3; di <= 3; di++) { const c = at(i + di, j + dj); if (c === 'g') n++; if (c === 'e') e++; }
    if (e === 0 && (!best || n > best[2])) best = [i, j, n];
  }
  if (best && best[2] > 20 && free(C(best[0]), C(best[1]), 1)) prop('fogueira', C(best[0]), C(best[1]), r() * 6.283, 3.2, 1.3);
  // vegetação
  for (let j = 0; j < H; j++) for (let i = 0; i < W; i++) {
    const ch = at(i, j), rr = rng(Math.imul(j * W + i + 1, 2654435761) ^ 0x51ed);
    const jit = (k = 0.8) => [(i + 0.5 + (rr() - 0.5) * k) * G, (j + 0.5 + (rr() - 0.5) * k) * G];
    const nearRoad = at(i + 1, j) === 'e' || at(i - 1, j) === 'e' || at(i, j + 1) === 'e' || at(i, j - 1) === 'e';
    const small = (m, p, s0 = 0.75, s1 = 1.3) => { if (rr() < p) { const [x, z] = jit(1); if (free(x, z, -0.6)) put(m, x, z, s0 + rr() * (s1 - s0), rr() * 6.283, 0.85 + rr() * 0.25); } };
    if (ch === 'm') {
      if (rr() < 0.72) {
        const [x, z] = jit(0.9), q = rr(), sc = 0.68 + rr() * 0.36;
        if (free(x, z, 0.3)) {
          const m = q < 0.4 ? 'pinho_a' : q < 0.75 ? 'pinho_b' : 'pinho_c';
          put(m, x, z, sc, rr() * 6.283, rr() < 0.22 ? 0.34 + rr() * 0.16 : 0.82 + rr() * 0.24);
          obstacles.push({ x, z, r: 0.55 * sc });
          const hgt = { pinho_a: 24, pinho_b: 19, pinho_c: 14 }[m] * sc, rad = { pinho_a: 6.6, pinho_b: 5.4, pinho_c: 4.2 }[m] * sc * 0.7;
          shadows.push([x, z, rad, hgt * 0.5]);
        }
      }
      small('samambaia', 0.4); small('capim', 0.3);
    } else if (ch === 'g') {
      small('flores', nearRoad ? 0.75 : 0.45); small('capim', 0.55); small('samambaia', 0.22);
      const p = rr();
      if (p < 0.045) { const [x, z] = jit(0.6), sc = 0.7 + rr() * 0.5; if (free(x, z, 0.5)) { put(rr() < 0.4 ? 'arbusto_amarelo' : 'arbusto_verde', x, z, sc); blocked.push([x, z, 1.5 * sc]); shadows.push([x, z, 1.8 * sc, 3 * sc]); } }
      else if (p < 0.055) { const [x, z] = jit(0.5), sc = 0.85 + rr() * 0.3; if (free(x, z, 2)) { put('arvore_outono', x, z, sc); obstacles.push({ x, z, r: 0.6 * sc }); blocked.push([x, z, 3]); shadows.push([x, z, 4.5 * sc, 9 * sc]); } }
      else if (p < 0.065) { const [x, z] = jit(0.5), sc = 0.5 + rr() * 0.5; if (free(x, z, 1)) { put('pedra_' + (1 + Math.floor(rr() * 4)), x, z, sc); obstacles.push({ x, z, r: 1.3 * sc }); blocked.push([x, z, 1.8 * sc]); } }
    } else if (ch === 't') {
      small('capim', 0.45); small('seixo_' + (1 + Math.floor(rr() * 2)), 0.15, 0.7, 1.4);
      if (nearRoad && rr() < 0.4) { const [x, z] = jit(0.9); if (free(x, z, -0.5)) put(rr() < 0.08 ? 'blocos_monte' : 'bloco_' + (1 + Math.floor(rr() * 3)), x, z, 0.6 + rr() * 0.6); }
    } else if (ch === 'a') {
      small('capim', 0.25);
    }
  }
  return { inst, obstacles, shadows };
}

// ---------------------------------------------------------------- terreno
const _m = new THREE.Matrix4(), _p = new THREE.Vector3(), _q = new THREE.Quaternion(), _s = new THREE.Vector3(), _c = new THREE.Color();
const UP = new THREE.Vector3(0, 1, 0);

export class Terrain {
  // W, H em quadrados; segments/doors em unidades de mundo; tiles = peças de piso do kit já carregadas
  constructor({ W, H, segments, doors, topDown, tiles }) {
    this.W = W; this.H = H; this.segments = segments; this.doors = doors; this.topDown = topDown; this.tiles = tiles;
    this.cells = 'p'.repeat(W * H); this.biome = BIOMES[0];
    this.group = new THREE.Group();
    this.dynamic = new THREE.Group(); // vegetação e peças de piso, refeitas a cada pintura
    this.group.add(this.dynamic);
    this.obstacles = [];
    const w = W * G, h = H * G;

    this.far = new THREE.Mesh(new THREE.PlaneGeometry(w + 700, h + 700), new THREE.MeshLambertMaterial({ color: 0x0c0c10 }));
    this.far.rotation.x = -Math.PI / 2; this.far.position.set(w / 2, -0.12, h / 2);

    const px = Math.max(8, Math.min(40, Math.floor(1536 / Math.max(W, H))));
    this.small = document.createElement('canvas'); this.small.width = W; this.small.height = H;
    this.canvas = document.createElement('canvas'); this.canvas.width = W * px; this.canvas.height = H * px;
    this.tex = new THREE.CanvasTexture(this.canvas); this.tex.colorSpace = THREE.SRGBColorSpace; this.tex.anisotropy = 4;
    this.ground = new THREE.Mesh(new THREE.PlaneGeometry(w, h), new THREE.MeshLambertMaterial({ map: this.tex }));
    this.ground.rotation.x = -Math.PI / 2; this.ground.position.set(w / 2, 0.01, h / 2);

    const liquid = (lava) => {
      const mask = document.createElement('canvas'); mask.width = W * 8; mask.height = H * 8;
      const alpha = new THREE.CanvasTexture(mask);
      const map = rippleTexture(lava); map.repeat.set(w / 6, h / 6);
      const mat = lava
        ? new THREE.MeshBasicMaterial({ map, alphaMap: alpha, transparent: true, depthWrite: false })
        : new THREE.MeshLambertMaterial({ map, alphaMap: alpha, transparent: true, opacity: 0.86, depthWrite: false });
      const mesh = new THREE.Mesh(new THREE.PlaneGeometry(w, h), mat);
      mesh.rotation.x = -Math.PI / 2; mesh.position.set(w / 2, lava ? 0.075 : 0.07, h / 2); mesh.renderOrder = 1;
      return { mask, alpha, map, mesh };
    };
    this.water = liquid(false); this.lava = liquid(true);
    // espuma branca na margem da água
    this.foamCanvas = document.createElement('canvas'); this.foamCanvas.width = W * 8; this.foamCanvas.height = H * 8;
    this.foamAlpha = new THREE.CanvasTexture(this.foamCanvas);
    this.foamMap = rippleTexture(false); this.foamMap.repeat.set(w / 3, h / 3);
    this.foam = new THREE.Mesh(new THREE.PlaneGeometry(w, h), new THREE.MeshBasicMaterial({ map: this.foamMap, alphaMap: this.foamAlpha, transparent: true, depthWrite: false, opacity: 0.9 }));
    this.foam.rotation.x = -Math.PI / 2; this.foam.position.set(w / 2, 0.08, h / 2); this.foam.renderOrder = 2;
    this.group.add(this.far, this.ground, this.water.mesh, this.lava.mesh, this.foam);

    // chão com texturas: 3 mapas de mistura (um pixel por quadrado) e um de sombra das copas
    this.splat = [0, 1, 2].map(() => { const c = document.createElement('canvas'); c.width = W; c.height = H; return c; });
    this.splatTex = this.splat.map((c) => { const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.NoColorSpace; t.flipY = false; t.generateMipmaps = false; t.minFilter = t.magFilter = THREE.LinearFilter; return t; });
    this.shadeCanvas = document.createElement('canvas'); this.shadeCanvas.width = W * 8; this.shadeCanvas.height = H * 8;
    this.shadeTex = new THREE.CanvasTexture(this.shadeCanvas); this.shadeTex.colorSpace = THREE.NoColorSpace; this.shadeTex.flipY = false;
    this.flatMat = this.ground.material;
    this.farFlat = this.far.material;
    groundTextures().then((T) => {
      if (this.disposed) return;
      this.texMat = groundMaterial(T, this.splatTex, this.shadeTex, w, h);
      this.ground.material = this.texMat;
    }).catch(() => {});
    this.extras = new THREE.Group(); this.group.add(this.extras);   // mata em volta e fundo panorâmico (Estrada na mata)
    this.extrasFor = null;

    this.matSolid = toon({ vertexColors: true });
    // na vista de cima, as copas ficam translúcidas para não esconder as miniaturas
    this.matTall = topDown ? toon({ vertexColors: true, transparent: true, opacity: 0.4, depthWrite: false }) : windify(toon({ vertexColors: true }), 0.011);
    this.matGrass = windify(toon({ vertexColors: true, side: THREE.DoubleSide }), 0.45);
    this.matGlow = new THREE.MeshBasicMaterial({ vertexColors: true });
    this.matLine = outlineMaterial(0.035);
    this.matLineTall = windify(outlineMaterial(0.045), 0.011);
    this.t = 0;
  }

  charAt(x, z) {
    const i = Math.floor(x / G), j = Math.floor(z / G);
    if (i < 0 || j < 0 || i >= this.W || j >= this.H) return '';
    return this.cells[j * this.W + i];
  }
  slowAt(x, z) { return SLOW[this.charAt(x, z)] || 1; }
  // custo de deslocamento em combate: terreno difícil (água, lama, brejo, mata) gasta o dobro
  costAt(x, z) { return DIFFICULT.has(this.charAt(x, z)) ? 2 : 1; }
  isDifficult(x, z) { return DIFFICULT.has(this.charAt(x, z)); }

  wallDist(x, z) {
    let best = Infinity;
    for (const s of this.segments) {
      const vx = s.x2 - s.x1, vz = s.z2 - s.z1;
      const t = Math.max(0, Math.min(1, ((x - s.x1) * vx + (z - s.z1) * vz) / (vx * vx + vz * vz || 1)));
      const d = Math.hypot(x - (s.x1 + vx * t), z - (s.z1 + vz * t));
      if (d < best) best = d;
    }
    for (const d of this.doors) { const dd = Math.hypot(x - d.mx, z - d.mz); if (dd < best) best = dd; }
    return best;
  }

  set(cells, biomeId, { imageFloor = false, spawn = null } = {}) {
    const { W, H } = this;
    this.lastOpts = { imageFloor, spawn };
    if (typeof cells !== 'string' || cells.length !== W * H) cells = 'p'.repeat(W * H);
    this.cells = cells; this.biome = biomeById(biomeId);
    const B = this.biome;
    this.far.material.color.setHex(this.topDown ? 0x0c0c10 : B.far);
    this.water.mesh.material.color.setHex(this.topDown ? 0x4a9cc8 : B.water); // na tela do mestre, água sempre azul para ler bem

    // ---- chão: uma cor por quadrado, ampliada com suavização (as bordas se misturam), mais granulado
    const sg = this.small.getContext('2d');
    const mw = document.createElement('canvas'); mw.width = W; mw.height = H;
    const ml = document.createElement('canvas'); ml.width = W; ml.height = H;
    const gw = mw.getContext('2d'), gl = ml.getContext('2d');
    gw.fillStyle = gl.fillStyle = '#000'; gw.fillRect(0, 0, W, H); gl.fillRect(0, 0, W, H);
    gw.fillStyle = gl.fillStyle = '#fff';
    let hasWater = false, hasLava = false;
    for (let j = 0; j < H; j++) for (let i = 0; i < W; i++) {
      const ch = cells[j * W + i];
      sg.fillStyle = GROUND[ch] || GROUND.p; sg.fillRect(i, j, 1, 1);
      if (ch === 'a') { gw.fillRect(i, j, 1, 1); hasWater = true; }
      if (ch === 'v') { gl.fillRect(i, j, 1, 1); hasLava = true; }
    }
    const cg = this.canvas.getContext('2d');
    cg.globalCompositeOperation = 'source-over'; cg.imageSmoothingEnabled = true; cg.imageSmoothingQuality = 'high';
    cg.drawImage(this.small, 0, 0, this.canvas.width, this.canvas.height);
    cg.globalCompositeOperation = 'overlay'; cg.fillStyle = cg.createPattern(noiseTile(), 'repeat');
    cg.fillRect(0, 0, this.canvas.width, this.canvas.height);
    cg.globalCompositeOperation = 'source-over';
    this.tex.needsUpdate = true;
    this.ground.visible = !imageFloor;
    {
      const imgs = this.splat.map((c) => c.getContext('2d').createImageData(W, H));
      for (let k = 0; k < W * H; k++) {
        const [t, ch] = SPLAT[cells[k]] || SPLAT.p;
        imgs[t].data[k * 4 + ch] = 255;
        for (const im of imgs) im.data[k * 4 + 3] = 255;
      }
      imgs.forEach((im, t) => { this.splat[t].getContext('2d').putImageData(im, 0, 0); this.splatTex[t].needsUpdate = true; });
    }
    for (const [L, src, on] of [[this.water, mw, hasWater], [this.lava, ml, hasLava]]) {
      const g = L.mask.getContext('2d');
      g.imageSmoothingEnabled = true; g.imageSmoothingQuality = 'high';
      g.drawImage(src, 0, 0, L.mask.width, L.mask.height);
      L.alpha.needsUpdate = true; L.mesh.visible = on;
    }
    this.foam.visible = hasWater;
    if (hasWater) {
      const mc = this.water.mask, src = mc.getContext('2d').getImageData(0, 0, mc.width, mc.height), fg = this.foamCanvas.getContext('2d'), out = fg.createImageData(mc.width, mc.height);
      const ss = (a, b, x) => { const t = Math.max(0, Math.min(1, (x - a) / (b - a))); return t * t * (3 - 2 * t); };
      for (let k = 0; k < src.data.length; k += 4) {
        const m = src.data[k] / 255, f = ss(0.22, 0.4, m) * (1 - ss(0.44, 0.62, m)) * 255;
        out.data[k] = out.data[k + 1] = out.data[k + 2] = f; out.data[k + 3] = 255;
      }
      fg.putImageData(out, 0, 0); this.foamAlpha.needsUpdate = true;
    }

    // ---- peças de piso do kit e vegetação
    for (const o of [...this.dynamic.children]) { o.dispose && o.dispose(); this.dynamic.remove(o); }
    this.obstacles = [];
    const batches = new Map();
    const put = (model, x, z, scale, ry, shade) => {
      if (!batches.has(model)) batches.set(model, []);
      batches.get(model).push([x, z, scale, ry, shade]);
    };
    const cellCount = W * H;
    const detail = Math.min(1, 1400 / cellCount); // mapas enormes recebem menos enfeite miúdo
    const is = (i, j, c) => i >= 0 && j >= 0 && i < W && j < H && cells[j * W + i] === c;
    const large = [], small = [];
    const used = new Uint8Array(cellCount);
    const id = B.id;
    const shadows = [];
    // Estrada na mata: árvores, plantas, pedras e objetos do kit feito no Blender (carrega na primeira vez)
    const useKit = id === 'estrada';
    const kit = useKit ? (this.topDown ? estradaKitTop : estradaKit) : null;
    if (useKit && !kit) {
      loadEstradaKit(this.topDown).then(() => { if (!this.disposed && this.biome.id === 'estrada') this.set(this.cells, 'estrada', this.lastOpts); }).catch(() => {});
    }
    if (kit) {
      const deco = decorateEstrada(cells, W, H, spawn, (x, z) => this.wallDist(x, z));
      this.dynamic.add(instanceKit(kit, deco.inst, { topDown: this.topDown, chunk: 60 }));
      this.obstacles.push(...deco.obstacles); shadows.push(...deco.shadows);
    }
    this.biomeExtras(id, useKit ? kit : null, imageFloor);
    const KIT_CELLS = 'mgtea';
    for (let j = 0; j < H; j++) for (let i = 0; i < W; i++) {
      const idx = j * W + i, ch = cells[idx];
      if (useKit && KIT_CELLS.includes(ch)) continue;
      if (ch === 'p') {
        if (imageFloor || used[idx]) continue;
        if (i % 2 === 0 && j % 2 === 0 && is(i + 1, j, 'p') && is(i, j + 1, 'p') && is(i + 1, j + 1, 'p')) {
          used[idx + 1] = used[idx + W] = used[idx + W + 1] = 1; large.push([(i + 1) * G, (j + 1) * G]);
        } else small.push([(i + 0.5) * G, (j + 0.5) * G]);
        continue;
      }
      const r = rng(Math.imul(idx + 1, 2654435761) ^ 0x51ed);
      const at = (model, { clear = 0.6, solid = 0, smin = 0.8, smax = 1.25, spread = 0.8, tint = 0 } = {}) => {
        const x = (i + 0.5 + (r() - 0.5) * spread) * G, z = (j + 0.5 + (r() - 0.5) * spread) * G;
        const scale = smin + r() * (smax - smin), ry = r() * Math.PI * 2, shade = 0.85 + r() * 0.3;
        if (this.wallDist(x, z) < clear) return;
        if (solid && spawn && Math.hypot(x - spawn.x, z - spawn.z) < 2) return;
        put(model, x, z, scale, ry, tint || shade);
        if (solid) this.obstacles.push({ x, z, r: solid * scale });
      };
      const tree = { clear: 1.3, solid: 0.3, smin: 0.9, smax: 1.5 };
      const grass = { clear: 0.7, smin: 0.8, smax: 1.5, spread: 1.0 };
      const tuft = () => at(id === 'deserto' || id === 'caverna' ? 'tuft_dry' : r() < 0.5 ? 'tuft' : 'tuft2', grass);
      const p = r();
      if (ch === 'g') {
        const n = Math.round((2 + r() * 3) * detail);
        for (let k = 0; k < n; k++) tuft();
        if (r() < 0.45 * detail && id !== 'pantano' && id !== 'caverna') at('flower', { ...grass, tint: FLOWER_COLORS[(r() * FLOWER_COLORS.length) | 0] });
        if (p < 0.06) at('bush');
        else if (p < 0.09 && id === 'floresta') at(r() < 0.3 ? 'blossom' : 'round', tree);
      } else if (ch === 'm') {
        if (p < 0.62) at(id === 'neve' ? 'pine_snow' : id === 'pantano' ? (r() < 0.6 ? 'swamp' : 'dead') : id === 'deserto' || id === 'caverna' ? 'dead' : r() < 0.45 ? 'pine' : r() < 0.82 ? 'round' : 'blossom', tree);
        if (r() < 0.25 && id !== 'neve') at('bush');
        if (id !== 'neve') { const n = Math.round((1 + r() * 2) * detail); for (let k = 0; k < n; k++) tuft(); }
      } else if (ch === 't') {
        if (p < 0.05) at('rock', { solid: 0.45, clear: 1.0 });
        else if (p < 0.2 * detail) at('tuft_dry', grass);
      } else if (ch === 'l') {
        if (p < 0.1) at('reed'); else if (p < 0.13) at('dead', tree);
      } else if (ch === 'b') {
        if (r() < 0.65) at('reed'); if (r() < 0.35) at('reed');
        if (p < 0.12) at('swamp', tree); else if (p < 0.24) at('mushroom');
        if (r() < 0.8 * detail) tuft();
      } else if (ch === 'a') {
        const shore = !is(i + 1, j, 'a') || !is(i - 1, j, 'a') || !is(i, j + 1, 'a') || !is(i, j - 1, 'a');
        if (id === 'floresta' || id === 'pantano' || id === 'masmorra') {
          if (p < 0.14) at('lily', { clear: 0.4, smin: 0.7, smax: 1.3 });
          if (shore && r() < 0.22) at('reed', { spread: 1.0 });
        }
      } else if (ch === 's') {
        if (p < 0.05 && id === 'deserto') at('cactus', { clear: 1.2, solid: 0.3, smin: 0.8, smax: 1.4 });
        else if (p < 0.09) at('rock', { solid: 0.45, clear: 1.0 });
        else if (p < 0.16 * detail) at('tuft_dry', grass);
      } else if (ch === 'r') {
        if (p < 0.16) at('rock', { solid: 0.45, clear: 1.0, smin: 0.7, smax: 1.6 });
        else if (p < 0.28 && id === 'caverna') at('stalagmite', { solid: 0.3, clear: 1.0, smin: 0.7, smax: 1.6 });
        else if (p < 0.36 && (id === 'caverna' || id === 'masmorra')) at('crystal', { solid: 0.3, clear: 0.9, smin: 0.7, smax: 1.5 });
      } else if (ch === 'n') {
        if (p < 0.03) at('rock', { solid: 0.45, clear: 1.0 }); else if (p < 0.06) at('pine_snow', tree);
      }
    }
    for (const [model, list] of batches) if (TALL.has(model)) for (const [x, z, sc] of list) shadows.push([x, z, 1.5 * sc, 4.5 * sc]);
    this.drawShadows(shadows);
    let tall = 0;
    for (const [model, list] of batches) if (TALL.has(model)) tall += list.length;
    const lines = !this.topDown && tall <= 450; // contorno custa o dobro de triângulos; em matas enormes fica de fora
    for (const [model, list] of batches) {
      const mat = model === 'crystal' ? this.matGlow : TALL.has(model) ? this.matTall : GRASS.has(model) ? this.matGrass : this.matSolid;
      const im = new THREE.InstancedMesh(modelGeo(model), mat, list.length);
      list.forEach(([x, z, sc, ry, shade], k) => {
        im.setMatrixAt(k, _m.compose(_p.set(x, 0, z), _q.setFromAxisAngle(UP, ry), _s.set(sc, sc, sc)));
        if (shade > 4) im.setColorAt(k, _c.setHex(shade)); else im.setColorAt(k, _c.setScalar(Math.min(1, shade)));
      });
      if (TALL.has(model) && this.topDown) im.renderOrder = 2;
      this.dynamic.add(im);
      if (lines && OUTLINED.has(model)) {
        const ol = new THREE.InstancedMesh(modelGeo(model), TALL.has(model) ? this.matLineTall : this.matLine, list.length);
        ol.instanceMatrix = im.instanceMatrix;
        this.dynamic.add(ol);
      }
    }
    const tile = (t, list) => {
      if (!t || !list.length) return;
      const im = new THREE.InstancedMesh(t.geometry, t.material, list.length);
      list.forEach(([x, z], k) => im.setMatrixAt(k, _m.multiplyMatrices(new THREE.Matrix4().makeTranslation(x, 0, z), t.matrix)));
      this.dynamic.add(im);
    };
    tile(this.tiles.large, large); tile(this.tiles.small, small);
  }

  // sombra das copas no chão, na direção do sol do jogo (o sol vem de -x, +z); sombras que se cruzam não somam
  drawShadows(list) {
    const g = this.shadeCanvas.getContext('2d'), k = this.shadeCanvas.width / (this.W * G);
    g.globalCompositeOperation = 'source-over'; g.fillStyle = '#fff'; g.fillRect(0, 0, this.shadeCanvas.width, this.shadeCanvas.height);
    g.globalCompositeOperation = 'darken';
    for (const [x, z, rad, h] of list) {
      const cx = (x + 0.27 * h) * k, cz = (z - 0.19 * h) * k, R = (rad + h * 0.12) * k;
      const gr = g.createRadialGradient(cx, cz, R * 0.15, cx, cz, R);
      const dark = Math.round(255 * (1 - 0.42 * Math.min(1, h / 12 + 0.4)));
      gr.addColorStop(0, `rgb(${dark},${dark},${dark})`); gr.addColorStop(1, '#fff');
      g.fillStyle = gr; g.beginPath(); g.ellipse(cx, cz, R * 1.15, R, -0.6, 0, Math.PI * 2); g.fill();
    }
    g.globalCompositeOperation = 'source-over';
    this.shadeTex.needsUpdate = true;
  }

  // Em volta do mapa: o chão do bioma continua até o horizonte e, ao longe, um fundo panorâmico renderizado no Blender
  // (cada bioma tem o seu). Na Estrada na mata, a mata do kit também continua além da borda.
  biomeExtras(id, kit, imageFloor) {
    const key = id + (kit ? ':kit' : '') + (imageFloor ? ':img' : '');
    if (key === this.extrasFor) return;
    for (const o of [...this.extras.children]) {
      o.traverse((c) => { if (c.isInstancedMesh) c.dispose(); if (c.isMesh && !c.isInstancedMesh) { c.geometry.dispose(); c.material.map && c.material.map.dispose(); c.material.dispose(); } });
      this.extras.remove(o);
    }
    this.far.material = this.farFlat; if (this.farTexMat) { this.farTexMat.map.dispose(); this.farTexMat.dispose(); this.farTexMat = null; }
    this.extrasFor = key;
    const w = this.W * G, h = this.H * G;
    if (kit) {
      const r = rng(4242), inst = {};
      const put = (m, x, z, s, tint = 1) => (inst[m] || (inst[m] = [])).push([x, 0, z, r() * 6.283, s, tint]);
      const BAND = 26;
      for (let z = -BAND; z < h + BAND; z += 3.3) for (let x = -BAND; x < w + BAND; x += 3.3) {
        const xx = x + (r() - 0.5) * 2.4, zz = z + (r() - 0.5) * 2.4;
        const d = Math.max(-xx, xx - w, -zz, zz - h);
        if (d < 1.5 || r() < 0.28) continue;
        const q = r(), tint = r() < 0.25 ? 0.35 + r() * 0.15 : 0.82 + r() * 0.24;
        put(d > 12 ? 'pinho_longe' : q < 0.4 ? 'pinho_a' : q < 0.75 ? 'pinho_b' : 'pinho_c', xx, zz, 0.75 + r() * 0.4, tint);
        if (d < 8 && r() < 0.5) put(r() < 0.5 ? 'samambaia' : 'capim', xx + 1.5, zz - 1, 0.8 + r() * 0.5);
      }
      this.extras.add(instanceKit(kit, inst, { topDown: this.topDown, chunk: 60 }));
    }
    // chão em volta com a textura do bioma
    const FT = FAR_GROUND[id] || FAR_GROUND.masmorra;
    groundTextures().then((T) => {
      if (this.extrasFor !== key) return;
      const t = T.list[FT[0]].clone(); t.repeat.set((w + 700) / 6, (h + 700) / 6); t.needsUpdate = true;
      this.farTexMat = new THREE.MeshLambertMaterial({ map: t, color: FT[1] });
      this.far.material = this.farTexMat;
    }).catch(() => {});
    if (this.topDown) return;
    const F = FUNDOS[id]; if (!F) return;
    new THREE.TextureLoader().loadAsync(F.img).then((tex) => {
      if (this.extrasFor !== key) { tex.dispose(); return; }
      tex.colorSpace = THREE.SRGBColorSpace; tex.wrapS = THREE.RepeatWrapping; tex.wrapT = THREE.ClampToEdgeWrapping;
      const RAD = F.rad || 300, BASE = F.base ?? -30, IMG = F.band || 210, CH = IMG * 2.6; tex.repeat.set(F.rep || 1, CH / IMG);
      const cyl = new THREE.Mesh(new THREE.CylinderGeometry(RAD, RAD, CH, 96, 1, true),
        new THREE.MeshBasicMaterial({ map: tex, side: THREE.BackSide, fog: false, depthWrite: false, transparent: !!F.alpha }));
      cyl.position.set(w / 2, BASE + CH / 2, h / 2); cyl.renderOrder = -1; cyl.name = 'fundo_bioma';
      this.extras.add(cyl);
    }).catch(() => {});
  }

  update(dt) {
    this.t += dt;
    this.water.map.offset.set(this.t * 0.035, this.t * 0.02);
    this.lava.map.offset.set(this.t * 0.012, -this.t * 0.008);
    this.foamMap.offset.set(-this.t * 0.03, this.t * 0.045);
    kitWind.value = this.t;
  }

  dispose() {
    this.disposed = true;
    for (const o of this.dynamic.children) o.dispose && o.dispose();
    for (const t of this.splatTex) t.dispose(); this.shadeTex.dispose(); if (this.texMat) this.texMat.dispose(); if (this.flatMat && this.flatMat !== this.ground.material) this.flatMat.dispose();
    for (const m of [this.far, this.ground, this.water.mesh, this.lava.mesh]) { m.geometry.dispose(); m.material.dispose(); }
    for (const t of [this.tex, this.water.alpha, this.water.map, this.lava.alpha, this.lava.map]) t.dispose();
    this.foam.geometry.dispose(); this.foam.material.dispose(); this.foamAlpha.dispose(); this.foamMap.dispose();
    for (const m of [this.matSolid, this.matTall, this.matGrass, this.matGlow, this.matLine, this.matLineTall]) m.dispose();
  }
}

// ---------------------------------------------------------------- vegetação avulsa (mapas prontos)
// list: [modelo, x, z, escala, rotação, altura do chão]. Mesmos modelos e materiais do terreno pintável.
export function plantGroup(list, { topDown = false } = {}) {
  const group = new THREE.Group();
  const matSolid = toon({ vertexColors: true });
  const matTall = topDown ? toon({ vertexColors: true, transparent: true, opacity: 0.4, depthWrite: false }) : windify(toon({ vertexColors: true }), 0.011);
  const matGrass = windify(toon({ vertexColors: true, side: THREE.DoubleSide }), 0.45);
  const matGlow = new THREE.MeshBasicMaterial({ vertexColors: true });
  const matLine = outlineMaterial(0.035), matLineTall = windify(outlineMaterial(0.045), 0.011);
  const batches = new Map();
  for (const it of list) { if (!MODELS[it[0]]) continue; if (!batches.has(it[0])) batches.set(it[0], []); batches.get(it[0]).push(it); }
  let tall = 0;
  for (const [model, l] of batches) if (TALL.has(model)) tall += l.length;
  const lines = !topDown && tall <= 700;
  for (const [model, l] of batches) {
    const mat = model === 'crystal' ? matGlow : TALL.has(model) ? matTall : GRASS.has(model) ? matGrass : matSolid;
    const im = new THREE.InstancedMesh(modelGeo(model), mat, l.length);
    l.forEach(([, x, z, sc, ry, y], k) => {
      im.setMatrixAt(k, _m.compose(_p.set(x, y - 0.05 * sc, z), _q.setFromAxisAngle(UP, ry), _s.set(sc, sc, sc)));
      im.setColorAt(k, _c.setScalar((TALL.has(model) ? 0.5 : 0.75) + ((k * 7919) % 100) / (TALL.has(model) ? 400 : 300))); // árvores mais escuras: pântano sombrio
    });
    im.computeBoundingSphere();
    if (TALL.has(model) && topDown) im.renderOrder = 2;
    group.add(im);
    if (lines && OUTLINED.has(model)) {
      const ol = new THREE.InstancedMesh(modelGeo(model), TALL.has(model) ? matLineTall : matLine, l.length);
      ol.instanceMatrix = im.instanceMatrix; ol.computeBoundingSphere();
      group.add(ol);
    }
  }
  group.userData.dispose = () => { for (const m of [matSolid, matTall, matGrass, matGlow, matLine, matLineTall]) m.dispose(); group.traverse((o) => o.isInstancedMesh && o.dispose()); };
  return group;
}

// bioma da encruzilhada: tarde de sol na mata de pinheiros, céu limpo, névoa leve e azulada ao longe, pólen no ar
BIOMES.push({ id: 'estrada', nome: 'Estrada na mata', fog: 0xb7c6c4, zenith: 0x4f8fd6, density: 0.0062, sky: 0xeaf1ff, ground: 0x5d6a33, hemi: 1.25, sun: 2.3, sunColor: 0xffe9c8, torch: 0, far: 0x5c7038, water: 0x2a4766,
  part: { color: 0xfff1b0, size: 0.07, n: 90, vy: -0.05, glow: true } });
// bioma do covil: pântano enevoado, névoa mais rala que o pântano comum (o mapa é grande)
BIOMES.push({ id: 'covil', nome: 'Covil (pântano)', fog: 0x4c5a49, zenith: 0x1d2622, density: 0.016, sky: 0xb9c9a8, ground: 0x2c3a26, hemi: 1.15, sun: 0.75, sunColor: 0xd8e8b8, torch: 4, far: 0x3f4c38, water: 0x5f8a44,
  part: { color: 0xd2ff6a, size: 0.14, n: 140, vy: 0.0, glow: true } });
