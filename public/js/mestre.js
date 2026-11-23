// Tela do mestre: mapa visto de cima, para montar a cena e acompanhar os jogadores.
import * as THREE from 'three';
import { MONSTERS, PROPS, HEROES, Session, makeRenderer, G, sizeOf } from './common.js';
import { TERRAINS, BIOMES, generateBiome } from './terreno.js';
import { fmtArea, SHAPES } from './area.js';
import { RulerDraw, makeLabel, medir, toScreen } from './regua.js';
import { MundoView, ImagemView, corDe } from './mundo.js';
import { CLASSES, HEROI_CLASSE } from './dnd-dados.js';
import { slotsMax, usosMax, USO_NOME, mod, fmtMod, cdMagia, circMax, magiaClerigo, magiasDominio } from './regras.js';
import { M2U, fmtM, logText, TurnOrder, banner, toast, chime, makeRangeRing, setPortrait, warmPortraits } from './combate-ui.js';

const $ = (id) => document.getElementById(id);
const SIDE = 300;
const canvas = $('c');
const renderer = makeRenderer(canvas, false);
const scene = new THREE.Scene();
scene.background = new THREE.Color(0x0b0b10);
scene.add(new THREE.AmbientLight(0xffffff, 1.5));
const sun = new THREE.DirectionalLight(0xffffff, 1.6);
sun.position.set(-6, 20, 8); scene.add(sun);

const camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0.1, 200);
camera.up.set(0, 0, -1);
const view = { cx: 20, cz: 20, size: 30 }; // size = metade da altura visível, em unidades de mundo
function applyCamera() {
  const w = Math.max(1, innerWidth - SIDE), h = innerHeight;
  renderer.setSize(w, h, false);
  const a = w / h;
  camera.left = -view.size * a; camera.right = view.size * a; camera.top = view.size; camera.bottom = -view.size;
  camera.position.set(view.cx, 80, view.cz);
  camera.lookAt(view.cx, 0, view.cz);
  camera.updateProjectionMatrix();
}
applyCamera();
addEventListener('resize', applyCamera);

// marcadores
const ring = new THREE.Mesh(new THREE.RingGeometry(0.9, 1.05, 40), new THREE.MeshBasicMaterial({ color: 0xffd36b, depthTest: false }));
ring.rotation.x = -Math.PI / 2; ring.position.y = 4.3; ring.visible = false; ring.renderOrder = 5; scene.add(ring);
const spawnMark = new THREE.Mesh(new THREE.RingGeometry(0.5, 0.75, 4), new THREE.MeshBasicMaterial({ color: 0x57d6a3, depthTest: false }));
spawnMark.rotation.x = -Math.PI / 2; spawnMark.position.y = 4.2; spawnMark.renderOrder = 4; scene.add(spawnMark);

// grade e contorno do pincel
let grid = null;
function buildGrid(W, H) {
  if (grid) { grid.geometry.dispose(); grid.removeFromParent(); }
  const pts = [];
  for (let i = 0; i <= W; i++) pts.push(i * G, 0, 0, i * G, 0, H * G);
  for (let j = 0; j <= H; j++) pts.push(0, 0, j * G, W * G, 0, j * G);
  const geo = new THREE.BufferGeometry(); geo.setAttribute('position', new THREE.Float32BufferAttribute(pts, 3));
  grid = new THREE.LineSegments(geo, new THREE.LineBasicMaterial({ color: 0x000000, transparent: true, opacity: 0.16, depthTest: false }));
  grid.position.y = 0.12; grid.renderOrder = 1; scene.add(grid);
}
const cursor = new THREE.Mesh(new THREE.PlaneGeometry(1, 1), new THREE.MeshBasicMaterial({ color: 0xffd36b, transparent: true, opacity: 0.35, depthTest: false }));
cursor.rotation.x = -Math.PI / 2; cursor.position.y = 4.4; cursor.renderOrder = 6; cursor.visible = false; scene.add(cursor);

// ---------------------------------------------------------------- sessão
let armed = null;        // item da paleta pronto para colocar
let selected = null;     // id da entidade selecionada
let settingSpawn = false;
let fitKey = '';

const session = new Session({
  scene, role: 'gm', topDown: true,
  on: {
    status(ok) { $('status').textContent = ok ? 'Conectado' : 'Sem conexão com o servidor…'; },
    map(map, world) {
      const key = map.name + '|' + map.w + 'x' + map.h;
      if (key !== fitKey) { // só reenquadra quando o mapa é outro; editar paredes não mexe na câmera
        fitKey = key;
        view.cx = world.bounds.w / 2; view.cz = world.bounds.h / 2;
        const a = Math.max(1, innerWidth - SIDE) / innerHeight;
        view.size = Math.max(world.bounds.h / 2, world.bounds.w / 2 / a) * 1.08;
        applyCamera();
      }
      walls = map.walls.map((w) => w.slice()); wdoors = map.doors.map((d) => ({ ...d })); drawWallOverlay(); refreshSaves();
      $('mapa-nome').textContent = `${map.name} — ${map.w}×${map.h} quadrados, ${map.walls.length} trechos de parede, ${map.doors.length} portas`;
      $('piso').hidden = !map.hasImage;
      $('piso').textContent = map.floorMode === 'image' ? 'Chão: imagem do mapa' : 'Chão: peças 3D';
      spawnMark.position.set(map.spawn.x, 4.2, map.spawn.z);
      select(null);
      TW = Math.ceil(map.w); TH = Math.ceil(map.h); cells = map.terrain.cells.split('');
      buildGrid(TW, TH); $('clima').value = map.terrain.biome;
    },
    spawn(s) { spawnMark.position.set(s.x, 4.2, s.z); },
    aoes() { renderAreaCards(); },
    aoeNew(a) { onNewArea(a); },
    terrain(t) { cells = t.cells.split(''); $('clima').value = t.biome; },
    players(list) {
      $('jogadores').innerHTML = '';
      if (!list.length) { const li = document.createElement('li'); li.className = 'pequeno'; li.textContent = 'Nenhum jogador conectado.'; $('jogadores').appendChild(li); }
      for (const p of list) {
        const li = document.createElement('li');
        const h = HEROES.find((x) => x.id === p.hero);
        li.className = p.off ? 'off' : '';
        li.append(`${p.off ? '○' : '●'} ${p.name} (${h ? h.nome : p.hero})${p.off ? ' · fora do ar' : ''}`);
        // deslocamento de voo: 0 = não voa; com valor, o jogador ganha os botões de subir e descer
        const voo = document.createElement('label'); voo.className = 'voo-jog'; voo.title = 'Deslocamento de voo deste jogador (0 = não voa)';
        voo.append('✈', field('vel', String(p.fly || 0).replace('.', ','), (v) => session.send({ t: 'player_set', id: p.id, fly: Number(String(v).replace(',', '.')) || 0 }), { inputMode: 'decimal' }), 'm');
        voo.classList.toggle('on', (p.fly || 0) > 0);
        li.appendChild(voo);
        const x = document.createElement('button'); x.textContent = '✕'; x.title = 'Tirar este jogador da sessão';
        x.onclick = () => { if (confirm(`Tirar ${p.name} da sessão? O personagem some do mapa e do combate.`)) session.send({ t: 'player_del', id: p.id }); };
        li.appendChild(x);
        $('jogadores').appendChild(li);
      }
      renderCombat();
    },
    combat: () => renderCombat(),
    fichas: () => renderFichas(),
    mesa: () => aplicaMesa(),
    rotas: () => mundo.onRotas(),
    imagens: () => renderImagens(),
    ping: (m) => mundo.onPing(m),
    traco: (m) => { if (m.ctx === 'cena') tracoCena(m); else mundo.onTraco(m); },
    clog(e) { toast(logText(e)); },
    cfx(fx) { if (fx === 'start') banner('start', 'COMBATE!', 'Rodada 1'); if (fx === 'end') banner('end', 'FIM DO COMBATE', ''); },
    frozen(on) { $('congelar').classList.toggle('on', on); $('congelar').textContent = on ? 'Movimento pausado — clique para liberar' : 'Pausar movimento dos jogadores'; },
    ents() { if (selected && !session.ents.has(selected)) select(null); renderCombat(); },
    oa(m) {
      // reação de um monstro: se o mestre está na visão desse monstro, quem pergunta é a visão
      const it = C().list.find((x) => x.cid === m.cid);
      if (!it || it.kind !== 'monster' || (visao && visao.id === it.ref)) return;
      gmOpportunity(m);
    },
    deny(msg) { toast(msg); },
  },
});
window.__session = session;

