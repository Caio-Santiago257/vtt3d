// Tela do jogador: primeira pessoa, pensada para celular.
import * as THREE from 'three';
import { AreaTool, GRIMORIOS, PRESETS, SHAPES, fmtArea } from './area.js';
import { areaCreatures, HEROES, MONSTERS, Session, makeRenderer, makeCharacter, sizeOf, ACT_CLIPS, animFor, updateAirMark, WALL_H } from './common.js';
import { glowTexture } from './gfx.js';
import { CelestialForm, hasRevelation } from './revelacao.js';
import { ReguaTool, RulerDraw, makeLabel, medir, toScreen } from './regua.js';
import { LightMap, NightPass, tickLuzes, LUZ_PESSOAL, VISAO_ESCURO, M2U as LM2U } from './luzes.js';
import { MundoView, ImagemView, corDe } from './mundo.js';
import { FichaUI } from './ficha-ui.js';
import { temFicha, grimorio, slotsLivres, efeitoEm, CIRC_NOME } from './regras.js';
import { ACTIONS, SLOT_NOME, M2U, fmtM, logText, TurnOrder, banner, toast, chime, unlockAudio, makeRangeRing, setPortrait, warmPortraits } from './combate-ui.js';

const $ = (id) => document.getElementById(id);
const mobile = matchMedia('(pointer: coarse)').matches;
// Visão do monstro: o mestre abre esta mesma tela com ?possuir=<id do monstro> e anda com ele.
const POSSESS = Number(new URLSearchParams(location.search).get('possuir')) || 0;
if (POSSESS) document.body.classList.add('modo-possuir');
let EYE = 1.8, SPEED = 4.2, SIZE = 1, BODY_R = 0.45;
// ---- voo: altura em unidades do mundo (0 = no chão)
let posY = 0, flyUp = false, flyDown = false;
const MAX_ALT = 30 * (4 / 3), selfAir = {};
function flySpeed() {
  // em combate vale o que o mestre deixou no combate; fora dele, o do jogador (ou do catálogo, para monstros)
  const it = session && session.combat.active ? meItem() : null;
  if (it && it.fly !== undefined) return it.fly;
  if (POSSESS) { const e = session && session.ents.get(POSSESS), m = e && MONSTERS.find((x) => x.id === e.data.model); return (m && m.fly) || 0; }
  const me = session && session.players.get(session.myId);
  return Math.max((me && me.data.fly) || 0, me && me.data.rev ? 9 : 0);   // Revelação Celestial: voo = deslocamento
}
const inAir = () => posY > 0.05;

// ---------------------------------------------------------------- entrada
let hero = localStorage.getItem('vtt.hero') || 'Knight';
$('nome').value = localStorage.getItem('vtt.nome') || '';
const grade = $('herois');
if (!POSSESS) HEROES.forEach((h) => {
  const b = document.createElement('button');
  b.textContent = h.nome; b.dataset.id = h.id; b.className = 'opcao';
  b.onclick = () => { hero = h.id; marcar(); };
  grade.appendChild(b);
});
function marcar() { [...grade.children].forEach((b) => b.classList.toggle('sel', b.dataset.id === hero)); }
marcar();

// ---------------------------------------------------------------- cena
const canvas = $('c');
const renderer = makeRenderer(canvas, mobile);
const scene = new THREE.Scene();
scene.background = new THREE.Color(0x050508);
scene.fog = new THREE.FogExp2(0x050508, 0.035);
const camera = new THREE.PerspectiveCamera(72, innerWidth / innerHeight, 0.1, 90);
camera.rotation.order = 'YXZ';
const hemi = new THREE.HemisphereLight(0x8c96b8, 0x1a1a22, 0.8);
const sun = new THREE.DirectionalLight(0xffffff, 0);
sun.position.set(-0.5, 1, 0.35);
scene.add(hemi, sun);
// céu em degradê: horizonte na cor da neblina, alto na cor do bioma
const skyGeo = new THREE.SphereGeometry(80, 24, 12);
skyGeo.setAttribute('color', new THREE.BufferAttribute(new Float32Array(skyGeo.attributes.position.count * 3), 3));
const sky = new THREE.Mesh(skyGeo, new THREE.MeshBasicMaterial({ vertexColors: true, side: THREE.BackSide, fog: false, depthWrite: false }));
sky.renderOrder = -10; sky.frustumCulled = false; scene.add(sky);
function paintSky(horizon, zenith) {
  const a = new THREE.Color(horizon), z = new THREE.Color(zenith), c = new THREE.Color(), pos = skyGeo.attributes.position, col = skyGeo.attributes.color;
  for (let i = 0; i < pos.count; i++) {
    const t = Math.max(0, Math.min(1, pos.getY(i) / 80 / 0.55)); // sobe do horizonte até ~35 graus
    c.copy(a).lerp(z, t * t * (3 - 2 * t)); col.setXYZ(i, c.r, c.g, c.b);
  }
  col.needsUpdate = true;
}
// partículas no ar em volta do jogador: pólen, vaga-lumes, neve, poeira
const PN = 260, PBOX = [26, 9, 26];
const pGeo = new THREE.BufferGeometry(); const pPos = new Float32Array(PN * 3), pSeed = new Float32Array(PN);
for (let i = 0; i < PN; i++) { pPos[i * 3] = Math.random() * PBOX[0]; pPos[i * 3 + 1] = Math.random() * PBOX[1]; pPos[i * 3 + 2] = Math.random() * PBOX[2]; pSeed[i] = Math.random() * 100; }
pGeo.setAttribute('position', new THREE.BufferAttribute(new Float32Array(PN * 3), 3));
const pMat = new THREE.PointsMaterial({ map: glowTexture(), size: 0.1, transparent: true, depthWrite: false, sizeAttenuation: true });
const motes = new THREE.Points(pGeo, pMat); motes.frustumCulled = false; scene.add(motes);
let pCfg = { n: 0, vy: 0 };
pGeo.setDrawRange(0, 0); paintSky(0x07070d, 0x07070d);
function updateMotes(dt, t) {
  const out = pGeo.attributes.position;
  for (let i = 0; i < pCfg.n; i++) {
    const s = pSeed[i];
    pPos[i * 3] += Math.sin(t * 0.4 + s) * 0.25 * dt; pPos[i * 3 + 1] += pCfg.vy * dt + Math.sin(t * 0.7 + s * 2) * 0.12 * dt; pPos[i * 3 + 2] += Math.cos(t * 0.33 + s) * 0.25 * dt;
    // a caixa de partículas acompanha a câmera, dando a volta nas bordas
    for (let k = 0; k < 3; k++) {
      const c = k === 0 ? camera.position.x : k === 1 ? PBOX[1] / 2 : camera.position.z, B = PBOX[k];
      out.array[i * 3 + k] = c + ((((pPos[i * 3 + k] - c) % B) + B * 1.5) % B) - B / 2;
    }
  }
  out.needsUpdate = true;
}
// clima do bioma escolhido pelo mestre, ajustado pelo horário (manhã, tarde, noite) que o mestre escolhe
let lastBiome = null;
const mixHex = (a, b, t) => new THREE.Color(a).lerp(new THREE.Color(b), t).getHex();
const horaAtual = () => (session && session.mesa && session.mesa.hora) || 'manha';
function comHora(b, hora) {
  if (hora === 'tarde') return { ...b, fog: mixHex(b.fog, 0xf0a060, 0.55), zenith: mixHex(b.zenith, 0x5a4f9e, 0.55), sky: mixHex(b.sky, 0xffc08a, 0.55),
    ground: mixHex(b.ground, 0x5a3a40, 0.3), sunColor: 0xffa055, sun: b.sun * 0.95, hemi: b.hemi * 0.85, far: mixHex(b.far, 0xc0703a, 0.35) };
  if (hora === 'noite') return { ...b, fog: 0x03050a, zenith: 0x010207, sky: 0xaab4d4, ground: 0x34343e, hemi: 1.05, sun: 0.35, sunColor: 0x9fb0ff, torch: 0,
    density: Math.max(b.density, 0.02), part: { ...b.part, n: Math.min(b.part.n, 60) } };
  return b;
}
function atmosfera(b0) {
  const b = comHora(b0, horaAtual());
  camera.far = 700; camera.updateProjectionMatrix();   // o fundo panorâmico de cada bioma fica a 300 unidades
  lastBiome = b0;
  paintSky(b.fog, b.zenith);
  pCfg = b.part; pGeo.setDrawRange(0, b.part.n);
  pMat.color.setHex(b.part.color); pMat.size = b.part.size * 2.2; pMat.blending = b.part.glow ? THREE.AdditiveBlending : THREE.NormalBlending; pMat.needsUpdate = true;
  scene.background.setHex(b.fog); scene.fog.color.setHex(b.fog); scene.fog.density = b.density;
  hemi.color.setHex(b.sky); hemi.groundColor.setHex(b.ground); hemi.intensity = b.hemi;
  sun.color.setHex(b.sunColor); sun.intensity = b.sun;
  // criatura grande (visão do monstro): a câmera fica longe, então a luz de quem olha precisa ir mais longe
  torch.intensity = b.torch * (SIZE > 1 ? 4 : 1); torch.distance = SIZE > 1 ? 34 : 15; torch.decay = SIZE > 1 ? 0.8 : 1.5;
  if (SIZE > 1) hemi.intensity = b.hemi * 1.8;
}
const torch = new THREE.PointLight(0xffc48a, 9, 15, 1.5); // a tocha do próprio jogador
scene.add(torch);

