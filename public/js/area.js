// Áreas de efeito de magia (D&D 2024): formas, desenho, quem é atingido e a ferramenta tática do jogador.
//
// Formas (Livro do Jogador 2024): Cone, Cubo, Cilindro, Linha, Esfera e Emanação (nova em 2024).
// - Cone: sai do ponto de origem numa direção; a largura num ponto é igual à distância até a origem.
// - Cubo: a origem fica numa face; o tamanho é o lado.  "Pessoal" = sai de você; com alcance = posto à distância.
// - Cilindro: círculo de raio dado (a altura não importa no mapa visto de cima).
// - Linha: comprimento e largura (normalmente 1,5 m).
// - Esfera: raio a partir de um ponto (que fica numa interseção da grade).
// - Emanação: sai da criatura em todas as direções e vai junto com ela; quem a cria fica de fora, a não ser que queira.
import * as THREE from 'three';

const G = 2;   // 1 quadrado = 2 unidades
const M2U = 2 / 1.5;   // metros para unidades (igual ao combate-ui; aqui sem importar, para não criar ciclo com common.js)
export const SHAPES = {
  esfera:   { nome: 'Esfera',   tam: 'Raio',        icone: '●', placed: true },
  cilindro: { nome: 'Cilindro', tam: 'Raio',        icone: '◉', placed: true },
  cubo:     { nome: 'Cubo',     tam: 'Lado',        icone: '■', placed: 'range' },
  cone:     { nome: 'Cone',     tam: 'Comprimento', icone: '◣', placed: false },
  linha:    { nome: 'Linha',    tam: 'Comprimento', icone: '━', placed: false },
  emanacao: { nome: 'Emanação', tam: 'Distância',   icone: '◎', placed: false },
};
// alcance 0 = Pessoal (sai de você). Valores do Livro do Jogador 2024 em metros (1,5 m por quadrado).
export const PRESETS = [
  { nome: 'Bola de Fogo', forma: 'esfera', tam: 6, alcance: 45, cor: 0xff7a2e },
  { nome: 'Mãos Flamejantes', forma: 'cone', tam: 4.5, alcance: 0, cor: 0xff8a3a },
  { nome: 'Relâmpago', forma: 'linha', tam: 30, larg: 1.5, alcance: 0, cor: 0x7fd8ff },
  { nome: 'Cone de Frio', forma: 'cone', tam: 18, alcance: 0, cor: 0x9fe6ff },
  { nome: 'Onda Trovejante', forma: 'cubo', tam: 4.5, alcance: 0, cor: 0x9fb8ff },
  { nome: 'Guardiões Espirituais', forma: 'emanacao', tam: 4.5, alcance: 0, cor: 0xffe39a },
  { nome: 'Despedaçar', forma: 'esfera', tam: 3, alcance: 18, cor: 0xc9a8ff },
  { nome: 'Coluna de Chamas', forma: 'cilindro', tam: 3, alcance: 18, cor: 0xffb347 },
  { nome: 'Nuvem de Adagas', forma: 'cubo', tam: 1.5, alcance: 18, cor: 0xdfe6f0 },
  { nome: 'Teia', forma: 'cubo', tam: 6, alcance: 18, cor: 0xe8e8e8 },
  { nome: 'Névoa Obscurecente', forma: 'esfera', tam: 6, alcance: 36, cor: 0xb8c4d0 },
  { nome: 'Sopro Ácido (dragão negro)', forma: 'linha', tam: 18, larg: 1.5, alcance: 0, cor: 0x9bff4a },
];
export const DEFAULT_COLOR = 0xb58cff;

