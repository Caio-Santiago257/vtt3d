// Revelação Celestial da Kaira: troca do modelo de chão pelo modelo com asas quando ela levanta voo.
//
// Subir (asas surgindo), ~2,4 s:
//   0,00 s  coluna de luz dourada sobe do chão, anel se abre no chão, faíscas em espiral; ela salta girando
//   0,45 s  clarão branco: troca de modelo; o modelo com asas começa o clipe "revelar"
//           (encolhida, as asas brotam minúsculas, crescem, se desdobram, a auréola acende, batida forte)
//   0,45 s  penas de luz caem devagar em volta
//   2,4  s  pairando (fly_idle / fly); a auréola fica com um brilho suave
// Descer (asas recolhendo), ~1,3 s: clipe "recolher" (asas fecham e encolhem), faíscas e um clarão pequeno,
//   e volta o modelo de chão.
import * as THREE from 'three';
import { makeCharacter } from './common.js';
import { glowTexture } from './gfx.js';

const GOLD = new THREE.Color(0xffe2a0), WHITE = new THREE.Color(0xfff8ec);
let columnTex = null;
function columnTexture() {
  if (columnTex) return columnTex;
  const c = document.createElement('canvas'); c.width = 64; c.height = 256;
  const g = c.getContext('2d');
  const grad = g.createLinearGradient(0, 256, 0, 0);
  grad.addColorStop(0, 'rgba(255,240,200,1)'); grad.addColorStop(0.35, 'rgba(255,220,150,0.55)'); grad.addColorStop(1, 'rgba(255,220,150,0)');
  g.fillStyle = grad; g.fillRect(0, 0, 64, 256);
  // faixas verticais suaves (raios)
  for (let i = 0; i < 9; i++) { g.fillStyle = `rgba(255,255,255,${0.08 + Math.random() * 0.12})`; g.fillRect(Math.random() * 60, 0, 2 + Math.random() * 4, 256); }
  columnTex = new THREE.CanvasTexture(c); columnTex.wrapS = THREE.RepeatWrapping; columnTex.colorSpace = THREE.SRGBColorSpace;
  return columnTex;
}
let featherTex = null;
function featherTexture() {
  if (featherTex) return featherTex;
  const c = document.createElement('canvas'); c.width = 32; c.height = 64;
  const g = c.getContext('2d');
  const grad = g.createRadialGradient(16, 32, 2, 16, 32, 30);
  grad.addColorStop(0, 'rgba(255,255,255,1)'); grad.addColorStop(1, 'rgba(255,240,210,0)');
  g.fillStyle = grad; g.beginPath(); g.ellipse(16, 32, 9, 28, 0, 0, Math.PI * 2); g.fill();
  g.strokeStyle = 'rgba(255,230,180,0.9)'; g.lineWidth = 1.5; g.beginPath(); g.moveTo(16, 4); g.lineTo(16, 62); g.stroke();
  featherTex = new THREE.CanvasTexture(c); featherTex.colorSpace = THREE.SRGBColorSpace;
  return featherTex;
}
const add = (o) => { o.renderOrder = 5; return o; };
const easeOut = (x) => 1 - (1 - x) * (1 - x);

