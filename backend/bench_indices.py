import os
import random
import re
import statistics
import sys
import time

import psycopg2

N = int(next((a for a in sys.argv[1:] if a.isdigit()), 200))
EXPLAIN = "--explain" in sys.argv
WARMUP = 20

INDICES = ["idx_addresses_user", "idx_categories_parent", "idx_products_category",
           "idx_products_category_name", "idx_product_images_prod", "idx_orders_user_created",
           "idx_orders_status", "idx_order_items_product"]

CONSULTAS = [
    ("Q1 Endereços do usuário (checkout)", "idx_addresses_user",
     "SELECT id, street, city FROM addresses WHERE user_id = %s", "users"),
    ("Q2 Listagem da categoria (cache miss)", "idx_products_category_name",
     "SELECT id FROM products WHERE category_id = %s AND active ORDER BY name LIMIT 200", "leaves"),
    ("Q3 Histórico de pedidos do usuário", "idx_orders_user_created",
     "SELECT id, status, total_amount, created_at FROM orders WHERE user_id = %s "
     "ORDER BY created_at DESC LIMIT 20", "users"),
    ("Q4 Contagem de pedidos por status", "idx_orders_status",
     "SELECT count(*) FROM orders WHERE status = %s", "status"),
    ("Q5 Vendas de um produto", "idx_order_items_product",
     "SELECT count(*), coalesce(sum(quantity), 0) FROM order_items WHERE product_id = %s", "products"),
    ("Q6 Imagens do produto (cache miss)", "idx_product_images_prod",
     "SELECT url FROM product_images WHERE product_id = %s ORDER BY position", "products"),
    ("Q7 Subcategorias de um departamento", "idx_categories_parent",
     "SELECT id, name FROM categories WHERE parent_id = %s", "roots"),
]


def dsn() -> str:
    url = os.environ.get("DATABASE_URL",
                         "postgresql+psycopg2://ecommerce:ecommerce@localhost:5432/ecommerce")
    return url.replace("postgresql+psycopg2://", "postgresql://")


def pools(cur) -> dict:
    def col(sql):
        cur.execute(sql)
        return [r[0] for r in cur.fetchall()]
    p = {
        "users": col("SELECT user_id FROM orders GROUP BY user_id ORDER BY random() LIMIT 500"),
        "leaves": col("SELECT id FROM categories WHERE parent_id IS NOT NULL"),
        "roots": col("SELECT id FROM categories WHERE parent_id IS NULL"),
        "products": col("SELECT product_id FROM order_items GROUP BY product_id ORDER BY random() LIMIT 500"),
        "status": ["pending", "cancelled"],
    }
    if not p["users"] or not p["products"] or not p["leaves"]:
        sys.exit("Banco sem dados: rode com SEED=1 (ou povoar.py) antes do benchmark.")
    return p


def scan(cur, sql, param) -> tuple[str, str]:
    cur.execute("EXPLAIN " + sql, (param,))
    plano = "\n".join(r[0] for r in cur.fetchall())
    nos = re.findall(r"((?:Parallel )?(?:Seq|Index Only|Index|Bitmap Heap|Bitmap Index) Scan"
                     r"(?: using \w+)?(?: on \w+)?)", plano)
    vistos = list(dict.fromkeys(n.replace(" on ", " em ") for n in nos))
    return ", ".join(vistos) or plano.splitlines()[0], plano


def medir(cur, sql, params) -> list[float]:
    for p in params[:WARMUP]:
        cur.execute(sql, (p,))
        cur.fetchall()
    xs = []
    for p in params:
        t = time.perf_counter()
        cur.execute(sql, (p,))
        cur.fetchall()
        xs.append((time.perf_counter() - t) * 1000)
    return xs


def resumo(xs) -> tuple[float, float]:
    xs = sorted(xs)
    return statistics.median(xs), xs[max(0, int(len(xs) * 0.95) - 1)]


def cenario(cur, sorteios) -> dict:
    out = {}
    for rotulo, _, sql, _ in CONSULTAS:
        plano_resumo, plano = scan(cur, sql, sorteios[rotulo][0])
        out[rotulo] = (*resumo(medir(cur, sql, sorteios[rotulo])), plano_resumo, plano)
    return out


def main():
    conn = psycopg2.connect(dsn())
    conn.autocommit = False
    cur = conn.cursor()

    cur.execute("SELECT indexname FROM pg_indexes WHERE schemaname = 'public' AND indexname = ANY(%s)",
                (INDICES,))
    faltando = set(INDICES) - {r[0] for r in cur.fetchall()}
    if faltando:
        sys.exit(f"Índices ausentes: {', '.join(sorted(faltando))}. Rode 'alembic upgrade head'.")

    cur.execute("SELECT count(*) FROM products")
    total = cur.fetchone()[0]
    rnd = random.Random(42)
    p = pools(cur)
    sorteios = {rot: [rnd.choice(p[pool]) for _ in range(N)] for rot, _, _, pool in CONSULTAS}
    conn.commit()

    total_br = f"{total:,}".replace(",", ".")
    print(f"N = {N} execuções por consulta e cenário (+{WARMUP} de aquecimento), {total_br} produtos no banco\n")

    com = cenario(cur, sorteios)
    conn.commit()

    try:
        for i in INDICES:
            cur.execute(f"DROP INDEX {i}")
        sem = cenario(cur, sorteios)
    finally:
        conn.rollback()

    cur.execute("SELECT count(*) FROM pg_indexes WHERE schemaname = 'public' AND indexname = ANY(%s)",
                (INDICES,))
    restaurados = cur.fetchone()[0]
    conn.close()

    larg = max(len(c[0]) for c in CONSULTAS)
    print(f"{'Consulta':<{larg}}  {'sem índice (med / p95)':>24}  {'com índice (med / p95)':>24}  {'ganho':>7}")
    print("-" * (larg + 62))
    for rotulo, *_ in CONSULTAS:
        sm, sp = sem[rotulo][:2]
        cm, cp = com[rotulo][:2]
        print(f"{rotulo:<{larg}}  {sm:9.3f} / {sp:8.3f} ms  {cm:9.3f} / {cp:8.3f} ms  {sm / cm:6.1f}x")

    print("\nPlano escolhido pelo PostgreSQL")
    for rotulo, indice, *_ in CONSULTAS:
        print(f"{rotulo} (índice: {indice})")
        print(f"   sem: {sem[rotulo][2]}")
        print(f"   com: {com[rotulo][2]}")
        if EXPLAIN:
            for nome, res in (("SEM", sem), ("COM", com)):
                print(f"   --- plano {nome} ---")
                print("   " + res[rotulo][3].replace("\n", "\n   "))

    print(f"\nÍndices restaurados pelo ROLLBACK: {restaurados} de {len(INDICES)}")


if __name__ == "__main__":
    main()
