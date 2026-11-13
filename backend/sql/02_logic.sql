-- =====================================================================
-- 02_logic.sql : triggers, view e stored procedure (regras de negocio)
-- =====================================================================

-- ---------- trg_update_timestamp ------------------------------------
CREATE OR REPLACE FUNCTION fn_update_timestamp() RETURNS trigger AS $$
BEGIN
    NEW.updated_at := now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_update_timestamp BEFORE UPDATE ON products
    FOR EACH ROW EXECUTE FUNCTION fn_update_timestamp();
CREATE TRIGGER trg_update_timestamp BEFORE UPDATE ON orders
    FOR EACH ROW EXECUTE FUNCTION fn_update_timestamp();
CREATE TRIGGER trg_update_timestamp BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION fn_update_timestamp();
CREATE TRIGGER trg_update_timestamp BEFORE UPDATE ON inventory
    FOR EACH ROW EXECUTE FUNCTION fn_update_timestamp();

-- ---------- trg_check_stock -----------------------------------------
-- Dispara antes de inserir em order_items e impede venda de estoque inexistente.
CREATE OR REPLACE FUNCTION fn_check_stock() RETURNS trigger AS $$
DECLARE
    v_available INT;
BEGIN
    SELECT quantity INTO v_available
      FROM inventory
     WHERE product_id = NEW.product_id;

    IF v_available IS NULL THEN
        RAISE EXCEPTION 'Produto % sem registro de estoque', NEW.product_id
            USING ERRCODE = 'EST01';
    END IF;

    IF v_available < NEW.quantity THEN
        RAISE EXCEPTION 'Estoque insuficiente para o produto % (disponivel: %, pedido: %)',
            NEW.product_id, v_available, NEW.quantity
            USING ERRCODE = 'EST01';
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_check_stock BEFORE INSERT ON order_items
    FOR EACH ROW EXECUTE FUNCTION fn_check_stock();

-- ---------- vw_order_summary ----------------------------------------
CREATE OR REPLACE VIEW vw_order_summary AS
SELECT o.id            AS order_id,
       o.created_at,
       o.status        AS order_status,
       u.id            AS user_id,
       u.name          AS user_name,
       u.email         AS user_email,
       COUNT(oi.id)                          AS distinct_items,
       COALESCE(SUM(oi.quantity), 0)         AS total_units,
       COALESCE(SUM(oi.subtotal), 0)         AS items_total,
       o.total_amount,
       p.method        AS payment_method,
       p.status        AS payment_status
  FROM orders o
  JOIN users u            ON u.id = o.user_id
  LEFT JOIN order_items oi ON oi.order_id = o.id
  LEFT JOIN payments p     ON p.order_id = o.id
 GROUP BY o.id, u.id, p.method, p.status;

-- ---------- sp_checkout ---------------------------------------------
-- Pre-condicao: o pedido (status 'pending') e seus itens ja foram inseridos
-- na MESMA transacao. A procedure trava o pedido e o estoque, revalida,
-- debita o estoque, registra o pagamento e confirma o pedido. Qualquer
-- erro desfaz tudo (tudo ou nada).
CREATE OR REPLACE PROCEDURE sp_checkout(
    IN    p_order_id       UUID,
    IN    p_method         VARCHAR,
    IN    p_transaction_id VARCHAR DEFAULT NULL,
    INOUT p_payment_id     UUID    DEFAULT NULL
)
LANGUAGE plpgsql AS $$
DECLARE
    v_status VARCHAR;
    v_total  NUMERIC(10,2);
    v_short  RECORD;
BEGIN
    -- 1) trava o pedido
    SELECT status INTO v_status FROM orders WHERE id = p_order_id FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Pedido % nao encontrado', p_order_id USING ERRCODE = 'EST02';
    END IF;
    IF v_status <> 'pending' THEN
        RAISE EXCEPTION 'Pedido % nao esta pendente (status: %)', p_order_id, v_status
            USING ERRCODE = 'EST02';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM order_items WHERE order_id = p_order_id) THEN
        RAISE EXCEPTION 'Pedido % nao possui itens', p_order_id USING ERRCODE = 'EST02';
    END IF;

    -- 2) trava o estoque em ordem fixa (evita deadlock entre pedidos concorrentes)
    PERFORM 1
       FROM inventory i
       JOIN order_items oi ON oi.product_id = i.product_id
      WHERE oi.order_id = p_order_id
      ORDER BY i.product_id
        FOR UPDATE OF i;

    -- 3) revalida o estoque ja com as linhas travadas
    SELECT oi.product_id, oi.quantity AS wanted, i.quantity AS available
      INTO v_short
      FROM order_items oi
      JOIN inventory i ON i.product_id = oi.product_id
     WHERE oi.order_id = p_order_id
       AND i.quantity < oi.quantity
     LIMIT 1;
    IF FOUND THEN
        RAISE EXCEPTION 'Estoque insuficiente para o produto % (disponivel: %, pedido: %)',
            v_short.product_id, v_short.available, v_short.wanted
            USING ERRCODE = 'EST01';
    END IF;

    -- 4) debita o estoque
    UPDATE inventory i
       SET quantity = i.quantity - oi.quantity
      FROM order_items oi
     WHERE oi.order_id = p_order_id
       AND oi.product_id = i.product_id;

    -- 5) recalcula o total a partir dos itens (precos congelados em order_items)
    SELECT SUM(subtotal) INTO v_total FROM order_items WHERE order_id = p_order_id;

    -- 6) registra o pagamento
    INSERT INTO payments (order_id, method, status, amount, transaction_id, paid_at)
    VALUES (p_order_id, p_method, 'approved', v_total, p_transaction_id, now())
    RETURNING id INTO p_payment_id;

    -- 7) confirma o pedido
    UPDATE orders SET status = 'paid', total_amount = v_total WHERE id = p_order_id;
END;
$$;