// ---- iluminação dinâmica: mapa de luz (paredes cortam a luz) e passada final do horário
const lightmap = new LightMap();
const night = new NightPass(renderer, { mobile });
let luzTimer = 0, segTimer = 0, ultimaHora = '';
const minhaLuz = () => (POSSESS ? '' : (myData() || {}).luz || '');
function visaoNoEscuro() {   // metros
  if (POSSESS) return SIZE > 1 ? 36 : 18;   // monstros costumam ter visão no escuro
  const d = myData(); if (!d) return 0;
  if (temFicha(d.hero)) { const f = ficha.f; return f.visaoEscuro ?? VISAO_ESCURO[d.hero] ?? 0; }
  return VISAO_ESCURO[d.hero] || 0;
}
function atualizaLuz(dt) {
  const w = session && session.world; if (!w) return;
  const hora = horaAtual();
  if (hora !== ultimaHora) { ultimaHora = hora; if (lastBiome) atmosfera(lastBiome); }
  lightmap.setBounds(0, 0, w.bounds.w, w.bounds.h);
  if ((segTimer -= dt) <= 0) { segTimer = 0.3; lightmap.setSegments(session.lightBlockers()); }
  if ((luzTimer -= dt) > 0) return;
  luzTimer = 0.1;
  const q = (v) => Math.round(v * 4) / 4;
  const self = { id: session.myId, x: q(pos.x), z: q(pos.z), y: posY, luz: minhaLuz() };
  const all = session.allLights(self).map((l) => ({ ...l, x: q(l.x), z: q(l.z) }));
  if (hora === 'noite') lightmap.setLights(all);
  // as fontes do mestre e as dos personagens também acendem luzes de verdade perto de quem olha (brilho nos modelos)
  session.dynPool = all.filter((l) => l.key[0] !== 'm').map((l) => ({ x: l.x, z: l.z, y: l.y, color: l.cor, range: (l.plena + l.penumbra) * 0.75, intensity: l.fogo ? 0.9 : 0.7 }));
  // a minha luz: a luz de verdade que vai junto com a câmera
  const L = LUZ_PESSOAL[minhaLuz()];
  if (hora === 'noite') { torch.intensity = L ? (L.plena ? 10 : 3) : 0; if (L) { torch.color.setHex(L.cor); torch.distance = (L.plena + L.penumbra) * LM2U * 1.2; } }
  const dv = visaoNoEscuro();
  lightmap.setViewer(q(pos.x), q(pos.z), hora === 'noite' && dv > 0 ? dv * LM2U : 0);
}

const pos = new THREE.Vector3(0, 0, 0);
let yaw = 0, pitch = 0, joined = false, moving = false;
let session = null;

// identidade fixa deste celular: se a tela bloquear, ele volta como o mesmo personagem
let token = localStorage.getItem('vtt.token');
if (!token) { token = Math.random().toString(36).slice(2) + Date.now().toString(36); localStorage.setItem('vtt.token', token); }

// ---------------------------------------------------------------- personagem próprio (terceira pessoa)
const selfHolder = new THREE.Group(); selfHolder.visible = false; scene.add(selfHolder);
let selfChar = null, selfModel = '', face = 0;
async function loadSelf(model) {
  if (model === selfModel) return;
  selfModel = model;
  const c = await makeCharacter(model);
  if (selfModel !== model) return;
  if (selfForm) { selfForm.dispose(); selfForm = null; }
  for (const ch of [...selfHolder.children]) selfHolder.remove(ch);
  selfChar = c; selfHolder.add(c.obj);
  if (hasRevelation(model)) selfForm = new CelestialForm(selfHolder, c, scene);
  updateRevBtn();
}
// ---- Revelação Celestial (Kaira): fora de combate o botão liga/desliga; em combate é a ação bônus
let selfForm = null;
const myData = () => { const me = session && session.players.get(session.myId); return me ? me.data : null; };
function updateRevBtn() {
  const d = myData(), b = $('revelar');
  const ok = !POSSESS && d && hasRevelation(d.hero);
  b.hidden = !ok; if (!ok) return;
  b.classList.toggle('on', !!d.rev);
  b.textContent = d.rev ? '✦ DESFAZER ASAS' : '✦ REVELAÇÃO CELESTIAL';
}
$('revelar').onclick = () => {
  const d = myData(); if (!d || !session) return;
  if (!d.rev && session.combat.active && meItem()) { toast('Em combate, a Revelação Celestial é a sua AÇÃO BÔNUS (menu de ações).'); return; }
  session.send({ t: 'revelacao', on: !d.rev });
  if (!d.rev) { selfForm && selfForm.preload(); toast('Asas reveladas por 1 minuto. Suba (▲ ou Espaço) para levantar voo.'); }
};
let viewOverride = null; // null = automático (3ª pessoa em combate)
const view = () => viewOverride || (POSSESS || (session && session.combat.active) ? '3p' : '1p');
$('vista').onclick = () => { viewOverride = view() === '3p' ? '1p' : '3p'; };

// marcador dourado sobre quem está agindo
const turnMark = new THREE.Mesh(new THREE.OctahedronGeometry(0.26, 0), new THREE.MeshBasicMaterial({ color: 0xffd36b, fog: false }));
turnMark.scale.y = 1.5; turnMark.visible = false; scene.add(turnMark);
const ring = makeRangeRing(0x5ff3ff); scene.add(ring);
// marca do ponto onde o turno começou (centro do círculo de movimento): um losango pequeno girando no chão
const startMark = new THREE.Mesh(new THREE.RingGeometry(0.22, 0.32, 4), new THREE.MeshBasicMaterial({ color: 0x5ff3ff, transparent: true, opacity: 0.85, depthWrite: false, side: THREE.DoubleSide }));
startMark.rotation.x = -Math.PI / 2; startMark.renderOrder = 4; startMark.visible = false; scene.add(startMark);

function resize() {
  renderer.setSize(innerWidth, innerHeight, false);
  camera.aspect = innerWidth / innerHeight; camera.updateProjectionMatrix();
}
addEventListener('resize', resize);

// ---------------------------------------------------------------- controles
const move = { x: 0, y: 0 };      // -1..1 (direita, frente)
const keys = new Set();
const stick = $('stick'), knob = stick.firstElementChild;
let moveTouch = null, lookTouch = null;

canvas.addEventListener('pointerdown', (e) => {
  if (!joined) return;
  canvas.setPointerCapture(e.pointerId);
  const left = e.pointerType !== 'mouse' && e.clientX < innerWidth * 0.45;
  if (left && !moveTouch) {
    moveTouch = { id: e.pointerId, x: e.clientX, y: e.clientY };
    stick.hidden = false; stick.style.left = e.clientX + 'px'; stick.style.top = e.clientY + 'px';
    knob.style.transform = 'translate(-50%,-50%)';
  } else if (!lookTouch) {
    lookTouch = { id: e.pointerId, x: e.clientX, y: e.clientY };
  }
  $('dica').hidden = true;
});
canvas.addEventListener('pointermove', (e) => {
  if (moveTouch && e.pointerId === moveTouch.id) {
    let dx = e.clientX - moveTouch.x, dy = e.clientY - moveTouch.y;
    const R = 56, d = Math.hypot(dx, dy);
    if (d > R) { dx *= R / d; dy *= R / d; }
    move.x = dx / R; move.y = -dy / R;
    knob.style.transform = `translate(calc(-50% + ${dx}px), calc(-50% + ${dy}px))`;
  } else if (lookTouch && e.pointerId === lookTouch.id) {
    const k = e.pointerType === 'mouse' ? 0.0032 : 0.0052;
    yaw -= (e.clientX - lookTouch.x) * k;
    pitch = Math.max(-1.2, Math.min(1.2, pitch - (e.clientY - lookTouch.y) * k));
    lookTouch.x = e.clientX; lookTouch.y = e.clientY;
  }
});
function release(e) {
  if (moveTouch && e.pointerId === moveTouch.id) { moveTouch = null; move.x = move.y = 0; stick.hidden = true; }
  if (lookTouch && e.pointerId === lookTouch.id) lookTouch = null;
}
canvas.addEventListener('pointerup', release);
canvas.addEventListener('pointercancel', release);
addEventListener('keydown', (e) => {
  if (['INPUT', 'TEXTAREA', 'SELECT'].includes(e.target.tagName)) return;
  keys.add(e.code);
  if (e.code === 'KeyE' && joined) interact();
  if (e.code === 'Space' && joined) e.preventDefault(); // espaço é subir (voo), não rolar a página nem apertar botão
});
addEventListener('keyup', (e) => keys.delete(e.code));
addEventListener('blur', () => keys.clear());

let alvo = null; // porta ao alcance
function interact() { if (alvo && session) session.send({ t: 'door', i: alvo.i }); }
$('interagir').addEventListener('click', interact);