// ---------------------------------------------------------------- paleta
function paleta(el, itens, kind) {
  for (const it of itens) {
    const b = document.createElement('button');
    b.className = 'bt'; b.textContent = it.nome;
    b.onclick = () => {
      const same = armed && armed.model === it.id;
      setBrush(null); setWallTool(null);
      armed = same ? null : { kind, model: it.id, btn: b };
      settingSpawn = false; $('entrada-bt').classList.remove('sel');
      document.querySelectorAll('#monstros .bt, #objetos .bt').forEach((x) => x.classList.toggle('sel', !same && x === b));
    };
    el.appendChild(b);
  }
}
paleta($('monstros'), MONSTERS, 'monster');
paleta($('objetos'), PROPS, 'prop');
function disarm() { setBrush(null); setWallTool(null); armed = null; document.querySelectorAll('#monstros .bt, #objetos .bt').forEach((x) => x.classList.remove('sel')); }

function nomeDe(d) {
  const it = (d.kind === 'monster' ? MONSTERS : PROPS).find((x) => x.id === d.model);
  return it ? it.nome : d.model;
}
function select(id) {
  selected = id;
  const e = id ? session.ents.get(id) : null;
  ring.visible = !!e;
  $('sel-ctl').hidden = !e; $('sel-nada').hidden = !!e;
  if (e) { $('sel-nome').textContent = nomeDe(e.data); $('escala').value = e.data.scale; }
  $('ver-visao').hidden = !(e && e.data.kind === 'monster');
}
function changeSel(patch) {
  const e = selected && session.ents.get(selected);
  if (!e) return;
  session.upsertEnt({ ...e.data, ...patch });
  session.send({ t: 'ent_update', id: e.data.id, ...patch });
}
$('girar-e').onclick = () => changeSel({ ry: session.ents.get(selected).data.ry + Math.PI / 8 });
$('girar-d').onclick = () => changeSel({ ry: session.ents.get(selected).data.ry - Math.PI / 8 });
$('escala').oninput = (e) => changeSel({ scale: Number(e.target.value) });
$('apagar').onclick = () => { if (selected) { session.send({ t: 'ent_del', id: selected }); select(null); } };
$('congelar').onclick = () => session.send({ t: 'freeze', on: !session.frozen });
$('piso').onclick = () => session.send({ t: 'floor', mode: session.map.floorMode === 'image' ? 'tiles' : 'image' });
$('entrada-bt').onclick = () => { settingSpawn = !settingSpawn; disarm(); $('entrada-bt').classList.toggle('sel', settingSpawn); };

// ---------------------------------------------------------------- terreno
let TW = 0, TH = 0, cells = [];
let brush = null, brushSize = 1, rectMode = false, sendTimer = null, dirty = false;
function setBrush(id) {
  brush = id; cursor.visible = false;
  document.querySelectorAll('#pinceis .bt').forEach((b) => b.classList.toggle('sel', b.dataset.id === id));
  if (id) { setWallTool(null); armed = null; document.querySelectorAll('#monstros .bt, #objetos .bt').forEach((x) => x.classList.remove('sel')); settingSpawn = false; $('entrada-bt').classList.remove('sel'); }
}
for (const t of TERRAINS) {
  const b = document.createElement('button'); b.className = 'bt'; b.dataset.id = t.id;
  const sw = document.createElement('i'); sw.style.background = t.cor; b.append(sw, t.nome);
  b.onclick = () => setBrush(brush === t.id ? null : t.id);
  $('pinceis').appendChild(b);
}
for (const n of [1, 2, 3, 5]) {
  const b = document.createElement('button'); b.className = 'bt' + (n === 1 ? ' sel' : ''); b.textContent = n; b.style.flex = '1';
  b.onclick = () => { brushSize = n; [...$('tamanhos').children].forEach((x) => x.classList.toggle('sel', x === b)); };
  $('tamanhos').appendChild(b);
}
function setMode(r) { rectMode = r; $('modo-pincel').classList.toggle('sel', !r); $('modo-ret').classList.toggle('sel', r); }
$('modo-pincel').onclick = () => setMode(false); $('modo-ret').onclick = () => setMode(true); setMode(false);
for (const b of BIOMES) {
  const bt = document.createElement('button'); bt.className = 'bt'; bt.textContent = b.nome;
  bt.onclick = () => {
    if (!session.map) return;
    if (!confirm(`Preencher o mapa inteiro com o bioma ${b.nome}? Isso substitui o terreno pintado.`)) return;
    cells = generateBiome(b.id, TW, TH, (Math.random() * 1e6) | 0).split('');
    commitTerrain(b.id, true);
  };
  $('biomas').appendChild(bt);
  const op = document.createElement('option'); op.value = b.id; op.textContent = b.nome; $('clima').appendChild(op);
}
$('clima').onchange = (e) => commitTerrain(e.target.value, true);
// aplica na tela na hora e avisa o servidor (no máximo ~12 vezes por segundo enquanto pinta)
function commitTerrain(biome, now) {
  const t = { biome: biome || session.map.terrain.biome, cells: cells.join('') };
  session.setTerrain(t);
  const push = () => { sendTimer = null; dirty = false; session.send({ t: 'terrain', ...session.map.terrain }); };
  if (now) { clearTimeout(sendTimer); push(); } else { dirty = true; if (!sendTimer) sendTimer = setTimeout(push, 80); }
}
const cellOf = (p) => ({ i: Math.floor(p.x / G), j: Math.floor(p.z / G) });
function footprint(c) { // quadrados cobertos pelo pincel centrado em c
  const a = -Math.floor((brushSize - 1) / 2);
  return { i0: c.i + a, j0: c.j + a, i1: c.i + a + brushSize - 1, j1: c.j + a + brushSize - 1 };
}
function fill(r) {
  let changed = false;
  for (let j = Math.max(0, r.j0); j <= Math.min(TH - 1, r.j1); j++) for (let i = Math.max(0, r.i0); i <= Math.min(TW - 1, r.i1); i++) {
    if (cells[j * TW + i] !== brush) { cells[j * TW + i] = brush; changed = true; }
  }
  if (changed) commitTerrain();
}
function showCursor(r) {
  const w = (r.i1 - r.i0 + 1) * G, h = (r.j1 - r.j0 + 1) * G;
  cursor.scale.set(w, h, 1); cursor.position.set(r.i0 * G + w / 2, 4.4, r.j0 * G + h / 2); cursor.visible = true;
}
const rectOf = (a, b) => ({ i0: Math.min(a.i, b.i), j0: Math.min(a.j, b.j), i1: Math.max(a.i, b.i), j1: Math.max(a.j, b.j) });

