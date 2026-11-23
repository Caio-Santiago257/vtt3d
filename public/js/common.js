// Código compartilhado entre a tela do mestre e a do jogador:
// carregamento dos modelos, construção do mapa 3D, entidades e rede.
import { buildCenario } from './cenario.js';
import { buildMesh as buildAreaMesh, disposeMesh as disposeAreaMesh, hits as areaHits, visibleParts } from './area.js';
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import * as SkeletonUtils from 'three/addons/utils/SkeletonUtils.js';
import { Terrain, biomeById } from './terreno.js';
import { toon, toonSoft, toonAnime, addRimSpec, addOutline, glowTexture, wind } from './gfx.js';

export const G = 2;            // unidades de mundo por quadrado do grid
export const WALL_H = 4;       // altura das paredes do kit
export const WALL_HALF = 0.5;  // meia espessura da parede

// ---------------------------------------------------------------- catálogo
// url e scale: assets novos ficam em /assets/<categoria>/ e são exportados em metros (1 m = 4/3 de unidade)
export const M = 4 / 3;
export const HEROES = [
  { id: 'Kaira', nome: 'Kaira', url: '/assets/characters/kaira/char_kaira_modelo.glb', scale: M, hide: [] },
  // Guy: halfling clérigo, com 1 m de altura (os olhos da câmera em 1ª pessoa ficam mais baixos)
  // Ghult'ok: orc bárbaro, 2,1 m (olhos mais altos)
  { id: 'Ghultok', nome: "Ghult'ok", url: '/assets/characters/ghultok/char_ghultok.glb', scale: M, hide: [], eye: 2.05 },
  { id: 'Guy', nome: 'Guy', url: '/assets/characters/guy/char_guy.glb', scale: M, hide: [], eye: 1.15 },
  { id: 'Knight', nome: 'Cavaleiro', hide: ['1H_Sword_Offhand', 'Badge_Shield', 'Rectangle_Shield', 'Spike_Shield', '2H_Sword'] },
  { id: 'Barbarian', nome: 'Bárbaro', hide: ['1H_Axe_Offhand', 'Barbarian_Round_Shield', '1H_Axe', 'Mug'] },
  { id: 'Mage', nome: 'Mago', hide: ['Spellbook', 'Spellbook_open', '1H_Wand'] },
  { id: 'Rogue', nome: 'Ladino', hide: ['Knife_Offhand', '1H_Crossbow', '2H_Crossbow', 'Throwable'] },
  { id: 'Rogue_Hooded', nome: 'Ladino encapuzado', hide: ['Knife_Offhand', '1H_Crossbow', '2H_Crossbow', 'Throwable'] },
];
export const MONSTERS = [
  // size: quantos quadrados o monstro ocupa de cada lado (Enorme = 3); o servidor lê o mesmo número do manifest
  { id: 'Dragao_Negro', nome: 'Dragão do Véu Corrompido', url: '/assets/characters/dragao_negro/char_dragao_negro.glb', scale: M, size: 3, fly: 24 },
  // Kobold: Pequeno, 1,2 m; pernas digitígradas e cauda (fontes/blender/kobold_*.py)
  { id: 'Kobold', nome: 'Kobold', url: '/assets/characters/kobold/char_kobold.glb', scale: M },
  { id: 'Skeleton_Warrior', nome: 'Esqueleto guerreiro' },
  { id: 'Skeleton_Minion', nome: 'Esqueleto lacaio' },
  { id: 'Skeleton_Rogue', nome: 'Esqueleto ladino' },
  { id: 'Skeleton_Mage', nome: 'Esqueleto mago' },
];
export const PROPS = [
  { id: 'table_medium', nome: 'Mesa', r: 1.1 }, { id: 'table_long', nome: 'Mesa longa', r: 1.2 },
  { id: 'chair', nome: 'Cadeira', r: 0.5 }, { id: 'stool', nome: 'Banco', r: 0.4 },
  { id: 'barrel_large', nome: 'Barril grande', r: 0.9 }, { id: 'barrel_small', nome: 'Barril pequeno', r: 0.6 },
  { id: 'crates_stacked', nome: 'Caixotes', r: 1.0 }, { id: 'box_large', nome: 'Caixa', r: 0.8 },
  { id: 'chest', nome: 'Baú', r: 0.9 }, { id: 'chest_gold', nome: 'Baú com ouro', r: 0.9 },
  { id: 'bed_floor', nome: 'Cama de chão', r: 0.9 }, { id: 'bed_decorated', nome: 'Cama', r: 1.2 },
  { id: 'shelf_large', nome: 'Estante', r: 0.9 }, { id: 'keg', nome: 'Tonel', r: 0.8 },
  { id: 'pillar', nome: 'Pilar', r: 0.8 }, { id: 'column', nome: 'Coluna baixa', r: 0.4 },
  { id: 'rubble_large', nome: 'Entulho', r: 1.0 }, { id: 'torch_lit', nome: 'Tocha', r: 0.2 },
  { id: 'coin_stack_large', nome: 'Pilha de moedas', r: 0.4 }, { id: 'sword_shield', nome: 'Espada e escudo', r: 0.5 },
  { id: 'stairs', nome: 'Escada', r: 1.5 }, { id: 'banner_red', nome: 'Estandarte', r: 0.3 },
];
const COVER = new Set(['barrel_large', 'barrel_small', 'crates_stacked', 'box_large', 'shelf_large', 'keg', 'pillar', 'rubble_large']);
// versões alternativas que só aparecem na galeria (não na escolha de personagem)
export const ALT_CHARS = [
  { id: 'Kaira_script', nome: 'Kaira (feita por script)', url: '/assets/characters/kaira/char_kaira_script.glb', scale: M },
  { id: 'Kaira_Asas', nome: 'Kaira com asas (Revelação Celestial)', url: '/assets/characters/kaira/char_kaira_asas.glb', scale: M },
];
// quantos quadrados a criatura ocupa de cada lado (Média = 1, Enorme = 3)
export const sizeOf = (model) => { const m = MONSTERS.find((x) => x.id === model); return (m && m.size) || 1; };
const findChar = (id) => HEROES.find((h) => h.id === id) || MONSTERS.find((m) => m.id === id) || ALT_CHARS.find((a) => a.id === id);
const CHAR_URL = (id) => {
  const e = findChar(id);
  return e && e.url ? e.url : `/assets/legacy/kaykit/chars/${id}.glb`;
};
const CHAR_SCALE = (id) => { const e = findChar(id); return (e && e.scale) || 1; };
// nomes de animação padronizados nos assets novos; os antigos continuam funcionando
export const ACT_CLIPS = {
  attack: ['1H_Melee_Attack_Chop', 'Spellcast_Shoot'], offhand: ['1H_Melee_Attack_Chop', 'Spellcast_Shoot'], opportunity: ['1H_Melee_Attack_Chop', 'Spellcast_Shoot'],
  magic: ['Spellcast_Shoot'], spell: ['Spellcast_Shoot'],
};
const CLIP_ALIAS = {
  Fly: 'fly', Fly_Idle: 'fly_idle', Idle_Air: 'fly_idle', Idle: 'idle', Walking_A: 'walk', Running_A: 'run', Hit_A: 'hit', Death_A: 'death', Spellcast_Shoot: 'cast', '1H_Melee_Attack_Chop': 'attack' };
