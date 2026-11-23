# Gera public/js/dnd-dados.js: classes (clérigo, feiticeiro, bárbaro) e a lista de magias do clérigo,
# a partir dos dados do 5eTools (Livro do Jogador 2024, XPHB), guardados em fontes/dados/5etools/.
# Rodar: python3 fontes/dados/gerar_dnd.py
import json, os, re

AQUI = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(AQUI, '5etools')
OUT = os.path.join(AQUI, '..', '..', 'public', 'js', 'dnd-dados.js')
ld = lambda f: json.load(open(os.path.join(SRC, f), encoding='utf8'))

# ---------------------------------------------------------------- nomes em português
NOMES = {
    'aid': 'Auxílio', 'animate dead': 'Animar Mortos', 'antimagic field': 'Campo Antimagia', 'astral projection': 'Projeção Astral',
    'augury': 'Augúrio', 'aura of life': 'Aura de Vida', 'aura of purity': 'Aura de Pureza', 'aura of vitality': 'Aura de Vitalidade',
    'bane': 'Perdição', 'banishment': 'Banimento', 'beacon of hope': 'Sinal de Esperança', 'bestow curse': 'Rogar Maldição',
    'blade barrier': 'Barreira de Lâminas', 'bless': 'Bênção', 'blindness/deafness': 'Cegueira/Surdez', 'calm emotions': 'Acalmar Emoções',
    'circle of power': 'Círculo de Poder', 'clairvoyance': 'Clarividência', 'command': 'Comando', 'commune': 'Comunhão',
    'conjure celestial': 'Conjurar Celestial', 'contagion': 'Contágio', 'continual flame': 'Chama Contínua', 'control water': 'Controlar a Água',
    'control weather': 'Controlar o Clima', 'create food and water': 'Criar Comida e Água', 'create or destroy water': 'Criar ou Destruir Água',
    'create undead': 'Criar Mortos-Vivos', 'cure wounds': 'Curar Ferimentos', 'daylight': 'Luz do Dia', 'death ward': 'Proteção contra a Morte',
    'detect evil and good': 'Detectar o Bem e o Mal', 'detect magic': 'Detectar Magia', 'detect poison and disease': 'Detectar Veneno e Doença',
    'dispel evil and good': 'Dissipar o Bem e o Mal', 'dispel magic': 'Dissipar Magia', 'divination': 'Adivinhação', 'divine word': 'Palavra Divina',
    'earthquake': 'Terremoto', 'enhance ability': 'Aprimorar Atributo', 'etherealness': 'Forma Etérea', 'feign death': 'Fingir-se de Morto',
    'find the path': 'Encontrar o Caminho', 'find traps': 'Encontrar Armadilhas', 'fire storm': 'Tempestade de Fogo', 'flame strike': 'Coluna de Chamas',
    'forbiddance': 'Proibição', 'freedom of movement': 'Liberdade de Movimento', 'gate': 'Portal', 'geas': 'Missão',
    'gentle repose': 'Repouso Tranquilo', 'glyph of warding': 'Glifo de Proteção', 'greater restoration': 'Restauração Maior',
    'guardian of faith': 'Guardião da Fé', 'guidance': 'Orientação', 'guiding bolt': 'Raio Guia', 'hallow': 'Consagrar', 'harm': 'Ferir',
    'heal': 'Cura Completa', 'healing word': 'Palavra Curativa', "heroes' feast": 'Banquete de Heróis', 'hold person': 'Imobilizar Pessoa',
    'holy aura': 'Aura Sagrada', 'inflict wounds': 'Infligir Ferimentos', 'insect plague': 'Praga de Insetos', 'legend lore': 'Lenda e Saber',
    'lesser restoration': 'Restauração Menor', 'light': 'Luz', 'locate creature': 'Localizar Criatura', 'locate object': 'Localizar Objeto',
    'magic circle': 'Círculo Mágico', 'mass cure wounds': 'Curar Ferimentos em Massa', 'mass heal': 'Cura Completa em Massa',
    'mass healing word': 'Palavra Curativa em Massa', 'meld into stone': 'Fundir-se à Pedra', 'mending': 'Consertar',
    'planar ally': 'Aliado Planar', 'planar binding': 'Vínculo Planar', 'plane shift': 'Mudança de Plano',
    'power word fortify': 'Palavra de Poder: Fortalecer', 'power word heal': 'Palavra de Poder: Curar', 'prayer of healing': 'Oração de Cura',
    'protection from energy': 'Proteção contra Energia', 'protection from evil and good': 'Proteção contra o Bem e o Mal',
    'protection from poison': 'Proteção contra Veneno', 'purify food and drink': 'Purificar Comida e Bebida', 'raise dead': 'Reviver os Mortos',
    'regenerate': 'Regenerar', 'remove curse': 'Remover Maldição', 'resistance': 'Resistência', 'resurrection': 'Ressurreição',
    'revivify': 'Revivificar', 'sacred flame': 'Chama Sagrada', 'sanctuary': 'Santuário', 'scrying': 'Vidência', 'sending': 'Enviar Mensagem',
    'shield of faith': 'Escudo da Fé', 'silence': 'Silêncio', 'spare the dying': 'Poupar os Moribundos', 'speak with dead': 'Falar com os Mortos',
    'spirit guardians': 'Guardiões Espirituais', 'spiritual weapon': 'Arma Espiritual', 'stone shape': 'Moldar Pedra',
    'summon celestial': 'Invocar Celestial', 'sunbeam': 'Raio de Sol', 'sunburst': 'Explosão Solar', 'symbol': 'Símbolo',
    'thaumaturgy': 'Taumaturgia', 'toll the dead': 'Dobre Fúnebre', 'tongues': 'Idiomas', 'true resurrection': 'Ressurreição Verdadeira',
    'true seeing': 'Visão da Verdade', 'warding bond': 'Vínculo Protetor', 'water walk': 'Andar sobre a Água', 'word of radiance': 'Palavra Radiante',
    'word of recall': 'Palavra de Retorno', 'zone of truth': 'Zona da Verdade',
    # magias de domínio que não estão na lista do clérigo
    'burning hands': 'Mãos Flamejantes', 'faerie fire': 'Fogo das Fadas', 'scorching ray': 'Raio Ardente', 'see invisibility': 'Ver o Invisível',
    'fireball': 'Bola de Fogo', 'arcane eye': 'Olho Arcano', 'wall of fire': 'Muralha de Fogo', 'charm person': 'Enfeitiçar Pessoa',
    'disguise self': 'Disfarçar-se', 'invisibility': 'Invisibilidade', 'pass without trace': 'Passos sem Pegadas',
    'hypnotic pattern': 'Padrão Hipnótico', 'nondetection': 'Indetectável', 'confusion': 'Confusão', 'dimension door': 'Porta Dimensional',
    'dominate person': 'Dominar Pessoa', 'modify memory': 'Modificar Memória', 'magic weapon': 'Arma Mágica',
    "crusader's mantle": 'Manto do Cruzado', 'fire shield': 'Escudo de Fogo', 'hold monster': 'Imobilizar Monstro',
    'steel wind strike': 'Golpe do Vento de Aço',
}
DANO = {'acid': 'ácido', 'bludgeoning': 'concussão', 'cold': 'frio', 'fire': 'fogo', 'force': 'energia', 'lightning': 'elétrico',
        'necrotic': 'necrótico', 'piercing': 'perfurante', 'poison': 'veneno', 'psychic': 'psíquico', 'radiant': 'radiante',
        'slashing': 'cortante', 'thunder': 'trovão'}
