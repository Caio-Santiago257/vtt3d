// Iluminação dinâmica: horário do dia, fontes de luz, paredes bloqueando a luz e visão no escuro.
//
// Como funciona:
//  1. LightMap desenha, visto de cima, um mapa de luz do mapa inteiro: cada fonte ilumina só o polígono que ela
//     "enxerga" (paredes e portas fechadas cortam a luz). Luz plena = 1, penumbra = 0,42, escuridão = 0.
//     Um segundo canal marca até onde quem olha enxerga no escuro (visão no escuro, também cortada por paredes).
//  2. NightPass desenha a cena numa textura e, numa passada final, recupera a posição de cada pixel no mundo
//     pela profundidade, lê o mapa de luz ali e escurece, tinge ou deixa em tons de cinza. Vale para qualquer mapa,
//     peça ou personagem, sem mexer nos materiais. De dia, a mesma passada só dá cor (manhã viva, tarde dourada).
// Regras do Livro do Jogador 2024: tocha 6 m de luz plena + 6 m de penumbra; lanterna coberta 9 + 9; vela 1,5 + 1,5;
// magia Luz 6 + 6. Visão no escuro: dentro do alcance, penumbra vira luz plena e escuridão vira penumbra, só em cinza.
import * as THREE from 'three';

export const M2U = 4 / 3;   // unidades do mundo por metro
export const HORAS = [['manha', '☀ Manhã'], ['tarde', '🌇 Tarde'], ['noite', '🌙 Noite']];

// fontes que o mestre espalha pelo mapa (metros)
export const LUZES = {
  tocha: { nome: 'Tocha de parede', icone: '🔥', plena: 6, penumbra: 6, cor: 0xffa24a, fogo: 1 },
  poste: { nome: 'Tocha em poste', icone: '🔥', plena: 6, penumbra: 6, cor: 0xffa24a, fogo: 1 },
  fogueira: { nome: 'Fogueira', icone: '🏕', plena: 9, penumbra: 9, cor: 0xff9038, fogo: 1 },
  braseiro: { nome: 'Braseiro', icone: '♨', plena: 4.5, penumbra: 4.5, cor: 0xff8030, fogo: 1 },
  velas: { nome: 'Velas', icone: '🕯', plena: 1.5, penumbra: 1.5, cor: 0xffbf6a, fogo: 1 },
  candelabro: { nome: 'Candelabro', icone: '🕯', plena: 3, penumbra: 3, cor: 0xffc070, fogo: 1 },
  lanterna: { nome: 'Lanterna pendurada', icone: '🏮', plena: 9, penumbra: 9, cor: 0xffcf88, fogo: 0.6 },
  cristal: { nome: 'Cristal arcano', icone: '💎', plena: 6, penumbra: 6, cor: 0x7fd2ff, fogo: 0 },
  orbe: { nome: 'Luz mágica', icone: '✨', plena: 6, penumbra: 6, cor: 0xe6ecff, fogo: 0 },
  fatuo: { nome: 'Fogo-fátuo', icone: '👻', plena: 0, penumbra: 3, cor: 0x8cff7a, fogo: 0.3 },
  dia: { nome: 'Luz do Dia (magia)', icone: '☀', plena: 18, penumbra: 18, cor: 0xfff2d8, fogo: 0 },
};
// luz que o personagem carrega
export const LUZ_PESSOAL = {
  tocha: { nome: 'Tocha', plena: 6, penumbra: 6, cor: 0xffa24a, fogo: 1, peca: 'tocha_mao' },
  lanterna: { nome: 'Lanterna coberta', plena: 9, penumbra: 9, cor: 0xffcf88, fogo: 0.6, peca: 'lanterna_mao' },
  lanterna_baixa: { nome: 'Lanterna (capuz baixo)', plena: 0, penumbra: 1.5, cor: 0xffcf88, fogo: 0.6, peca: 'lanterna_mao' },
  vela: { nome: 'Vela', plena: 1.5, penumbra: 1.5, cor: 0xffbf6a, fogo: 1, peca: 'vela_mao' },
  luz: { nome: 'Magia Luz', plena: 6, penumbra: 6, cor: 0xeef2ff, fogo: 0, peca: 'orbe_mao' },
  dia: { nome: 'Luz do Dia', plena: 18, penumbra: 18, cor: 0xfff2d8, fogo: 0, peca: 'orbe_mao' },
};
// visão no escuro (metros) dos personagens da mesa: Guy é halfling (não tem), Kaira é aasimar (18 m), Ghult'ok é orc (36 m)
export const VISAO_ESCURO = { Guy: 0, Kaira: 18, Ghultok: 36 };