const propRadius = (id) => (PROPS.find((p) => p.id === id) || { r: 0.7 }).r;

// ---------------------------------------------------------------- modelos
const loader = new GLTFLoader();
const cache = new Map();
export function loadGLB(url) {
  if (!cache.has(url)) cache.set(url, loader.loadAsync(url));
  return cache.get(url);
}
const matCache = new Map();
// Material em faixas de luz (estilo anime) no lugar do PBR do arquivo; também é mais leve em celular.
// Aproveita do arquivo: cor, textura, normal map, emissão, transparência e lado duplo.
// Propriedades extras gravadas no material do GLB (extras): ramp 'soft', rim, spec, specSize, noOutline.
function lambert(src) {
  if (!matCache.has(src)) {
    const ex = src.userData || {};
    const o = { map: src.map || null, color: src.color ? src.color.clone() : 0xffffff, side: src.side };
    if (src.normalMap) { o.normalMap = src.normalMap; o.normalScale = src.normalScale.clone(); }
    if (src.emissiveMap || (src.emissive && src.emissive.getHex())) { o.emissive = src.emissive.clone(); o.emissiveMap = src.emissiveMap || null; o.emissiveIntensity = src.emissiveIntensity; }
    if (src.transparent) { o.transparent = true; o.opacity = src.opacity; o.depthWrite = false; }
    if (src.alphaTest) o.alphaTest = src.alphaTest;
    if (src.vertexColors) o.vertexColors = true;
    const m = (ex.ramp === 'anime' ? toonAnime : ex.ramp === 'soft' ? toonSoft : toon)(o);
    addRimSpec(m, { rim: ex.rim || 0, spec: ex.spec || 0, specSize: ex.specSize || 0.9 });
    m.userData.noOutline = !!ex.noOutline || !!src.transparent || !!src.alphaTest;
    if (ex.outline) m.userData.outline = ex.outline;
    m.name = src.name;
    matCache.set(src, m);
  }
  return matCache.get(src);
}
function simplify(root) {
  root.traverse((o) => {
    if (o.isMesh) {
      o.material = Array.isArray(o.material) ? o.material.map(lambert) : lambert(o.material);
      o.frustumCulled = !o.isSkinnedMesh; // esqueleto animado sai da caixa original
    }
  });
  return root;
}

let _Celestial = null;   // revelacao.js importa este módulo; carrega sob demanda para não criar ciclo
export async function makeCharacter(model) {
  const gltf = await loadGLB(CHAR_URL(model));
  const obj = simplify(SkeletonUtils.clone(gltf.scene));
  obj.scale.multiplyScalar(CHAR_SCALE(model));
  const hero = HEROES.find((h) => h.id === model);
  if (hero) obj.traverse((o) => { if (hero.hide.includes(o.name)) o.visible = false; });
  addOutline(obj);
  const mixer = new THREE.AnimationMixer(obj);
  let current = null, currentName = '', locked = false, wanted = 'Idle';
  const find = (n) => THREE.AnimationClip.findByName(gltf.animations, n) || THREE.AnimationClip.findByName(gltf.animations, CLIP_ALIAS[n] || '');
  function play(name) {
    wanted = name;
    if (locked || name === currentName) return;
    const clip = find(name) || find('Idle');
    if (!clip) return;
    const next = mixer.clipAction(clip);
    next.reset().play();
    if (current) current.crossFadeTo(next, 0.25, false);
    current = next; currentName = name;
  }
  // toca um clipe uma vez (ataque, magia, dano) e volta ao que o jogo pedir depois; com hold, fica parado no fim (morte)
  function once(names, hold = false) {
    const clip = [].concat(names).map(find).find(Boolean);
    if (!clip) return false;
    const next = mixer.clipAction(clip);
    next.reset(); next.setLoop(THREE.LoopOnce, 1); next.clampWhenFinished = true; next.play();
    if (current && current !== next) current.crossFadeTo(next, 0.15, false);
    current = next; currentName = clip.name; locked = true;
    if (!hold) {
      const done = (ev) => {
        if (ev.action !== next) return;
        mixer.removeEventListener('finished', done);
        locked = false; const w = wanted; currentName = ''; play(w);
      };
      mixer.addEventListener('finished', done);
    }
    return true;
  }
  play('Idle');
  mixer.update(Math.random() * 3); // dessincroniza os idles
  return { obj, mixer, play, once, has: (n) => !!find(n), clips: gltf.animations.map((a) => a.name) };
}

export async function makeProp(model) {
  const gltf = await loadGLB(`/assets/legacy/kaykit/dungeon/${model}.glb`);
  return simplify(gltf.scene.clone(true));
}

