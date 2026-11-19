// Gera o mapa de exemplo no formato Universal VTT (sem imagem) e a cena inicial.
const fs = require('fs'), path = require('path');
const P = (x, y) => ({ x, y });
// Planta (em quadrados): sala de entrada 10x10, corredor, salão 12x12 ao leste, cripta 10x6 ao sul.
const los = [
  // sala de entrada (0,0)-(10,10): porta leste em y 4..5, porta sul em x 4..5
  [P(0, 0), P(10, 0), P(10, 4)],
  [P(10, 5), P(10, 10), P(5, 10)],
  [P(4, 10), P(0, 10), P(0, 0)],
  // corredor leste (10,3)-(16,6)
  [P(10, 3), P(16, 3)],
  [P(10, 6), P(16, 6)],
  // salão (16,-1)-(28,11): entrada oeste em y 4..5
  [P(16, 4), P(16, -1), P(28, -1), P(28, 11), P(16, 11), P(16, 5)],
  // corredor sul (3,10)-(6,14)
  [P(3, 10), P(3, 14)],
  [P(6, 10), P(6, 14)],
  // cripta (0,14)-(10,20): entrada norte em x 4..5
  [P(4, 14), P(0, 14), P(0, 20), P(10, 20), P(10, 14), P(5, 14)],
  // colunata do salão: dois trechos de parede soltos
  [P(20, 2), P(20, 4)],
  [P(24, 6), P(24, 8)],
];
const portal = (a, b, closed) => ({ position: P((a.x + b.x) / 2, (a.y + b.y) / 2), bounds: [a, b], rotation: 0, closed, freestanding: false });
const portals = [portal(P(10, 4), P(10, 5), true), portal(P(16, 4), P(16, 5), false), portal(P(4, 10), P(5, 10), true), portal(P(4, 14), P(5, 14), true)];
const light = (x, y, color = 'ffffb066', range = 6) => ({ position: P(x, y), range, intensity: 1, color, shadows: true });
const lights = [light(1, 1), light(9, 9), light(13, 4.5), light(17, 0), light(27, 0), light(27, 10), light(17, 10), light(22, 5, 'ffff7744', 8), light(1, 19, 'ff66ddaa'), light(9, 19, 'ff66ddaa')];
const uvtt = { format: 0.3, resolution: { map_origin: P(0, -1), map_size: P(28, 21), pixels_per_grid: 70 }, line_of_sight: los, objects_line_of_sight: [], portals, environment: { baked_lighting: false, ambient_light: 'ff333344' }, lights };
fs.writeFileSync(path.join(__dirname, '..', 'mapas', 'masmorra-exemplo.dd2vtt'), JSON.stringify(uvtt));
// cena inicial: posições em unidades de mundo (2 por quadrado), já com a origem (0,-1) descontada => z = (y+1)*2
const W = (x, y) => ({ x: x * 2, z: (y + 1) * 2 });
const e = (kind, model, x, y, deg = 0, scale = 1) => ({ kind, model, ...W(x, y), ry: (deg * Math.PI) / 180, scale });
const cena = [
  e('prop', 'barrel_large', 1, 1), e('prop', 'barrel_small', 1.9, 0.9), e('prop', 'crates_stacked', 8.8, 1.2, 20),
  e('prop', 'table_medium', 7.5, 7.5), e('prop', 'chair', 7.5, 6.3, 180), e('prop', 'stool', 6.4, 7.6, 90),
  e('prop', 'chest', 27, 5, -90), e('prop', 'table_long', 22, 9.5), e('prop', 'shelf_large', 22, -0.6), e('prop', 'pillar', 18.5, 1.5), e('prop', 'pillar', 18.5, 8.5), e('prop', 'pillar', 26, 1.5), e('prop', 'pillar', 26, 8.5),
  e('prop', 'bed_floor', 1.2, 18.5, 90), e('prop', 'chest_gold', 9, 17, -90), e('prop', 'rubble_large', 8.5, 15),
  e('monster', 'Skeleton_Warrior', 22, 5, -90, 1.25), e('monster', 'Skeleton_Minion', 20.5, 7, -70), e('monster', 'Skeleton_Rogue', 21, 2.5, -110), e('monster', 'Skeleton_Mage', 26, 5, -90),
  e('monster', 'Skeleton_Minion', 5, 17.5, 180),
];
fs.writeFileSync(path.join(__dirname, '..', 'mapas', 'masmorra-exemplo.cena.json'), JSON.stringify(cena));
console.log('ok', los.length, 'polilinhas');