// ---------------------------------------------------------------- tempo e animação das chamas
export const luzTempo = { value: 0 };
const anim = new Set();
export function tickLuzes(t) { luzTempo.value = t; for (const f of anim) f(t); }

let _glow = null;
function glowTex() {
  if (_glow) return _glow;
  const c = document.createElement('canvas'); c.width = c.height = 64;
  const g = c.getContext('2d'), gr = g.createRadialGradient(32, 32, 0, 32, 32, 32);
  gr.addColorStop(0, 'rgba(255,255,255,1)'); gr.addColorStop(0.25, 'rgba(255,255,255,.55)'); gr.addColorStop(1, 'rgba(255,255,255,0)');
  g.fillStyle = gr; g.fillRect(0, 0, 64, 64);
  _glow = new THREE.CanvasTexture(c); _glow.colorSpace = THREE.SRGBColorSpace; return _glow;
}
// chama: um quadro sempre de frente para a câmera, com o formato e o tremor feitos no shader
function flameMat(color) {
  return new THREE.ShaderMaterial({
    uniforms: { uT: luzTempo, uC: { value: new THREE.Color(color) }, uSeed: { value: Math.random() * 50 } },
    vertexShader: `varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }`,
    fragmentShader: `uniform float uT; uniform vec3 uC; uniform float uSeed; varying vec2 vUv;
      float n(vec2 p){ return sin(p.x*7.1+uT*9.0+uSeed)*sin(p.y*5.3-uT*13.0+uSeed*1.7); }
      void main(){
        vec2 p = vUv - vec2(0.5, 0.18);
        float w = 0.30 * (1.0 - smoothstep(0.0, 0.82, p.y)) + 0.04;
        p.x += n(vUv*3.0) * 0.06 * vUv.y + sin(uT*6.0+uSeed)*0.03*vUv.y;
        float body = 1.0 - smoothstep(w*0.55, w, abs(p.x));
        body *= smoothstep(-0.16, 0.02, p.y) * (1.0 - smoothstep(0.55, 0.85, p.y + n(vUv*2.0)*0.06));
        float core = (1.0 - smoothstep(0.0, w*0.55, abs(p.x))) * (1.0 - smoothstep(0.05, 0.45, p.y)) * smoothstep(-0.12, 0.0, p.y);
        vec3 col = mix(uC*1.2, vec3(1.0, 0.97, 0.85), core);
        gl_FragColor = vec4(col * (body*1.3 + core), body);
        if (gl_FragColor.a < 0.01) discard;
      }`,
    transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, fog: false, side: THREE.DoubleSide,
  });
}
function flame(color, h = 0.5) {
  const m = new THREE.Mesh(new THREE.PlaneGeometry(h * 0.62, h), flameMat(color));
  m.geometry.translate(0, h * 0.32, 0);
  m.onBeforeRender = (r, s, cam) => {   // gira só em volta do eixo vertical para ficar de frente
    const p = new THREE.Vector3(); m.getWorldPosition(p);
    const a = Math.atan2(cam.position.x - p.x, cam.position.z - p.z), pq = new THREE.Quaternion();
    if (m.parent) m.parent.getWorldQuaternion(pq);
    m.quaternion.copy(pq.invert()).multiply(new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 1, 0), a));
  };
  m.renderOrder = 5; return m;
}
function halo(color, size, op = 0.55) {
  const s = new THREE.Sprite(new THREE.SpriteMaterial({ map: glowTex(), color, transparent: true, opacity: op, depthWrite: false, blending: THREE.AdditiveBlending, fog: false }));
  s.scale.setScalar(size); s.renderOrder = 4; return s;
}
const MAT = {};
const mat = (k, c, o = {}) => (MAT[k] = MAT[k] || new THREE.MeshStandardMaterial({ color: c, roughness: 0.85, metalness: 0, ...o }));
const glowMat = (c) => new THREE.MeshBasicMaterial({ color: c, fog: false });
const cyl = (r0, r1, h, m, seg = 8) => new THREE.Mesh(new THREE.CylinderGeometry(r0, r1, h, seg), m);

