// Régua: mede a distância entre dois pontos do mapa, de quadrado a quadrado.
// Regra do Livro do Jogador 2024: cada quadrado vale 1,5 m e a diagonal também conta 1 quadrado.
// Usada pelo jogador (visão tática, com a mesma transição da área de magia) e pelo mestre (mapa de cima).
import * as THREE from 'three';
import { G } from './common.js';

const M2U = 4 / 3;   // unidades de mundo por metro
const ease = (t) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);
export const cellCenter = (v) => (Math.floor(v / G) + 0.5) * G;
const fmt = (m) => (Math.round(m * 10) / 10).toString().replace('.', ',') + ' m';

// a e b: pontos no chão (x, z). Encaixa no centro dos quadrados.
export function medir(ax, az, bx, bz) {
  const ci = Math.floor(ax / G), cj = Math.floor(az / G), di = Math.floor(bx / G), dj = Math.floor(bz / G);
  const quad = Math.max(Math.abs(di - ci), Math.abs(dj - cj));
  const reta = Math.hypot((di - ci) * G, (dj - cj) * G) / M2U;
  return { quad, m: quad * 1.5, reta, txt: fmt(quad * 1.5), retaTxt: fmt(reta) };
}

// desenho: faixa tracejada entre os centros, os dois quadrados das pontas e um disco em cada ponta
export class RulerDraw {
  constructor(scene) {
    this.scene = scene;
    this.group = new THREE.Group(); this.group.visible = false; this.group.renderOrder = 30; scene.add(this.group);
    const mat = (color, opacity) => new THREE.MeshBasicMaterial({ color, transparent: true, opacity, depthTest: false, depthWrite: false, side: THREE.DoubleSide, fog: false });
    this.matDash = mat(0xffe27a, 1); this.matUnder = mat(0x000000, 0.55); this.matCell = mat(0xffe27a, 0.22); this.matEdge = mat(0xffe27a, 0.95);
    this.dash = new THREE.Mesh(new THREE.BufferGeometry(), this.matDash); this.dash.renderOrder = 33;
    this.under = new THREE.Mesh(new THREE.BufferGeometry(), this.matUnder); this.under.renderOrder = 32;
    this.cells = new THREE.Mesh(new THREE.BufferGeometry(), this.matCell); this.cells.renderOrder = 31;
    this.edges = new THREE.Mesh(new THREE.BufferGeometry(), this.matEdge); this.edges.renderOrder = 32;
    const disc = new THREE.CircleGeometry(1, 24); disc.rotateX(-Math.PI / 2);
    this.endA = new THREE.Mesh(disc, this.matDash); this.endB = new THREE.Mesh(disc, this.matDash);
    this.endA.renderOrder = this.endB.renderOrder = 34;
    this.group.add(this.cells, this.edges, this.under, this.dash, this.endA, this.endB);
  }
  // largura da linha em unidades de mundo (quem chama ajusta ao zoom da câmera)
  set(ax, az, bx, bz, y, w = 0.18) {
    const x1 = cellCenter(ax), z1 = cellCenter(az), x2 = cellCenter(bx), z2 = cellCenter(bz);
    const L = Math.hypot(x2 - x1, z2 - z1), ux = L ? (x2 - x1) / L : 1, uz = L ? (z2 - z1) / L : 0;
    const quad = (pts, a, b, half) => {   // retângulo ao longo da linha, de a até b
      const nx = -uz * half, nz = ux * half;
      const p = (t, s) => [x1 + ux * t + nx * s, y, z1 + uz * t + nz * s];
      pts.push(...p(a, -1), ...p(b, -1), ...p(b, 1), ...p(a, -1), ...p(b, 1), ...p(a, 1));
    };
    const dash = [], under = [];
    const on = w * 4, off = w * 2.6;
    for (let t = 0; t < L; t += on + off) quad(dash, t, Math.min(L, t + on), w / 2);
    quad(under, 0, L, w * 0.95);
    this.dash.geometry.dispose(); this.dash.geometry = geo(dash);
    this.under.geometry.dispose(); this.under.geometry = geo(under);
    // quadrados das pontas: preenchidos com borda
    const cells = [], edges = [], h = G / 2, e = Math.max(0.05, w * 0.35);
    for (const [cx, cz] of [[x1, z1], [x2, z2]]) {
      cells.push(...sq(cx, cz, h, y));
      for (const [a, b, c, d] of [[-h, -h, h, -h + e], [-h, h - e, h, h], [-h, -h, -h + e, h], [h - e, -h, h, h]]) edges.push(...rect(cx + a, cz + b, cx + c, cz + d, y));
    }
    this.cells.geometry.dispose(); this.cells.geometry = geo(cells);
    this.edges.geometry.dispose(); this.edges.geometry = geo(edges);
    this.endA.position.set(x1, y, z1); this.endB.position.set(x2, y, z2);
    this.endA.scale.setScalar(w * 1.6); this.endB.scale.setScalar(w * 1.6);
    this.group.visible = true;
    this.mid = new THREE.Vector3((x1 + x2) / 2, y, (z1 + z2) / 2); this.b = new THREE.Vector3(x2, y, z2);
  }
  hide() { this.group.visible = false; }
  dispose() {
    this.group.removeFromParent();
    for (const m of [this.dash, this.under, this.cells, this.edges]) m.geometry.dispose();
    this.endA.geometry.dispose();
    for (const m of [this.matDash, this.matUnder, this.matCell, this.matEdge]) m.dispose();
  }
}
function geo(arr) { const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.Float32BufferAttribute(arr, 3)); return g; }
function rect(x1, z1, x2, z2, y) { return [x1, y, z1, x2, y, z1, x2, y, z2, x1, y, z1, x2, y, z2, x1, y, z2]; }
function sq(cx, cz, h, y) { return rect(cx - h, cz - h, cx + h, cz + h, y); }

