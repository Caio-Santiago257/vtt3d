// VTT 3D em primeira pessoa — servidor local do protótipo.
// Uso: node server.js   (porta padrão 3000; mude com a variável PORT)
'use strict';
const http = require('http');
const fs = require('fs');
const path = require('path');
const os = require('os');
const { WebSocketServer } = require('ws');
const QRCode = require('qrcode');

const PORT = Number(process.env.PORT) || 3000;
const PUBLIC = path.join(__dirname, 'public');
const DATA = path.join(__dirname, 'data');
const G = 2; // unidades de mundo por quadrado do grid
fs.mkdirSync(DATA, { recursive: true });

// ---------------------------------------------------------------- estado
let map = null;      // mapa normalizado (sem a imagem)
let ents = [];       // monstros e objetos colocados pelo mestre
let doors = [];      // true = fechada
let frozen = false;
let nextId = 1;
const players = new Map(); // ws -> jogador

const MAP_FILE = path.join(DATA, 'map.json');
const SCENE_FILE = path.join(DATA, 'scene.json');

function imageFile() {
  for (const ext of ['png', 'jpg', 'webp']) {
    const f = path.join(DATA, 'map-image.' + ext);
    if (fs.existsSync(f)) return f;
  }
  return null;
}

function saveScene() {
  try {
    fs.writeFileSync(MAP_FILE, JSON.stringify(map));
    fs.writeFileSync(SCENE_FILE, JSON.stringify({ ents, doors, nextId }));
  } catch (e) { console.error('Não consegui salvar a cena:', e.message); }
}
let saveTimer = null;
function saveSoon() { clearTimeout(saveTimer); saveTimer = setTimeout(saveScene, 800); }

// Centro de quadrado livre de paredes mais próximo do meio do mapa (em unidades de mundo).
function freeSpot(walls, w, h) {
  const dist = (px, py, s) => {
    const vx = s[2] - s[0], vy = s[3] - s[1];
    const t = Math.max(0, Math.min(1, ((px - s[0]) * vx + (py - s[1]) * vy) / (vx * vx + vy * vy || 1)));
    return Math.hypot(px - (s[0] + vx * t), py - (s[1] + vy * t));
  };
  let best = { x: w / 2, y: h / 2 }, bestScore = Infinity;
  for (let i = 0; i < Math.ceil(w); i++) for (let j = 0; j < Math.ceil(h); j++) {
    const x = i + 0.5, y = j + 0.5;
    if (walls.some((s) => dist(x, y, s) < 0.9)) continue; // 0.9 quadrado de folga
    const score = Math.hypot(x - w / 2, y - h / 2);
    if (score < bestScore) { bestScore = score; best = { x, y }; }
  }
  return { x: best.x * G, z: best.y * G };
}

// Converte um arquivo Universal VTT (.dd2vtt / .uvtt / .df2vtt) no formato interno.
function normalizeUVTT(j, name) {
  const res = j.resolution || {};
  const o = res.map_origin || { x: 0, y: 0 };
  const size = res.map_size || { x: 20, y: 20 };
  const num = (v) => (Number.isFinite(Number(v)) ? Number(v) : 0);
  const walls = [];
  const addPoly = (poly) => {
    if (!Array.isArray(poly)) return;
    for (let i = 0; i + 1 < poly.length; i++) {
      const a = poly[i], b = poly[i + 1];
      const w = [num(a.x) - o.x, num(a.y) - o.y, num(b.x) - o.x, num(b.y) - o.y];
      if (Math.hypot(w[2] - w[0], w[3] - w[1]) > 0.02) walls.push(w);
    }
  };
  (j.line_of_sight || []).forEach(addPoly);
  const doorList = [];
  for (const p of j.portals || []) {
    const b = p.bounds || [];
    if (b.length < 2) continue;
    doorList.push({
      x1: num(b[0].x) - o.x, y1: num(b[0].y) - o.y,
      x2: num(b[1].x) - o.x, y2: num(b[1].y) - o.y,
      closed: p.closed !== false,
    });
  }
  const lights = [];
  for (const l of j.lights || []) {
    if (!l.position) continue;
    let c = String(l.color || 'ffffcc88').replace('#', '');
    if (c.length === 8) c = c.slice(2); // AARRGGBB -> RRGGBB
    if (!/^[0-9a-fA-F]{6}$/.test(c)) c = 'ffcc88';
    lights.push({
      x: num(l.position.x) - o.x, y: num(l.position.y) - o.y,
      range: num(l.range) || 4, intensity: num(l.intensity) || 1, color: '#' + c,
    });
  }
  let image = null;
  if (typeof j.image === 'string' && j.image.length > 100) {
    image = Buffer.from(j.image.replace(/^data:[^,]*,/, ''), 'base64');
  }
  const w = Math.max(1, num(size.x)), h = Math.max(1, num(size.y));
  return {
    map: {
      version: Date.now(), name: name || 'mapa', w, h, walls, doors: doorList, lights,
      hasImage: !!image, floorMode: 'tiles',
      terrain: { biome: 'masmorra', cells: 'p'.repeat(Math.ceil(w) * Math.ceil(h)) },
      spawn: freeSpot(walls, w, h),
    },
    image,
  };
}

function setMap(norm) {
  for (const ext of ['png', 'jpg', 'webp']) fs.rmSync(path.join(DATA, 'map-image.' + ext), { force: true });
  if (norm.image) {
    const b = norm.image;
    const ext = b[0] === 0x89 ? 'png' : b[0] === 0xff ? 'jpg' : 'webp';
    fs.writeFileSync(path.join(DATA, 'map-image.' + ext), b);
  }
  map = norm.map;
  doors = map.doors.map((d) => d.closed);
}

function loadSample() {
  const j = JSON.parse(fs.readFileSync(path.join(__dirname, 'mapas', 'masmorra-exemplo.dd2vtt'), 'utf8'));
  setMap(normalizeUVTT(j, 'Masmorra de exemplo'));
  map.spawn = { x: 5 * G, z: 5 * G };
  const sample = JSON.parse(fs.readFileSync(path.join(__dirname, 'mapas', 'masmorra-exemplo.cena.json'), 'utf8'));
  nextId = 1;
  ents = sample.map((e) => ({ id: nextId++, scale: 1, ry: 0, ...e }));
}