// ---------------------------------------------------------------- peças animadas de cada fonte de luz
// tipo: chave de LUZES ou de LUZ_PESSOAL (peca). top = vista de cima do mestre (mostra os alcances)
export function makeLightToken(tipo, { top = false } = {}) {
  const g = new THREE.Group(), L = LUZES[tipo] || LUZES.orbe, cor = L.cor;
  const updates = [];
  const bob = (o, amp, spd) => { const y0 = o.position.y, ph = Math.random() * 6; updates.push((t) => { o.position.y = y0 + Math.sin(t * spd + ph) * amp; }); };
  const pulse = (s, base, amp, spd) => { const ph = Math.random() * 6; updates.push((t) => { s.scale.setScalar(base * (1 + amp * Math.sin(t * spd + ph) * Math.sin(t * spd * 0.37 + ph))); }); };
  const fire = (x, y, z, h, haloS) => { const f = flame(cor, h); f.position.set(x, y, z); g.add(f); const hl = halo(cor, haloS); hl.position.set(x, y + h * 0.35, z); g.add(hl); pulse(hl, haloS, 0.12, 9); return f; };
  const wood = mat('madeira', 0x5a3a22), iron = mat('ferro', 0x3a3a40, { metalness: 0.6, roughness: 0.5 }), stone = mat('pedra', 0x77736c), wax = mat('cera', 0xf2e6cf);
  switch (tipo) {
    case 'tocha': {   // suporte de parede: placa, braço e tocha inclinada
      const plate = new THREE.Mesh(new THREE.BoxGeometry(0.28, 0.4, 0.05), iron); plate.position.set(0, 2.0, -0.02); g.add(plate);
      const stick = cyl(0.045, 0.035, 0.6, wood); stick.position.set(0, 2.15, 0.16); stick.rotation.x = 0.45; g.add(stick);
      const cup = cyl(0.09, 0.05, 0.12, iron); cup.position.set(0, 2.42, 0.28); cup.rotation.x = 0.45; g.add(cup);
      fire(0, 2.45, 0.3, 0.55, 1.6); break;
    }
    case 'poste': {
      const base = cyl(0.22, 0.28, 0.12, stone, 10); base.position.y = 0.06; g.add(base);
      const pole = cyl(0.05, 0.06, 1.9, wood); pole.position.y = 1.0; g.add(pole);
      const cup = cyl(0.13, 0.07, 0.16, iron, 10); cup.position.y = 2.0; g.add(cup);
      fire(0, 2.05, 0, 0.6, 1.7); break;
    }
    case 'fogueira': {
      for (let i = 0; i < 9; i++) { const a = (i / 9) * Math.PI * 2, s = new THREE.Mesh(new THREE.DodecahedronGeometry(0.17, 0), stone); s.position.set(Math.cos(a) * 0.62, 0.1, Math.sin(a) * 0.62); s.rotation.set(i, i * 2, 0); g.add(s); }
      for (let i = 0; i < 3; i++) { const l = cyl(0.07, 0.07, 0.95, wood); l.rotation.z = Math.PI / 2 - 0.35; l.rotation.y = (i / 3) * Math.PI; l.position.y = 0.2; g.add(l); }
      const brasa = new THREE.Mesh(new THREE.CircleGeometry(0.42, 16), glowMat(0xff5a1a)); brasa.rotation.x = -Math.PI / 2; brasa.position.y = 0.05; g.add(brasa);
      fire(0, 0.12, 0, 1.25, 3.4); fire(0.18, 0.1, 0.1, 0.8, 0.1); fire(-0.16, 0.1, -0.08, 0.9, 0.1);
      break;
    }
    case 'braseiro': {
      for (let i = 0; i < 3; i++) { const a = (i / 3) * Math.PI * 2, leg = cyl(0.03, 0.03, 0.9, iron); leg.position.set(Math.cos(a) * 0.22, 0.42, Math.sin(a) * 0.22); leg.rotation.z = Math.cos(a) * 0.25; leg.rotation.x = -Math.sin(a) * 0.25; g.add(leg); }
      const bowl = new THREE.Mesh(new THREE.CylinderGeometry(0.42, 0.22, 0.25, 14, 1, true), iron); bowl.position.y = 0.95; g.add(bowl);
      const brasa = new THREE.Mesh(new THREE.CircleGeometry(0.38, 14), glowMat(0xff6a20)); brasa.rotation.x = -Math.PI / 2; brasa.position.y = 1.0; g.add(brasa);
      fire(0, 1.0, 0, 0.85, 2.4); fire(0.12, 1.0, -0.1, 0.55, 0.1); break;
    }
    case 'velas': {
      [[0, 0, 0.32], [0.16, 0.08, 0.22], [-0.13, 0.1, 0.18]].forEach(([x, z, h]) => { const c = cyl(0.045, 0.05, h, wax); c.position.set(x, h / 2 + 0.75, z); g.add(c); fire(x, h + 0.75, z, 0.16, 0.5); });
      const mesa = cyl(0.3, 0.3, 0.05, wood, 12); mesa.position.y = 0.72; g.add(mesa); const pe = cyl(0.05, 0.08, 0.72, wood); pe.position.y = 0.36; g.add(pe);
      break;
    }
    case 'candelabro': {
      const pe = cyl(0.04, 0.16, 1.5, iron); pe.position.y = 0.75; g.add(pe);
      for (let i = -1; i <= 1; i++) { const arm = new THREE.Mesh(new THREE.BoxGeometry(0.03, 0.03, 0.01 + Math.abs(i) * 0.5), iron); arm.position.set(i * 0.22, 1.5, 0); arm.rotation.y = Math.PI / 2; g.add(arm); const c = cyl(0.04, 0.04, 0.2, wax); c.position.set(i * 0.25, 1.62, 0); g.add(c); fire(i * 0.25, 1.73, 0, 0.17, 0.55); }
      break;
    }
    case 'lanterna': {
      const pole = cyl(0.045, 0.06, 2.4, wood); pole.position.y = 1.2; g.add(pole);
      const arm = new THREE.Mesh(new THREE.BoxGeometry(0.5, 0.05, 0.05), wood); arm.position.set(0.25, 2.35, 0); g.add(arm);
      const lan = new THREE.Group(); lan.position.set(0.45, 2.0, 0); g.add(lan);
      const vidro = new THREE.Mesh(new THREE.BoxGeometry(0.2, 0.28, 0.2), new THREE.MeshBasicMaterial({ color: cor, transparent: true, opacity: 0.85, fog: false })); lan.add(vidro);
      const teto = new THREE.Mesh(new THREE.ConeGeometry(0.17, 0.12, 4), iron); teto.position.y = 0.2; teto.rotation.y = Math.PI / 4; lan.add(teto);
      for (const [x, z] of [[-1, -1], [1, -1], [1, 1], [-1, 1]]) { const b = cyl(0.012, 0.012, 0.3, iron, 4); b.position.set(x * 0.1, 0, z * 0.1); lan.add(b); }
      const fio = cyl(0.008, 0.008, 0.25, iron, 4); fio.position.set(0.45, 2.22, 0); g.add(fio);
      const hl = halo(cor, 1.8); lan.add(hl); pulse(hl, 1.8, 0.06, 7);
      updates.push((t) => { lan.rotation.z = Math.sin(t * 1.3) * 0.06; });
      break;
    }
    case 'cristal': {
      const cm = new THREE.MeshStandardMaterial({ color: cor, emissive: cor, emissiveIntensity: 1.4, roughness: 0.2, transparent: true, opacity: 0.92 });
      const base = new THREE.Mesh(new THREE.DodecahedronGeometry(0.35, 0), stone); base.scale.y = 0.5; base.position.y = 0.12; g.add(base);
      [[0, 0, 0.9, 0], [0.18, 0.08, 0.55, 0.4], [-0.15, -0.1, 0.65, -0.35]].forEach(([x, z, h, r]) => { const c = new THREE.Mesh(new THREE.OctahedronGeometry(0.16, 0), cm); c.scale.set(1, h / 0.32, 1); c.position.set(x, 0.25 + h / 2, z); c.rotation.z = r; g.add(c); });
      const hl = halo(cor, 2.6, 0.5); hl.position.y = 0.8; g.add(hl); pulse(hl, 2.6, 0.18, 2.2);
      break;
    }
    case 'fatuo': {
      for (let i = 0; i < 3; i++) {
        const o = new THREE.Group(); o.position.set((i - 1) * 0.35, 1.3 + i * 0.15, (i % 2) * 0.25); g.add(o);
        o.add(new THREE.Mesh(new THREE.SphereGeometry(0.06, 8, 6), glowMat(cor))); const hl = halo(cor, 0.9, 0.7); o.add(hl);
        const ph = i * 2.1; updates.push((t) => { o.position.x = (i - 1) * 0.35 + Math.sin(t * 0.9 + ph) * 0.25; o.position.y = 1.3 + i * 0.15 + Math.sin(t * 1.7 + ph) * 0.15; hl.material.opacity = 0.5 + 0.3 * Math.sin(t * 3 + ph); });
      }
      break;
    }
    case 'dia': case 'orbe': default: {
      const big = tipo === 'dia';
      const o = new THREE.Group(); o.position.y = big ? 2.6 : 1.8; g.add(o);
      o.add(new THREE.Mesh(new THREE.SphereGeometry(big ? 0.22 : 0.12, 16, 12), glowMat(cor)));
      const hl = halo(cor, big ? 4.5 : 1.6, 0.75); o.add(hl); pulse(hl, big ? 4.5 : 1.6, 0.08, 3);
      bob(o, 0.08, 1.6);
      break;
    }
    // ---- luzes carregadas na mão (presas no osso da mão do personagem)
    case 'tocha_mao': { const s = cyl(0.03, 0.025, 0.45, wood); s.position.y = 0.1; g.add(s); fire(0, 0.32, 0, 0.36, 1.1); break; }
    case 'lanterna_mao': {
      const v = new THREE.Mesh(new THREE.BoxGeometry(0.12, 0.16, 0.12), new THREE.MeshBasicMaterial({ color: 0xffcf88, transparent: true, opacity: 0.85, fog: false })); v.position.y = -0.12; g.add(v);
      const t2 = new THREE.Mesh(new THREE.ConeGeometry(0.1, 0.07, 4), iron); t2.position.y = -0.01; t2.rotation.y = Math.PI / 4; g.add(t2);
      const hl = halo(0xffcf88, 1.2); hl.position.y = -0.12; g.add(hl); pulse(hl, 1.2, 0.05, 7); break;
    }
    case 'vela_mao': { const c = cyl(0.03, 0.03, 0.14, wax); c.position.y = 0.05; g.add(c); fire(0, 0.12, 0, 0.12, 0.4); break; }
    case 'orbe_mao': { const o = new THREE.Group(); o.position.y = 0.35; g.add(o); o.add(new THREE.Mesh(new THREE.SphereGeometry(0.07, 12, 8), glowMat(0xeef2ff))); const hl = halo(0xeef2ff, 1.0, 0.8); o.add(hl); bob(o, 0.05, 2); break; }
  }
  // vista do mestre: anéis da luz plena (amarelo) e da penumbra (laranja) para ver até onde a luz chega
  if (top && LUZES[tipo]) {
    const ring = (r, c, op) => { const m = new THREE.Mesh(new THREE.RingGeometry(Math.max(0.01, r - 0.08), r, 64), new THREE.MeshBasicMaterial({ color: c, transparent: true, opacity: op, depthTest: false })); m.rotation.x = -Math.PI / 2; m.position.y = 4.3; m.renderOrder = 6; return m; };
    if (L.plena) g.add(ring(L.plena * M2U, 0xffe27a, 0.75));
    g.add(ring((L.plena + L.penumbra) * M2U, 0xff9a4a, 0.5));
    const dot = new THREE.Mesh(new THREE.CircleGeometry(0.35, 16), new THREE.MeshBasicMaterial({ color: cor, depthTest: false })); dot.rotation.x = -Math.PI / 2; dot.position.y = 4.35; dot.renderOrder = 7; g.add(dot);
  }
  const upd = (t) => { for (const f of updates) f(t); };
  if (updates.length) anim.add(upd);
  g.userData.dispose = () => anim.delete(upd);
  g.userData.luz = true;
  return g;
}

