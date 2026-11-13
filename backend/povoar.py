import argparse
import os
import time

import psycopg2

TABELAS = ["users", "addresses", "categories", "products", "product_images",
           "inventory", "orders", "order_items", "payments"]


def dsn() -> str:
    url = os.environ.get("DATABASE_URL",
                         "postgresql+psycopg2://ecommerce:ecommerce@localhost:5432/ecommerce")
    return url.replace("postgresql+psycopg2://", "postgresql://")


def ler_sql(caminho: str) -> str:
    with open(caminho, encoding="utf8") as f:
        return "\n".join(l for l in f.read().splitlines() if not l.startswith("\\"))


def etapa(cur, conn, titulo: str, sql: str) -> None:
    print(f"{titulo}...", end=" ", flush=True)
    t0 = time.perf_counter()
    cur.execute(sql)
    conn.commit()
    print(f"ok ({time.perf_counter() - t0:.1f} s)", flush=True)


def tabela(titulo: str, colunas: list[str], linhas: list[tuple]) -> None:
    linhas = [["" if v is None else str(v) for v in l] for l in linhas]
    larg = [max(len(c), *(len(l[i]) for l in linhas)) if linhas else len(c)
            for i, c in enumerate(colunas)]
    sep = "+" + "+".join("-" * (w + 2) for w in larg) + "+"
    print(f"\n{titulo}")
    print(sep)
    print("| " + " | ".join(c.ljust(w) for c, w in zip(colunas, larg)) + " |")
    print(sep)
    for l in linhas:
        print("| " + " | ".join(v.ljust(w) for v, w in zip(l, larg)) + " |")
    print(sep)


def consulta(cur, sql: str, params=()) -> tuple[list[str], list[tuple]]:
    cur.execute(sql, params)
    return [d[0] for d in cur.description], cur.fetchall()


def povoar(cur, conn, reset: bool) -> None:
    if reset:
        etapa(cur, conn, "Apagando dados existentes",
              f"TRUNCATE {', '.join(TABELAS)} CASCADE")

    cur.execute("SELECT count(*) FROM products")
    if cur.fetchone()[0] == 0:
        etapa(cur, conn, "Carregando 04_seed.sql", ler_sql("sql/04_seed.sql"))
    else:
        print("Seed ignorado: já há produtos (use --reset para recriar).")

    cur.execute("SELECT EXISTS (SELECT 1 FROM categories WHERE slug LIKE 'cat-%')")
    if cur.fetchone()[0]:
        etapa(cur, conn, "Aplicando 05_vitrine.sql", ler_sql("sql/05_vitrine.sql"))
    else:
        print("Catálogo de demonstração já aplicado.")

    conn.commit()
    conn.autocommit = True
    print("VACUUM ANALYZE...", end=" ", flush=True)
    for t in TABELAS:
        cur.execute(f"VACUUM ANALYZE {t}")
    print("ok")
    conn.autocommit = False

    try:
        import redis
        r = redis.Redis.from_url(os.environ.get("REDIS_URL", "redis://localhost:6379/0"))
        n = sum(r.delete(k) for k in r.scan_iter("cache:*", count=1000))
        print(f"Redis: {n} chaves de cache removidas.")
    except Exception as e:
        print(f"Aviso: não foi possível limpar o cache do Redis ({e}).")


def mostrar(cur, n: int) -> None:
    contagens = []
    for t in TABELAS:
        cur.execute(f"SELECT count(*) FROM {t}")
        contagens.append((t, f"{cur.fetchone()[0]:,}".replace(",", ".")))
    tabela("Registros por tabela", ["tabela", "linhas"], contagens)

    tabela(f"Produtos (amostra aleatória de {n})", *consulta(cur, """
        SELECT p.sku, left(p.name, 45) AS nome, d.name || ' › ' || c.name AS categoria,
               p.price AS preco, i.quantity AS estoque, p.active AS ativo
          FROM products p
          JOIN categories c ON c.id = p.category_id
          LEFT JOIN categories d ON d.id = c.parent_id
          JOIN inventory i ON i.product_id = p.id
         ORDER BY random() LIMIT %s""", (n,)))

    tabela(f"Usuários (amostra aleatória de {n})", *consulta(cur, """
        SELECT u.name AS nome, u.email, u.phone AS telefone,
               to_char(u.created_at, 'DD/MM/YYYY') AS cadastro,
               (SELECT count(*) FROM addresses a WHERE a.user_id = u.id) AS enderecos,
               (SELECT count(*) FROM orders o WHERE o.user_id = u.id) AS pedidos
          FROM users u
         ORDER BY random() LIMIT %s""", (n,)))

    cols, pedidos = consulta(cur, """
        SELECT order_id, to_char(created_at, 'DD/MM/YYYY HH24:MI') AS data, user_name AS cliente,
               order_status AS status, distinct_items AS itens, total_units AS unidades,
               total_amount AS total, payment_method AS pagamento, payment_status AS pgto
          FROM vw_order_summary
         WHERE order_id IN (SELECT id FROM orders ORDER BY random() LIMIT %s)""", (n,))
    tabela(f"Pedidos (amostra aleatória de {n}, via vw_order_summary)",
           cols, [(str(p[0])[:8],) + p[1:] for p in pedidos])

    if pedidos:
        tabela(f"Itens do pedido {str(pedidos[0][0])[:8]}", *consulta(cur, """
            SELECT left(p.name, 45) AS produto, oi.quantity AS qtd,
                   oi.unit_price AS preco_unit, oi.subtotal
              FROM order_items oi JOIN products p ON p.id = oi.product_id
             WHERE oi.order_id = %s ORDER BY p.name""", (pedidos[0][0],)))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--reset", action="store_true", help="apaga todos os dados antes de povoar")
    ap.add_argument("--so-mostrar", action="store_true", help="só mostra os dados, sem povoar")
    ap.add_argument("--amostra", type=int, default=5, help="registros exibidos por entidade")
    args = ap.parse_args()

    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    conn = psycopg2.connect(dsn())
    cur = conn.cursor()
    try:
        t0 = time.perf_counter()
        if not args.so_mostrar:
            povoar(cur, conn, args.reset)
            print(f"Povoamento concluído em {time.perf_counter() - t0:.1f} s.")
        mostrar(cur, args.amostra)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