// ---------------------------------------------------------------- mapas salvos
const SAVES = path.join(__dirname, 'mapas-salvos');
fs.mkdirSync(SAVES, { recursive: true });
const saveName = (n) => String(n || '').replace(/[^\p{L}\p{N} _-]/gu, '').trim().slice(0, 60);
const saveFile = (n) => path.join(SAVES, saveName(n) + '.json');
function listSaves() {
  return fs.readdirSync(SAVES).filter((f) => f.endsWith('.json'))
    .map((f) => ({ name: f.slice(0, -5), when: fs.statSync(path.join(SAVES, f)).mtimeMs }))
    .sort((a, b) => b.when - a.when);
}
function writeSave(name) {
  const img = imageFile();
  const data = { formato: 'vtt3d-mapa', versao: 1, map: { ...map, name }, ents, doors, nextId,
    image: img ? { ext: path.extname(img).slice(1), base64: fs.readFileSync(img).toString('base64') } : null };
  fs.writeFileSync(saveFile(name), JSON.stringify(data));
  map.name = name;
}
function readSave(name) {
  const d = JSON.parse(fs.readFileSync(saveFile(name), 'utf8'));
  if (!d.map || !Array.isArray(d.map.walls)) throw new Error('arquivo de mapa inválido');
  for (const ext of ['png', 'jpg', 'webp']) fs.rmSync(path.join(DATA, 'map-image.' + ext), { force: true });
  if (d.image && d.image.base64) fs.writeFileSync(path.join(DATA, 'map-image.' + (d.image.ext || 'png')), Buffer.from(d.image.base64, 'base64'));
  map = d.map; map.version = Date.now();
  ents = d.ents || []; doors = d.doors || map.doors.map((x) => x.closed); nextId = d.nextId || ents.reduce((m, e) => Math.max(m, e.id), 0) + 1;
}
function blankMap(w, h, name) {
  for (const ext of ['png', 'jpg', 'webp']) fs.rmSync(path.join(DATA, 'map-image.' + ext), { force: true });
  map = { version: Date.now(), name: name || 'Mapa novo', w, h, walls: [], doors: [], lights: [], hasImage: false, floorMode: 'tiles',
    terrain: { biome: 'masmorra', cells: 'p'.repeat(w * h) }, spawn: { x: w * G / 2, z: h * G / 2 } };
  ents = []; doors = []; nextId = 1;
}
function listProntos() {
  const dir = path.join(__dirname, 'mapas', 'prontos');
  if (!fs.existsSync(dir)) return [];
  return fs.readdirSync(dir).filter((f) => f.endsWith('.json')).map((f) => {
    try { const d = JSON.parse(fs.readFileSync(path.join(dir, f), 'utf8')); return { id: f.slice(0, -5), nome: d.map.name, w: d.map.w, h: d.map.h }; } catch { return null; }
  }).filter(Boolean);
}
function loadPronto(file) {
  const d = JSON.parse(fs.readFileSync(file, 'utf8'));
  for (const ext of ['png', 'jpg', 'webp']) fs.rmSync(path.join(DATA, 'map-image.' + ext), { force: true });
  map = { ...d.map, version: Date.now() };
  nextId = 1; ents = (d.ents || []).map((e) => ({ id: nextId++, scale: 1, ry: 0, ...e }));
  doors = map.doors.map((x) => !!x.closed);
}
function mapChanged() { saveScene(); relocatePlayers(); broadcast({ t: 'map', version: map.version, ents, doors }); }

function boot() {
  try {
    if (fs.existsSync(MAP_FILE) && fs.existsSync(SCENE_FILE)) {
      map = JSON.parse(fs.readFileSync(MAP_FILE, 'utf8'));
      const s = JSON.parse(fs.readFileSync(SCENE_FILE, 'utf8'));
      if (!map.terrain) map.terrain = { biome: 'masmorra', cells: 'p'.repeat(Math.ceil(map.w) * Math.ceil(map.h)) };
      ents = s.ents || []; doors = s.doors || map.doors.map((d) => d.closed); nextId = s.nextId || 1;
      return;
    }
  } catch (e) { console.error('Cena salva ilegível, carregando o exemplo:', e.message); }
  loadSample();
  saveScene();
}
boot();

// ---------------------------------------------------------------- rede local
function lanAddresses() {
  const out = [];
  for (const list of Object.values(os.networkInterfaces())) {
    for (const i of list || []) if (i.family === 'IPv4' && !i.internal) out.push(i.address);
  }
  // redes domésticas primeiro
  out.sort((a, b) => Number(b.startsWith('192.168.')) - Number(a.startsWith('192.168.')));
  return out;
}
const playerUrl = (ip) => `http://${ip}:${PORT}/`;

// ---------------------------------------------------------------- mesa: o que os jogadores veem
// modo 'mundo' (mapa de Faerûn), 'cena' (mapa 3D de batalha) ou 'imagem' (teatro da mente: uma imagem que o mestre mostra).
// Rotas de viagem desenhadas no mapa do mundo ficam salvas junto, em data/mesa.json. Imagens enviadas ficam em data/imagens/.
const IMG_DIR = path.join(DATA, 'imagens');
fs.mkdirSync(IMG_DIR, { recursive: true });
const MESA_FILE = path.join(DATA, 'mesa.json');
let mesa = { modo: 'mundo', imagem: null, legenda: '' };
let rotas = [], nextRota = 1;
try {
  const j = JSON.parse(fs.readFileSync(MESA_FILE, 'utf8'));
  if (['mundo', 'cena', 'imagem'].includes(j.modo)) mesa.modo = j.modo;
  if (j.imagem && fs.existsSync(path.join(IMG_DIR, path.basename(j.imagem)))) { mesa.imagem = j.imagem; mesa.legenda = String(j.legenda || ''); }
  else if (mesa.modo === 'imagem') mesa.modo = 'mundo';
  rotas = Array.isArray(j.rotas) ? j.rotas : [];
  nextRota = rotas.reduce((m, r) => Math.max(m, r.id + 1), 1);
} catch {}
function saveMesa() {
  try { fs.writeFileSync(MESA_FILE, JSON.stringify({ ...mesa, rotas })); } catch (e) { console.error('Não consegui salvar a mesa:', e.message); }
}
const IMG_EXT = { 'image/png': '.png', 'image/jpeg': '.jpg', 'image/webp': '.webp', 'image/gif': '.gif' };
function listImagens() {
  return fs.readdirSync(IMG_DIR).filter((f) => /\.(png|jpe?g|webp|gif)$/i.test(f))
    .map((f) => ({ f, t: fs.statSync(path.join(IMG_DIR, f)).mtimeMs }))
    .sort((a, b) => b.t - a.t).map(({ f }) => ({ url: '/imagens/' + f, nome: f.replace(/^[a-z0-9]+-/, '').replace(/\.[a-z]+$/i, '').replace(/_/g, ' ') }));
}
const ptList = (v, n) => (Array.isArray(v) ? v.slice(0, n).map((q) => [num(q && q[0], -1e5, 1e5), num(q && q[1], -1e5, 1e5)]) : []);

// ---------------------------------------------------------------- HTTP
const TYPES = {
  '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.css': 'text/css; charset=utf-8',
  '.json': 'application/json', '.webmanifest': 'application/manifest+json', '.glb': 'model/gltf-binary', '.png': 'image/png', '.jpg': 'image/jpeg',
  '.webp': 'image/webp', '.svg': 'image/svg+xml', '.txt': 'text/plain; charset=utf-8', '.gif': 'image/gif', '.jpeg': 'image/jpeg',
};