// ---------------------------------------------------------------- paredes e portas
let walls = [], wdoors = [], wallTool = null, wallTimer = null;
const overlay = new THREE.LineSegments(new THREE.BufferGeometry(), new THREE.LineBasicMaterial({ vertexColors: true, depthTest: false }));
overlay.position.y = 4.6; overlay.renderOrder = 7; overlay.visible = false; scene.add(overlay);
const preview = new THREE.Line(new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(), new THREE.Vector3()]), new THREE.LineBasicMaterial({ color: 0xffffff, depthTest: false }));
preview.position.y = 4.7; preview.renderOrder = 8; preview.visible = false; preview.frustumCulled = false; scene.add(preview);
function drawWallOverlay() {
  const P = [], C = [];
  for (const w of walls) { P.push(w[0] * G, 0, w[1] * G, w[2] * G, 0, w[3] * G); C.push(1, 0.83, 0.42, 1, 0.83, 0.42); }
  for (const d of wdoors) { P.push(d.x1 * G, 0, d.y1 * G, d.x2 * G, 0, d.y2 * G); C.push(0.34, 0.84, 0.64, 0.34, 0.84, 0.64); }
  overlay.geometry.dispose(); overlay.geometry = new THREE.BufferGeometry();
  overlay.geometry.setAttribute('position', new THREE.Float32BufferAttribute(P, 3));
  overlay.geometry.setAttribute('color', new THREE.Float32BufferAttribute(C, 3));
}
function setWallTool(t) {
  wallTool = t; overlay.visible = !!t; preview.visible = false;
  for (const [id, k] of [['w-parede', 'wall'], ['w-porta', 'door'], ['w-apagar', 'erase']]) $(id).classList.toggle('sel', t === k);
  if (t) { brush = null; cursor.visible = false; document.querySelectorAll('#pinceis .bt, #monstros .bt, #objetos .bt').forEach((x) => x.classList.remove('sel')); armed = null; settingSpawn = false; $('entrada-bt').classList.remove('sel'); }
}
$('w-parede').onclick = () => setWallTool(wallTool === 'wall' ? null : 'wall');
$('w-porta').onclick = () => setWallTool(wallTool === 'door' ? null : 'door');
$('w-apagar').onclick = () => setWallTool(wallTool === 'erase' ? null : 'erase');
// a linha amarela aparece na hora; o 3D é refeito logo depois, para todo mundo
function commitWalls() {
  drawWallOverlay();
  clearTimeout(wallTimer);
  wallTimer = setTimeout(() => session.send({ t: 'walls', walls, doors: wdoors }), 250);
}
const snap = (p, e) => { const k = e.shiftKey ? 2 : 1; return { x: Math.round((p.x / G) * k) / k, y: Math.round((p.z / G) * k) / k }; };
function segDist(px, py, x1, y1, x2, y2) {
  const vx = x2 - x1, vy = y2 - y1, len2 = vx * vx + vy * vy || 1;
  const t = Math.max(0, Math.min(1, ((px - x1) * vx + (py - y1) * vy) / len2));
  return { d: Math.hypot(px - (x1 + vx * t), py - (y1 + vy * t)), t };
}
// apaga o trecho de um quadrado em volta do ponto; portas saem inteiras
function eraseAt(p) {
  const px = p.x / G, py = p.z / G;
  let best = null, bd = 0.45;
  walls.forEach((w, i) => { const r = segDist(px, py, w[0], w[1], w[2], w[3]); if (r.d < bd) { bd = r.d; best = { i, t: r.t }; } });
  let bestDoor = -1;
  wdoors.forEach((d, i) => { const r = segDist(px, py, d.x1, d.y1, d.x2, d.y2); if (r.d < bd) { bd = r.d; bestDoor = i; } });
  if (bestDoor >= 0) { wdoors.splice(bestDoor, 1); commitWalls(); return; }
  if (!best) return;
  const w = walls[best.i], L = Math.hypot(w[2] - w[0], w[3] - w[1]), s = best.t * L;
  const a = Math.max(0, Math.min(L - 1, Math.floor(s))), b = Math.min(L, a + 1);
  const at = (d) => [w[0] + ((w[2] - w[0]) * d) / L, w[1] + ((w[3] - w[1]) * d) / L];
  const parts = [];
  if (a > 0.05) parts.push([w[0], w[1], ...at(a)]);
  if (L - b > 0.05) parts.push([...at(b), w[2], w[3]]);
  walls.splice(best.i, 1, ...parts);
  commitWalls();
}

// ---------------------------------------------------------------- mapas salvos
async function refreshSaves() {
  const j = await (await fetch('/api/saves', { cache: 'no-store' })).json();
  const el = $('salvos'); el.innerHTML = '';
  if (!j.saves.length) { const p = document.createElement('p'); p.className = 'pequeno'; p.textContent = 'Nenhum mapa salvo ainda.'; el.appendChild(p); }
  for (const sv of j.saves) {
    const row = document.createElement('div'); row.className = 'salvo';
    const open = document.createElement('button'); open.className = 'bt' + (sv.name === j.current ? ' atual' : ''); open.textContent = sv.name; open.title = 'Abrir este mapa';
    open.onclick = async () => {
      if (!confirm(`Abrir "${sv.name}"? O que não foi salvo no mapa atual será perdido.`)) return;
      await fetch('/api/saves/load?name=' + encodeURIComponent(sv.name), { method: 'POST' });
      $('mapa-msg').textContent = `Mapa "${sv.name}" aberto.`;
    };
    const del = document.createElement('button'); del.className = 'bt x'; del.textContent = '✕'; del.title = 'Apagar este mapa salvo';
    del.onclick = async () => {
      if (!confirm(`Apagar o mapa salvo "${sv.name}"? Isso não pode ser desfeito.`)) return;
      await fetch('/api/saves?name=' + encodeURIComponent(sv.name), { method: 'DELETE' }); refreshSaves();
    };
    row.append(open, del); el.appendChild(row);
  }
}
$('salvar').onclick = async () => {
  const name = prompt('Nome do mapa:', session.map ? session.map.name : '');
  if (!name) return;
  const j = await (await fetch('/api/saves?name=' + encodeURIComponent(name), { method: 'POST' })).json();
  $('mapa-msg').textContent = j.error || `Mapa salvo como "${j.name}".`;
  if (j.name && session.map) { session.map.name = j.name; fitKey = j.name + '|' + session.map.w + 'x' + session.map.h; }
  refreshSaves();
};
$('novo').onclick = async () => {
  const txt = prompt('Tamanho do mapa em quadrados (largura x altura):', '30x20');
  if (!txt) return;
  const m = txt.match(/(\d+)\D+(\d+)/);
  if (!m) { $('mapa-msg').textContent = 'Não entendi o tamanho. Use o formato 30x20.'; return; }
  if (!confirm('Criar um mapa vazio? O que não foi salvo no mapa atual será perdido.')) return;
  await fetch(`/api/blank?w=${m[1]}&h=${m[2]}&name=${encodeURIComponent('Mapa novo')}`, { method: 'POST' });
  $('mapa-msg').textContent = 'Mapa vazio criado. Desenhe as paredes e pinte o terreno.';
};

// ---------------------------------------------------------------- mapa: importar
$('importar').onclick = () => $('arquivo').click();
$('arquivo').onchange = async (ev) => {
  const f = ev.target.files[0];
  if (!f) return;
  $('mapa-msg').textContent = `Enviando ${f.name}…`;
  try {
    const r = await fetch('/api/map?name=' + encodeURIComponent(f.name.replace(/\.[^.]+$/, '')), { method: 'POST', body: f });
    const j = await r.json();
    $('mapa-msg').textContent = j.error ? j.error : `Importado: ${j.walls} trechos de parede, ${j.doors} portas, ${j.lights} luzes${j.hasImage ? ', com imagem' : ''}.`;
  } catch (e) { $('mapa-msg').textContent = 'Falha no envio: ' + e.message; }
  ev.target.value = '';
};
$('exemplo').onclick = async () => {
  if (!confirm('Trocar o mapa atual pelo mapa de exemplo? A cena atual será substituída.')) return;
  await fetch('/api/sample', { method: 'POST' });
  $('mapa-msg').textContent = 'Mapa de exemplo carregado.';
};