// rótulo com a distância, que acompanha a ponta da linha na tela
export function makeLabel() {
  const el = document.createElement('div'); el.className = 'regua-rotulo'; el.hidden = true;
  el.innerHTML = '<b></b><small></small>'; document.body.appendChild(el);
  return {
    el,
    show(med, screen) {
      el.hidden = false;
      el.querySelector('b').textContent = med.txt;
      el.querySelector('small').textContent = med.quad ? `${med.quad} ${med.quad === 1 ? 'quadrado' : 'quadrados'}` + (Math.abs(med.reta - med.m) > 0.2 ? ` · em linha reta ${med.retaTxt}` : '') : 'mesmo quadrado';
      // perto da borda direita o rótulo vai para o outro lado da ponta
      const w = el.offsetWidth || 200, left = screen.x + 14 + w > innerWidth - 8;
      el.style.transform = left ? 'translate(calc(-100% - 14px), -50%)' : 'translate(14px, -50%)';
      el.style.left = Math.round(screen.x) + 'px'; el.style.top = Math.round(Math.max(40, Math.min(innerHeight - 40, screen.y))) + 'px';
    },
    hide() { el.hidden = true; },
  };
}
export function toScreen(v, camera, canvas) {
  const p = v.clone().project(camera), r = canvas.getBoundingClientRect();
  return { x: r.left + (p.x + 1) / 2 * r.width, y: r.top + (1 - p.y) / 2 * r.height };
}