// Assets ficam guardados no navegador, mas ele confere a cada carga se o arquivo mudou (resposta 304 se não mudou).
// Antes era max-age de 1 dia, e um modelo atualizado com o mesmo nome só aparecia no dia seguinte.
function sendFile(res, file, cache, req) {
  fs.stat(file, (err, st) => {
    if (err || !st.isFile()) { res.writeHead(404); res.end('Não encontrado'); return; }
    const etag = `"${st.size.toString(36)}-${Math.floor(st.mtimeMs).toString(36)}"`;
    if (cache && req && req.headers['if-none-match'] === etag) { res.writeHead(304, { ETag: etag }); res.end(); return; }
    res.writeHead(200, {
      'Content-Type': TYPES[path.extname(file).toLowerCase()] || 'application/octet-stream',
      'Content-Length': st.size,
      'Cache-Control': 'no-cache',
      ...(cache ? { ETag: etag } : {}),
    });
    fs.createReadStream(file).pipe(res);
  });
}
function sendJSON(res, obj, code = 200) {
  const s = JSON.stringify(obj);
  res.writeHead(code, { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' });
  res.end(s);
}

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url, 'http://x');
  const p = decodeURIComponent(url.pathname);
  try {
    if (p === '/api/map' && req.method === 'GET') return sendJSON(res, map);
    if (p === '/api/map-image') {
      const f = imageFile();
      if (!f) { res.writeHead(404); return res.end(); }
      return sendFile(res, f, false);
    }
    if (p === '/api/info') {
      const ips = lanAddresses();
      return sendJSON(res, { urls: ips.map(playerUrl), port: PORT });
    }
    if (p === '/qr.svg') {
      const ips = lanAddresses();
      const target = url.searchParams.get('u') || (ips[0] ? playerUrl(ips[0]) : `http://localhost:${PORT}/`);
      const svg = await QRCode.toString(target, { type: 'svg', margin: 1 });
      res.writeHead(200, { 'Content-Type': 'image/svg+xml', 'Cache-Control': 'no-store' });
      return res.end(svg);
    }
    if (p === '/api/map' && req.method === 'POST') {
      const chunks = []; let total = 0;
      for await (const c of req) {
        total += c.length;
        if (total > 400 * 1024 * 1024) return sendJSON(res, { error: 'Arquivo grande demais (limite de 400 MB).' }, 413);
        chunks.push(c);
      }
      let j;
      try { j = JSON.parse(Buffer.concat(chunks).toString('utf8')); }
      catch { return sendJSON(res, { error: 'O arquivo não é um Universal VTT válido (esperava JSON).' }, 400); }
      if (!j.resolution || !Array.isArray(j.line_of_sight)) {
        return sendJSON(res, { error: 'Não encontrei os dados de grid e paredes. Exporte como Universal VTT (.dd2vtt).' }, 400);
      }
      const norm = normalizeUVTT(j, url.searchParams.get('name') || 'mapa importado');
      setMap(norm);
      ents = []; nextId = 1;
      saveScene();
      relocatePlayers();
      broadcast({ t: 'map', version: map.version, ents, doors });
      return sendJSON(res, { ok: true, walls: map.walls.length, doors: map.doors.length, lights: map.lights.length, hasImage: map.hasImage });
    }
    if (p === '/api/saves' && req.method === 'GET') return sendJSON(res, { saves: listSaves(), current: map.name });
    if (p === '/api/saves' && req.method === 'POST') {
      const name = saveName(url.searchParams.get('name'));
      if (!name) return sendJSON(res, { error: 'Dê um nome ao mapa.' }, 400);
      writeSave(name); saveScene();
      return sendJSON(res, { ok: true, name });
    }
    if (p === '/api/saves/load' && req.method === 'POST') {
      const name = saveName(url.searchParams.get('name'));
      if (!name || !fs.existsSync(saveFile(name))) return sendJSON(res, { error: 'Mapa salvo não encontrado.' }, 404);
      readSave(name); mapChanged();
      return sendJSON(res, { ok: true, name });
    }
    if (p === '/api/saves' && req.method === 'DELETE') {
      const name = saveName(url.searchParams.get('name'));
      if (name) fs.rmSync(saveFile(name), { force: true });
      return sendJSON(res, { ok: true });
    }
    if (p === '/api/blank' && req.method === 'POST') {
      const w = Math.max(4, Math.min(80, parseInt(url.searchParams.get('w'), 10) || 30));
      const h = Math.max(4, Math.min(80, parseInt(url.searchParams.get('h'), 10) || 20));
      blankMap(w, h, saveName(url.searchParams.get('name')));
      mapChanged();
      return sendJSON(res, { ok: true });
    }
    // mapas prontos (mapas/prontos/*.json): cenário com relevo, já com monstros posicionados
    if (p === '/api/prontos' && req.method === 'GET') return sendJSON(res, { prontos: listProntos() });
    if (p === '/api/pronto' && req.method === 'POST') {
      const id = String(url.searchParams.get('id') || '').replace(/[^a-z0-9-]/g, '');
      const file = path.join(__dirname, 'mapas', 'prontos', id + '.json');
      if (!id || !fs.existsSync(file)) return sendJSON(res, { error: 'Mapa pronto não encontrado.' }, 404);
      loadPronto(file); mapChanged();
      return sendJSON(res, { ok: true, name: map.name });
    }
    if (p === '/api/sample' && req.method === 'POST') {
      loadSample(); saveScene(); relocatePlayers();
      broadcast({ t: 'map', version: map.version, ents, doors });
      return sendJSON(res, { ok: true });
    }
    // imagens do teatro da mente
    if (p === '/api/imagens' && req.method === 'GET') return sendJSON(res, { imagens: listImagens() });
    if (p === '/api/imagens' && req.method === 'POST') {
      const ext = IMG_EXT[String(req.headers['content-type'] || '').split(';')[0].trim()];
      if (!ext) return sendJSON(res, { error: 'Envie uma imagem PNG, JPG, WEBP ou GIF.' }, 400);
      const chunks = []; let total = 0;
      for await (const c of req) {
        total += c.length;
        if (total > 40 * 1024 * 1024) return sendJSON(res, { error: 'Imagem grande demais (limite de 40 MB).' }, 413);
        chunks.push(c);
      }
      const nome = String(url.searchParams.get('nome') || 'imagem').normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/\.[a-z0-9]+$/i, '').replace(/[^A-Za-z0-9 _-]/g, '').trim().replace(/ +/g, '_').slice(0, 50) || 'imagem';
      const f = Date.now().toString(36) + '-' + nome + ext;
      fs.writeFileSync(path.join(IMG_DIR, f), Buffer.concat(chunks));
      broadcastGM({ t: 'imagens', list: listImagens() });
      return sendJSON(res, { ok: true, url: '/imagens/' + f });
    }
    if (p === '/api/imagens' && req.method === 'DELETE') {
      const f = path.basename(String(url.searchParams.get('f') || ''));
      if (f) fs.rmSync(path.join(IMG_DIR, f), { force: true });
      if (mesa.imagem === '/imagens/' + f) { mesa = { modo: 'mundo', imagem: null, legenda: '' }; saveMesa(); broadcast({ t: 'mesa', ...mesa }); }
      broadcastGM({ t: 'imagens', list: listImagens() });
      return sendJSON(res, { ok: true });
    }
    if (p.startsWith('/imagens/')) return sendFile(res, path.join(IMG_DIR, path.basename(p)), true, req);
    // arquivos estáticos
    let rel = p === '/' ? '/jogador.html' : p === '/mestre' ? '/mestre.html' : p === '/galeria' ? '/galeria.html' : p;
    const file = path.normalize(path.join(PUBLIC, rel));
    if (!file.startsWith(PUBLIC + path.sep)) { res.writeHead(403); return res.end(); }
    return sendFile(res, file, rel.startsWith('/assets/') || rel.startsWith('/vendor/'), req);
  } catch (e) {
    console.error(e);
    if (!res.headersSent) sendJSON(res, { error: 'Erro interno: ' + e.message }, 500);
  }
});

// ---------------------------------------------------------------- WebSocket
const wss = new WebSocketServer({ server });
function send(ws, msg) { if (ws.readyState === 1) ws.send(JSON.stringify(msg)); }
function broadcast(msg, except) {
  const s = JSON.stringify(msg);
  for (const c of wss.clients) if (c !== except && c.readyState === 1) c.send(s);
}
function broadcastGM(msg) {
  const s = JSON.stringify(msg);
  for (const c of wss.clients) if (c.role === 'gm' && c.readyState === 1) c.send(s);
}
const clamp = (v, a, b) => Math.min(b, Math.max(a, Number(v) || 0));

// ---- jogadores com identidade fixa: o celular que bloqueia a tela volta como o mesmo personagem
const known = new Map(); // token -> registro do jogador
const online = (rec) => [...players.values()].includes(rec);
// ---- áreas de magia: o jogador posiciona e confirma; todos veem; somem sozinhas depois de AOE_MS (o mestre pode fixar ou apagar)
const AOE_FORMAS = new Set(['esfera', 'cilindro', 'cubo', 'cone', 'linha', 'emanacao']);
const AOE_MS = Number(process.env.AOE_MS) || 15000;
let aoes = [], nextAoe = 1;
const num = (v, lo, hi, d = 0) => { const n = Number(v); return Number.isFinite(n) ? Math.max(lo, Math.min(hi, n)) : d; };