// ---------------------------------------------------------------- mouse
const ray = new THREE.Raycaster(), ndc = new THREE.Vector2(), plane = new THREE.Plane(new THREE.Vector3(0, 1, 0), 0), hit = new THREE.Vector3();
function worldAt(e) {
  const r = canvas.getBoundingClientRect();
  ndc.set(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1);
  ray.setFromCamera(ndc, camera);
  return ray.ray.intersectPlane(plane, hit) ? { x: hit.x, z: hit.z } : null;
}
function pick(p) {
  let best = null, bd = Infinity;
  for (const pl of session.players.values()) {
    const d = Math.hypot(pl.holder.position.x - p.x, pl.holder.position.z - p.z);
    if (d < 1.1 && d < bd) { bd = d; best = { type: 'player', ref: pl }; }
  }
  for (const e of session.ents.values()) {
    const d = Math.hypot(e.data.x - p.x, e.data.z - p.z);
    if (d < Math.max(0.9, e.radius * 1.1) && d < bd) { bd = d; best = { type: 'ent', ref: e }; }
  }
  return best;
}
// monstro grande ocupa quadrados inteiros: 3 x 3 fica com o centro no meio de um quadrado
function snapBig(model, p) {
  const n = sizeOf(model); if (n <= 1) return { x: p.x, z: p.z };
  const off = n % 2 ? 0.5 : 0;
  return { x: (Math.round(p.x / G - off) + off) * G, z: (Math.round(p.z / G - off) + off) * G };
}
let drag = null;
canvas.addEventListener('contextmenu', (e) => e.preventDefault());
// em qualquer lugar da página (o clique direito pode terminar fora do mapa, em cima de um rótulo ou de um painel);
// campos de texto continuam com o menu normal (copiar/colar)
document.addEventListener('contextmenu', (e) => { if (!e.target.closest('input, textarea, [contenteditable]')) e.preventDefault(); }, true);
canvas.addEventListener('pointerdown', (e) => {
  canvas.setPointerCapture(e.pointerId);
  const p = worldAt(e);
  if (!p) return;
  if (e.button !== 0) { drag = { type: 'pan', x: e.clientX, y: e.clientY }; return; }
  if (reguaOn) { drag = { type: 'regua' }; rgA = p; rgB = p; drawRegua(); return; }
  if (picking) {
    const got = pick(p);
    if (got && (got.type === 'player' || got.ref.data.kind === 'monster')) toggleMember(got);
    return;
  }
  if (settingSpawn) {
    session.send({ t: 'spawn', x: p.x, z: p.z });
    settingSpawn = false; $('entrada-bt').classList.remove('sel');
    return;
  }
  if (wallTool === 'erase') { drag = { type: 'erase' }; eraseAt(p); return; }
  if (wallTool) {
    const a = snap(p, e);
    drag = { type: 'wall', from: a, to: a };
    preview.geometry.setFromPoints([new THREE.Vector3(a.x * G, 0, a.y * G), new THREE.Vector3(a.x * G, 0, a.y * G)]);
    preview.material.color.setHex(wallTool === 'door' ? 0x57d6a3 : 0xffffff); preview.visible = true;
    return;
  }
  if (brush) {
    const c = cellOf(p);
    if (rectMode) drag = { type: 'rect', from: c, to: c };
    else { drag = { type: 'paint' }; fill(footprint(c)); }
    return;
  }
  const got = pick(p);
  if (got && got.type === 'ent') { select(got.ref.data.id); drag = { type: 'ent', ref: got.ref, ox: got.ref.data.x - p.x, oz: got.ref.data.z - p.z }; return; }
  if (got && got.type === 'player') { got.ref.dragging = true; drag = { type: 'player', ref: got.ref }; return; }
  if (armed) { const q = armed.kind === 'monster' ? snapBig(armed.model, p) : p; session.send({ t: 'ent_add', kind: armed.kind, model: armed.model, x: q.x, z: q.z, ry: 0, scale: 1 }); return; }
  const door = session.nearestDoor(p, 1.3);
  if (door) { session.send({ t: 'door', i: door.i }); return; }
  select(null);
  drag = { type: 'pan', x: e.clientX, y: e.clientY };
});
let lastSend = 0;
canvas.addEventListener('pointermove', (e) => {
  if (drag && (drag.type === 'wall' || drag.type === 'erase')) {
    const p = worldAt(e);
    if (!p) return;
    if (drag.type === 'erase') { eraseAt(p); return; }
    drag.to = snap(p, e);
    preview.geometry.setFromPoints([new THREE.Vector3(drag.from.x * G, 0, drag.from.y * G), new THREE.Vector3(drag.to.x * G, 0, drag.to.y * G)]);
    return;
  }
  if (brush && (!drag || drag.type === 'paint' || drag.type === 'rect')) {
    const p = worldAt(e);
    if (p) {
      const c = cellOf(p);
      if (drag && drag.type === 'rect') { drag.to = c; showCursor(rectOf(drag.from, c)); }
      else { showCursor(footprint(c)); if (drag) fill(footprint(c)); }
    }
    return;
  }
  if (!drag) return;
  if (drag.type === 'regua') { const p = worldAt(e); if (p) { rgB = p; drawRegua(); } return; }
  if (drag.type === 'pan') {
    const k = (view.size * 2) / innerHeight;
    view.cx -= (e.clientX - drag.x) * k; view.cz -= (e.clientY - drag.y) * k;
    drag.x = e.clientX; drag.y = e.clientY; applyCamera();
    return;
  }
  const p = worldAt(e);
  if (!p) return;
  if (drag.type === 'ent') {
    const d = drag.ref.data;
    session.upsertEnt({ ...d, x: p.x + drag.ox, z: p.z + drag.oz });
    if (performance.now() - lastSend > 60) { lastSend = performance.now(); session.send({ t: 'ent_update', id: d.id, x: d.x, z: d.z }); }
  } else if (drag.type === 'player') {
    drag.ref.holder.position.set(p.x, 0, p.z);
  }
});
function endDrag() {
  if (!drag) return;
  if (drag.type === 'rect') fill(rectOf(drag.from, drag.to));
  if (drag.type === 'wall') {
    preview.visible = false;
    const a = drag.from, b = drag.to;
    if (Math.hypot(b.x - a.x, b.y - a.y) >= 0.4) {
      if (wallTool === 'door') wdoors.push({ x1: a.x, y1: a.y, x2: b.x, y2: b.y, closed: true });
      else walls.push([a.x, a.y, b.x, b.y]);
      commitWalls();
    }
  }
  if (drag.type === 'ent') {
    const d = drag.ref.data;
    if (d.kind === 'monster' && sizeOf(d.model) > 1) { const q = snapBig(d.model, d); session.upsertEnt({ ...d, x: q.x, z: q.z }); }
    session.send({ t: 'ent_update', id: d.id, x: d.x, z: d.z });
  }
  if (drag.type === 'player') {
    const pl = drag.ref, h = pl.holder.position;
    pl.data.x = h.x; pl.data.z = h.z;
    session.send({ t: 'player_move', id: pl.data.id, x: h.x, z: h.z });
    setTimeout(() => { pl.dragging = false; }, 300);
  }
  drag = null;
}
canvas.addEventListener('pointerup', endDrag);
canvas.addEventListener('pointercancel', endDrag);
canvas.addEventListener('wheel', (e) => {
  e.preventDefault();
  view.size = Math.max(4, Math.min(200, view.size * (e.deltaY > 0 ? 1.12 : 0.89)));
  applyCamera();
}, { passive: false });
addEventListener('keydown', (e) => {
  if (e.target.tagName === 'INPUT') return;
  if (e.code === 'KeyR' && !e.ctrlKey && !e.metaKey) { setRegua(!reguaOn); return; }
  if (e.code === 'Escape' && reguaOn) { setRegua(false); return; }
  if (e.code === 'KeyN' && session.combat.active) { session.send({ t: 'c_next' }); return; }
  if (e.code === 'Escape') { disarm(); select(null); settingSpawn = false; $('entrada-bt').classList.remove('sel'); }
  if (!selected) return;
  if (e.code === 'KeyQ') $('girar-e').click();
  if (e.code === 'KeyE') $('girar-d').click();
  if (e.code === 'Delete' || e.code === 'Backspace') $('apagar').click();
});

// ---------------------------------------------------------------- abas
document.querySelectorAll('.abas button').forEach((b) => {
  b.onclick = () => {
    document.querySelectorAll('.abas button').forEach((x) => x.classList.toggle('sel', x === b));
    document.querySelectorAll('section.aba').forEach((sec) => { sec.hidden = sec.dataset.aba !== b.dataset.aba; });
    if (b.dataset.aba !== 'combate') setPicking(false);
  };
});