export class CelestialForm {
  // holder: o grupo que o jogo move e gira; base: personagem de chão (makeCharacter) já dentro do holder
  constructor(holder, base, scene) {
    this.holder = holder; this.base = base; this.scene = scene;
    this.pivot = new THREE.Group(); holder.add(this.pivot);
    holder.remove(base.obj); this.pivot.add(base.obj);
    this.wings = null; this.loading = null;
    this.timeScale = 1;
    this.state = 'chao';   // chao | subindo | asas | descendo
    this.t = 0; this.char = base; this.spin = 0;
    // efeitos (criados uma vez, ficam escondidos)
    const fx = this.fx = new THREE.Group(); scene.add(fx); fx.visible = false;
    const additive = { transparent: true, depthWrite: false, blending: THREE.AdditiveBlending };
    this.column = add(new THREE.Mesh(new THREE.CylinderGeometry(0.75, 1.0, 9, 24, 1, true), new THREE.MeshBasicMaterial({ map: columnTexture(), color: GOLD, side: THREE.DoubleSide, ...additive })));
    this.column.position.y = 4.5;
    this.ring = add(new THREE.Mesh(new THREE.RingGeometry(0.7, 1.0, 48), new THREE.MeshBasicMaterial({ color: GOLD, side: THREE.DoubleSide, ...additive })));
    this.ring.rotation.x = -Math.PI / 2; this.ring.position.y = 0.06;
    this.flash = add(new THREE.Sprite(new THREE.SpriteMaterial({ map: glowTexture(), color: WHITE, ...additive })));
    this.flash.position.y = 1.4;
    const N = 70;
    this.sparkGeo = new THREE.BufferGeometry(); this.sparkGeo.setAttribute('position', new THREE.BufferAttribute(new Float32Array(N * 3), 3));
    this.sparks = add(new THREE.Points(this.sparkGeo, new THREE.PointsMaterial({ map: glowTexture(), color: GOLD, size: 0.22, sizeAttenuation: true, ...additive })));
    this.sparkSeed = Array.from({ length: N }, () => [Math.random() * Math.PI * 2, Math.random(), 0.5 + Math.random() * 1.1]);
    const F = 16;
    this.feathers = Array.from({ length: F }, () => {
      const s = add(new THREE.Sprite(new THREE.SpriteMaterial({ map: featherTexture(), color: WHITE, transparent: true, depthWrite: false, opacity: 0 })));
      s.scale.set(0.18, 0.36, 1); fx.add(s); return { s, a: Math.random() * Math.PI * 2, r: 0.5 + Math.random() * 1.6, h: 1.5 + Math.random() * 2.5, ph: Math.random() * 6 };
    });
    fx.add(this.column, this.ring, this.flash, this.sparks);
    // brilho permanente da auréola (só com asas)
    this.haloGlow = add(new THREE.Sprite(new THREE.SpriteMaterial({ map: glowTexture(), color: GOLD, ...additive, opacity: 0 })));
    this.haloGlow.scale.setScalar(1.1); scene.add(this.haloGlow);
    this.light = new THREE.PointLight(0xffe6b0, 0, 9, 1.6); scene.add(this.light);   // fica na cena com intensidade 0 (sem recompilar materiais)
    this._v = new THREE.Vector3();
  }

  async ensureWings() {
    if (this.wings || this.loading) return this.loading;
    this.loading = makeCharacter('Kaira_Asas').then((c) => {
      this.wings = c; c.obj.visible = false; this.pivot.add(c.obj);
      this.haloBone = null; c.obj.traverse((o) => { if (o.isBone && o.name === 'Halo') this.haloBone = o; });
      return c;
    });
    return this.loading;
  }
  preload() { this.ensureWings(); }