TR = {'strength': 'For', 'dexterity': 'Des', 'constitution': 'Con', 'intelligence': 'Int', 'wisdom': 'Sab', 'charisma': 'Car'}
COND = {'blinded': 'Cego', 'charmed': 'Enfeitiçado', 'deafened': 'Surdo', 'frightened': 'Amedrontado', 'grappled': 'Agarrado',
        'incapacitated': 'Incapacitado', 'invisible': 'Invisível', 'paralyzed': 'Paralisado', 'petrified': 'Petrificado',
        'poisoned': 'Envenenado', 'prone': 'Caído', 'restrained': 'Impedido', 'stunned': 'Atordoado', 'unconscious': 'Inconsciente'}
ESCOLA = {'A': 'Abjuração', 'C': 'Conjuração', 'D': 'Adivinhação', 'E': 'Encantamento', 'V': 'Evocação', 'I': 'Ilusão', 'N': 'Necromancia', 'T': 'Transmutação'}
COR = {'fire': 0xff8a3a, 'radiant': 0xffe9a0, 'necrotic': 0x7a5aa0, 'thunder': 0x9fb8ff, 'cold': 0xbfe3ff, 'lightning': 0x7fd8ff,
       'force': 0xc9a8ff, 'acid': 0x9bff4a, 'poison': 0xb8e06a, 'psychic': 0xff9ae6}
