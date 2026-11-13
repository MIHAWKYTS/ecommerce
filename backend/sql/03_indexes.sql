-- =====================================================================
-- 03_indexes.sql : indices de desempenho (separados para a analise
-- comparativa "com e sem indexacao" exigida pela disciplina)
-- Ja existem indices implicitos em PKs e colunas UNIQUE (email, sku, slug,
-- inventory.product_id, payments.order_id, order_items(order_id, product_id)).
-- =====================================================================
CREATE INDEX idx_addresses_user        ON addresses(user_id);
CREATE INDEX idx_categories_parent     ON categories(parent_id);
CREATE INDEX idx_products_category     ON products(category_id) WHERE active;
CREATE INDEX idx_product_images_prod   ON product_images(product_id, position);
CREATE INDEX idx_orders_user_created   ON orders(user_id, created_at DESC);
CREATE INDEX idx_orders_status         ON orders(status);
CREATE INDEX idx_order_items_product   ON order_items(product_id);
