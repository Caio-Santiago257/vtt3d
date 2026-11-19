// Visual "anime": sombreamento em faixas (toon), contorno escuro e vento na vegetação.
import * as THREE from 'three';

// rampa de luz em 4 faixas: sombra, meia-sombra, luz, brilho
const ramp = new THREE.DataTexture(new Uint8Array([70, 70, 70, 255, 150, 150, 150, 255, 215, 215, 215, 255, 255, 255, 255, 255]), 4, 1, THREE.RGBAFormat);
ramp.minFilter = ramp.magFilter = THREE.NearestFilter; ramp.needsUpdate = true;

// rampa mais suave para a vegetação: as faixas ficam menos marcadas em formas redondas
const softRamp = new THREE.DataTexture(new Uint8Array([105, 140, 172, 200, 224, 242, 255, 255].flatMap((v) => [v, v, v, 255])), 8, 1, THREE.RGBAFormat);
softRamp.minFilter = softRamp.magFilter = THREE.NearestFilter; softRamp.needsUpdate = true;
export function toonSoft(opts = {}) { return new THREE.MeshToonMaterial({ gradientMap: softRamp, ...opts }); }

// rampa "anime": luz e sombra com uma transição curta e suave, sem os degraus que denunciam os polígonos
function smoothRamp(shadow, edge0, edge1) {
  const N = 256, data = new Uint8Array(N * 4);
  for (let i = 0; i < N; i++) {
    const x = i / (N - 1), t = Math.min(1, Math.max(0, (x - edge0) / (edge1 - edge0))), k = t * t * (3 - 2 * t);
    const v = Math.round(255 * (shadow + (1 - shadow) * k));
    data.set([v, v, v, 255], i * 4);
  }
  const tex = new THREE.DataTexture(data, N, 1, THREE.RGBAFormat);
  tex.minFilter = tex.magFilter = THREE.LinearFilter; tex.needsUpdate = true;
  return tex;
}
const animeRamp = smoothRamp(0.74, 0.42, 0.56);
export function toonAnime(opts = {}) { return new THREE.MeshToonMaterial({ gradientMap: animeRamp, ...opts }); }

export function toon(opts = {}) { return new THREE.MeshToonMaterial({ gradientMap: ramp, ...opts }); }

// Luz de borda e brilho especular em faixa, como nos JRPGs. Só entram nos assets que pedem
// (propriedades "rim" e "spec" gravadas no material do GLB); o resto do jogo continua igual.
export function addRimSpec(mat, { rim = 0, spec = 0, specSize = 0.9, rimColor = 0xffffff } = {}) {
  if (!rim && !spec) return mat;
  const prev = mat.onBeforeCompile;
  mat.onBeforeCompile = (shader, r) => {
    prev && prev(shader, r);
    shader.uniforms.uRim = { value: rim };
    shader.uniforms.uSpec = { value: spec };
    shader.uniforms.uSpecSize = { value: specSize };
    shader.uniforms.uRimColor = { value: new THREE.Color(rimColor) };
    shader.fragmentShader = 'uniform float uRim; uniform float uSpec; uniform float uSpecSize; uniform vec3 uRimColor;\n' +
      shader.fragmentShader.replace('#include <opaque_fragment>', `
        {
          vec3 V = normalize(vViewPosition);
          float ndv = clamp(dot(normal, V), 0.0, 1.0);
          float rimF = smoothstep(0.66, 0.72, 1.0 - ndv) * uRim;
          outgoingLight += uRimColor * rimF * (0.35 + 0.65 * diffuseColor.rgb);
          #if NUM_DIR_LIGHTS > 0
            vec3 L = directionalLights[0].direction;
            float h = clamp(dot(normal, normalize(L + V)), 0.0, 1.0);
            float sp = smoothstep(uSpecSize, uSpecSize + 0.02, h) * uSpec;
            outgoingLight += directionalLights[0].color * sp * 0.6;
          #endif
        }
        #include <opaque_fragment>`);
  };
  mat.customProgramCacheKey = () => `rimspec-${rim}-${spec}-${specSize}`;
  return mat;
}