// ---------------------------------------------------------------- combate
const ordemGM = new TurnOrder($('ordem-gm'), { gm: true, max: 14 });
let picking = false;
function setPicking(on) {
  picking = on;
  $('cb-pick').classList.toggle('on', on);
  $('cb-pick').textContent = on ? 'Selecionando… (clique de novo para parar)' : 'Selecionar no mapa';
  if (on) { disarm(); select(null); }
}
$('cb-pick').onclick = () => setPicking(!picking);
const C = () => session.combat;
const memberOf = (kind, ref) => C().list.find((x) => x.kind === kind && x.ref === ref);
function monsterName(model) {
  const base = (MONSTERS.find((m) => m.id === model) || { nome: model }).nome;
  const n = C().list.filter((x) => x.kind === 'monster' && x.model === model).length;
  return n ? `${base} ${n + 1}` : base;
}
function addPlayer(id) { if (!memberOf('player', id)) session.send({ t: 'c_add', kind: 'player', ref: id }); }
function addMonster(e) { if (!memberOf('monster', e.data.id)) session.send({ t: 'c_add', kind: 'monster', ref: e.data.id, name: monsterName(e.data.model), model: e.data.model }); }
function toggleMember(got) {
  if (got.type === 'player') {
    const it = memberOf('player', got.ref.data.id);
    if (it) session.send({ t: 'c_remove', cid: it.cid }); else addPlayer(got.ref.data.id);
  } else {
    const it = memberOf('monster', got.ref.data.id);
    if (it) session.send({ t: 'c_remove', cid: it.cid }); else addMonster(got.ref);
  }
}
$('cb-all-pl').onclick = () => { for (const p of session.players.values()) addPlayer(p.data.id); };
$('cb-all-mo').onclick = () => {
  // um por vez, para a numeração dos nomes sair certa
  const todo = [...session.ents.values()].filter((e) => e.data.kind === 'monster' && !memberOf('monster', e.data.id));
  const counts = {};
  for (const e of todo) {
    const base = (MONSTERS.find((m) => m.id === e.data.model) || { nome: e.data.model }).nome;
    const have = C().list.filter((x) => x.kind === 'monster' && x.model === e.data.model).length;
    counts[e.data.model] = (counts[e.data.model] ?? have) + 1;
    const n = counts[e.data.model];
    session.send({ t: 'c_add', kind: 'monster', ref: e.data.id, name: n > 1 ? `${base} ${n}` : base, model: e.data.model });
  }
};
$('cb-roll').onclick = () => {
  for (const it of C().list) if (it.kind === 'monster' && (it.init === null || it.init === undefined)) {
    session.send({ t: 'c_set', cid: it.cid, init: 1 + Math.floor(Math.random() * 20) });
  }
};
$('cb-sort').onclick = () => session.send({ t: 'c_sort' });
$('cb-start').onclick = () => {
  const missing = C().list.filter((x) => x.init === null || x.init === undefined);
  if (!C().list.length) { toast('Inclua participantes primeiro'); return; }
  if (missing.length && !confirm(`${missing.map((x) => x.name).join(', ')} sem iniciativa. Iniciar mesmo assim? (vão para o fim da ordem)`)) return;
  setPicking(false);
  session.send({ t: 'c_start' });
};
$('cb-next').onclick = () => session.send({ t: 'c_next' });
$('cb-prev').onclick = () => session.send({ t: 'c_prev' });
$('cb-end').onclick = () => { if (confirm('Encerrar o combate? A ordem de iniciativa será apagada.')) session.send({ t: 'c_end' }); };

function field(cls, value, onChange, attrs = {}) {
  const i = document.createElement('input'); i.className = cls; i.value = value ?? '';
  Object.assign(i, attrs);
  i.onchange = () => onChange(i.value);
  i.onkeydown = (e) => { if (e.key === 'Enter') i.blur(); e.stopPropagation(); };
  return i;
}
function miniBt(txt, title, on, cls = '') { const b = document.createElement('button'); b.className = 'mini ' + cls; b.textContent = txt; b.title = title; b.onclick = on; return b; }
let listSig = '';
function renderCombat() {
  const c = C();
  warmPortraits(c.list.map((x) => x.model));
  ordemGM.render(c, -1);
  $('cb-run').hidden = !c.active;
  $('cb-start').hidden = c.active;
  $('cb-roll').hidden = c.active;
  $('cb-pick-help').textContent = c.active ? 'Para incluir alguém no meio do combate, ligue a seleção e clique nele; depois ajuste a iniciativa e use "Reordenar".' : 'Ligue e clique nos jogadores e monstros do mapa para incluir ou tirar do combate.';
  if (c.active) $('cb-round').textContent = `RODADA ${c.round}`;
  // lista: só reconstrói quando algo mudou, e nunca por cima do campo que o mestre está editando
  const sig = JSON.stringify(c.list.map((x) => [x.cid, x.name, x.init, x.speed, x.fly, x.hidden, x.flags, x.reac])) + (c.cur && c.cur.cid);
  const editing = document.activeElement && document.activeElement.closest && document.activeElement.closest('#cb-list');
  if (sig !== listSig && !editing) {
    listSig = sig;
    const box = $('cb-list'); box.innerHTML = '';
    if (!c.list.length) box.innerHTML = '<p class="pequeno">Ninguém no combate ainda.</p>';
    c.list.forEach((it, i) => {
      const row = document.createElement('div');
      row.className = `cb-row ${it.kind}${c.cur && c.cur.cid === it.cid ? ' cur' : ''}`;
      const l1 = document.createElement('div'); l1.className = 'l1';
      const img = document.createElement('img'); img.alt = ''; setPortrait(img, it.model);
      l1.append(img, field('nome', it.name, (v) => session.send({ t: 'c_set', cid: it.cid, name: v }), { title: 'Nome na ordem de turno', disabled: it.kind === 'player' }),
        field('ini', it.init, (v) => session.send({ t: 'c_set', cid: it.cid, init: v === '' ? null : Number(v) }), { type: 'number', title: 'Iniciativa (só o mestre vê)', placeholder: 'ini' }),
        miniBt('✕', 'Tirar do combate', () => session.send({ t: 'c_remove', cid: it.cid }), 'x'));
      const l2 = document.createElement('div'); l2.className = 'l2';
      l2.append('Desloc.', field('vel', String(it.speed).replace('.', ','), (v) => session.send({ t: 'c_set', cid: it.cid, speed: Number(String(v).replace(',', '.')) }), { title: 'Deslocamento em metros' }), 'm',
        ' ✈', field('vel', String(it.fly || 0).replace('.', ','), (v) => session.send({ t: 'c_set', cid: it.cid, fly: Number(String(v).replace(',', '.')) || 0 }), { title: 'Deslocamento de voo em metros (0 = não voa)' }), 'm',
        miniBt(it.hidden ? 'Oculto' : 'Visível', 'Esconder dos jogadores na ordem de turno', () => session.send({ t: 'c_set', cid: it.cid, hidden: !it.hidden }), it.hidden ? 'on' : ''),
        miniBt('▲', 'Subir na ordem (empates)', () => session.send({ t: 'c_swap', cid: it.cid, dir: -1 })),
        miniBt('▼', 'Descer na ordem (empates)', () => session.send({ t: 'c_swap', cid: it.cid, dir: 1 })));
      if (it.flags && it.flags.length) { const f = document.createElement('span'); f.className = 'flags'; f.textContent = it.flags.join(', '); l2.append(f); }
      row.append(l1, l2);
      box.appendChild(row);
    });
  }
  renderCur();
  // registro
  if (c.log) {
    const box = $('cb-log');
    const lines = c.log.slice(-14).reverse();
    box.innerHTML = lines.length ? '' : '<p class="pequeno">As ações dos jogadores aparecem aqui.</p>';
    for (const e of lines) { const d = document.createElement('div'); d.className = 'ln'; d.innerHTML = '<small></small>'; d.firstChild.textContent = `R${e.round}`; d.append(logText(e)); box.appendChild(d); }
  }
}
let curSig = '';
function renderCur() {
  const c = C(), box = $('cb-cur');
  if (!c.active || !c.cur) { box.innerHTML = ''; curSig = ''; return; }
  const it = c.list.find((x) => x.cid === c.cur.cid);
  if (!it) return;
  const used = curMoved(it);
  const sig = [it.cid, it.name, c.cur.action, c.cur.bonus, it.reac, c.cur.budget, c.cur.dash, Math.round(used * 10)].join('|');
  if (sig === curSig) return;
  curSig = sig;
  box.innerHTML = '';
  const quem = document.createElement('div'); quem.className = 'quem';
  const img = document.createElement('img'); img.alt = ''; setPortrait(img, it.model);
  const nm = document.createElement('div'); nm.textContent = it.name;
  const sm = document.createElement('small'); sm.textContent = it.kind === 'player' ? 'Jogador — joga pelo celular' : 'Monstro — você move no mapa'; nm.appendChild(sm);
  quem.append(img, nm);
  const total = c.cur.budget, left = Math.max(0, total - used);
  const movl = document.createElement('div'); movl.className = 'movl';
  movl.innerHTML = 'Movimento: <b></b>';
  movl.querySelector('b').textContent = `${fmtM(used)} de ${fmtM(total)}${c.cur.dash ? ' (com Disparada)' : ''}`;
  const bar = document.createElement('div'); bar.className = 'bar'; bar.innerHTML = '<i></i>'; bar.firstChild.style.width = (total ? (left / total) * 100 : 0) + '%';
  const chips = document.createElement('div'); chips.className = 'chips';
  const chip = (label, used, what) => {
    const b = document.createElement('span'); b.className = 'chip' + (used ? ' usada' : ''); b.textContent = `${label}: ${used ? 'usada' : 'livre'}`;
    if (used) { b.title = 'Clique para devolver'; b.onclick = () => session.send({ t: 'c_restore', what }); }
    return b;
  };
  chips.append(chip('Ação', c.cur.action, 'action'), chip('Bônus', c.cur.bonus, 'bonus'), chip('Reação', it.reac, 'reaction'));
  const lb = document.createElement('div'); lb.className = 'linha-bt';
  lb.append(Object.assign(document.createElement('button'), { className: 'bt', textContent: '− 1,5 m', onclick: () => session.send({ t: 'c_extra', m: -1.5 }) }),
    Object.assign(document.createElement('button'), { className: 'bt', textContent: '+ 1,5 m', onclick: () => session.send({ t: 'c_extra', m: 1.5 }) }),
    Object.assign(document.createElement('button'), { className: 'bt', textContent: 'Devolver mov.', title: 'Zera o movimento usado a partir de onde está', onclick: () => session.send({ t: 'c_restore', what: 'move' }) }));
  box.append(quem, movl, bar, chips, lb);
}
// quanto quem está agindo já andou: jogador pelo que o servidor contou; monstro em linha reta desde o início do turno
function curMoved(it) {
  const c = C();
  if (it.kind === 'player' || session.turnUsed > 0) return session.turnUsed || 0;
  const p = session.combatantPos(it);
  return p ? Math.hypot(p.x - c.cur.sx, p.z - c.cur.sz) / M2U : 0;
}

