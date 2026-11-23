// Regras da ficha (Livro do Jogador 2024): modificadores, proficiência, espaços de magia e magias preparadas.
import { CLASSES, HEROI_CLASSE, MAGIAS_CLERIGO } from './dnd-dados.js';
import { GRIMORIO_FEITICEIRO } from './area.js';

export const ATRS = [['for', 'Força'], ['des', 'Destreza'], ['con', 'Constituição'], ['int', 'Inteligência'], ['sab', 'Sabedoria'], ['car', 'Carisma']];
export const ATR_CURTO = { for: 'FOR', des: 'DES', con: 'CON', int: 'INT', sab: 'SAB', car: 'CAR' };
export const PERICIAS = [
  ['acrobacia', 'Acrobacia', 'des'], ['adestrar', 'Adestrar Animais', 'sab'], ['arcanismo', 'Arcanismo', 'int'], ['atletismo', 'Atletismo', 'for'],
  ['atuacao', 'Atuação', 'car'], ['enganacao', 'Enganação', 'car'], ['furtividade', 'Furtividade', 'des'], ['historia', 'História', 'int'],
  ['intimidacao', 'Intimidação', 'car'], ['intuicao', 'Intuição', 'sab'], ['investigacao', 'Investigação', 'int'], ['medicina', 'Medicina', 'sab'],
  ['natureza', 'Natureza', 'int'], ['percepcao', 'Percepção', 'sab'], ['persuasao', 'Persuasão', 'car'], ['prestidigitacao', 'Prestidigitação', 'des'],
  ['religiao', 'Religião', 'int'], ['sobrevivencia', 'Sobrevivência', 'sab'],
];
export const CIRC_NOME = ['Truque', '1º círculo', '2º círculo', '3º círculo', '4º círculo', '5º círculo', '6º círculo', '7º círculo', '8º círculo', '9º círculo'];
export const temFicha = (hero) => !!HEROI_CLASSE[hero];
export const classeDe = (hero) => CLASSES[HEROI_CLASSE[hero]];
export const mod = (v) => Math.floor((v - 10) / 2);
export const fmtMod = (n) => (n >= 0 ? '+' : '−') + Math.abs(n);
export const prof = (nivel) => 2 + Math.floor((nivel - 1) / 4);

// valores iniciais (o jogador muda na ficha)
const INICIAL = {
  Guy: { atr: { for: 10, des: 12, con: 14, int: 10, sab: 16, car: 13 }, pericias: ['medicina', 'religiao', 'intuicao', 'persuasao'], sub: 'Life', ca: 16 },
  Kaira: { atr: { for: 8, des: 14, con: 14, int: 10, sab: 12, car: 16 }, pericias: ['arcanismo', 'enganacao', 'intuicao', 'persuasao'], sub: '', ca: 12 },
  Ghultok: { atr: { for: 16, des: 14, con: 16, int: 8, sab: 12, car: 10 }, pericias: ['atletismo', 'intimidacao', 'percepcao', 'sobrevivencia'], sub: '', ca: 15 },
};
export function novaFicha(hero) {
  const b = INICIAL[hero] || INICIAL.Guy;
  const f = { hero, nivel: 1, atr: { ...b.atr }, sub: b.sub, ordem: 'protetor', pericias: [...b.pericias], salvExtra: [], pvTemp: 0, ca: b.ca,
    deslocamento: hero === 'Guy' ? 7.5 : 9, truques: [], preparadas: [], slotsUsados: [0, 0, 0, 0, 0, 0, 0, 0, 0], usos: {}, notas: '' };
  f.pvMax = pvSugerido(f); f.pv = f.pvMax;
  if (hero === 'Guy') { f.truques = ['Sacred Flame', 'Guidance', 'Thaumaturgy']; f.preparadas = ['Bless', 'Cure Wounds', 'Healing Word', 'Guiding Bolt']; }
  return f;
}
export function pvSugerido(f) {
  const c = classeDe(f.hero), m = mod(f.atr.con);
  return Math.max(1, c.dv + m + (f.nivel - 1) * (c.dv / 2 + 1 + m));
}
export const slotsMax = (f) => { const c = classeDe(f.hero); return c && c.slots ? c.slots[f.nivel - 1] : [0, 0, 0, 0, 0, 0, 0, 0, 0]; };
export const slotsLivres = (f, circ) => Math.max(0, slotsMax(f)[circ - 1] - (f.slotsUsados[circ - 1] || 0));
export function circMax(f) { const s = slotsMax(f); let n = 0; s.forEach((v, i) => { if (v > 0) n = i + 1; }); return n; }
export const atrMagia = (f) => classeDe(f.hero).atr;
export const cdMagia = (f) => 8 + prof(f.nivel) + mod(f.atr[atrMagia(f)]);
export const ataqueMagia = (f) => prof(f.nivel) + mod(f.atr[atrMagia(f)]);
export const truquesMax = (f) => { const c = classeDe(f.hero); return c.truques ? c.truques[f.nivel - 1] + (f.hero === 'Guy' && f.ordem === 'taumaturgo' ? 1 : 0) : 0; };
export const preparadasMax = (f) => { const c = classeDe(f.hero); return c.preparadas ? c.preparadas[f.nivel - 1] : 0; };
export const usosMax = (f) => {
  const c = classeDe(f.hero), n = f.nivel - 1, out = {};
  if (c.canalizar && c.canalizar[n]) out.canalizar = c.canalizar[n];
  if (c.furias) out.furias = c.furias[n];
  if (c.pontos && c.pontos[n]) out.pontos = c.pontos[n];
  if (f.hero === 'Kaira') out.inata = 2;
  if (f.hero === 'Guy' && f.nivel >= 10) out.intervencao = 1;
  return out;
};
export const USO_NOME = { canalizar: 'Canalizar Divindade', furias: 'Fúria', pontos: 'Pontos de Feitiçaria', inata: 'Feitiçaria Inata', intervencao: 'Intervenção Divina' };
// descanso curto: Canalizar Divindade e Fúria voltam 1; Restauração Feiticeira (nível 5) devolve metade do nível em pontos
export function descansoCurto(f) {
  const u = f.usos;
  if (u.canalizar) u.canalizar--;
  if (u.furias) u.furias--;
  if (f.hero === 'Kaira' && f.nivel >= 5 && u.pontos) u.pontos = Math.max(0, u.pontos - Math.floor(f.nivel / 2));
}
export function descansoLongo(f) {
  f.slotsUsados = [0, 0, 0, 0, 0, 0, 0, 0, 0]; f.usos = {}; f.pv = f.pvMax; f.pvTemp = 0;
}

