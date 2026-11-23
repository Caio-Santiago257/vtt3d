// Mapa do mundo (Faerûn) e imagem do teatro da mente, usados pela tela do jogador e pela do mestre.
// O mapa é uma imagem grande que se arrasta e se aproxima com os dedos (ou o mouse). Por cima:
//  - régua: arraste para medir em milhas e km, com o tempo de viagem a pé (Livro do Jogador 2024);
//  - rota: toque ponto a ponto para planejar uma viagem e salve; todos veem as rotas salvas;
//  - ping: segure o dedo (ou o botão esquerdo) parado num ponto; o ping do mestre leva a tela dos jogadores até lá;
//  - lugares: pontos com um pouco da lore das cidades e lugares de interesse (liga e desliga).
// Réguas e rotas sendo desenhadas aparecem ao vivo para todos (mensagem "traco").

const h = (tag, cls, txt) => { const e = document.createElement(tag); if (cls) e.className = cls; if (txt !== undefined) e.textContent = txt; return e; };
const SVGNS = 'http://www.w3.org/2000/svg';
const sv = (tag, attrs = {}) => { const e = document.createElementNS(SVGNS, tag); for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v); return e; };
export const COR_HEROI = { Guy: '#ffd36b', Kaira: '#c9a8ff', Ghultok: '#ff7a5a', '': '#7fe0ff' };
export const corDe = (hero, gm) => (gm ? '#7fe0ff' : COR_HEROI[hero] || '#9fe0c0');
const fmt1 = (v) => (Math.round(v * 10) / 10).toString().replace('.', ',');
const fmtInt = (v) => Math.round(v).toLocaleString('pt-BR');
// ritmo de viagem por dia (8 h de marcha): rápido 30, normal 24, lento 18 milhas
export function viagem(mi) {
  if (mi < 0.5) return '';
  const d = (v) => (v < 1 ? `${fmt1(v * 8)} h` : `${fmt1(v)} ${v < 1.95 ? 'dia' : 'dias'}`);
  return `a pé: ${d(mi / 24)} (normal) · ${d(mi / 30)} rápido · ${d(mi / 18)} lento`;
}
export const distTxt = (mi) => `${fmtInt(mi)} mi · ${fmtInt(mi * 1.609)} km`;
const TIPO_ICONE = { capital: '★', cidade: '●', fortaleza: '■', ruina: '✕', local: '▲', regiao: '◆' };
const TIPO_NOME = { capital: 'Capital', cidade: 'Cidade', fortaleza: 'Fortaleza', ruina: 'Ruína', local: 'Lugar de interesse', regiao: 'Região' };