// ---------------------------------------------------------------- fichas dos personagens
// Uma ficha por herói (Guy, Kaira, Ghult'ok), salva em fichas/<herói>.json na pasta do projeto.
// Quem joga com o herói edita; todos recebem as fichas (o mestre vê na aba Fichas).
const FICHAS_DIR = path.join(__dirname, 'fichas');
fs.mkdirSync(FICHAS_DIR, { recursive: true });
const FICHA_HEROIS = new Set(['Guy', 'Kaira', 'Ghultok']);
const fichas = {};
for (const h of FICHA_HEROIS) {
  try { fichas[h] = JSON.parse(fs.readFileSync(path.join(FICHAS_DIR, h + '.json'), 'utf8')); } catch {}
}
const strList = (v, n, len = 40) => (Array.isArray(v) ? v.slice(0, n).map((x) => String(x).slice(0, len)) : []);
function normFicha(hero, f) {
  f = f && typeof f === 'object' ? f : {};
  const atr = {};
  for (const k of ['for', 'des', 'con', 'int', 'sab', 'car']) atr[k] = Math.round(num(f.atr && f.atr[k], 1, 30, 10));
  const usos = {};
  for (const k of ['canalizar', 'furias', 'pontos', 'inata', 'intervencao']) usos[k] = Math.round(num(f.usos && f.usos[k], 0, 99, 0));
  return {
    hero, nivel: Math.round(num(f.nivel, 1, 20, 1)), atr,
    sub: String(f.sub || '').slice(0, 20), ordem: f.ordem === 'taumaturgo' ? 'taumaturgo' : 'protetor',
    pericias: strList(f.pericias, 18, 20), salvExtra: strList(f.salvExtra, 6, 4),
    pvMax: Math.round(num(f.pvMax, 0, 999, 0)), pv: Math.round(num(f.pv, -999, 999, 0)), pvTemp: Math.round(num(f.pvTemp, 0, 999, 0)),
    ca: Math.round(num(f.ca, 0, 40, 10)), deslocamento: num(f.deslocamento, 0, 60, 9),
    truques: strList(f.truques, 12), preparadas: strList(f.preparadas, 40),
    slotsUsados: Array.from({ length: 9 }, (_, i) => Math.round(num(f.slotsUsados && f.slotsUsados[i], 0, 9, 0))),
    usos, notas: String(f.notas || '').slice(0, 4000), salvoEm: Date.now(),
  };
}
let fichaTimer = {};
function saveFicha(hero) {
  clearTimeout(fichaTimer[hero]);
  fichaTimer[hero] = setTimeout(() => {
    const file = path.join(FICHAS_DIR, hero + '.json'), tmp = file + '.tmp';
    try { fs.writeFileSync(tmp, JSON.stringify(fichas[hero], null, 2)); fs.renameSync(tmp, file); }
    catch (e) { console.error('Não consegui salvar a ficha de ' + hero + ':', e.message); }
  }, 300);
}
const sendAoes = () => broadcast({ t: 'aoes', list: aoes });
setInterval(() => {
  const now = Date.now(), n = aoes.length;
  aoes = aoes.filter((a) => a.fixa || now < a.at + a.ttl);
  if (aoes.length !== n) sendAoes();
}, 500);
const playerList = () => [...known.values()].map((p) => ({ ...p, off: !online(p) }));
const playerById = (id) => [...known.values()].find((p) => p.id === id);
const socketsOf = (rec) => [...players].filter(([, p]) => p === rec).map(([c]) => c);

// mapa novo: todo mundo volta ao ponto de entrada
function relocatePlayers() {
  for (const pl of known.values()) {
    pl.x = map.spawn.x + (Math.random() - 0.5) * 1.5; pl.z = map.spawn.z + (Math.random() - 0.5) * 1.5;
    for (const c of socketsOf(pl)) send(c, { t: 'teleport', x: pl.x, z: pl.z });
  }
}

// ---------------------------------------------------------------- combate (D&D 2024)
// 1 quadrado = 1,5 m = 2 unidades de mundo, então 1 m = 4/3 de unidade.
const M2U = G / 1.5;
const DIFFICULT = new Set(['a', 'l', 'b', 'm']); // água, lama, brejo e mata custam o dobro
const ACTIONS = {
  action: ['attack', 'magic', 'dash', 'disengage', 'dodge', 'help', 'hide', 'influence', 'ready', 'search', 'study', 'utilize'],
  bonus: ['offhand', 'spell', 'potion', 'dash', 'disengage', 'hide', 'class', 'revelacao', 'other'],
  reaction: ['opportunity', 'spell', 'readied', 'other'],
};
// estados que ficam marcados no retrato até o começo do próximo turno de quem os usou
const FLAGS = { dodge: 'Esquivando', disengage: 'Desengajado', hide: 'Escondido', ready: 'Preparado' };

let combat = { active: false, round: 0, turn: 0, n: 0, list: [], cur: null, log: [], oa: {} };

// Tamanho de cada criatura em quadrados (Média = 1, Enorme = 3), lido do catálogo de assets.
const SIZES = {}, SPEEDS = {}, FLY = {};   // deslocamento em metros (D&D: dragão negro adulto anda 12 m)
try {
  for (const a of JSON.parse(fs.readFileSync(path.join(PUBLIC, 'assets', 'manifest.json'), 'utf8'))) {
    if (a.tamanho) SIZES[a.id] = Number(a.tamanho) || 1;
    if (a.deslocamento) SPEEDS[a.id] = Number(a.deslocamento) || 9;
    if (a.voo) FLY[a.id] = Number(a.voo) || 0;
  }
} catch (e) { console.error('Não li os tamanhos do manifest:', e.message); }
function sizeOf(it) {
  if (it.kind === 'player') return 1;
  const e = ents.find((x) => x.id === it.ref);
  return (e && SIZES[e.model]) || 1;
}
// Distância de combate em metros, contada em quadrados como no tabuleiro (diagonal vale 1),
// de borda a borda: dois personagens Médios lado a lado estão a 1,5 m; um Enorme ocupa 3 x 3.
function reachDist(a, b) {
  const pa = posOf(a), pb = posOf(b); if (!pa || !pb) return Infinity;
  const sa = sizeOf(a), sb = sizeOf(b);
  const gapH = Math.max(Math.abs(pa.x - pb.x), Math.abs(pa.z - pb.z)) - (sa + sb) * G / 2;
  // na vertical cada criatura é tão alta quanto larga: quem voa por cima também conta a altura
  const gapV = pa.y > pb.y ? pa.y - (pb.y + sb * G) : pb.y - (pa.y + sa * G);
  return Math.max(1.5, (Math.max(gapH, gapV) + G) / M2U);
}
const REACH = 1.5, REACH_TOL = 0.45;           // folga: no mapa livre ninguém fica exatamente no centro do quadrado
const inReach = (a, b) => reachDist(a, b) <= REACH + REACH_TOL;
const hostile = (a, b) => (a.kind === 'player') !== (b.kind === 'player');
const MELEE = { action: ['attack'], bonus: ['offhand'], reaction: ['opportunity'] };
const fmtM = (m) => (Math.round(m * 10) / 10).toLocaleString('pt-BR') + ' m';
let nextCid = 1;

function terrainCost(x, z) {
  const t = map.terrain; if (!t) return 1;
  const W = Math.ceil(map.w), i = Math.floor(x / G), j = Math.floor(z / G);
  if (i < 0 || j < 0 || i >= W || j >= Math.ceil(map.h)) return 1;
  return DIFFICULT.has(t.cells[j * W + i]) ? 2 : 1;
}
function posOf(it) {
  if (it.kind === 'player') { const p = playerById(it.ref); return p ? { x: p.x, z: p.z, y: p.y || 0 } : null; }
  const e = ents.find((x) => x.id === it.ref); return e ? { x: e.x, z: e.z, y: e.y || 0 } : null;
}

