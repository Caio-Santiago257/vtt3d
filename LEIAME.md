# VTT 3D em primeira pessoa — protótipo

O mestre monta a cena no PC, vista de cima. Os jogadores entram pelo celular e veem o mapa em 3D pelos olhos do personagem.

## Como rodar

1. Instale o Node.js (versão LTS) em https://nodejs.org, se ainda não tiver.
2. Windows: dê dois cliques em `iniciar.bat`. Mac ou Linux: rode `./iniciar.sh`.
3. A tela do mestre abre em `http://localhost:3000/mestre`.
4. Os jogadores leem o QR code da tela do mestre com o celular, no mesmo Wi-Fi do PC.

Na primeira vez, o Windows pergunta se o Node pode aceitar conexões. Permita em **redes privadas**, senão os celulares não conseguem entrar.

Na primeira vez, o `iniciar.bat` (ou o `iniciar.sh`) roda `npm install` sozinho para baixar as dependências; precisa de internet só nessa hora. Se aparecer "npm não é reconhecido", o Node.js não está instalado: instale a versão LTS e abra um prompt novo.

## Tela do mestre

- **Colocar:** clique em um monstro ou objeto da lista e depois no mapa.
- **Mover:** arraste. Também funciona com os jogadores.
- **Girar / tamanho / remover:** selecione e use o painel, ou `Q`, `E` e `Delete`.
- **Portas:** clique em uma porta para abrir ou fechar.
- **Pausar movimento:** trava todos os jogadores onde estão.
- **Ponto de entrada:** onde os jogadores aparecem ao entrar.
- **Navegar:** botão direito arrasta o mapa, a roda do mouse dá zoom.

A cena é salva sozinha na pasta `data/` e volta quando você reinicia o servidor.

## Paredes e portas

Na seção **Paredes e portas**:

- **Desenhar parede / Desenhar porta:** arraste de um canto de quadrado a outro. Segure Shift para encaixar em meio quadrado. Diagonais funcionam.
- **Apagar:** clique ou arraste sobre uma parede para remover um quadrado dela por vez. Portas saem inteiras.

Enquanto a ferramenta está ativa, as paredes aparecem como linhas amarelas e as portas como linhas verdes. O 3D é refeito logo depois de cada alteração, para o mestre e para os jogadores.

## Mapas salvos

- **Salvar mapa atual:** guarda paredes, portas, terreno, bioma, monstros e objetos com um nome.
- **Lista de mapas:** clique no nome para abrir; o ✕ apaga o mapa salvo.
- **Novo mapa vazio:** cria um mapa em branco do tamanho que você escolher, para desenhar do zero.

Cada mapa salvo é um arquivo `.json` na pasta `mapas-salvos/`. Para levar um mapa para outro PC, copie o arquivo para a mesma pasta de lá.

## Mapas prontos: Covil do Dragão Negro

Na aba **Cena**, em **Mapas prontos**, o botão **Covil do Dragão Negro** troca o mapa da mesa. Antes, salve o mapa atual se quiser guardá-lo. O mapa vem de `mapas/prontos/covil-dragao-negro.json` e já traz o dragão no covil e quatro esqueletos nas ruínas. Os jogadores entram perto da estátua tombada, no sudoeste.

É um mapa grande: **64 × 64 quadrados (96 × 96 m)**, com relevo de verdade. O cenário foi recriado a partir das referências em `fontes/recebidos/covil-referencias/`:

- **Covil do dragão (noroeste):** caverna aberta cercada por paredões de rocha, com o chão coberto de ossos. Tem esqueletos humanos e sete esqueletos de criaturas grandes (quadrúpedes, chifrudos, serpentes). No fundo fica o tesouro: monte de ouro, baús, taças, gemas e aventureiros mortos em volta. No alto há um bosque de cogumelos que brilham, com um cogumelo gigante no meio.
- **Crista de rocha:** separa o covil do resto, em diagonal, e é coberta de matacões. A entrada é a **boca da caverna**, logo à frente do vau do rio. Quem voa alto passa por cima.
- **Rio:** fundo e sinuoso, de sudoeste para nordeste. Tem um **vau raso** na frente da boca da caverna. Nas partes fundas, os personagens nadam com a cabeça para fora.
- **Laboratório em ruínas (sudeste):** paredes com ameias quebradas, desmoronamentos, nichos de ossuário com crânios, canos de bronze e colunas caídas. Inundado pela água do pântano, e mais fundo quanto mais se entra:

  | Sala | Profundidade |
  |---|---|
  | D (entrada pela brecha norte) | 0,4 m |
  | Anexo | 0,7 m |
  | B | 0,9 a 1,7 m |
  | Corredor | 1,8 a 2,1 m |
  | C | 2,2 m |
  | A, a mais funda | 2,4 m |

  - Dentro: tanques de vidro (inteiros, com líquido verde que brilha, quebrados e tombados), mesas, estantes com livros, gaiolas com restos e frascos.
  - No meio da sala A, um **altar em degraus** seco, com crânios e velas.
  - O portão sul desabou e está bloqueado.
- **Pântano em volta:** musgo, lama, poças, juncos, ninfeias e árvores. A **cabeça colossal tombada** fica no sudoeste.
- **Borda:** do lado do covil, paredões altos. Do lado do pântano, uma fileira de árvores grandes e pedras. Há uma parede invisível bem na borda, e nem voando se passa. Ao longe, um fundo panorâmico de mata na névoa.
- **Regras:**
  - água e lama são terreno difícil;
  - o ataque de 1,5 m e o ataque de oportunidade funcionam igual;
  - as luzes vêm dos cogumelos, dos tanques, do altar, do tesouro e de uma fogueira na entrada.

**Gerar de novo** (depois de mudar a planta ou as texturas):

```
python3 fontes/mapas/covil_texturas.py      # texturas (1024 px; o fundo tem 4096 x 1024)
python3 fontes/mapas/covil_gerar.py         # relevo, água, mistura, colisão, vegetação, posições
python3 fontes/blender/covil_cenario.py     # ruínas, ossos, tesouro, cogumelos, estátua (GLB)
```

Os arquivos ficam em `public/assets/maps/covil/`. O motor de mapas com relevo está em `public/js/cenario.js` e serve para outros mapas prontos no mesmo formato: uma pasta com `dados.json`, `mistura_a.png`, `mistura_b.png`, as texturas em `tex/` e o GLB.

Peso do mapa:

| Arquivo | Tamanho |
|---|---|
| GLB | 12 MB |
| Texturas | 8 MB |
| Relevo e colisão | 0,2 MB |

Cada celular baixa tudo uma vez e guarda. O cenário tem cerca de 160 mil triângulos fixos, mais 95 mil do chão e as cópias leves de ossos, cogumelos e entulho.

## Mapas prontos: Encruzilhada da Floresta

Na aba **Cena**, em **Mapas prontos**, o botão **Encruzilhada da Floresta** carrega um mapa de batalha numa estrada antiga no meio da mata de pinheiros. Ele vem sem monstros: você coloca os inimigos que quiser. Os jogadores entram pela estrada do oeste.

É do mesmo tamanho do covil: **64 × 64 quadrados (96 × 96 m)**, com relevo de verdade. Foi recriado a partir das referências em `fontes/recebidos/estrada-referencias/`, que guarda a `Forest_Crossroads.jpg` e as vistas mandadas:

- **Estradas:** duas estradas de lajes de pedra se cruzam numa encruzilhada com uma placa de madeira.
  - A estrada leste–oeste é larga. A do norte para o sul é mais estreita.
  - As lajes são cinza-azuladas. Em alguns pontos faltam lajes ou há lama nas rodeiras.
  - As beiras são de terra batida, com blocos de pedra soltos (restos do meio-fio) e montinhos de blocos.
  - A estrada fica um pouco abaixo da mata, e o barranco de grama sobe dos lados.
