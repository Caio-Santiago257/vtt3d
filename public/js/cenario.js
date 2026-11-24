// Mapas prontos com relevo (ex.: Covil do Dragão Negro): terreno em 3D com texturas misturadas,
// água em níveis (rio e salas inundadas), vegetação, ruínas modeladas, borda natural e fundo panorâmico.
// Os dados vêm de /assets/maps/<id>/ (gerados por fontes/mapas/<id>_gerar.py e fontes/blender/<id>_cenario.py).
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { toonSoft, addRimSpec } from './gfx.js';
import { plantGroup } from './terreno.js';
import { loadKit, instanceKit, kitWind } from './kit.js';

const G = 2;
const texLoader = new THREE.TextureLoader();
const gltfLoader = new GLTFLoader();

function decodeHeights(b64) {
  const bin = atob(b64), buf = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) buf[i] = bin.charCodeAt(i);
  const raw = new Int16Array(buf.buffer), out = new Float32Array(raw.length);
  for (let i = 0; i < raw.length; i++) out[i] = raw[i] / 100;
  return out;
}

export async function buildCenario(map, { topDown = false } = {}) {
  const base = `/assets/maps/${map.cenario}/`;
  const D = await (await fetch(base + 'dados.json')).json();
  const n = D.n, x0 = D.x0, res = D.res, span = (n - 1) * res;
  const H = decodeHeights(D.relevo);
  const group = new THREE.Group();
  const W = map.w * G, Hh = map.h * G;

  // ---- consultas de altura e água (usadas pelo jogo todo)
  const groundAt = (x, z) => {
    const fx = Math.min(n - 1.001, Math.max(0, (x - x0) / res)), fz = Math.min(n - 1.001, Math.max(0, (z - x0) / res));
    const i = Math.floor(fx), j = Math.floor(fz), tx = fx - i, tz = fz - j, k = j * n + i;
    return (H[k] * (1 - tx) + H[k + 1] * tx) * (1 - tz) + (H[k + n] * (1 - tx) + H[k + n + 1] * tx) * tz;
  };
  const rooms = D.agua.salas || [];
  const inLab = (x, z) => rooms.some(([a, b, c, d]) => x >= a && x <= c && z >= b && z <= d);
  // poças (mapas de mata): cada uma com o seu nível; fora delas não há água
  const pocas = D.agua.pocas || null;
  const pondAt = (x, z) => { for (const p of pocas) { const dx = x - p[0], dz = z - p[1]; if (dx * dx + dz * dz < p[2] * p[2]) return p[3]; } return -999; };
  const waterAt = pocas ? pondAt : (x, z) => (inLab(x, z) ? D.agua.lab : D.agua.rio);
  // onde a criatura fica de pé: no chão, ou boiando com o peito para fora quando a água é funda (size = quadrados)
  const standAt = (x, z, size = 1) => {
    const g = groundAt(x, z), wl = waterAt(x, z), deep = 1.85 * size;
    return wl - g > deep ? wl - deep : g;
  };

  // ---- texturas
  const T = {};
  const load = (name, { srgb = true, rep = true } = {}) => texLoader.loadAsync(base + 'tex/' + name).then((t) => {
    if (srgb) t.colorSpace = THREE.SRGBColorSpace;
    if (rep) t.wrapS = t.wrapT = THREE.RepeatWrapping;
    t.anisotropy = 4; T[name.replace(/\.(jpg|png|webp)$/, '')] = t; return t;
  });
  const splat = (name) => texLoader.loadAsync(base + name).then((t) => { t.colorSpace = THREE.NoColorSpace; t.flipY = false; return t; }); // linha 0 da imagem = norte
  // o chão usa 5 papéis (lama, musgo, caverna, piso, rocha); cada mapa diz qual arquivo faz cada papel
  const TX = D.texturas || {};
  const role = { lama: TX.lama || 'lama.jpg', musgo: TX.musgo || 'musgo.jpg', caverna: TX.caverna || 'caverna.jpg', piso: TX.piso || 'piso.jpg', rocha: TX.rocha || 'rocha.jpg' };
  const loadRole = (r) => texLoader.loadAsync(base + 'tex/' + role[r]).then((t) => { t.colorSpace = THREE.SRGBColorSpace; t.wrapS = t.wrapT = THREE.RepeatWrapping; t.anisotropy = 4; T['@' + r] = t; T[role[r].replace(/\.(jpg|png)$/, '')] = t; return t; });
  const FD = D.fundo || {};
  const CEU = D.ceu || null;
  const extra = D.tex_glb ? D.tex_glb.map((f) => load(f, { srgb: !/_n\./.test(f) })) : D.kit ? [] : [...['tijolo.jpg', 'ossuario.jpg', 'madeira.jpg', 'metal.jpg', 'ouro.jpg', 'agua.jpg'].map((f) => load(f)),
    ...['tijolo_n.png', 'piso_n.png', 'rocha_n.png', 'ossuario_n.png'].map((f) => load(f, { srgb: false }))];
  const [splatA, splatB] = await Promise.all([splat('mistura_a.png'), splat('mistura_b.png'),
    ...['lama', 'musgo', 'caverna', 'piso', 'rocha'].map(loadRole), ...extra,
    load('agua_n.png', { srgb: false }), ...(CEU ? [] : [load(FD.img || 'fundo.jpg')])]);
  T.fundo = CEU ? null : T[(FD.img || 'fundo.jpg').replace(/\.(jpg|png|webp)$/, '')];
  const ESC = TX.escalas || [7, 6, 6, 8], LIMO = TX.limo || [0.13, 0.22, 0.08], SOMBRA = TX.sombra ?? 0.35, MOLHADO = TX.molhado !== false;

  // ---- terreno: grade de alturas, mistura de 5 texturas; encostas íngremes viram rocha (projeção nos 3 eixos)
  const geo = new THREE.BufferGeometry();
  const pos = new Float32Array(n * n * 3);
  for (let j = 0; j < n; j++) for (let i = 0; i < n; i++) { const k = (j * n + i) * 3; pos[k] = x0 + i * res; pos[k + 1] = H[j * n + i]; pos[k + 2] = x0 + j * res; }
  const idx = new Uint32Array((n - 1) * (n - 1) * 6);
  let q = 0;
  for (let j = 0; j < n - 1; j++) for (let i = 0; i < n - 1; i++) {
    const a = j * n + i, b = a + 1, c = a + n, d = c + 1;
    idx[q++] = a; idx[q++] = c; idx[q++] = b; idx[q++] = b; idx[q++] = c; idx[q++] = d;
  }
  geo.setAttribute('position', new THREE.BufferAttribute(pos, 3)); geo.setIndex(new THREE.BufferAttribute(idx, 1));
  geo.computeVertexNormals(); geo.computeBoundingSphere();
  const tmat = toonSoft({ color: 0xffffff });
  tmat.onBeforeCompile = (sh) => {
    Object.assign(sh.uniforms, {
      tMusgo: { value: T['@musgo'] }, tLama: { value: T['@lama'] }, tCaverna: { value: T['@caverna'] }, tPiso: { value: T['@piso'] }, tRocha: { value: T['@rocha'] },
      tSplatA: { value: splatA }, tSplatB: { value: splatB }, uX0: { value: x0 }, uSpan: { value: span },
      uEsc: { value: new THREE.Vector4(...ESC) }, uLimo: { value: new THREE.Vector3(...LIMO) }, uSombra: { value: SOMBRA }, uMolhado: { value: MOLHADO ? 1 : 0 },
    });
    sh.vertexShader = sh.vertexShader
      .replace('#include <common>', '#include <common>\nvarying vec3 vWPos; varying vec3 vWNorm;')
      .replace('#include <begin_vertex>', '#include <begin_vertex>\nvWPos = (modelMatrix * vec4(transformed, 1.0)).xyz; vWNorm = normalize(mat3(modelMatrix) * objectNormal);');
    sh.fragmentShader = sh.fragmentShader
      .replace('#include <common>', `#include <common>
varying vec3 vWPos; varying vec3 vWNorm;
uniform sampler2D tMusgo, tLama, tCaverna, tPiso, tRocha, tSplatA, tSplatB; uniform float uX0, uSpan, uSombra, uMolhado; uniform vec4 uEsc; uniform vec3 uLimo;`)
      .replace('#include <map_fragment>', `
vec2 w = vWPos.xz;
vec2 suv = (w - uX0) / uSpan;
vec3 sa = texture2D(tSplatA, suv).rgb, sb = texture2D(tSplatB, suv).rgb;
// duas escalas de cada textura misturadas: some o padrão repetido quando se olha de longe
vec3 cMusgo = mix(texture2D(tMusgo, w / uEsc.y).rgb, texture2D(tMusgo, w / (uEsc.y * 3.8) + 0.37).rgb, 0.45);
vec3 cLama = mix(texture2D(tLama, w / uEsc.x).rgb, texture2D(tLama, w / (uEsc.x * 3.7) + 0.21).rgb, 0.45);
vec3 cCav = mix(texture2D(tCaverna, w / uEsc.z).rgb, texture2D(tCaverna, w / (uEsc.z * 2.8) + 0.5).rgb, 0.3);
vec3 cPiso = texture2D(tPiso, w / uEsc.w).rgb;
float s = sa.r + sa.g + sa.b + 1e-4;
vec3 col = (cLama * sa.r + cMusgo * sa.g + cCav * sa.b) / s;
col = mix(col, cPiso, sb.r);
col *= 1.0 - uSombra * sb.g;
col = mix(col, uLimo, sb.b * 0.5);
vec3 nn = normalize(vWNorm), an = abs(nn); an /= (an.x + an.y + an.z);
vec3 rock = texture2D(tRocha, vWPos.zy / 9.0).rgb * an.x + texture2D(tRocha, vWPos.xz / 9.0).rgb * an.y + texture2D(tRocha, vWPos.xy / 9.0).rgb * an.z;
col = mix(col, rock, smoothstep(0.40, 0.62, 1.0 - nn.y));
col *= mix(mix(0.7, 1.0, smoothstep(-0.45, 0.2, vWPos.y)), 1.0, 1.0 - uMolhado);        // chão molhado perto da água (covil)
diffuseColor.rgb *= col;`);
  };
  const terrainMesh = new THREE.Mesh(geo, tmat);
  terrainMesh.name = 'cenario_terreno';
  group.add(terrainMesh);

  // ---- água: um quadrado por célula da grade onde o chão fica abaixo do nível; cor e transparência pela profundidade
  {
    const P = [], C = [], I = [];
    const AC = (D.agua && D.agua.cor) || null, AF = (D.agua && D.agua.fundo) || null;
    const add = (x, z, wl, lab) => {
      const b = P.length / 3;
      for (const [dx, dz] of [[0, 0], [res, 0], [0, res], [res, res]]) {
        const depth = Math.max(0, wl - groundAt(x + dx, z + dz)), t = Math.min(1, depth / 2.6);
        P.push(x + dx, wl, z + dz);
        if (AC) { const k = Math.min(1, depth / 0.9); C.push(AC[0] + (AF[0] - AC[0]) * k, AC[1] + (AF[1] - AC[1]) * k, AC[2] + (AF[2] - AC[2]) * k, 0.55 + 0.4 * k); }
        else if (lab) C.push(0.24 - 0.17 * t, 0.36 - 0.22 * t, 0.15 - 0.09 * t, 0.6 + 0.27 * Math.min(1, depth / 1.6));
        else C.push(0.22 - 0.15 * t, 0.33 - 0.2 * t, 0.2 - 0.11 * t, 0.5 + 0.38 * Math.min(1, depth / 1.6));
      }
      I.push(b, b + 2, b + 1, b + 1, b + 2, b + 3);
    };
    const step = pocas ? res / 2 : res;     // poças pequenas: grade mais fina para a borda ficar redonda
    const cellsN = Math.round((n - 1) * res / step);
    for (let j = 0; j < cellsN; j++) for (let i = 0; i < cellsN; i++) {
      const x = x0 + i * step, z = x0 + j * step, cx = x + step / 2, cz = z + step / 2;
      if (pocas) {
        const wl = pondAt(cx, cz); if (wl < -900) continue;
        if (Math.min(groundAt(x, z), groundAt(x + step, z), groundAt(x, z + step), groundAt(x + step, z + step)) < wl - 0.01) {
          const b = P.length / 3;
          for (const [dx, dz] of [[0, 0], [step, 0], [0, step], [step, step]]) {
            const depth = Math.max(0, wl - groundAt(x + dx, z + dz)), k = Math.min(1, depth / 0.8);
            P.push(x + dx, wl, z + dz);
            C.push(AC[0] + (AF[0] - AC[0]) * k, AC[1] + (AF[1] - AC[1]) * k, AC[2] + (AF[2] - AC[2]) * k, 0.45 + 0.5 * k);
          }
          I.push(b, b + 2, b + 1, b + 1, b + 2, b + 3);
        }
        continue;
      }
      if (step !== res) continue;
      const lab = inLab(cx, cz), wl = lab ? D.agua.lab : D.agua.rio;
      if (!lab && D.agua.lab_area) { const [a, b, c, d] = D.agua.lab_area; if (cx > a && cx < c && cz > b && cz < d) continue; }
      const k = j * n + i;
      if (Math.min(H[k], H[k + 1], H[k + n], H[k + n + 1]) < wl - 0.02) add(x, z, wl, lab);
    }
    const wg = new THREE.BufferGeometry();
    wg.setAttribute('position', new THREE.Float32BufferAttribute(P, 3));
    wg.setAttribute('color', new THREE.Float32BufferAttribute(C, 4));
    wg.setAttribute('uv', new THREE.Float32BufferAttribute(P.filter((_, i) => i % 3 !== 1).map((v) => v / 7), 2));
    wg.setIndex(I); wg.computeVertexNormals();
    // água parada: lisa, escura e com brilho de céu nas ondulações (o relevo da textura só mexe no brilho)
    T.agua_n.repeat.set(0.6, 0.6);
    const wmat = new THREE.MeshPhongMaterial({ vertexColors: true, transparent: true, depthWrite: false, normalMap: T.agua_n, normalScale: new THREE.Vector2(0.35, 0.35), shininess: 140,
      specular: topDown ? 0x2a3328 : (pocas ? 0x9fb4c8 : 0x8fa88a), emissive: pocas ? 0x050a12 : 0x0b140d }); // vista de cima: menos brilho, para ler o fundo
    const water = new THREE.Mesh(wg, wmat); water.renderOrder = 1; water.name = 'cenario_agua';
    group.add(water);
    if (D.ceu && !topDown && !pocas) {
      // mar aberto: a mesma água continua do fim do relevo até perto do céu (um anel com o quadrado do relevo vazado)
      const R = (D.ceu.raio || 360) * 0.985, mx = (map.w * G) / 2, mz = (map.h * G) / 2;
      const sh = new THREE.Shape(); sh.absarc(mx, mz, R, 0, Math.PI * 2, false);
      const hole = new THREE.Path(); hole.moveTo(x0, x0); hole.lineTo(x0, x0 + span); hole.lineTo(x0 + span, x0 + span); hole.lineTo(x0 + span, x0); hole.lineTo(x0, x0);
      sh.holes.push(hole);
      const sg = new THREE.ShapeGeometry(sh, 64), sp = sg.attributes.position, cnt = sp.count;
      const P2 = new Float32Array(cnt * 3), C2 = new Float32Array(cnt * 4), U2 = new Float32Array(cnt * 2);
      for (let i = 0; i < cnt; i++) {
        const x = sp.getX(i), z = sp.getY(i);
        P2.set([x, D.agua.rio, z], i * 3); C2.set([AF[0], AF[1], AF[2], 0.95], i * 4); U2.set([x / 7, z / 7], i * 2);
      }
      const og = new THREE.BufferGeometry();
      og.setAttribute('position', new THREE.BufferAttribute(P2, 3)); og.setAttribute('color', new THREE.BufferAttribute(C2, 4)); og.setAttribute('uv', new THREE.BufferAttribute(U2, 2));
      const idx = Array.from(sg.index.array); for (let i = 0; i < idx.length; i += 3) { const t = idx[i + 1]; idx[i + 1] = idx[i + 2]; idx[i + 2] = t; }   // de frente para cima
      og.setIndex(idx); og.computeVertexNormals(); sg.dispose();
      const oceano = new THREE.Mesh(og, wmat); oceano.renderOrder = 1; oceano.name = 'cenario_oceano'; group.add(oceano);
    }
    group.userData.water = water;
  }

  // ---- vegetação (árvores, juncos, ninfeias, pedras) e as ruínas modeladas
  if (D.vegetacao && D.vegetacao.length) group.add(plantGroup(D.vegetacao, { topDown }));
  const mats = new Map();
  if (D.kit) {
    const kits = [base + D.kit, ...(D.kit_extra || []).map((f) => base + f)];
    const kit = await loadKit(kits, { texBase: base + 'tex/', topDown });
    const kitGroup = instanceKit(kit, D.instancias || {}, { topDown, origin: x0 }); kitGroup.name = 'cenario_kit';
    group.add(kitGroup);
  }
  const glbName = D.glb || (D.kit ? null : 'covil.glb');
  const gltf = glbName ? await gltfLoader.loadAsync(base + glbName) : null;
  const conv = (src) => {
    if (mats.has(src)) return mats.get(src);
    const ex = src.userData || {};
    let m;
    if (ex.glow) {
      m = new THREE.MeshBasicMaterial({ color: src.color.clone() });
      // brilho > 1: à noite a janela acesa passa de 1 e a passada da noite não escurece (luz própria)
      if (ex.brilho) glowMats.push({ m, base: src.color.clone(), brilho: ex.brilho });
    } else if (ex.cascata) {
      // água que corre: a textura desliza ao longo da faixa
      const t = T[ex.tex].clone(); t.needsUpdate = true; flowTex.push({ t, v: ex.cascata });
      m = new THREE.MeshBasicMaterial({ map: t, color: 0xf2fbff, transparent: true, opacity: Math.min(1, (ex.opacity || 0.85) * 1.1), depthWrite: false, side: THREE.DoubleSide });
    } else if (ex.glass) m = new THREE.MeshPhongMaterial({ color: src.color.clone(), map: ex.tex ? T[ex.tex] : null, transparent: true, opacity: ex.opacity || 0.35, depthWrite: false, side: THREE.DoubleSide, shininess: 90, specular: 0x667766 });
    else {
      m = toonSoft({ color: ex.tex ? 0xffffff : src.color.clone(), map: ex.tex ? T[ex.tex] : null, normalMap: ex.normal ? T[ex.normal] : null });
      addRimSpec(m, { rim: ex.rim || 0 });
      if (ex.dupla) m.side = THREE.DoubleSide;
    }
    mats.set(src, m); return m;
  };
  const glowMats = [], flowTex = [], spinners = [], telhados = [];
  if (gltf) {
    gltf.scene.traverse((o) => {
      const ud = o.userData || {};
      // TELHADO_*: telhados, andar de cima e cúpula (somem na visão de cima); gira_eixo: peças que giram
      if (/^TELHADO/.test(o.name) || ud.telhado) { telhados.push(o); if (topDown) o.visible = false; }
      if (ud.gira_eixo) spinners.push({ o, ax: new THREE.Vector3(ud.gira_eixo === 'x' ? 1 : 0, ud.gira_eixo === 'y' ? 1 : 0, ud.gira_eixo === 'z' ? 1 : 0), v: ud.gira_vel || 0.3 });
      if (!o.isMesh) return;
      o.material = Array.isArray(o.material) ? o.material.map(conv) : conv(o.material);
      if (o.isInstancedMesh) o.computeBoundingSphere();
    });
    group.add(gltf.scene);
  }

  // ---- fundo: pântano distante num cilindro em volta de tudo, e um chão longe da cor da névoa
  const backdrop = new THREE.Group();
  if (!topDown && CEU) {
    // céu aberto: esfera com o panorama do horário (estrelas à noite), o mar distante já pintado nele
    const ceuTex = {};
    const loadCeu = (h) => ceuTex[h] || (ceuTex[h] = texLoader.loadAsync(base + CEU[h]).then((t) => { t.colorSpace = THREE.SRGBColorSpace; return t; }));
    const ceuMat = new THREE.MeshBasicMaterial({ map: await loadCeu('dia'), side: THREE.BackSide, fog: false, depthWrite: false });
    const sph = new THREE.Mesh(new THREE.SphereGeometry(CEU.raio || 360, 96, 48), ceuMat);
    sph.scale.x = -1;   // vista de dentro: desespelha o panorama
    sph.position.set(W / 2, CEU.y ?? 0, Hh / 2); sph.renderOrder = -1; sph.frustumCulled = false; sph.name = 'ceu';
    const AFc = (D.agua && D.agua.fundo) || FD.chao || [0.02, 0.05, 0.1];
    const far = new THREE.Mesh(new THREE.CircleGeometry((CEU.raio || 360) * 0.985, 64), new THREE.MeshBasicMaterial({ color: new THREE.Color(...AFc) }));
    far.rotation.x = -Math.PI / 2; far.position.set(W / 2, (D.agua.rio ?? 0) - 0.6, Hh / 2);
    backdrop.add(sph, far); group.add(backdrop);
    let pedida = 'dia';
    backdrop.userData.setHora = (h) => {
      const k = h === 'noite' ? 'noite' : h === 'tarde' ? 'tarde' : 'dia'; pedida = k;
      loadCeu(k).then((t) => { if (pedida === k) { ceuMat.map = t; ceuMat.needsUpdate = true; } }).catch(() => {});
    };
  } else if (!topDown) {
    // cilindro alto: a imagem ocupa só a faixa de baixo (130 unidades); acima, a cor do céu da própria imagem continua
    // até bem alto, para a borda do cilindro não aparecer contra o céu
    const RAD = FD.raio || 230, BASE = FD.base ?? -35, IMG = FD.faixa || 130, CH = Math.max(420, IMG * 2.6);
    const cyl = new THREE.Mesh(new THREE.CylinderGeometry(RAD, RAD, CH, 96, 1, true),
      new THREE.MeshBasicMaterial({ map: T.fundo, side: THREE.BackSide, fog: false, depthWrite: false, transparent: /\.(png|webp)$/.test(FD.img || '') }));  // a parte de cima some no céu do jogo
    T.fundo.wrapS = THREE.RepeatWrapping; T.fundo.wrapT = THREE.ClampToEdgeWrapping; T.fundo.repeat.set(FD.repetir || 2, CH / IMG);
    cyl.position.set(W / 2, BASE + CH / 2, Hh / 2); cyl.renderOrder = -1;
    const far = new THREE.Mesh(new THREE.CircleGeometry(RAD * 2.3, 48), new THREE.MeshBasicMaterial({ color: FD.chao ? new THREE.Color(...FD.chao) : 0x3c4a38 }));
    far.rotation.x = -Math.PI / 2; far.position.set(W / 2, FD.chao_y ?? -1.6, Hh / 2);
    backdrop.add(cyl, far);
    group.add(backdrop);
  }

  // ---- dados de jogo
  const segments = D.colisao.map(([x1, z1, x2, z2, top]) => ({ x1, z1, x2, z2, top }));
  let cells = (map.terrain && map.terrain.cells) || '';
  const W2 = map.w;
  const charAt = (x, z) => { const i = Math.floor(x / G), j = Math.floor(z / G); return i < 0 || j < 0 || i >= W2 || j >= map.h ? '' : cells[j * W2 + i]; };
  const DIFF = new Set(['a', 'l', 'b', 'm']), SLOW = { a: 0.55, l: 0.8, b: 0.75 };
  let tWater = 0;
  const terrain = {
    obstacles: D.obstaculos.map(([x, z, r]) => ({ x, z, r })), biome: { id: D.bioma },
    charAt, costAt: (x, z) => (DIFF.has(charAt(x, z)) ? 2 : 1), isDifficult: (x, z) => DIFF.has(charAt(x, z)), slowAt: (x, z) => SLOW[charAt(x, z)] || 1,
    // o mestre pode repintar o custo dos quadrados; o visual do cenário continua o mesmo
    set(c) { if (typeof c === 'string' && c.length === cells.length) cells = c; },
    update(dt) {
      tWater += dt; kitWind.value = tWater; T.agua_n.offset.set(-tWater * 0.006, tWater * 0.009);
      for (const f of flowTex) f.t.offset.y = (f.t.offset.y - dt * f.v) % 1;
      for (const s of spinners) s.o.rotateOnAxis(s.ax, s.v * dt);
    },
    dispose() {
      geo.dispose(); tmat.dispose();
      for (const t of new Set(Object.values(T))) if (t) t.dispose();
      for (const f of flowTex) f.t.dispose(); splatA.dispose(); splatB.dispose();
      for (const m of mats.values()) m.dispose();
      group.traverse((o) => { if (o.userData && o.userData.dispose) o.userData.dispose(); if (o.geometry) o.geometry.dispose(); });
    },
    group: new THREE.Group(),
  };
  // horário: troca o céu e acende as janelas à noite
  const setHora = (h) => {
    if (backdrop.userData.setHora) backdrop.userData.setHora(h);
    for (const g of glowMats) g.m.color.copy(g.base).multiplyScalar(h === 'noite' ? g.brilho : 0.85);
  };
  // telhados: o jogador os esconde na visão tática (olhando de cima)
  const setTelhados = (v) => { for (const o of telhados) o.visible = v && !topDown; };
  return { group, segments, doors: [], terrain, cenario: map.cenario, groundAt, standAt, waterAt, backdrop, bounds: { w: W, h: Hh },
    setHora, setTelhados, temTelhados: telhados.length > 0, luar: CEU ? CEU.luar || 0 : 0, ceuAberto: !!CEU };
}
