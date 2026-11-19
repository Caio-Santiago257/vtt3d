// Galeria de assets: mostra cada modelo como ele aparece no jogo (mesmo material, contorno e luz),
// com turnaround em 5 vistas, régua em metros, malha aramada e troca de animação.
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { makeCharacter, makeProp, M, loadGLB } from './common.js';
import { wind } from './gfx.js';

const $ = (id) => document.getElementById(id);
const SIDE = 240;
const canvas = $('c');
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, preserveDrawingBuffer: true });
renderer.setPixelRatio(Math.min(devicePixelRatio || 1, 2));
const scene = new THREE.Scene();
const cam = new THREE.PerspectiveCamera(30, 1, 0.05, 200);
const controls = new OrbitControls(cam, canvas);
controls.enableDamping = true;

// ---- luz: as mesmas combinações do jogo
const hemi = new THREE.HemisphereLight(0xe6f1ff, 0x5a7a3a, 1.5);
const sun = new THREE.DirectionalLight(0xfff0cc, 2.0); sun.position.set(-3, 6, 4);
const torch = new THREE.PointLight(0xffc48a, 0, 14, 1.5); torch.position.set(1.5, 3, 2.5);
scene.add(hemi, sun, torch);
const LUZ = {
  dia: () => { scene.background = new THREE.Color(0xbfdcef); hemi.color.setHex(0xe6f1ff); hemi.groundColor.setHex(0x5a7a3a); hemi.intensity = 1.5; sun.intensity = 2.0; torch.intensity = 0; },
  masmorra: () => { scene.background = new THREE.Color(0x07070d); hemi.color.setHex(0x9aa4d0); hemi.groundColor.setHex(0x1e1c2a); hemi.intensity = 0.9; sun.intensity = 0; torch.intensity = 14; },
  estudio: () => { scene.background = new THREE.Color(0x2a2730); hemi.color.setHex(0xffffff); hemi.groundColor.setHex(0x404048); hemi.intensity = 1.3; sun.intensity = 1.6; torch.intensity = 0; },
};

// ---- chão com grade de quadrados de 1,5 m e régua de altura
const grid = new THREE.GridHelper(2 * 8, 8, 0x8a8478, 0x6a655c); grid.material.transparent = true; grid.material.opacity = 0.45; scene.add(grid);
const floor = new THREE.Mesh(new THREE.CircleGeometry(60, 64), new THREE.MeshLambertMaterial({ color: 0x8c8678 }));
floor.rotation.x = -Math.PI / 2; floor.position.y = -0.005; scene.add(floor);
const ruler = new THREE.Group(); scene.add(ruler);
function makeRuler(hUnits, hMeters) {
  ruler.clear();
  const mat = new THREE.LineBasicMaterial({ color: 0xffd36b });
  const x = -1.6;
  const pts = [new THREE.Vector3(x, 0, 0), new THREE.Vector3(x, hUnits, 0)];
  ruler.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(pts), mat));
  for (let m = 0; m <= hMeters + 0.001; m += 0.5) {
    const y = m * M, w = Number.isInteger(m) ? 0.18 : 0.09;
    ruler.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(x - w, y, 0), new THREE.Vector3(x, y, 0)]), mat));
  }
  ruler.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(x, hUnits, 0), new THREE.Vector3(x + 0.6, hUnits, 0)]), mat));
}

// ---- catálogo
let manifest = [], current = null, item = null, turn = false, paused = false, wire = false;
const holder = new THREE.Group(); scene.add(holder);

