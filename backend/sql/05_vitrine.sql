-- =====================================================================
-- 05_vitrine.sql : catalogo de demonstracao (apresentacao), sobre o seed.
-- Rodar APOS 04_seed.sql. So faz UPDATE em linhas existentes: nao muda
-- quantidade de linhas, ids, estoque, pedidos (unit_price) nem indices.
--   * 10 categorias raiz e 50 subcategorias com nomes reais de varejo,
--     atribuidos pela relacao parent_id (corrige a numeracao do seed);
--   * 100 mil produtos com nome, descricao e preco da sua subcategoria,
--     marcas FICTICIAS e variacao deterministica pelo numero do SKU;
--   * product_images apontando para fotos locais do frontend
--     (/produtos/<slug-da-subcategoria>/<1|2>.jpg).
-- Reaplicavel: reconhece as categorias pelos slugs do seed (cat-N, cat-N-S)
-- ou pelos slugs ja aplicados, e produz sempre o mesmo resultado.
-- Sem metacomandos do psql (roda pelo entrypoint e pelo psql).
-- =====================================================================
BEGIN;

CREATE TEMP TABLE vitrine_def (
    dept INT, dept_name TEXT, dept_slug TEXT,
    leaf INT, leaf_name TEXT, leaf_slug TEXT,
    tipo TEXT, vars TEXT[], pmin NUMERIC, pmax NUMERIC, descr TEXT
) ON COMMIT DROP;

-- vars em ordem crescente de preco: a variacao define a faixa do preco
INSERT INTO vitrine_def VALUES
(1,'Eletrodomésticos','eletrodomesticos',1,'Geladeiras','geladeiras','Geladeira',
 '{"Frost Free 260 L","Frost Free 340 L","Frost Free 410 L Inox","Duplex 480 L Inox","Side by Side 560 L"}',1900,8900,
 'Refrigerador com controle eletrônico de temperatura, prateleiras ajustáveis e baixo consumo de energia.'),
(1,'Eletrodomésticos','eletrodomesticos',2,'Fogões','fogoes','Fogão',
 '{"4 Bocas Branco","4 Bocas Inox","5 Bocas Inox","5 Bocas Mesa de Vidro","Cooktop 5 Bocas"}',700,3200,
 'Fogão com acendimento automático, queimadores de alto rendimento e forno amplo.'),
(1,'Eletrodomésticos','eletrodomesticos',3,'Micro-ondas','micro-ondas','Micro-ondas',
 '{"20 L Branco","25 L Espelhado","30 L Inox","32 L com Grill","34 L Inox Digital"}',450,1500,
 'Micro-ondas com painel digital, funções pré-programadas e trava de segurança.'),
(1,'Eletrodomésticos','eletrodomesticos',4,'Máquinas de lavar','maquinas-de-lavar','Máquina de Lavar',
 '{"9 kg","11 kg","12 kg Inverter","13 kg Lava e Seca","15 kg Inverter"}',1400,4800,
 'Lavadora com vários programas de lavagem, centrifugação eficiente e economia de água.'),
(1,'Eletrodomésticos','eletrodomesticos',5,'Aspiradores','aspiradores','Aspirador de Pó',
 '{"Portátil 600 W","Vertical 1000 W","Água e Pó 1400 W","Sem Fio 2 em 1","Robô Inteligente Wi-Fi"}',180,2400,
 'Aspirador com filtro lavável, alta potência de sucção e acessórios para vários tipos de piso.'),

(2,'TV e Vídeo','tv-e-video',1,'Smart TVs','smart-tvs','Smart TV',
 '{"32\" HD","43\" Full HD","50\" 4K UHD","55\" 4K UHD","65\" 4K QLED","75\" 4K QLED"}',1100,7900,
 'Smart TV com Wi-Fi, aplicativos de streaming, HDR e espelhamento de tela.'),
(2,'TV e Vídeo','tv-e-video',2,'Soundbars','soundbars','Soundbar',
 '{"2.0 80 W","2.1 160 W Bluetooth","3.1 300 W","5.1 450 W Dolby Atmos"}',350,3500,
 'Soundbar com conexão HDMI ARC, Bluetooth e modos de som para filmes e música.'),
(2,'TV e Vídeo','tv-e-video',3,'Projetores','projetores','Projetor',
 '{"Portátil 720p","Full HD 3500 Lúmens","Full HD Wi-Fi","4K Laser"}',600,9000,
 'Projetor com ajuste de foco, correção de trapézio e entradas HDMI e USB.'),