// ---------------------------------------------------------------- arrastar e aproximar uma imagem
// Desenha num canvas só o pedaço visível, com a versão da imagem que basta para o zoom atual:
// afastado usa a pequena (1/4), no meio a de 1/2, e a grande só é baixada e decodificada quando alguém aproxima.
// Assim o celular não precisa reescalar 15 megapixels a cada movimento.
class PanZoom {
  constructor(root, w, h) {
    this.root = root; this.w = w; this.h = h; this.s = 1; this.tx = 0; this.ty = 0; this.anim = null;
    this.cv = document.createElement('canvas'); this.cv.className = 'pz-canvas'; root.appendChild(this.cv);
    this.cx = this.cv.getContext('2d', { alpha: false });
    this.fontes = [];   // [{ url, f, bmp, loading }]  f = pixels da imagem por pixel da fonte
    this.listeners = [];
  }
  // fontes da maior redução para a menor; a primeira é carregada já
  setSources(list, w, h) {
    this.w = w; this.h = h;
    for (const f of this.fontes) if (f.bmp && f.bmp.close) f.bmp.close();
    this.fontes = list.map((q) => ({ ...q })); this.load(this.fontes[0]);
  }
  setImage(url, w, h) { this.setSources([{ url, f: 1 }], w, h); }
  async load(fo) {
    if (fo.bmp || fo.loading) return;
    fo.loading = true;
    try {
      const blob = await (await fetch(fo.url)).blob();
      fo.bmp = 'createImageBitmap' in window ? await createImageBitmap(blob) : await new Promise((ok, no) => { const i = new Image(); i.onload = () => ok(i); i.onerror = no; i.src = URL.createObjectURL(blob); });
    } catch (e) { console.warn('imagem', fo.url, e); }
    fo.loading = false; this.render(); this.onLoad && this.onLoad(fo);
  }
  get box() { return this.root.getBoundingClientRect(); }
  fitScale() { const b = this.box; return Math.min(b.width / this.w, b.height / this.h) || 1; }
  fit() { const b = this.box, s = this.fitScale(); this.set(s, (b.width - this.w * s) / 2, (b.height - this.h * s) / 2); }
  set(s, tx, ty) {
    const b = this.box, fs = this.fitScale();
    this.s = Math.max(fs * 0.8, Math.min(Math.max(3, fs * 2), s));
    // a imagem não sai inteira da tela: sempre sobra um pedaço dela à vista
    const W = this.w * this.s, H = this.h * this.s, mx = b.width * 0.5, my = b.height * 0.5;
    this.tx = Math.min(b.width - mx, Math.max(mx - W, tx)); this.ty = Math.min(b.height - my, Math.max(my - H, ty));
    if (W < b.width) this.tx = Math.min(Math.max(this.tx, 0), b.width - W);
    if (H < b.height) this.ty = Math.min(Math.max(this.ty, 0), b.height - H);
    this.render();
    for (const f of this.listeners) f();
  }
  render() {
    if (this.raf) return;
    this.raf = requestAnimationFrame(() => { this.raf = 0; this.paint(); });
  }
  paint() {
    if (this.root.hidden) return;
    const b = this.box, dpr = Math.min(window.devicePixelRatio || 1, 2);
    const W = Math.round(b.width * dpr), H = Math.round(b.height * dpr);
    if (this.cv.width !== W || this.cv.height !== H) { this.cv.width = W; this.cv.height = H; }
    const cx = this.cx; cx.fillStyle = '#0d1a24'; cx.fillRect(0, 0, W, H);
    // fonte ideal: a mais leve em que cada pixel dela ocupa no máximo ~1,3 pixel da tela
    const k = this.s * dpr;
    let want = this.fontes.length - 1;
    for (let i = 0; i < this.fontes.length; i++) if (k * this.fontes[i].f <= 1.3) { want = i; break; }
    if (!this.fontes[want]) return;
    this.load(this.fontes[want]);
    let fo = this.fontes[want];
    if (!fo.bmp) fo = [...this.fontes].reverse().find((q) => q.bmp) || null;   // enquanto carrega, usa a que já tem
    if (!fo) return;
    // só o retângulo visível
    const ix0 = Math.max(0, -this.tx / this.s), iy0 = Math.max(0, -this.ty / this.s);
    const ix1 = Math.min(this.w, (b.width - this.tx) / this.s), iy1 = Math.min(this.h, (b.height - this.ty) / this.s);
    if (ix1 <= ix0 || iy1 <= iy0) return;
    const sw = fo.bmp.width / this.w, sh = fo.bmp.height / this.h;
    cx.imageSmoothingEnabled = true; cx.imageSmoothingQuality = k * fo.f < 0.6 ? 'medium' : 'low';
    cx.drawImage(fo.bmp, ix0 * sw, iy0 * sh, (ix1 - ix0) * sw, (iy1 - iy0) * sh,
      (ix0 * this.s + this.tx) * dpr, (iy0 * this.s + this.ty) * dpr, (ix1 - ix0) * this.s * dpr, (iy1 - iy0) * this.s * dpr);
  }
  zoomAt(f, sx, sy) { const ix = (sx - this.tx) / this.s, iy = (sy - this.ty) / this.s, s = this.s * f; this.set(s, sx - ix * s, sy - iy * s); }
  toScreen(x, y) { return { x: x * this.s + this.tx, y: y * this.s + this.ty }; }
  toImage(cx, cy) { const b = this.box; return { x: (cx - b.left - this.tx) / this.s, y: (cy - b.top - this.ty) / this.s }; }
  // desliza até deixar (x, y) no centro, com o zoom s
  flyTo(x, y, s, ms = 900) {
    const b = this.box, s0 = this.s, c0 = this.toImage(b.left + b.width / 2, b.top + b.height / 2), t0 = performance.now();
    cancelAnimationFrame(this.anim);
    const step = () => {
      const k = Math.min(1, (performance.now() - t0) / ms), e = k < 0.5 ? 4 * k * k * k : 1 - Math.pow(-2 * k + 2, 3) / 2;
      const ss = s0 + (s - s0) * e, cx = c0.x + (x - c0.x) * e, cy = c0.y + (y - c0.y) * e;
      this.set(ss, b.width / 2 - cx * ss, b.height / 2 - cy * ss);
      if (k < 1) this.anim = requestAnimationFrame(step);
    };
    step();
  }
}
function h_(tag, cls) { const e = document.createElement(tag); e.className = cls; return e; }