# resumo curto das que não causam dano nem curam (o resto sai dos dados)
NOTA = {
    'bless': '+1d4 em ataques e TR de até 3 criaturas', 'bane': '−1d4 em ataques e TR de até 3 criaturas · TR Car',
    'guidance': '+1d4 numa perícia à escolha', 'resistance': 'reduz 1d4 de um dano à escolha', 'light': 'objeto brilha 6 m',
    'thaumaturgy': 'pequenos prodígios: voz, chamas, tremores', 'spare the dying': 'estabiliza uma criatura com 0 PV',
    'mending': 'conserta uma quebra pequena', 'shield of faith': '+2 de CA', 'sanctuary': 'quem atacar o alvo faz TR Sab',
    'command': 'uma ordem de uma palavra · TR Sab', 'detect magic': 'sente magia a 9 m', 'aid': '+5 PV máx. em até 3 criaturas',
    'lesser restoration': 'acaba com Cego, Surdo, Paralisado ou Envenenado', 'silence': 'esfera de 6 m sem som',
    'calm emotions': 'suprime Amedrontado/Enfeitiçado · TR Car', 'hold person': 'Paralisado · TR Sab', 'warding bond': '+1 CA e TR, divide o dano',
    'augury': 'presságio: bom, ruim ou os dois', 'revivify': 'volta à vida quem morreu há até 1 min', 'dispel magic': 'acaba com uma magia',
    'beacon of hope': 'vantagem em TR de Sab e morte, cura máxima', 'death ward': 'cai a 1 PV em vez de 0', 'freedom of movement': 'ignora terreno difícil e Impedido',
    'banishment': 'manda para outro plano · TR Car', 'greater restoration': 'acaba com exaustão, maldição ou petrificação',
    'protection from evil and good': 'proteção contra aberrações, celestiais, corruptores…', 'invisibility': 'alvo fica Invisível',
    'see invisibility': 'vê criaturas invisíveis', 'faerie fire': 'contorno de luz: ataques com vantagem · TR Des',
    'magic weapon': 'arma vira mágica, +1', 'spiritual weapon': 'arma espectral: 1d8 + mod energia, ataca como ação bônus',
    'create or destroy water': 'cria ou destrói até 40 litros de água', 'detect poison and disease': 'sente venenos e doenças a 9 m',
    'detect evil and good': 'sente aberrações, celestiais, corruptores… a 9 m', 'disguise self': 'muda a aparência por ilusão',
    'purify food and drink': 'tira veneno e podridão da comida', 'enhance ability': 'vantagem em testes de um atributo',
    'continual flame': 'chama eterna, sem calor', 'find traps': 'sente armadilhas à vista', 'locate object': 'sente um objeto a até 300 m',
    'pass without trace': '+10 em Furtividade para o grupo', 'protection from poison': 'acaba com Envenenado, resistência a veneno',
    'gentle repose': 'impede que um corpo apodreça ou se levante', 'zone of truth': 'ninguém mente lá dentro · TR Car',
    'water walk': 'até 10 criaturas andam sobre líquidos', 'animate dead': 'cria um esqueleto ou zumbi',
    'clairvoyance': 'sensor invisível que vê ou ouve à distância', 'create food and water': 'comida e água para 15 pessoas',
    'daylight': 'esfera de 18 m de luz do dia', 'feign death': 'parece morto, resistência a quase tudo',
    'meld into stone': 'entra na pedra', 'nondetection': 'imune a adivinhação', 'protection from energy': 'resistência a um tipo de dano',
    'remove curse': 'acaba com maldições', 'revivify': 'volta à vida quem morreu há até 1 min, com 1 PV', 'sending': 'mensagem de 25 palavras a qualquer distância',
    'speak with dead': 'o cadáver responde 5 perguntas', 'tongues': 'entende e fala qualquer idioma', 'aura of vitality': 'ação bônus: cura 2d6 em alguém na aura',
    "crusader's mantle": 'aliados na aura causam +1d4 radiante', 'glyph of warding': 'glifo que explode ou guarda uma magia',
    'divination': 'pergunta a um deus sobre os próximos 7 dias', 'aura of purity': 'resistência a veneno e vantagem contra condições',
    'aura of life': 'resistência a necrótico; quem tem 0 PV recupera 1', 'confusion': 'age ao acaso · TR Sab',
    'control water': 'inunda, divide ou faz redemoinho na água', 'fire shield': 'escudo de chamas: resistência e dano em quem bate',
    'guardian of faith': 'guardião de 3 m: 20 radiante em quem chega · TR Des', 'locate creature': 'sente uma criatura a até 300 m',
    'stone shape': 'molda pedra', 'arcane eye': 'olho invisível que se move e vê', 'dimension door': 'teleporte de até 150 m',
    'wall of fire': 'muralha de chamas: 5d8 fogo · TR Des', 'circle of power': 'aliados com vantagem em TR contra magia',
    'commune': '3 perguntas de sim ou não ao deus', 'dispel evil and good': 'afasta e bane extraplanares',
    'hallow': 'consagra uma área com um efeito extra', 'legend lore': 'conta a lenda de algo importante',
    'planar binding': 'prende um ser extraplanar a seu serviço · TR Car', 'raise dead': 'volta à vida quem morreu há até 10 dias',
    'scrying': 'vê uma criatura em qualquer plano · TR Sab', 'summon celestial': 'invoca um espírito celestial aliado',
    'planar ally': 'pede ajuda a um ser do seu deus', "heroes' feast": 'banquete: +2d10 PV máx., imunidade a veneno e medo',
    'create undead': 'cria até 3 carniçais', 'find the path': 'sabe o caminho até um lugar', 'heal': 'cura 70 PV e acaba com Cego/Surdo/Envenenado',
    'word of recall': 'teleporta você e até 5 aliados ao santuário', 'true seeing': 'vê através de ilusões e o invisível (36 m)',
    'forbiddance': 'impede teleporte; dano a certos tipos de criatura', 'conjure celestial': 'coluna de luz: cura ou 6d12 radiante',
    'etherealness': 'vai para o Plano Etéreo', 'plane shift': 'leva até 9 criaturas para outro plano', 'power word fortify': '120 PV temporários divididos',
    'regenerate': 'cura 4d8 + 15 e regenera membros', 'resurrection': 'volta à vida quem morreu há até 100 anos',
    'symbol': 'glifo que dispara um efeito ao ser visto', 'antimagic field': 'nenhuma magia funciona na esfera',
    'control weather': 'muda o clima num raio de 8 km', 'holy aura': 'aliados com vantagem em TR; ataques contra eles com desvantagem',
    'astral projection': 'você e até 8 aliados viajam ao Plano Astral', 'gate': 'abre um portal para outro plano',
    'mass heal': 'cura até 700 PV divididos', 'power word heal': 'cura todos os PV e as condições de um alvo',
    'true resurrection': 'volta à vida quem morreu há até 200 anos', 'mass healing word': 'ação bônus: cura 2d4 + mod em até 6 criaturas',
    'sanctuary': 'quem atacar o alvo faz TR Sab ou escolhe outro', 'geas': 'impõe uma missão · TR Sab',
    'magic circle': 'cilindro que barra um tipo de criatura · TR Car', 'beacon of hope': 'vantagem em TR de Sab e de morte, cura máxima',
}