(2,'TV e Vídeo','tv-e-video',4,'Suportes de TV','suportes-de-tv','Suporte de TV',
 '{"Fixo 14\" a 42\"","Fixo 32\" a 75\"","Articulado 32\" a 55\"","Articulado 40\" a 85\""}',60,450,
 'Suporte de parede em aço com kit de instalação e nivelador incluso.'),
(2,'TV e Vídeo','tv-e-video',5,'TV Box','tv-box','Receptor de Streaming',
 '{"Full HD","4K HDR","4K Wi-Fi 6 com Controle por Voz"}',200,900,
 'Receptor de streaming que transforma qualquer TV com HDMI em smart TV.'),

(3,'Celulares','celulares',1,'Smartphones','smartphones','Smartphone',
 '{"64 GB 4G","128 GB 4G","128 GB 5G","256 GB 5G","512 GB 5G"}',800,7500,
 'Smartphone com tela de alta resolução, câmera múltipla e bateria para o dia todo.'),
(3,'Celulares','celulares',2,'Capas','capas','Capa para Celular',
 '{"Silicone","Transparente Antichoque","Couro Sintético","Carteira com Cartões"}',30,160,
 'Capa protetora com recortes precisos e bordas elevadas para proteger a tela e a câmera.'),
(3,'Celulares','celulares',3,'Carregadores','carregadores','Carregador',
 '{"Veicular Duplo","USB-C 20 W","Sem Fio 15 W","Turbo 33 W","Turbo 65 W GaN"}',40,260,
 'Carregador com proteção contra sobrecarga e superaquecimento.'),
(3,'Celulares','celulares',4,'Fones de ouvido','fones-de-ouvido','Fone de Ouvido',
 '{"Intra-auricular com Fio","Bluetooth Esportivo","TWS Bluetooth","Headphone Bluetooth","Cancelamento de Ruído"}',40,1800,
 'Fone com som equilibrado, microfone embutido e almofadas confortáveis.'),
(3,'Celulares','celulares',5,'Smartwatches','smartwatches','Smartwatch',
 '{"Fitness 1,4\"","Tela AMOLED 1,7\"","GPS e Oxímetro","Premium com eSIM"}',150,2900,
 'Relógio inteligente com monitor cardíaco, notificações e resistência à água.'),

(4,'Informática','informatica',1,'Notebooks','notebooks','Notebook',
 '{"Celeron 4 GB 128 GB","Core i3 8 GB 256 GB","Ryzen 5 8 GB 512 GB","Core i7 16 GB 512 GB","Gamer RTX 16 GB 1 TB"}',1700,9500,
 'Notebook com tela Full HD, SSD rápido e teclado ABNT2.'),
(4,'Informática','informatica',2,'Monitores','monitores','Monitor',
 '{"21,5\" Full HD","24\" Full HD IPS","27\" QHD","27\" Gamer 165 Hz","34\" Ultrawide"}',550,3800,
 'Monitor com bordas finas, ajuste de inclinação e entradas HDMI e DisplayPort.'),
(4,'Informática','informatica',3,'Teclados','teclados','Teclado',
 '{"USB ABNT2","Sem Fio ABNT2","Mecânico RGB","Mecânico Sem Fio 75%"}',50,750,
 'Teclado com layout ABNT2, teclas silenciosas e construção resistente.'),
(4,'Informática','informatica',4,'Mouses','mouses','Mouse',
 '{"Óptico USB","Sem Fio","Ergonômico Vertical","Gamer 16000 DPI"}',30,450,
 'Mouse com sensor preciso, pegada confortável e botões de alta durabilidade.'),
(4,'Informática','informatica',5,'Impressoras','impressoras','Impressora',
 '{"Jato de Tinta","Multifuncional Wi-Fi","Tanque de Tinta Wi-Fi","Laser Monocromática"}',350,2200,
 'Impressora com conexão USB e Wi-Fi e impressão pelo celular.'),

(5,'Games','games',1,'Consoles','consoles','Console',
 '{"Retrô 10 Mil Jogos","Portátil 64 GB","Next-Gen Digital 825 GB","Next-Gen 1 TB"}',350,4800,
 'Console com controle sem fio, saída HDMI e acesso a jogos digitais.'),
(5,'Games','games',2,'Controles','controles','Controle',
 '{"com Fio USB","Sem Fio Bluetooth","Pro com Vibração","Elite com Paddles"}',90,1300,
 'Controle ergonômico com gatilhos sensíveis e bateria recarregável.'),