// gestos: um dedo (ou mouse) chama a ferramenta; dois dedos sempre arrastam e aproximam
function gestures(pz, el, tool) {
  const ptrs = new Map(); let pinch = null, one = null, lp = 0;
  el.addEventListener('pointerdown', (e) => {
    if (e.target.closest('.mu-ui, .mesa-voltar')) return;
    e.preventDefault();
    try { el.setPointerCapture(e.pointerId); } catch {}
    ptrs.set(e.pointerId, { x: e.clientX, y: e.clientY });
    clearTimeout(lp);
    if (ptrs.size === 2) {
      if (one && one.drag) tool.cancel && tool.cancel();
      one = null; const [a, b] = [...ptrs.values()];
      pinch = { d: Math.hypot(a.x - b.x, a.y - b.y), cx: (a.x + b.x) / 2, cy: (a.y + b.y) / 2 };
      return;
    }
    if (ptrs.size > 2) return;
    const pan = e.pointerType === 'mouse' && e.button !== 0;
    one = { x0: e.clientX, y0: e.clientY, x: e.clientX, y: e.clientY, moved: false, pan, drag: false, target: e.target };
    if (!pan && tool.mode() !== 'mover') { one.drag = tool.down(pz.toImage(e.clientX, e.clientY)); }
    if (!pan && tool.mode() === 'mover') lp = setTimeout(() => { if (one && !one.moved) { one.done = true; tool.longPress(pz.toImage(one.x, one.y)); } }, 550);
  });
  el.addEventListener('pointermove', (e) => {
    const p = ptrs.get(e.pointerId); if (!p) return;
    p.x = e.clientX; p.y = e.clientY;
    if (ptrs.size >= 2 && pinch) {
      const [a, b] = [...ptrs.values()], d = Math.hypot(a.x - b.x, a.y - b.y), cx = (a.x + b.x) / 2, cy = (a.y + b.y) / 2, bx = pz.box;
      pz.set(pz.s, pz.tx + cx - pinch.cx, pz.ty + cy - pinch.cy);
      if (pinch.d > 10) pz.zoomAt(d / pinch.d, cx - bx.left, cy - bx.top);
      pinch = { d, cx, cy }; return;
    }
    if (!one) return;
    const dx = e.clientX - one.x, dy = e.clientY - one.y; one.x = e.clientX; one.y = e.clientY;
    if (Math.hypot(e.clientX - one.x0, e.clientY - one.y0) > 8) { one.moved = true; clearTimeout(lp); }
    if (one.drag) tool.move(pz.toImage(e.clientX, e.clientY));
    else if (one.moved) pz.set(pz.s, pz.tx + dx, pz.ty + dy);
  });
  const up = (e) => {
    if (!ptrs.has(e.pointerId)) return;
    ptrs.delete(e.pointerId); clearTimeout(lp);
    if (ptrs.size < 2) pinch = null;
    if (one && ptrs.size === 0) {
      if (one.drag) tool.up(pz.toImage(e.clientX, e.clientY));
      else if (!one.moved && !one.done && !one.pan) tool.tap(pz.toImage(e.clientX, e.clientY), one.target);
      one = null;
    }
  };
  el.addEventListener('pointerup', up); el.addEventListener('pointercancel', up);
  el.addEventListener('contextmenu', (e) => e.preventDefault());
  el.addEventListener('wheel', (e) => { e.preventDefault(); const b = pz.box; pz.zoomAt(e.deltaY > 0 ? 1 / 1.15 : 1.15, e.clientX - b.left, e.clientY - b.top); }, { passive: false });
}