def ft2m(ft): return round(ft / 5 * 1.5, 1)
def plain(t):  # {@tag texto|...} -> texto
    return re.sub(r'\{@\w+ ([^}|]*)(?:\|[^}]*)?\}', r'\1', t)
def flat(entries):
    out = []
    for e in entries:
        if isinstance(e, str): out.append(e)
        elif isinstance(e, dict):
            out += flat(e.get('entries', [])) + flat(e.get('items', []))
    return out

spells = {s['name'].lower(): s for s in ld('spells-xphb.json')['spell']}
look = ld('gendata-spell-source-lookup.json')['xphb']
lista = sorted(n for n, v in look.items() if v.get('class', {}).get('XPHB', {}).get('Cleric'))

def tempo(s):
    t = s['time'][0]
    u = t['unit']
    if u in ('action', 'bonus', 'reaction'): return u
    return f"{t['number']} {'min' if u == 'minute' else 'h' if u == 'hour' else u}"

def spell(en):
    s = spells[en]
    raw = ' '.join(flat(s['entries'])); txt = plain(raw)
    rg = s['range']; dist = rg.get('distance', {})
    r = {'en': s['name'], 'nome': NOMES[en], 'circ': s['level'], 'escola': ESCOLA.get(s['school'], s['school']), 'tempo': tempo(s)}
    if s.get('meta', {}).get('ritual'): r['ritual'] = True
    if any(d.get('concentration') for d in s.get('duration', [])): r['conc'] = True
    d0 = s['duration'][0]
    if d0['type'] == 'timed':
        dd = d0['duration']; r['dur'] = f"{dd['amount']} {dict(round='rodada', minute='min', hour='h', day='dia').get(dd['type'], dd['type'])}"
    elif d0['type'] == 'instant': r['dur'] = 'instantânea'
    else: r['dur'] = 'até ser dissipada' if d0['type'] == 'permanent' else d0['type']
    # alcance
    if dist.get('type') == 'touch': r['alcance'] = 0; r['toque'] = True
    elif dist.get('type') == 'self': r['alcance'] = 0; r['pessoal'] = True
    elif dist.get('type') == 'feet': r['alcance'] = ft2m(dist['amount'])
    elif dist.get('type') == 'miles': r['alcance'] = dist['amount'] * 1600
    else: r['alcance'] = 0; r['especial'] = dist.get('type', rg['type'])
    # área: pessoal (cone, linha, emanação…) ou num ponto
    if rg['type'] in ('emanation', 'radius', 'sphere', 'cone', 'line', 'cube', 'cylinder', 'hemisphere'):
        forma = {'emanation': 'emanacao', 'radius': 'emanacao', 'sphere': 'emanacao', 'hemisphere': 'emanacao', 'cone': 'cone', 'line': 'linha', 'cube': 'cubo', 'cylinder': 'cilindro'}[rg['type']]
        r.update(forma=forma, tam=ft2m(dist['amount']), alcance=0); r.pop('pessoal', None)
        if forma == 'linha':
            m = re.search(r'(\d+) feet wide|(\d+)-foot-wide', txt); r['larg'] = ft2m(int(next(g for g in m.groups() if g))) if m else 1.5
    else:
        m = (re.search(r'(\d+)-foot-radius,? (?:\d+-foot-(?:high|tall) )?(Sphere|Cylinder|Emanation)', txt)
             or re.search(r'(\d+)-foot (Cube|Cone|Emanation)', txt) or re.search(r'(\d+)-foot-long,? (\d+)-foot-wide (Line)', txt))
        if m and 'areaTags' in s:
            g = m.groups()
            if g[-1] == 'Line': r.update(forma='linha', tam=ft2m(int(g[0])), larg=ft2m(int(g[1])))
            else:
                r.update(forma={'Sphere': 'esfera', 'Cylinder': 'cilindro', 'Emanation': 'emanacao', 'Cube': 'cubo', 'Cone': 'cone'}[g[-1]], tam=ft2m(int(g[0])))
                if r['forma'] in ('cone', 'emanacao') and not r.get('toque') and r['alcance']: pass
    if r.get('forma') == 'emanacao' and r.get('alcance'): r['forma'] = 'esfera'
    # efeito
    parts = []
    dmg = re.findall(r'\{@damage ([^}|]+)', raw)
    heal = 'HL' in s.get('miscTags', [])
    tipos = [DANO.get(t, t) for t in s.get('damageInflict', [])]
    if dmg and not heal: parts.append(f"{dmg[0]} {' ou '.join(tipos)}".strip())
    if heal:
        m = re.search(r'\{@dice ([^}|]+)\}', raw)
        parts.append(f"cura {m.group(1)} + mod" if m else 'cura')
    if s.get('savingThrow'): parts.append('TR ' + '/'.join(TR[x] for x in s['savingThrow']))
    if s.get('spellAttack'): parts.append('ataque')
    if en in NOTA and (not dmg or en in ('wall of fire', 'meld into stone', 'dimension door', 'fire shield', 'glyph of warding', 'conjure celestial', 'symbol', 'forbiddance', 'spiritual weapon', "crusader's mantle")): parts = [NOTA[en]] + [p for p in parts if p.startswith('TR') and 'TR' not in NOTA[en]]
    elif not dmg and not heal and s.get('conditionInflict'): parts.insert(0, ', '.join(COND.get(c, c) for c in s['conditionInflict']))
    r['efeito'] = ' · '.join(parts) if parts else ''
    # dano ou cura que sobe com o espaço de magia; truques que sobem com o nível do personagem
    hl = ' '.join(flat(s.get('entriesHigherLevel', [])))
    m = re.search(r'\{@scale(?:dice|damage) ([^|}]+)\|[^|}]*\|([^|}]+)', hl)
    if m and r['circ'] > 0: r['sobe'] = m.group(2)
    if r['circ'] == 0 and s.get('scalingLevelDice'): r['escala'] = True
    if s.get('damageInflict'): r['cor'] = COR.get(s['damageInflict'][0], 0xffe9a0)
    elif heal: r['cor'] = 0x8fffb0
    # alvo: magia de ataque ou de criatura sem área
    if not r.get('forma'): r['alvo'] = r['alcance']
    r['url'] = 'https://5e.tools/spells.html#' + re.sub(r'[^a-z0-9]+', '%20', en).strip('%20').replace(' ', '%20') + '_xphb'
    return r

