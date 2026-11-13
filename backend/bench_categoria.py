import random
import statistics
import sys
import time

from sqlalchemy import select

from app import redis_routines as rr
from app import services
from app.config import settings
from app.db import SessionLocal
from app.models import Category

N = int(sys.argv[1]) if len(sys.argv) > 1 else 300


def ms(fn):
    t = time.perf_counter()
    fn()
    return (time.perf_counter() - t) * 1000


def report(nome, xs):
    xs = sorted(xs)
    p95 = xs[int(len(xs) * 0.95) - 1]
    print(f"{nome:<52} mediana {statistics.median(xs):7.3f} ms   p95 {p95:7.3f} ms")


def main():
    r = rr.connect(settings.redis_url)
    db = SessionLocal()
    leaves = [str(i) for i in db.scalars(select(Category.id).where(Category.parent_id.isnot(None)))]

    for c in leaves:
        services.load_category_ids(db, c, 200)

    def ids_sql(limit, offset=0):
        return [ms(lambda: services.load_category_ids(db, random.choice(leaves), limit, offset)) for _ in range(N)]

    print(f"N = {N} repetições por cenário, {len(leaves)} subcategorias\n")
    print("1) Consulta SQL dos ids (PostgreSQL, sem Redis)")
    report("   LIMIT 20 (loader antigo)", ids_sql(20))
    report("   LIMIT 200 (loader novo, só no cache miss)", ids_sql(200))
    report("   LIMIT 20 OFFSET 200 (página 11, sem cache)", ids_sql(20, 200))

    def ids_cache(cached_ids, page, miss):
        out = []
        for _ in range(N):
            c = random.choice(leaves)
            key = rr.k_category(c)
            if miss:
                r.delete(key)
            else:
                rr.get_category_page(r, c, 1, 20, cached_ids, lambda x: services.load_category_ids(db, x, cached_ids),
                                     lambda x, o, l: services.load_category_ids(db, x, l, o))
            out.append(ms(lambda: rr.get_category_page(
                r, c, page, 20, cached_ids, lambda x: services.load_category_ids(db, x, cached_ids),
                lambda x, o, l: services.load_category_ids(db, x, l, o))))
        return out

    print("\n2) Ids de uma página via cache-aside (LIST cache:category:{id}:products)")
    report("   miss, LIST de 20 ids (antes)", ids_cache(20, 1, True))
    report("   miss, LIST de 200 ids (depois)", ids_cache(200, 1, True))
    report("   hit página 1, LIST de 20 ids (antes)", ids_cache(20, 1, False))
    report("   hit página 1, LIST de 200 ids (depois)", ids_cache(200, 1, False))
    report("   hit página 5, LIST de 200 ids (depois)", ids_cache(200, 5, False))

    def full_page(hit):
        out = []
        for _ in range(N):
            c = random.choice(leaves)
            if hit:
                services.category_products(r, db, c, 1)
            else:
                r.delete(rr.k_category(c))
                for pid in services.load_category_ids(db, c, 200):
                    r.delete(rr.k_product(pid))
            out.append(ms(lambda: services.category_products(r, db, c, 1)))
        return out

    print("\n3) Página completa (ids + 20 produtos), como a rota GET /categories/{id}/products")
    report("   tudo em miss (LIST de 200 + 20 produtos)", full_page(False))
    report("   tudo em hit", full_page(True))
    db.close()


if __name__ == "__main__":
    main()