- **Mata:**
  - pinheiros de três tamanhos, alguns quase pretos;
  - árvores de outono alaranjadas e arbustos amarelos e verdes;
  - três árvores mortas e brancas, pedras grandes, troncos caídos e tocos;
  - samambaias, touceiras com florzinhas e capim, mais densos na beira das estradas.
- **Poças:** poças escuras na mata. São terreno difícil.
- **Clareiras:** na encruzilhada e em volta dela, para a batalha caber.
- **Sombras:** a sombra das copas fica marcada no chão, na mesma direção do sol do jogo. Assim o mapa lê bem de cima, como na referência.
- **Em volta do mapa:**
  - a mata continua por 72 m para cada lado, com o relevo subindo devagar;
  - mais longe, o fundo panorâmico mostra a mata abrindo numa planície de capim, com bosques e fileiras de árvores, uma serra azulada e o céu de fim de tarde com nuvens;
  - a borda do mapa tem uma parede invisível, e nem voando se passa.
- **Clima:** tarde de sol, névoa leve e azulada ao longe e pólen no ar.
- **Vista do mestre:** as copas ficam um pouco transparentes, para você ver os personagens embaixo.
- **Regras:**
  - troncos, pedras grandes, troncos caídos, tocos e a placa bloqueiam a passagem;
  - poças são terreno difícil.

**Feito no Blender:** todas as árvores, plantas, pedras, blocos, troncos e a placa foram modelados por script no Blender (`fontes/blender/estrada_cenario.py`).

- **Pinheiros:** tronco com casca e andares de ramos em cartões dobrados em V, que pendem mais na base.
- **Árvores de folhas:** cachos de raminhos.
- **Pedras:** esferas deformadas por ruído e partidas em facetas.
- **Fundo panorâmico:** foi renderizado no Cycles (`fontes/blender/estrada_fundo.py`). A cena tem os mesmos pinheiros do kit, a planície, a serra e o céu físico. Depois a imagem é reprojetada para o cilindro do jogo.
- **No jogo:** o kit é um GLB leve (0,5 MB), e o jogo espalha cópias de cada peça nas posições geradas, cerca de 10 mil cópias. As cópias são separadas em blocos, para a câmera desenhar só o que está na frente dela.
- **Vento:** as plantas e as copas balançam com o vento.

**Gerar de novo** (depois de mudar a planta, as texturas ou os modelos):

```
python3 fontes/mapas/estrada_texturas.py    # texturas do chão e das folhas (cartões com transparência)
python3 fontes/mapas/estrada_gerar.py       # relevo, estradas, poças, mistura, sombras, posições, mapa pronto
python3 fontes/blender/estrada_cenario.py   # kit no Blender (GLB) e estrada_kit.blend
python3 fontes/blender/estrada_fundo.py     # fundo panorâmico no Cycles (uns 3 minutos)
```

Os arquivos ficam em `public/assets/maps/estrada/`. O motor de mapas (`public/js/cenario.js`) ficou genérico:

- cada mapa diz no `dados.json` quais texturas fazem cada papel do chão (e em que escala);
- se tem poças ou rio;
- se usa um kit instanciado ou um GLB inteiro;
- como é o fundo.

## Retratos da ordem de iniciativa

- **Arte desenhada:** a Kaira, nas três versões do modelo, o Ghult'ok, o Guy, o Kobold, o Dragão do Véu Corrompido e os quatro tipos de esqueleto usam a arte desenhada no lugar da foto do modelo 3D.
- **Arquivos:** os originais estão em `fontes/recebidos/retratos/`. Os recortes do rosto, em 256 px, estão em `public/assets/retratos/`.
- **Moldura:** o retrato é quadrado, com uma moldura dourada fina e dois losangos dourados nos cantos, uma versão simples da moldura da arte. Os cartões da ordem ficaram menores.
- **Novos retratos:** acrescente uma linha em `ART`, em `public/js/combate-ui.js`.

## Áreas de magia (medidor tático)

As formas seguem o Livro do Jogador 2024:

| Forma | O que é | Como se posiciona |
|---|---|---|
| **Esfera** | raio a partir de um ponto | arrastar o centro (encaixa nas interseções da grade), dentro do alcance |
| **Cilindro** | círculo de raio dado (a altura não aparece no mapa) | igual à esfera |
| **Cubo** | lado; a origem fica numa face | pessoal: sai de você e se aponta com o dedo; com alcance: arrastar (ocupa quadrados inteiros) |
| **Cone** | sai de você; a largura em cada ponto é igual à distância até a origem | apontar com o dedo |
| **Linha** | comprimento × largura (normalmente 1,5 m) | apontar com o dedo |
| **Emanação** (nova em 2024) | em volta de quem conjura e vai junto; quem a cria fica de fora | fica em você |

**Para o jogador:**
- **Em combate:** ao escolher **Magia** (a ação, ou a magia de ação bônus), aparece "Área da magia". Dá para escolher:
  - **Alvo único**, que mantém a escolha de alvo de antes;
  - uma das **magias prontas**: Bola de Fogo, Mãos Flamejantes, Relâmpago, Cone de Frio, Onda Trovejante, Guardiões Espirituais, Despedaçar, Coluna de Chamas, Nuvem de Adagas, Teia, Névoa Obscurecente e Sopro Ácido do dragão negro;
  - **Escolher forma e tamanho**: forma, tamanho, alcance (0 = sai de você) e, na linha, a largura.
- **Fora de combate:** o botão **◎ ÁREA DE MAGIA**, no canto da tela, abre a mesma escolha.
- **Visão tática:** depois da escolha, a câmera sobe num arco até ficar de cima, com a frente do personagem para cima na tela. A neblina some para ler o mapa.
  - Arrastar o dedo posiciona ou aponta a área.
  - Um círculo tracejado mostra o alcance, e a área não passa dele.
  - Quem está dentro ganha um anel vermelho (inimigo) ou verde (aliado), com a lista no canto.
  - **＋ / －** ou pinça com dois dedos aproximam e afastam; no PC, também a roda do mouse.
  - **CONFIRMAR** (Enter) envia a área e volta à visão de antes; **CANCELAR** (Esc) desiste.
  - Em combate, confirmar também gasta a ação.
- **Monstros:** o mestre, na visão do monstro, usa a mesma ferramenta. O Sopro Ácido do dragão está entre as magias prontas.

**Para o mestre:**
- **Aviso e câmera:** a área aparece no mapa com um brilho e um aviso de quem lançou. Se estiver fora da tela, a câmera desliza até ela.
- **Cartão:** no canto superior direito aparece um cartão com a magia, a forma e o tamanho, quem está dentro (vermelho = inimigos, verde = aliados) e uma barra do tempo restante.
- **Tempo:** a área some sozinha **15 segundos** depois da confirmação. Para mudar o tempo, inicie o servidor com `AOE_MS=30000`, por exemplo.
- **📌 FIXAR:** mantém a área até ser apagada, bom para Teia ou Névoa. Tocar de novo solta a área, e o tempo recomeça.
- **✕:** apaga a área na hora.
- **Jogadores:** também veem a área no chão, com uma borda de luz.

**Quem está dentro:** a criatura conta como atingida se a área cobre parte do espaço dela. O jogo testa pontos dentro de cada quadrado que ela ocupa, então o dragão 3 × 3 é pego pela ponta.

**Paredes e objetos cortam a área (linha de efeito):** o jogo traça raios a partir da origem da área. Para as áreas postas, a origem é o ponto escolhido; para o cone, a linha, o cubo pessoal e a emanação, é o centro de quem conjura.
- **Onde o raio para:** numa parede, numa porta fechada ou num objeto alto e sólido. A área continua pelos lados livres.
- **Objetos que bloqueiam:** barris, caixotes, caixas, estantes, tonéis, pilares, entulho e, nos cenários, árvores e pedras.
- **Objetos que não bloqueiam:** mesas, baús, camas e cadeiras são baixos, então a área passa por cima.
- **Nos cenários prontos:** só bloqueiam as paredes mais altas que uma pessoa.
- **Como aparece:** a parte bloqueada fica num cinza bem apagado, para mostrar o que a parede impediu. Quem está atrás da cobertura não entra na lista de atingidos.