// ---- geometria: contorno da área em XZ (lista de [x, z]), usado para desenhar e para testar quem está dentro
export function outline(a) {
  const S = a.tam * M2U, pts = [];
  const dx = Math.sin(a.dir || 0), dz = Math.cos(a.dir || 0), px = dz, pz = -dx;   // frente e lado
  if (a.forma === 'esfera' || a.forma === 'cilindro' || a.forma === 'emanacao') {
    const r = a.forma === 'emanacao' ? S + (a.half || 1) : S;   // emanação: conta a partir da borda de quem a cria
    for (let i = 0; i < 72; i++) { const t = (i / 72) * Math.PI * 2; pts.push([a.cx + Math.cos(t) * r, a.cz + Math.sin(t) * r]); }
  } else if (a.forma === 'cone') {
    pts.push([a.ox, a.oz], [a.ox + dx * S + px * S / 2, a.oz + dz * S + pz * S / 2], [a.ox + dx * S - px * S / 2, a.oz + dz * S - pz * S / 2]);
  } else if (a.forma === 'linha') {
    const W = (a.larg || 1.5) * M2U / 2;
    pts.push([a.ox + px * W, a.oz + pz * W], [a.ox + dx * S + px * W, a.oz + dz * S + pz * W], [a.ox + dx * S - px * W, a.oz + dz * S - pz * W], [a.ox - px * W, a.oz - pz * W]);
  } else if (a.forma === 'cubo') {
    if (a.alcance > 0) { const h = S / 2; pts.push([a.cx - h, a.cz - h], [a.cx + h, a.cz - h], [a.cx + h, a.cz + h], [a.cx - h, a.cz + h]); }
    else { const h = S / 2; pts.push([a.ox + px * h, a.oz + pz * h], [a.ox + dx * S + px * h, a.oz + dz * S + pz * h], [a.ox + dx * S - px * h, a.oz + dz * S - pz * h], [a.ox - px * h, a.oz - pz * h]); }
  }
  return pts;
}
function inPoly(pts, x, z) {
  let c = false;
  for (let i = 0, j = pts.length - 1; i < pts.length; j = i++) {
    const [xi, zi] = pts[i], [xj, zj] = pts[j];
    if ((zi > z) !== (zj > z) && x < ((xj - xi) * (z - zi)) / (zj - zi) + xi) c = !c;
  }
  return c;
}
// criaturas atingidas: basta a área cobrir parte do espaço dela (testa pontos dentro de cada quadrado ocupado)
export function hits(a, creatures, parts) {
  const polys = parts || [outline(a)], out = [];
  for (const c of creatures) {
    if (a.forma === 'emanacao' && a.dono && c.key === a.dono) continue;   // quem cria a emanação fica de fora
    const n = Math.max(1, c.size || 1), half = (n * G) / 2, k = n * 2;
    let hit = false;
    for (let i = 0; i < k && !hit; i++) for (let j = 0; j < k && !hit; j++) {
      const x = c.x - half + ((i + 0.5) / k) * half * 2, z = c.z - half + ((j + 0.5) / k) * half * 2;
      if (polys.some((pts) => inPoly(pts, x, z))) hit = true;
    }
    if (hit) out.push(c);
  }
  return out;
}