// marcas no mapa: anel dourado em quem está no combate, alcance de quem está agindo
const rangeRing = makeRangeRing(0x5ff3ff);
rangeRing.material.depthTest = false; rangeRing.renderOrder = 9; scene.add(rangeRing);
const memberMarks = new Map();
const markGeo = new THREE.RingGeometry(0.95, 1.15, 32);
function updateCombatMarks(dt, t) {
  const c = C();
  const live = new Set();
  for (const it of c.list) {
    const p = session.combatantPos(it);
    if (!p) continue;
    live.add(it.cid);
    let m = memberMarks.get(it.cid);
    if (!m) {
      m = new THREE.Mesh(markGeo, new THREE.MeshBasicMaterial({ color: it.kind === 'player' ? 0x3fa8ff : 0xffd36b, depthTest: false, transparent: true }));
      m.rotation.x = -Math.PI / 2; m.renderOrder = 8; scene.add(m); memberMarks.set(it.cid, m);
    }
    const cur = c.active && c.cur && c.cur.cid === it.cid;
    m.position.set(p.x, 4.35, p.z);
    const big = it.kind === 'monster' && session.ents.get(it.ref) ? sizeOf(session.ents.get(it.ref).data.model) : 1;
    m.scale.setScalar((cur ? 1.25 + Math.sin(t * 5) * 0.08 : 1) * big);
    m.material.opacity = cur ? 1 : 0.75;
  }
  for (const [cid, m] of memberMarks) if (!live.has(cid)) { m.removeFromParent(); m.material.dispose(); memberMarks.delete(cid); }
  // alcance: jogador = o que sobra a partir de onde está; monstro = a partir de onde começou o turno
  const it = c.active && c.cur ? c.list.find((x) => x.cid === c.cur.cid) : null;
  rangeRing.visible = !!it;
  if (it) {
    if (it.kind === 'player') {
      const p = session.combatantPos(it);
      if (p) rangeRing.userData.set(p.x, p.z, Math.max(0, c.cur.budget - (session.turnUsed || 0)) * M2U, dt, t);
    } else rangeRing.userData.set(c.cur.sx, c.cur.sz, c.cur.budget * M2U, dt, t);
    rangeRing.position.y = 4.25;
    renderCur();
  }
}

// ---------------------------------------------------------------- QR e laço
fetch('/api/info').then((r) => r.json()).then((info) => {
  const url = info.urls[0] || location.origin + '/';
  $('qr').src = '/qr.svg?u=' + encodeURIComponent(url);
  $('link').textContent = info.urls.length ? info.urls.join('\n') : url;
});
// ---- áreas de magia lançadas pelos jogadores: aparecem no mapa, com quem está dentro; somem sozinhas
// depois de alguns segundos. O mestre pode FIXAR (fica até apagar) ou APAGAR na hora.
var areaBox = null, areaPan = null, areaTick = 0;
function areaCenter(a) {
  if (a.forma === 'esfera' || a.forma === 'cilindro' || a.forma === 'emanacao' || (a.forma === 'cubo' && a.alcance > 0)) return { x: a.cx, z: a.cz };
  const L = a.tam * M2U / 2; return { x: a.ox + Math.sin(a.dir) * L, z: a.oz + Math.cos(a.dir) * L };
}
function onNewArea(a) {
  try { chime('turn'); } catch {}
  toast(`${a.por} lançou ${a.nome || 'uma área'} — ${fmtArea(a)}`);
  // se a área estiver fora da tela, a câmera desliza até ela
  const c = areaCenter(a), w = Math.max(1, innerWidth - SIDE) / innerHeight;
  if (Math.abs(c.x - view.cx) > view.size * w * 0.8 || Math.abs(c.z - view.cz) > view.size * 0.8) areaPan = c;
}
function renderAreaCards() {
  if (!areaBox) { areaBox = document.createElement('div'); areaBox.className = 'areas-mestre'; areaBox.id = 'areas-mestre'; document.body.appendChild(areaBox); }
  areaBox.textContent = '';
  for (const { data: a, dying } of session.aoes.values()) {
    if (dying) continue;
    const card = document.createElement('div'); card.className = 'area-card'; card.dataset.id = a.id;
    card.style.setProperty('--cor', '#' + (a.cor || 0xb58cff).toString(16).padStart(6, '0'));
    card.innerHTML = '<div class="ac-topo"><b></b><button class="ac-fixar"></button><button class="ac-apagar" title="Apagar">✕</button></div><div class="ac-desc"></div><div class="ac-alvos"></div><div class="ac-barra"><i></i></div>';
    card.querySelector('b').textContent = `${SHAPES[a.forma].icone} ${a.nome || SHAPES[a.forma].nome} · ${a.por}`;
    card.querySelector('.ac-desc').textContent = fmtArea(a);
    const fx = card.querySelector('.ac-fixar'); fx.textContent = a.fixa ? '📌 FIXADA' : '📌 FIXAR'; fx.classList.toggle('on', a.fixa);
    fx.title = a.fixa ? 'Soltar: some sozinha daqui a alguns segundos' : 'Manter no mapa até apagar';
    fx.onclick = () => session.send({ t: 'aoe_fixar', id: a.id, on: !a.fixa });
    card.querySelector('.ac-apagar').onclick = () => session.send({ t: 'aoe_del', id: a.id });
    areaBox.appendChild(card);
  }
  updateAreaCards();
}
function updateAreaCards() {
  if (!areaBox) return;
  for (const card of areaBox.children) {
    const a = session.aoes.get(Number(card.dataset.id)); if (!a) continue;
    const hit = session.aoeHits(a.data), box = card.querySelector('.ac-alvos');
    const sig = hit.map((c) => c.key).join(',');
    if (box.dataset.sig !== sig) {
      box.dataset.sig = sig; box.textContent = '';
      if (!hit.length) box.textContent = 'Ninguém na área';
      for (const c of hit) { const s = document.createElement('span'); s.textContent = c.name; if (c.ally) s.className = 'aliado'; box.appendChild(s); }
    }
    const left = a.data.fixa ? 1 : Math.max(0, (a.data.at + a.data.ttl - Date.now()) / a.data.ttl);
    card.querySelector('.ac-barra i').style.width = (left * 100).toFixed(1) + '%';
  }
}
const clock = new THREE.Timer();
function frame() {
  requestAnimationFrame(frame);
  clock.update(); const dt = Math.min(clock.getDelta(), 0.25);
  session.update(dt, null);
  if (areaPan) {
    const k = Math.min(1, dt * 4); view.cx += (areaPan.x - view.cx) * k; view.cz += (areaPan.z - view.cz) * k; applyCamera();
    if (Math.hypot(areaPan.x - view.cx, areaPan.z - view.cz) < 0.2) areaPan = null;
  }
  if ((areaTick -= dt) <= 0) { areaTick = 0.25; updateAreaCards(); }
  updateTracosCena();
  if (rgA && reguaOn) { drawRegua(true); rgLabel.show(medir(rgA.x, rgA.z, rgB.x, rgB.z), toScreen(rgDraw.b, camera, canvas)); }
  updateCombatMarks(dt, performance.now() / 1000);
  const e = selected && session.ents.get(selected);
  if (e) { ring.position.set(e.data.x, 4.3, e.data.z); ring.scale.setScalar(Math.max(1, e.radius * 1.2)); }
  placeChip(e);
  // com a visão do monstro aberta por cima, esta tela não precisa desenhar (sobra placa de vídeo para a visão)
  if (visao && visao.frame && visao.frame.classList.contains('on')) return;
  if (document.body.classList.contains('mesa-cobre')) return;   // mapa do mundo ou imagem por cima
  renderer.render(scene, camera);
}
frame();
window.__cam = camera; window.__THREE = THREE;