**Feitiços da Kaira:** ao escolher Magia, quem joga de Kaira vê primeiro as magias de feiticeira, do truque ao 3º círculo, separadas por círculo.
- **Fonte:** dados do 5eTools, Livro do Jogador 2024 (`spells-xphb.json`, baixado do espelho oficial do 5eTools no GitHub).
- **Nomes:** os nomes em português foram traduzidos aqui. O nome original aparece ao parar o mouse em cima.
- **Magias com área** abrem a ferramenta tática:
  - truques: Respingo Ácido, Trovão;
  - 1º círculo: Mãos Flamejantes, Spray de Cores, Onda Trovejante, Sono, Graxa, Névoa Obscurecente;
  - 2º círculo: Despedaçar, Nuvem de Adagas, Teia, Escuridão, Lufada de Vento, Sopro do Dragão;
  - 3º círculo: Bola de Fogo, Relâmpago, Medo, Padrão Hipnótico, Lentidão, Nuvem Fétida, Tempestade de Granizo.
- **Magias de alvo** levam à escolha do alvo, como antes: Raio de Fogo, Explosão Feiticeira, Raio de Gelo, Lasca Mental, Orbe Cromático, Mísseis Mágicos, Faca de Gelo, Raio Ardente, Espinho Mental, Imobilizar Pessoa e Toque Vampírico.
- **Ação bônus:** o menu de ação bônus mostra só o Sopro do Dragão.
- **Registro:** o nome da magia aparece no registro do combate, por exemplo "Lyra ▸ Magia: Bola de Fogo".
- **Outros personagens:** basta acrescentar o grimório em `GRIMORIOS`, em `public/js/area.js`.

Código: `public/js/area.js` (formas, desenho, quem é atingido e a ferramenta tática), mensagens `aoe`, `aoe_del` e `aoe_fixar` em `server.js`.

## Terreno e biomas

Na seção **Terreno** da aba **Construir**:

- **Bioma:** cada botão monta uma paisagem pronta no mapa inteiro e muda o clima que os jogadores veem (neblina, luz, cor do céu). Cada clique gera um desenho diferente, no tamanho do mapa atual. Os mapas têm uma forma, com caminhos, água e um lugar aberto para a luta:
  - **Estrada na mata:** uma estrada de lajes de pedra cruza a mata de ponta a ponta. Às vezes uma segunda estrada cruza com ela, formando uma encruzilhada.
    - Beiras de terra com blocos de pedra soltos, clareira em volta do cruzamento, clareirinhas na mata e poças.
    - Usa o kit feito no Blender, o mesmo da Encruzilhada da Floresta: pinheiros (alguns quase pretos), árvores de outono, arbustos, samambaias, flores, capim e pedras.
    - Objetos de cena, todos modelados no Blender do mestre: a placa na encruzilhada, uma carroça quebrada na beira da estrada com caixotes caídos, o marco de pedra, um trecho de cerca e uma fogueira apagada na maior clareira.
    - A mata continua em volta do mapa e, ao longe, aparece o fundo panorâmico da planície.
  - **Floresta:** trilha de terra e um riacho cortando a mata, com uma clareira no meio. As bordas são mais fechadas.
  - **Pântano:** canais de água parada, margens de lama, ilhas de brejo e mata alagada.
  - **Deserto:** dunas, mesas de rocha, um leito seco de rio e um oásis com água e mato em volta.
  - **Neve:** campo nevado com lago congelado, bosques de pinheiro, rochas e uma trilha pisada.
  - **Caverna:** paredões irregulares na borda, chão de terra e rocha, um rio subterrâneo e um bolsão de lava.
  - **Masmorra:** piso de pedra, para você desenhar as paredes.
- **Chão com texturas:** cada tipo de chão tem uma textura de verdade (grama, chão da mata, terra, lama, brejo, areia, rocha, neve e lajes). A borda entre dois chãos é misturada e tremida, para não parecer quadriculada. As copas das árvores deixam sombra no chão, na direção do sol.
- **Fundo de cada bioma:** o mapa não fica mais flutuando no escuro. O chão do bioma continua até o horizonte e, ao longe, aparece um fundo panorâmico renderizado no Blender (Cycles, `fontes/blender/fundos_biomas.py`):
  - **Floresta:** colinas verdes, mata de pinheiros e árvores redondas, e uma serra azulada.
  - **Pântano:** charco com espelhos d'água, árvores mortas e névoa esverdeada.
  - **Deserto:** dunas, mesas de rocha avermelhada e uma serra árida.
  - **Neve:** campo nevado, pinheiros e montanhas brancas.
  - **Caverna:** paredões e teto de rocha, estalagmites e cristais azuis que brilham.
  - **Masmorra:** salão de pedra com colunas e tochas.
  - **Estrada na mata e Covil:** usam os fundos dos mapas prontos.
  - A névoa do fundo tem a cor da névoa do bioma, para emendar com o chão. Para gerar de novo: `python3 fontes/blender/fundos_biomas.py` (uns 3 minutos por bioma).
- **Só o clima:** troca neblina e luz sem repintar o chão.
- **Pincel:** escolha um chão e arraste no mapa. Os chãos são: grama, mata, terra, lama, brejo, água, areia, rocha, neve, lava, piso de pedra e **estrada de pedra**. Tamanhos 1, 2, 3 e 5 quadrados.
- **Retângulo:** arraste para preencher uma área de uma vez.

Um rio é só pintar água arrastando o mouse: as margens se misturam sozinhas e a água é animada. Árvores, juncos, pedras e arbustos aparecem conforme o chão pintado e somem se você pintar outra coisa por cima. Árvores, pedras, cactos, a carroça, a fogueira e o marco bloqueiam a passagem. Água, lama e brejo deixam o jogador mais lento.

**Objetos da estrada feitos no Blender do mestre:** carroça, cerca, fogueira, marco e caixotes.

- O script é o `fontes/blender/estrada_props.py`.
- Ele rodou no Blender aberto no PC do mestre, pela ponte do Blender. Os objetos ficaram lá, na coleção `COL_Estrada_Props`.
- O GLB exportado de lá foi trazido para `public/assets/maps/estrada/props.glb`.
- O mesmo script também roda aqui: `python3 fontes/blender/estrada_props.py`.

As texturas do chão ficam em `public/assets/terreno/tex/`. Para gerar de novo: `python3 fontes/mapas/terreno_texturas.py`.

## Combate (D&D 2024)

### Mestre: aba Combate

1. **Montar:** clique em **Selecionar no mapa** e clique nos jogadores e monstros que entram na luta, ou use **+ Todos os jogadores** e **+ Todos os monstros**. Quem está no combate ganha um anel no mapa.
2. **Iniciativa:** digite o valor de cada um. **Rolar d20 para monstros sem valor** preenche os monstros que faltam. Empates se resolvem com ▲ e ▼.
3. **Deslocamento:** cada participante começa com 9 m. Mude o número para quem tem bônus ou penalidade de velocidade.
4. **Oculto:** esconde uma criatura da ordem que os jogadores veem (ela continua agindo na vez dela).
5. **Iniciar combate:** a ordem é organizada pela iniciativa e começa a rodada 1.

Durante o combate:

- **Próximo turno** (ou a tecla **N**) e **Anterior**.
- O quadro do turno atual mostra quanto já foi andado. **+1,5 m / −1,5 m** dão ou tiram deslocamento só neste turno, e **Devolver mov.** zera o que foi gasto.
- Clique em **Ação**, **Bônus** ou **Reação** quando estiverem "usadas" para devolvê-las (caso de toque errado do jogador).
- O anel azul no mapa mostra o alcance de quem está agindo. Para monstros, o anel fica onde o monstro começou o turno, e você o move arrastando.
- Dá para incluir alguém no meio da luta: ligue a seleção, clique nele, ajuste a iniciativa e use **Reordenar pela iniciativa**.
- O **Registro** lista o que cada jogador declarou.