(5,'Games','games',3,'Jogos','jogos','Jogo',
 '{"de Futebol Edição Padrão","de Corrida Edição Padrão","de Aventura Edição Padrão","de RPG Edição Deluxe","de Estratégia Edição Completa"}',60,350,
 'Jogo em mídia digital com legendas e dublagem em português.'),
(5,'Games','games',4,'Headsets','headsets','Headset Gamer',
 '{"P2 com Microfone","USB 7.1","Sem Fio 2,4 GHz","Sem Fio com ANC"}',90,1200,
 'Headset com som surround, microfone removível e almofadas de espuma.'),
(5,'Games','games',5,'Cadeiras gamer','cadeiras-gamer','Cadeira Gamer',
 '{"Reclinável Preta","Reclinável Vermelha","Ergonômica com Apoio Lombar","Pro Reclinável 180°"}',600,2500,
 'Cadeira com regulagem de altura, braços ajustáveis e almofadas de apoio.'),

(6,'Móveis','moveis',1,'Sofás','sofas','Sofá',
 '{"2 Lugares Linho","3 Lugares Suede","3 Lugares Retrátil","Canto 5 Lugares","Retrátil e Reclinável 4 Lugares"}',900,5500,
 'Sofá com estrutura de madeira, espuma de alta densidade e tecido de fácil limpeza.'),
(6,'Móveis','moveis',2,'Mesas','mesas','Mesa',
 '{"de Centro","de Escritório 120 cm","de Jantar 4 Lugares","de Jantar 6 Lugares"}',200,2600,
 'Mesa com tampo resistente a riscos e montagem simples.'),
(6,'Móveis','moveis',3,'Cadeiras','cadeiras','Cadeira',
 '{"de Plástico","de Jantar Estofada","de Escritório Giratória","Presidente Ergonômica"}',60,1400,
 'Cadeira com acabamento durável e assento confortável.'),
(6,'Móveis','moveis',4,'Guarda-roupas','guarda-roupas','Guarda-roupa',
 '{"2 Portas","4 Portas","6 Portas com Espelho","Casal 3 Portas de Correr"}',450,2900,
 'Guarda-roupa com cabideiro, gavetas com corrediças e prateleiras internas.'),
(6,'Móveis','moveis',5,'Estantes','estantes','Estante',
 '{"para Livros 4 Prateleiras","Rack para TV até 55\"","Home Theater até 65\"","Painel Modular"}',180,1800,
 'Móvel em MDP com acabamento texturizado e nichos organizadores.'),

(7,'Casa e Cozinha','casa-e-cozinha',1,'Panelas','panelas','Jogo de Panelas',
 '{"Alumínio 5 Peças","Antiaderente 5 Peças","Cerâmica 7 Peças","Inox Fundo Triplo 5 Peças"}',120,1200,
 'Jogo de panelas com tampas de vidro e cabos que não esquentam.'),
(7,'Casa e Cozinha','casa-e-cozinha',2,'Liquidificadores','liquidificadores','Liquidificador',
 '{"500 W 2 L","900 W 3 L","1200 W Copo de Vidro","Alta Potência 1400 W"}',110,750,
 'Liquidificador com lâminas de aço inox, várias velocidades e função pulsar.'),
(7,'Casa e Cozinha','casa-e-cozinha',3,'Cafeteiras','cafeteiras','Cafeteira',
 '{"Elétrica 15 Xícaras","de Cápsulas","Expresso 15 Bar","Superautomática"}',120,4200,
 'Cafeteira com placa de aquecimento, sistema corta-pingo e fácil limpeza.'),
(7,'Casa e Cozinha','casa-e-cozinha',4,'Air fryers','air-fryers','Fritadeira Air Fryer',
 '{"3,2 L","4 L Digital","5,5 L Digital","Forno Oven 12 L"}',280,1100,
 'Fritadeira sem óleo com cesto antiaderente, timer e controle de temperatura.'),
(7,'Casa e Cozinha','casa-e-cozinha',5,'Utensílios','utensilios','Kit de Utensílios',
 '{"de Silicone 5 Peças","de Bambu 12 Peças","de Facas Inox 6 Peças","de Potes Herméticos 10 Peças"}',40,300,
 'Kit de cozinha prático, resistente e fácil de guardar.'),

(8,'Esporte e Lazer','esporte-e-lazer',1,'Bicicletas','bicicletas','Bicicleta',
 '{"Infantil Aro 16","Urbana Aro 26","Mountain Bike Aro 29 21v","Speed Aro 700","Elétrica 350 W"}',500,7500,
 'Bicicleta com quadro leve, freios eficientes e selim confortável.'),