// ---------------------------------------------------------------- tela cheia
// Esconde a barra do navegador (o endereço no topo), em pé ou deitado. O navegador só aceita depois de um toque
// do jogador: tenta ao entrar, e se a tela cheia cair (o jogador saiu dela, trocou de aba...), o botão ⛶ aparece.
// No iPhone o Safari não deixa sites entrarem em tela cheia: lá o caminho é "Adicionar à Tela de Início"
// (o manifesto e as metas apple-mobile-web-app fazem o jogo abrir sem barra nenhuma).
const fsEl = () => document.fullscreenElement || document.webkitFullscreenElement;
const fsOk = !!(document.documentElement.requestFullscreen || document.documentElement.webkitRequestFullscreen);
const standalone = matchMedia('(display-mode: fullscreen), (display-mode: standalone)').matches || navigator.standalone;
const touchDevice = matchMedia('(pointer: coarse)').matches;
function telaCheia() {
  if (POSSESS || standalone || fsEl() || !touchDevice) return;   // no PC (e na visão do monstro do mestre) não força
  const el = document.documentElement;
  try {
    const p = el.requestFullscreen ? el.requestFullscreen({ navigationUI: 'hide' }) : el.webkitRequestFullscreen();
    if (p && p.catch) p.catch(() => {});
  } catch {}
}
function updateFsBtn() { $('telacheia').hidden = POSSESS || standalone || !touchDevice || !fsOk || !!fsEl() || !session; }
document.addEventListener('fullscreenchange', updateFsBtn); document.addEventListener('webkitfullscreenchange', updateFsBtn);
// no PC (e na visão do monstro, dentro da página do mestre) o botão direito também não abre o menu do navegador
document.addEventListener('contextmenu', (e) => { if (!e.target.closest('input, textarea')) e.preventDefault(); }, true);
$('telacheia').addEventListener('click', () => { telaCheia(); setTimeout(updateFsBtn, 400); });
if (touchDevice && !fsOk && !standalone && !POSSESS && !localStorage.getItem('vtt.dicaIphone')) {
  // iPhone: avisa uma vez como jogar sem a barra
  setTimeout(() => { toast('Para jogar sem a barra do navegador: toque em Compartilhar e em "Adicionar à Tela de Início".'); localStorage.setItem('vtt.dicaIphone', '1'); }, 2500);
}

// ---------------------------------------------------------------- sessão
function entrar() {
  const nome = POSSESS ? '' : $('nome').value.trim() || HEROES.find((h) => h.id === hero).nome;
  if (!POSSESS) EYE = (HEROES.find((h) => h.id === hero) || {}).eye || 1.8;   // altura dos olhos (o halfling vê de mais baixo)
  if (!POSSESS) { localStorage.setItem('vtt.nome', nome); localStorage.setItem('vtt.hero', hero); }
  $('entrar').disabled = true; $('entrar').textContent = 'Entrando…';
  unlockAudio();
  telaCheia();   // o toque em ENTRAR conta como gesto do usuário: o navegador deixa esconder a barra de endereço
  session = new Session({
    scene, role: POSSESS ? 'gm' : 'player',
    hello: () => (POSSESS ? {} : { name: nome, hero, token }),
    on: {
      init(m) {
        updateFsBtn();
        if (m.me) { pos.set(m.me.x, 0, m.me.z); posY = m.me.y || 0; }
        if (POSSESS) {
          const e = m.ents.find((x) => x.id === POSSESS);
          if (!e) { aviso('Este monstro não está mais no mapa.'); return; }
          if (joined) return; // reconexão: continua de onde está
          pos.set(e.x, 0, e.z); posY = e.y || 0; yaw = e.ry + Math.PI; hero = e.model;
          SIZE = sizeOf(e.model); EYE = SIZE > 1 ? 3.2 + SIZE * 0.35 : 1.8; SPEED = SIZE > 1 ? 6 : 4.2; BODY_R = SIZE > 1 ? SIZE * 0.8 : 0.45;
          if (lastBiome) atmosfera(lastBiome); // a luz depende do tamanho da criatura
          const mon = MONSTERS.find((x) => x.id === e.model);
          $('possuido-nome').textContent = mon ? mon.nome : e.model;
          $('possuido').hidden = false;
        }
        joined = true;
        session.myPos = pos;
        loadSelf(hero);
        updateFichaBtn();
        aplicaMesa();
        $('entrada').hidden = true; $('hud').hidden = false;
        if (!mobile) $('dica').textContent = 'W A S D: andar · Arraste o mouse: olhar · E: interagir';
      },
      frozen(on) { aviso(on ? 'O mestre pausou o movimento' : ''); },
      teleport(m) { pos.x = m.x; pos.z = m.z; if (m.y !== undefined) posY = m.y; },
      pteleport(m) { if (m.id === POSSESS) { pos.x = m.x; pos.z = m.z; if (m.y !== undefined) posY = m.y; } },
      ents(changed) {
        if (!POSSESS) return;
        const e = session.ents.get(POSSESS);
        if (!e) { if (joined) sair(); return; }
        e.hidden = true;
        // o mestre arrastou este monstro no mapa (os próprios passos não voltam do servidor)
        if (changed && changed.id === POSSESS && joined) { pos.x = changed.x; pos.z = changed.z; posY = changed.y || 0; }
      },
      oa: offerOpportunity,
      deny(msg) { toast(msg, 'neg'); },
      atmos: atmosfera,
      players: () => updateRevBtn(),
      combat: onCombat,
      fichas() { ficha.onServer(); updateFichaBtn(); luzTimer = 0; },
      mesa: () => { aplicaMesa(); luzTimer = 0; },
      rotas: () => mundo.onRotas(),
      ping(m) {
        mundo.onPing(m);
        if (m.leva && !mundo.visible) toast('O Mestre marcou um ponto no mapa do mundo', 'vez');
      },
      traco(m) { if (m.ctx === 'cena') tracoCena(m); else mundo.onTraco(m); },
      clog(e) {
        toast(logText(e), e.cid === myCid() ? 'vez' : '');
        if (e.cid === myCid() && selfChar && ACT_CLIPS[e.id]) selfChar.once(ACT_CLIPS[e.id]);
      },
      cfx(fx) {
        if (fx === 'start') { viewOverride = null; banner('start', 'COMBATE!', 'Role a iniciativa'); chime('start'); }
        if (fx === 'end') { viewOverride = null; closeSub(); banner('end', 'FIM DO COMBATE', ''); chime('end'); }
      },
      kicked() { aviso('O mestre removeu você da sessão. Recarregue a página para entrar de novo.'); joined = false; },
      status(ok) { if (joined) aviso(ok ? (session.frozen ? 'O mestre pausou o movimento' : '') : 'Reconectando…'); else if (!ok) { $('erro').hidden = false; $('erro').textContent = 'Não consegui conectar ao servidor. Tentando de novo…'; } },
    },
  });
  window.__session = session;
}
function aviso(txt) { $('aviso').hidden = !txt; $('aviso').textContent = txt; }
$('entrar').addEventListener('click', entrar);
// ---- botões de voo (celular): aparecem só para quem tem deslocamento de voo
function holdButton(el, on) {
  const down = (e) => { e.preventDefault(); on(true); el.classList.add('on'); el.setPointerCapture && el.setPointerCapture(e.pointerId); };
  const up = () => { on(false); el.classList.remove('on'); };
  el.addEventListener('pointerdown', down); el.addEventListener('pointerup', up); el.addEventListener('pointercancel', up); el.addEventListener('lostpointercapture', up);
}
holdButton($('voo-sobe'), (v) => { flyUp = v; });
holdButton($('voo-desce'), (v) => { flyDown = v; });
let flyShown = null, flyTxt = '';
function updateFlyPad(canFly) {
  if (canFly !== flyShown) {
    flyShown = canFly; $('voo').hidden = !canFly;
    if (canFly && joined) toast(`Você pode voar (${fmtM(flySpeed())}). ${POSSESS ? 'Espaço sobe, Shift desce.' : 'Segure ▲ para subir e ▼ para descer.'}`);
  }
  document.body.classList.toggle('em-combate', !!(session && session.combat.active));
  if (!canFly) return;
  const t = fmtM(Math.round(posY / M2U * 2) / 2);
  if (t !== flyTxt) { flyTxt = t; $('voo-alt').textContent = t; }
  $('voo').classList.toggle('no-ar', inAir());
}
// sair da visão do monstro: avisa a tela do mestre (que abriu esta numa moldura) para fazer a transição de volta
function sair() {
  if (window.parent !== window) window.parent.postMessage({ t: 'sair-visao' }, location.origin);
  else location.href = '/mestre';
}
$('possuido-sair').addEventListener('click', sair);
addEventListener('keydown', (e) => { if (POSSESS && e.code === 'Escape') sair(); });
if (POSSESS) { $('entrada').hidden = true; entrar(); }
$('nome').addEventListener('keydown', (e) => { if (e.key === 'Enter') entrar(); });

// ---------------------------------------------------------------- combate
const ordem = new TurnOrder($('ordem'), { gm: false, max: 7, collapsible: true });
const cmd = $('cmd');
let lastN = -1, turnUsed = 0, pending = {}, blockedHint = 0, endConfirm = 0;
const C = () => session.combat;
const meItem = () => C().list.find((x) => (POSSESS ? x.kind === 'monster' && x.ref === POSSESS : x.kind === 'player' && x.ref === session.myId));
const myCid = () => { const it = session && meItem(); return it ? it.cid : -1; };
const inFight = () => !!(session && C().active && meItem());
const myTurn = () => inFight() && C().cur && C().cur.cid === myCid();
const budgetNow = () => (C().cur ? (inAir() || flyUp ? C().cur.fbudget || 0 : C().cur.budget) : 0);
const remaining = () => (myTurn() ? Math.max(0, budgetNow() - turnUsed) : 0);
// custo em metros do início do turno até um ponto, em linha reta (terreno difícil conta dobrado; no ar, distância 3D)
function costFrom(sx, sy, sz, x, y, z) {
  const air = sy > 0.05 || y > 0.05;
  const d = Math.hypot(x - sx, z - sz, air ? y - sy : 0);
  if (air || d < 0.01 || !session.world) return d / M2U;
  const n = Math.max(1, Math.ceil(d / 0.25)); let c = 0;
  for (let i = 0; i < n; i++) { const k = (i + 0.5) / n; c += session.world.terrain.costAt(sx + (x - sx) * k, sz + (z - sz) * k); }
  return (d * c / n) / M2U;
}