// ---------------------------------------------------------------- jogador: visão tática com a régua
// ctx: { scene, camera, canvas, caster: () => ({x, z, y, camYaw}), onExit() }
export class ReguaTool {
  constructor(ctx) {
    this.ctx = ctx; this.phase = 'off'; this.t = 0; this.zoom = 1; this.pan = { x: 0, z: 0 };
    this.from = { p: new THREE.Vector3(), q: new THREE.Quaternion() };
    this.top = { p: new THREE.Vector3(), q: new THREE.Quaternion() };
    this.ray = new THREE.Raycaster(); this.plane = new THREE.Plane(new THREE.Vector3(0, 1, 0), 0);
    this.draw = new RulerDraw(ctx.scene); this.label = makeLabel();
    this.ptrs = new Map(); this.a = null; this.b = null;
    const c = ctx.canvas;
    c.addEventListener('pointerdown', (e) => this.down(e), true);
    c.addEventListener('pointermove', (e) => this.moveP(e), true);
    c.addEventListener('pointerup', (e) => this.up(e), true);
    c.addEventListener('pointercancel', (e) => this.up(e), true);
    c.addEventListener('contextmenu', (e) => { if (this.busy) e.preventDefault(); });
    c.addEventListener('wheel', (e) => { if (this.phase === 'tatico') { e.preventDefault(); this.zoomBy(e.deltaY > 0 ? 1.12 : 1 / 1.12); } }, { passive: false });
  }
  get busy() { return this.phase !== 'off'; }
  start() {
    const k = this.ctx.caster();
    this.k = k; this.phase = 'entrando'; this.t = 0; this.zoom = 1; this.pan = { x: 0, z: 0 }; this.a = this.b = null;
    this.camYaw = k.camYaw;
    this.from.p.copy(this.ctx.camera.position); this.from.q.copy(this.ctx.camera.quaternion);
    this.draw.hide(); this.label.hide();
    document.body.classList.add('modo-tatico', 'modo-regua');
  }
  finish() {
    if (this.phase !== 'tatico' && this.phase !== 'entrando') return;
    this.phase = 'saindo'; this.t = 0; this.label.hide();
    document.body.classList.remove('modo-tatico', 'modo-regua');
    this.ctx.onExit && this.ctx.onExit();
  }
  topPose() {
    const k = this.k, cam = this.ctx.camera;
    const reach = 15;   // uns 7 quadrados para cada lado; ＋/－ e a pinça mudam
    const aspect = Math.min(cam.aspect, 1.0);
    this.h = Math.max(8, (reach / Math.tan(THREE.MathUtils.degToRad(cam.fov / 2)) / Math.max(0.55, aspect)) * this.zoom);
    this.top.p.set(k.x + this.pan.x, k.y + this.h, k.z + this.pan.z);
    this.top.q.setFromEuler(new THREE.Euler(-Math.PI / 2, this.camYaw, 0, 'YXZ'));
  }
  zoomBy(f) { this.zoom = Math.max(0.3, Math.min(6, this.zoom * f)); this.redraw(); }
  apply(dt) {
    if (this.phase === 'off') return false;
    const cam = this.ctx.camera;
    this.topPose();
    if (this.phase === 'entrando' || this.phase === 'saindo') {
      this.t += dt / 0.9;
      const k = ease(Math.min(1, this.t)), w = this.phase === 'entrando' ? k : 1 - k;
      const nP = this.phase === 'entrando' ? this.from.p : cam.position.clone();
      const nQ = this.phase === 'entrando' ? this.from.q : cam.quaternion.clone();
      const p = nP.clone().lerp(this.top.p, w); p.y += Math.sin(w * Math.PI) * 3;
      cam.position.copy(p); cam.quaternion.copy(nQ).slerp(this.top.q, w);
      if (this.t >= 1) { if (this.phase === 'entrando') this.phase = 'tatico'; else { this.phase = 'off'; this.draw.hide(); } }
      this.draw.matDash.opacity = w; this.draw.matCell.opacity = 0.22 * w; this.draw.matEdge.opacity = 0.95 * w; this.draw.matUnder.opacity = 0.55 * w;
    } else { cam.position.copy(this.top.p); cam.quaternion.copy(this.top.q); }
    if (this.phase === 'tatico' && this.a && this.b) this.label.show(medir(this.a.x, this.a.z, this.b.x, this.b.z), toScreen(this.draw.b, cam, this.ctx.canvas));
    return true;
  }
  redraw() {
    if (!this.a || !this.b) return;
    this.draw.set(this.a.x, this.a.z, this.b.x, this.b.z, this.k.y + 0.06, Math.max(0.12, (this.h || 30) * 0.006));
  }
  pick(e) {
    const r = this.ctx.canvas.getBoundingClientRect();
    const v = new THREE.Vector2(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1);
    this.ray.setFromCamera(v, this.ctx.camera); this.plane.constant = -this.k.y;
    const p = new THREE.Vector3(); return this.ray.ray.intersectPlane(this.plane, p) ? p : null;
  }
  // um dedo: mede (toca no ponto de partida e arrasta); dois dedos: arrastam o mapa e aproximam/afastam.
  // No PC: botão esquerdo mede, direito ou do meio arrasta o mapa, a roda dá zoom.
  down(e) {
    if (!this.busy) return;
    e.stopImmediatePropagation(); e.preventDefault();
    if (this.phase !== 'tatico') return;
    try { this.ctx.canvas.setPointerCapture(e.pointerId); } catch {}
    this.ptrs.set(e.pointerId, { x: e.clientX, y: e.clientY, pan: e.pointerType === 'mouse' && e.button !== 0 });
    if (this.ptrs.size === 1 && !this.ptrs.get(e.pointerId).pan) {
      const p = this.pick(e); if (!p) return;
      this.a = { x: p.x, z: p.z }; this.b = { x: p.x, z: p.z }; this.measuring = true; this.redraw();
    } else { this.measuring = false; this.pinch0 = { d: this.pinchDist(), z: this.zoom, c: this.center() }; }
  }
  moveP(e) {
    if (!this.busy) return;
    e.stopImmediatePropagation();
    const pt = this.ptrs.get(e.pointerId); if (!pt) return;
    const px = pt.x, py = pt.y; pt.x = e.clientX; pt.y = e.clientY;
    if (pt.pan && this.ptrs.size === 1) { this.panBy(e.clientX - px, e.clientY - py); return; }
    if (this.ptrs.size >= 2 && this.pinch0) {
      const d = this.pinchDist(); if (d > 10) this.zoom = Math.max(0.3, Math.min(6, this.pinch0.z * (this.pinch0.d / d)));
      const c = this.center(); this.panBy(c.x - this.pinch0.c.x, c.y - this.pinch0.c.y); this.pinch0.c = c;
      this.redraw();
    } else if (this.measuring) { const p = this.pick(e); if (p) { this.b = { x: p.x, z: p.z }; this.redraw(); } }
  }
  up(e) {
    if (!this.busy) return;
    e.stopImmediatePropagation(); this.ptrs.delete(e.pointerId);
    if (this.ptrs.size < 2) this.pinch0 = null;
    if (!this.ptrs.size) this.measuring = false;
  }
  panBy(dx, dy) {   // arrasta o mapa junto com o dedo (a tela gira com a câmera)
    const r = this.ctx.canvas.getBoundingClientRect();
    const worldPerPx = (2 * this.h * Math.tan(THREE.MathUtils.degToRad(this.ctx.camera.fov / 2))) / r.height;
    const c = Math.cos(this.camYaw), s = Math.sin(this.camYaw);
    // direita da tela = (cos, -sin) no chão; para cima na tela = (-sin, -cos)
    this.pan.x -= (dx * c + dy * s) * worldPerPx;
    this.pan.z -= (-dx * s + dy * c) * worldPerPx;
  }
  pinchDist() { const [a, b] = [...this.ptrs.values()]; return a && b ? Math.hypot(a.x - b.x, a.y - b.y) : 1; }
  center() { const v = [...this.ptrs.values()]; return { x: v.reduce((s, p) => s + p.x, 0) / v.length, y: v.reduce((s, p) => s + p.y, 0) / v.length }; }
}