// ---------------------------------------------------------------- visão do monstro
// O mestre entra no monstro: a tela do jogador abre numa moldura por cima desta, no modo "possuir".
// Esta tela continua conectada por baixo; ao voltar, a moldura sai com a transição ao contrário.
var visao = null; // { id, frame } (var: o laço de quadros começa antes deste trecho rodar)
var chip = document.createElement('button');
chip.className = 'visao-chip'; chip.textContent = '👁 VER VISÃO'; chip.hidden = true; chip.title = 'Entrar na visão deste monstro (V)';
document.body.appendChild(chip);
chip.onclick = () => selected && enterView(selected);
$('ver-visao').onclick = () => selected && enterView(selected);
addEventListener('keydown', (e) => { if (e.code === 'KeyV' && !visao && selected && e.target.tagName !== 'INPUT' && session.ents.get(selected)?.data.kind === 'monster') enterView(selected); });
var tmpV = new THREE.Vector3();
function screenOf(x, z, y = 0) {
  tmpV.set(x, y, z).project(camera);
  const r = canvas.getBoundingClientRect();
  return { x: r.left + (tmpV.x + 1) / 2 * r.width, y: r.top + (1 - tmpV.y) / 2 * r.height };
}
function placeChip(e) {
  if (!chip) return;
  const show = !!(e && e.data.kind === 'monster' && !visao && !drag);
  chip.hidden = !show; if (!show) return;
  const s = screenOf(e.data.x, e.data.z - Math.max(1, e.radius) * 1.2, 4.5);
  chip.style.left = s.x + 'px'; chip.style.top = s.y + 'px';
}
function fxLayer(kind, nome, at) {
  const fx = document.createElement('div'); fx.className = 'visao-fx ' + kind;
  fx.innerHTML = '<div class="iris"></div><div class="rot"><span></span><b></b></div>';
  fx.querySelector('span').textContent = kind === 'entra' ? 'VISÃO DE' : 'DE VOLTA AO';
  fx.querySelector('b').textContent = nome;
  if (at) { fx.style.setProperty('--x', at.x + 'px'); fx.style.setProperty('--y', at.y + 'px'); }
  document.body.appendChild(fx);
  return fx;
}
function enterView(id) {
  const e = session.ents.get(id); if (!e || visao) return;
  const nome = nomeDe(e.data), at = screenOf(e.data.x, e.data.z, 1);
  const fx = fxLayer('entra', nome, at);
  try { chime('turn'); } catch {}
  visao = { id, frame: null };
  setTimeout(() => {
    // tela coberta pela íris: abre a visão por baixo do efeito
    const f = document.createElement('iframe'); f.className = 'visao-moldura'; f.src = '/?possuir=' + id; f.allow = 'autoplay';
    visao.frame = f; document.body.appendChild(f);
    f.addEventListener('load', () => setTimeout(() => { f.classList.add('on'); f.focus(); }, 900));
    setTimeout(() => { fx.classList.add('some'); setTimeout(() => fx.remove(), 500); }, 1900);
  }, 700);
}
function exitView() {
  if (!visao) return;
  const e = session.ents.get(visao.id);
  const fx = fxLayer('sai', 'MESTRE', e ? screenOf(e.data.x, e.data.z, 1) : null);
  const f = visao.frame;
  setTimeout(() => { if (f) f.remove(); visao = null; if (e) select(e.data.id); }, 80);
  setTimeout(() => { fx.classList.add('some'); setTimeout(() => fx.remove(), 500); }, 1100);
}
addEventListener('message', (ev) => { if (ev.origin === location.origin && ev.data && ev.data.t === 'sair-visao') exitView(); });

// ataque de oportunidade de um monstro, perguntado ao mestre
function gmOpportunity(m) {
  const box = document.createElement('div'); box.className = 'oa';
  box.innerHTML = '<div class="oa-tit">ATAQUE DE OPORTUNIDADE!</div><div class="oa-corpo"><img alt=""><p></p></div><div class="oa-bts"><button class="oa-sim">ATACAR</button><button class="oa-nao">DEIXAR PASSAR</button></div><i class="oa-tempo"></i>';
  setPortrait(box.querySelector('img'), m.model);
  box.querySelector('p').append(Object.assign(document.createElement('b'), { textContent: m.name }), ` saiu do alcance de ${m.rname}. Usar a reação de ${m.rname} para atacar?`);
  box.querySelector('.oa-sim').onclick = () => { session.send({ t: 'act', slot: 'reaction', id: 'opportunity', target: m.target, as: m.cid }); box.remove(); };
  box.querySelector('.oa-nao').onclick = () => box.remove();
  document.body.appendChild(box);
  try { chime('turn'); } catch {}
  setTimeout(() => box.remove(), 15000);
}
window.__gm = { select, enterView, exitView, visao: () => visao };

// ---- mapas prontos: cenários grandes com relevo (ex.: Covil do Dragão Negro)
async function listarProntos() {
  const box = $('prontos'); if (!box) return;
  try {
    const { prontos } = await (await fetch('/api/prontos')).json();
    box.innerHTML = '';
    for (const m of prontos) {
      const b = document.createElement('button'); b.className = 'bt pronto';
      b.innerHTML = `<b></b><small></small>`; b.querySelector('b').textContent = m.nome;
      b.querySelector('small').textContent = `${m.w} × ${m.h} quadrados (${Math.round(m.w * 1.5)} × ${Math.round(m.h * 1.5)} m)`;
      b.onclick = async () => {
        if (!confirm(`Carregar "${m.nome}"? O mapa atual sai da mesa (salve antes, se quiser guardar).`)) return;
        b.disabled = true; b.querySelector('small').textContent = 'carregando...';
        await fetch('/api/pronto?id=' + encodeURIComponent(m.id), { method: 'POST' });
        b.disabled = false; listarProntos();
      };
      box.appendChild(b);
    }
    if (!prontos.length) box.textContent = 'Nenhum mapa pronto na pasta mapas/prontos.';
  } catch { box.textContent = 'Não consegui listar os mapas prontos.'; }
}
listarProntos();

// ---------------------------------------------------------------- régua do mestre
// Liga no botão (ou R) e arraste com o botão esquerdo; o botão direito continua arrastando o mapa.
var reguaOn = false, rgA = null, rgB = null, rgDraw = new RulerDraw(scene), rgLabel = makeLabel();
function drawRegua(onlyWidth) {
  if (!rgA) return;
  const w = Math.max(0.1, view.size * 0.011);
  if (onlyWidth && rgDraw._w === w && rgDraw._k === `${rgA.x},${rgA.z},${rgB.x},${rgB.z}`) return;
  rgDraw._w = w; rgDraw._k = `${rgA.x},${rgA.z},${rgB.x},${rgB.z}`;
  rgDraw.set(rgA.x, rgA.z, rgB.x, rgB.z, 4.6, w);
}
function setRegua(on) {
  reguaOn = on; $('regua-mestre').classList.toggle('on', on); document.body.classList.toggle('regua-on', on);
  $('regua-mestre').textContent = on ? '📏 RÉGUA LIGADA · Esc sai' : '📏 RÉGUA';
  if (on) { disarm(); select(null); } else { rgA = rgB = null; rgDraw.hide(); rgLabel.hide(); }
}
$('regua-mestre').onclick = () => setRegua(!reguaOn);