export function makeLabel(text, color = '#ffffff') {
  const c = document.createElement('canvas');
  c.width = 256; c.height = 64;
  const g = c.getContext('2d');
  g.font = 'bold 30px system-ui, sans-serif';
  g.textAlign = 'center'; g.textBaseline = 'middle';
  g.lineWidth = 6; g.strokeStyle = 'rgba(0,0,0,.85)';
  g.strokeText(text, 128, 32); g.fillStyle = color; g.fillText(text, 128, 32);
  const tex = new THREE.CanvasTexture(c);
  tex.colorSpace = THREE.SRGBColorSpace;
  const s = new THREE.Sprite(new THREE.SpriteMaterial({ map: tex, depthTest: false, fog: false, transparent: true }));
  s.scale.set(3, 0.75, 1);
  s.renderOrder = 10;
  return s;
}

// animação conforme o estado: no ar usa os clipes de voo, se o modelo tiver (o dragão tem); sem eles, paira parado
export function animFor(c, air, moving) {
  if (air) return c.has('Fly') ? (moving ? 'Fly' : 'Fly_Idle') : 'Idle';
  return moving ? 'Walking_A' : 'Idle';
}

// marca de quem está voando: sombra no chão, fio até o corpo e, na tela do mestre, a altura em metros
const AIR_SHADOW = new THREE.MeshBasicMaterial({ color: 0x000000, transparent: true, opacity: 0.35, depthWrite: false });
const AIR_LINE = new THREE.MeshBasicMaterial({ color: 0x9fe8ff, transparent: true, opacity: 0.55, depthWrite: false });
function makeAirMark(size = 1) {
  const g = new THREE.Group();
  const sh = new THREE.Mesh(new THREE.CircleGeometry(size > 1 ? size * 0.9 : 0.7, 28), AIR_SHADOW);
  sh.rotation.x = -Math.PI / 2; sh.position.y = 0.04; g.add(sh);
  const line = new THREE.Mesh(new THREE.CylinderGeometry(0.035, 0.035, 1, 6), AIR_LINE);
  line.position.y = 0.5; g.add(line);
  g.userData = { line, shadow: sh, label: null, txt: '' };
  return g;
}
export function updateAirMark(owner, scene, x, z, alt, topDown, size, gy = 0) {
  const on = alt > 0.15;
  if (!owner.air && !on) return;
  if (!owner.air) { owner.air = makeAirMark(size); scene.add(owner.air); }
  const m = owner.air, u = m.userData;
  m.visible = on; if (!on) return;
  m.position.set(x, gy, z);
  u.line.visible = !topDown; u.line.scale.y = Math.max(0.01, alt); u.line.position.y = alt / 2;
  u.shadow.material.opacity = 0.35;
  const txt = '▲ ' + (Math.round((alt / (4 / 3)) * 2) / 2).toLocaleString('pt-BR') + ' m';
  if (txt !== u.txt) {
    u.txt = txt;
    if (u.label) { u.label.material.map.dispose(); u.label.removeFromParent(); }
    u.label = makeLabel(txt, '#9fe8ff'); m.add(u.label);
  }
  u.label.position.y = topDown ? 6.2 : alt + 0.4;
  u.label.scale.set(topDown ? 4.2 : 2.4, topDown ? 1.05 : 0.6, 1);
}

// ---------------------------------------------------------------- mapa 3D
class Kit {
  constructor() { this.batches = new Map(); }
  add(name, matrix) {
    if (!this.batches.has(name)) this.batches.set(name, []);
    this.batches.get(name).push(matrix.clone());
  }
  async flush(group) {
    const tmp = new THREE.Matrix4();
    await Promise.all([...this.batches].map(async ([name, mats]) => {
      const gltf = await loadGLB(`/assets/legacy/kaykit/dungeon/${name}.glb`);
      gltf.scene.updateMatrixWorld(true);
      gltf.scene.traverse((o) => {
        if (!o.isMesh) return;
        const im = new THREE.InstancedMesh(o.geometry, lambert(o.material), mats.length);
        mats.forEach((m, i) => im.setMatrixAt(i, tmp.multiplyMatrices(m, o.matrixWorld)));
        im.instanceMatrix.needsUpdate = true;
        group.add(im);
      });
    }));
  }
}