async function load(it) {
  item = it;
  document.querySelectorAll('#g-lista button').forEach((b) => b.classList.toggle('sel', b.dataset.id === it.id));
  holder.clear(); current = null;
  $('g-titulo').innerHTML = ''; $('g-titulo').append(it.nome); const sm = document.createElement('small'); sm.textContent = it.nota || it.url; $('g-titulo').append(sm);
  if (it.tipo === 'char') { current = await makeCharacter(it.id); holder.add(current.obj); }
  else if (it.tipo === 'glb') {
    // modelo bruto, como chegou: só apoia no chão para medir
    const g = (await loadGLB(it.url)).scene.clone(true);
    g.updateMatrixWorld(true); const b = new THREE.Box3().setFromObject(g); g.position.y -= b.min.y;
    holder.add(g);
  }
  else { holder.add(await makeProp(it.id)); }
  // animações
  const sel = $('g-anim'); sel.innerHTML = '';
  (current ? current.clips : []).forEach((n) => { const o = document.createElement('option'); o.value = o.textContent = n; sel.appendChild(o); });
  sel.hidden = !current;
  if (current && current.clips.length) { const first = current.clips.find((n) => /^(idle|Idle)$/.test(n)) || current.clips[0]; sel.value = first; current.play(first); }
  setWire(wire);
  measure();
}
function measure() {
  holder.updateMatrixWorld(true);
  holder.traverse((o) => { if (o.isSkinnedMesh) o.skeleton.update(); });
  const box = new THREE.Box3().setFromObject(holder, true);
  const size = box.getSize(new THREE.Vector3());
  let tris = 0, verts = 0; const mats = new Set(); let bones = 0;
  holder.traverse((o) => {
    if (!o.isMesh || o.userData.isOutline) return;
    const g = o.geometry; const n = g.index ? g.index.count / 3 : g.attributes.position.count / 3;
    tris += n; verts += g.attributes.position.count; [].concat(o.material).forEach((m) => mats.add(m.name || m.uuid));
    if (o.isSkinnedMesh) bones = Math.max(bones, o.skeleton.bones.length);
  });
  const hM = size.y / M;
  makeRuler(size.y, Math.ceil(hM * 2) / 2);
  $('g-info').innerHTML = '';
  const t = document.createElement('table');
  const row = (k, v) => { const r = t.insertRow(); r.insertCell().textContent = k; r.insertCell().textContent = v; };
  row('Altura', `${hM.toFixed(2).replace('.', ',')} m (${size.y.toFixed(2).replace('.', ',')} u)`);
  row('Largura × prof.', `${(size.x / M).toFixed(2).replace('.', ',')} × ${(size.z / M).toFixed(2).replace('.', ',')} m`);
  row('Triângulos', Math.round(tris).toLocaleString('pt-BR'));
  row('Vértices', verts.toLocaleString('pt-BR'));
  row('Materiais', mats.size);
  if (bones) row('Ossos', bones);
  if (current) row('Animações', current.clips.length);
  const b = document.createElement('b'); b.textContent = item.nome;
  $('g-info').append(b, t);
  frame(size);
  window.__stats = { h: hM, tris: Math.round(tris), verts, mats: mats.size, bones, clips: current ? current.clips : [] };
}
let target = new THREE.Vector3(0, 1, 0), dist = 6, fit = new THREE.Vector3(1, 2, 1);
function frame(size) {
  target.set(0, size.y * 0.5, 0); fit.copy(size);
  dist = Math.max(size.y, size.x * 1.2) * 2.1 + 0.5;
  controls.target.copy(target);
  cam.position.set(dist * 0.35, size.y * 0.6, dist);
  controls.update();
}
function setWire(on) {
  wire = on; $('g-arame').classList.toggle('on', on);
  holder.traverse((o) => { if (o.isMesh) [].concat(o.material).forEach((m) => { m.wireframe = on; }); });
}

$('g-modo').onclick = () => { turn = !turn; $('g-modo').classList.toggle('on', turn); $('g-rotulos').hidden = !turn; $('g-info').hidden = turn; };
$('g-pausa').onclick = () => { paused = !paused; $('g-pausa').classList.toggle('on', paused); };
$('g-arame').onclick = () => setWire(!wire);
$('g-regua').onclick = () => { ruler.visible = grid.visible = !ruler.visible; $('g-regua').classList.toggle('on', ruler.visible); };
$('g-anim').onchange = (e) => current && current.play(e.target.value);
$('g-luz').onchange = (e) => LUZ[e.target.value]();
LUZ.dia();