// ---------------------------------------------------------------- fichas (só leitura)
function renderFichas() {
  const box = $('fichas-gm'); if (!box) return;
  box.textContent = '';
  const fs = session.fichas || {};
  const ids = Object.keys(HEROI_CLASSE);
  for (const id of ids) {
    const f = fs[id], c = CLASSES[HEROI_CLASSE[id]];
    const card = document.createElement('div'); card.className = 'fg-card'; card.dataset.classe = c.id;
    const nome = id === 'Ghultok' ? "Ghult'ok" : id;
    if (!f) { card.innerHTML = `<b>${nome}</b><div class="fg-m">${c.nome} · ficha ainda não preenchida</div>`; box.appendChild(card); continue; }
    const sub = c.subs[f.sub];
    const l = [`PV ${f.pv}/${f.pvMax}` + (f.pvTemp ? ` (+${f.pvTemp})` : ''), `CA ${f.ca}`, `Iniciativa ${fmtMod(mod(f.atr.des))}`, `Percepção passiva ${10 + mod(f.atr.sab) + (f.pericias.includes('percepcao') ? 2 + Math.floor((f.nivel - 1) / 4) : 0)}`];
    if (c.atr) l.push(`CD ${cdMagia(f)}`);
    const sm = slotsMax(f).map((m, i) => (m ? `${i + 1}º ${m - (f.slotsUsados[i] || 0)}/${m}` : '')).filter(Boolean);
    const um = Object.entries(usosMax(f)).map(([k, m]) => `${USO_NOME[k]} ${m - ((f.usos || {})[k] || 0)}/${m}`);
    let prep = '';
    if (id === 'Guy') {
      const cm = circMax(f);
      const names = [...magiasDominio(f).map((m) => m.nome), ...f.preparadas.map(magiaClerigo).filter((m) => m && m.circ <= cm).map((m) => m.nome)];
      prep = names.length ? 'Preparadas: ' + [...new Set(names)].join(', ') : 'Nenhuma magia preparada';
    }
    card.innerHTML = '<b></b><div class="fg-m"></div><div class="fg-l"></div>' + (sm.length ? '<div class="fg-m fg-s"></div>' : '') + (um.length ? '<div class="fg-m fg-u"></div>' : '') + (prep ? '<div class="fg-m fg-p"></div>' : '');
    card.querySelector('b').textContent = nome;
    card.querySelector('.fg-m').textContent = `${c.nome} nível ${f.nivel}` + (sub && f.nivel >= 3 ? ` · ${sub.nome}` : '');
    const fl = card.querySelector('.fg-l'); for (const t of l) { const s = document.createElement('span'); s.textContent = t; fl.appendChild(s); }
    if (sm.length) card.querySelector('.fg-s').textContent = 'Espaços: ' + sm.join(' · ');
    if (um.length) card.querySelector('.fg-u').textContent = um.join(' · ');
    if (prep) card.querySelector('.fg-p').textContent = prep;
    box.appendChild(card);
  }
}

// ---------------------------------------------------------------- mesa: mapa do mundo, cena 3D ou imagem
var gmVeCena = false;
var mundo = window.__mundoGM = new MundoView($('mesa-mundo'), { role: 'gm', send: (m) => session.send(m), session: () => session, toast, me: () => ({ nome: 'Mestre', hero: '' }) });
var imagemView = new ImagemView($('mesa-imagem'));
function aplicaMesa() {
  const m = session.mesa || { modo: 'cena' };
  document.querySelectorAll('.mesa-modos button').forEach((b) => b.classList.toggle('sel', b.dataset.modo === m.modo));
  const local = gmVeCena && m.modo !== 'cena';
  if (m.modo === 'imagem' && m.imagem && !local) imagemView.show(m.imagem, m.legenda); else imagemView.hide();
  if (m.modo === 'mundo' && !local) mundo.show(); else mundo.hide();
  document.body.classList.toggle('mesa-cobre', m.modo !== 'cena' && !local);
  $('gm-ver').hidden = m.modo === 'cena';
  $('gm-ver').textContent = local ? 'Voltar a ver o que os jogadores veem' : 'Ver a cena 3D só na minha tela';
  $('mesa-dica').textContent = { mundo: 'Os jogadores estão vendo o mapa de Faerûn.', cena: 'Os jogadores estão na cena 3D (eles ainda podem abrir o mapa do mundo pelo botão 🗺 MAPA).', imagem: 'Os jogadores estão vendo a imagem marcada abaixo.' }[m.modo];
  renderImagens();
}
document.querySelectorAll('.mesa-modos button').forEach((b) => {
  b.onclick = () => {
    const m = b.dataset.modo;
    if (m === 'imagem' && !(session.mesa && session.mesa.imagem)) { const first = (session.imagens || [])[0]; if (!first) { toast('Envie uma imagem primeiro.', 'neg'); return; } session.send({ t: 'mesa', modo: 'imagem', imagem: first.url, legenda: $('img-legenda').value }); return; }
    gmVeCena = false; session.send({ t: 'mesa', modo: m });
  };
});
$('gm-ver').onclick = () => { gmVeCena = !gmVeCena; aplicaMesa(); };
$('rotas-limpar').onclick = () => { if (confirm('Apagar todas as rotas do mapa do mundo?')) session.send({ t: 'rotas_limpar' }); };
function renderImagens() {
  const box = $('imgs-gm'); if (!box) return; box.textContent = '';
  const m = session.mesa || {};
  for (const im of session.imagens || []) {
    const d = document.createElement('div'); d.className = 'img-gm' + (m.modo === 'imagem' && m.imagem === im.url ? ' sel' : '');
    const img = document.createElement('img'); img.src = im.url; img.alt = ''; img.loading = 'lazy';
    const sp = document.createElement('span'); sp.textContent = im.nome;
    const del = document.createElement('button'); del.textContent = '✕'; del.title = 'Apagar imagem';
    del.onclick = (e) => { e.stopPropagation(); if (confirm('Apagar esta imagem?')) fetch('/api/imagens?f=' + encodeURIComponent(im.url.split('/').pop()), { method: 'DELETE' }); };
    d.onclick = () => { gmVeCena = false; session.send({ t: 'mesa', modo: 'imagem', imagem: im.url, legenda: $('img-legenda').value }); };
    d.append(img, sp, del); box.appendChild(d);
  }
}
async function enviarImagens(files) {
  for (const f of files) {
    if (!/^image\/(png|jpeg|webp|gif)$/.test(f.type)) { toast(`${f.name}: só PNG, JPG, WEBP ou GIF.`, 'neg'); continue; }
    const r = await fetch('/api/imagens?nome=' + encodeURIComponent(f.name), { method: 'POST', headers: { 'Content-Type': f.type }, body: f });
    const j = await r.json().catch(() => ({}));
    if (!r.ok) toast(j.error || 'Não consegui enviar a imagem.', 'neg'); else toast(`Imagem enviada: ${f.name}`);
  }
}
$('img-enviar').onclick = () => $('img-arquivo').click();
$('img-arquivo').onchange = () => { enviarImagens([...$('img-arquivo').files]); $('img-arquivo').value = ''; };
const solta = $('solta-img');
for (const ev of ['dragenter', 'dragover']) solta.addEventListener(ev, (e) => { e.preventDefault(); solta.classList.add('on'); });
for (const ev of ['dragleave', 'drop']) solta.addEventListener(ev, (e) => { e.preventDefault(); solta.classList.remove('on'); });
solta.addEventListener('drop', (e) => enviarImagens([...e.dataTransfer.files]));
aplicaMesa();

// réguas dos jogadores na cena 3D (ao vivo)
var tracosCena = new Map();
function tracoCena(m) {
  let t = tracosCena.get(m.id);
  if (!m.pts || m.pts.length < 2) { if (t) { t.draw.dispose(); t.label.el.remove(); tracosCena.delete(m.id); } return; }
  if (!t) { t = { draw: new RulerDraw(scene), label: makeLabel() }; tracosCena.set(m.id, t); }
  t.draw.matDash.color.set(corDe(m.hero, false)); t.label.el.style.borderColor = corDe(m.hero, false);
  t.a = { x: m.pts[0][0], z: m.pts[0][1] }; t.b = { x: m.pts[1][0], z: m.pts[1][1] }; t.por = m.por;
  t.draw.set(t.a.x, t.a.z, t.b.x, t.b.z, 4.55, Math.max(0.1, view.size * 0.009));
}
function updateTracosCena() {
  if (!tracosCena) return;
  for (const t of tracosCena.values()) {
    if (document.body.classList.contains('mesa-cobre')) { t.label.hide(); continue; }
    const med = medir(t.a.x, t.a.z, t.b.x, t.b.z);
    t.label.show({ ...med, txt: `${t.por}: ${med.txt}` }, toScreen(t.draw.b, camera, canvas));
  }
}