(8,'Esporte e Lazer','esporte-e-lazer',2,'Esteiras','esteiras','Esteira',
 '{"Dobrável 10 km/h","Elétrica 12 km/h","Elétrica 16 km/h com Inclinação","Profissional 18 km/h"}',1300,8500,
 'Esteira com painel de treino, amortecimento e chave de segurança.'),
(8,'Esporte e Lazer','esporte-e-lazer',3,'Halteres','halteres','Halter',
 '{"Emborrachado 2 kg (Par)","Emborrachado 5 kg (Par)","Kit Anilhas 20 kg","Ajustável até 24 kg"}',60,1500,
 'Equipamento para treino de força em casa ou na academia.'),
(8,'Esporte e Lazer','esporte-e-lazer',4,'Tênis de corrida','tenis-de-corrida','Tênis de Corrida',
 '{"Masculino","Feminino","Amortecimento Max","Placa de Carbono"}',180,1300,
 'Tênis leve com cabedal respirável e solado de alta tração.'),
(8,'Esporte e Lazer','esporte-e-lazer',5,'Barracas','barracas','Barraca de Camping',
 '{"2 Pessoas","4 Pessoas","6 Pessoas","Iglu Impermeável 8 Pessoas"}',150,1200,
 'Barraca com montagem rápida, sobreteto impermeável e bolsa de transporte.'),

(9,'Moda','moda',1,'Camisetas','camisetas','Camiseta',
 '{"Básica Algodão","Estampada","Dry Fit","Polo Piquet"}',40,200,
 'Camiseta com tecido macio, costura reforçada e caimento confortável.'),
(9,'Moda','moda',2,'Calças','calcas','Calça',
 '{"Moletom","Jeans Slim","Sarja Chino","Social Alfaiataria"}',80,350,
 'Calça com modelagem atual e tecido de boa durabilidade.'),
(9,'Moda','moda',3,'Tênis','tenis','Tênis',
 '{"Casual Lona","Skate","Casual Couro","Branco Couro Premium"}',120,700,
 'Tênis casual com palmilha acolchoada e solado de borracha.'),
(9,'Moda','moda',4,'Mochilas','mochilas','Mochila',
 '{"Escolar 20 L","Executiva para Notebook","Antifurto USB","Trilha 40 L"}',70,450,
 'Mochila com alças acolchoadas, vários compartimentos e tecido resistente.'),
(9,'Moda','moda',5,'Relógios','relogios','Relógio',
 '{"Digital Esportivo","Analógico Casual","Cronógrafo Aço","Automático Safira"}',90,2200,
 'Relógio com pulseira ajustável e resistência à água.'),

(10,'Beleza e Saúde','beleza-e-saude',1,'Perfumes','perfumes','Perfume',
 '{"Colônia 100 ml","Eau de Toilette 50 ml","Eau de Toilette 100 ml","Eau de Parfum 100 ml"}',70,700,
 'Fragrância marcante com boa fixação.'),
(10,'Beleza e Saúde','beleza-e-saude',2,'Secadores','secadores','Secador de Cabelo',
 '{"1200 W","2000 W Íons","2100 W Profissional","Escova Secadora Rotativa"}',90,700,
 'Secador com várias temperaturas, jato frio e bico concentrador.'),
(10,'Beleza e Saúde','beleza-e-saude',3,'Barbeadores','barbeadores','Barbeador',
 '{"Descartável (Kit 4)","Elétrico Seco","Elétrico à Prova d''Água","Aparador Multigroom 10 em 1"}',25,600,
 'Barbeador com lâminas precisas para um corte rente e confortável.'),
(10,'Beleza e Saúde','beleza-e-saude',4,'Maquiagem','maquiagem','Kit de Maquiagem',
 '{"Básico","Bases e Corretivos","Paleta de Sombras 18 Cores","Completo com Maleta"}',50,450,
 'Kit de maquiagem com cores versáteis e fórmula de longa duração.'),
(10,'Beleza e Saúde','beleza-e-saude',5,'Balanças','balancas','Balança',
 '{"de Cozinha Digital","Digital de Vidro","de Bioimpedância","Bluetooth com App"}',40,350,
 'Balança digital com visor de fácil leitura e desligamento automático.');