// ---------------------------------------------------------------- polígono do que uma luz alcança
// Varredura por ângulo: um raio para cada ponta de parede (e um pouco antes e depois); o polígono é o
// ponto mais próximo que cada raio toca. Fica dentro de um quadrado do tamanho do alcance.
export function visPoly(px, pz, R, segs) {
  const all = [];
  for (const s of segs) {
    if (Math.min(s.x1, s.x2) > px + R || Math.max(s.x1, s.x2) < px - R || Math.min(s.z1, s.z2) > pz + R || Math.max(s.z1, s.z2) < pz - R) continue;
    // parede passando bem em cima da luz (tocha encostada): não conta, senão a luz some
    const ex = s.x2 - s.x1, ez = s.z2 - s.z1, l2 = ex * ex + ez * ez || 1, k = Math.max(0, Math.min(1, ((px - s.x1) * ex + (pz - s.z1) * ez) / l2));
    if (Math.hypot(s.x1 + ex * k - px, s.z1 + ez * k - pz) < 0.04) continue;
    all.push(s);
  }
  const x0 = px - R, x1 = px + R, z0 = pz - R, z1 = pz + R;
  all.push({ x1: x0, z1: z0, x2: x1, z2: z0 }, { x1: x1, z1: z0, x2: x1, z2: z1 }, { x1: x1, z1: z1, x2: x0, z2: z1 }, { x1: x0, z1: z1, x2: x0, z2: z0 });
  const angs = [];
  for (const s of all) for (const [x, z] of [[s.x1, s.z1], [s.x2, s.z2]]) { const a = Math.atan2(z - pz, x - px); angs.push(a - 1e-4, a, a + 1e-4); }
  for (let i = 0; i < 32; i++) angs.push(-Math.PI + (i / 32) * Math.PI * 2);
  angs.sort((a, b) => a - b);
  const pts = [];
  for (const a of angs) {
    const dx = Math.cos(a), dz = Math.sin(a);
    let tmin = Infinity;
    for (const s of all) {
      const ex = s.x2 - s.x1, ez = s.z2 - s.z1, den = dx * ez - dz * ex;
      if (Math.abs(den) < 1e-9) continue;
      const qx = s.x1 - px, qz = s.z1 - pz, t = (qx * ez - qz * ex) / den, u = (qx * dz - qz * dx) / den;
      if (t > 1e-6 && u >= -1e-6 && u <= 1 + 1e-6 && t < tmin) tmin = t;
    }
    if (tmin < Infinity) pts.push(px + dx * tmin, pz + dz * tmin);
  }
  return pts;
}