// ---- paredes e objetos cortam a área (linha de efeito)
// A área só chega onde uma linha reta desde a origem não bate numa parede, porta fechada ou objeto sólido.
// Raios saem da origem: para cada direção, o trecho [entrada, saída] da área é cortado no primeiro obstáculo.
// Raios consecutivos que chegam formam um polígono; onde a parede corta tudo, a área se divide.
export const originOf = (a) => (a.vx !== undefined ? [a.vx, a.vz] : SHAPES[a.forma].placed && a.alcance > 0 ? [a.cx, a.cz] : [a.ox, a.oz]);
function raySeg(ox, oz, ux, uz, s) {   // distância até o segmento, ou Infinity
  const ex = s.x2 - s.x1, ez = s.z2 - s.z1, den = ux * ez - uz * ex;
  if (Math.abs(den) < 1e-9) return Infinity;
  const wx = s.x1 - ox, wz = s.z1 - oz;
  const t = (wx * ez - wz * ex) / den, k = (wx * uz - wz * ux) / den;
  return t > 1e-4 && k >= -1e-6 && k <= 1 + 1e-6 ? t : Infinity;
}
function rayCircle(ox, oz, ux, uz, c) {
  const wx = c.x - ox, wz = c.z - oz, b = wx * ux + wz * uz, d2 = wx * wx + wz * wz - c.r * c.r;
  if (d2 <= 0) return Infinity;   // a origem está dentro do objeto: ele não conta
  const disc = b * b - d2; if (disc < 0 || b < 0) return Infinity;
  return b - Math.sqrt(disc);
}
export function visibleParts(a, B) {
  const poly = outline(a);
  if (!B || (!B.segs.length && !B.circles.length)) return [poly];
  const [ox, oz] = originOf(a);
  let reach = 0; for (const [x, z] of poly) reach = Math.max(reach, Math.hypot(x - ox, z - oz));
  reach += 0.5;
  const near = (x1, z1, x2, z2) => {   // segmento perto o bastante para importar
    const vx = x2 - x1, vz = z2 - z1, l2 = vx * vx + vz * vz || 1;
    const t = Math.max(0, Math.min(1, ((ox - x1) * vx + (oz - z1) * vz) / l2));
    return Math.hypot(x1 + vx * t - ox, z1 + vz * t - oz) < reach;
  };
  const segs = B.segs.filter((s) => near(s.x1, s.z1, s.x2, s.z2));
  const circles = B.circles.filter((c) => Math.hypot(c.x - ox, c.z - oz) - c.r < reach);
  if (!segs.length && !circles.length) return [poly];
  const inside = inPoly(poly, ox, oz);
  // direções: uniformes + vértices da área + pontas dos obstáculos (para cortar reto nas quinas)
  const base = Math.atan2(poly[0][1] - oz, poly[0][0] - ox);
  let lo = 0, hi = Math.PI * 2, angs = [];
  if (!inside) {   // só o leque que enxerga a área
    const rel = poly.map(([x, z]) => { let d = Math.atan2(z - oz, x - ox) - base; while (d > Math.PI) d -= Math.PI * 2; while (d < -Math.PI) d += Math.PI * 2; return d; });
    lo = base + Math.min(...rel); hi = base + Math.max(...rel);
  }
  const N = inside ? 540 : 260;
  for (let i = 0; i <= N; i++) angs.push(lo + ((hi - lo) * i) / N);
  const addA = (x, z) => {
    let t = Math.atan2(z - oz, x - ox);
    if (inside) { if (t < 0) t += Math.PI * 2; }
    else { while (t < lo) t += Math.PI * 2; while (t > lo + Math.PI * 2) t -= Math.PI * 2; if (t > hi) return; }
    angs.push(t - 1e-5, t + 1e-5);
  };
  for (const [x, z] of poly) addA(x, z);
  for (const s of segs) { addA(s.x1, s.z1); addA(s.x2, s.z2); }
  for (const c of circles) {
    const d = Math.hypot(c.x - ox, c.z - oz), t0 = Math.atan2(c.z - oz, c.x - ox), w = Math.asin(Math.min(1, c.r / d));
    addA(ox + Math.cos(t0 + w) * d, oz + Math.sin(t0 + w) * d); addA(ox + Math.cos(t0 - w) * d, oz + Math.sin(t0 - w) * d);
  }
  angs.sort((p, q) => p - q);
  // para cada direção: trecho da área [rin, rout] cortado pelo primeiro obstáculo
  let blocked = false;
  const rays = angs.map((t) => {
    const ux = Math.cos(t), uz = Math.sin(t);
    let rin = Infinity, rout = -Infinity;
    if (inside) { rin = 0; rout = 0; }
    for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) {
      const d = raySeg(ox, oz, ux, uz, { x1: poly[j][0], z1: poly[j][1], x2: poly[i][0], z2: poly[i][1] });
      if (d < Infinity) { rin = Math.min(rin, d); rout = Math.max(rout, d); }
    }
    if (inside) rin = 0;
    let rb = Infinity;
    for (const s of segs) rb = Math.min(rb, raySeg(ox, oz, ux, uz, s));
    for (const c of circles) rb = Math.min(rb, rayCircle(ox, oz, ux, uz, c));
    if (rb < rout - 0.02 && rb > rin) blocked = true;
    const far = Math.min(rout, rb);
    return far - rin > 0.02 && rout > rin ? { ux, uz, rin, far } : null;
  });
  if (!blocked && rays.every(Boolean)) return [poly];
  if (!blocked && !inside) return [poly];
  // trechos seguidos viram polígonos (borda de fora na ida, de dentro na volta)
  const parts = []; let run = [];
  const flush = () => {
    if (run.length > 1) {
      const pts = run.map((r) => [ox + r.ux * r.far, oz + r.uz * r.far]);
      if (inside) pts.push([ox, oz]);
      else for (let i = run.length - 1; i >= 0; i--) pts.push([ox + run[i].ux * run[i].rin, oz + run[i].uz * run[i].rin]);
      parts.push(pts);
    }
    run = [];
  };
  if (rays.every(Boolean)) {
    if (inside) return [rays.map((r) => [ox + r.ux * r.far, oz + r.uz * r.far])];   // nada cortou: a área inteira
  } else if (inside) {   // volta completa: começa num raio bloqueado para os trechos não ficarem partidos na emenda
    const k = rays.findIndex((r) => !r); rays.push(...rays.splice(0, k));
  }
  for (const r of rays) { if (r) run.push(r); else flush(); }
  flush();
  return parts;
}