# ---------------------------------------------------------------- classes
def cls(f):
    d = ld(f); c = [x for x in d['class'] if x.get('source') == 'XPHB'][0]
    return d, c
SALV = {'str': 'for', 'dex': 'des', 'con': 'con', 'int': 'int', 'wis': 'sab', 'cha': 'car'}
PER = {'acrobatics': 'acrobacia', 'animal handling': 'adestrar', 'arcana': 'arcanismo', 'athletics': 'atletismo', 'deception': 'enganacao',
       'history': 'historia', 'insight': 'intuicao', 'intimidation': 'intimidacao', 'investigation': 'investigacao', 'medicine': 'medicina',
       'nature': 'natureza', 'perception': 'percepcao', 'performance': 'atuacao', 'persuasion': 'persuasao', 'religion': 'religiao',
       'sleight of hand': 'prestidigitacao', 'stealth': 'furtividade', 'survival': 'sobrevivencia'}

def slots(c):
    for g in c['classTableGroups']:
        if 'rowsSpellProgression' in g: return g['rowsSpellProgression']
    return None

# características de classe: nome em português e um resumo curto (Livro do Jogador 2024)
FEAT = {
    'Cleric': [
        (1, 'Conjuração', 'Magias de clérigo preparadas a partir da lista inteira; Sabedoria é o atributo de conjuração.'),
        (1, 'Ordem Divina', 'Protetor (armas marciais e armadura pesada) ou Taumaturgo (+1 truque e bônus em Arcanismo/Religião).'),
        (2, 'Canalizar Divindade', 'Divindade Divina (cura) ou Expulsar Mortos-Vivos; recupera 1 uso no descanso curto e todos no longo.'),
        (3, 'Domínio Divino', 'Escolha do domínio: magias sempre preparadas e poderes próprios.'),
        (4, 'Aumento no Valor de Atributo', '+2 em um atributo ou +1 em dois (ou um talento).'),
        (5, 'Queimar Mortos-Vivos', 'Expulsar Mortos-Vivos também causa dano radiante.'),
        (6, 'Característica do Domínio', ''),
        (7, 'Golpes Abençoados', 'Golpe Divino (+1d8 no ataque) ou Conjuração Potente (+Sab no dano de truques).'),
        (8, 'Aumento no Valor de Atributo', ''),
        (10, 'Intervenção Divina', 'Uma vez por descanso longo, conjura qualquer magia de clérigo de até 5º círculo sem espaço.'),
        (12, 'Aumento no Valor de Atributo', ''),
        (14, 'Golpes Abençoados Aprimorados', 'O Golpe Divino passa a 2d8, ou a Conjuração Potente concede PV temporários.'),
        (16, 'Aumento no Valor de Atributo', ''),
        (17, 'Característica do Domínio', ''),
        (19, 'Dádiva Épica', 'Um talento de Dádiva Épica.'),
        (20, 'Intervenção Divina Maior', 'A Intervenção Divina pode conjurar Desejo (uma vez a cada 2d4 descansos longos).'),
    ],
    'Sorcerer': [
        (1, 'Conjuração', 'Magias de feiticeiro; Carisma é o atributo de conjuração.'),
        (1, 'Feitiçaria Inata', 'Ação bônus: 1 min com +1 na CD e vantagem nos ataques de magia (2 vezes por descanso longo).'),
        (2, 'Fonte de Magia', 'Pontos de feitiçaria: viram espaços de magia e vice-versa.'),
        (2, 'Metamagia', 'Duas opções de Metamagia para alterar magias com pontos de feitiçaria.'),
        (3, 'Origem Feiticeira', 'Escolha da subclasse.'),
        (4, 'Aumento no Valor de Atributo', ''),
        (5, 'Restauração Feiticeira', 'No descanso curto, recupera pontos de feitiçaria (metade do nível).'),
        (6, 'Característica da Origem', ''),
        (7, 'Feitiçaria Encarnada', 'Gasta 2 pontos para ativar a Feitiçaria Inata; duas Metamagias na mesma magia.'),
        (8, 'Aumento no Valor de Atributo', ''),
        (10, 'Metamagia', '+2 opções de Metamagia.'),
        (12, 'Aumento no Valor de Atributo', ''),
        (14, 'Característica da Origem', ''),
        (16, 'Aumento no Valor de Atributo', ''),
        (17, 'Metamagia', '+2 opções de Metamagia.'),
        (18, 'Característica da Origem', ''),
        (19, 'Dádiva Épica', 'Um talento de Dádiva Épica.'),
        (20, 'Apoteose Arcana', 'Com a Feitiçaria Inata ativa, uma Metamagia por turno sai de graça.'),
    ],
    'Barbarian': [
        (1, 'Fúria', 'Ação bônus: resistência a concussão, perfurante e cortante, + dano de fúria e vantagem em For.'),
        (1, 'Defesa sem Armadura', 'Sem armadura, CA = 10 + Des + Con (escudo vale).'),
        (1, 'Maestria em Armas', 'Usa a propriedade de maestria de algumas armas simples ou marciais.'),
        (2, 'Sentido de Perigo', 'Vantagem em TR de Destreza se não estiver Incapacitado.'),
        (2, 'Ataque Descuidado', 'Vantagem nos ataques de Força neste turno; ataques contra você também têm.'),
        (3, 'Caminho Primal', 'Escolha da subclasse.'),
        (3, 'Conhecimento Primal', 'Uma perícia a mais; em fúria, algumas perícias usam Força.'),
        (4, 'Aumento no Valor de Atributo', ''),
        (5, 'Ataque Extra', 'Dois ataques com a ação Atacar.'),
        (5, 'Movimento Rápido', '+3 m de deslocamento sem armadura pesada.'),
        (6, 'Característica do Caminho', ''),
        (7, 'Instinto Feral', 'Vantagem na iniciativa.'),
        (7, 'Bote Instintivo', 'Ao entrar em fúria, anda metade do deslocamento.'),
        (8, 'Aumento no Valor de Atributo', ''),
        (9, 'Golpe Brutal', 'Abre mão da vantagem do Ataque Descuidado: +1d10 e um efeito (empurrar ou atrasar).'),
        (10, 'Característica do Caminho', ''),
        (11, 'Fúria Implacável', 'Caindo a 0 PV em fúria, TR de Con (CD 10) para ficar de pé.'),
        (12, 'Aumento no Valor de Atributo', ''),
        (13, 'Golpe Brutal Aprimorado', 'Novos efeitos: Golpe Atordoante e Golpe Rasgante.'),
        (14, 'Característica do Caminho', ''),
        (15, 'Fúria Persistente', 'Recupera as fúrias na iniciativa uma vez; a fúria dura 10 min.'),
        (16, 'Aumento no Valor de Atributo', ''),
        (17, 'Golpe Brutal Aprimorado', '+2d10 e dois efeitos.'),
        (18, 'Poder Indomável', 'Testes de Força nunca ficam abaixo do valor de Força.'),
        (19, 'Dádiva Épica', 'Um talento de Dádiva Épica.'),
        (20, 'Campeão Primal', '+4 em Força e Constituição (máximo 25).'),
    ],
}
SUB = {
    'Cleric': {
        'Life': ('Domínio da Vida', {3: 'Discípulo da Vida, Preservar a Vida', 6: 'Curandeiro Abençoado', 17: 'Cura Suprema'}),
        'Light': ('Domínio da Luz', {3: 'Radiância da Alvorada, Clarão Protetor', 6: 'Clarão Protetor Aprimorado', 17: 'Coroa de Luz'}),
        'Trickery': ('Domínio da Trapaça', {3: 'Bênção do Trapaceiro, Invocar Duplicata', 6: 'Transposição do Trapaceiro', 17: 'Duplicata Aprimorada'}),
        'War': ('Domínio da Guerra', {3: 'Golpe Guiado, Sacerdote de Guerra', 6: 'Bênção do Deus da Guerra', 17: 'Avatar da Batalha'}),
    },
    'Sorcerer': {
        'Draconic': ('Feitiçaria Dracônica', {3: 'Resiliência Dracônica', 6: 'Afinidade Elemental', 14: 'Asas de Dragão', 18: 'Companheiro Dracônico'}),
        'Wild Magic': ('Magia Selvagem', {3: 'Marés do Caos, Surto de Magia Selvagem', 6: 'Distorcer a Sorte', 14: 'Caos Controlado', 18: 'Surto Domado'}),
        'Aberrant': ('Feitiçaria Aberrante', {3: 'Fala Telepática', 6: 'Feitiçaria Psiônica, Defesas Psíquicas', 14: 'Revelação na Carne', 18: 'Implosão Distorcida'}),
        'Clockwork': ('Feitiçaria Mecânica', {3: 'Restaurar o Equilíbrio', 6: 'Bastião da Lei', 14: 'Transe da Ordem', 18: 'Cavalgada Mecânica'}),
    },
    'Barbarian': {
        'Berserker': ('Caminho do Berserker', {3: 'Frenesi', 6: 'Fúria Irracional', 10: 'Retaliação', 14: 'Presença Intimidante'}),
        'Wild Heart': ('Caminho do Coração Selvagem', {3: 'Fala Animal, Fúria Selvagem', 6: 'Aspecto Selvagem', 10: 'Fala da Natureza', 14: 'Poder Selvagem'}),
        'World Tree': ('Caminho da Árvore do Mundo', {3: 'Vitalidade da Árvore', 6: 'Galhos da Árvore', 10: 'Raízes Esmagadoras', 14: 'Viagem pela Árvore'}),
        'Zealot': ('Caminho do Fanático', {3: 'Fúria Divina, Guerreiro dos Deuses', 6: 'Foco Fanático', 10: 'Presença Zelosa', 14: 'Fúria dos Deuses'}),
    },
}
HEROI = {'Guy': 'Cleric', 'Kaira': 'Sorcerer', 'Ghultok': 'Barbarian'}
NOME_CL = {'Cleric': 'Clérigo', 'Sorcerer': 'Feiticeira', 'Barbarian': 'Bárbaro'}
ATR = {'Cleric': 'sab', 'Sorcerer': 'car'}