-- mapeamento: slug do seed (cat-N / cat-N-S) ou slug ja aplicado.
-- Raizes pela parte numerica do slug; filhas pela relacao REAL parent_id.
CREATE TEMP TABLE vitrine_map ON COMMIT DROP AS
WITH seed_r AS (
    SELECT id, row_number() OVER (ORDER BY substring(slug FROM 5)::int) AS dept
      FROM categories
     WHERE parent_id IS NULL AND slug ~ '^cat-[0-9]+$'
), r AS (
    SELECT c.id, coalesce(sr.dept, d.dept) AS dept
      FROM categories c
      LEFT JOIN seed_r sr ON sr.id = c.id
      LEFT JOIN (SELECT DISTINCT dept, dept_slug FROM vitrine_def) d ON d.dept_slug = c.slug
     WHERE c.parent_id IS NULL AND coalesce(sr.dept, d.dept) IS NOT NULL
), l AS (
    SELECT c.id, r.dept,
           coalesce(d.leaf, row_number() OVER (PARTITION BY c.parent_id ORDER BY c.slug COLLATE "C")) AS leaf
      FROM categories c
      JOIN r ON c.parent_id = r.id
      LEFT JOIN vitrine_def d ON d.dept = r.dept AND d.leaf_slug = c.slug
     WHERE c.slug ~ '^cat-[0-9]+-[0-9]+$' OR d.leaf IS NOT NULL
)
SELECT id, dept, NULL::bigint AS leaf FROM r
UNION ALL
SELECT id, dept, leaf FROM l;

ALTER TABLE products DISABLE TRIGGER trg_update_timestamp;

-- produtos: k = posicao do produto dentro da subcategoria (o seed distribui por n % 50).
-- Nome = tipo + marca + modelo + variacao: ordenado por nome (como a listagem),
-- a primeira pagina mostra uma marca com as variacoes se alternando.
WITH s AS (
    SELECT p.id, d.tipo, d.vars, d.pmin, d.pmax, d.descr,
           substring(p.sku FROM 5)::int / 50 AS k,
           cardinality(d.vars) AS nv
      FROM products p
      JOIN vitrine_map m ON m.id = p.category_id
      JOIN vitrine_def d ON d.dept = m.dept AND d.leaf = m.leaf
     WHERE p.sku ~ '^SKU-[0-9]+$'
), v AS (
    SELECT s.*, k % nv AS vi,
           (ARRAY['Nordivo','Kalvix','Brisano','Zentiq','Orvalle','Tekari',
                  'Valtrix','Quenza','Dorvik','Sallum','Ivoren','Marbeli'])[(k / nv) % 12 + 1] AS marca,
           (1000 + k)::text AS modelo   -- unico dentro da subcategoria
      FROM s
)
UPDATE products p
   SET name  = v.tipo || ' ' || v.marca || ' ' || upper(left(v.marca, 2)) || '-' || v.modelo || ' ' || v.vars[v.vi + 1],
       description = v.descr || ' Marca ' || v.marca || ', modelo ' || upper(left(v.marca, 2)) || '-' || v.modelo || '.',
       price = least(floor(v.pmin + (v.pmax - v.pmin) * (v.vi + ((v.k * 7919) % 100) / 100.0) / v.nv) + 0.90, v.pmax)
  FROM v
 WHERE p.id = v.id;

ALTER TABLE products ENABLE TRIGGER trg_update_timestamp;

-- imagens: 2 fotos por subcategoria; a posicao do produto na subcategoria (k) e a
-- posicao da imagem alternam qual aparece primeiro (o SKU nao serve: n % 50 e fixo)
UPDATE product_images i
   SET url = '/produtos/' || d.leaf_slug || '/' || ((substring(p.sku FROM 5)::int / 50 + i.position) % 2 + 1) || '.jpg'
  FROM products p
  JOIN vitrine_map m ON m.id = p.category_id
  JOIN vitrine_def d ON d.dept = m.dept AND d.leaf = m.leaf
 WHERE i.product_id = p.id AND p.sku ~ '^SKU-[0-9]+$';

-- categorias por ultimo (o mapeamento acima depende dos slugs antigos)
UPDATE categories c
   SET name = d.dept_name, slug = d.dept_slug
  FROM vitrine_map m
  JOIN (SELECT DISTINCT dept, dept_name, dept_slug FROM vitrine_def) d ON d.dept = m.dept
 WHERE c.id = m.id AND m.leaf IS NULL;

UPDATE categories c
   SET name = d.leaf_name, slug = d.leaf_slug
  FROM vitrine_map m
  JOIN vitrine_def d ON d.dept = m.dept AND d.leaf = m.leaf
 WHERE c.id = m.id;

COMMIT;