  // wanted: deve estar com asas (Revelação ativa e no ar)
  update(dt, wanted) {
    if (wanted && (this.state === 'chao' || this.state === 'descendo')) {
      if (!this.wings) { this.ensureWings(); return this.char; }
      this.state = 'subindo'; this.t = 0; this.swapped = false;
    } else if (!wanted && (this.state === 'asas' || this.state === 'subindo') && this.wings) {
      this.state = 'descendo'; this.t = 0; this.swapped = false;
      this.wings.once('recolher', true);
    }
    dt *= this.timeScale;   // timeScale: só para inspecionar a transição em câmera lenta
    this.t += dt;
    const fx = this.fx, h = this.holder;
    h.getWorldPosition(this._v);
    fx.position.set(this._v.x, this._v.y, this._v.z);
    if (this.state === 'subindo') {
      const t = this.t;
      fx.visible = true;
      // salto girando (no pivô, para não brigar com a direção e a altura que o jogo controla)
      const jump = t < 0.45 ? easeOut(t / 0.45) : Math.max(0, 1 - (t - 0.45) / 1.9);
      this.pivot.position.y = 1.0 * jump;
      this.pivot.rotation.y = t < 1.0 ? easeOut(Math.min(1, t / 1.0)) * Math.PI * 4 : 0;
      // coluna, anel, clarão, faíscas, penas, luz
      const col = t < 0.3 ? t / 0.3 : Math.max(0, 1 - (t - 0.3) / 0.8);   // some antes das asas abrirem, para elas aparecerem
      this.column.material.opacity = 0.6 * col; this.column.scale.set(0.6 + 0.6 * col, 0.3 + 0.7 * Math.min(1, t / 0.35), 0.6 + 0.6 * col);
      this.column.material.map.offset.x = t * 0.4;
      const rt = Math.min(1, t / 0.9); this.ring.scale.setScalar(0.3 + 3.2 * easeOut(rt)); this.ring.material.opacity = 1 - rt;
      const ft = (t - 0.38) / 0.5; this.flash.material.opacity = ft < 0 ? 0 : 0.9 * Math.max(0, 1 - ft * 1.4); this.flash.scale.setScalar(ft < 0 ? 0 : 1 + 7 * easeOut(Math.min(1, ft * 2)));
      this.flash.position.y = 1.4 + this.pivot.position.y;
      this.light.intensity = 9 * Math.max(0, Math.min(1, t / 0.45) * (1 - Math.max(0, (t - 0.5) / 0.6))) + 2.5 * Math.max(0, 1 - Math.abs(t - 1.5) / 0.5);   // pico no clarão e outro na batida forte
      this.sparksAt(t, 1, Math.max(0, 1 - Math.max(0, t - 1.6) / 0.8));
      this.feathersAt(t - 0.45);
      if (!this.swapped && t >= 0.45) {   // troca de modelo no clarão
        this.swapped = true;
        this.base.obj.visible = false; this.wings.obj.visible = true; this.char = this.wings;
        this.wings.once('revelar');
      }
      if (t > 2.4) { this.state = 'asas'; fx.visible = false; this.pivot.position.y = 0; this.pivot.rotation.y = 0; this.light.intensity = 0; }
    } else if (this.state === 'descendo') {
      const t = this.t;
      fx.visible = true;
      this.column.material.opacity = 0; this.ring.material.opacity = 0;
      this.sparksAt(t + 1.4, -1, Math.max(0, 1 - t / 1.4));
      const ft = (t - 1.0) / 0.35; this.flash.material.opacity = ft < 0 ? 0 : Math.max(0, 0.7 - ft); this.flash.scale.setScalar(ft < 0 ? 0 : 1 + 2.5 * Math.min(1, ft * 2));
      this.light.intensity = 3 * Math.max(0, 1 - t / 1.3);
      this.feathersAt(-1);
      if (!this.swapped && t >= 1.2) {
        this.swapped = true;
        this.wings.obj.visible = false; this.base.obj.visible = true; this.char = this.base;
      }
      if (t > 1.5) { this.state = 'chao'; fx.visible = false; this.light.intensity = 0; }
    }
    // auréola: brilho suave sobre o osso Halo do modelo com asas
    const haloOn = this.wings && this.char === this.wings && this.haloBone;
    const target = haloOn ? (this.state === 'subindo' ? Math.max(0, (this.t - 1.3) / 0.6) : 1) : 0;
    this.haloGlow.material.opacity += (Math.min(0.75, target * 0.75) - this.haloGlow.material.opacity) * Math.min(1, dt * 6);
    if (haloOn) { this.haloBone.getWorldPosition(this._v); this.haloGlow.position.copy(this._v); this.haloGlow.position.y += 0.12; }
    this.haloGlow.visible = this.haloGlow.material.opacity > 0.01;
    if (this.light.intensity > 0) { this.holder.getWorldPosition(this._v); this.light.position.set(this._v.x, this._v.y + 1.6, this._v.z); }
    return this.char;
  }

  sparksAt(t, dir, k) {
    const p = this.sparkGeo.attributes.position;
    this.sparkSeed.forEach(([a0, off, sp], i) => {
      const u = (t * sp * 0.6 + off) % 1;
      const a = a0 + t * 3.2 * dir + u * 5;
      const r = 1.1 * (1 - u * 0.6);
      p.setXYZ(i, Math.cos(a) * r, (dir > 0 ? u : 1 - u) * 4.2 + this.pivot.position.y, Math.sin(a) * r);
    });
    p.needsUpdate = true;
    this.sparks.material.opacity = k;
  }
  feathersAt(t) {
    for (const f of this.feathers) {
      if (t < 0) { f.s.material.opacity = 0; continue; }
      const y = f.h + 1.0 - t * 0.55, sway = Math.sin(t * 2.2 + f.ph) * 0.35;
      f.s.position.set(Math.cos(f.a) * f.r + sway, Math.max(0.05, y), Math.sin(f.a) * f.r);
      f.s.material.rotation = Math.sin(t * 2 + f.ph) * 0.7;
      f.s.material.opacity = Math.max(0, Math.min(1, t * 3) * (1 - Math.max(0, (t - 1.6) / 1.0)));
    }
  }

  dispose() {
    this.fx.removeFromParent(); this.haloGlow.removeFromParent(); this.light.removeFromParent();
    this.sparkGeo.dispose();
  }
}

// a forma com asas só vale para quem tem a Revelação Celestial
export const hasRevelation = (hero) => hero === 'Kaira';
