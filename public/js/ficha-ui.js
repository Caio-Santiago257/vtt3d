// Ficha do personagem na tela do jogador: nível, atributos, perícias, características,
// magias preparadas (Guy) e recursos (espaços de magia, Canalizar Divindade, Fúria, pontos de feitiçaria).
// Cada mudança vai para o servidor, que salva em fichas/<herói>.json na pasta do projeto.
import { CLASSES, HEROI_CLASSE, MAGIAS_CLERIGO } from './dnd-dados.js';
import { GRIMORIO_FEITICEIRO } from './area.js';
import {
  ATRS, ATR_CURTO, PERICIAS, CIRC_NOME, classeDe, mod, fmtMod, prof, novaFicha, pvSugerido, slotsMax, circMax, cdMagia, ataqueMagia,
  truquesMax, preparadasMax, usosMax, USO_NOME, descansoCurto, descansoLongo, magiasDominio, efeitoEm, tempoNome,
} from './regras.js';

const h = (tag, cls, txt) => { const e = document.createElement(tag); if (cls) e.className = cls; if (txt !== undefined) e.textContent = txt; return e; };
const SUB_ROTULO = { Cleric: 'Domínio', Sorcerer: 'Origem feiticeira', Barbarian: 'Caminho primal' };
const m2txt = (v) => String(v).replace('.', ',') + ' m';
const alcTxt = (m) => (m.forma ? `${{ esfera: 'esfera', cilindro: 'cilindro', cubo: 'cubo', cone: 'cone', linha: 'linha', emanacao: 'emanação' }[m.forma]} de ${m2txt(m.tam)}` + (m.alcance ? ` a ${m2txt(m.alcance)}` : '')
  : m.toque ? 'toque' : m.pessoal ? 'pessoal' : m.alcance ? m2txt(m.alcance) : 'especial');

export class FichaUI {
  // opts: { session: () => Session, hero: () => id, inFight: () => bool, toast(msg, cls) }
  constructor(opts) {
    this.o = opts; this.tab = 'ficha'; this.filtro = 'todas'; this.local = null; this.dirty = 0;
    const el = this.el = h('div', 'ficha-painel'); el.hidden = true;
    el.innerHTML = '<div class="fp-topo"><div class="fp-tit"><b></b><small></small></div><button class="fp-fechar" aria-label="Fechar">✕</button></div><div class="fp-abas"></div><div class="fp-corpo"></div>';
    el.querySelector('.fp-fechar').onclick = () => this.close();
    document.body.appendChild(el);
  }
  get hero() { return this.o.hero(); }
  get cls() { return classeDe(this.hero); }
  // ficha atual: a cópia local (enquanto há mudança indo para o servidor) ou a do servidor
  get f() {
    const s = this.o.session(), srv = s && s.fichas && s.fichas[this.hero];
    if (this.local && (this.dirty > performance.now() || !srv)) return this.local;
    this.local = srv ? JSON.parse(JSON.stringify(srv)) : novaFicha(this.hero);
    this.local.usos = this.local.usos || {};
    return this.local;
  }
  save() {
    const f = this.local; if (!f) return;
    this.dirty = performance.now() + 1500;
    clearTimeout(this.tm);
    this.tm = setTimeout(() => { const s = this.o.session(); if (s) s.send({ t: 'ficha', ficha: f }); }, 250);
  }
  change(fn) { const f = this.f; fn(f); this.save(); this.render(); }
  open(tab) {
    if (tab) this.tab = tab; this.el.hidden = false; document.body.classList.add('ficha-aberta');
    const s = this.o.session();
    if (s && !(s.fichas && s.fichas[this.hero])) { this.f; this.save(); }   // primeira vez: já salva a ficha inicial (o mestre passa a ver)
    this.render();
  }
  close() { this.el.hidden = true; document.body.classList.remove('ficha-aberta'); }
  get isOpen() { return !this.el.hidden; }
  onServer() { if (this.isOpen && this.dirty < performance.now()) this.render(); }

  // ---- gasto de espaço de magia (chamado pelo menu de combate e pela área de magia)
  gastar(circ) {
    if (!(circ > 0)) return;
    this.change((f) => { f.slotsUsados[circ - 1] = Math.min(slotsMax(f)[circ - 1], (f.slotsUsados[circ - 1] || 0) + 1); });
  }