function mulberry(seed) {
  let a = seed >>> 0;
  return () => { a = (a + 0x6d2b79f5) >>> 0; let t = a; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
}

const _p = new THREE.Vector3(), _q = new THREE.Quaternion(), _s = new THREE.Vector3(), _m = new THREE.Matrix4();
const Y = new THREE.Vector3(0, 1, 0);
function trs(x, y, z, ry, sx = 1, sy = 1, sz = 1) {
  return _m.compose(_p.set(x, y, z), _q.setFromAxisAngle(Y, ry), _s.set(sx, sy, sz));
}

// Constrói o cenário a partir do mapa normalizado pelo servidor.
// Retorna { group, segments, doors, lights, bounds }.
export async function buildWorld(map, { topDown = false } = {}) {
  // mapa pronto com relevo: o cenário inteiro vem pronto da pasta do mapa
  if (map.cenario) {
    const c = await buildCenario(map, { topDown });
    const lights = (map.lights || []).map((l) => ({ x: l.x * G, z: l.y * G, y: c.groundAt(l.x * G, l.y * G) + 2.2, color: new THREE.Color(l.color), range: Math.max(6, l.range * G), intensity: l.intensity }));
    return { ...c, lights, imageFloor: false };
  }
  const group = new THREE.Group();
  const kit = new Kit();
  const rnd = mulberry(1234);
  const W = map.w * G, H = map.h * G;

  // ---- paredes: cada trecho é preenchido com peças do kit esticadas para caber
  const segments = [];
  const verts = new Map();
  const vkey = (x, z) => `${Math.round(x * 20)},${Math.round(z * 20)}`;
  const addVert = (x, z, dx, dz) => {
    const k = vkey(x, z);
    if (!verts.has(k)) verts.set(k, { x, z, dirs: [] });
    verts.get(k).dirs.push([dx, dz]);
  };
  for (const w of map.walls) {
    const x1 = w[0] * G, z1 = w[1] * G, x2 = w[2] * G, z2 = w[3] * G;
    const L = Math.hypot(x2 - x1, z2 - z1);
    if (L < 0.05) continue;
    segments.push({ x1, z1, x2, z2 });
    const dx = (x2 - x1) / L, dz = (z2 - z1) / L;
    addVert(x1, z1, dx, dz); addVert(x2, z2, -dx, -dz);
    const ry = -Math.atan2(dz, dx);
    const halves = Math.max(1, Math.round(L / 2));
    const s = L / (halves * 2);
    let done = 0; // em "metades" (2 unidades cada)
    while (done < halves) {
      if (halves - done >= 2) {
        const c = (done + 1) * 2 * s; // centro da peça inteira
        kit.add(rnd() < 0.1 ? 'wall_cracked' : 'wall', trs(x1 + dx * c, 0, z1 + dz * c, ry, s));
        done += 2;
      } else {
        const a = done * 2 * s; // a meia parede começa na origem e segue em +x
        kit.add('wall_half', trs(x1 + dx * a, 0, z1 + dz * a, ry, s));
        done += 1;
      }
    }
  }
  // pilares nas pontas e quinas, para esconder as emendas
  for (const v of verts.values()) {
    let need = v.dirs.length !== 2;
    if (!need) {
      const [a, b] = v.dirs;
      need = Math.abs(a[0] * b[1] - a[1] * b[0]) > 0.3 || a[0] * b[0] + a[1] * b[1] > 0;
    }
    if (need) kit.add('pillar', trs(v.x, 0, v.z, 0, 0.8, 1, 0.8));
  }

  // ---- chão: o terreno pintável cuida do piso; aqui só a imagem do mapa, quando o mestre escolhe usá-la
  const imageFloor = map.floorMode === 'image' && map.hasImage;
  if (imageFloor) {
    const tex = await new THREE.TextureLoader().loadAsync('/api/map-image?v=' + map.version);
    tex.colorSpace = THREE.SRGBColorSpace; tex.anisotropy = 4;
    const floor = new THREE.Mesh(new THREE.PlaneGeometry(W, H), new THREE.MeshLambertMaterial({ map: tex }));
    floor.rotation.x = -Math.PI / 2; floor.position.set(W / 2, 0.05, H / 2);
    group.add(floor);
  }
  await kit.flush(group);

  // ---- portas
  const doorGltf = await loadGLB('/assets/legacy/kaykit/dungeon/wall_doorway.glb');
  let doorSrc = null;
  doorGltf.scene.traverse((o) => { if (o.name === 'wall_doorway_door') doorSrc = o; });
  const doorBox = new THREE.Box3();
  if (doorSrc) {
    const probe = doorSrc.clone(true); probe.position.set(0, 0, 0); probe.rotation.set(0, 0, 0); probe.updateMatrixWorld(true);
    doorBox.setFromObject(probe);
  }
  const stone = new THREE.MeshLambertMaterial({ color: 0x5d6068 });
  const doors = map.doors.map((d, i) => {
    const x1 = d.x1 * G, z1 = d.y1 * G, x2 = d.x2 * G, z2 = d.y2 * G;
    const L = Math.hypot(x2 - x1, z2 - z1) || 1;
    const dx = (x2 - x1) / L, dz = (z2 - z1) / L;
    const pivot = new THREE.Group();
    pivot.position.set(x1, 0, z1);
    const base = -Math.atan2(dz, dx);
    pivot.rotation.y = base;
    const DOOR_H = 3;
    if (doorSrc) {
      const leaf = simplify(doorSrc.clone(true));
      leaf.rotation.set(0, 0, 0);
      const dw = doorBox.max.x - doorBox.min.x || 1, dh = doorBox.max.y - doorBox.min.y || 1;
      const sx = L / dw;
      leaf.scale.set(sx, DOOR_H / dh, 1);
      leaf.position.set(-doorBox.min.x * sx, -doorBox.min.y * (DOOR_H / dh), 0);
      pivot.add(leaf);
    }
    // verga de pedra sobre a porta
    const lintel = new THREE.Mesh(new THREE.BoxGeometry(L, WALL_H - DOOR_H, 1), stone);
    lintel.position.set((x1 + x2) / 2, DOOR_H + (WALL_H - DOOR_H) / 2, (z1 + z2) / 2);
    lintel.rotation.y = base;
    group.add(pivot, lintel);
    return { i, x1, z1, x2, z2, mx: (x1 + x2) / 2, mz: (z1 + z2) / 2, pivot, base, closed: true, angle: 0 };
  });

  // ---- luzes do mapa: uma chama visível para cada uma; as luzes de verdade vêm de um conjunto fixo
  const lights = map.lights.map((l) => ({ x: l.x * G, z: l.y * G, color: new THREE.Color(l.color), range: Math.max(6, l.range * G), intensity: l.intensity }));
  if (lights.length && !topDown) {
    const flames = new THREE.InstancedMesh(new THREE.SphereGeometry(0.14, 8, 6), new THREE.MeshBasicMaterial({ fog: false }), lights.length);
    lights.forEach((l, i) => { flames.setMatrixAt(i, trs(l.x, 2.6, l.z, 0)); flames.setColorAt(i, l.color); });
    group.add(flames);
    for (const l of lights) { // halo em volta de cada chama
      const halo = new THREE.Sprite(new THREE.SpriteMaterial({ map: glowTexture(), color: l.color, blending: THREE.AdditiveBlending, depthWrite: false, transparent: true, opacity: 0.8 }));
      halo.position.set(l.x, 2.6, l.z); halo.scale.setScalar(2.6); group.add(halo);
    }
  }
  // ---- terreno
  const tilePiece = async (name) => {
    const gltf = await loadGLB(`/assets/legacy/kaykit/dungeon/${name}.glb`);
    gltf.scene.updateMatrixWorld(true);
    let found = null;
    gltf.scene.traverse((o) => { if (o.isMesh && !found) found = { geometry: o.geometry, material: lambert(o.material), matrix: o.matrixWorld.clone() }; });
    return found;
  };
  const tiles = { large: await tilePiece('floor_tile_large'), small: await tilePiece('floor_tile_small') };
  const terrain = new Terrain({ W: Math.ceil(map.w), H: Math.ceil(map.h), segments, doors, topDown, tiles });
  const tr = map.terrain || {};
  terrain.set(tr.cells, tr.biome, { imageFloor, spawn: map.spawn });
  group.add(terrain.group);
  return { group, segments, doors, lights, terrain, imageFloor, bounds: { w: W, h: H }, groundAt: () => 0, standAt: () => 0, waterAt: () => -Infinity };
}

export function disposeGroup(group) {
  group.traverse((o) => {
    if (o.isInstancedMesh) o.dispose();
    if (o.geometry && (o.geometry.type === 'PlaneGeometry' || o.geometry.type === 'BoxGeometry' || o.geometry.type === 'SphereGeometry')) o.geometry.dispose();
  });
  group.removeFromParent();
}

// ---------------------------------------------------------------- sessão
// Mantém a cena sincronizada com o servidor (mapa, portas, monstros, objetos, jogadores).
// criaturas no mapa para as áreas de magia (self: posição local de quem está jogando, mais nova que a do servidor)
export function areaCreatures(s, self) {
  const out = [];
  for (const p of s.players.values()) {
    const d = p.data; if (d.off) continue;
    const me = self && self.key === 'p' + d.id;
    out.push({ key: 'p' + d.id, name: d.name, x: me ? self.x : d.x, z: me ? self.z : d.z, size: 1, ally: true });
  }
  for (const e of s.ents.values()) {
    const d = e.data; if (d.kind !== 'monster') continue;
    const it = s.combat.list.find((x) => x.kind === 'monster' && x.ref === d.id);
    const mon = MONSTERS.find((m) => m.id === d.model);
    const me = self && self.key === 'm' + d.id;
    out.push({ key: 'm' + d.id, name: it ? it.name : mon ? mon.nome : d.model, x: me ? self.x : d.x, z: me ? self.z : d.z, size: sizeOf(d.model), ally: false });
  }
  return out;
}
export class Session {
  constructor({ scene, role, topDown = false, hello = {}, on = {} }) {
    this.scene = scene; this.role = role; this.topDown = topDown; this.hello = hello; this.on = on;
    this.world = null; this.map = null; this.mapVersion = 0;
    this.ents = new Map(); this.players = new Map();
    this.doorState = []; this.frozen = false; this.myId = 0; this.connected = false;
    this.combat = { active: false, list: [], cur: null, round: 0 }; this.turnUsed = 0; this.kicked = false; this.fichas = {};
    this.lightPool = [];
    this.aoes = new Map(); this._hitRings = []; this._aoeTimer = 0;
    if (!topDown) {
      for (let i = 0; i < 5; i++) {
        const l = new THREE.PointLight(0xffb066, 0, 16, 1.6);
        l.position.set(0, 2.6, 0); scene.add(l); this.lightPool.push(l);
      }
    }
    this._lightTimer = 0;
    this.connect();
  }

  connect() {
    const proto = location.protocol === 'https:' ? 'wss' : 'ws';
    const ws = new WebSocket(`${proto}://${location.host}`);
    this.ws = ws;
    ws.onopen = () => {
      this.connected = true;
      ws.send(JSON.stringify({ t: 'hello', role: this.role, ...(typeof this.hello === 'function' ? this.hello() : this.hello) }));
      this.on.status && this.on.status(true);
    };
    ws.onclose = () => {
      this.connected = false;
      this.on.status && this.on.status(false);
      if (!this.kicked) setTimeout(() => this.connect(), 1500);
    };
    ws.onmessage = (ev) => { try { this.handle(JSON.parse(ev.data)); } catch (e) { console.error(e); } };
  }
  send(msg) { if (this.ws && this.ws.readyState === 1) this.ws.send(JSON.stringify(msg)); }

  async handle(m) {
    switch (m.t) {
      case 'init':
        this.myId = m.id; this.frozen = m.frozen; this.doorState = m.doors;
        if (m.aoes) this.syncAoes(m.aoes);
        this.syncEnts(m.ents); this.syncPlayers(m.players);
        // avisa a tela antes de carregar o mapa: mensagens que chegam durante a carga não podem ser desfeitas depois
        this.on.init && this.on.init(m);
        this.on.frozen && this.on.frozen(this.frozen);
        if (m.version !== this.mapVersion) await this.loadMap();
        else this.applyDoors(true);
        break;
      case 'map':
        this.doorState = m.doors; this.syncEnts(m.ents);
        await this.loadMap();
        break;
      case 'ent': this.upsertEnt(m.ent); this.on.ents && this.on.ents(m.ent); break;
      case 'ent_del': this.removeEnt(m.id); this.on.ents && this.on.ents(); break;
      case 'players': this.turnUsed = m.tu || 0; this.syncPlayers(m.list); break;
      case 'combat': this.combat = m; this.on.combat && this.on.combat(m); break;
      case 'clog': this.animateAct(m); this.on.clog && this.on.clog(m); break;
      case 'cfx': this.on.cfx && this.on.cfx(m.fx); break;
      case 'kicked': this.kicked = true; this.on.kicked && this.on.kicked(); break;
      case 'door':
        this.doorState[m.i] = m.closed;
        if (this.world && this.world.doors[m.i]) this.world.doors[m.i].closed = m.closed;
        break;
      case 'terrain': this.setTerrain(m.terrain); break;
      case 'frozen': this.frozen = m.on; this.on.frozen && this.on.frozen(m.on); break;
      case 'teleport': this.on.teleport && this.on.teleport(m); break;
      case 'pteleport': this.on.pteleport && this.on.pteleport(m); break;
      case 'oa': this.on.oa && this.on.oa(m); break;
      case 'deny': this.on.deny && this.on.deny(m.msg); break;
      case 'aoes': this.syncAoes(m.list); break;
      case 'fichas': this.fichas = m.fichas || {}; this.on.fichas && this.on.fichas(this.fichas); break;
      case 'spawn': if (this.map) this.map.spawn = m.spawn; this.on.spawn && this.on.spawn(m.spawn); break;
    }
  }

  async loadMap() {
    const token = (this._mapToken = (this._mapToken || 0) + 1);
    const map = await (await fetch('/api/map', { cache: 'no-store' })).json();
    const world = await buildWorld(map, { topDown: this.topDown });
    if (token !== this._mapToken) { world.terrain.dispose(); disposeGroup(world.group); return; }
    if (this.world) { this.world.terrain.dispose(); disposeGroup(this.world.group); }
    this.map = map; this.mapVersion = map.version; this.world = world;
    this.scene.add(world.group);
    this.applyDoors(true);
    this._lightTimer = 0;
    this.on.map && this.on.map(map, world);
    this.on.atmos && this.on.atmos(biomeById(map.terrain && map.terrain.biome));
  }

  // troca o terreno sem reconstruir paredes e portas
  setTerrain(terrain) {
    if (!this.map || !this.world) return;
    const changedBiome = !this.map.terrain || this.map.terrain.biome !== terrain.biome;
    this.map.terrain = terrain;
    this.world.terrain.set(terrain.cells, terrain.biome, { imageFloor: this.world.imageFloor, spawn: this.map.spawn });
    if (changedBiome) this.on.atmos && this.on.atmos(biomeById(terrain.biome));
    this.on.terrain && this.on.terrain(terrain);
  }

  applyDoors(snap) {
    if (!this.world) return;
    this.world.doors.forEach((d, i) => {
      d.closed = this.doorState[i] !== false;
      if (snap) { d.angle = d.closed ? 0 : 1; d.pivot.rotation.y = d.base + d.angle * 1.75; }
    });
  }

  // ---- monstros e objetos
  syncEnts(list) {
    const ids = new Set(list.map((e) => e.id));
    for (const id of [...this.ents.keys()]) if (!ids.has(id)) this.removeEnt(id);
    list.forEach((e) => this.upsertEnt(e));
    this.on.ents && this.on.ents();
  }
  upsertEnt(data) {
    let e = this.ents.get(data.id);
    if (e && e.data.model !== data.model) { this.removeEnt(data.id); e = null; }
    if (!e) {
      e = { data: { ...data }, holder: new THREE.Group(), char: null, radius: 0.6 };
      this.ents.set(data.id, e);
      this.scene.add(e.holder);
      const done = (obj) => { if (this.ents.get(data.id) === e) e.holder.add(obj); };
      if (data.kind === 'monster' && this.topDown) {
        // na vista de cima, um disco vermelho ajuda a achar o monstro
        const sz = sizeOf(data.model), r0 = sz > 1 ? sz - 0.25 : 0.62, r1 = sz > 1 ? sz : 0.8;
        const disc = new THREE.Mesh(new THREE.RingGeometry(r0, r1, sz > 1 ? 4 : 28, 1, Math.PI / 4), new THREE.MeshBasicMaterial({ color: 0xff5a4a, depthTest: false }));
        disc.rotation.x = -Math.PI / 2; disc.position.y = 4.1; disc.renderOrder = 3; e.holder.add(disc);
      }
      if (data.kind === 'monster') makeCharacter(data.model).then((c) => { e.char = c; done(c.obj); }).catch(console.error);
      else makeProp(data.model).then(done).catch(console.error);
    }
    const fresh = !e.seen; e.seen = true;
    Object.assign(e.data, data);
    const size = data.kind === 'monster' ? sizeOf(data.model) : 1;
    e.size = size;
    e.radius = (data.kind === 'monster' ? (size > 1 ? size * 0.85 : 0.6) : propRadius(data.model)) * data.scale;
    // monstro andando (visão do monstro) desliza até a posição; o resto vai direto
    if (fresh || !data.mv || this.topDown) { e.holder.position.set(data.x, this.baseAt(data.x, data.z, data.kind === 'monster' ? sizeOf(data.model) : 1) + (this.topDown ? 0 : data.y || 0), data.z); e.holder.rotation.y = data.ry; }
    e.holder.scale.setScalar(data.scale);
  }
  removeEnt(id) {
    const e = this.ents.get(id);
    if (!e) return;
    e.holder.removeFromParent(); if (e.air) e.air.removeFromParent(); this.ents.delete(id);
  }

  // ---- outros jogadores
  syncPlayers(list) {
    const ids = new Set(list.map((p) => p.id));
    for (const [id, p] of this.players) if (!ids.has(id)) { p.holder.removeFromParent(); if (p.air) p.air.removeFromParent(); this.players.delete(id); }
    let changed = false;
    for (const d of list) {
      let p = this.players.get(d.id);
      if (!p) {
        changed = true;
        p = { data: d, holder: new THREE.Group(), char: null };
        p.holder.position.set(d.x, 0, d.z); p.holder.rotation.y = d.ry;
        this.players.set(d.id, p);
        if (d.id !== this.myId) {
          this.scene.add(p.holder);
          const label = makeLabel(d.name, '#ffe9a8');
          label.position.y = this.topDown ? 4.5 : 2.9;
          if (this.topDown) label.scale.multiplyScalar(1.6);
          p.holder.add(label);
          makeCharacter(d.hero).then(async (c) => {
            p.char = c; p.holder.add(c.obj);
            if (d.hero === 'Kaira') {   // Revelação Celestial: forma alada
              _Celestial = _Celestial || (await import('./revelacao.js')).CelestialForm;
              p.form = new _Celestial(p.holder, c, this.scene); if (p.data.rev) p.form.preload();
            }
          }).catch(console.error);
        }
      }
      p.data = d;
    }
    const sig = list.map((p) => p.id + p.name + p.hero + (p.off ? 0 : 1) + ':' + (p.fly || 0) + (p.rev ? 'R' : '')).join('|');
    if (changed || sig !== this._lastSig) { this._lastSig = sig; this.on.players && this.on.players(list); }
  }

  // quem atacou toca o golpe; quem conjurou toca a magia (o próprio personagem do jogador é animado pela tela dele)
  animateAct(m) {
    const it = this.combat.list.find((x) => x.cid === m.cid); if (!it) return;
    const holder = it.kind === 'player' ? this.players.get(it.ref) : this.ents.get(it.ref);
    const c = holder && holder.char; if (!c) return;
    const clips = ACT_CLIPS[m.id]; if (clips) c.once(clips);
  }

  // posição atual de um participante do combate
  combatantPos(it) {
    if (!it) return null;
    if (it.kind === 'player') {
      if (it.ref === this.myId && this.myPos) return this.myPos;
      const p = this.players.get(it.ref); return p ? p.holder.position : null;
    }
    const e = this.ents.get(it.ref); return e ? e.holder.position : null;
  }

  // ---- por quadro
  update(dt, focus) {
    wind.value += dt;
    const k = 1 - Math.exp(-dt * 12);
    for (const e of this.ents.values()) {
      const alt = e.data.y || 0;
      if (e.hidden) { e.holder.visible = false; if (e.air) e.air.visible = false; continue; }
      const h = e.holder;
      if (e.data.mv && !this.topDown) {
        h.position.x += (e.data.x - h.position.x) * k; h.position.z += (e.data.z - h.position.z) * k;
        let dr = e.data.ry - h.rotation.y; dr = Math.atan2(Math.sin(dr), Math.cos(dr)); h.rotation.y += dr * k;
      }
      const gy = this.baseAt(h.position.x, h.position.z, e.size || 1);
      if (e.data.kind === 'monster') h.position.y += (gy + (this.topDown ? 0 : alt) - h.position.y) * k;
      if (e.data.kind === 'monster') updateAirMark(e, this.scene, h.position.x, h.position.z, alt, this.topDown, e.size || 1, gy);
      if (e.char) {
        if (e.data.kind === 'monster') e.char.play(animFor(e.char, alt > 0.15, !!e.data.mv));
        e.char.mixer.update(dt);
      }
    }
    for (const p of this.players.values()) {
      if (p.data.id === this.myId) continue;
      if (p.dragging) continue;
      const h = p.holder;
      h.position.x += (p.data.x - h.position.x) * k;
      h.position.z += (p.data.z - h.position.z) * k;
      const alt = p.data.y || 0, gy = this.baseAt(h.position.x, h.position.z, 1);
      h.position.y += (gy + (this.topDown ? 0 : alt + (alt > 0.15 ? Math.sin(performance.now() / 400 + p.data.id) * 0.08 : 0)) - h.position.y) * k;
      updateAirMark(p, this.scene, h.position.x, h.position.z, alt, this.topDown, 1, gy);
      let dr = p.data.ry - h.rotation.y;
      dr = Math.atan2(Math.sin(dr), Math.cos(dr));
      h.rotation.y += dr * k;
      if (p.char) {
        const air = alt > 0.15;   // na visão de cima do mestre o token não sobe, mas as asas aparecem igual
        const c = p.form ? p.form.update(dt, !!p.data.rev && air) : p.char;
        c.play(animFor(c, air, !!p.data.mv)); c.mixer.update(dt * (p.form ? p.form.timeScale : 1));
      }
    }
    this.updateAoes(dt);
    if (this.world) {
      this.world.terrain.update(dt);
      for (const d of this.world.doors) {
        const target = d.closed ? 0 : 1;
        if (d.angle !== target) {
          d.angle += Math.sign(target - d.angle) * Math.min(Math.abs(target - d.angle), dt * 2.5);
          d.pivot.rotation.y = d.base + d.angle * 1.75;
        }
      }
      // as luzes de verdade acompanham as chamas mais próximas de quem olha
      if (focus && this.lightPool.length) {
        this._lightTimer -= dt;
        if (this._lightTimer <= 0) {
          this._lightTimer = 0.4;
          const near = this.world.lights
            .map((l) => ({ l, d: (l.x - focus.x) ** 2 + (l.z - focus.z) ** 2 }))
            .sort((a, b) => a.d - b.d).slice(0, this.lightPool.length);
          this.lightPool.forEach((pl, i) => {
            const n = near[i];
            if (!n) { pl.intensity = 0; return; }
            pl.position.set(n.l.x, n.l.y !== undefined ? n.l.y : 2.6, n.l.z); pl.color.copy(n.l.color);
            pl.distance = n.l.range * 1.6; pl.baseIntensity = 14 * n.l.intensity;
          });
        }
        const t = performance.now() / 1000;
        this.lightPool.forEach((pl, i) => { if (pl.baseIntensity) pl.intensity = pl.baseIntensity * (0.9 + 0.1 * Math.sin(t * 9 + i * 2.1) * Math.sin(t * 5.3 + i)); });
      }
    }
  }

  // ---- colisão: empurra um círculo para fora de paredes, portas fechadas, objetos e monstros
  // altura de quem está de pé (no chão, ou boiando em água funda); 0 em mapas planos
  // ---- áreas de magia vindas do servidor: aparecem com um brilho, piscam a borda e somem devagar
  syncAoes(list) {
    const ids = new Set(list.map((a) => a.id));
    for (const [id, a] of this.aoes) if (!ids.has(id)) a.dying = true;
    for (const d of list) {
      const old = this.aoes.get(d.id);
      if (old) { old.data = d; old.dying = false; continue; }
      const parts = visibleParts(d, this.areaBlockers(d.y || 0));   // paredes e objetos cortam a área
      const mesh = buildAreaMesh(d, { top: this.topDown, y: (d.y || 0) + 0.02, parts });
      mesh.userData.setAlpha(0); this.scene.add(mesh);
      this.aoes.set(d.id, { data: d, mesh, parts, k: 0, dying: false, born: performance.now() });
      this.on.aoeNew && this.on.aoeNew(d);
    }
    this._aoeTimer = 0;
    this.on.aoes && this.on.aoes();
  }
  creatures() { return areaCreatures(this); }
  aoeHits(d) { const a = this.aoes.get(d.id); return areaHits(d, this.creatures(), a && a.parts); }
  // o que bloqueia uma área: paredes (nos cenários, só as mais altas que uma pessoa), portas fechadas e objetos sólidos
  areaBlockers(y0 = 0) {
    const w = this.world; if (!w) return null;
    const segs = [];
    for (const s of w.segments) if (s.top === undefined || s.top > 900 || s.top > y0 + 1.6) segs.push(s);
    for (const d of w.doors || []) if (d.angle < 0.6) segs.push(d);
    const circles = ((w.terrain && w.terrain.obstacles) || []).filter((o) => o.r > 0.15);
    // objetos altos dão cobertura total (mesas, baús, camas e cadeiras são baixos: a área passa por cima)
    for (const e of this.ents.values()) if (e.data.kind !== 'monster' && COVER.has(e.data.model)) circles.push({ x: e.data.x, z: e.data.z, r: e.radius * 0.8 });
    return { segs, circles };
  }
  updateAoes(dt) {
    const t = performance.now() / 1000;
    for (const [id, a] of this.aoes) {
      a.k = a.dying ? Math.max(0, a.k - dt / 0.7) : Math.min(1, a.k + dt / 0.45);
      const flash = Math.max(0, 1 - (performance.now() - a.born) / 900);   // brilho ao aparecer
      a.mesh.userData.setAlpha(a.k * (0.85 + 0.15 * Math.sin(t * 4)) + flash * 1.2);
      if (a.dying && a.k <= 0) { this.scene.remove(a.mesh); disposeAreaMesh(a.mesh); this.aoes.delete(id); this._aoeTimer = 0; }
    }
    // anel em quem está dentro de alguma área (vermelho = inimigo, verde = aliado)
    this._aoeTimer -= dt;
    if (this._aoeTimer <= 0) {
      this._aoeTimer = 0.25;
      const hit = new Map();
      for (const a of this.aoes.values()) if (!a.dying) for (const c of areaHits(a.data, this.creatures(), a.parts)) hit.set(c.key, c);
      const list = [...hit.values()];
      while (this._hitRings.length < list.length) {
        const m = new THREE.Mesh(new THREE.RingGeometry(0.85, 1.08, 40), new THREE.MeshBasicMaterial({ color: 0xff5050, transparent: true, depthTest: !this.topDown, depthWrite: false, side: THREE.DoubleSide, fog: false }));
        m.rotation.x = -Math.PI / 2; m.renderOrder = 23; this.scene.add(m); this._hitRings.push(m);
      }
      this._hitRings.forEach((m, i) => {
        const c = list[i]; m.visible = !!c; if (!c) return;
        m.scale.setScalar(c.size || 1); m.position.set(c.x, this.baseAt(c.x, c.z, c.size || 1) + 0.15, c.z);
        m.material.color.set(c.ally ? 0x6fe39a : 0xff5050);
      });
    }
    for (const m of this._hitRings) if (m.visible) m.material.opacity = 0.65 + 0.35 * Math.sin(t * 6);
  }
  baseAt(x, z, size = 1) { return this.world && this.world.standAt ? this.world.standAt(x, z, size) : 0; }

  collide(pos, radius = 0.45, skip = 0, y = 0) {
    if (!this.world) return;
    const abs = this.baseAt(pos.x, pos.z) + y;
    const over = y > WALL_H - 0.2;   // voando acima das paredes
    const push = (cx, cz, minD) => {
      const dx = pos.x - cx, dz = pos.z - cz;
      const d = Math.hypot(dx, dz);
      if (d < minD && d > 1e-5) { const f = (minD - d) / d; pos.x += dx * f; pos.z += dz * f; }
    };
    const seg = (s, half) => {
      const vx = s.x2 - s.x1, vz = s.z2 - s.z1;
      const len2 = vx * vx + vz * vz || 1;
      let t = ((pos.x - s.x1) * vx + (pos.z - s.z1) * vz) / len2;
      t = Math.max(0, Math.min(1, t));
      push(s.x1 + vx * t, s.z1 + vz * t, radius + half);
    };
    for (let it = 0; it < 3; it++) {
      for (const s of this.world.segments) if (s.top !== undefined && (s.top > 900 || abs < s.top)) seg(s, WALL_HALF); // trechos com altura própria (mapas prontos)
      if (!over) {
        for (const s of this.world.segments) if (s.top === undefined) seg(s, WALL_HALF);
        for (const d of this.world.doors) if (d.angle < 0.6) seg(d, 0.15);
        for (const o of this.world.terrain.obstacles) push(o.x, o.z, radius + o.r);
      }
      for (const e of this.ents.values()) {
        if (e.data.id === skip) continue;
        const ey = e.data.y || 0, top = ey + (e.size > 1 ? e.size * 2 : 2.4) * (e.data.scale || 1);
        if (y > top || ey > y + 2.4) continue; // passa por cima (ou por baixo) de quem não está na mesma altura
        push(e.data.x, e.data.z, radius + e.radius * 0.8);
      }
    }
  }

  nearestDoor(pos, maxDist = 2.6) {
    if (!this.world) return null;
    let best = null, bd = maxDist;
    for (const d of this.world.doors) {
      const dist = Math.hypot(d.mx - pos.x, d.mz - pos.z);
      if (dist < bd) { bd = dist; best = d; }
    }
    return best;
  }
}

export function makeRenderer(canvas, mobile) {
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, powerPreference: 'high-performance' });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, mobile ? 1.5 : 2));
  renderer.setSize(window.innerWidth, window.innerHeight, false);
  return renderer;
}