// ---- desenho
function ribbon(pts, w) {   // faixa fechada ao longo do contorno (borda grossa, visível de cima)
  const pos = [], idx = [], n = pts.length;
  for (let i = 0; i < n; i++) {
    const [ax, az] = pts[(i - 1 + n) % n], [bx, bz] = pts[i], [cx, cz] = pts[(i + 1) % n];
    let n1x = -(bz - az), n1z = bx - ax; const l1 = Math.hypot(n1x, n1z) || 1; n1x /= l1; n1z /= l1;
    let n2x = -(cz - bz), n2z = cx - bx; const l2 = Math.hypot(n2x, n2z) || 1; n2x /= l2; n2z /= l2;
    let mx = n1x + n2x, mz = n1z + n2z; const ml = Math.hypot(mx, mz) || 1; mx /= ml; mz /= ml;
    const k = Math.min(3, 1 / Math.max(0.3, mx * n1x + mz * n1z));
    pos.push(bx - mx * w * k, 0, bz - mz * w * k, bx + mx * w * k, 0, bz + mz * w * k);
    const a = i * 2, b = ((i + 1) % n) * 2;
    idx.push(a, b, a + 1, b, b + 1, a + 1);
  }
  const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3)); g.setIndex(idx);
  return g;
}
function curtain(pts, h) {   // parede baixa e transparente na borda (para quem vê de lado, em 1ª/3ª pessoa)
  const pos = [], uv = [], idx = [], n = pts.length;
  for (let i = 0; i <= n; i++) { const [x, z] = pts[i % n]; pos.push(x, 0, z, x, h, z); uv.push(i / n, 0, i / n, 1); }
  for (let i = 0; i < n; i++) { const a = i * 2; idx.push(a, a + 2, a + 1, a + 2, a + 3, a + 1); }
  const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3)); g.setAttribute('uv', new THREE.Float32BufferAttribute(uv, 2)); g.setIndex(idx);
  return g;
}
let fadeTex = null;
function fadeTexture() {
  if (fadeTex) return fadeTex;
  const c = document.createElement('canvas'); c.width = 4; c.height = 64; const g = c.getContext('2d');
  const gr = g.createLinearGradient(0, 64, 0, 0); gr.addColorStop(0, 'rgba(255,255,255,1)'); gr.addColorStop(1, 'rgba(255,255,255,0)');
  g.fillStyle = gr; g.fillRect(0, 0, 4, 64); fadeTex = new THREE.CanvasTexture(c); return fadeTex;
}
// grupo com preenchimento, borda e cortina. top: visão de cima do mestre (desenha por cima de tudo)
export function buildMesh(a, { top = false, y = 0, parts = null } = {}) {
  const full = outline(a), color = new THREE.Color(a.cor || DEFAULT_COLOR);
  parts = parts || [full];
  const grp = new THREE.Group(); grp.position.y = y;
  const mats = [];
  const common = { transparent: true, depthWrite: false, depthTest: !top, side: THREE.DoubleSide, fog: false };
  const cut = parts.length !== 1 || parts[0] !== full;
  if (cut) {   // a área inteira, bem apagada, para mostrar o que a parede bloqueou
    const gs = new THREE.ShapeGeometry(new THREE.Shape(full.map(([x, z]) => new THREE.Vector2(x, -z)))); gs.rotateX(-Math.PI / 2);
    const ghost = new THREE.Mesh(gs, new THREE.MeshBasicMaterial({ color: 0x9a9aa8, opacity: 0.07, ...common }));
    ghost.position.y = 0.04; ghost.renderOrder = 18; grp.add(ghost); mats.push([ghost.material, 0.07]);
    const gl = new THREE.Mesh(ribbon(full, top ? 0.05 : 0.035), new THREE.MeshBasicMaterial({ color: 0xc8c8d4, opacity: 0.35, ...common }));
    gl.position.y = 0.05; gl.renderOrder = 18; grp.add(gl); mats.push([gl.material, 0.35]);
  }
  for (const pts of parts) addPart(grp, pts, a, color, top, common, mats);
  grp.userData.mats = mats;
  grp.userData.setAlpha = (k) => { for (const [m, o] of mats) m.opacity = o * k; };
  return grp;
}
function addPart(grp, pts, a, color, top, common, mats) {
  const shape = new THREE.Shape(pts.map(([x, z]) => new THREE.Vector2(x, -z)));
  const fillGeo = new THREE.ShapeGeometry(shape); fillGeo.rotateX(-Math.PI / 2);
  const fo = top ? 0.34 : 0.26;
  const fill = new THREE.Mesh(fillGeo, new THREE.MeshBasicMaterial({ color, opacity: fo, ...common }));
  fill.position.y = 0.06; fill.renderOrder = 20; grp.add(fill); mats.push([fill.material, fo]);
  const edge = new THREE.Mesh(ribbon(pts, top ? 0.16 : 0.1), new THREE.MeshBasicMaterial({ color: color.clone().lerp(new THREE.Color(0xffffff), 0.35), opacity: 0.95, ...common }));
  edge.position.y = 0.08; edge.renderOrder = 21; grp.add(edge); mats.push([edge.material, 0.95]);
  if (!top) {
    const wall = new THREE.Mesh(curtain(pts, a.forma === 'cilindro' || a.forma === 'esfera' ? 2.6 : 1.4), new THREE.MeshBasicMaterial({ color, map: fadeTexture(), opacity: 0.55, blending: THREE.AdditiveBlending, ...common }));
    wall.renderOrder = 19; grp.add(wall); mats.push([wall.material, 0.55]);
  }
}
export function disposeMesh(g) { g.traverse((o) => { if (o.geometry) o.geometry.dispose(); if (o.material) o.material.dispose(); }); }

// círculo de alcance (tracejado) em volta de quem conjura
export function rangeCircle(r, color = 0xffffff) {
  const pts = []; for (let i = 0; i <= 128; i++) { const t = (i / 128) * Math.PI * 2; pts.push(new THREE.Vector3(Math.cos(t) * r, 0.1, Math.sin(t) * r)); }
  const line = new THREE.Line(new THREE.BufferGeometry().setFromPoints(pts), new THREE.LineDashedMaterial({ color, dashSize: 0.6, gapSize: 0.4, transparent: true, opacity: 0.85, depthTest: false, fog: false }));
  line.computeLineDistances(); line.renderOrder = 22; return line;
}