  render() {
    const f = this.f, c = this.cls; if (!c) return;
    const sub = c.subs[f.sub];
    this.el.dataset.classe = c.id;
    this.el.querySelector('.fp-tit b').textContent = (this.o.nome ? this.o.nome() : this.hero).toUpperCase();
    this.el.querySelector('.fp-tit small').textContent = `${c.nome} · nível ${f.nivel}` + (sub && f.nivel >= 3 ? ` · ${sub.nome}` : '');
    const abas = this.el.querySelector('.fp-abas'); abas.textContent = '';
    const tabs = [['ficha', 'FICHA'], ...(c.atr ? [['magias', 'MAGIAS']] : []), ['recursos', 'RECURSOS']];
    if (!tabs.some((t) => t[0] === this.tab)) this.tab = 'ficha';
    for (const [id, nome] of tabs) {
      const b = h('button', id === this.tab ? 'sel' : '', nome); b.onclick = () => { this.tab = id; this.render(); this.el.querySelector('.fp-corpo').scrollTop = 0; };
      abas.appendChild(b);
    }
    const body = this.el.querySelector('.fp-corpo'), top = body.scrollTop; body.textContent = '';
    if (this.tab === 'ficha') this.renderFicha(body, f, c);
    else if (this.tab === 'magias') this.renderMagias(body, f, c);
    else this.renderRecursos(body, f, c);
    body.scrollTop = top;
  }
  sec(body, t) { const s = h('div', 'fp-sec', t); body.appendChild(s); return s; }
  stepper(label, val, onSet, { min = 0, max = 99, fmt = (v) => v, step = 1, sub } = {}) {
    const row = h('div', 'fp-num'); const l = h('span', '', label);
    if (sub) { const s = h('small', '', sub); l.appendChild(s); }
    const mi = h('button', '', '−'), v = h('b', '', fmt(val)), pl = h('button', '', '+');
    mi.onclick = () => onSet(Math.max(min, Math.round((val - step) * 10) / 10)); pl.onclick = () => onSet(Math.min(max, Math.round((val + step) * 10) / 10));
    row.append(l, mi, v, pl); return row;
  }

