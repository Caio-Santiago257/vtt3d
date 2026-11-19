// Kits de cenário feitos no Blender (árvores, plantas, pedras, objetos): cada nó do GLB é uma peça, e o jogo espalha
// cópias (InstancedMesh). Os materiais vêm de "extras": qual textura usar, se é cartão recortado, quanto balança
// com o vento e se é copa (fica translúcida na vista de cima do mestre). Usado pelos mapas prontos e pelo terreno pintado.
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { toonSoft } from './gfx.js';

const texLoader = new THREE.TextureLoader();
const gltfLoader = new GLTFLoader();
export const kitWind = { value: 0 };                 // tempo do vento, compartilhado por todos os kits
const texCache = new Map(), kitCache = new Map();

function loadTex(url, srgb) {
  if (!texCache.has(url)) texCache.set(url, texLoader.loadAsync(url).then((t) => {
    t.colorSpace = srgb ? THREE.SRGBColorSpace : THREE.NoColorSpace; t.wrapS = t.wrapT = THREE.RepeatWrapping; t.anisotropy = 4; return t;
  }));
  return texCache.get(url);
}

async function material(src, texBase, topDown) {
  const ex = src.userData || {};
  const map = ex.tex ? await loadTex(`${texBase}${ex.tex}.${ex.card ? 'png' : 'jpg'}`, true).catch(() => null) : null;
  const normalMap = ex.normal && !ex.card ? await loadTex(`${texBase}${ex.normal}.png`, false).catch(() => null) : null;
  const tint = ex.tint ? new THREE.Color(...ex.tint) : new THREE.Color(1, 1, 1);
  const m = toonSoft({ color: tint, map, normalMap, side: ex.card ? THREE.DoubleSide : THREE.FrontSide, alphaTest: ex.card ? 0.5 : 0 });
  if (ex.card) m.alphaToCoverage = true;
  if (topDown && ex.copa) { m.transparent = true; m.opacity = 0.78; }
  if (ex.vento && !topDown) {
    m.onBeforeCompile = (sh) => {
      sh.uniforms.uVento = kitWind; sh.uniforms.uAmp = { value: ex.vento };
      sh.vertexShader = sh.vertexShader.replace('#include <common>', '#include <common>\nuniform float uVento, uAmp;')
        .replace('#include <begin_vertex>', `#include <begin_vertex>
#ifdef USE_INSTANCING
vec2 ph = instanceMatrix[3].xz;
#else
vec2 ph = vec2(0.0);
#endif
float hh = max(transformed.y, 0.0);
float sw = sin(uVento * 1.7 + ph.x * 0.31 + ph.y * 0.17) + 0.4 * sin(uVento * 3.9 + ph.x * 0.7 + transformed.x * 0.8);
transformed.x += sw * uAmp * hh;
transformed.z += cos(uVento * 1.3 + ph.y * 0.29) * uAmp * hh * 0.6;`);
    };
    m.customProgramCacheKey = () => 'kitvento' + ex.vento;
  }
  return m;
}

// Carrega um ou mais GLB de kit. Devolve Map(nome da peça -> [{ geometry, material, copa }]).
// A geometria fica no espaço da peça (a base no chão, em y = 0).
export function loadKit(urls, { texBase, topDown = false }) {
  const key = urls.join('|') + (topDown ? '#top' : '');
  if (kitCache.has(key)) return kitCache.get(key);
  const p = (async () => {
    const out = new Map(), mats = new Map();
    for (const url of urls) {
      const g = await gltfLoader.loadAsync(url);
      g.scene.updateMatrixWorld(true);
      for (const node of g.scene.children) {
        const inv = new THREE.Matrix4().copy(node.matrixWorld).invert();
        const parts = [];
        const meshes = []; node.traverse((o) => { if (o.isMesh) meshes.push(o); });
        for (const mesh of meshes) {
          if (!mats.has(mesh.material)) mats.set(mesh.material, await material(mesh.material, texBase, topDown));
          parts.push({ geometry: mesh.geometry.clone().applyMatrix4(new THREE.Matrix4().multiplyMatrices(inv, mesh.matrixWorld)),
            material: mats.get(mesh.material), copa: !!(mesh.material.userData && mesh.material.userData.copa) });
        }
        out.set(node.name, parts);
      }
    }
    return out;
  })();
  kitCache.set(key, p);
  return p;
}

// Espalha as cópias: instancias = { peça: [[x, y, z, giro, escala, tom], ...] }. As cópias são separadas em blocos
// (chunk unidades) para a câmera só desenhar os blocos que estão na frente dela.
const _m = new THREE.Matrix4(), _p = new THREE.Vector3(), _q = new THREE.Quaternion(), _s = new THREE.Vector3(), _c = new THREE.Color(), UP = new THREE.Vector3(0, 1, 0);
export function instanceKit(kit, instancias, { topDown = false, chunk = 107, origin = 0 } = {}) {
  const group = new THREE.Group(); group.name = 'kit';
  group.dispose = () => group.children.forEach((o) => o.dispose());
  for (const [name, list] of Object.entries(instancias)) {
    const parts = kit.get(name); if (!parts || !list.length) continue;
    const chunks = new Map();
    for (const it of list) { const k = Math.floor((it[0] - origin) / chunk) + ',' + Math.floor((it[2] - origin) / chunk); if (!chunks.has(k)) chunks.set(k, []); chunks.get(k).push(it); }
    for (const part of parts) for (const items of chunks.values()) {
      const im = new THREE.InstancedMesh(part.geometry, part.material, items.length);
      items.forEach(([x, y, z, ry, sc, tint], k) => {
        im.setMatrixAt(k, _m.compose(_p.set(x, y, z), _q.setFromAxisAngle(UP, ry), _s.set(sc, sc, sc)));
        im.setColorAt(k, _c.setScalar(tint ?? 1));
      });
      im.computeBoundingSphere(); im.name = name;
      if (topDown && part.copa) im.renderOrder = 2;
      group.add(im);
    }
  }
  return group;
}