export const wind = { value: 0 }; // tempo compartilhado; quem desenha a cena avança
// Faz o material balançar com o vento: quanto mais alto o vértice, mais ele se move.
export function windify(mat, factor) {
  const prev = mat.onBeforeCompile;
  mat.onBeforeCompile = (shader, r) => {
    prev && prev(shader, r);
    shader.uniforms.uWind = wind;
    shader.vertexShader = 'uniform float uWind;\n' + shader.vertexShader.replace('#include <begin_vertex>', `#include <begin_vertex>
      {
        float sw = transformed.y * transformed.y * ${factor.toFixed(4)};
        #ifdef USE_INSTANCING
          vec3 ip = instanceMatrix[3].xyz;
        #else
          vec3 ip = vec3(0.0);
        #endif
        transformed.x += sin(uWind * 1.3 + ip.x * 0.5 + ip.z * 0.3) * sw;
        transformed.z += cos(uWind * 1.1 + ip.z * 0.5) * sw * 0.7;
      }`);
  };
  mat.customProgramCacheKey = () => 'wind' + factor + (mat.userData.outline || 0);
  return mat;
}

// Material de contorno: a mesma malha desenhada pelo avesso, um pouco inflada.
export function outlineMaterial(width, color = 0x2b1c1a) {
  const mat = new THREE.MeshBasicMaterial({ color, side: THREE.BackSide });
  mat.userData.outline = width;
  mat.onBeforeCompile = (shader) => {
    shader.vertexShader = shader.vertexShader.replace('#include <begin_vertex>', `#include <begin_vertex>
      transformed += normalize(normal) * ${width.toFixed(4)};`);
  };
  mat.customProgramCacheKey = () => 'outline' + width;
  return mat;
}
const outlines = new Map();
const outlineFor = (w) => { if (!outlines.has(w)) outlines.set(w, outlineMaterial(w)); return outlines.get(w); };

// Adiciona contorno a um personagem (malhas com esqueleto e itens presos aos ossos).
export function addOutline(root) {
  const list = [];
  root.traverse((o) => {
    // tecidos transparentes, cartões de cabelo e olhos não ganham contorno (o casco invertido mostraria o retângulo)
    const mats = o.isMesh ? [].concat(o.material) : [];
    if (o.isMesh && o.visible && !o.userData.isOutline && !mats.some((m) => m.userData && m.userData.noOutline)) list.push(o);
  });
  for (const o of list) {
    // espessura vem do material (extra "outline", em metros do modelo); padrão do KayKit: 0,022
    const w = Math.max(...[].concat(o.material).map((x) => (x.userData && x.userData.outline) || 0.022));
    let m;
    if (o.isSkinnedMesh) { m = new THREE.SkinnedMesh(o.geometry, outlineFor(w)); m.bind(o.skeleton, o.bindMatrix); }
    else m = new THREE.Mesh(o.geometry, outlineFor(w));
    m.position.copy(o.position); m.quaternion.copy(o.quaternion); m.scale.copy(o.scale);
    m.frustumCulled = false; m.userData.isOutline = true;
    o.parent.add(m);
  }
}

// Brilho suave (chamas, vaga-lumes): textura radial para sprites e partículas.
let glowTex = null;
export function glowTexture() {
  if (glowTex) return glowTex;
  const c = document.createElement('canvas'); c.width = c.height = 64;
  const g = c.getContext('2d'), gr = g.createRadialGradient(32, 32, 0, 32, 32, 32);
  gr.addColorStop(0, 'rgba(255,255,255,1)'); gr.addColorStop(0.25, 'rgba(255,255,255,.55)'); gr.addColorStop(1, 'rgba(255,255,255,0)');
  g.fillStyle = gr; g.fillRect(0, 0, 64, 64);
  glowTex = new THREE.CanvasTexture(c);
  return glowTex;
}