// ---------------------------------------------------------------- mapa do mundo
// opts: { role: 'gm'|'player', send(msg), me: () => ({ nome, hero }), session: () => Session, toast(msg), extras: [botões], onClose }
export class MundoView {
  constructor(root, opts) {
    this.root = root; this.o = opts; this.mode = 'mover'; this.lore = localStorage.getItem('vtt.lore') !== '0';
    this.tracos = new Map(); this.pings = []; this.regua = null; this.rota = null; this.data = null; this.verRotas = true;
    root.classList.add('mundo');
    this.pz = new PanZoom(root, 4763, 3185);
    this.svg = sv('svg', { class: 'mu-svg' }); root.appendChild(this.svg);
    this.mark = h('div', 'mu-lugares'); root.appendChild(this.mark);
    this.pingLayer = h('div', 'mu-pings'); root.appendChild(this.pingLayer);
    this.buildUI();
    this.pz.listeners.push(() => this.schedule());
    gestures(this.pz, root, {
      mode: () => this.mode,
      down: (p) => this.toolDown(p), move: (p) => this.toolMove(p), up: (p) => this.toolUp(p), cancel: () => this.toolCancel(),
      tap: (p, el) => this.tap(p, el), longPress: (p) => this.ping(p),
    });
    addEventListener('resize', () => { if (this.visible) this.pz.set(this.pz.s, this.pz.tx, this.pz.ty); });
    fetch('/assets/mundo/faerun.json').then((r) => r.json()).then((d) => {
      this.data = d; this.pz.setSources([{ url: d.mini, f: 4 }, { url: d.meio, f: 2 }, { url: d.img, f: 1 }], d.w, d.h); this.buildMarkers();
      if (this.visible) this.pz.fit();
    });
  }
  get visible() { return !this.root.hidden; }
  show() { const first = this.root.hidden; this.root.hidden = false; if (first && this.data) { if (!this.fitted) { this.fitted = true; this.pz.fit(); } else this.pz.set(this.pz.s, this.pz.tx, this.pz.ty); } else if (first) this.pz.render(); }
  hide() { this.root.hidden = true; }
  mpp() { return this.data ? this.data.milhasPorPx : 0.798; }