// ---- voo
// Deslocamento de voo em metros (0 = não voa). Monstro: o do catálogo, ou o que o mestre puser no combate.
// Jogador: o mestre libera na tela dele (vale dentro e fora do combate).
const MAX_ALT = 30 * M2U;          // teto de voo: 30 m
// ---- Revelação Celestial (aasimar; aqui, só a Kaira): ação bônus; por 1 minuto (10 rodadas) ganha asas
// e deslocamento de voo igual ao deslocamento. Fora de combate, ela liga e desliga pelo botão e dura 60 s.
const REV_HEROES = new Set(['Kaira']);
const REV_ROUNDS = 10, REV_MS = Number(process.env.REV_MS) || 60000;   // REV_MS: só para testes lentos
function playerFly(p) {
  if (!p) return 0;
  const it = combat.list.find((x) => x.kind === 'player' && x.ref === p.id);
  return Math.max(p.fly || 0, p.rev ? (it ? it.speed : 9) : 0);
}
function setRevelacao(p, on, inCombat) {
  if (!p) return;
  if (on) { p.rev = true; p.revAte = inCombat ? combat.round + REV_ROUNDS : 0; p.revFim = inCombat ? 0 : Date.now() + REV_MS; }
  else {
    p.rev = false; p.revAte = 0; p.revFim = 0;
    if (!playerFly(p) && p.y) { p.y = 0; for (const s of socketsOf(p)) send(s, { t: 'teleport', x: p.x, z: p.z, y: 0 }); }
  }
  sendCombat();
}
setInterval(() => {   // fim da revelação: 10 rodadas depois, ou 60 s fora de combate
  for (const p of known.values()) {
    if (!p.rev) continue;
    const it = combat.active && combat.list.find((x) => x.kind === 'player' && x.ref === p.id);
    if (p.revAte && !combat.active) { p.revFim = Date.now() + Math.max(1, p.revAte - combat.round) * 6000; p.revAte = 0; continue; }   // o combate acabou: o resto do minuto segue no relógio
    if ((p.revAte && combat.round > p.revAte) || (!p.revAte && p.revFim && !it && Date.now() > p.revFim)) {
      setRevelacao(p, false);
      for (const s of socketsOf(p)) send(s, { t: 'deny', msg: 'A Revelação Celestial terminou: as asas se desfazem.' });
    }
  }
}, 1000);
function flyOf(it) {
  if (it.kind === 'player') return playerFly(playerById(it.ref));
  if (it.fly !== undefined) return it.fly;
  const e = ents.find((x) => x.id === it.ref); return (e && FLY[e.model]) || 0;
}
const entFly = (e) => { const it = itemOfEnt(e.id); return it ? flyOf(it) : FLY[e.model] || 0; };
const curItem = () => (combat.active ? combat.list[combat.turn] : null);
// no chão vale o deslocamento a pé; no ar, o de voo. O que já andou conta para os dois (regra de trocar de deslocamento).
const budget = (air = false) => { const c = combat.cur, it = curItem(); return c && it ? (air ? flyOf(it) : it.speed) * (1 + c.dash) + c.extra : 0; };
const isTurnOf = (rec) => { const it = curItem(); return !!(it && it.kind === 'player' && it.ref === rec.id); };
const inCombat = (rec) => combat.active && combat.list.some((x) => x.kind === 'player' && x.ref === rec.id);

function combatView(gm) {
  const c = combat, it = curItem();
  const list = c.list.filter((x) => gm || !x.hidden).map((x) => (gm ? { ...x }
    : { cid: x.cid, kind: x.kind, ref: x.ref, name: x.name, model: x.model, flags: x.flags, reac: x.reac }));
  for (const x of list) x.fly = flyOf(c.list.find((y) => y.cid === x.cid));
  const cur = it && c.cur ? { cid: it.cid, n: c.n, used: c.cur.used, budget: budget(), fbudget: budget(true), dash: c.cur.dash, action: c.cur.action, bonus: c.cur.bonus, sx: c.cur.sx, sz: c.cur.sz, sy: c.cur.sy || 0 } : null;
  return { t: 'combat', active: c.active, round: c.round, cur, list, log: gm ? c.log.slice(-40) : undefined };
}
function sendCombat() { for (const c of wss.clients) if (c.role) send(c, combatView(c.role === 'gm')); }

function beginTurn() {
  const it = curItem(); if (!it) return;
  it.flags = []; it.reac = false;
  const p = posOf(it) || { x: 0, z: 0 };
  combat.n++;
  combat.cur = { used: 0, extra: 0, dash: 0, action: false, bonus: false, sx: p.x, sz: p.z, sy: p.y || 0 };
  combat.oa = {};
  combat.cur.near = nearSet(it);
}

// ---- ataque de oportunidade
// Quem está agindo anda; toda criatura hostil que o tinha ao alcance e deixa de ter ganha a chance de reagir.
function nearSet(mover) {
  return new Set(combat.list.filter((x) => x !== mover && hostile(x, mover) && inReach(x, mover)).map((x) => x.cid));
}
// o mestre arrastou alguém para perto de quem está agindo: passa a contar para a oportunidade
function refreshNear() {
  const it = curItem(); if (!it || !combat.cur) return;
  for (const cid of nearSet(it)) combat.cur.near.add(cid);
}
function checkOpportunity(mover) {
  const c = combat.cur; if (!c || !mover || curItem() !== mover) return;
  const now = nearSet(mover);
  for (const cid of c.near) {
    if (now.has(cid)) continue;
    const r = combat.list.find((x) => x.cid === cid);
    if (!r || r.reac || mover.flags.includes(FLAGS.disengage)) continue;
    combat.oa[r.cid] = { target: mover.cid, until: Date.now() + 30000 };
    const msg = { t: 'oa', cid: r.cid, rname: r.name, target: mover.cid, name: mover.name, model: mover.model };
    if (r.kind === 'player') { const pl = playerById(r.ref); if (pl) for (const s of socketsOf(pl)) send(s, msg); }
    else for (const s of wss.clients) if (s.role === 'gm') send(s, msg);
  }
  c.near = now;
}
function endCombat() {
  combat = { active: false, round: 0, turn: 0, n: combat.n, list: [], cur: null, log: [], oa: {} };
}
function advance(dir) {
  if (!combat.active || !combat.list.length) return;
  combat.turn += dir;
  if (combat.turn >= combat.list.length) { combat.turn = 0; combat.round++; }
  if (combat.turn < 0) { combat.turn = combat.list.length - 1; combat.round = Math.max(1, combat.round - 1); }
  beginTurn();
}
function removeCombatant(pred) {
  const curCid = curItem() && curItem().cid;
  const before = combat.list.length;
  const idx = combat.list.findIndex(pred);
  if (idx < 0) return false;
  combat.list.splice(idx, 1);
  if (!combat.active) return true;
  if (!combat.list.length) { endCombat(); return true; }
  if (idx < combat.turn) combat.turn--;
  if (curCid === undefined || combat.list.every((x) => x.cid !== curCid)) {
    if (combat.turn >= combat.list.length) { combat.turn = 0; combat.round++; }
    beginTurn();
  }
  return before !== combat.list.length;
}
function addLog(entry) { combat.log.push({ ...entry, at: Date.now(), round: combat.round }); if (combat.log.length > 80) combat.log.shift(); }

