// Peças de interface do combate usadas pelo mestre e pelos jogadores:
// catálogo de ações do D&D 2024, retratos, coluna de iniciativa, avisos animados e anel de alcance.
import * as THREE from 'three';
import { makeCharacter, sizeOf } from './common.js';

export const M2U = 2 / 1.5; // 1 quadrado = 1,5 m = 2 unidades de mundo
export const fmtM = (m) => (Math.round(m * 10) / 10).toLocaleString('pt-BR', { maximumFractionDigits: 1 }) + ' m';

// ---------------------------------------------------------------- ações (regras de 2024)
// alvo: 'any' pede um alvo; 'opt' oferece alvo mas aceita "sem alvo"
export const ACTIONS = {
  action: [
    { id: 'attack', nome: 'Atacar', desc: 'Ataque com arma ou desarmado', alvo: 'any' },
    { id: 'magic', nome: 'Magia', desc: 'Conjurar magia ou usar item mágico', alvo: 'opt' },
    { id: 'dash', nome: 'Disparada', desc: 'Ganha deslocamento extra igual ao seu' },
    { id: 'disengage', nome: 'Desengajar', desc: 'Sem ataques de oportunidade neste turno' },
    { id: 'dodge', nome: 'Esquivar', desc: 'Ataques contra você com desvantagem' },
    { id: 'help', nome: 'Ajudar', desc: 'Dá vantagem a um aliado', alvo: 'any' },
    { id: 'hide', nome: 'Esconder', desc: 'Teste de Furtividade para sumir' },
    { id: 'influence', nome: 'Influenciar', desc: 'Convencer, enganar ou intimidar', alvo: 'opt' },
    { id: 'ready', nome: 'Preparar', desc: 'Reagir a um gatilho que você define' },
    { id: 'search', nome: 'Procurar', desc: 'Teste de Sabedoria para perceber algo' },
    { id: 'study', nome: 'Estudar', desc: 'Teste de Inteligência para lembrar ou analisar' },
    { id: 'utilize', nome: 'Utilizar', desc: 'Usar um objeto que exige ação' },
  ],
  bonus: [
    { id: 'offhand', nome: 'Ataque leve', desc: 'Segundo ataque com arma Leve', alvo: 'any' },
    { id: 'spell', nome: 'Magia', desc: 'Magia de ação bônus', alvo: 'opt' },
    { id: 'potion', nome: 'Poção', desc: 'Beber ou dar uma poção', alvo: 'opt' },
    { id: 'dash', nome: 'Disparada', desc: 'Por habilidade de classe' },
    { id: 'disengage', nome: 'Desengajar', desc: 'Por habilidade de classe' },
    { id: 'hide', nome: 'Esconder', desc: 'Por habilidade de classe' },
    { id: 'class', nome: 'Habilidade', desc: 'Fúria, Inspiração, Segundo Fôlego…', alvo: 'opt' },
    { id: 'revelacao', nome: 'Revelação Celestial', desc: 'Asas de luz: voo igual ao deslocamento por 1 minuto', so: ['Kaira'] },
    { id: 'other', nome: 'Outra', desc: 'Combine com o mestre', alvo: 'opt' },
  ],
  reaction: [
    { id: 'opportunity', nome: 'Oportunidade', desc: 'Atacar quem sai do seu alcance', alvo: 'any' },
    { id: 'spell', nome: 'Magia', desc: 'Escudo, Contramágica…', alvo: 'opt' },
    { id: 'readied', nome: 'Ação preparada', desc: 'O gatilho aconteceu', alvo: 'opt' },
    { id: 'other', nome: 'Outra', desc: 'Combine com o mestre', alvo: 'opt' },
  ],
};
export const SLOT_NOME = { action: 'Ação', bonus: 'Ação bônus', reaction: 'Reação', end: 'Fim do turno' };
export function logText(e) {
  if (e.slot === 'end') return `${e.who} encerrou o turno`;
  const a = (ACTIONS[e.slot] || []).find((x) => x.id === e.id);
  return `${e.who} ▸ ${a ? a.nome : e.id}${e.spell ? ': ' + e.spell : ''}${e.target ? ' ▸ ' + e.target : ''}`;
}

