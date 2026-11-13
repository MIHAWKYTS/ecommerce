# Plataforma de E-commerce de Alto Tráfego (BD II)

Projeto da disciplina Banco de Dados II (UFAL). Persistência poliglota: PostgreSQL 16 guarda os dados transacionais e o Redis 7 guarda sessão, carrinho e cache. A API é FastAPI e o frontend é Next.js 15 com Tailwind CSS.

## Como rodar

Requisito: Docker com o plugin `docker compose`.

    SEED=1 docker compose up --build       # recomendado: catálogo de demonstração com 100 mil produtos
    docker compose up --build              # banco vazio (sem produtos)

No Windows (PowerShell), defina a variável antes:

    $env:SEED="1"; docker compose up --build

No Prompt de Comando (cmd): `set SEED=1` e depois `docker compose up --build`.

- Loja: http://localhost:3000
- API (documentação interativa): http://localhost:8000/docs

Com `SEED=1`, a primeira subida leva cerca de 30 s depois que as imagens estão construídas: o backend carrega o seed (`04_seed.sql`, cerca de 15 s), aplica o catálogo de demonstração (`05_vitrine.sql`, cerca de 5 s) e limpa o cache do Redis. Nas subidas seguintes essas etapas são puladas e o backend fica pronto em cerca de 3 s. (Medido numa máquina de 12 CPUs com Docker Desktop; o primeiro `--build` leva mais tempo.)

Para testar a loja, **crie uma conta nova** na tela "Entrar" (aba "Criar conta"). Os usuários do seed têm senha fictícia e não fazem login.

Comandos úteis:

    docker compose down                    # para tudo e mantém o banco
    docker compose down -v                 # para tudo e APAGA o banco (volta ao zero)
    docker compose restart redis           # limpa sessões, carrinhos e cache (Redis sem persistência)
    docker compose logs -f backend         # acompanha o log da API

### Testes e medições

Os testes de integração e o benchmark rodam dentro de um container do backend, contra o PostgreSQL e o Redis do compose (que não expõem portas para fora):

    docker compose run --rm --no-deps -v "$PWD/backend:/app" --entrypoint "" backend python -m pytest -q
    docker compose run --rm --no-deps -v "$PWD/backend:/app" --entrypoint "" backend python bench_indices.py 200
    docker compose run --rm --no-deps -v "$PWD/backend:/app" --entrypoint "" backend python bench_categoria.py 300
    docker compose run --rm --no-deps -v "$PWD/backend:/app" --entrypoint "" backend python bench_vazao.py 10

Os testes exigem o banco com seed. O `bench_indices.py` faz a análise com e sem indexação: mede 7 consultas da aplicação (mediana e p95, em ms) com os 8 índices do projeto e sem eles, e mostra o plano escolhido pelo PostgreSQL (Seq Scan ou Index Scan). Os índices são removidos com `DROP INDEX` dentro de uma transação que termina em `ROLLBACK`, então voltam sozinhos; durante a medição (cerca de 15 s) a API fica bloqueada nessas tabelas, então não rode durante a demonstração. O `bench_categoria.py` mede a listagem por categoria com e sem cache, dentro do processo (medianas e p95, em ms). O `bench_vazao.py` mede a vazão da API pela HTTP (req/s e latência p50, p95 e p99) em 7 rotas, com 1 e 32 requisições simultâneas, mais uma curva de saturação; leva cerca de 4 minutos com 10 s por cenário. Ele cria um usuário de teste por execução e, fora isso, só lê e escreve no carrinho, sem criar pedidos nem mexer no estoque, e precisa que o backend esteja no ar (`docker compose up`). Na máquina de desenvolvimento a API saturou em cerca de 1.200 req/s.

### Edição do catálogo (administrador)

`PATCH /products/{id}` exige sessão de um usuário cujo e-mail esteja em `ADMIN_EMAILS` (vários separados por vírgula). Sem a variável, a rota responde 403 para todos.

    ADMIN_EMAILS=admin@loja.com SEED=1 docker compose up --build

Depois crie a conta `admin@loja.com` na tela "Entrar" (ou por `POST /auth/register`) e envie o `session_id` no cabeçalho:

    curl -X PATCH http://localhost:8000/products/<id> -H "Authorization: Bearer <session_id>" \
         -H "Content-Type: application/json" -d '{"price": "199.90"}'

### Desenvolvimento sem Docker

Suba um PostgreSQL 16 e um Redis 7 e defina `DATABASE_URL` (ex.: `postgresql+psycopg2://ecommerce:ecommerce@localhost:5432/ecommerce`) e `REDIS_URL` (ex.: `redis://localhost:6379/0`).

    cd backend && pip install -r requirements.txt && alembic upgrade head && uvicorn app.main:app --reload
    cd frontend && npm install && npm run dev     # NEXT_PUBLIC_API_URL, padrão http://localhost:8000

Para povoar sem Docker, rode `04_seed.sql` e depois `05_vitrine.sql` com o `psql`.

## Novidades

- **Frontend redesenhado**: visual de loja com Tailwind CSS, cabeçalho com busca de categorias e contador do carrinho, layout responsivo (celular e computador), estados de carregamento e erro, confirmação de compra e página de detalhe do pedido. A sessão expirada leva ao login e volta à página em que o usuário estava.
- **Catálogo realista**: departamentos e subcategorias reais (ex.: Eletrodomésticos › Geladeiras, TV e Vídeo › Smart TVs), produtos com nome, descrição e preço coerentes, marcas fictícias e 100 fotos reais servidas pelo próprio frontend (a loja funciona sem internet). Aplicado por `05_vitrine.sql`, sem alterar os scripts 01 a 04 nem a quantidade de linhas.
- **Paginação**: "Carregar mais" na categoria. A API aceita `?page=N`; as 10 primeiras páginas saem da mesma chave LIST do Redis (`LRANGE`), sem chave nova.
- **Estoque na página do produto**: "Em estoque" ou "Esgotado", lido sempre no PostgreSQL (o estoque nunca entra no cache).
- **Detalhe do pedido**: `GET /orders/{id}` usa a view `vw_order_summary` e mostra os itens com o preço congelado da compra.
- **Índice da listagem**: `products(category_id, name) WHERE active` (`06_indice_listagem.sql`, migração Alembic 0002). A consulta da categoria caiu de cerca de 4,5 ms para 0,9 ms no cache miss.