function onCombat(c) {
  warmPortraits(c.list.map((x) => x.model)); // já na montagem do combate, antes de começar
  document.body.classList.toggle('combate', !!c.active);
  ordem.render(c, session.myId);
  if (!c.active) { lastN = -1; pending = {}; closeSub(); buildMenu(); return; }
  if (c.cur && c.cur.n !== lastN) {
    lastN = c.cur.n; pending = {}; endConfirm = 0; closeSub();
    if (myTurn()) {
      turnUsed = c.cur.used;
      banner('turn', 'SEU TURNO!', `${(meItem() || {}).name || ''} · ${fmtM(c.cur.budget)} de deslocamento`);
      chime('turn');
      try { navigator.vibrate && navigator.vibrate([90, 50, 160]); } catch {}
    } else {
      const it = c.list.find((x) => x.cid === c.cur.cid);
      toast(it ? `Turno de ${it.name}` : 'Turno de uma criatura', 'vez');
    }
  } else if (myTurn()) turnUsed = Math.min(turnUsed, c.cur.used + 0.05); // o servidor conta igual (distância do início)
  buildMenu();
}

function tile(cls, key, title, sub, onClick) {
  const b = document.createElement('button');
  b.className = 'tile ' + cls;
  b.innerHTML = '<span class="k"></span><span class="t"><b></b><small></small></span>';
  b.querySelector('.k').textContent = key; b.querySelector('b').textContent = title; b.querySelector('small').textContent = sub;
  b.onclick = onClick;
  return b;
}
function buildMenu() {
  cmd.innerHTML = '';
  if (!inFight()) { cmd.hidden = true; return; }
  cmd.hidden = false;
  const c = C(), me = meItem();
  const reacUsed = me.reac || pending.reaction;
  if (myTurn()) {
    const a = tile('t-acao', 'A', 'AÇÃO', 'Atacar, magia, disparada…', () => openSub('action'));
    if (c.cur.action || pending.action) a.classList.add('usada');
    const b = tile('bonus', 'B', 'AÇÃO BÔNUS', 'Ataque leve, poção…', () => openSub('bonus'));
    if (c.cur.bonus || pending.bonus) b.classList.add('usada');
    const r = tile('reacao', 'R', 'REAÇÃO', 'Uma por rodada', () => openSub('reaction'));
    if (reacUsed) r.classList.add('usada');
    // dois toques para passar a vez; o estado sobrevive ao menu ser redesenhado
    const confirming = performance.now() < endConfirm;
    const f = tile('fim' + (confirming ? ' confirmar' : ''), '▶', confirming ? 'CONFIRMAR?' : 'FIM DO TURNO', confirming ? 'Toque de novo para passar' : 'Passar a vez', () => {
      if (performance.now() < endConfirm) { endConfirm = 0; closeSub(); session.send({ t: 'end_turn', as: myCid() }); return; }
      endConfirm = performance.now() + 2600; buildMenu();
      setTimeout(() => { if (endConfirm && performance.now() >= endConfirm) { endConfirm = 0; buildMenu(); } }, 2700);
    });
    cmd.append(a, b, r, f);
  } else {
    const it = c.cur && c.list.find((x) => x.cid === c.cur.cid);
    const w = document.createElement('div'); w.className = 'cmd-wait';
    w.innerHTML = 'AGUARDANDO · <b></b>'; w.querySelector('b').textContent = it ? `Turno de ${it.name}` : 'Turno de uma criatura';
    const r = tile('reacao mini', 'R', 'REAÇÃO', reacUsed ? 'Já usada nesta rodada' : 'Ataque de oportunidade…', () => openSub('reaction'));
    if (reacUsed) r.classList.add('usada');
    cmd.append(w, r);
  }
}

let sub = null;
function closeSub() { if (sub) { sub.remove(); sub = null; } }
function subPanel(title, onBack) {
  closeSub();
  sub = document.createElement('div'); sub.className = 'sub';
  sub.innerHTML = '<div class="sub-top"><h3></h3><button class="voltar">◀ VOLTAR</button></div><div class="sub-grid"></div>';
  sub.querySelector('h3').textContent = title;
  sub.querySelector('.voltar').onclick = onBack || closeSub;
  document.body.appendChild(sub);
  return sub.querySelector('.sub-grid');
}
function openSub(slot) {
  castSpell = '';
  const grid = subPanel(SLOT_NOME[slot].toUpperCase());
  for (const a of ACTIONS[slot]) {
    if (a.so && !(myData() && a.so.includes(myData().hero))) continue;   // habilidade de um herói só
    if (a.so && myData() && myData().rev) continue;
    const b = document.createElement('button'); b.className = 'opt';
    b.innerHTML = '<b></b><small></small>'; b.querySelector('b').textContent = a.nome; b.querySelector('small').textContent = a.desc;
    b.onclick = () => (a.id === 'magic' || (a.id === 'spell' && slot === 'bonus') ? openArea({ slot, a }) : a.alvo ? openTargets(slot, a) : declare(slot, a, 0));   // magia: pergunta a área antes
    grid.appendChild(b);
  }
}
function openTargets(slot, a) {
  const grid = subPanel(a.nome.toUpperCase() + ' ▸ ALVO', () => openSub(slot));
  const mine = myCid();
  // inimigos primeiro; aliados depois (Ajudar mira aliados)
  const list = [...C().list].filter((x) => x.cid !== mine || a.id === 'potion' || a.id === 'spell' || a.id === 'magic')
    .sort((x, y) => (x.kind === y.kind ? 0 : (x.kind === 'monster') === (a.id !== 'help') ? -1 : 1));
  const melee = MELEE.has(a.id);
  if (melee) {
    const n = document.createElement('p'); n.className = 'sub-nota';
    n.textContent = 'Ataque básico: só alcança criaturas a até 1,5 m (um quadrado) de você.';
    grid.appendChild(n);
  }
  for (const it of list) {
    const b = document.createElement('button'); b.className = 'opt alvo ' + it.kind;
    const img = document.createElement('img'); img.alt = ''; setPortrait(img, it.model);
    const t = document.createElement('span'); t.className = 'alvo-txt';
    const nm = document.createElement('b'); nm.textContent = it.cid === mine ? 'Você' : it.name;
    const dist = it.cid === mine ? 0 : distTo(it);
    const d = document.createElement('small'); d.textContent = it.cid === mine ? '' : Number.isFinite(dist) ? fmtM(dist) : '';
    t.append(nm, d); b.append(img, t);
    if (melee && it.cid !== mine && !(dist <= REACH_OK)) {
      b.classList.add('longe'); d.textContent = `FORA DE ALCANCE · ${fmtM(dist)}`;
      b.onclick = () => toast(`${it.name} está a ${fmtM(dist)}. Chegue a 1,5 m para atacar.`, 'neg');
    } else b.onclick = () => declare(slot, a, it.cid);
    grid.appendChild(b);
  }
  if (a.alvo === 'opt') {
    const b = document.createElement('button'); b.className = 'opt';
    b.innerHTML = '<b>Sem alvo</b><small>Área, objeto ou outro</small>';
    b.onclick = () => declare(slot, a, 0);
    grid.appendChild(b);
  }
}
let castSpell = '';   // nome da magia escolhida no grimório (vai para o registro do combate)
let castSlot = 0;     // espaço de magia que a magia escolhida vai gastar (0 = truque ou sem ficha)
function declare(slot, a, target) {
  pending[slot] = true;
  session.send({ t: 'act', slot, id: a.id, target, as: myCid(), spell: castSpell || undefined });
  if (castSlot) ficha.gastar(castSlot);
  if (castSpell === 'Luz') session.send({ t: 'luz_pessoal', luz: 'luz' });
  if (castSpell === 'Luz do Dia') session.send({ t: 'luz_pessoal', luz: 'dia' });
  castSpell = ''; castSlot = 0;
  setTimeout(() => { if (pending[slot]) { pending[slot] = false; buildMenu(); } }, 1500); // se o servidor recusar, o botão volta
  closeSub(); buildMenu();
}