Os valores de iniciativa só aparecem para o mestre.

### Jogador: celular

- Quando o combate começa, a câmera passa para **terceira pessoa**, atrás do personagem. O botão no canto superior direito alterna entre 1ª e 3ª pessoa.
- A **ordem dos turnos** fica no canto superior esquerdo, com retratos e sem números. O botão **ORDEM** esconde e mostra a lista.
- Na sua vez aparece o aviso **SEU TURNO!**, com som e vibração, e o menu de comandos:
  - **Ação:** Atacar, Magia, Disparada, Desengajar, Esquivar, Ajudar, Esconder, Influenciar, Preparar, Procurar, Estudar, Utilizar.
  - **Ação bônus:** ataque com arma Leve, magia, poção, Disparada, Desengajar ou Esconder por habilidade de classe, outras habilidades.
  - **Reação:** uma por rodada, também fora do seu turno.
  - **Fim do turno:** toque duas vezes para passar a vez.
- Ações que pedem alvo mostram os retratos dos participantes para escolher.
- O círculo azul no chão mostra até onde você ainda pode ir, e o medidor embaixo mostra os metros que restam. **Disparada** soma mais um deslocamento.
- **Terreno difícil** (água, lama, brejo e mata) gasta o dobro.
- Fora da sua vez, seu personagem não anda e as portas não abrem.

O app só registra e mostra o que cada um declarou. Dados, acertos e dano continuam na mesa.

### Alcance do ataque básico

- **Atacar** (ação), **Ataque leve** (ação bônus) e **Oportunidade** (reação) só alcançam criaturas a até **1,5 m**, ou seja, um quadrado de distância.
- A distância é contada como no tabuleiro: de borda a borda, com a diagonal valendo um quadrado. Um personagem colado no dragão está a 1,5 m dele, mesmo que o centro do dragão esteja longe.
- Na lista de alvos, cada um mostra a distância. Quem está longe aparece apagado, com **FORA DE ALCANCE · 4,5 m**, e não pode ser escolhido.
- O servidor confere a distância de novo e recusa o ataque se ninguém estiver ao alcance.
- **Magia** e as demais ações não têm esse limite.

### Ataque de oportunidade

- Quando quem está agindo **sai do alcance** de uma criatura inimiga, essa criatura ganha a chance de reagir. Vale tanto para quem já começou o turno colado quanto para quem chegou perto e depois se afastou.
- Aparece o aviso **ATAQUE DE OPORTUNIDADE!**, com o retrato de quem saiu, e dois botões:
  - **ATACAR** gasta a reação da rodada.
  - **DEIXAR PASSAR** fecha o aviso.
- O aviso some sozinho em 15 segundos.
- Quem recebe o aviso:
  - se a reação é de um jogador, ele recebe no celular;
  - se é de um monstro, o mestre recebe na tela dele. Se o mestre estiver na visão desse monstro, recebe na visão.
- Não há oportunidade quando:
  - quem saiu usou **Desengajar** neste turno;
  - a reação de quem ficaria com a chance já foi gasta na rodada;
  - os dois são do mesmo lado (jogador com jogador, monstro com monstro).
- O mestre arrastar uma criatura que não é a da vez não provoca oportunidade.

### Mestre: visão do monstro

- Clique num monstro no mapa. Aparecem o botão **👁 VER VISÃO**, em cima do monstro, e **Ver visão do token**, no painel. A tecla de atalho é **V**.
- Uma íris fecha a tela a partir do monstro e você entra na visão dele, em terceira pessoa. O botão no canto alterna para primeira pessoa.
- **W A S D** e o mouse andam e olham, como para os jogadores.
- No turno do monstro aparece o mesmo menu de comandos dos jogadores: ação, ação bônus, reação e fim do turno. O deslocamento é contado igual ao dos jogadores. O dragão tem 12 m.
- **◀ VOLTAR AO MESTRE**, no topo, ou a tecla **Esc**, faz a transição de volta para o mapa do mestre.
- A tela do mestre continua conectada por baixo e para de desenhar enquanto a visão está aberta, para sobrar placa de vídeo.

### Voo

- **Quem voa:** criaturas com deslocamento de voo.
  - O **dragão negro adulto** já vem com **24 m**, o voo dele em D&D.
  - Jogadores só voam quando o mestre libera.
- **Liberar para um jogador:** na lista de jogadores da aba Cena, preencha o campo **✈ \_\_ m**. Com 0, ele não voa. No combate, cada participante também tem o campo **✈** ao lado do deslocamento.
- **Controles:**
  - **Celular:** quando o jogador tem voo, aparecem no lado direito os botões **▲** (subir) e **▼** (descer), para segurar, com a altura atual entre eles.
  - **Teclado** (inclusive o mestre na visão do monstro): **Espaço** sobe e **Shift** ou **C** desce. W A S D anda no ar.
- **Custo no combate:**
  - no ar, cada metro custa um metro, seja para o lado, para subir ou para descer;
  - terreno difícil não conta no ar;
  - o limite no ar é o deslocamento de voo, e no chão é o deslocamento normal;
  - o que já foi gasto vale para os dois, como na regra de trocar de deslocamento: quem anda 3 m no chão e levanta voo com 9 m ainda tem 6 m;
  - o medidor de movimento mostra **VOANDO**.
- **Altura máxima:** 30 m.
- **Paredes:** acima de 3 m de altura, as paredes e os objetos do chão não seguram mais. Num mapa de masmorra isso deixa voar por cima das paredes, porque o mapa ainda não tem teto.
- **Alcance:** a altura conta. Um dragão a 6 m do chão está fora do alcance de 1,5 m de quem está embaixo dele. O ataque de oportunidade também vale no ar.
- **Quem está no ar aparece com:**
  - uma sombra no chão;
  - um fio até o corpo;
  - a altura em metros, por exemplo **▲ 4,5 m**. Na tela do mestre aparece só a altura.
- Se o mestre tirar o voo de quem está no ar, ele volta ao chão.
- **Animações:** o dragão tem `fly_idle` (pairando, batendo as asas) e `fly` (voando para a frente, com as patas recolhidas). Personagens sem asas pairam parados, com uma leve flutuação.

### Criaturas grandes

- O **Dragão negro adulto** é Enorme: ocupa **3 × 3 quadrados** (4,5 × 4,5 m).
- O modelo dele tem 4,55 m de largura, 6,1 m de altura até a ponta das asas e 8,4 m de comprimento, com a cauda.
- Ao colocar ou soltar o dragão no mapa do mestre, ele se encaixa no meio de um quadrado, ocupando 3 × 3 quadrados inteiros. O anel vermelho em volta dele também é quadrado.
- O tamanho de cada monstro fica no campo `tamanho` do `public/assets/manifest.json`, o deslocamento em `deslocamento` e o voo em `voo`. O servidor lê os três ao iniciar. Do lado do jogo, o tamanho e o voo também ficam em `MONSTERS` (`size` e `fly`), em `public/js/common.js`.

## Galeria de assets

Abra `http://localhost:3000/galeria` no PC. A galeria mostra cada modelo com o mesmo material, contorno e luz do jogo:

- **Turnaround:** frente, 3/4, lateral, 3/4 costas e costas, lado a lado, como nas folhas conceituais.
- **Animação:** escolha qualquer clipe do modelo e pause num quadro.
- **Luz:** dia, masmorra ou estúdio.
- **Malha:** mostra a malha aramada.
- **Régua:** altura em metros e grade de quadrados de 1,5 m.

Também mostra triângulos, vértices, materiais, ossos e altura real de cada modelo.

## Personagens novos

**Kaira** (elfa etérea) é a primeira personagem no padrão novo e já aparece na escolha de personagem. A versão jogável vem do modelo 3D recebido (`fontes/recebidos/kaira_modelo_recebido.glb`, original preservado), preparado em duas etapas por script (Blender 5.3 como módulo Python):

