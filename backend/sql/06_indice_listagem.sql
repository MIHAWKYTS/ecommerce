-- =====================================================================
-- 06_indice_listagem.sql : indice da listagem paginada por categoria.
-- Separado do 03_indexes.sql para nao alterar a analise "com e sem os 7
-- indices". Atende a consulta do loader de cache miss da categoria:
--   SELECT id FROM products WHERE category_id = $1 AND active
--    ORDER BY name LIMIT 200 [OFFSET n]
-- Com (category_id, name) parcial em active, o PostgreSQL le as linhas ja
-- na ordem de name e para no LIMIT, sem ordenar a categoria inteira.
-- =====================================================================
CREATE INDEX IF NOT EXISTS idx_products_category_name ON products(category_id, name) WHERE active;