// ---- área de magia: escolher a forma e o tamanho, ir para a visão tática, posicionar com o dedo e confirmar
const groundY = (x, z) => (session && session.world && session.world.groundAt ? session.world.groundAt(x, z) : 0);
const myKey = () => (POSSESS ? 'm' + POSSESS : 'p' + (session ? session.myId : 0));
const areaTool = new AreaTool({
  scene, camera, canvas,
  caster: () => ({ x: pos.x, z: pos.z, y: groundY(pos.x, pos.z), half: SIZE, key: myKey(), yaw: yaw + Math.PI, camYaw: yaw }),
  ground: groundY,
  blockers: () => session.areaBlockers(groundY(pos.x, pos.z)),
  creatures: () => areaCreatures(session, { key: myKey(), x: pos.x, z: pos.z }),
  onChange: (a, hit) => {
    const box = $('tt-alvos'); box.textContent = '';
    for (const c of hit) { const s = document.createElement('span'); s.textContent = c.key === myKey() ? 'Você' : c.name; if (c.ally) s.className = 'aliado'; box.appendChild(s); }
  },
  onConfirm: (a, hit) => {
    $('tatico').hidden = true;
    const by = POSSESS ? (session.ents.get(POSSESS) ? (meItem() || {}).name || 'Monstro' : 'Monstro') : undefined;
    session.send({ t: 'aoe', area: { ...a, y: groundY(a.ox, a.oz) }, por: by });
    if (areaFrom) declare(areaFrom.slot, areaFrom.a, 0); else { if (castSlot) ficha.gastar(castSlot); castSpell = ''; castSlot = 0; }
    toast(`${a.nome || SHAPES[a.forma].nome}: área enviada ao mestre` + (hit.length ? ` · ${hit.length} na área` : ''));
    areaFrom = null;
  },
  onCancel: () => { castSpell = ''; castSlot = 0; $('tatico').hidden = true; if (areaFrom) { const f = areaFrom; areaFrom = null; buildMenu(); openSub(f.slot); } },
});
let areaFrom = null;   // {slot, a} quando a magia veio do menu de combate

// ---- régua: vai para a visão de cima e mede arrastando o dedo
let reguaSend = 0;
const regua = new ReguaTool({
  scene, camera, canvas,
  caster: () => ({ x: pos.x, z: pos.z, y: groundY(pos.x, pos.z), camYaw: yaw }),
  // o mestre e os outros jogadores veem a medição ao vivo
  onMeasure: (a, b) => {
    const now = performance.now(); if (now - reguaSend < 90) return; reguaSend = now;
    session.send({ t: 'traco', ctx: 'cena', tipo: 'regua', pts: [[a.x, a.z], [b.x, b.z]] });
  },
  onExit: () => { $('regua-hud').hidden = true; session.send({ t: 'traco', ctx: 'cena', tipo: 'regua', pts: [] }); },
});
// réguas dos outros na cena 3D
const tracosCena = new Map();
function tracoCena(m) {
  let t = tracosCena.get(m.id);
  if (!m.pts || m.pts.length < 2) { if (t) { t.draw.dispose(); t.label.el.remove(); tracosCena.delete(m.id); } return; }
  if (!t) { t = { draw: new RulerDraw(scene), label: makeLabel() }; t.label.el.classList.add('outro'); tracosCena.set(m.id, t); }
  t.draw.matDash.color.set(corDe(m.hero, m.id === 'gm')); t.label.el.style.borderColor = corDe(m.hero, m.id === 'gm');
  t.a = { x: m.pts[0][0], z: m.pts[0][1] }; t.b = { x: m.pts[1][0], z: m.pts[1][1] }; t.por = m.por;
  t.draw.set(t.a.x, t.a.z, t.b.x, t.b.z, groundY(t.a.x, t.a.z) + 0.07, 0.16);
}
function updateTracosCena() {
  for (const t of tracosCena.values()) {
    const sc = toScreen(t.draw.b, camera, canvas), v = t.draw.b.clone().project(camera);
    if (v.z > 1 || document.body.classList.contains('mesa-cobre')) { t.label.hide(); continue; }
    const med = medir(t.a.x, t.a.z, t.b.x, t.b.z);
    t.label.show({ ...med, txt: `${t.por}: ${med.txt}` }, sc);
  }
}

// ---- mesa: o mestre escolhe se os jogadores veem a cena 3D, o mapa do mundo ou uma imagem (teatro da mente)
const fichaNoMapa = document.createElement('button'); fichaNoMapa.className = 'mu-bt'; fichaNoMapa.innerHTML = '<i>📜</i><span>FICHA</span>';
fichaNoMapa.onclick = () => (ficha.isOpen ? ficha.close() : ficha.open());
const batalhaNoMapa = document.createElement('button'); batalhaNoMapa.className = 'mu-bt batalha'; batalhaNoMapa.innerHTML = '<i>⚔</i><span>BATALHA</span>'; batalhaNoMapa.title = 'Voltar para o mapa de batalha 3D';
const mundo = new MundoView($('mesa-mundo'), {
  role: 'player', send: (m) => session && session.send(m), session: () => session, toast,
  me: () => ({ nome: (myData() || {}).name || '', hero: (myData() || {}).hero || '' }), extras: [batalhaNoMapa, fichaNoMapa],
});
const imagem = new ImagemView($('mesa-imagem'));
// cada jogador pode trocar a própria tela: voltar à batalha 3D quando o mestre mostra o mapa ou uma imagem,
// ou abrir o mapa do mundo quando a mesa está na cena. Quando o mestre muda o modo, todos voltam a acompanhar.
let vistaLocal = null;   // null = acompanha a mesa; 'cena' ou 'mundo' = escolha do próprio jogador
let ultimoModo = '';
function aplicaMesa() {
  if (!joined || POSSESS || !session) return;
  const m = session.mesa || { modo: 'cena' };
  if (m.modo !== ultimoModo) { if (ultimoModo && m.modo !== 'cena') toast(m.modo === 'mundo' ? 'O Mestre abriu o mapa do mundo' : 'O Mestre está mostrando uma imagem', 'vez'); ultimoModo = m.modo; vistaLocal = null; }
  let modo = vistaLocal || m.modo;
  if (modo === 'imagem' && !m.imagem) modo = 'cena';
  if (modo === 'imagem') imagem.show(m.imagem, m.legenda); else imagem.hide();
  if (modo === 'mundo') mundo.show(); else mundo.hide();
  fichaNoMapa.hidden = !temFicha((myData() || {}).hero);
  $('btn-mapa').hidden = modo !== 'cena';
  const cobre = modo !== 'cena';
  document.body.classList.toggle('mesa-cobre', cobre);
  if (cobre) { if (regua.busy) regua.finish(); if (areaTool.busy) areaTool.finish(false); closeArea(); }
}
function verLocal(modo) { const base = (session.mesa || {}).modo || 'cena'; vistaLocal = modo === base ? null : modo; aplicaMesa(); }
$('btn-mapa').onclick = () => verLocal('mundo');
$('mesa-voltar').onclick = () => verLocal('cena');
batalhaNoMapa.onclick = () => verLocal('cena');
function openRegua() {
  if (areaTool.busy || regua.busy) return;
  closeArea(); closeSub(); ficha.close();
  moveTouch = null; lookTouch = null; move.x = move.y = 0; stick.hidden = true; flyUp = flyDown = false;
  $('regua-hud').hidden = false;
  regua.start();
}
$('btn-regua').onclick = openRegua;
$('rg-sair').onclick = () => regua.finish();
$('rg-mais').onclick = () => regua.zoomBy(1 / 1.25);
$('rg-menos').onclick = () => regua.zoomBy(1.25);

