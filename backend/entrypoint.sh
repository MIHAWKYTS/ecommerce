#!/bin/sh
set -e
alembic upgrade head
if [ "$SEED" = "1" ]; then
  python - <<'PY'
import os, psycopg2
dsn = os.environ["DATABASE_URL"].replace("postgresql+psycopg2://", "postgresql://")
conn = psycopg2.connect(dsn)
cur = conn.cursor()
cur.execute("SELECT count(*) FROM products")
if cur.fetchone()[0] == 0:
    print("Carregando seed...", flush=True)
    sql = "\n".join(l for l in open("sql/04_seed.sql", encoding="utf8").read().splitlines() if not l.startswith("\\"))
    cur.execute(sql)
    conn.commit()
    print("Seed concluído.", flush=True)
else:
    print("Seed ignorado: já há produtos.", flush=True)

cur.execute("SELECT EXISTS (SELECT 1 FROM categories WHERE slug LIKE 'cat-%')")
if cur.fetchone()[0]:
    print("Aplicando catálogo de demonstração...", flush=True)
    sql = "\n".join(l for l in open("sql/05_vitrine.sql", encoding="utf8").read().splitlines() if not l.startswith("\\"))
    cur.execute(sql)
    conn.commit()
    conn.autocommit = True
    for t in ("categories", "products", "product_images"):
        cur.execute(f"VACUUM ANALYZE {t}")
    import redis
    r = redis.Redis.from_url(os.environ["REDIS_URL"])
    n = sum(r.delete(k) for k in r.scan_iter("cache:*", count=1000))
    print(f"Catálogo aplicado; {n} chaves de cache removidas.", flush=True)
else:
    print("Catálogo de demonstração já aplicado.", flush=True)
PY
fi
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2