  // ---------------------------------------------------------------- aba FICHA
  renderFicha(body, f, c) {
    const p = prof(f.nivel);
    const topo = h('div', 'fp-grade2'); body.appendChild(topo);
    topo.appendChild(this.stepper('Nível', f.nivel, (v) => this.change((x) => { const old = pvSugerido(x); const cheio = x.pv >= x.pvMax; x.nivel = v; if (x.pvMax === old) { x.pvMax = pvSugerido(x); x.pv = cheio ? x.pvMax : Math.min(x.pv, x.pvMax); } }), { min: 1, max: 20, sub: `Proficiência ${fmtMod(p)}` }));
    // subclasse (a partir do 3º nível)
    const sl = h('label', 'fp-sel'); sl.append(h('span', '', SUB_ROTULO[c.id]));
    const sel = h('select'); sel.disabled = f.nivel < 3;
    sel.appendChild(new Option(f.nivel < 3 ? 'a partir do nível 3' : '— escolha —', ''));
    for (const [id, s] of Object.entries(c.subs)) sel.appendChild(new Option(s.nome, id));
    sel.value = f.sub || ''; sel.onchange = () => this.change((x) => { x.sub = sel.value; });
    sl.appendChild(sel); topo.appendChild(sl);
    if (c.id === 'Cleric') {
      const ol = h('label', 'fp-sel'); ol.append(h('span', '', 'Ordem Divina'));
      const os = h('select'); os.append(new Option('Protetor (armas marciais, armadura pesada)', 'protetor'), new Option('Taumaturgo (+1 truque, +Sab em Arcanismo e Religião)', 'taumaturgo'));
      os.value = f.ordem || 'protetor'; os.onchange = () => this.change((x) => { x.ordem = os.value; });
      ol.appendChild(os); topo.appendChild(ol);
    }

    this.sec(body, 'ATRIBUTOS');
    const g = h('div', 'fp-atrs'); body.appendChild(g);
    for (const [k, nome] of ATRS) {
      const card = h('div', 'fp-atr' + (c.salv.includes(k) ? ' salv' : ''));
      const m = mod(f.atr[k]), tr = m + (c.salv.includes(k) ? p : 0);
      card.append(h('small', '', nome.toUpperCase()), h('b', '', fmtMod(m)));
      const row = h('div', 'fp-atr-v');
      const mi = h('button', '', '−'), v = h('span', '', f.atr[k]), pl = h('button', '', '+');
      mi.onclick = () => this.change((x) => { const old = pvSugerido(x); x.atr[k] = Math.max(1, x.atr[k] - 1); if (k === 'con' && x.pvMax === old) { const cheio = x.pv >= x.pvMax; x.pvMax = pvSugerido(x); if (cheio) x.pv = x.pvMax; } });
      pl.onclick = () => this.change((x) => { const old = pvSugerido(x); x.atr[k] = Math.min(30, x.atr[k] + 1); if (k === 'con' && x.pvMax === old) { const cheio = x.pv >= x.pvMax; x.pvMax = pvSugerido(x); if (cheio) x.pv = x.pvMax; } });
      row.append(mi, v, pl); card.appendChild(row);
      card.appendChild(h('em', '', `Salvaguarda ${fmtMod(tr)}` + (c.salv.includes(k) ? ' ●' : '')));
      g.appendChild(card);
    }

    this.sec(body, 'COMBATE');
    const cb = h('div', 'fp-grade2'); body.appendChild(cb);
    const sug = pvSugerido(f);
    cb.appendChild(this.stepper('PV máximos', f.pvMax, (v) => this.change((x) => { x.pvMax = v; x.pv = Math.min(x.pv, v); }), { min: 1, max: 999, sub: `sugerido ${sug} (d${c.dv})` }));
    cb.appendChild(this.stepper('Classe de Armadura', f.ca, (v) => this.change((x) => { x.ca = v; }), { min: 5, max: 30, sub: c.id === 'Barbarian' ? `sem armadura: ${10 + mod(f.atr.des) + mod(f.atr.con)}` : '' }));
    cb.appendChild(this.stepper('Deslocamento', f.deslocamento, (v) => this.change((x) => { x.deslocamento = v; }), { min: 0, max: 30, step: 1.5, fmt: m2txt }));
    const info = h('div', 'fp-info');
    const chip = (t, v) => { const d = h('div'); d.append(h('small', '', t), h('b', '', v)); info.appendChild(d); };
    chip('Iniciativa', fmtMod(mod(f.atr.des)) + (c.id === 'Barbarian' && f.nivel >= 7 ? ' (vantagem)' : ''));
    const perc = f.pericias.includes('percepcao') ? p : 0;
    chip('Percepção passiva', 10 + mod(f.atr.sab) + perc);
    chip('Proficiência', fmtMod(p));
    if (c.atr) { chip('CD de magia', cdMagia(f)); chip('Ataque de magia', fmtMod(ataqueMagia(f))); }
    if (c.id === 'Barbarian') { chip('Dano de fúria', '+' + c.danoFuria[f.nivel - 1]); chip('Maestrias', c.maestria[f.nivel - 1]); }
    body.appendChild(info);
    const prf = h('p', 'fp-nota', `Proficiências da classe: armas ${c.armas.map((a) => ({ simple: 'simples', martial: 'marciais' }[a] || a)).join(' e ')}` +
      (c.armaduras.length ? `; armaduras ${c.armaduras.map((a) => ({ light: 'leves', medium: 'médias', heavy: 'pesadas', shield: 'escudos' }[a] || a)).join(', ')}` : '; sem armaduras') +
      (c.id === 'Cleric' && f.ordem === 'protetor' ? ' (+ marciais e pesadas pela Ordem Divina)' : '') + '.');
    body.appendChild(prf);

    this.sec(body, `PERÍCIAS · toque para marcar proficiência (a classe escolhe ${c.pericias.n}: ★)`);
    const pg = h('div', 'fp-pericias'); body.appendChild(pg);
    for (const [id, nome, atr] of PERICIAS) {
      const on = f.pericias.includes(id);
      let v = mod(f.atr[atr]) + (on ? p : 0);
      if (c.id === 'Cleric' && f.ordem === 'taumaturgo' && (id === 'arcanismo' || id === 'religiao')) v += Math.max(1, mod(f.atr.sab));
      const b = h('button', 'fp-per' + (on ? ' on' : '') + (c.pericias.de.includes(id) ? ' cls' : ''));
      b.append(h('i', '', on ? '●' : '○'), h('span', '', nome + (c.pericias.de.includes(id) ? ' ★' : '')), h('small', '', ATR_CURTO[atr]), h('b', '', fmtMod(v)));
      b.onclick = () => this.change((x) => { x.pericias = on ? x.pericias.filter((q) => q !== id) : [...x.pericias, id]; });
      pg.appendChild(b);
    }

    this.sec(body, 'CARACTERÍSTICAS DE CLASSE');
    const lst = h('div', 'fp-carac'); body.appendChild(lst);
    const sub = c.subs[f.sub];
    for (const [lv, nome, desc] of c.carac) {
      let d = desc;
      if (!d && sub && sub.carac[lv]) d = `${sub.nome}: ${sub.carac[lv]}`;
      else if (lv === 3 && sub) d = `${sub.nome}: ${sub.carac[3]}` + (c.id === 'Cleric' ? ' (magias do domínio sempre preparadas)' : '');
      const row = h('div', 'fp-c' + (lv <= f.nivel ? ' on' : ''));
      row.append(h('i', '', lv), h('b', '', nome), h('small', '', d || ''));
      lst.appendChild(row);
    }

    this.sec(body, 'ANOTAÇÕES');
    const ta = h('textarea', 'fp-notas'); ta.value = f.notas || ''; ta.placeholder = 'Equipamento, talentos, idiomas, história…';
    ta.oninput = () => { this.f.notas = ta.value; this.save(); };
    body.appendChild(ta);
    body.appendChild(h('p', 'fp-nota', 'A ficha é salva sozinha no computador do mestre (pasta fichas do projeto).'));
  }