// ---------------------------------------------------------------- mapa de luz visto de cima
export class LightMap {
  constructor() {
    this.cv = document.createElement('canvas'); this.cx = this.cv.getContext('2d');
    this.dv = document.createElement('canvas'); this.dx = this.dv.getContext('2d');
    this.tex = new THREE.CanvasTexture(this.cv); this.dvTex = new THREE.CanvasTexture(this.dv);
    for (const t of [this.tex, this.dvTex]) { t.minFilter = t.magFilter = THREE.LinearFilter; t.generateMipmaps = false; t.flipY = false; }
    this.segs = []; this.lights = []; this.sigL = ''; this.sigS = ''; this.viewer = null; this.sigV = '';
    this.bounds = { x: 0, z: 0, w: 1, h: 1 }; this.k = 8; this.polys = new Map();
  }
  setBounds(x, z, w, h) {
    const k = Math.max(2, Math.min(10, 1400 / Math.max(w, h)));
    if (this.bounds.x === x && this.bounds.z === z && this.bounds.w === w && this.bounds.h === h) return;
    this.bounds = { x, z, w, h }; this.k = k;
    this.cv.width = this.dv.width = Math.ceil(w * k); this.cv.height = this.dv.height = Math.ceil(h * k);
    this.tex.dispose(); this.dvTex.dispose();
    this.tex = new THREE.CanvasTexture(this.cv); this.dvTex = new THREE.CanvasTexture(this.dv);
    for (const t of [this.tex, this.dvTex]) { t.minFilter = t.magFilter = THREE.LinearFilter; t.generateMipmaps = false; t.flipY = false; }
    this.polys.clear(); this.sigL = this.sigV = '#';
  }
  // segmentos que bloqueiam a luz: paredes altas e portas fechadas
  setSegments(segs) {
    const sig = segs.length + ':' + segs.reduce((a, s) => a + s.x1 * 3 + s.z1 * 7 + s.x2 * 11 + s.z2 * 13, 0).toFixed(2);
    if (sig === this.sigS) return;
    this.sigS = sig; this.segs = segs; this.polys.clear(); this.sigL = this.sigV = '#';
  }
  // lights: [{ key, x, z, plena, penumbra (unidades), cor (THREE.Color) }]
  setLights(lights) {
    const sig = lights.map((l) => `${l.key}:${l.x.toFixed(2)},${l.z.toFixed(2)},${l.plena},${l.penumbra},${l.cor.getHexString()}`).join('|');
    if (sig === this.sigL) return;
    this.sigL = sig; this.lights = lights; this.draw();
  }
  setViewer(x, z, dv) {   // dv em unidades (0 = sem visão no escuro)
    const sig = dv ? `${x.toFixed(1)},${z.toFixed(1)},${dv}` : '0';
    if (sig === this.sigV) return;
    this.sigV = sig; this.viewer = dv ? { x, z, dv } : null; this.drawDV();
  }
  poly(key, x, z, R) {
    const id = `${key}:${x.toFixed(2)},${z.toFixed(2)},${R}`;
    let p = this.polys.get(id);
    if (!p) { p = visPoly(x, z, R, this.segs); this.polys.set(id, p); if (this.polys.size > 400) this.polys.delete(this.polys.keys().next().value); }
    return p;
  }
  path(ctx, pts) {
    const { x, z } = this.bounds, k = this.k;
    ctx.beginPath();
    for (let i = 0; i < pts.length; i += 2) { const X = (pts[i] - x) * k, Y = (pts[i + 1] - z) * k; i ? ctx.lineTo(X, Y) : ctx.moveTo(X, Y); }
    ctx.closePath();
  }
  draw() {
    const c = this.cx, { x, z } = this.bounds, k = this.k;
    c.globalCompositeOperation = 'source-over'; c.fillStyle = '#000'; c.fillRect(0, 0, this.cv.width, this.cv.height);
    c.globalCompositeOperation = 'lighten';   // luz sobre luz não soma: vale a mais forte
    for (const l of this.lights) {
      const R = l.plena + l.penumbra; if (R <= 0) continue;
      const pts = this.poly(l.key, l.x, l.z, R);
      c.save(); this.path(c, pts); c.clip();
      const X = (l.x - x) * k, Y = (l.z - z) * k, gr = c.createRadialGradient(X, Y, 0, X, Y, R * k);
      const r = Math.round(l.cor.r * 255), g = Math.round(l.cor.g * 255), b = Math.round(l.cor.b * 255);
      const m = Math.max(r, g, b) || 1, full = `rgb(${Math.round(r / m * 255)},${Math.round(g / m * 255)},${Math.round(b / m * 255)})`;
      const dim = `rgb(${Math.round(r / m * 107)},${Math.round(g / m * 107)},${Math.round(b / m * 107)})`;
      const pb = l.plena / R;
      if (l.plena > 0) { gr.addColorStop(0, full); gr.addColorStop(Math.max(0, pb - 0.04), full); gr.addColorStop(Math.min(1, pb + 0.04), dim); }
      else gr.addColorStop(0, dim);
      gr.addColorStop(0.9, dim); gr.addColorStop(1, 'rgb(0,0,0)');
      c.fillStyle = gr; c.fillRect(X - R * k, Y - R * k, R * k * 2, R * k * 2);
      c.restore();
    }
    this.tex.needsUpdate = true;
  }
  drawDV() {
    const c = this.dx; c.fillStyle = '#000'; c.fillRect(0, 0, this.dv.width, this.dv.height);
    const v = this.viewer;
    if (v) {
      const { x, z } = this.bounds, k = this.k, pts = this.poly('dv', v.x, v.z, v.dv);
      c.save(); this.path(c, pts); c.clip();
      const X = (v.x - x) * k, Y = (v.z - z) * k, gr = c.createRadialGradient(X, Y, 0, X, Y, v.dv * k);
      gr.addColorStop(0, '#fff'); gr.addColorStop(0.9, '#fff'); gr.addColorStop(1, '#000');
      c.fillStyle = gr; c.fillRect(X - v.dv * k, Y - v.dv * k, v.dv * k * 2, v.dv * k * 2); c.restore();
    }
    this.dvTex.needsUpdate = true;
  }
}

