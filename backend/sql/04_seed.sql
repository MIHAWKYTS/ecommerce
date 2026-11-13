-- =====================================================================
-- 04_seed.sql : povoamento automatizado (PostgreSQL), 100% SQL.
-- Volume: 100.000 produtos (entidade principal) e 100.000 pedidos.
-- Reprodutivel: setseed fixo. Rodar APOS 01, 02 e (opcionalmente) 03.
-- As triggers sao desativadas so durante a carga e reativadas no fim.
-- Os pedidos historicos NAO debitam o estoque: inventory representa o
-- estoque ATUAL. password_hash e um valor ficticio (nao e hash real).
-- =====================================================================
\timing on
SELECT setseed(0.42);

BEGIN;
ALTER TABLE order_items DISABLE TRIGGER trg_check_stock;
ALTER TABLE orders      DISABLE TRIGGER trg_update_timestamp;
ALTER TABLE products    DISABLE TRIGGER trg_update_timestamp;

-- ---- categorias: 10 raizes + 5 filhas cada (60) ----------------------
INSERT INTO categories (name, slug)
SELECT 'Categoria ' || n, 'cat-' || n FROM generate_series(1,10) n;

INSERT INTO categories (parent_id, name, slug)
SELECT c.id, 'Subcategoria ' || r.n || '.' || s, 'cat-' || r.n || '-' || s
  FROM (SELECT id, row_number() OVER (ORDER BY slug) AS n
          FROM categories WHERE parent_id IS NULL) r
  JOIN categories c ON c.id = r.id
 CROSS JOIN generate_series(1,5) s;

-- ---- usuarios (20.000) + enderecos ------------------------------------
INSERT INTO users (name, email, password_hash, phone, created_at)
SELECT 'Usuario ' || n,
       'usuario' || n || '@exemplo.com',
       'seed-nao-e-hash-real',
       '82' || lpad((900000000 + n)::text, 9, '0'),
       now() - (random() * interval '730 days')
  FROM generate_series(1,20000) n;

CREATE TEMP TABLE t_users ON COMMIT DROP AS
SELECT row_number() OVER (ORDER BY email) AS n, id FROM users;
CREATE INDEX ON t_users(n);

INSERT INTO addresses (user_id, street, number, city, state, zip_code, is_default)
SELECT id, 'Rua ' || n, (n % 999 + 1)::text, 'Penedo', 'AL', '57200-000', TRUE FROM t_users;

INSERT INTO addresses (user_id, street, number, complement, city, state, zip_code, is_default)
SELECT id, 'Avenida ' || n, (n % 500 + 1)::text, 'Apto ' || (n % 50 + 1), 'Arapiraca', 'AL', '57300-000', FALSE
  FROM t_users WHERE n % 2 = 0;

-- ---- produtos (100.000) + estoque + imagens ---------------------------
INSERT INTO products (category_id, sku, name, description, price, active, created_at)
SELECT leaf.id,
       'SKU-' || lpad(n::text, 7, '0'),
       'Produto ' || n,
       'Descricao do produto ' || n,
       round((10 + random() * 990)::numeric, 2),
       random() < 0.95,
       now() - (random() * interval '365 days')
  FROM generate_series(1,100000) n
  JOIN LATERAL (SELECT id FROM categories WHERE parent_id IS NOT NULL
                 ORDER BY slug OFFSET (n % 50) LIMIT 1) leaf ON TRUE;

CREATE TEMP TABLE t_products ON COMMIT DROP AS
SELECT row_number() OVER (ORDER BY sku) AS n, id, price FROM products;
CREATE INDEX ON t_products(n);

INSERT INTO inventory (product_id, quantity, reserved_quantity)
SELECT id, CASE WHEN random() < 0.05 THEN 0 ELSE (random() * 500)::int END, 0
  FROM t_products;

INSERT INTO product_images (product_id, url, position)
SELECT p.id, 'https://cdn.exemplo.com/produtos/' || p.n || '/' || pos || '.jpg', pos
  FROM t_products p CROSS JOIN generate_series(0,1) pos;

-- ---- pedidos (100.000) -------------------------------------------------
CREATE TEMP TABLE t_def_addr ON COMMIT DROP AS
SELECT DISTINCT ON (user_id) user_id, id AS address_id
  FROM addresses WHERE is_default ORDER BY user_id;
CREATE INDEX ON t_def_addr(user_id);

INSERT INTO orders (id, user_id, address_id, status, created_at)
SELECT gen_random_uuid(), u.id, a.address_id,
       CASE WHEN r < 0.85 THEN 'paid' WHEN r < 0.95 THEN 'pending' ELSE 'cancelled' END,
       now() - (random() * interval '365 days')
  FROM (SELECT n, random() AS r, 1 + floor(random() * 20000)::int AS un
          FROM generate_series(1,100000) n) g
  JOIN t_users u    ON u.n = g.un
  JOIN t_def_addr a ON a.user_id = u.id;

CREATE TEMP TABLE t_orders ON COMMIT DROP AS
SELECT row_number() OVER (ORDER BY id) AS n, id, status, created_at FROM orders;
CREATE INDEX ON t_orders(n);

-- 1 a 4 itens por pedido; produtos distintos por construcao (919 e primo com 100000)
INSERT INTO order_items (order_id, product_id, quantity, unit_price)
SELECT o.id, p.id, 1 + (random() * 2)::int, p.price
  FROM t_orders o
  JOIN LATERAL generate_series(1, 1 + (o.n % 4)::int) k ON TRUE
  JOIN t_products p ON p.n = ((o.n * 7919 + k * 919) % 100000) + 1;

UPDATE orders o SET total_amount = s.total
  FROM (SELECT order_id, SUM(subtotal) AS total FROM order_items GROUP BY order_id) s
 WHERE s.order_id = o.id;

-- ---- pagamentos: aprovado p/ pagos; falho p/ metade dos cancelados ----
INSERT INTO payments (order_id, method, status, amount, transaction_id, paid_at)
SELECT o.id,
       (ARRAY['pix','cartao_credito','boleto'])[1 + (o.n % 3)::int],
       CASE WHEN o.status = 'paid' THEN 'approved' ELSE 'failed' END,
       ord.total_amount,
       'TX-' || substr(md5(o.id::text), 1, 16),
       CASE WHEN o.status = 'paid' THEN o.created_at + interval '30 seconds' END
  FROM t_orders o
  JOIN orders ord ON ord.id = o.id
 WHERE o.status = 'paid' OR (o.status = 'cancelled' AND o.n % 2 = 0);

ALTER TABLE order_items ENABLE TRIGGER trg_check_stock;
ALTER TABLE orders      ENABLE TRIGGER trg_update_timestamp;
ALTER TABLE products    ENABLE TRIGGER trg_update_timestamp;
COMMIT;

ANALYZE;

SELECT 'users' AS tabela, count(*) FROM users UNION ALL
SELECT 'addresses', count(*) FROM addresses UNION ALL
SELECT 'categories', count(*) FROM categories UNION ALL
SELECT 'products', count(*) FROM products UNION ALL
SELECT 'product_images', count(*) FROM product_images UNION ALL
SELECT 'inventory', count(*) FROM inventory UNION ALL
SELECT 'orders', count(*) FROM orders UNION ALL
SELECT 'order_items', count(*) FROM order_items UNION ALL
SELECT 'payments', count(*) FROM payments;