  // ---------------------------------------------------------------- aba MAGIAS
  renderMagias(body, f, c) {
    const cm = circMax(f), fight = this.o.inFight();
    const info = h('div', 'fp-info'); body.appendChild(info);
    const chip = (t, v, cls = '') => { const d = h('div', cls); d.append(h('small', '', t), h('b', '', v)); info.appendChild(d); };
    if (c.id === 'Cleric') {
      const nT = f.truques.filter((en) => MAGIAS_CLERIGO.some((m) => m.en === en && m.circ === 0)).length;
      const domEn = new Set(magiasDominio(f).map((m) => m.en));
      const nP = f.preparadas.filter((en) => !domEn.has(en) && MAGIAS_CLERIGO.some((m) => m.en === en && m.circ > 0 && m.circ <= cm)).length;
      chip('Truques', `${nT} / ${truquesMax(f)}`, nT > truquesMax(f) ? 'demais' : '');
      chip('Preparadas', `${nP} / ${preparadasMax(f)}`, nP > preparadasMax(f) ? 'demais' : '');
    }
    chip('Círculo máximo', cm ? `${cm}º` : '—');
    chip('CD', cdMagia(f)); chip('Ataque', fmtMod(ataqueMagia(f)));
    const prox = c.slots.findIndex((row) => row[cm] > 0);
    if (cm < 9 && prox >= 0) body.appendChild(h('p', 'fp-nota', `O ${cm + 1}º círculo libera no nível ${prox + 1}.`));

    if (c.id === 'Sorcerer') {
      body.appendChild(h('p', 'fp-nota', 'Feitiços da Kaira disponíveis no jogo (até o 3º círculo). Em combate aparecem só os do círculo que o nível permite e cada um gasta um espaço.'));
      for (let k = 0; k <= Math.min(3, cm); k++) {
        const list = GRIMORIO_FEITICEIRO.filter((m) => m.circ === k); if (!list.length) continue;
        this.sec(body, CIRC_NOME[k].toUpperCase());
        const g = h('div', 'fp-magias'); body.appendChild(g);
        for (const m of list) g.appendChild(this.spellRow(m, f, { fixed: true }));
      }
      return;
    }

    // Guy: escolhe as magias preparadas do dia (fora de combate)
    body.appendChild(h('p', 'fp-nota' + (fight ? ' alerta' : ''), fight
      ? 'Em combate as magias preparadas ficam travadas. No menu MAGIA aparecem só as preparadas.'
      : 'Toque nas magias para preparar. No combate só aparecem as preparadas, e cada magia de 1º círculo ou mais gasta um espaço.'));
    const fl = h('div', 'fp-filtro'); body.appendChild(fl);
    for (const [id, nome] of [['todas', 'Todas'], ['prep', 'Só as preparadas']]) {
      const b = h('button', this.filtro === id ? 'sel' : '', nome); b.onclick = () => { this.filtro = id; this.render(); }; fl.appendChild(b);
    }
    const dom = magiasDominio(f);
    if (dom.length) {
      this.sec(body, `SEMPRE PREPARADAS · ${c.subs[f.sub].nome.toUpperCase()} · não contam no limite`);
      const g = h('div', 'fp-magias'); body.appendChild(g);
      for (const m of dom) g.appendChild(this.spellRow(m, f, { fixed: true, tag: 'domínio' }));
    } else if (f.nivel >= 3 && !f.sub) body.appendChild(h('p', 'fp-nota', 'Escolha o Domínio na aba FICHA para ganhar as magias de domínio.'));
    const domSet = new Set(dom.map((m) => m.en));
    for (let k = 0; k <= cm; k++) {
      let list = MAGIAS_CLERIGO.filter((m) => m.circ === k && !m.dominio && !domSet.has(m.en));
      const sel = k === 0 ? f.truques : f.preparadas;
      if (this.filtro === 'prep') list = list.filter((m) => sel.includes(m.en));
      if (!list.length) continue;
      this.sec(body, k === 0 ? `TRUQUES · escolha ${truquesMax(f)}` : CIRC_NOME[k].toUpperCase());
      const g = h('div', 'fp-magias'); body.appendChild(g);
      for (const m of list) g.appendChild(this.spellRow(m, f, { toggle: !fight }));
    }
  }
  spellRow(m, f, { toggle = false, fixed = false, tag = '' } = {}) {
    const list = m.circ === 0 ? f.truques : f.preparadas;
    const on = fixed || list.includes(m.en);
    const b = h('div', 'fp-mag' + (on ? ' on' : '') + (fixed ? ' fixa' : ''));
    const ck = h('i', '', fixed ? '✦' : on ? '✔' : '');
    const t = h('span', 'fp-mag-t');
    const nm = h('b', '', m.nome); nm.title = m.en;
    const tags = [tempoNome(m.tempo), alcTxt(m)];
    if (m.conc) tags.push('concentração'); if (m.ritual) tags.push('ritual'); if (tag) tags.unshift(tag);
    t.append(nm, h('small', '', (efeitoEm(m, m.circ, f.nivel) || m.escola || '') + ' · ' + tags.join(' · ')));
    b.append(ck, t);
    if (m.url) { const a = h('a', 'fp-mag-i', 'ⓘ'); a.href = m.url; a.target = '_blank'; a.rel = 'noopener'; a.title = 'Ver no 5e.tools (em inglês)'; a.onclick = (e) => e.stopPropagation(); b.appendChild(a); }
    if (toggle && !fixed) b.onclick = () => {
      const max = m.circ === 0 ? truquesMax(f) : preparadasMax(f);
      if (!on && list.length >= max) {
        // conta só o que vale no nível atual (magias acima do círculo máximo não contam)
        const cm = circMax(f), domEn = new Set(magiasDominio(f).map((q) => q.en));
        const valid = list.filter((en) => { const x = MAGIAS_CLERIGO.find((q) => q.en === en); return x && !domEn.has(en) && (m.circ === 0 ? x.circ === 0 : x.circ > 0 && x.circ <= cm); });
        if (valid.length >= max) { this.o.toast(m.circ === 0 ? `Você já tem ${max} truques. Desmarque um antes.` : `Limite de ${max} magias preparadas no nível ${f.nivel}. Desmarque uma antes.`, 'neg'); return; }
      }
      this.change((x) => { const key = m.circ === 0 ? 'truques' : 'preparadas'; x[key] = on ? x[key].filter((q) => q !== m.en) : [...x[key], m.en]; });
    };
    else if (!fixed && !toggle) b.onclick = () => this.o.toast('Em combate não dá para trocar as magias preparadas.', 'neg');
    return b;
  }