// ---- desenho: uma vista livre, ou cinco vistas lado a lado (frente, 3/4, lateral, 3/4 costas, costas)
const clock = new THREE.Timer();
const tcam = new THREE.PerspectiveCamera(22, 1, 0.05, 200);
function resize() {
  const w = Math.max(1, innerWidth - SIDE), h = innerHeight;
  renderer.setSize(w, h, false);
  cam.aspect = w / h; cam.updateProjectionMatrix();
}
addEventListener('resize', resize); resize();
function loop() {
  requestAnimationFrame(loop);
  clock.update(); const dt = Math.min(clock.getDelta(), 0.1);
  wind.value += dt;
  if (current && !paused) current.mixer.update(dt);
  const w = Math.max(1, innerWidth - SIDE), h = innerHeight;
  if (!turn) {
    renderer.setScissorTest(false); renderer.setViewport(0, 0, w, h);
    controls.update(); renderer.render(scene, cam);
    return;
  }
  ruler.visible = false;
  renderer.setScissorTest(true);
  const n = 5, vw = w / n;
  const angles = [0, -Math.PI / 4, -Math.PI / 2, -Math.PI * 3 / 4, Math.PI];
  const hh = target.y * 2;
  tcam.aspect = vw / h; tcam.updateProjectionMatrix();
  // cabe na altura e na largura (a maior entre largura e profundidade, porque a vista gira)
  const tv = Math.tan(THREE.MathUtils.degToRad(tcam.fov / 2)), th = tv * tcam.aspect;
  const dh = (hh / 2) / tv * 1.12;
  const d = Math.max(dh, Math.min((Math.max(fit.x, fit.z) / 2) / th * 1.12, dh * 1.35), 2);
  for (let i = 0; i < n; i++) {
    renderer.setViewport(i * vw, 0, vw, h); renderer.setScissor(i * vw, 0, vw, h);
    tcam.position.set(Math.sin(angles[i]) * d, target.y, Math.cos(angles[i]) * d);
    tcam.lookAt(0, target.y, 0);
    renderer.render(scene, tcam);
  }
  ruler.visible = $('g-regua').classList.contains('on');
}
loop();

// ---- lista
(async () => {
  manifest = await (await fetch('/assets/manifest.json', { cache: 'no-store' })).json();
  const groups = {};
  for (const it of manifest) (groups[it.categoria] ||= []).push(it);
  for (const [g, list] of Object.entries(groups)) {
    const h = document.createElement('h2'); h.textContent = g; $('g-lista').appendChild(h);
    for (const it of list) {
      const b = document.createElement('button'); b.dataset.id = it.id; b.textContent = it.nome;
      if (it.legado) { const s = document.createElement('small'); s.textContent = 'legado'; b.appendChild(s); }
      b.onclick = () => load(it); $('g-lista').appendChild(b);
    }
  }
  const q = new URLSearchParams(location.search);
  if (q.get('luz')) { $('g-luz').value = q.get('luz'); LUZ[q.get('luz')](); }
  if (q.get('modo') === 'turn') $('g-modo').click();
  const first = manifest.find((x) => x.id === q.get('a')) || manifest[0];
  if (first) await load(first);
  if (q.get('anim') && current) { $('g-anim').value = q.get('anim'); current.play(q.get('anim')); }
  window.__ready = true;
})();
window.__cam = { cam, controls };
// para os testes: congela uma animação num ponto (0..1) do clipe
window.__setAnim = (name, frac) => {
  if (!current) return;
  current.mixer.stopAllAction(); current.play(name);
  const a = current.mixer._actions.find((x) => x.getClip().name === name) || current.mixer._actions[0];
  a.reset(); a.play(); a.paused = false; a.setEffectiveWeight(1);
  current.mixer.update(0); a.time = frac * a.getClip().duration; current.mixer.update(0);
  paused = true;
};
window.__galeria = { load: (id) => load(manifest.find((x) => x.id === id)), get item() { return item; } };