export const fmtArea = (a) => {
  const s = SHAPES[a.forma];
  const tam = String(a.tam).replace('.', ',') + ' m';
  return `${s.nome} · ${s.tam.toLowerCase()} ${tam}` + (a.forma === 'linha' ? ` × ${String(a.larg || 1.5).replace('.', ',')} m` : '') + (a.alcance ? ` · alcance ${String(a.alcance).replace('.', ',')} m` : ' · pessoal');
};

// ---- ferramenta do jogador: escolher a área, ir para a visão tática, posicionar com o dedo e confirmar
const ease = (t) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);
export class AreaTool {
  // ctx: { scene, camera, canvas, caster: () => ({x, z, y, half, key, yaw}), ground: (x, z) => y, creatures: () => [...], onConfirm(area), onCancel() }
  constructor(ctx) {
    this.ctx = ctx; this.active = false; this.phase = 'off';   // off | entrando | tatico | saindo
    this.t = 0; this.zoom = 1; this.area = null; this.mesh = null; this.range = null;
    this.from = { p: new THREE.Vector3(), q: new THREE.Quaternion() };
    this.top = { p: new THREE.Vector3(), q: new THREE.Quaternion() };
    this.ray = new THREE.Raycaster(); this.plane = new THREE.Plane(new THREE.Vector3(0, 1, 0), 0);
    this.ptrs = new Map(); this.hitRings = [];
    const c = ctx.canvas;
    c.addEventListener('pointerdown', (e) => this.down(e), true);
    c.addEventListener('pointermove', (e) => this.moveP(e), true);
    c.addEventListener('pointerup', (e) => this.up(e), true);
    c.addEventListener('pointercancel', (e) => this.up(e), true);
    c.addEventListener('wheel', (e) => { if (this.phase === 'tatico') { e.preventDefault(); this.zoomBy(e.deltaY > 0 ? 1.12 : 1 / 1.12); } }, { passive: false });
  }
  get busy() { return this.phase !== 'off'; }

  // começa: area = { nome, forma, tam, larg, alcance, cor }
  start(area) {
    const k = this.ctx.caster();
    this.area = { ...area, half: k.half, dono: k.key, dir: k.yaw, ox: k.x, oz: k.z, cx: k.x, cz: k.z };
    // origem da linha de efeito: o ponto escolhido (áreas postas) ou o centro de quem conjura
    if (!(SHAPES[area.forma].placed && area.alcance > 0)) { this.area.vx = k.x; this.area.vz = k.z; }
    if (SHAPES[area.forma].placed && area.alcance > 0) {   // começa um pouco à frente, dentro do alcance
      const d = Math.min(area.alcance * M2U, Math.max(4, area.tam * M2U + 2));
      this.area.cx = k.x + Math.sin(k.yaw) * d; this.area.cz = k.z + Math.cos(k.yaw) * d;
    }
    this.fixOrigin(); this.snap();
    this.phase = 'entrando'; this.t = 0; this.zoom = 1; this.active = true;
    this.camYaw = k.camYaw;
    // enquadra a área e um pouco em volta; o alcance inteiro de magias longas (45 m) deixaria tudo minúsculo — o − afasta
    const S = area.tam * M2U, R = area.alcance * M2U;
    this.reach = Math.max(10, SHAPES[area.forma].placed && R ? Math.min(R + S, Math.hypot(this.area.cx - k.x, this.area.cz - k.z) + S * 1.4) : S * 1.15 + k.half) + 1.5;
    this.from.p.copy(this.ctx.camera.position); this.from.q.copy(this.ctx.camera.quaternion);
    this.rebuild();
    const r = this.area.alcance > 0 ? this.area.alcance * M2U : 0;
    if (r) { this.range = rangeCircle(r + k.half, 0xffffff); this.range.position.set(k.x, k.y + 0.05, k.z); this.ctx.scene.add(this.range); }
    document.body.classList.add('modo-tatico');
  }
  fixOrigin() {   // cone, linha e cubo pessoal saem da borda de quem conjura, na direção escolhida
    const a = this.area, k = this.ctx.caster();
    if (!(SHAPES[a.forma].placed && a.alcance > 0)) {
      if (a.forma === 'emanacao') { a.cx = k.x; a.cz = k.z; a.ox = k.x; a.oz = k.z; return; }
      a.ox = k.x + Math.sin(a.dir) * k.half; a.oz = k.z + Math.cos(a.dir) * k.half;
    }
  }
  snap() {   // esfera e cilindro: centro numa interseção da grade; cubo posto: ocupa quadrados inteiros
    const a = this.area;
    if (!(SHAPES[a.forma].placed && a.alcance > 0)) return;
    if (a.forma === 'cubo') {
      const n = Math.max(1, Math.round(a.tam / 1.5)), off = n % 2 ? 0.5 : 0;
      a.cx = (Math.round(a.cx / G - off) + off) * G; a.cz = (Math.round(a.cz / G - off) + off) * G;
    } else { a.cx = Math.round(a.cx / G) * G; a.cz = Math.round(a.cz / G) * G; }
  }
  rebuild() {
    if (this.mesh) { this.ctx.scene.remove(this.mesh); disposeMesh(this.mesh); }
    const k = this.ctx.caster();
    if (SHAPES[this.area.forma].placed && this.area.alcance > 0) { this.area.vx = this.area.cx; this.area.vz = this.area.cz; }
    const parts = visibleParts(this.area, this.ctx.blockers ? this.ctx.blockers() : null);
    this.mesh = buildMesh(this.area, { top: true, y: k.y + 0.02, parts }); this.ctx.scene.add(this.mesh);
    // marca quem seria atingido
    const hit = hits(this.area, this.ctx.creatures(), parts);
    while (this.hitRings.length < hit.length) {
      const m = new THREE.Mesh(new THREE.RingGeometry(0.85, 1.05, 40), new THREE.MeshBasicMaterial({ color: 0xff5050, transparent: true, depthTest: false, side: THREE.DoubleSide, fog: false }));
      m.rotation.x = -Math.PI / 2; m.renderOrder = 23; this.ctx.scene.add(m); this.hitRings.push(m);
    }
    this.hitRings.forEach((m, i) => {
      const c = hit[i]; m.visible = !!c; if (!c) return;
      m.scale.setScalar(c.size || 1); m.position.set(c.x, this.ctx.ground(c.x, c.z) + 0.12, c.z);
      m.material.color.set(c.ally ? 0x6fe39a : 0xff5050);
    });
    this.hitList = hit;
    this.ctx.onChange && this.ctx.onChange(this.area, hit);
  }
  topPose() {   // câmera bem acima de quem conjura, olhando para baixo, com a frente do personagem para cima na tela
    const k = this.ctx.caster(), a = this.area, cam = this.ctx.camera;
    const reach = this.reach;   // enquadramento fixo enquanto arrasta (senão o mapa fugiria do dedo)
    const aspect = Math.min(cam.aspect, 1.0);   // na vertical o celular vê menos
    const h = (reach / Math.tan(THREE.MathUtils.degToRad(cam.fov / 2)) / Math.max(0.55, aspect)) * this.zoom;
    this.top.p.set(k.x, k.y + Math.max(10, h), k.z);
    const e = new THREE.Euler(-Math.PI / 2, this.camYaw, 0, 'YXZ');
    this.top.q.setFromEuler(e);
  }
  zoomBy(f) { this.zoom = Math.max(0.35, Math.min(4, this.zoom * f)); }