  // ---- interface
  buildUI() {
    const ui = this.ui = h('div', 'mu-ui');
    ui.innerHTML = `
      <div class="mu-topo"><b>FAERÛN</b><div class="mu-escala"><i></i><span></span></div></div>
      <div class="mu-barra"></div>
      <div class="mu-info" hidden></div>
      <div class="mu-rotas" hidden><div class="mu-rotas-topo"><b>ROTAS DE VIAGEM</b><button class="mu-x" aria-label="Fechar">✕</button></div><div class="mu-rotas-lista"></div></div>
      <div class="mu-card" hidden><button class="mu-x" aria-label="Fechar">✕</button><small></small><b></b><p></p><a target="_blank" rel="noopener">Saiba mais na Forgotten Realms Wiki (em inglês) ↗</a></div>`;
    this.root.appendChild(ui);
    const bar = ui.querySelector('.mu-barra');
    const bt = (id, icon, nome, fn, title) => { const b = h('button', 'mu-bt'); b.dataset.id = id; b.innerHTML = `<i>${icon}</i><span>${nome}</span>`; b.title = title || nome; b.onclick = fn; bar.appendChild(b); return b; };
    this.btns = {
      mover: bt('mover', '✋', 'MOVER', () => this.setMode('mover'), 'Arrastar o mapa · segure parado para marcar um ping'),
      regua: bt('regua', '📏', 'RÉGUA', () => this.setMode('regua'), 'Arraste para medir'),
      rota: bt('rota', '🧭', 'ROTA', () => this.setMode('rota'), 'Toque ponto a ponto para planejar uma viagem'),
      lore: bt('lore', '📍', 'LUGARES', () => this.setLore(!this.lore), 'Mostrar ou esconder os pontos com lore'),
      rotas: bt('rotas', '🗺', 'ROTAS', () => this.toggleRotas(), 'Rotas salvas'),
      fit: bt('fit', '⌖', 'MAPA TODO', () => this.pz.flyTo(this.pz.w / 2, this.pz.h / 2, this.pz.fitScale(), 600)),
    };
    for (const e of this.o.extras || []) bar.appendChild(e);
    ui.querySelector('.mu-rotas .mu-x').onclick = () => this.toggleRotas(false);
    ui.querySelector('.mu-card .mu-x').onclick = () => { ui.querySelector('.mu-card').hidden = true; };
    this.setMode('mover'); this.setLore(this.lore);
  }
  setMode(m) {
    if (this.mode === 'rota' && m !== 'rota' && this.rota && this.rota.length) this.cancelRota();
    if (this.mode === 'regua' && m !== 'regua') this.clearRegua();
    this.mode = m;
    for (const [k, b] of Object.entries(this.btns)) if (['mover', 'regua', 'rota'].includes(k)) b.classList.toggle('sel', k === m);
    this.root.dataset.modo = m;
    const info = this.ui.querySelector('.mu-info');
    if (m === 'regua') this.info('📏 Toque num ponto e arraste até o destino', 'regua');
    else if (m === 'rota') { this.rota = []; this.info('🧭 Toque no mapa para marcar o ponto de partida e as paradas', 'rota'); }
    else info.hidden = true;
    this.schedule();
  }
  setLore(on) { this.lore = on; localStorage.setItem('vtt.lore', on ? '1' : '0'); this.btns.lore.classList.toggle('sel', on); this.mark.hidden = !on; if (!on) this.ui.querySelector('.mu-card').hidden = true; }
  info(html, kind, buttons = []) {
    const el = this.ui.querySelector('.mu-info'); el.hidden = false; el.dataset.kind = kind || ''; el.textContent = '';
    const t = h('div', 'mu-info-t'); t.innerHTML = html; el.appendChild(t);
    if (buttons.length) { const r = h('div', 'mu-info-bt'); for (const [nome, fn, cls] of buttons) { const b = h('button', cls || '', nome); b.onclick = fn; r.appendChild(b); } el.appendChild(r); }
  }

  // ---- lugares com lore
  buildMarkers() {
    this.mark.textContent = '';
    for (const l of this.data.lugares) {
      const b = h('button', 'mu-lugar ' + l.tipo); b.title = l.nome;
      b.innerHTML = `<i>${TIPO_ICONE[l.tipo] || '●'}</i><span></span>`; b.querySelector('span').textContent = l.nome.replace(/ \(.*\)$/, '');
      b.dataset.id = l.id;   // toque rápido abre a lore; segurar parado marca um ping (os gestos do mapa cuidam dos dois)
      l.el = b; this.mark.appendChild(b);
    }
    this.schedule();
  }
  card(l) {
    const c = this.ui.querySelector('.mu-card'); c.hidden = false;
    c.querySelector('small').textContent = `${TIPO_NOME[l.tipo]} · ${l.regiao}`;
    c.querySelector('b').textContent = l.nome; c.querySelector('p').textContent = l.texto; c.querySelector('a').href = l.url;
  }