function handleCombatGM(m) {
  const find = (cid) => combat.list.find((x) => x.cid === cid);
  switch (m.t) {
    case 'c_add': {
      const kind = m.kind === 'player' ? 'player' : 'monster', ref = Number(m.ref);
      if (combat.list.some((x) => x.kind === kind && x.ref === ref)) return true;
      let name = String(m.name || '').slice(0, 30), model = String(m.model || '').replace(/[^\w]/g, '');
      if (kind === 'player') { const p = playerById(ref); if (!p) return true; name = p.name; model = p.hero; }
      else if (!ents.some((e) => e.id === ref)) return true;
      const init = m.init === null || m.init === undefined || m.init === '' ? null : clamp(m.init, -10, 99);
      const it = { cid: nextCid++, kind, ref, name: name || 'Criatura', model, init, hidden: false, speed: SPEEDS[model] || 9, reac: false, flags: [] };
      if (combat.active) {
        // entra na posição da iniciativa sem mudar de quem é a vez
        let at = combat.list.findIndex((x) => (x.init ?? -99) < (init ?? -99));
        if (at < 0) at = combat.list.length;
        combat.list.splice(at, 0, it);
        if (at <= combat.turn) combat.turn++;
      } else combat.list.push(it);
      return true;
    }
    case 'c_remove': removeCombatant((x) => x.cid === m.cid); return true;
    case 'c_set': {
      const it = find(m.cid); if (!it) return true;
      if ('init' in m) it.init = m.init === null || m.init === '' ? null : clamp(m.init, -10, 99);
      if ('name' in m) it.name = String(m.name || '').slice(0, 30) || it.name;
      if ('hidden' in m) it.hidden = !!m.hidden;
      if ('speed' in m) it.speed = clamp(m.speed, 0, 60);
      if ('fly' in m) {
        const v = clamp(m.fly, 0, 60);
        if (it.kind === 'player') setPlayerFly(playerById(it.ref), v); else it.fly = v;
      }
      return true;
    }
    case 'c_swap': {
      const i = combat.list.findIndex((x) => x.cid === m.cid), j = i + (m.dir > 0 ? 1 : -1);
      if (i < 0 || j < 0 || j >= combat.list.length) return true;
      const cur = combat.turn;
      [combat.list[i], combat.list[j]] = [combat.list[j], combat.list[i]];
      if (combat.active) { if (cur === i) combat.turn = j; else if (cur === j) combat.turn = i; }
      return true;
    }
    case 'c_sort': {
      // reordena sem tirar a vez de quem está agindo
      const cur = curItem();
      combat.list.sort((a, b) => (b.init ?? -99) - (a.init ?? -99));
      if (cur) combat.turn = combat.list.indexOf(cur);
      return true;
    }
    case 'c_start':
      if (!combat.list.length) return true;
      combat.list.sort((a, b) => (b.init ?? -99) - (a.init ?? -99));
      combat.active = true; combat.round = 1; combat.turn = 0; combat.log = [];
      beginTurn();
      broadcast({ t: 'cfx', fx: 'start' });
      return true;
    case 'c_next': advance(1); return true;
    case 'c_prev': advance(-1); return true;
    case 'c_end':
      if (combat.active) broadcast({ t: 'cfx', fx: 'end' });
      endCombat(); return true;
    case 'c_extra':
      if (combat.cur) combat.cur.extra = clamp(combat.cur.extra + Number(m.m || 0), -60, 120);
      return true;
    case 'c_restore': {
      const c = combat.cur, it = curItem(); if (!c || !it) return true;
      if (m.what === 'action') c.action = false;
      if (m.what === 'bonus') c.bonus = false;
      if (m.what === 'move') { c.used = 0; const p = posOf(it); if (p) { c.sx = p.x; c.sz = p.z; } }
      if (m.what === 'reaction') { const t = find(m.cid) || it; t.reac = false; }
      return true;
    }
  }
  return false;
}

// ação declarada por um jogador no celular, ou pelo mestre na visão de um monstro
function handleAct(it, m, ws) {
  const slot = m.slot, id = String(m.id || '');
  if (!combat.active || !it || !ACTIONS[slot] || !ACTIONS[slot].includes(id)) return;
  const c = combat.cur, isTurn = curItem() === it;
  const target = combat.list.find((x) => x.cid === m.target);
  const deny = (msg) => send(ws, { t: 'deny', msg });
  // ataque básico (corpo a corpo) só em quem está a até 1,5 m
  if (MELEE[slot] && MELEE[slot].includes(id) && target) {
    const offer = id === 'opportunity' && combat.oa[it.cid] && combat.oa[it.cid].target === target.cid && combat.oa[it.cid].until > Date.now();
    if (!offer && !inReach(it, target)) return deny(`${target.name} está a ${fmtM(reachDist(it, target))}. O ataque básico só alcança até 1,5 m.`);
  }
  if (id === 'revelacao') {
    const p = it.kind === 'player' ? playerById(it.ref) : null;
    if (!p || !REV_HEROES.has(p.hero)) return deny('Só a Kaira tem a Revelação Celestial.');
    if (p.rev) return deny('A Revelação Celestial já está ativa.');
  }
  if (slot === 'reaction') { if (it.reac) return deny('A reação desta rodada já foi usada.'); it.reac = true; delete combat.oa[it.cid]; }
  else {
    if (!isTurn) return deny('Só dá para usar isso no próprio turno.');
    if (c[slot]) return deny('Já foi usada neste turno.');
    c[slot] = true;
    if (id === 'dash') c.dash++;
    if (FLAGS[id] && !it.flags.includes(FLAGS[id])) it.flags.push(FLAGS[id]);
  }
  if (id === 'revelacao') setRevelacao(playerById(it.ref), true, true);
  const entry = { cid: it.cid, who: it.name, slot, id, target: target ? target.name : '', tcid: target ? target.cid : 0, spell: m.spell ? String(m.spell).slice(0, 40) : '' };
  addLog(entry);
  broadcast({ t: 'clog', ...entry });
  sendCombat();
}

// Movimento de quem está em combate: só no próprio turno e até o limite de deslocamento.
// Devolve false quando o passo não vale (o cliente volta para onde estava).
// ---- deslocamento no combate: um círculo a partir de onde a criatura começou o turno (como em Trails in the Sky)
// O gasto não é o caminho percorrido: é a distância em linha reta do ponto de início até onde ela está agora.
// Andar para um lado e voltar não gasta nada; dá para se reposicionar à vontade dentro do círculo.
// Terreno difícil continua custando o dobro no trecho da linha que passa por ele; no ar, conta a distância 3D.
// O ataque de oportunidade não muda: sair do alcance de alguém dispara a reação na hora, mesmo voltando depois.
function costFrom(sx, sy, sz, x, y, z) {
  const air = sy > 0.05 || y > 0.05;
  const d = Math.hypot(x - sx, z - sz, air ? y - sy : 0);
  if (air || d < 0.01) return d / M2U;
  const n = Math.max(1, Math.ceil(d / 0.25)); let c = 0;
  for (let i = 0; i < n; i++) { const k = (i + 0.5) / n; c += terrainCost(sx + (x - sx) * k, sz + (z - sz) * k); }
  return (d * c / n) / M2U;
}
function combatStep(it, ox, oz, nx, nz, oy = 0, ny = 0) {
  const d = Math.hypot(nx - ox, nz - oz, ny - oy);
  if (!combat.active || !it || d <= 0.01) return true;
  if (curItem() !== it) return false;
  const c = combat.cur;
  const air = oy > 0.05 || ny > 0.05 || (c.sy || 0) > 0.05;
  const used = costFrom(c.sx, c.sy || 0, c.sz, nx, ny, nz), lim = budget(air);
  // fora do círculo só pode voltar para dentro (a folga de 0,3 m cobre o atraso do celular)
  if (used > lim + 0.3 && used > c.used + 0.01) return false;
  c.used = used;
  return true;
}
// o mestre dá (ou tira) deslocamento de voo a um jogador; sem voo, quem estava no ar desce ao chão
function setPlayerFly(p, v) {
  if (!p) return;
  p.fly = v;
  if (!playerFly(p) && p.y) { p.y = 0; for (const s of socketsOf(p)) send(s, { t: 'teleport', x: p.x, z: p.z, y: 0 }); }
}
const altOf = (v, fly) => (fly > 0 ? clamp(Number(v) || 0, 0, MAX_ALT) : 0);
const itemOfPlayer = (rec) => combat.list.find((x) => x.kind === 'player' && x.ref === rec.id);
const itemOfEnt = (id) => combat.list.find((x) => x.kind === 'monster' && x.ref === id);