  // chamado depois que o jogo já posicionou a câmera do jeito normal: mistura com a pose tática
  apply(dt) {
    if (this.phase === 'off') return false;
    const cam = this.ctx.camera;
    this.topPose();
    if (this.phase === 'entrando' || this.phase === 'saindo') {
      this.t += (dt / 0.9) * (this.speed || 1);
      const k = ease(Math.min(1, this.t)), w = this.phase === 'entrando' ? k : 1 - k;
      const normalP = this.phase === 'entrando' ? this.from.p : cam.position.clone();
      const normalQ = this.phase === 'entrando' ? this.from.q : cam.quaternion.clone();
      const p = normalP.clone().lerp(this.top.p, w);
      p.y += Math.sin(w * Math.PI) * 3;   // um arco: a câmera sobe por cima do personagem
      cam.position.copy(p); cam.quaternion.copy(normalQ).slerp(this.top.q, w);
      if (this.t >= 1) {
        if (this.phase === 'entrando') this.phase = 'tatico';
        else { this.phase = 'off'; this.active = false; }
      }
    } else { cam.position.copy(this.top.p); cam.quaternion.copy(this.top.q); }
    this.fadeTatico = this.phase === 'saindo' ? 1 - Math.min(1, this.t) : this.phase === 'entrando' ? Math.min(1, this.t) : 1;
    if (this.mesh) this.mesh.userData.setAlpha(this.fadeTatico);
    if (this.range) this.range.material.opacity = 0.85 * this.fadeTatico;
    if (this.phase === 'off') this.cleanup();
    return true;
  }
  cleanup() {
    if (this.mesh) { this.ctx.scene.remove(this.mesh); disposeMesh(this.mesh); this.mesh = null; }
    if (this.range) { this.ctx.scene.remove(this.range); this.range.geometry.dispose(); this.range = null; }
    for (const m of this.hitRings) m.visible = false;
  }
  finish(ok) {
    if (this.phase !== 'tatico' && this.phase !== 'entrando') return;
    document.body.classList.remove('modo-tatico');
    const area = this.area;
    this.phase = 'saindo'; this.t = 0;
    for (const m of this.hitRings) m.visible = false;
    if (ok) this.ctx.onConfirm(area, this.hitList || []); else this.ctx.onCancel && this.ctx.onCancel();
  }