classes = {}
dom_spells = set()
for f, cid in [('class-cleric.json', 'Cleric'), ('class-sorcerer.json', 'Sorcerer'), ('class-barbarian.json', 'Barbarian')]:
    d, c = cls(f)
    sp = c['startingProficiencies']
    sk = sp['skills'][0]['choose']
    o = {'id': cid, 'nome': NOME_CL[cid], 'dv': c['hd']['faces'], 'salv': [SALV[x] for x in c['proficiency']],
         'armas': sp.get('weapons', []), 'armaduras': sp.get('armor', []),
         'pericias': {'de': [PER[x] for x in sk['from']], 'n': sk['count']}, 'carac': FEAT[cid], 'subs': {}}
    if cid in ATR:
        o['atr'] = ATR[cid]; o['slots'] = slots(c)
        o['truques'] = c['cantripProgression']; o['preparadas'] = c['preparedSpellsProgression']
    for t in c['classTableGroups']:
        if 'rows' not in t: continue
        labs = [plain(l).split('|')[0] for l in t['colLabels']]
        for j, lab in enumerate(labs):
            col = [r[j] if not isinstance(r[j], dict) else r[j]['value'] for r in t['rows']]
            key = {'Channel Divinity': 'canalizar', 'Sorcery Points': 'pontos', 'Rages': 'furias', 'Rage Damage': 'danoFuria', 'Weapon Mastery': 'maestria'}.get(lab)
            if key: o[key] = [int(x) for x in col]
    for s in d['subclass']:
        if s['source'] != 'XPHB': continue
        nm, feats = SUB[cid][s['shortName']]
        sub = {'nome': nm, 'carac': feats}
        if cid == 'Cleric':
            prep = s['additionalSpells'][0]['prepared']
            sub['magias'] = {int(k): [x.split('|')[0] for x in v] for k, v in prep.items()}
            for v in sub['magias'].values(): dom_spells.update(v)
        o['subs'][s['shortName']] = sub
    classes[cid] = o

todas = sorted(set(lista) | dom_spells)
magias = [spell(n) for n in todas]
for m in magias:
    if m['en'].lower() not in lista: m['dominio'] = True   # só entra pelo domínio
magias.sort(key=lambda m: (m['circ'], m['nome']))

js = ('// Gerado por fontes/dados/gerar_dnd.py a partir do 5eTools (Livro do Jogador 2024, XPHB). Não edite à mão.\n'
      f'export const HEROI_CLASSE = {json.dumps(HEROI)};\n'
      f'export const CLASSES = {json.dumps(classes, ensure_ascii=False)};\n'
      f'export const MAGIAS_CLERIGO = {json.dumps(magias, ensure_ascii=False)};\n')
open(OUT, 'w', encoding='utf8').write(js)
print('magias', len(magias), 'de domínio só:', sum(1 for m in magias if m.get('dominio')), '->', OUT, os.path.getsize(OUT), 'bytes')