  // ---- ferramentas
  toolDown(p) {
    if (this.mode === 'regua') { this.regua = [p, p]; this.sendTraco('regua', this.regua); this.schedule(); return true; }
    return false;   // rota: o toque é tratado no "tap" (arrastar move o mapa)
  }
  toolMove(p) {
    if (this.mode === 'regua' && this.regua) {
      this.regua[1] = p; this.schedule();
      const now = performance.now(); if (now - (this.lastSend || 0) > 80) { this.lastSend = now; this.sendTraco('regua', this.regua); }
    }
  }
  toolUp(p) {
    if (this.mode === 'regua' && this.regua) {
      this.regua[1] = p; this.sendTraco('regua', this.regua); this.schedule();
      clearTimeout(this.clearT); this.clearT = setTimeout(() => this.sendTraco('regua', []), 12000);   // os outros veem por 12 s
    }
  }
  toolCancel() { if (this.mode === 'regua') this.clearRegua(); }
  clearRegua() { if (this.regua) { this.regua = null; this.sendTraco('regua', []); this.schedule(); } }
  tap(p, el) {
    const mk = el && el.closest && el.closest('.mu-lugar');
    if (mk && this.mode === 'mover') { this.card(this.data.lugares.find((l) => l.id === mk.dataset.id)); return; }
    if (this.mode === 'rota') {
      this.rota.push(p); this.sendTraco('rota', this.rota); this.rotaInfo(); this.schedule();
    } else if (this.mode === 'mover') this.ui.querySelector('.mu-card').hidden = true;
  }
  rotaInfo() {
    const r = this.rota, mi = pathLen(r) * this.mpp();
    if (r.length < 2) { this.info('🧭 Partida marcada. Toque nas paradas e no destino.', 'rota', [['CANCELAR', () => this.cancelRota(), 'nao']]); return; }
    this.info(`🧭 <b>${distTxt(mi)}</b> · ${r.length - 1} trecho(s)<br><small>${viagem(mi)}</small>`, 'rota', [
      ['DESFAZER', () => { this.rota.pop(); this.sendTraco('rota', this.rota); this.rotaInfo(); this.schedule(); }],
      ['CANCELAR', () => this.cancelRota(), 'nao'],
      ['SALVAR', () => this.saveRota(), 'sim'],
    ]);
  }
  cancelRota() { this.rota = []; this.sendTraco('rota', []); this.info('🧭 Toque no mapa para marcar o ponto de partida e as paradas', 'rota'); this.schedule(); }
  saveRota() {
    const nome = (prompt('Nome da rota (ex.: Águas Profundas até Portal de Baldur):', '') || '').trim();
    this.o.send({ t: 'rota_add', nome: nome || 'Rota de ' + (this.o.me().nome || 'viagem'), pts: this.rota.map((q) => [Math.round(q.x), Math.round(q.y)]) });
    this.rota = []; this.sendTraco('rota', []); this.o.toast && this.o.toast('Rota salva: todos podem ver no botão ROTAS.');
    this.setMode('mover'); this.toggleRotas(true);
  }
  sendTraco(tipo, pts) { this.o.send({ t: 'traco', ctx: 'mundo', tipo, pts: pts.map((q) => [Math.round(q.x), Math.round(q.y)]) }); }
  ping(p) {
    const me = this.o.me(), gm = this.o.role === 'gm';
    this.o.send({ t: 'ping', x: Math.round(p.x), y: Math.round(p.y), leva: gm });
    this.showPing({ x: p.x, y: p.y, por: gm ? 'Mestre' : me.nome, hero: me.hero, gm });
    try { navigator.vibrate && navigator.vibrate(40); } catch {}
  }