  // ---- dedo: arrasta para posicionar (ou apontar); dois dedos: aproxima/afasta
  pick(e) {
    const r = this.ctx.canvas.getBoundingClientRect();
    const v = new THREE.Vector2(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1);
    this.ray.setFromCamera(v, this.ctx.camera);
    this.plane.constant = -this.ctx.caster().y;
    const p = new THREE.Vector3(); return this.ray.ray.intersectPlane(this.plane, p) ? p : null;
  }
  down(e) {
    if (this.phase !== 'tatico') { if (this.busy) { e.stopImmediatePropagation(); e.preventDefault(); } return; }
    e.stopImmediatePropagation(); e.preventDefault();
    this.ctx.canvas.setPointerCapture(e.pointerId);
    this.ptrs.set(e.pointerId, { x: e.clientX, y: e.clientY });
    if (this.ptrs.size === 1) this.aim(e);
    else this.pinch0 = { d: this.pinchDist(), z: this.zoom };
  }
  moveP(e) {
    if (!this.busy) return;
    e.stopImmediatePropagation();
    if (!this.ptrs.has(e.pointerId)) return;
    this.ptrs.set(e.pointerId, { x: e.clientX, y: e.clientY });
    if (this.ptrs.size >= 2 && this.pinch0) { const d = this.pinchDist(); if (d > 10) this.zoom = Math.max(0.35, Math.min(4, this.pinch0.z * (this.pinch0.d / d))); }
    else if (this.ptrs.size === 1) this.aim(e);
  }
  up(e) { if (!this.busy) return; e.stopImmediatePropagation(); this.ptrs.delete(e.pointerId); if (this.ptrs.size < 2) this.pinch0 = null; }
  pinchDist() { const [a, b] = [...this.ptrs.values()]; return Math.hypot(a.x - b.x, a.y - b.y); }
  aim(e) {
    const p = this.pick(e); if (!p) return;
    this.aimAt(p.x, p.z);
  }
  aimAt(x, z) {
    const a = this.area, k = this.ctx.caster();
    if (SHAPES[a.forma].placed && a.alcance > 0) {
      let dx = x - k.x, dz = z - k.z; const d = Math.hypot(dx, dz), max = a.alcance * M2U + k.half;
      if (d > max) { dx *= max / d; dz *= max / d; }
      a.cx = k.x + dx; a.cz = k.z + dz; this.snap();
      // o encaixe na grade pode empurrar para fora do alcance: volta um quadrado para dentro
      for (let i = 0; i < 4 && Math.hypot(a.cx - k.x, a.cz - k.z) > max + 0.01; i++) {
        if (Math.abs(a.cx - k.x) >= Math.abs(a.cz - k.z)) a.cx -= Math.sign(a.cx - k.x) * G; else a.cz -= Math.sign(a.cz - k.z) * G;
      }
      a.dir = Math.atan2(a.cx - k.x, a.cz - k.z);
    } else if (a.forma !== 'emanacao') {
      if (Math.hypot(x - k.x, z - k.z) < 0.3) return;
      a.dir = Math.atan2(x - k.x, z - k.z); this.fixOrigin();
    }
    this.rebuild();
  }
}