// ---- ficha do personagem (Guy, Kaira, Ghult'ok)
const ficha = new FichaUI({
  session: () => session, hero: () => (myData() || {}).hero || hero, inFight: () => inFight(), toast,
  luzAtual: () => minhaLuz(),
  setLuz: (tipo) => { session.send({ t: 'luz_pessoal', luz: tipo }); setTimeout(() => ficha.isOpen && ficha.render(), 250); },
  nome: () => (myData() || {}).name || hero,
});
function updateFichaBtn() {
  const d = myData(), ok = !POSSESS && !!d && temFicha(d.hero);
  $('btn-ficha').hidden = !ok;
}
$('btn-ficha').onclick = () => (ficha.isOpen ? ficha.close() : ficha.open());
const custom = { forma: 'esfera', tam: 6, alcance: 18, larg: 1.5 };
const m2txt = (v) => (v ? String(v).replace('.', ',') + ' m' : 'Pessoal');
function areaPanel(title) {
  $('ae-titulo').textContent = title; const body = $('ae-corpo'); body.textContent = ''; $('area-escolha').hidden = false;
  return body;
}
function closeArea() { $('area-escolha').hidden = true; }
$('ae-fechar').onclick = () => { closeArea(); if (areaFrom) { areaFrom = null; buildMenu(); } };
function openArea(from) {
  areaFrom = from || null; closeSub();
  const body = areaPanel('MAGIA ▸ ÁREA DE EFEITO');
  const opt = (icone, nome, desc, fn, cls = '') => {
    const b = document.createElement('button'); b.className = 'ae-op ' + cls;
    b.innerHTML = '<i></i><span><b></b><small></small></span>';
    b.querySelector('i').textContent = icone; b.querySelector('b').textContent = nome; b.querySelector('small').textContent = desc;
    b.onclick = fn; return b;
  };
  const sec = (t) => { const p = document.createElement('div'); p.className = 'ae-sec'; p.textContent = t; body.appendChild(p); const g = document.createElement('div'); g.className = 'ae-lista'; body.appendChild(g); return g; };
  const temF = !POSSESS && myData() && temFicha(myData().hero);
  if (areaFrom) {
    const g = sec(temF ? 'ITEM MÁGICO OU OUTRA FONTE · SEM ÁREA' : 'SEM ÁREA');
    g.appendChild(opt('◇', temF ? 'Item mágico (alvo único)' : 'Alvo único', temF ? 'Poção, varinha, pergaminho… (não gasta espaço)' : 'Escolher uma criatura (sem área)', () => { closeArea(); const f = areaFrom; areaFrom = null; castSlot = 0; openTargets(f.slot, f.a); }, 'unico'));
  }
  // grimório do personagem: com ficha, só o que ele pode conjurar (Guy: truques, preparadas e de domínio;
  // Kaira: até o círculo que o nível permite). Sem ficha (outros heróis), o grimório fixo de antes.
  const fx = !POSSESS && myData() && temFicha(myData().hero) ? ficha.f : null;
  const book = fx ? grimorio(fx) : !POSSESS && myData() && GRIMORIOS[myData().hero];
  if (book) {
    const tempo = areaFrom ? (areaFrom.slot === 'bonus' ? 'bonus' : 'action') : null;
    const quem = (myData().name || myData().hero).toUpperCase();
    if (fx && fx.hero === 'Guy' && !book.some((p) => p.circ > 0)) body.appendChild(Object.assign(document.createElement('p'), { className: 'ae-aviso', textContent: 'Nenhuma magia preparada. Abra a FICHA ▸ MAGIAS fora de combate para preparar.' }));
    for (let c = 0; c <= 9; c++) {
      // em combate, as de 1 minuto ou mais não cabem num turno; a área fora de combate só mostra as de área
      const list = book.filter((p) => p.circ === c && (!tempo || p.tempo === tempo) && (p.forma || areaFrom) && (!areaFrom || ['action', 'bonus', 'reaction'].includes(p.tempo)));
      if (!list.length) continue;
      const g = sec(`${fx && fx.hero === 'Guy' ? 'MAGIAS PREPARADAS' : 'FEITIÇOS'} DE ${quem} · ${c ? CIRC_NOME[c].toUpperCase() : 'TRUQUES'}`);
      for (const p of list) {
        const livre = fx && c > 0 ? [...Array(10 - c)].some((_, i) => slotsLivres(fx, c + i) > 0) : true;
        const ef = fx ? efeitoEm(p, c, fx.nivel) : p.efeito;
        const desc = (p.forma ? fmtArea(p) : p.alvo ? `alvo · alcance ${m2txt(p.alvo)}` : p.pessoal ? 'pessoal' : 'alvo · toque') + (ef ? ' · ' + ef : '') + (p.dominio ? ' · domínio' : '') + (p.conc ? ' · concentração' : '');
        const go = (slotLv) => {
          castSlot = slotLv || 0;
          if (p.forma) { castSpell = p.nome; beginArea({ ...p, cor: p.cor || 0xffe9a0 }); return; }
          closeArea(); const f = areaFrom; areaFrom = null; castSpell = p.nome; openTargets(f.slot, f.a);
        };
        const b = opt(p.forma ? SHAPES[p.forma].icone : '◇', p.nome, livre ? desc : 'SEM ESPAÇOS DE MAGIA · ' + desc, () => {
          if (!livre) { toast(`Sem espaços de magia do ${c}º círculo ou maior. Descanse para recuperar.`, 'neg'); return; }
          if (fx && c > 0) pickSlot(p, fx, go); else go(0);
        }, (p.forma ? '' : 'unico') + (livre ? '' : ' sem-espaco'));
        b.title = p.en; g.appendChild(b);
      }
    }
  }
  // quem tem ficha só conjura o próprio grimório; a área livre fica para item mágico ou outra fonte
  if (!fx) {
    const g1 = sec(book ? 'OUTRAS MAGIAS PRONTAS' : 'MAGIAS PRONTAS');
    for (const p of PRESETS) g1.appendChild(opt(SHAPES[p.forma].icone, p.nome, fmtArea(p), () => { castSpell = p.nome; castSlot = 0; beginArea(p); }));
  }
  const g2 = sec(fx ? 'ITEM MÁGICO OU OUTRA FONTE' : 'OUTRA MAGIA');
  g2.appendChild(opt('✎', 'Escolher forma e tamanho', 'Esfera, cone, cubo, cilindro, linha ou emanação', () => openCustom()));
}
// magia de 1º círculo ou mais: escolhe o espaço (o menor livre já vem marcado; maior = mais dano ou cura)
function pickSlot(p, fx, go) {
  const opts = [];
  for (let lv = p.circ; lv <= 9; lv++) if (slotsLivres(fx, lv) > 0) opts.push(lv);
  if (opts.length === 1) { go(opts[0]); return; }
  const body = areaPanel(`${p.nome.toUpperCase()} ▸ ESPAÇO DE MAGIA`);
  const g = document.createElement('div'); g.className = 'ae-lista'; body.appendChild(g);
  for (const lv of opts) {
    const b = document.createElement('button'); b.className = 'ae-op';
    b.innerHTML = '<i></i><span><b></b><small></small></span>';
    b.querySelector('i').textContent = lv; b.querySelector('b').textContent = `${lv}º círculo` + (lv > p.circ ? ' (elevado)' : '');
    b.querySelector('small').textContent = `${slotsLivres(fx, lv)} livre(s)` + (efeitoEm(p, lv, fx.nivel) ? ' · ' + efeitoEm(p, lv, fx.nivel) : '');
    b.onclick = () => go(lv);
    g.appendChild(b);
  }
}
function openCustom() {
  const body = areaPanel('ÁREA ▸ FORMA E TAMANHO');
  const pS = document.createElement('div'); pS.className = 'ae-sec'; pS.textContent = 'TIPO DE ÁREA'; body.appendChild(pS);
  const grid = document.createElement('div'); grid.className = 'ae-lista'; body.appendChild(grid);
  const DESC = { esfera: 'Raio a partir de um ponto', cilindro: 'Círculo de raio dado, com altura', cubo: 'Lado; sai de você ou à distância', cone: 'Sai de você numa direção', linha: 'Sai de você em linha reta', emanacao: 'Ao seu redor, vai com você' };
  for (const [id, s] of Object.entries(SHAPES)) {
    const b = document.createElement('button'); b.className = 'ae-op' + (custom.forma === id ? ' sel' : '');
    b.innerHTML = '<i></i><span><b></b><small></small></span>'; b.querySelector('i').textContent = s.icone; b.querySelector('b').textContent = s.nome; b.querySelector('small').textContent = DESC[id];
    b.onclick = () => { custom.forma = id; if (!s.placed) custom.alcance = 0; else if (!custom.alcance && s.placed === true) custom.alcance = 18; openCustom(); };
    grid.appendChild(b);
  }
  const s = SHAPES[custom.forma];
  const stepper = (label, key, step, min, max, fmt = m2txt) => {
    const row = document.createElement('div'); row.className = 'ae-num';
    const l = document.createElement('span'); l.textContent = label;
    const minus = document.createElement('button'); minus.textContent = '−';
    const v = document.createElement('b'); v.textContent = fmt(custom[key]);
    const plus = document.createElement('button'); plus.textContent = '+';
    const set = (n) => { custom[key] = Math.round(Math.max(min, Math.min(max, n)) * 10) / 10; v.textContent = fmt(custom[key]); };
    minus.onclick = () => set(custom[key] - (custom[key] > 30 ? step * 2 : step)); plus.onclick = () => set(custom[key] + (custom[key] >= 30 ? step * 2 : step));
    row.append(l, minus, v, plus); body.appendChild(row);
  };
  const pT = document.createElement('div'); pT.className = 'ae-sec'; pT.textContent = 'TAMANHO'; body.appendChild(pT);
  stepper(s.tam + (s.tam === 'Raio' || s.tam === 'Distância' ? '' : ''), 'tam', 1.5, 1.5, 90, (v) => m2txt(v));
  if (custom.forma === 'linha') stepper('Largura', 'larg', 1.5, 1.5, 9, (v) => m2txt(v));
  if (s.placed) stepper('Alcance (0 = sai de você)', 'alcance', 1.5, 0, 150);
  const go = document.createElement('button'); go.className = 'ae-ir'; go.textContent = 'POSICIONAR NO MAPA ▸';
  go.onclick = () => { castSlot = 0; beginArea({ nome: '', ...custom, alcance: s.placed ? custom.alcance : 0 }); };
  body.appendChild(go);
}
function beginArea(p) {
  closeArea();
  moveTouch = null; lookTouch = null; move.x = move.y = 0; stick.hidden = true; flyUp = flyDown = false;
  $('tt-nome').textContent = (p.nome || SHAPES[p.forma].nome).toUpperCase();
  $('tt-desc').textContent = fmtArea(p);
  $('tt-dica').textContent = SHAPES[p.forma].placed && p.alcance > 0 ? 'Arraste o dedo no mapa para posicionar a área (dentro do círculo de alcance)'
    : p.forma === 'emanacao' ? 'A emanação fica em volta de você' : 'Arraste o dedo para apontar a direção';
  $('tatico').hidden = false;
  areaTool.start(p);
}
$('tt-confirmar').onclick = () => areaTool.finish(true);
$('tt-cancelar').onclick = () => areaTool.finish(false);
$('tt-mais').onclick = () => areaTool.zoomBy(1 / 1.25);
$('tt-menos').onclick = () => areaTool.zoomBy(1.25);
$('btn-area').onclick = () => openArea(null);
addEventListener('keydown', (e) => {
  if (areaTool.phase === 'tatico' && e.code === 'Enter') areaTool.finish(true);
  if (areaTool.phase === 'tatico' && e.code === 'Escape') areaTool.finish(false);
  if (regua.phase === 'tatico' && e.code === 'Escape') regua.finish();
  if (joined && !POSSESS && e.code === 'KeyM' && !['INPUT', 'TEXTAREA', 'SELECT'].includes(e.target.tagName) && true) { verLocal(document.body.classList.contains('mesa-cobre') ? 'cena' : 'mundo'); }
  if (!document.body.classList.contains('mesa-cobre') && !areaTool.busy && !regua.busy && joined && !POSSESS && e.code === 'KeyR' && !['INPUT', 'TEXTAREA', 'SELECT'].includes(e.target.tagName) && !ficha.isOpen) openRegua();
});
// visão tática: neblina rala e câmera enxergando longe, para ver o mapa de cima
let tactK = 0, baseFog = null, baseFar = null;
function tacticalView(dt, on) {
  if (!on && tactK === 0) { baseFog = scene.fog ? scene.fog.density : null; baseFar = camera.far; return; }
  tactK = Math.max(0, Math.min(1, tactK + (on ? dt : -dt) * 1.6));
  if (scene.fog && baseFog !== null) scene.fog.density = baseFog * (1 - 0.92 * tactK);
  const far = baseFar + 500 * tactK; if (Math.abs(camera.far - far) > 0.5) { camera.far = far; camera.updateProjectionMatrix(); }
}