  // ---- o que vem dos outros
  onTraco(m) {
    if (m.ctx !== 'mundo') return;
    if (!m.pts || m.pts.length < 2 && m.tipo === 'regua' || !m.pts.length) this.tracos.delete(m.id);
    else this.tracos.set(m.id, { ...m, pts: m.pts.map(([x, y]) => ({ x, y })) });
    this.schedule();
  }
  onPing(m) {
    this.showPing(m);
    if (m.leva && this.o.role !== 'gm' && this.visible) this.pz.flyTo(m.x, m.y, Math.max(this.pz.s, this.pz.fitScale() * 2.6), 1100);
  }
  showPing(m) {
    const el = h('div', 'mu-ping' + (m.gm ? ' gm' : '')); el.style.setProperty('--c', corDe(m.hero, m.gm));
    el.innerHTML = '<i></i><i></i><i></i><span></span>'; el.querySelector('span').textContent = m.por;
    this.pingLayer.appendChild(el);
    const p = { ...m, el, t: performance.now() }; this.pings.push(p);
    setTimeout(() => { el.remove(); this.pings = this.pings.filter((q) => q !== p); }, 4200);
    this.schedule();
  }
  onRotas() { this.renderRotas(); this.schedule(); }
  toggleRotas(on) {
    const el = this.ui.querySelector('.mu-rotas'); el.hidden = on === undefined ? !el.hidden : !on;
    this.btns.rotas.classList.toggle('sel', !el.hidden); this.renderRotas();
  }
  renderRotas() {
    const box = this.ui.querySelector('.mu-rotas-lista'); box.textContent = '';
    const s = this.o.session(), list = (s && s.rotas) || [], me = this.o.me();
    if (!list.length) { box.appendChild(h('p', 'mu-vazio', 'Nenhuma rota salva. Use 🧭 ROTA para planejar uma viagem.')); return; }
    for (const r of [...list].reverse()) {
      const mi = pathLen(r.pts.map(([x, y]) => ({ x, y }))) * this.mpp();
      const row = h('div', 'mu-rota'); row.style.setProperty('--c', corDe(r.hero, r.dono === 'gm'));
      const t = h('div', 'mu-rota-t');
      t.append(h('b', '', r.nome), h('small', '', `${r.por} · ${distTxt(mi)}`), h('em', '', viagem(mi)));
      const ver = h('button', '', '👁'); ver.title = 'Ver no mapa';
      ver.onclick = () => { const b = bounds(r.pts), bx = this.pz.box; this.pz.flyTo((b.x0 + b.x1) / 2, (b.y0 + b.y1) / 2, Math.min(bx.width / (b.x1 - b.x0 + 200), bx.height / (b.y1 - b.y0 + 200)), 800); };
      row.append(t, ver);
      const mine = this.o.role === 'gm' || (me && r.por === me.nome);
      if (mine) { const del = h('button', 'del', '✕'); del.title = 'Apagar rota'; del.onclick = () => this.o.send({ t: 'rota_del', id: r.id }); row.appendChild(del); }
      box.appendChild(row);
    }
  }