1. `fontes/blender/kaira_glb_1_reduzir.py`: reduz a malha de 3,2 milhões para 60 mil triângulos e salva `kaira_glb_reduzido.blend`. Leva cerca de 1 minuto.
2. `fontes/blender/kaira_glb_2_rig.py`: põe a personagem em 1,80 m com os pés no chão e cria o esqueleto. Os pesos saem da cor da textura, que separa pele, cabelo e tecido. Depois aplica as 6 animações e exporta `public/assets/characters/kaira/char_kaira_modelo.glb`. Leva cerca de 15 segundos.

- **Esqueleto:** 81 ossos com nomes no padrão Mixamo. Tem correntes para cabelo, saia e mangas, mais `socket_hand_r`, `socket_hand_l`, `socket_back` e `socket_head`.
- **Animações:** `idle`, `walk`, `run`, `cast`, `hit` e `death`. São as mesmas funções da versão por script, com passo mais curto e saia e cabelo mais contidos.
- **Material:** rampa suave, sem contorno. O contorno marcava o tecido fino com manchas pretas.
- **Arquivo:** 4,6 MB, com texturas de cor e de normal em 2048 px.
- **Limite conhecido:** o modelo recebido é uma peça só, com tecido em várias camadas soltas. Por isso, na corrida e na conjuração a barra da saia e a manga ainda abrem algumas frestas.

A Kaira anterior, modelada inteira por script (`fontes/blender/kaira.py`), continua na galeria como "Kaira (feita por script)", em `char_kaira_script.glb`.

**Ghult'ok (orc bárbaro):** vem do modelo recebido do Meshy (`fontes/recebidos/ghultok_recebido.glb`, original preservado), preparado em duas etapas:

1. `fontes/blender/ghultok_1_reduzir.py`: reduz de 5,3 milhões para 260 mil triângulos (`TRIS=260000`). Com 60 mil, as mechas de pelo viravam serrilhado; com 260 mil o pelo e o rosto ficam fiéis ao modelo. Reduzir tudo de uma vez estoura a memória, então a malha é cortada em 6 fatias horizontais e cada uma é reduzida separada. Os vértices das emendas ficam fora da redução e se fundem de novo na junção, sem rachaduras.
2. `fontes/blender/ghultok_2_rig.py`: cria o esqueleto, distribui os pesos, gera as animações e exporta `public/assets/characters/ghultok/char_ghultok.glb` (17 MB). O sombreamento é suave (sem facetas).

- **Altura:** 2,1 m (tamanho Médio, ocupa 1 quadrado). Os olhos ficam mais altos, a 2,05.
- **Esqueleto:** os mesmos nomes de ossos da Kaira e do Guy, mais:
  - tanga da frente, pano de trás e franjas de pelo dos dois lados, com 3 ossos cada;
  - cabelo comprido nas costas, com 3 ossos;
  - o coque no alto da cabeça.
- **Peças grudadas:** no modelo recebido, o cabelo, a tanga, as franjas e as mãos vêm grudados no corpo, com arestas em comum. O script separa cada parte pela posição e pela cor; o vermelho da tanga é reconhecido pela cor. Depois corta as arestas entre partes que se mexem diferente (606 arestas) e refaz os pesos. Assim o pano não estica junto com a perna.
- **Joelho:** a articulação ficou acima do pelo da bota, para o pelo acompanhar a canela inteiro.
- **Braços colados no manto:** no modelo, os braços nascem colados no manto de pelo e na lateral do corpo, e as franjas das braçadeiras se misturam com as do quadril. Braço levantado acima do peito rasga a malha (vira uma "lâmina" esticada). Por isso as animações tiram a força do quadril, do tronco e da cabeça, e os braços se mexem pouco (no máximo uns 25 a 40 graus).
- **Cabelo comprido:** cai com a gravidade. Quando a cabeça vai para trás (no rugido), os ossos do cabelo compensam; sem isso, a ponta varria o quadril e esticava a malha.
- **Animações:** gravadas quadro a quadro, a 30 por segundo:
  - `walk`: passada pesada e calma de 1 s: contato, descida, passagem e subida duas vezes por ciclo; o quadril vai para o lado da perna de apoio; braços balançam pouco; a tanga, as franjas e o cabelo seguem com atraso;
  - `run`: corrida pesada, com o tronco inclinado e os punhos baixos;
  - `idle`: respiração funda e troca de peso;
  - `attack`: investida de ombro com cabeçada: recua o peso, gira o tronco e explode para a frente com o corpo todo;
  - `cast`: a Fúria; ele se encolhe, estufa o peito, joga a cabeça para trás e ruge tremendo;
  - `hit` e `death`.

**Guy (halfling clérigo):** vem do modelo recebido do Meshy (`fontes/recebidos/guy_recebido.glb`, original preservado), preparado em duas etapas:

1. `fontes/blender/guy_1_reduzir.py`: reduz de 1,66 milhão para 60 mil triângulos.
2. `fontes/blender/guy_2_rig.py`: cria o esqueleto, distribui os pesos, gera as animações e exporta `public/assets/characters/guy/char_guy.glb` (4,5 MB).

- **Altura:** 1 m (halfling, tamanho Pequeno, ocupa 1 quadrado). Para mudar, rode com `ALTURA=0.95 python3 guy_2_rig.py`, por exemplo.
- **Esqueleto:** os mesmos nomes de ossos da Kaira, mais quatro painéis do manto (três ossos cada), dois para o capuz caído nas costas e dois para o topete.
- **Pesos:** cada parte do corpo é separada por posição e pela cor da textura. Quatro detalhes importam:
  - **Cor da pele:** foi medida na textura, por volta de (0,99 0,86 0,78), para separar a pele do manto branco e do dourado.
  - **Mãos soltas do manto:** no modelo recebido, as mãos estão grudadas no manto, com arestas em comum. O script solta as faces da mão (120 arestas cortadas); sem isso, o tecido esticava junto com o braço.
  - **Suavização por parte:** os pesos são suavizados só entre vértices da mesma parte.
  - **Pernas e manto:** as pernas mexem o manto pela frente, por trás e pelos lados.
- **Animações:** são amostradas quadro a quadro, a 30 por segundo, e cada parte vem um pouco atrás da anterior:
  - **ordem do atraso:** quadril → tronco → ombros → braço → cotovelo → mão; o manto e o capuz vêm atrás das pernas, e o topete por último;
  - `walk`: trote curto e rápido de halfling, com 16 quadros por ciclo:
    - o pé rola do calcanhar à ponta e o joelho cede no impacto;
    - o corpo quica duas vezes por ciclo;
    - o quadril gira e o tronco gira ao contrário;
    - a cabeça mantém o olhar à frente;
  - `run`: corrida de 12 quadros;
  - `idle`: 3,6 s; respira, muda o peso de perna e olha em volta;
  - `cast`: prece com as mãos no peito, depois ergue a mão;
  - `attack`: golpe de maça;
  - `hit` e `death`.
- **Câmera:** os olhos ficam mais baixos, a 1,15 em vez de 1,8. A câmera de 3ª pessoa fica mais perto e mais baixa, na mesma proporção.
- **Não foi feito no Unity:** este ambiente não tem Unity. Tudo foi feito por script, com Blender.

**Kobold (monstro):** vem do modelo recebido (`fontes/recebidos/kobold_recebido.glb`, original preservado), preparado em duas etapas:

1. `fontes/blender/kobold_1_reduzir.py`: reduz de 1,3 milhão para 80 mil triângulos.
2. `fontes/blender/kobold_2_rig.py`: costura as emendas soltas da malha, cria o esqueleto, distribui os pesos, gera as animações e exporta `public/assets/characters/kobold/char_kobold.glb` (6,2 MB).