// ---- alcance (mesma conta do servidor): quadrados de borda a borda, diagonal vale 1
const MELEE = new Set(['attack', 'offhand', 'opportunity']);
const REACH_OK = 1.5 + 0.45;
function sizeOfItem(it) {
  if (it.kind === 'player') return 1;
  const e = session.ents.get(it.ref); return e ? sizeOf(e.data.model) : 1;
}
function distTo(it) {
  // posição que o servidor conhece (a do modelo na tela ainda pode estar deslizando até lá)
  const src = it.kind === 'player' ? session.players.get(it.ref) : session.ents.get(it.ref);
  const me = meItem(), p = src ? src.data : session.combatantPos(it);
  if (!me || !p) return Infinity;
  const cheb = Math.max(Math.abs(p.x - pos.x), Math.abs(p.z - pos.z));
  return Math.max(1.5, (cheb - (sizeOfItem(me) - 1) - (sizeOfItem(it) - 1)) / M2U);
}

// ---- ataque de oportunidade: alguém saiu do meu alcance
let oaBox = null;
function offerOpportunity(m) {
  if (m.cid !== myCid()) return;
  if (oaBox) oaBox.remove();
  chime('turn'); try { navigator.vibrate && navigator.vibrate([60, 40, 60]); } catch {}
  const box = document.createElement('div'); box.className = 'oa';
  box.innerHTML = '<div class="oa-tit">ATAQUE DE OPORTUNIDADE!</div><div class="oa-corpo"><img alt=""><p></p></div><div class="oa-bts"><button class="oa-sim">ATACAR</button><button class="oa-nao">DEIXAR PASSAR</button></div><i class="oa-tempo"></i>';
  setPortrait(box.querySelector('img'), m.model);
  box.querySelector('p').innerHTML = '';
  box.querySelector('p').append(Object.assign(document.createElement('b'), { textContent: m.name }), ' saiu do seu alcance. Gastar a reação para atacar?');
  const close = () => { if (oaBox === box) oaBox = null; box.remove(); };
  box.querySelector('.oa-sim').onclick = () => { pending.reaction = true; session.send({ t: 'act', slot: 'reaction', id: 'opportunity', target: m.target, as: m.cid }); close(); buildMenu(); };
  box.querySelector('.oa-nao').onclick = close;
  document.body.appendChild(box); oaBox = box;
  setTimeout(close, 15000);
}

function updateCombatHUD(dt, t) {
  const c = session.combat;
  // medidor e anel só no meu turno
  const mine = myTurn();
  $('mov').hidden = !mine;
  if (mine) {
    const left = remaining(), total = budgetNow();
    $('mov-n').textContent = fmtM(left);
    $('mov-de').textContent = `de ${fmtM(total)} · ${Math.floor(left / 1.5 + 1e-6)} quadr.`;
    $('mov-bar').style.width = (total > 0 ? (left / total) * 100 : 0) + '%';
    $('mov').classList.toggle('zero', left < 0.05);
    const dif = session.world && session.world.terrain.isDifficult(pos.x, pos.z);
    const tag = $('mov-tag');
    const air = inAir();
    tag.hidden = !(air || dif || c.cur.dash);
    tag.textContent = air ? 'VOANDO' : dif ? 'TERRENO DIFÍCIL ×2' : 'DISPARADA';
    tag.classList.toggle('dif', !air && !!dif);
    tag.classList.toggle('voo', air);
  }
  // o anel fica parado onde o turno começou, com o raio de todo o deslocamento: dentro dele, qualquer ponto vale
  ring.visible = mine;
  if (mine) { ring.userData.set(c.cur.sx, c.cur.sz, budgetNow() * M2U, dt, t); ring.position.y = (session.world && session.world.standAt ? session.world.standAt(c.cur.sx, c.cur.sz, SIZE) : 0) + 0.14; }
  startMark.visible = mine;
  if (mine) { startMark.position.set(c.cur.sx, (session.world && session.world.standAt ? session.world.standAt(c.cur.sx, c.cur.sz, SIZE) : 0) + 0.05, c.cur.sz); startMark.rotation.z = t * 0.6; }
  else ring.userData.r = 0;
  // marcador sobre quem está agindo
  const it = c.active && c.cur ? c.list.find((x) => x.cid === c.cur.cid) : null;
  const p = it ? session.combatantPos(it) : null;
  const showMark = !!p && !(mine && view() === '1p');
  turnMark.visible = showMark;
  if (showMark) { turnMark.position.set(p.x, 3.1 + Math.sin(t * 3) * 0.12, p.z); turnMark.rotation.y = t * 2; }
}

// câmera de ombro: recua quando há parede entre o personagem e a câmera
function hitT(px, pz, qx, qz, ax, az, bx, bz) {
  const rx = qx - px, rz = qz - pz, sx = bx - ax, sz = bz - az, den = rx * sz - rz * sx;
  if (Math.abs(den) < 1e-9) return 1;
  const t = ((ax - px) * sz - (az - pz) * sx) / den, u = ((ax - px) * rz - (az - pz) * rx) / den;
  return t >= 0 && t <= 1 && u >= 0 && u <= 1 ? t : 1;
}
const camT = new THREE.Vector3(), camP = new THREE.Vector3();
function thirdPerson(bob) {
  // personagem pequeno (halfling): câmera mais perto e mais baixa, na proporção da altura dos olhos
  const small = SIZE > 1 ? 1 : Math.max(0.68, Math.min(1.15, EYE / 1.8));   // halfling mais perto, orc um pouco mais longe
  const k = SIZE > 1 ? SIZE * 1.15 : small, D = 4.4 * k, SH = SIZE > 1 ? 0 : 1.05 * k;
  pitch = Math.max(-0.95, Math.min(0.3, pitch));
  // o alvo da câmera acompanha a altura do voo (antes ficava preso no chão)
  camT.set(pos.x, (SIZE > 1 ? 1.7 * k : 1.55 * k) + standY + posY - (inAir() ? 0 : sink) + bob, pos.z);
  const cp = Math.cos(pitch), fx = -Math.sin(yaw) * cp, fy = Math.sin(pitch), fz = -Math.cos(yaw) * cp;
  camP.set(camT.x - fx * D + Math.cos(yaw) * SH, camT.y - fy * D + 0.45, camT.z - fz * D - Math.sin(yaw) * SH);
  let tmin = 1;
  // criatura grande: a câmera fica acima das paredes (4 unidades), então não precisa recuar por causa delas
  if (SIZE > 1) camP.y = Math.max(camP.y, 7);
  // acima das paredes (câmera e personagem) não há o que atravessar
  const overWalls = camP.y > WALL_H + 0.6 && camT.y > WALL_H + 0.2;
  if (session.world && !overWalls) {
    for (const w of session.world.segments) tmin = Math.min(tmin, hitT(camT.x, camT.z, camP.x, camP.z, w.x1, w.z1, w.x2, w.z2));
    for (const d of session.world.doors) if (d.angle < 0.6) tmin = Math.min(tmin, hitT(camT.x, camT.z, camP.x, camP.z, d.x1, d.z1, d.x2, d.z2));
  }
  if (tmin < 1) {
    const full = camP.distanceTo(camT), k = Math.max(0.12, (tmin * full - 0.55) / full);
    camP.lerpVectors(camT, camP, k);
  }
  camP.y = Math.max(0.5, camP.y);
  camera.position.copy(camP);
  camera.rotation.set(pitch, yaw, 0);
  selfHolder.visible = camP.distanceTo(camT) > 1.1 * (SIZE > 1 ? SIZE : 1);
}