  // ---- desenho (a cada mudança de vista ou de dados, no próximo quadro)
  schedule() { if (this.raf) return; this.raf = requestAnimationFrame(() => { this.raf = 0; this.draw(); }); }
  draw() {
    if (!this.visible) return;
    const pz = this.pz, b = pz.box, S = (q) => pz.toScreen(q.x, q.y);
    this.svg.setAttribute('viewBox', `0 0 ${b.width} ${b.height}`); this.svg.textContent = '';
    // escala dinâmica
    const nice = [10, 20, 25, 50, 100, 150, 200, 250, 500, 1000];
    const pxPerMi = pz.s / this.mpp(); let mi = nice[0];
    for (const n of nice) if (n * pxPerMi <= 150) mi = n;
    this.ui.querySelector('.mu-escala i').style.width = (mi * pxPerMi).toFixed(0) + 'px';
    this.ui.querySelector('.mu-escala span').textContent = `${mi} milhas · ${fmtInt(mi * 1.609)} km`;
    // rotas salvas, rascunhos e réguas dos outros, a minha régua e a minha rota
    const s = this.o.session();
    if (this.verRotas && s && s.rotas) for (const r of s.rotas) this.path(r.pts.map(([x, y]) => S({ x, y })), corDe(r.hero, r.dono === 'gm'), { dash: '', label: r.nome, w: 3.5, op: 0.85 });
    for (const t of this.tracos.values()) {
      const pts = t.pts.map(S), mi2 = pathLen(t.pts) * this.mpp();
      this.path(pts, corDe(t.hero, t.id === 'gm'), { dash: t.tipo === 'regua' ? '10 7' : '3 6', label: `${t.por} ${t.tipo === 'regua' ? '📏' : '🧭'} ${distTxt(mi2)}`, w: 3 });
    }
    const myC = corDe(this.o.me().hero, this.o.role === 'gm');
    if (this.regua) {
      const mi3 = Math.hypot(this.regua[1].x - this.regua[0].x, this.regua[1].y - this.regua[0].y) * this.mpp();
      this.path(this.regua.map(S), myC, { dash: '12 8', w: 4 });
      if (mi3 > 0.3) this.info(`📏 <b>${distTxt(mi3)}</b><br><small>${viagem(mi3)}</small>`, 'regua', [['LIMPAR', () => this.clearRegua(), 'nao']]);
    }
    if (this.rota && this.rota.length) this.path(this.rota.map(S), myC, { dash: '3 7', w: 4, dots: true });
    // pontos de lore
    if (this.lore && this.data) {
      const zoomed = pz.s > pz.fitScale() * 1.7;
      for (const l of this.data.lugares) {
        const q = S(l), off = q.x < -40 || q.y < -40 || q.x > b.width + 40 || q.y > b.height + 40;
        l.el.hidden = off; if (off) continue;
        l.el.style.transform = `translate3d(${q.x.toFixed(1)}px, ${q.y.toFixed(1)}px, 0)`;
        l.el.classList.toggle('nome', zoomed || l.tipo === 'capital' || l.tipo === 'regiao');
        l.el.classList.toggle('longe', !zoomed && l.tipo !== 'capital' && l.tipo !== 'regiao');
      }
    }
    for (const p of this.pings) { const q = S(p); p.el.style.transform = `translate(${q.x}px, ${q.y}px)`; }
  }
  path(pts, cor, { dash = '', label = '', w = 3, op = 1, dots = false } = {}) {
    if (pts.length < 1) return;
    const d = pts.map((q, i) => `${i ? 'L' : 'M'}${q.x.toFixed(1)},${q.y.toFixed(1)}`).join(' ');
    this.svg.appendChild(sv('path', { d, fill: 'none', stroke: 'rgba(0,0,0,.55)', 'stroke-width': w + 3, 'stroke-linecap': 'round', 'stroke-linejoin': 'round', opacity: op }));
    this.svg.appendChild(sv('path', { d, fill: 'none', stroke: cor, 'stroke-width': w, 'stroke-dasharray': dash, 'stroke-linecap': 'round', 'stroke-linejoin': 'round', opacity: op }));
    const ends = dots ? pts : [pts[0], pts[pts.length - 1]];
    for (const q of ends) this.svg.appendChild(sv('circle', { cx: q.x, cy: q.y, r: w + 2, fill: cor, stroke: '#000', 'stroke-width': 1.5, opacity: op }));
    if (label && pts.length > 1) {
      const q = pts[pts.length - 1], t = sv('text', { x: q.x + 10, y: q.y - 10, class: 'mu-rot' }); t.textContent = label;
      t.setAttribute('fill', cor); this.svg.appendChild(t);
    }
  }
}
const pathLen = (pts) => { let s = 0; for (let i = 1; i < pts.length; i++) s += Math.hypot(pts[i].x - pts[i - 1].x, pts[i].y - pts[i - 1].y); return s; };
const bounds = (pts) => ({ x0: Math.min(...pts.map((q) => q[0])), x1: Math.max(...pts.map((q) => q[0])), y0: Math.min(...pts.map((q) => q[1])), y1: Math.max(...pts.map((q) => q[1])) });

// ---------------------------------------------------------------- imagem do teatro da mente
export class ImagemView {
  constructor(root) {
    this.root = root; root.classList.add('imagem-mesa');
    this.pz = new PanZoom(root, 1, 1);
    this.leg = h('div', 'im-legenda mu-ui'); root.appendChild(this.leg);
    gestures(this.pz, root, { mode: () => 'mover', down: () => false, move() {}, up() {}, tap() {}, longPress() {} });
    addEventListener('resize', () => { if (!root.hidden && this.url) this.pz.fit(); });
  }
  show(url, legenda) {
    this.root.hidden = false;
    this.leg.textContent = legenda || ''; this.leg.hidden = !legenda;
    if (url === this.url) return;
    this.url = url; this.root.classList.remove('pronta');
    const img = new Image();
    img.onload = () => { this.pz.setImage(url, img.naturalWidth, img.naturalHeight); this.pz.fit(); this.pz.onLoad = () => this.root.classList.add('pronta'); };
    img.src = url;
  }
  hide() { this.root.hidden = true; }
}