## Estrutura

- `backend/sql/`: scripts do PostgreSQL, fonte da verdade do DDL.
  - `01_schema.sql` (9 tabelas), `02_logic.sql` (triggers, view `vw_order_summary`, procedure `sp_checkout`), `03_indexes.sql` (7 índices da análise com e sem indexação): aplicados pela migração Alembic 0001.
  - `04_seed.sql`: 100 mil produtos, 20 mil usuários e 100 mil pedidos.
  - `05_vitrine.sql`: catálogo de demonstração sobre o seed (só `UPDATE`, reaplicável).
  - `06_indice_listagem.sql`: índice da listagem por categoria, aplicado pela migração Alembic 0002.
- `backend/app/`: FastAPI. Rotas em `main.py`, regras de negócio em `services.py`, rotinas Redis em `redis_routines.py`, modelos SQLAlchemy em `models.py`.
- `backend/tests/test_api.py`: 13 testes de integração (edição de produto com invalidação do cache, autenticação, cache, carrinho, checkout, estoque insuficiente, compra concorrente da última unidade, paginação, estoque sem cache, detalhe do pedido, listagem com hits e misses misturados, carregamento em lote).
- `backend/bench_indices.py`: análise comparativa com e sem os índices (7 consultas, planos do PostgreSQL).
- `backend/bench_categoria.py`: benchmark da listagem por categoria (consulta e cache, dentro do processo).
- `backend/bench_vazao.py`: vazão e latência da API pela HTTP, por rota e por concorrência.
- `frontend/`: Next.js (App Router). Páginas em `app/`, componentes em `components/`, cliente da API e utilitários em `lib/`, fotos dos produtos em `public/produtos/` (créditos e licenças em `public/produtos/CREDITOS.md`).

## API

| Rota | Descrição |
|---|---|
| `GET /health` | Verifica PostgreSQL e Redis |
| `POST /auth/register`, `POST /auth/login` | Devolvem `{session_id, user}` |
| `POST /auth/logout`, `GET /auth/me` | Exigem `Authorization: Bearer <session_id>` |
| `GET /categories` | Lista plana com `parent_id` |
| `GET /categories/{id}/products?page=N` | 20 produtos por página, ordem por nome (cache-aside) |
| `GET /products/{id}` | Dados de catálogo (cache-aside, sem estoque) |
| `PATCH /products/{id}` | Edita nome, descrição, preço, ativo ou categoria (só administrador) e invalida o cache |
| `GET /products/{id}/stock` | Estoque disponível, sempre do PostgreSQL |
| `GET /addresses`, `POST /addresses` | Endereços do usuário |
| `GET /cart`, `PUT /cart/items/{id}`, `DELETE /cart` | Carrinho no Redis; o `PUT` define a quantidade total (0 remove) |
| `POST /checkout` | `{address_id, method}`, com `method` em `pix`, `credit_card` ou `boleto` |
| `GET /orders`, `GET /orders/{id}` | Histórico e detalhe dos pedidos do usuário |

## Redis

| Chave | Tipo | TTL |
|---|---|---|
| `session:{session_id}` | STRING (JSON) | 30 min, renovado a cada requisição |
| `cart:{user_id}` | HASH | 7 dias |
| `cache:product:{product_id}` | STRING (JSON) | 5 min |
| `cache:category:{category_id}:products` | LIST (até 200 ids, em ordem) | 5 min |

## Regras de consistência

- O checkout lê o carrinho no Redis, cria o pedido e os itens e chama `sp_checkout` na mesma transação. O carrinho só é limpo depois do COMMIT. Estoque insuficiente vira HTTP 409 e o carrinho é preservado.
- O estoque nunca entra no cache. Ele é validado no banco pelo trigger `trg_check_stock` e pela procedure, que trava as linhas com `FOR UPDATE` em ordem fixa.
- O preço do pedido vem do PostgreSQL no momento do checkout, não do cache nem do carrinho.
- Edição de produto (invalidate-on-write): o `PATCH` grava no PostgreSQL, faz COMMIT e só então apaga `cache:product:{id}`; se mudar nome, ativo ou categoria, apaga também a LIST da categoria antiga e da nova. A leitura seguinte é um miss e recarrega do banco. Ainda existe uma janela pequena (um leitor que leu o valor antigo antes do COMMIT pode regravá-lo depois da invalidação), limitada pelo TTL de 5 min.

## Limitações (projeto acadêmico)

- O pagamento é simulado: todo pedido nasce pago.
- Sem busca de produtos por texto (só de categorias), sem painel administrativo no frontend (a edição de produto existe só pela API) e sem rotas de criação de produto ou de ajuste de estoque.
- Sem HTTPS, rate limit ou refresh de sessão além do TTL deslizante.
- A ordenação dos produtos é alfabética por nome.
- A coluna `reserved_quantity` existe, mas não é usada.
- As fotos são da Wikimedia Commons sob licenças livres (CC0, domínio público, CC BY e CC BY-SA), com créditos em `frontend/public/produtos/CREDITOS.md`. As marcas e os modelos da loja são fictícios.