// ---------------------------------------------------------------- retratos
// Cada retrato é uma foto do rosto do próprio modelo 3D, feita uma vez e guardada.
let pr = null;
const portraits = new Map();
function portraitRig() {
  if (pr) return pr;
  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, preserveDrawingBuffer: true });
  renderer.setPixelRatio(1); renderer.setSize(160, 160, false); renderer.setClearColor(0x000000, 0);
  const scene = new THREE.Scene();
  scene.add(new THREE.HemisphereLight(0xffffff, 0x445066, 1.6));
  const key = new THREE.DirectionalLight(0xffffff, 2.2); key.position.set(1.5, 2, 3); scene.add(key);
  const cam = new THREE.PerspectiveCamera(28, 1, 0.05, 50);
  pr = { renderer, scene, cam, queue: Promise.resolve() };
  return pr;
}
export function portrait(model) {
  if (!model) return Promise.resolve('');
  if (portraits.has(model)) return portraits.get(model);
  const job = (async () => {
    const rig = portraitRig();
    await rig.queue; // um retrato por vez: o palco é um só
    const c = await makeCharacter(model);
    c.mixer.update(0.6);
    c.obj.updateMatrixWorld(true);
    c.obj.traverse((o) => { if (o.isSkinnedMesh) o.skeleton.update(); });
    const box = new THREE.Box3().setFromObject(c.obj, true);
    const h = box.max.y - box.min.y || 2;
    let head = new THREE.Vector3((box.min.x + box.max.x) / 2, box.max.y - h * 0.24, (box.min.z + box.max.z) / 2);
    if (sizeOf(model) > 1) {
      // criatura grande e comprida (dragão): a cabeça fica na frente e baixa, não no alto do modelo
      const d = box.max.z - box.min.z;
      head = new THREE.Vector3((box.min.x + box.max.x) / 2, box.min.y + h * 0.36, box.max.z - d * 0.1);
      rig.cam.position.set(head.x + h * 0.35, head.y + h * 0.1, head.z + h * 0.75);
    } else rig.cam.position.set(head.x + h * 0.18, head.y + h * 0.04, head.z + h * 1.15);
    rig.cam.lookAt(head);
    rig.scene.add(c.obj);
    rig.renderer.render(rig.scene, rig.cam);
    const url = rig.renderer.domElement.toDataURL('image/png');
    rig.scene.remove(c.obj);
    return url;
  })();
  pr && (pr.queue = job.catch(() => {}));
  portraits.set(model, job);
  return job;
}
// gera retratos com folga entre um e outro, para não travar a tela
const warmQueue = [];
export function warmPortraits(models) {
  for (const m of models) if (m && !portraits.has(m) && !warmQueue.includes(m)) warmQueue.push(m);
  if (warmQueue.length === 1 || (warmQueue.length && !warmQueue.running)) pump();
}
function pump() {
  if (!warmQueue.length) { warmQueue.running = false; return; }
  warmQueue.running = true;
  const m = warmQueue.shift();
  portrait(m).finally(() => setTimeout(pump, 120));
}
// retratos desenhados (arte do Caio): usados no lugar da foto do modelo 3D
const ART = {
  Kaira: '/assets/retratos/kaira.webp', Kaira_Asas: '/assets/retratos/kaira.webp', Kaira_script: '/assets/retratos/kaira.webp',
  Skeleton_Warrior: '/assets/retratos/esqueleto.webp', Skeleton_Minion: '/assets/retratos/esqueleto.webp',
  Skeleton_Rogue: '/assets/retratos/esqueleto.webp', Skeleton_Mage: '/assets/retratos/esqueleto.webp',
  Dragao_Negro: '/assets/retratos/dragao_veu.webp', Ghultok: '/assets/retratos/ghultok.webp', Guy: '/assets/retratos/guy.webp',
  Kobold: '/assets/retratos/kobold.webp',
};
export const hasArt = (model) => !!ART[model];
export function setPortrait(img, model) {
  img.classList.toggle('arte', !!ART[model]);
  if (ART[model]) { img.dataset.model = model; img.src = ART[model]; return; }
  img.dataset.model = model;
  portrait(model).then((url) => { if (img.dataset.model === model && url) img.src = url; }).catch(() => {});
}