// ---------------------------------------------------------------- passada final: horário, escuridão e visão no escuro
export class NightPass {
  constructor(renderer, { mobile = false } = {}) {
    this.renderer = renderer;
    const gl2 = renderer.capabilities.isWebGL2;
    this.rt = new THREE.WebGLRenderTarget(1, 1, {
      type: gl2 ? THREE.HalfFloatType : THREE.UnsignedByteType, samples: gl2 ? (mobile ? 2 : 4) : 0,
      depthTexture: new THREE.DepthTexture(1, 1),
    });
    this.rt.depthTexture.type = THREE.UnsignedIntType;
    this.mat = new THREE.ShaderMaterial({
      uniforms: {
        tColor: { value: this.rt.texture }, tDepth: { value: this.rt.depthTexture }, tLuz: { value: null }, tDV: { value: null },
        uInvProj: { value: new THREE.Matrix4() }, uCamWorld: { value: new THREE.Matrix4() }, uCam: { value: new THREE.Vector3() },
        uMapa: { value: new THREE.Vector4(0, 0, 1, 1) }, uHora: { value: 0 }, uAmb: { value: 0.025 }, uDV: { value: 0 }, uT: luzTempo,
      },
      vertexShader: 'varying vec2 vUv; void main(){ vUv = uv; gl_Position = vec4(position.xy, 0.0, 1.0); }',
      fragmentShader: `
        uniform sampler2D tColor, tDepth, tLuz, tDV;
        uniform mat4 uInvProj, uCamWorld; uniform vec3 uCam; uniform vec4 uMapa;
        uniform float uHora, uAmb, uDV, uT;
        varying vec2 vUv;
        vec3 sat(vec3 c, float s){ float l = dot(c, vec3(0.2126, 0.7152, 0.0722)); return mix(vec3(l), c, s); }
        void main(){
          vec3 col = texture2D(tColor, vUv).rgb;
          if (uHora > 1.5) {   // noite
            float d = texture2D(tDepth, vUv).x;
            vec4 vp = uInvProj * vec4(vUv * 2.0 - 1.0, d * 2.0 - 1.0, 1.0); vp /= vp.w;
            vec3 wp = (uCamWorld * vp).xyz;
            // lê a luz um pouco para o lado de quem olha: a face da parede virada para a luz acende, a de trás não
            vec2 toC = uCam.xz - wp.xz; float L = length(toC);
            vec2 sxz = wp.xz + (L > 0.001 ? toC / L * min(0.25, L) : vec2(0.0));
            vec2 uv = (sxz - uMapa.xy) / uMapa.zw;
            bool fora = d >= 0.99999 || uv.x < 0.0 || uv.y < 0.0 || uv.x > 1.0 || uv.y > 1.0;
            vec3 luz = fora ? vec3(0.0) : texture2D(tLuz, uv).rgb;
            float dv = (fora || uDV < 0.5) ? 0.0 : texture2D(tDV, uv).r;
            float lvl = max(luz.r, max(luz.g, luz.b));
            vec3 tint = lvl > 0.001 ? luz / lvl : vec3(1.0);
            float flick = 1.0 + 0.05 * sin(uT * 11.0 + wp.x * 0.9) * sin(uT * 7.3 + wp.z * 1.1);
            float f = clamp(lvl / 0.75, 0.0, 1.0) * mix(1.0, flick, step(0.05, lvl));
            vec3 aceso = col * mix(vec3(1.0), tint, 0.5);
            vec3 escuro = col * uAmb * vec3(0.65, 0.75, 1.0);
            vec3 res = mix(escuro, aceso, f);
            res = sat(res, mix(0.6, 1.0, smoothstep(0.5, 0.8, lvl)));   // penumbra tem menos cor
            if (dv > 0.0) {
              // visão no escuro: penumbra vira luz plena; escuridão vira penumbra, só em cinza
              float fd = smoothstep(0.05, 0.3, lvl);
              float g = dot(col, vec3(0.2126, 0.7152, 0.0722));
              vec3 cinza = vec3(g) * 0.6 * vec3(0.92, 0.96, 1.0);
              res = mix(res, max(res, mix(cinza, aceso, fd)), dv);
            }
            col = res;
          } else if (uHora > 0.5) {   // tarde: luz dourada e sombras mais quentes
            float l = dot(col, vec3(0.2126, 0.7152, 0.0722));
            col = sat(col, 1.1) * mix(vec3(0.95, 0.74, 0.62), vec3(1.12, 0.92, 0.72), smoothstep(0.0, 0.6, l));
          } else {   // manhã: cores vivas
            col = sat(col, 1.18) * 1.03;
          }
          gl_FragColor = vec4(col, 1.0);
          #include <colorspace_fragment>
        }`,
      depthTest: false, depthWrite: false,
    });
    this.quad = new THREE.Mesh(new THREE.PlaneGeometry(2, 2), this.mat); this.quad.frustumCulled = false;
    this.scene = new THREE.Scene(); this.scene.add(this.quad); this.cam = new THREE.Camera();
  }
  setSize(w, h) { this.rt.setSize(w, h); }
  // hora: 'manha' | 'tarde' | 'noite'; lm: LightMap; opts: { amb, dv }
  render(scene, camera, hora, lm, { amb = 0.025, dv = false } = {}) {
    const r = this.renderer, s = r.getDrawingBufferSize(new THREE.Vector2());
    if (this.rt.width !== s.x || this.rt.height !== s.y) this.rt.setSize(s.x, s.y);
    r.setRenderTarget(this.rt); r.render(scene, camera); r.setRenderTarget(null);
    const u = this.mat.uniforms;
    u.uHora.value = hora === 'noite' ? 2 : hora === 'tarde' ? 1 : 0;
    camera.updateMatrixWorld();
    u.uInvProj.value.copy(camera.projectionMatrixInverse); u.uCamWorld.value.copy(camera.matrixWorld); u.uCam.value.setFromMatrixPosition(camera.matrixWorld);
    if (lm) { u.tLuz.value = lm.tex; u.tDV.value = lm.dvTex; u.uMapa.value.set(lm.bounds.x, lm.bounds.z, lm.bounds.w, lm.bounds.h); }
    u.uAmb.value = amb; u.uDV.value = dv ? 1 : 0;
    r.render(this.scene, this.cam);
  }
}