// ---------------------------------------------------------------- laço principal
const clock = new THREE.Timer();
let sendTimer = 0, last = '', sink = 0, standY = 0;
function frame() {
  requestAnimationFrame(frame);
  clock.update(); const dt = Math.min(clock.getDelta(), 0.25);
  if (joined && session) {
    let mx = move.x, my = move.y;
    if (keys.has('KeyW') || keys.has('ArrowUp')) my += 1;
    if (keys.has('KeyS') || keys.has('ArrowDown')) my -= 1;
    if (keys.has('KeyD')) mx += 1;
    if (keys.has('KeyA')) mx -= 1;
    if (keys.has('ArrowLeft')) yaw += dt * 2;
    if (keys.has('ArrowRight')) yaw -= dt * 2;
    const cobre = document.body.classList.contains('mesa-cobre');
    if (areaTool.busy || regua.busy || ficha.isOpen || cobre) { mx = my = 0; flyUp = flyDown = false; }   // posicionando a área: o personagem fica parado
    const len = Math.hypot(mx, my);
    if (len > 1) { mx /= len; my /= len; }
    // voo: espaço / botão ▲ sobe; shift, C ou botão ▼ desce
    const canFly = flySpeed() > 0;
    if (!canFly && posY > 0) posY = 0;
    const vy = canFly && !areaTool.busy && !regua.busy ? ((keys.has('Space') || flyUp ? 1 : 0) - (keys.has('ShiftLeft') || keys.has('ShiftRight') || keys.has('KeyC') || flyDown ? 1 : 0)) : 0;
    const climbs = (vy > 0 && posY < MAX_ALT) || (vy < 0 && posY > 0);
    const wants = (len > 0.08 || climbs) && (!session.frozen || !!POSSESS);
    // em combate só se anda no próprio turno, e até acabar o deslocamento
    const fight = inFight(), turn = myTurn();
    moving = wants && (!fight || (turn && remaining() > 0.01));
    if (wants && fight && !turn && performance.now() - blockedHint > 3000) { blockedHint = performance.now(); toast('Espere o seu turno para se mover'); }
    if (moving) {
      const sin = Math.sin(yaw), cos = Math.cos(yaw);
      // frente = -Z da câmera; direita = +X
      const dx = len > 0.08 ? -sin * my + cos * mx : 0, dz = len > 0.08 ? -cos * my - sin * mx : 0;
      if (len > 0.08) face = Math.atan2(dx, dz);
      const VS = SPEED * 0.75 * (climbs ? vy : 0);
      // em passos curtos, para não atravessar parede quando o aparelho engasga
      const slow = session.world ? session.world.terrain.slowAt(pos.x, pos.z) : 1; // água e lama atrasam
      for (let left = dt * slow; left > 0; left -= 0.04) {
        const step = Math.min(left, 0.04), px = pos.x, pz = pos.z, py = posY;
        pos.x += dx * SPEED * step;
        pos.z += dz * SPEED * step;
        posY = Math.max(0, Math.min(MAX_ALT, posY + VS * step / (posY > 0.05 || VS > 0 ? 1 : slow)));
        session.collide(pos, BODY_R, POSSESS, posY);
        if (turn) {
          // círculo de movimento: o gasto é a distância do ponto onde o turno começou (não o caminho andado).
          // Passando da borda, o personagem desliza ao longo dela (a posição é puxada de volta para o círculo).
          const cur = session.combat.cur, sy = cur.sy || 0;
          const air = py > 0.05 || posY > 0.05 || sy > 0.05;
          const budget = air ? cur.fbudget || 0 : cur.budget;
          const used = costFrom(cur.sx, sy, cur.sz, pos.x, posY, pos.z);
          if (used > budget && used > turnUsed + 1e-4) {
            let lo = 0, hi = 1;   // quanto do vetor início -> posição cabe no círculo (busca binária: o terreno difícil deforma o círculo)
            for (let i = 0; i < 14; i++) {
              const k = (lo + hi) / 2;
              if (costFrom(cur.sx, sy, cur.sz, cur.sx + (pos.x - cur.sx) * k, sy + (posY - sy) * k, cur.sz + (pos.z - cur.sz) * k) <= budget) lo = k; else hi = k;
            }
            pos.x = cur.sx + (pos.x - cur.sx) * lo; pos.z = cur.sz + (pos.z - cur.sz) * lo; posY = sy + (posY - sy) * lo;
            turnUsed = Math.max(turnUsed, budget); break;
          }
          turnUsed = used;
        }
      }
    }
    const bob = moving ? Math.sin(performance.now() / 110) * 0.035 : 0;
    // mapa com relevo: fica de pé na altura do chão (ou boiando na água funda); mapa plano: afunda um pouco na água
    standY += ((session.world && session.world.standAt ? session.world.standAt(pos.x, pos.z, SIZE) : 0) - standY) * Math.min(1, dt * 10);
    const wade = session.world && !session.world.cenario && session.world.terrain.charAt(pos.x, pos.z) === 'a' ? 0.3 : 0;
    sink += (wade - sink) * Math.min(1, dt * 5);
    const third = view() === '3p';
    $('vista').textContent = third ? '1ª PESSOA' : '3ª PESSOA';
    if (!third) face = yaw + Math.PI; // ao trocar para 3ª pessoa, o personagem olha para onde a câmera olhava
    if (third) thirdPerson(bob * 0.5);
    else {
      const fwd = SIZE > 1 ? SIZE * 1.3 : 0; // a cabeça do dragão fica bem à frente do centro
      camera.position.set(pos.x - Math.sin(yaw) * fwd, EYE + standY + posY + bob - sink, pos.z - Math.cos(yaw) * fwd); camera.rotation.set(pitch, yaw, 0); selfHolder.visible = false;
    }
    const tact = areaTool.apply(dt) || regua.apply(dt);
    if (tact) selfHolder.visible = true;
    tacticalView(dt, tact);
    // o personagem vira na direção em que anda
    let dr = face - selfHolder.rotation.y; dr = Math.atan2(Math.sin(dr), Math.cos(dr));
    selfHolder.rotation.y += dr * Math.min(1, dt * 12);
    const hover = inAir() && !(selfChar && selfChar.has('Fly')) ? Math.sin(performance.now() / 400) * 0.08 : 0; // quem não tem asas paira
    selfHolder.position.set(pos.x, standY + (inAir() ? posY + hover : -sink * 0.8), pos.z);
    if (selfChar) {
      const d = myData();
      const c = selfForm ? selfForm.update(dt, !!(d && d.rev) && inAir()) : selfChar;
      c.play(animFor(c, inAir(), moving && len > 0.08)); c.mixer.update(dt * (selfForm ? selfForm.timeScale : 1));
    }
    updateAirMark(selfAir, scene, pos.x, pos.z, posY, false, SIZE, standY);
    updateFlyPad(canFly);
    const showArea = !inFight() && !areaTool.busy && !regua.busy;   // fora de combate: botão para medir/lançar área; em combate vem pelo menu de magia
    if ($('btn-area').hidden === showArea) $('btn-area').hidden = !showArea;
    // em 3ª pessoa a tocha vai junto da câmera (luz de quem olha), para não estourar o personagem de perto
    if (SIZE > 1) torch.position.set(pos.x * 0.7 + camera.position.x * 0.3, 9 + standY + posY, pos.z * 0.7 + camera.position.z * 0.3);
    else if (third) torch.position.set(camera.position.x, camera.position.y + 0.4, camera.position.z);
    else torch.position.set(pos.x, EYE + standY + 0.3, pos.z);

    alvo = posY < 1 ? session.nearestDoor(pos) : null;
    const btn = $('interagir');
    btn.hidden = !alvo;
    if (alvo) btn.textContent = alvo.closed ? 'Abrir porta' : 'Fechar porta';

    sendTimer -= dt;
    if (sendTimer <= 0) {
      sendTimer = 0.1;
      // o modelo olha para +Z; a câmera olha para -Z
      const ry = third ? selfHolder.rotation.y : yaw + Math.PI;
      const s = `${pos.x.toFixed(2)},${pos.z.toFixed(2)},${posY.toFixed(2)},${ry.toFixed(2)},${moving ? 1 : 0}`;
      const mv = moving && len > 0.08 ? 1 : 0; // subir/descer parado não é "andar" (o modelo bate asas no lugar)
      if (s !== last) { last = s; session.send(POSSESS ? { t: 'pmove', id: POSSESS, x: pos.x, z: pos.z, y: posY, ry, mv } : { t: 'move', x: pos.x, z: pos.z, y: posY, ry, mv }); }
    }
    if (POSSESS) { const e = session.ents.get(POSSESS); if (e) { e.hidden = true; e.holder.position.set(pos.x, posY, pos.z); } }
    session.update(dt, pos);
    tickLuzes(performance.now() / 1000);
    atualizaLuz(dt);
    updateCombatHUD(dt, performance.now() / 1000);
    updateTracosCena();
    sky.position.copy(camera.position);
    updateMotes(dt, performance.now() / 1000);
  }
  // com o mapa do mundo ou uma imagem cobrindo a tela, a cena 3D não precisa ser desenhada (poupa a bateria)
  if (!document.body.classList.contains('mesa-cobre')) {
    const hora = horaAtual();
    if (session && session.world) night.render(scene, camera, hora, lightmap, { amb: 0.022, dv: hora === 'noite' && visaoNoEscuro() > 0 });
    else renderer.render(scene, camera);
  }
}
frame();
window.__dbg = { gl: renderer, area: areaTool, regua, ficha, mundo, imagem, lightmap, night, openArea, form: () => selfForm, posY: () => posY, flySpeed: () => flySpeed(), pos, setYaw: (v) => { yaw = v; }, setPitch: (v) => { pitch = v; }, turnUsed: () => turnUsed, view, cam: camera, self: selfHolder, torch, scene, hemi, size: () => SIZE, biome: () => lastBiome };