// ---------------------------------------------------------------- coluna de iniciativa
// Mostra a ordem a partir de quem está agindo agora, como nos JRPGs.
// O mestre vê os valores de iniciativa; os jogadores veem só a ordem.
export class TurnOrder {
  constructor(root, { gm = false, max = 8, collapsible = false } = {}) {
    this.root = root; this.gm = gm; this.max = max; this.myRef = 0;
    root.classList.add('to-root', gm ? 'to-gm' : 'to-pl');
    root.innerHTML = '';
    if (collapsible) {
      this.toggle = document.createElement('button');
      this.toggle.className = 'to-toggle';
      this.toggle.innerHTML = '<span class="to-ico"><img alt=""></span><span class="to-cap">ORDEM</span>';
      this.toggle.onclick = () => { this.root.classList.toggle('to-closed'); try { localStorage.setItem('vtt.ordem', this.root.classList.contains('to-closed') ? '0' : '1'); } catch {} };
      root.appendChild(this.toggle);
      try { if (localStorage.getItem('vtt.ordem') === '0') root.classList.add('to-closed'); } catch {}
    }
    this.head = document.createElement('div'); this.head.className = 'to-head';
    this.list = document.createElement('div'); this.list.className = 'to-list';
    root.append(this.head, this.list);
    root.hidden = true;
  }
  render(c, myRef = 0) {
    this.myRef = myRef;
    if (!c || !c.active) { this.root.hidden = true; return; }
    this.root.hidden = false;
    this.head.textContent = `RODADA ${c.round}`;
    const list = c.list;
    let start = c.cur ? list.findIndex((x) => x.cid === c.cur.cid) : 0;
    const rows = [];
    if (start < 0) { rows.push({ unknown: true }); start = 0; } // vez de uma criatura oculta
    for (let k = 0; k < list.length && rows.length < this.max; k++) {
      const idx = (start + k) % list.length;
      if (k > 0 && idx === 0) rows.push({ divider: true });
      rows.push(list[idx]);
    }
    this.list.innerHTML = '';
    rows.forEach((it, i) => {
      if (it.divider) { const d = document.createElement('div'); d.className = 'to-div'; d.textContent = 'próxima rodada'; this.list.appendChild(d); return; }
      const el = document.createElement('div');
      const mine = it.kind === 'player' && it.ref === myRef;
      el.className = `to-slot ${it.unknown ? 'monster' : it.kind}${i === 0 ? ' cur' : ''}${mine ? ' me' : ''}${it.hidden ? ' oculto' : ''}`;
      const face = document.createElement('div'); face.className = 'to-face' + (!it.unknown && hasArt(it.model) ? ' arte' : '');
      if (it.unknown) face.innerHTML = '<b class="to-q">?</b>';
      else { const img = document.createElement('img'); img.alt = ''; face.appendChild(img); setPortrait(img, it.model); }
      el.appendChild(face);
      const name = document.createElement('span'); name.className = 'to-name';
      name.textContent = it.unknown ? '???' : mine ? 'VOCÊ' : it.name;
      el.appendChild(name);
      if (this.gm && !it.unknown) {
        const b = document.createElement('b'); b.className = 'to-init'; b.textContent = it.init ?? '–'; el.appendChild(b);
      }
      if (it.flags && it.flags.length) {
        const f = document.createElement('span'); f.className = 'to-flags'; f.textContent = it.flags.join(' · '); el.appendChild(f);
      }
      this.list.appendChild(el);
    });
    if (this.toggle) {
      const cur = rows[0];
      const img = this.toggle.querySelector('img');
      if (cur && !cur.unknown) setPortrait(img, cur.model); else img.removeAttribute('src');
      this.toggle.classList.toggle('minha', !!(cur && cur.kind === 'player' && cur.ref === myRef));
    }
  }
}

// ---------------------------------------------------------------- avisos animados
let layer = null;
function bannerLayer() {
  if (!layer) { layer = document.createElement('div'); layer.className = 'fx-layer'; document.body.appendChild(layer); }
  return layer;
}
// kind: 'turn' (seu turno), 'start' (combate!), 'end' (fim do combate)
export function banner(kind, title, sub = '') {
  const el = document.createElement('div');
  el.className = 'fx-banner fx-' + kind;
  el.innerHTML = '<div class="fx-band"></div><div class="fx-streaks"><i></i><i></i><i></i><i></i><i></i></div><div class="fx-text"><b></b><small></small></div><div class="fx-stars"><i></i><i></i><i></i><i></i><i></i><i></i></div>';
  el.querySelector('b').textContent = title;
  el.querySelector('small').textContent = sub;
  bannerLayer().appendChild(el);
  // sai quando a animação termina de verdade (num aparelho engasgado, um cronômetro venceria antes de ela aparecer)
  el.querySelector('.fx-band').addEventListener('animationend', () => el.remove());
  setTimeout(() => el.remove(), 8000);
}
// recado curto no topo: de quem é a vez, o que alguém fez
export function toast(text, kind = '') {
  let box = document.querySelector('.fx-toasts');
  if (!box) { box = document.createElement('div'); box.className = 'fx-toasts'; document.body.appendChild(box); }
  const el = document.createElement('div'); el.className = 'fx-toast ' + kind; el.textContent = text;
  box.appendChild(el);
  while (box.children.length > 3) box.firstChild.remove();
  setTimeout(() => { el.classList.add('out'); setTimeout(() => el.remove(), 400); }, 3200);
}

