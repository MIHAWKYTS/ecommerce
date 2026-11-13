-- =====================================================================
-- Plataforma de E-commerce de Alto Trafego | Banco de Dados II
-- 01_schema.sql : tabelas, chaves, restricoes (PostgreSQL 13+)
-- gen_random_uuid() e nativo a partir do PostgreSQL 13.
-- =====================================================================

BEGIN;

CREATE TABLE users (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name          VARCHAR(150) NOT NULL,
    email         VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    phone         VARCHAR(20),
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE addresses (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id    UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    street     VARCHAR(200) NOT NULL,
    number     VARCHAR(20)  NOT NULL,
    complement VARCHAR(100),
    city       VARCHAR(100) NOT NULL,
    state      CHAR(2)      NOT NULL,
    zip_code   VARCHAR(10)  NOT NULL,
    is_default BOOLEAN      NOT NULL DEFAULT FALSE
);

CREATE TABLE categories (
    id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    parent_id UUID REFERENCES categories(id) ON DELETE SET NULL,  -- auto-relacionamento
    name      VARCHAR(100) NOT NULL,
    slug      VARCHAR(120) NOT NULL UNIQUE,
    CONSTRAINT ck_categories_not_self_parent CHECK (parent_id IS DISTINCT FROM id)
);

CREATE TABLE products (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    category_id UUID NOT NULL REFERENCES categories(id),
    sku         VARCHAR(50)  NOT NULL UNIQUE,
    name        VARCHAR(200) NOT NULL,
    description TEXT,
    price       NUMERIC(10,2) NOT NULL CHECK (price >= 0),
    active      BOOLEAN NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE product_images (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    url        VARCHAR(500) NOT NULL,
    position   INT NOT NULL DEFAULT 0
);

CREATE TABLE inventory (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id        UUID NOT NULL UNIQUE REFERENCES products(id) ON DELETE CASCADE,  -- 1:1
    quantity          INT NOT NULL DEFAULT 0 CHECK (quantity >= 0),
    reserved_quantity INT NOT NULL DEFAULT 0 CHECK (reserved_quantity >= 0),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE orders (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id      UUID NOT NULL REFERENCES users(id),
    address_id   UUID NOT NULL REFERENCES addresses(id),
    status       VARCHAR(20) NOT NULL DEFAULT 'pending'
                 CHECK (status IN ('pending','paid','cancelled')),
    total_amount NUMERIC(10,2) NOT NULL DEFAULT 0 CHECK (total_amount >= 0),
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE order_items (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id   UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    product_id UUID NOT NULL REFERENCES products(id),
    quantity   INT NOT NULL CHECK (quantity > 0),
    unit_price NUMERIC(10,2) NOT NULL CHECK (unit_price >= 0),  -- preco congelado na compra
    subtotal   NUMERIC(10,2) GENERATED ALWAYS AS (quantity * unit_price) STORED,
    CONSTRAINT uq_order_items_order_product UNIQUE (order_id, product_id)
);

CREATE TABLE payments (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id       UUID NOT NULL UNIQUE REFERENCES orders(id),  -- 1:1
    method         VARCHAR(30) NOT NULL,
    status         VARCHAR(20) NOT NULL DEFAULT 'pending'
                   CHECK (status IN ('pending','approved','failed')),
    amount         NUMERIC(10,2) NOT NULL CHECK (amount >= 0),
    transaction_id VARCHAR(100),
    paid_at        TIMESTAMPTZ
);

COMMIT;