- **Ficha no jogo:** aparece na lista de monstros (Inimigos). Tamanho Pequeno (1 quadrado), 1,2 m de altura, deslocamento 9 m. O retrato da ordem de iniciativa é `public/assets/retratos/kobold.webp`.
- **Esqueleto:** coluna, pescoço em duas partes, cabeça e mandíbula, cauda com 5 ossos, pernas digitígradas (coxa, canela, pé e dedos) e tanga na frente e atrás. Tem os mesmos sockets dos outros personagens.
- **Pesos:** as partes são separadas por posição e pela cor da textura (a tanga amarela, as adagas do cinto e o vermelho das escamas). As adagas do cinto seguem só o quadril.
- **Pés no chão:** em cada quadro, o script calcula a posição dos pés e ajusta a altura do corpo para o pé de apoio tocar o chão.
- **Animações:**
  - `idle`: 4 s; agachado, olha em volta aos trancos, como um réptil, rosna, mexe as garras e a cauda;
  - `walk` e `run`: passos curtos e rápidos, corpo inclinado para a frente, cauda balançando;
  - `attack`: bote com as garras e mordida;
  - `cast`: grito de guerra com a boca bem aberta;
  - `hit` e `death`.
- **Limites:** em poses extremas, aparecem pequenos esticões no cinto e na junção do quadril.

**Kaira alada (Revelação Celestial):** vem do segundo modelo recebido do Meshy (`fontes/recebidos/kaira_asas_recebido.glb`, original preservado), preparado em duas etapas:

1. `fontes/blender/kaira_asas_1_reduzir.py`: reduz de 5,4 milhões para 60 mil triângulos.
2. `fontes/blender/kaira_asas_2_rig.py`: cria um esqueleto com ossos próprios para as asas (base, ponta e penas de baixo), a auréola, o cabelo e a saia. Depois aplica as animações e exporta `public/assets/characters/kaira/char_kaira_asas.glb` (4,6 MB).

- **Animações:**
  - `revelar`: encolhida, as asas brotam minúsculas e fechadas, crescem, se desdobram e dão uma batida forte, e a auréola aparece;
  - `fly_idle`: pairando, batendo as asas;
  - `fly`: voando para a frente;
  - `recolher`: as asas fecham e encolhem até sumir.
- **Não foi feito no Unity:** este ambiente não tem Unity. Tudo foi feito por script, com Blender para o modelo e as animações e three.js para os efeitos de luz.

### Como funciona no jogo

A Revelação Celestial só aparece para quem joga com a Kaira.

- **Fora de combate:** o botão **✦ REVELAÇÃO CELESTIAL** fica no canto da tela e dura 1 minuto. Tocar de novo desfaz as asas.
- **Em combate:** é uma **ação bônus**, no menu AÇÃO BÔNUS, e dura 10 rodadas. Se o combate acabar antes, o resto do minuto continua no relógio.
- **Voo:** enquanto a Revelação está ativa, ela voa com o próprio deslocamento (9 m), mesmo que o mestre não tenha dado voo.
- **Fim da Revelação:** quando acaba, se ela estiver no ar, desce ao chão.
- **Troca de modelo:** só acontece quando ela sai do chão (▲ ou Espaço). Até lá ela continua com o modelo normal.
- **Ao subir (cerca de 2,4 s):**
  - sobe uma coluna de luz dourada e um anel se abre no chão;
  - faíscas sobem em espiral;
  - ela salta girando duas voltas;
  - um clarão branco marca a troca de modelo e começa a animação `revelar`;
  - penas de luz caem em volta;
  - a auréola ganha um brilho que fica enquanto ela tem asas.
- **Ao pousar (cerca de 1,3 s):** toca `recolher`, faíscas descem, um clarão pequeno aparece e ela volta ao modelo normal.
- **Quem vê:** os outros jogadores e o mestre também veem a transição.
- **Código:** `public/js/revelacao.js`. Para usar com outra personagem, é só incluí-la em `REV_HEROES`, no servidor, e em `hasRevelation`, no cliente.

**Dragão do Véu Corrompido:** este modelo novo substitui o dragão negro antigo, que ficou guardado em `fontes/antigos/char_dragao_negro_modelo1.glb`. O original recebido também foi preservado, em `fontes/recebidos/dragao_veu_recebido.glb`.

O modelo foi preparado em duas etapas:
1. `fontes/blender/dragao_veu_1_reduzir.py`: reduz de 1,15 milhão para 40 mil triângulos.
2. `fontes/blender/dragao_veu_2_rig.py`: cria o esqueleto, distribui os pesos, gera as animações e exporta `public/assets/characters/dragao_negro/char_dragao_negro.glb`. O caminho do arquivo é o mesmo, então o jogo usa o modelo novo sem mudar nada.

- **Tamanho:** a escala segue a regra do antigo (3 × 3 quadrados e 3 de altura no mínimo): 11,6 m de comprimento, 7,6 m de envergadura e 4,55 m de altura.
- **Esqueleto:**
  - quadril → coluna → peito → dois ossos de pescoço → cabeça, com **mandíbula** separada;
  - cauda com 7 ossos;
  - patas com 3 ossos, com o cotovelo para trás e o joelho para a frente;
  - cada asa com braço, antebraço e três dedos (o maior em dois ossos).
- **Pesos:** separados por parte (corpo, asa, pata, mandíbula), com no máximo 4 ossos por vértice. A suavização só mistura vizinhos da mesma parte.
- **Animações:** gravadas quadro a quadro, a 30 por segundo, sem deslocamento embutido:
  - `idle`: 5 s; respira, olha em volta, ajeita a asa e entreabre a boca;
  - `walk`: andar de quadrúpede em sequência lateral, com 48 quadros. O corpo cai no apoio, a coluna faz um S, os ombros e o quadril rolam, a cabeça fica estável e a cauda ondula com atraso;
  - `run`: corrida em galope, com 24 quadros;
  - `attack`: mordida com antecipação, avanço em arco e a boca fechando;
  - `cast`: o sopro; ergue o peito puxando ar e abre as asas e a boca;
  - `roar`: rugido;
  - `hit` e `death`;
  - `fly_idle`: pairando, com duas batidas fortes por ciclo e o corpo inclinado de nariz para cima;
  - `fly`: voo para a frente, com uma batida larga e um trecho de planeio.
- **Batida das asas:** a descida é rápida, com a asa toda aberta. Na subida, mais lenta, o pulso dobra e os dedos recolhem. A ponta da asa vem atrasada.
- **Kaira e Guy:** também ganharam animações novas.
  - **Kaira:** andar novo (`walk_v2` em `kaira_glb_2_rig.py`). O pé rola do calcanhar à ponta, o passo cruza um pouco à frente e o quadril rola. Braços, cabelo, mangas e saia vêm com atraso.
  - **Kaira alada:** voo e pairar novos, com descida rápida e subida dobrando a asa.
  - **Guy:** o manto agora segue as pernas com atraso.
- **Skills e Blender:** a criação usou as skills `blender-skills` (blender-director, animation, rigging e as referências de creature-artist). O trabalho foi feito no Blender 5.3 sem tela, aqui no ambiente de trabalho. O Blender aberto no PC do Caio respondeu, mas não houve como trocar arquivos com ele sem uma pasta compartilhada.

**Dragão negro adulto:** vem do modelo recebido do Meshy (`fontes/recebidos/dragao_negro_recebido.glb`, original preservado), preparado em duas etapas:

1. `fontes/blender/dragao_1_reduzir.py`: reduz a malha de 2,4 milhões para 40 mil triângulos, em cerca de 1 minuto.
2. `fontes/blender/dragao_2_rig.py`: gira o corpo para andar para a frente, centra entre as quatro patas e escala para ocupar 3 × 3 quadrados. Depois cria o esqueleto e os pesos e aplica as animações. Leva cerca de 10 segundos.

- **Esqueleto:** 33 ossos, cobrindo coluna, pescoço, cabeça, cauda em 6 partes, 4 patas e 2 asas, cada asa com membrana em 3 pontas.
- **Animações:**
  - `idle`: respiração;
  - `walk`: passo diagonal;
  - `run`: corrida, com as asas meio abertas;
  - `attack`: mordida com garra;
  - `cast`: sopro, com as asas abertas;
  - `hit`: dano;
  - `death`: morte;
  - `fly_idle`: pairando, batendo as asas;
  - `fly`: voando para a frente.