// ---- magias
const BY_EN = new Map(MAGIAS_CLERIGO.map((m) => [m.en, m]));
export const magiaClerigo = (en) => BY_EN.get(en);
export function magiasDominio(f) {
  const c = classeDe(f.hero), sub = c && c.subs[f.sub];
  if (!sub || !sub.magias || f.nivel < 3) return [];
  const out = [];
  for (const [lv, list] of Object.entries(sub.magias)) if (f.nivel >= +lv) for (const n of list) {
    const m = MAGIAS_CLERIGO.find((x) => x.en.toLowerCase() === n); if (m) out.push(m);
  }
  return out;
}
// o que o personagem pode conjurar agora (truques + preparadas + de domínio), com a marca de onde vem
export function grimorio(f) {
  if (!f) return null;
  if (f.hero === 'Guy') {
    const cm = circMax(f), dom = magiasDominio(f), seen = new Set();
    const out = [];
    for (const m of dom) { seen.add(m.en); out.push({ ...m, dominio: true }); }
    for (const en of f.truques) { const m = BY_EN.get(en); if (m && m.circ === 0 && !seen.has(en)) { seen.add(en); out.push(m); } }
    for (const en of f.preparadas) { const m = BY_EN.get(en); if (m && m.circ > 0 && m.circ <= cm && !seen.has(en)) { seen.add(en); out.push(m); } }
    return out.sort((a, b) => a.circ - b.circ || a.nome.localeCompare(b.nome));
  }
  if (f.hero === 'Kaira') { const cm = circMax(f); return GRIMORIO_FEITICEIRO.filter((p) => p.circ <= cm); }
  return null;
}
// efeito com o dano ou a cura do espaço usado (e dos truques pelo nível do personagem)
export function efeitoEm(m, slot, nivel) {
  let t = m.efeito || '';
  if (m.circ === 0 && m.escala) {
    const k = 1 + (nivel >= 5) + (nivel >= 11) + (nivel >= 17);
    return t.replace(/(\d+)d(\d+)/, (_, n, d) => `${n * k}d${d}`);
  }
  if (m.sobe && slot > m.circ) {
    const extra = slot - m.circ, md = /^(\d+)d(\d+)$/.exec(m.sobe);
    if (md) return t.replace(new RegExp(`(\\d+)d${md[2]}`), (_, n) => `${+n + md[1] * extra}d${md[2]}`);
    if (/^\d+$/.test(m.sobe)) return t.replace(/(\d+) PV/, (_, n) => `${+n + m.sobe * extra} PV`);
  }
  return t;
}
export const tempoNome = (t) => ({ action: 'ação', bonus: 'ação bônus', reaction: 'reação' }[t] || t);