wss.on('connection', (ws) => {
  ws.role = null;
  ws.on('message', (raw) => {
    let m; try { m = JSON.parse(raw); } catch { return; }
    if (m.t === 'hello') {
      ws.role = m.role === 'gm' ? 'gm' : 'player';
      let me = null;
      if (ws.role === 'player') {
        const token = String(m.token || '').slice(0, 64) || 'anon-' + Math.random();
        me = known.get(token);
        const jitter = () => (Math.random() - 0.5) * 1.5;
        if (!me) {
          me = { id: nextId++, x: map.spawn.x + jitter(), z: map.spawn.z + jitter(), ry: 0, mv: 0 };
          known.set(token, me);
        }
        me.name = String(m.name || 'Aventureiro').slice(0, 20);
        me.hero = String(m.hero || 'Knight').slice(0, 30);
        for (const it of combat.list) if (it.kind === 'player' && it.ref === me.id) { it.name = me.name; it.model = me.hero; }
        players.set(ws, me);
      }
      send(ws, { t: 'init', id: me ? me.id : 0, me, version: map.version, ents, doors, frozen, players: playerList(), aoes });
      send(ws, combatView(ws.role === 'gm'));
      send(ws, { t: 'fichas', fichas });
      send(ws, { t: 'mesa', ...mesa });
      send(ws, { t: 'rotas', list: rotas });
      if (ws.role === 'gm') send(ws, { t: 'imagens', list: listImagens() });
      return;
    }
    if (!ws.role) return;
    const me = players.get(ws);
    switch (m.t) {
      case 'move': {
        if (!me) break;
        const nx = Number(m.x) || 0, nz = Number(m.z) || 0, oy = me.y || 0, ny = altOf(m.y, playerFly(me));
        me.ry = Number(m.ry) || 0;
        const d = Math.hypot(nx - me.x, nz - me.z, ny - oy);
        // em combate só anda quem está no próprio turno, até o limite de deslocamento
        let ok = !frozen || d < 0.01;
        const it = inCombat(me) ? itemOfPlayer(me) : null;
        if (ok && it) ok = combatStep(it, me.x, me.z, nx, nz, oy, ny);
        if (ok) { me.x = nx; me.z = nz; me.y = ny; me.mv = m.mv ? 1 : 0; if (it && d > 0.01) checkOpportunity(it); }
        else { me.mv = 0; send(ws, { t: 'teleport', x: me.x, z: me.z, y: oy }); }
        break;
      }
      case 'door': {
        // em combate, um jogador só mexe em porta no próprio turno
        if (me && combat.active && inCombat(me) && !isTurnOf(me)) break;
        const i = m.i | 0;
        if (i >= 0 && i < doors.length) { doors[i] = !doors[i]; broadcast({ t: 'door', i, closed: doors[i] }); saveSoon(); }
        break;
      }
      case 'aoe': {
        const a = m.area || {};
        if (!AOE_FORMAS.has(a.forma)) break;
        const W = 2000;
        const area = {
          id: nextAoe++, forma: a.forma, nome: String(a.nome || '').slice(0, 40), por: me ? me.name : String(m.por || 'Mestre').slice(0, 30),
          tam: num(a.tam, 0.5, 150, 1.5), larg: num(a.larg, 0.5, 30, 1.5), alcance: num(a.alcance, 0, 500), dir: num(a.dir, -10, 10),
          ox: num(a.ox, -W, W), oz: num(a.oz, -W, W), vx: num(a.vx, -W, W, num(a.ox, -W, W)), vz: num(a.vz, -W, W, num(a.oz, -W, W)), cx: num(a.cx, -W, W), cz: num(a.cz, -W, W), y: num(a.y, -100, 200),
          half: num(a.half, 0.5, 8, 1), dono: String(a.dono || '').slice(0, 12), cor: num(a.cor, 0, 0xffffff, 0xb58cff),
          at: Date.now(), ttl: AOE_MS, fixa: false,
        };
        aoes.push(area); if (aoes.length > 12) aoes.shift();
        sendAoes();
        break;
      }
      case 'revelacao': {
        if (!me || !REV_HEROES.has(me.hero)) break;
        const inC = combat.active && combat.list.some((x) => x.kind === 'player' && x.ref === me.id);
        if (m.on && inC) { send(ws, { t: 'deny', msg: 'Em combate, a Revelação Celestial é a sua ação bônus (menu AÇÃO BÔNUS).' }); break; }
        setRevelacao(me, !!m.on, false);
        break;
      }
      // ---- mesa, mapa do mundo e teatro da mente
      case 'mesa': {
        if (ws.role !== 'gm') break;
        const modo = ['mundo', 'cena', 'imagem'].includes(m.modo) ? m.modo : mesa.modo;
        const img = typeof m.imagem === 'string' && m.imagem.startsWith('/imagens/') && fs.existsSync(path.join(IMG_DIR, path.basename(m.imagem))) ? m.imagem : mesa.imagem;
        if (modo === 'imagem' && !img) break;
        mesa = { modo, imagem: img, legenda: m.legenda !== undefined ? String(m.legenda).slice(0, 120) : mesa.legenda };
        saveMesa(); broadcast({ t: 'mesa', ...mesa });
        break;
      }
      case 'ping': {   // marca um ponto no mapa do mundo; o do mestre leva a tela dos jogadores até lá
        const gm = ws.role === 'gm';
        broadcast({ t: 'ping', x: num(m.x, -1e5, 1e5), y: num(m.y, -1e5, 1e5), por: me ? me.name : 'Mestre', hero: me ? me.hero : '', gm, leva: gm && !!m.leva }, ws);
        break;
      }
      case 'traco': {   // régua ou rota sendo desenhada agora (ao vivo para todos); pts vazio apaga
        const id = me ? 'p' + me.id : 'gm';
        ws.traco = id;
        broadcast({ t: 'traco', id, ctx: m.ctx === 'cena' ? 'cena' : 'mundo', tipo: m.tipo === 'rota' ? 'rota' : 'regua', pts: ptList(m.pts, 80), por: me ? me.name : 'Mestre', hero: me ? me.hero : '' }, ws);
        break;
      }
      case 'rota_add': {
        const pts = ptList(m.pts, 120);
        if (pts.length < 2) break;
        rotas.push({ id: nextRota++, nome: String(m.nome || 'Rota').slice(0, 60), pts, por: me ? me.name : 'Mestre', hero: me ? me.hero : '', dono: me ? 'p' + me.id : 'gm', em: Date.now() });
        if (rotas.length > 60) rotas.shift();
        saveMesa(); broadcast({ t: 'rotas', list: rotas });
        break;
      }
      case 'rota_del': {
        const r = rotas.find((x) => x.id === m.id);
        if (!r || !(ws.role === 'gm' || (me && r.dono === 'p' + me.id))) break;
        rotas = rotas.filter((x) => x !== r); saveMesa(); broadcast({ t: 'rotas', list: rotas });
        break;
      }
      case 'rotas_limpar': if (ws.role === 'gm') { rotas = []; saveMesa(); broadcast({ t: 'rotas', list: rotas }); } break;
      case 'ficha': {
        // o jogador edita a ficha do próprio herói; o mestre pode editar qualquer uma
        const hero = ws.role === 'gm' ? String(m.hero || '') : me && me.hero;
        if (!FICHA_HEROIS.has(hero)) break;
        fichas[hero] = normFicha(hero, m.ficha);
        saveFicha(hero);
        broadcast({ t: 'fichas', fichas });
        break;
      }
      case 'act': {
        // o mestre age por um monstro (visão do monstro): "as" é o participante do combate
        const it = me ? itemOfPlayer(me) : ws.role === 'gm' ? combat.list.find((x) => x.cid === m.as && x.kind === 'monster') : null;
        handleAct(it, m, ws);
        break;
      }
      case 'end_turn': {
        const cur = curItem();
        const mine = cur && (me ? cur.kind === 'player' && cur.ref === me.id : ws.role === 'gm' && cur.cid === m.as);
        if (mine) { addLog({ cid: cur.cid, who: cur.name, slot: 'end', id: 'end' }); advance(1); sendCombat(); }
        break;
      }
    }
    if (ws.role !== 'gm') return;
    if (handleCombatGM(m)) { sendCombat(); return; }
    switch (m.t) {
      case 'aoe_del': aoes = aoes.filter((a) => a.id !== m.id); sendAoes(); break;
      case 'aoe_fixar': { const a = aoes.find((x) => x.id === m.id); if (a) { a.fixa = !!m.on; if (!a.fixa) a.at = Date.now(); sendAoes(); } break; }
      case 'ent_add': {
        const e = {
          id: nextId++, kind: m.kind === 'prop' ? 'prop' : 'monster', model: String(m.model || '').replace(/[^\w]/g, ''),
          x: Number(m.x) || 0, z: Number(m.z) || 0, ry: Number(m.ry) || 0, scale: clamp(m.scale || 1, 0.3, 4),
        };
        ents.push(e); broadcast({ t: 'ent', ent: e }); saveSoon();
        break;
      }
      case 'pmove': {
        // o mestre anda com um monstro pela visão dele (WASD): mesmas regras de turno e deslocamento dos jogadores
        const e = ents.find((x) => x.id === m.id && x.kind === 'monster');
        if (!e) break;
        const nx = Number(m.x) || 0, nz = Number(m.z) || 0, it = itemOfEnt(e.id), oy = e.y || 0, ny = altOf(m.y, entFly(e));
        e.ry = Number(m.ry) || 0;
        if (it && !combatStep(it, e.x, e.z, nx, nz, oy, ny)) { e.mv = 0; send(ws, { t: 'pteleport', id: e.id, x: e.x, z: e.z, y: oy }); broadcast({ t: 'ent', ent: e }); break; }
        const moved = Math.hypot(nx - e.x, nz - e.z, ny - oy) > 0.01;
        e.x = nx; e.z = nz; e.y = ny; e.mv = m.mv ? 1 : 0;
        broadcast({ t: 'ent', ent: e }, ws); saveSoon();
        if (it && moved) checkOpportunity(it);
        break;
      }
      case 'ent_update': {
        const e = ents.find((x) => x.id === m.id);
        if (!e) break;
        if (m.x !== undefined) e.x = Number(m.x) || 0;
        if (m.z !== undefined) e.z = Number(m.z) || 0;
        if (m.ry !== undefined) e.ry = Number(m.ry) || 0;
        if (m.scale !== undefined) e.scale = clamp(m.scale, 0.3, 4);
        e.mv = 0;
        broadcast({ t: 'ent', ent: e }, ws); saveSoon();
        // arrastar o monstro da vez no mapa também conta como ele se mexendo (pode provocar oportunidade)
        { const it = itemOfEnt(e.id); if (it && curItem() === it) checkOpportunity(it); else refreshNear(); }
        break;
      }
      case 'ent_del':
        ents = ents.filter((x) => x.id !== m.id); broadcast({ t: 'ent_del', id: m.id }); saveSoon();
        if (removeCombatant((x) => x.kind === 'monster' && x.ref === m.id)) sendCombat();
        break;
      case 'terrain': {
        // o mestre manda o terreno inteiro: uma letra por quadrado
        const n = Math.ceil(map.w) * Math.ceil(map.h);
        const cells = String(m.cells || '');
        if (cells.length !== n || !/^[pgmtlbasrnve]*$/.test(cells)) break;
        map.terrain = { biome: String(m.biome || 'masmorra').replace(/[^a-z]/g, '').slice(0, 20), cells };
        broadcast({ t: 'terrain', terrain: map.terrain }, ws); saveSoon();
        break;
      }
      case 'walls': {
        const ok = (v) => Number.isFinite(v) && v > -5 && v < 500;
        const walls = (Array.isArray(m.walls) ? m.walls : []).slice(0, 5000)
          .map((w) => (Array.isArray(w) ? w.slice(0, 4).map(Number) : [])).filter((w) => w.length === 4 && w.every(ok));
        const newDoors = (Array.isArray(m.doors) ? m.doors : []).slice(0, 500)
          .map((d) => ({ x1: Number(d.x1), y1: Number(d.y1), x2: Number(d.x2), y2: Number(d.y2), closed: d.closed !== false }))
          .filter((d) => [d.x1, d.y1, d.x2, d.y2].every(ok));
        map.walls = walls; map.doors = newDoors; doors = newDoors.map((d) => d.closed);
        map.version = Date.now(); saveSoon();
        broadcast({ t: 'map', version: map.version, ents, doors });
        break;
      }
      case 'freeze':
        frozen = !!m.on; broadcast({ t: 'frozen', on: frozen });
        break;
      case 'floor':
        map.floorMode = m.mode === 'image' && map.hasImage ? 'image' : 'tiles';
        map.version = Date.now(); saveSoon();
        broadcast({ t: 'map', version: map.version, ents, doors });
        break;
      case 'spawn':
        map.spawn = { x: Number(m.x) || 0, z: Number(m.z) || 0 }; saveSoon();
        broadcast({ t: 'spawn', spawn: map.spawn });
        break;
      case 'player_move': {
        // o mestre pode arrastar qualquer jogador, mesmo em combate (não gasta deslocamento)
        const pl = playerById(m.id);
        if (pl) { pl.x = Number(m.x) || 0; pl.z = Number(m.z) || 0; for (const c of socketsOf(pl)) send(c, { t: 'teleport', x: pl.x, z: pl.z, y: pl.y || 0 }); refreshNear(); }
        break;
      }
      case 'player_set': {
        // deslocamento de voo do jogador (metros; 0 tira o voo)
        const pl = playerById(m.id);
        if (pl && 'fly' in m) { setPlayerFly(pl, clamp(m.fly, 0, 60)); sendCombat(); }
        break;
      }
      case 'player_del': {
        // tira da sessão um jogador que saiu de vez
        for (const [tok, pl] of known) if (pl.id === m.id) {
          known.delete(tok);
          for (const c of socketsOf(pl)) { players.delete(c); send(c, { t: 'kicked' }); c.close(); }
        }
        if (removeCombatant((x) => x.kind === 'player' && x.ref === m.id)) sendCombat();
        break;
      }
    }
  });
  ws.on('close', () => { players.delete(ws); if (ws.traco) broadcast({ t: 'traco', id: ws.traco, pts: [] }); });
  ws.on('error', () => {});
});

// posições dos jogadores, 10 vezes por segundo (com o deslocamento já usado no turno)
setInterval(() => {
  if (wss.clients.size) broadcast({ t: 'players', list: playerList(), tu: combat.cur ? combat.cur.used : 0 });
}, 100);

server.listen(PORT, '0.0.0.0', () => {
  const ips = lanAddresses();
  console.log('\n  VTT 3D — protótipo\n');
  console.log(`  Tela do mestre (neste PC):  http://localhost:${PORT}/mestre`);
  if (ips.length) {
    console.log('  Jogadores (celular, mesmo Wi-Fi):');
    for (const ip of ips) console.log('     ' + playerUrl(ip));
  } else {
    console.log('  Não encontrei rede local. Conecte o PC ao Wi-Fi para os celulares entrarem.');
  }
  console.log('\n  Deixe esta janela aberta durante a sessão. Ctrl+C encerra.\n');
});