// ---- grimório de feiticeiro (até o 3º círculo) — dados do 5eTools (Livro do Jogador 2024, XPHB)
// Pés convertidos para metros como no livro em português (1,5 m a cada 5 pés). Nomes em português traduzidos aqui;
// o nome original fica ao lado para conferir no livro. tempo: 'action' (ação Magia) ou 'bonus'.
// Com forma: abre a ferramenta de área. Sem forma: magia de alvo (escolhe a criatura, como antes).
const F = (circ, nome, en, x) => ({ circ, nome, en, tempo: 'action', ...x });
export const GRIMORIO_FEITICEIRO = [
  F(0, 'Respingo Ácido', 'Acid Splash', { forma: 'esfera', tam: 1.5, alcance: 18, efeito: '1d6 ácido · TR Des', cor: 0x9bff4a }),
  F(0, 'Trovão', 'Thunderclap', { forma: 'emanacao', tam: 1.5, alcance: 0, efeito: '1d6 trovão · TR Con', cor: 0x9fb8ff }),
  F(0, 'Raio de Fogo', 'Fire Bolt', { alvo: 36, efeito: '1d10 fogo · ataque' }),
  F(0, 'Explosão Feiticeira', 'Sorcerous Burst', { alvo: 36, efeito: '1d8 do tipo à escolha · ataque' }),
  F(0, 'Raio de Gelo', 'Ray of Frost', { alvo: 18, efeito: '1d8 frio · ataque' }),
  F(0, 'Lasca Mental', 'Mind Sliver', { alvo: 18, efeito: '1d6 psíquico · TR Int' }),
  F(1, 'Mãos Flamejantes', 'Burning Hands', { forma: 'cone', tam: 4.5, alcance: 0, efeito: '3d6 fogo · TR Des', cor: 0xff8a3a }),
  F(1, 'Spray de Cores', 'Color Spray', { forma: 'cone', tam: 4.5, alcance: 0, efeito: 'Cego · TR Con', cor: 0xff9ae6 }),
  F(1, 'Onda Trovejante', 'Thunderwave', { forma: 'cubo', tam: 4.5, alcance: 0, efeito: '2d8 trovão, empurra 3 m · TR Con', cor: 0x9fb8ff }),
  F(1, 'Sono', 'Sleep', { forma: 'esfera', tam: 1.5, alcance: 18, efeito: 'Incapacitado · TR Sab', cor: 0xc8b8ff }),
  F(1, 'Graxa', 'Grease', { forma: 'cubo', tam: 3, alcance: 18, efeito: 'terreno difícil, Caído · TR Des', cor: 0xc9b26a }),
  F(1, 'Névoa Obscurecente', 'Fog Cloud', { forma: 'esfera', tam: 6, alcance: 36, efeito: 'escuridão densa', cor: 0xb8c4d0 }),
  F(1, 'Orbe Cromático', 'Chromatic Orb', { alvo: 27, efeito: '3d8 do tipo à escolha · ataque' }),
  F(1, 'Mísseis Mágicos', 'Magic Missile', { alvo: 36, efeito: '3 dardos de 1d4+1 energia' }),
  F(1, 'Faca de Gelo', 'Ice Knife', { alvo: 18, efeito: '1d10 perfurante + 2d6 frio em volta · TR Des' }),
  F(2, 'Despedaçar', 'Shatter', { forma: 'esfera', tam: 3, alcance: 18, efeito: '3d8 trovão · TR Con', cor: 0xc9a8ff }),
  F(2, 'Nuvem de Adagas', 'Cloud of Daggers', { forma: 'cubo', tam: 1.5, alcance: 18, efeito: '4d4 cortante', cor: 0xdfe6f0 }),
  F(2, 'Teia', 'Web', { forma: 'cubo', tam: 6, alcance: 18, efeito: 'Impedido · TR Des', cor: 0xe8e8e8 }),
  F(2, 'Escuridão', 'Darkness', { forma: 'esfera', tam: 4.5, alcance: 18, efeito: 'escuridão mágica', cor: 0x5a4a7a }),
  F(2, 'Lufada de Vento', 'Gust of Wind', { forma: 'linha', tam: 18, larg: 3, alcance: 0, efeito: 'empurra 4,5 m · TR For', cor: 0xcfefff }),
  F(2, 'Sopro do Dragão (exalar)', "Dragon's Breath", { forma: 'cone', tam: 4.5, alcance: 0, efeito: '3d6 do tipo escolhido · TR Des', cor: 0xffb347 }),
  F(2, 'Sopro do Dragão', "Dragon's Breath", { tempo: 'bonus', alvo: 0, efeito: 'toque: o alvo pode exalar um cone de 4,5 m' }),
  F(2, 'Raio Ardente', 'Scorching Ray', { alvo: 36, efeito: '3 raios de 2d6 fogo · ataque' }),
  F(2, 'Espinho Mental', 'Mind Spike', { alvo: 36, efeito: '3d8 psíquico · TR Sab' }),
  F(2, 'Imobilizar Pessoa', 'Hold Person', { alvo: 18, efeito: 'Paralisado · TR Sab' }),
  F(3, 'Bola de Fogo', 'Fireball', { forma: 'esfera', tam: 6, alcance: 45, efeito: '8d6 fogo · TR Des', cor: 0xff7a2e }),
  F(3, 'Relâmpago', 'Lightning Bolt', { forma: 'linha', tam: 30, larg: 1.5, alcance: 0, efeito: '8d6 elétrico · TR Des', cor: 0x7fd8ff }),
  F(3, 'Medo', 'Fear', { forma: 'cone', tam: 9, alcance: 0, efeito: 'Amedrontado · TR Sab', cor: 0x8a6ab0 }),
  F(3, 'Padrão Hipnótico', 'Hypnotic Pattern', { forma: 'cubo', tam: 9, alcance: 36, efeito: 'Encantado · TR Sab', cor: 0xff9ae6 }),
  F(3, 'Lentidão', 'Slow', { forma: 'cubo', tam: 12, alcance: 36, efeito: 'até 6 criaturas · TR Sab', cor: 0x9fe6c8 }),
  F(3, 'Nuvem Fétida', 'Stinking Cloud', { forma: 'esfera', tam: 6, alcance: 27, efeito: 'perde a ação · TR Con', cor: 0xd6e06a }),
  F(3, 'Tempestade de Granizo', 'Sleet Storm', { forma: 'cilindro', tam: 6, alcance: 45, efeito: 'Caído, perde concentração · TR Des', cor: 0xbfe3ff }),
  F(3, 'Toque Vampírico', 'Vampiric Touch', { alvo: 0, efeito: '3d6 necrótico, cura metade · ataque' }),
];
export const GRIMORIOS = { Kaira: GRIMORIO_FEITICEIRO };