- **Arquivo:** 3,6 MB.

## Organização dos assets

- `public/assets/characters`, `enemies`, `environment`, `buildings`, `props`, `animations`, `materials`, `textures`: assets no padrão novo.
- `public/assets/legacy/kaykit/`: os modelos KayKit em uso, até serem substituídos.
- `public/assets/manifest.json`: lista do que aparece na galeria.
- `fontes/recebidos/`: as folhas conceituais e referências recebidas, intactas.
- `fontes/kaykit/`: os pacotes KayKit originais completos.
- `fontes/blender/`: scripts e arquivos .blend que geram cada asset.
- `docs/inventario-assets.csv`: inventário de todos os modelos, arquivo por arquivo.

Padrão de exportação: metros, pivô no chão, frente para +Z no jogo, material com as propriedades extras `ramp`, `rim`, `spec`, `specSize`, `outline` e `noOutline`, que o jogo lê.

## Tela do jogador

- Lado esquerdo da tela: andar. Lado direito: olhar.
- Perto de uma porta aparece o botão de abrir e fechar.
- No computador: `W A S D`, arrastar o mouse e `E`.

## Importar mapas do Dungeon Alchemist

1. No Dungeon Alchemist, exporte o mapa como **Universal VTT** (arquivo `.dd2vtt`).
2. Na tela do mestre, clique em **Importar Universal VTT** e escolha o arquivo.
3. As paredes, portas e luzes do arquivo viram 3D. O botão **Chão** alterna entre as peças 3D e a imagem do mapa.

Para o resultado ficar melhor, exporte o mapa sem os móveis e coloque os móveis 3D pela lista de objetos.

## Mesa: mapa do mundo, cena 3D e imagem (teatro da mente)

A aba **Mesa** do mestre escolhe o que aparece no celular dos jogadores:

| Modo | O que os jogadores veem |
|---|---|
| 🗺 **Mapa do mundo** | o mapa de Faerûn, para olhar à vontade (é o modo padrão quando o servidor abre) |
| ⚔ **Cena 3D** | o mapa de batalha 3D, como antes; o botão **🗺 MAPA** (ou a tecla M) abre o mapa do mundo só para quem tocou |
| 🖼 **Imagem** | uma imagem em tela cheia, com legenda, para o teatro da mente |

- **Tela do mestre:** a área do mapa mostra o mesmo que os jogadores veem. **Ver a cena 3D só na minha tela** deixa o mestre mexer na cena enquanto os jogadores olham o mapa ou a imagem.
- **O modo fica salvo** em `data/mesa.json`.
- **Bateria:** com o mapa ou a imagem cobrindo a tela, o celular para de desenhar a cena 3D.

### Mapa de Faerûn

- **Mover:** arraste com um dedo. Dois dedos ou a roda do mouse aproximam e afastam. **⌖ MAPA TODO** volta para o mapa inteiro.
- **Escala:** a do próprio mapa, que vai de 0 a 480 milhas em 601,5 pixels (0,8 milha por pixel). No canto, uma barra de escala acompanha o zoom.
- **📏 RÉGUA:** arraste de um ponto a outro. Aparecem a distância em milhas e em km e o tempo de viagem a pé, no ritmo normal (24 milhas por dia), rápido (30) e lento (18), como no Livro do Jogador 2024.
  - De Águas Profundas a Portal de Baldur, em linha reta, dá 466 milhas (749 km), uns 19 dias a pé.
- **🧭 ROTA:** toque ponto a ponto (partida, paradas, destino). A conta da viagem vai somando trecho por trecho.
  - **SALVAR** pede um nome e guarda a rota para todos. **DESFAZER** tira o último ponto.
  - **🗺 ROTAS** lista as rotas salvas, com autor, distância e tempo. 👁 leva até a rota, e ✕ apaga (quem fez a rota ou o mestre).
  - O mestre tem **Apagar todas as rotas** na aba Mesa. As rotas ficam em `data/mesa.json`.
- **Ao vivo:** quando alguém usa a régua ou desenha uma rota, todos veem na hora, na cor do personagem e com o nome.
  - Cores: Guy dourado, Kaira lilás, Ghult'ok laranja, mestre azul-claro.
  - A régua some 12 segundos depois de soltar.
- **Ping:** segure o dedo (ou o botão esquerdo do mouse) parado num ponto por meio segundo. Aparecem ondas com o nome de quem marcou.
  - **Ping do mestre:** a tela de todos os jogadores desliza até o ponto e aproxima.
  - Quem está na cena 3D recebe um aviso.
- **📍 LUGARES:** liga e desliga os pontos de lore de 53 lugares: as capitais, as cidades grandes da Costa da Espada e do Norte, os Vales e o Mar da Lua, além de ruínas e lugares famosos.
  - Toque num ponto para ler um resumo. O link leva à página do lugar na Forgotten Realms Wiki, em inglês.
  - Com o mapa inteiro aparecem só os nomes das capitais e regiões; aproximando, aparecem todos.
  - A escolha fica guardada no celular.
- **📜 FICHA:** abre a ficha sem sair do mapa.

**Dados:** `fontes/mundo/gerar_faerun.py` gera `public/assets/mundo/faerun.json`, com a escala e os lugares. As posições foram conferidas uma a uma sobre a imagem. Os textos de lore foram escritos aqui, em resumo próprio, para a época da 5ª edição. O mapa original enviado fica em `fontes/recebidos/mundo/` e não vai para o GitHub. O jogo usa uma cópia em WEBP de 2,7 MB.

### Imagens (teatro da mente)

- **Enviar:** pelo botão **Enviar imagem…** ou arrastando os arquivos para a aba Mesa. Aceita PNG, JPG, WEBP ou GIF, até 40 MB. As imagens ficam em `data/imagens/`.
- **Mostrar:** clique numa imagem e ela aparece em tela cheia para todos, com a legenda, se você escreveu uma. Os jogadores podem aproximar com os dedos.
- **Apagar:** ✕ na miniatura.

Código: `public/js/mundo.js` (mapa e imagem), mensagens `mesa`, `ping`, `traco`, `rota_add`, `rota_del` e `rotas_limpar` em `server.js`.

## Régua

Mede a distância entre dois pontos do mapa, de quadrado a quadrado. Segue a regra do Livro do Jogador 2024: cada quadrado vale 1,5 m e a diagonal também conta 1 quadrado.

- **Jogador:** o botão **📏 RÉGUA**, no canto esquerdo, ou a tecla R no PC. Funciona dentro e fora de combate.
  - A câmera sobe num arco até a visão de cima, com a mesma transição da área de magia.
  - Toque num ponto e arraste o dedo: a linha tracejada vai sendo desenhada, e o rótulo na ponta mostra os metros, os quadrados e a distância em linha reta quando ela for diferente.
  - Os dois quadrados das pontas ficam destacados. A linha fica na tela até você medir de novo.
  - Dois dedos arrastam o mapa e aproximam ou afastam. No PC: botão direito arrasta, a roda dá zoom. **＋ / －** também funcionam.
  - **◀ VOLTAR** (ou Esc) volta para a visão de antes. Enquanto mede, o personagem fica parado.
- **Mestre:** o botão **📏 RÉGUA**, no canto superior direito do mapa, ou a tecla R. Com a régua ligada, arraste com o botão esquerdo para medir. O direito continua arrastando o mapa. Esc desliga.

- **Ao vivo:** o mestre e os outros jogadores veem a régua de quem está medindo na cena 3D, com o nome e a distância.

Código: `public/js/regua.js`.

## Ficha do personagem

Guy (clérigo), Kaira (feiticeira) e Ghult'ok (bárbaro) têm ficha. Quem joga com eles vê o botão **📜 FICHA** no canto esquerdo.