  // ---------------------------------------------------------------- aba RECURSOS
  renderRecursos(body, f, c) {
    this.sec(body, 'PONTOS DE VIDA');
    const pv = h('div', 'fp-pv'); body.appendChild(pv);
    const big = h('div', 'fp-pv-n'); big.append(h('b', '', f.pv), h('span', '', ` / ${f.pvMax}`));
    if (f.pvTemp) big.appendChild(h('em', '', ` +${f.pvTemp} temp.`));
    pv.appendChild(big);
    const bt = h('div', 'fp-pv-bt');
    for (const d of [-10, -5, -1, +1, +5, +10]) {
      const b = h('button', d < 0 ? 'dano' : 'cura', (d > 0 ? '+' : '−') + Math.abs(d));
      b.onclick = () => this.change((x) => {
        if (d < 0 && x.pvTemp) { const t = Math.min(x.pvTemp, -d); x.pvTemp -= t; x.pv += d + t; } else x.pv = Math.min(x.pvMax, x.pv + d);
        x.pv = Math.max(-x.pvMax, x.pv);
      });
      bt.appendChild(b);
    }
    pv.appendChild(bt);
    pv.appendChild(this.stepper('PV temporários', f.pvTemp || 0, (v) => this.change((x) => { x.pvTemp = v; }), { min: 0, max: 999 }));

    const sm = slotsMax(f);
    if (c.atr && sm.some((v) => v > 0)) {
      this.sec(body, 'ESPAÇOS DE MAGIA · toque para gastar ou recuperar');
      const g = h('div', 'fp-slots'); body.appendChild(g);
      sm.forEach((max, i) => {
        if (!max) return;
        const used = f.slotsUsados[i] || 0, row = h('div', 'fp-slot');
        row.appendChild(h('span', '', `${i + 1}º`));
        const pips = h('div', 'fp-pips');
        for (let j = 0; j < max; j++) {
          const free = j < max - used, p = h('button', free ? 'cheio' : 'vazio'); p.setAttribute('aria-label', free ? 'Gastar' : 'Recuperar');
          p.onclick = () => this.change((x) => { x.slotsUsados[i] = Math.max(0, Math.min(max, (x.slotsUsados[i] || 0) + (free ? 1 : -1))); });
          pips.appendChild(p);
        }
        row.append(pips, h('small', '', `${max - used} de ${max}`));
        g.appendChild(row);
      });
    }
    const um = usosMax(f);
    if (Object.keys(um).length) {
      this.sec(body, 'USOS DE CARACTERÍSTICAS');
      const g = h('div', 'fp-slots'); body.appendChild(g);
      for (const [k, max] of Object.entries(um)) {
        const used = f.usos[k] || 0, row = h('div', 'fp-slot uso');
        row.appendChild(h('span', '', USO_NOME[k]));
        const pips = h('div', 'fp-pips');
        if (max > 8) {   // pontos de feitiçaria: contador
          const mi = h('button', 'mini', '−'), pl = h('button', 'mini', '+');
          mi.onclick = () => this.change((x) => { x.usos[k] = Math.min(max, (x.usos[k] || 0) + 1); });
          pl.onclick = () => this.change((x) => { x.usos[k] = Math.max(0, (x.usos[k] || 0) - 1); });
          pips.append(mi, h('b', '', `${max - used}`), pl);
        } else for (let j = 0; j < max; j++) {
          const free = j < max - used, p = h('button', free ? 'cheio' : 'vazio');
          p.onclick = () => this.change((x) => { x.usos[k] = Math.max(0, Math.min(max, (x.usos[k] || 0) + (free ? 1 : -1))); });
          pips.appendChild(p);
        }
        row.append(pips, h('small', '', `${max - used} de ${max}`));
        g.appendChild(row);
      }
    }
    this.sec(body, 'DESCANSO');
    const rb = h('div', 'fp-descanso'); body.appendChild(rb);
    const curto = h('button', '', 'DESCANSO CURTO'), longo = h('button', 'longo', 'DESCANSO LONGO');
    curto.title = 'Recupera 1 uso de Canalizar Divindade e de Fúria' + (f.hero === 'Kaira' ? '; pontos de feitiçaria a partir do nível 5' : '');
    curto.onclick = () => { if (this.o.inFight()) return this.o.toast('Não dá para descansar em combate.', 'neg'); this.change(descansoCurto); this.o.toast('Descanso curto: usos recuperados.'); };
    let conf = 0;
    longo.onclick = () => {
      if (this.o.inFight()) return this.o.toast('Não dá para descansar em combate.', 'neg');
      if (performance.now() > conf) { conf = performance.now() + 2500; longo.textContent = 'CONFIRMAR?'; setTimeout(() => { longo.textContent = 'DESCANSO LONGO'; }, 2500); return; }
      this.change(descansoLongo); this.o.toast('Descanso longo: PV, espaços de magia e usos recuperados.');
    };
    rb.append(curto, longo);
    body.appendChild(h('p', 'fp-nota', 'Descanso curto: 1 uso de Canalizar Divindade e de Fúria. Descanso longo: tudo volta, inclusive os PV e os espaços de magia.' + (c.id === 'Cleric' ? ' Depois do descanso longo, o clérigo pode trocar as magias preparadas.' : '')));
  }
}