// ---------------------------------------------------------------- som
let actx = null;
export function unlockAudio() {
  try { if (!actx) actx = new (window.AudioContext || window.webkitAudioContext)(); if (actx.state === 'suspended') actx.resume(); } catch {}
}
export function chime(kind = 'turn') {
  if (!actx) return;
  const notes = kind === 'turn' ? [880, 1174.7, 1568] : kind === 'start' ? [392, 523.3, 784] : kind === 'end' ? [784, 587.3, 392] : [1046.5];
  const t0 = actx.currentTime;
  notes.forEach((f, i) => {
    const o = actx.createOscillator(), g = actx.createGain();
    o.type = i === notes.length - 1 ? 'triangle' : 'square';
    o.frequency.value = f;
    const t = t0 + i * 0.09;
    g.gain.setValueAtTime(0.0001, t); g.gain.exponentialRampToValueAtTime(0.12, t + 0.015); g.gain.exponentialRampToValueAtTime(0.0001, t + 0.35);
    o.connect(g).connect(actx.destination); o.start(t); o.stop(t + 0.4);
  });
}

// ---------------------------------------------------------------- anel de alcance
// Um disco no chão desenhado por shader: borda com espessura fixa e marcas girando.
export function makeRangeRing(color = 0x5ff3ff) {
  const mat = new THREE.ShaderMaterial({
    transparent: true, depthWrite: false,
    uniforms: { uR: { value: 1 }, uT: { value: 0 }, uC: { value: new THREE.Color(color) }, uA: { value: 1 } },
    vertexShader: 'varying vec2 vP; void main(){ vP = position.xy; gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.0); }',
    fragmentShader: `uniform float uR; uniform float uT; uniform vec3 uC; uniform float uA; varying vec2 vP;
      void main(){
        float d = length(vP) * uR;           // distância em unidades de mundo
        float band = smoothstep(uR - 0.16, uR - 0.06, d) * (1.0 - smoothstep(uR - 0.02, uR + 0.02, d));
        float glow = smoothstep(uR - 0.9, uR, d) * (1.0 - step(uR, d)) * 0.28;
        float ang = atan(vP.y, vP.x);
        float ticks = step(0.5, fract(ang * 6.0 / 3.14159 * 4.0 + uT * 0.35)) * smoothstep(uR - 0.55, uR - 0.35, d) * (1.0 - smoothstep(uR - 0.2, uR - 0.12, d));
        float fill = (1.0 - step(uR, d)) * 0.07;
        float pulse = 0.82 + 0.18 * sin(uT * 3.0);
        float a = (band * pulse + glow + ticks * 0.55 + fill) * uA;
        if (a < 0.01) discard;
        gl_FragColor = vec4(uC * (1.0 + band * 0.6), a);
      }`,
  });
  const mesh = new THREE.Mesh(new THREE.PlaneGeometry(2, 2), mat);
  mesh.rotation.x = -Math.PI / 2; mesh.position.y = 0.14; mesh.renderOrder = 3; mesh.visible = false;
  mesh.userData.r = 0;
  // raio em unidades de mundo; anima suavemente até o alvo
  mesh.userData.set = (x, z, r, dt, t) => {
    const cur = mesh.userData.r;
    mesh.userData.r = cur + (r - cur) * Math.min(1, dt * 8);
    const R = Math.max(0.05, mesh.userData.r);
    mesh.position.x = x; mesh.position.z = z;
    mesh.scale.set(R, R, 1);
    mat.uniforms.uR.value = R; mat.uniforms.uT.value = t;
  };
  return mesh;
}