- **Onde fica salva:** no computador do mestre, na pasta `fichas` do projeto (`fichas/Guy.json`, `fichas/Kaira.json`, `fichas/Ghultok.json`). Salva sozinha a cada mudança, enquanto o servidor está aberto. A pasta não vai para o GitHub.
- **Aba FICHA:** o jogador preenche nível e atributos. O resto sai das regras da classe (Livro do Jogador 2024, dados do 5eTools):
  - modificadores, bônus de proficiência e salvaguardas da classe (marcadas com ●);
  - subclasse a partir do nível 3: domínio do clérigo, origem da feiticeira ou caminho do bárbaro. No Guy, também a Ordem Divina;
  - PV máximos sugeridos pelo dado de vida (pode mudar), CA, deslocamento, iniciativa, percepção passiva, CD e ataque de magia, dano de fúria;
  - perícias: toque para marcar proficiência; as opções da classe têm ★;
  - características de classe nível a nível, com as já liberadas acesas;
  - anotações livres.
- **Aba RECURSOS:**
  - pontos de vida, com botões de dano e cura e PV temporários;
  - espaços de magia por círculo (toque para gastar ou recuperar);
  - usos de Canalizar Divindade, Fúria, Feitiçaria Inata e pontos de feitiçaria;
  - **descanso curto:** recupera 1 uso de Canalizar Divindade e de Fúria;
  - **descanso longo:** tudo volta, inclusive os PV e os espaços. Toque duas vezes para confirmar.
- **Mestre:** a aba **Fichas** mostra o resumo de cada um: nível, PV, CA, espaços livres, usos e as magias preparadas do Guy.

### Magias preparadas do Guy

O clérigo pode preparar qualquer magia da lista de clérigo, até o círculo que o nível permite. A quantidade segue a tabela do clérigo 2024.

| Nível | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
|---|---|---|---|---|---|---|---|---|---|---|
| Magias preparadas | 4 | 5 | 6 | 7 | 9 | 10 | 11 | 12 | 14 | 15 |
| Círculo máximo | 1º | 1º | 2º | 2º | 3º | 3º | 4º | 4º | 5º | 5º |

Os truques são 3 até o nível 3, 4 do 4 ao 9 e 5 a partir do 10, com +1 pela Ordem Divina Taumaturgo.

- **Preparar:** na aba **MAGIAS**, fora de combate, toque nas magias. O contador mostra quantas cabem, e a ficha recusa passar do limite.
- **Domínio:** a partir do nível 3, as magias do domínio ficam sempre preparadas e não contam no limite.
- **Cada magia mostra:** efeito, tempo de conjuração, alcance ou área, e as marcas de concentração e ritual. O **ⓘ** abre a página da magia no 5e.tools, em inglês.
- **Em combate:** a lista fica travada. No menu **MAGIA** aparecem só os truques, as preparadas e as de domínio. Não aparecem as magias prontas genéricas nem as de 1 minuto ou mais.
  - **Espaços:** magias de 1º círculo ou mais gastam um espaço. Com mais de um círculo livre, o jogo pergunta qual usar e mostra o dano ou a cura no círculo elevado.
  - **Sem espaço:** a magia aparece apagada.
  - **Truques:** o dano sobe com o nível do personagem.
- **Item mágico:** a opção **Item mágico (alvo único)** e a área livre continuam no menu, para poções, varinhas e pergaminhos. Elas não gastam espaço.
- **Fora de combate:** o botão **◎ ÁREA DE MAGIA** mostra as magias de área preparadas, e confirmar também gasta o espaço.

**Kaira:** não prepara, mas o grimório dela agora segue a ficha. Em combate aparecem só os círculos que o nível permite, e cada magia gasta um espaço, do mesmo jeito. O grimório da Kaira no jogo continua indo até o 3º círculo.

**De onde vêm os dados:** `fontes/dados/gerar_dnd.py` lê os arquivos do 5eTools guardados em `fontes/dados/5etools/` e gera `public/js/dnd-dados.js`. São 139 magias: as 117 da lista de clérigo mais as dos quatro domínios. Os nomes em português foram traduzidos aqui. O nome original aparece ao parar o mouse em cima.

Código: `public/js/regras.js` (contas), `public/js/ficha-ui.js` (painel), mensagem `ficha` em `server.js`.

## O que ainda não existe

- As paredes só têm um visual (pedra). Os monstros são o dragão negro adulto e quatro esqueletos.
- O ataque de oportunidade só avisa: o movimento de quem saiu não é interrompido, e o resultado continua na mesa.
- Mapas com corredores de 1 ou 2 quadrados não comportam uma criatura 3 × 3. A colisão do dragão é um círculo, então ele passa raspando onde caberia de lado.
- A vegetação é automática: ainda não dá para colocar ou tirar uma árvore específica.
- Olhar girando o celular (giroscópio).
- Teto, escadas e andares.
- Senha para a tela do mestre: qualquer pessoa na rede que abrir `/mestre` controla a cena.
- Condições e rolagem de dados no app. Os pontos de vida da ficha não aparecem nos tokens do mapa.
- Ficha para os outros heróis (Cavaleiro, Mago…): só Guy, Kaira e Ghult'ok têm classe definida.
- O alcance no chão é em linha reta: não desvia de paredes nem desconta terreno difícil antes de você andar.
- A ordem de combate não é salva: se o servidor for reiniciado no meio da luta, monte a ordem de novo.

- No Covil do Dragão Negro, pintar o terreno muda só o custo de movimento dos quadrados. A aparência do cenário continua a mesma. As ferramentas de parede e porta valem por cima do cenário.
- A altura do voo é contada a partir do chão de baixo. Quem voa por cima da crista sobe junto com o relevo.

## Créditos

Modelos 3D: KayKit Dungeon Remastered, KayKit Adventurers e KayKit Skeletons, de Kay Lousberg (www.kaylousberg.com), licença CC0.
Renderização: three.js (licença MIT).
Fontes: Anton e M PLUS Rounded 1c (SIL Open Font License), em `public/fonts`.

## Tela cheia no celular e botão direito do mestre

- **Jogador no celular:**
  - Ao tocar em ENTRAR, o jogo entra em tela cheia e a barra de endereço some, com o celular em pé ou deitado.
  - Se a tela cheia cair (o jogador saiu dela ou trocou de aba), aparece o botão **⛶** no canto direito para voltar.
  - No PC e na visão do monstro do mestre isso não acontece.
- **iPhone:** o Safari não deixa um site entrar em tela cheia. O jeito é tocar em Compartilhar e em "Adicionar à Tela de Início". Aberto por esse ícone, o jogo roda sem barra nenhuma, graças ao `manifest.webmanifest` e às metas `apple-mobile-web-app`. O jogo mostra essa dica uma vez.
- **Mestre:** o botão direito (que gira a câmera) não abre mais o menu do navegador em nenhum lugar da página, mesmo quando o clique termina fora do mapa. Nos campos de texto, o menu de copiar e colar continua funcionando.

## Movimento no combate: círculo a partir do início do turno

O movimento funciona como em Trails in the Sky.
- **Círculo:** no começo do turno fica marcado o ponto de partida, um losango ciano no chão. O anel mostra até onde o personagem pode ir, com raio igual a todo o deslocamento (9 m, por exemplo).
- **Reposicionar:** dentro do círculo o jogador anda à vontade. Ir para um lado e voltar não gasta nada, porque o gasto é a distância em linha reta do início até onde ele está.
- **Na borda:** o personagem para ali e desliza ao longo dela, sem atravessar.
- **Terreno difícil:** o trecho da linha reta que passa por ele conta dobrado, então o círculo encolhe daquele lado.
- **Voo:** no ar conta a distância 3D, incluindo subir e descer.
- **Disparada e metros extras:** a Disparada e os metros extras dados pelo mestre aumentam o círculo.
- **Ataque de oportunidade:** não mudou. Sair do alcance de uma criatura hostil dispara a reação na hora, mesmo que o personagem volte depois e mesmo sem terminar o movimento.
- **Paredes:** ao contornar uma parede, o caminho real pode ser maior que a linha reta. O jogo conta só a linha reta, como um círculo de movimento faz.
- **Medidor:** o medidor de movimento ficou menor. No celular deitado, ele mostra só os metros e a barra.

