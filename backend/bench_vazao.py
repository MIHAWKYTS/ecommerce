import asyncio
import multiprocessing as mp
import random
import statistics
import sys
import time
import uuid

import httpx

BASE = "http://backend:8000"
DUR = float(sys.argv[1]) if len(sys.argv) > 1 else 10.0
PROCS = 4


def setup():
    c = httpx.Client(base_url=BASE, timeout=30)
    leaf = next(x for x in c.get("/categories").json() if x["parent_id"])
    pids = [p["id"] for page in (1, 2, 3) for p in c.get(f"/categories/{leaf['id']}/products?page={page}").json()]
    for pid in pids:
        c.get(f"/products/{pid}")
    r = c.post("/auth/register", json={"name": "Carga", "email": f"carga{uuid.uuid4().hex[:8]}@exemplo.com",
                                       "password": "segredo123"})
    tok = {"Authorization": f"Bearer {r.json()['session_id']}"}
    for pid in pids[:3]:
        c.put(f"/cart/items/{pid}", headers=tok, json={"quantity": 1})
    return leaf["id"], pids, tok


def scenarios(leaf, pids, tok):
    return {
        "GET /health (SELECT 1 + PING)": lambda: ("GET", "/health", None, None),
        "GET /categories (PostgreSQL, sem cache)": lambda: ("GET", "/categories", None, None),
        "GET /categories/{id}/products (cache hit)": lambda: ("GET", f"/categories/{leaf}/products?page={random.randint(1, 3)}", None, None),
        "GET /products/{id} (cache hit)": lambda: ("GET", f"/products/{random.choice(pids)}", None, None),
        "GET /products/{id}/stock (PostgreSQL)": lambda: ("GET", f"/products/{random.choice(pids)}/stock", None, None),
        "GET /cart (sessão + carrinho no Redis)": lambda: ("GET", "/cart", tok, None),
        "PUT /cart/items/{id} (escrita no Redis)": lambda: ("PUT", f"/cart/items/{random.choice(pids[:3])}", tok,
                                                            {"quantity": random.randint(1, 5)}),
    }


async def _run(make, conc, dur, out):
    lat, err = [], 0
    limits = httpx.Limits(max_connections=conc, max_keepalive_connections=conc)
    async with httpx.AsyncClient(base_url=BASE, timeout=30, limits=limits) as c:
        end = time.perf_counter() + dur

        async def worker():
            nonlocal err
            while time.perf_counter() < end:
                m, path, h, body = make()
                t = time.perf_counter()
                try:
                    r = await c.request(m, path, headers=h, json=body)
                    if r.status_code >= 400:
                        err += 1
                except httpx.HTTPError:
                    err += 1
                lat.append((time.perf_counter() - t) * 1000)

        await asyncio.gather(*(worker() for _ in range(conc)))
    out.put((lat, err))


def _proc(name, conc, dur, args, out):
    make = scenarios(*args)[name]
    asyncio.run(_run(make, conc, dur, out))


def measure(name, conc, args):
    procs = min(PROCS, conc)
    per = [conc // procs + (1 if i < conc % procs else 0) for i in range(procs)]
    q = mp.Queue()
    ps = [mp.Process(target=_proc, args=(name, n, DUR, args, q)) for n in per]
    [p.start() for p in ps]
    res = [q.get() for _ in ps]
    [p.join() for p in ps]
    lat = sorted(x for l, _ in res for x in l)
    err = sum(e for _, e in res)
    q = lambda f: lat[min(len(lat) - 1, int(len(lat) * f))]
    return len(lat) / DUR, statistics.median(lat), q(0.95), q(0.99), err, len(lat)


def main():
    args = setup()
    print(f"{DUR:.0f} s por cenário, gerador com até {PROCS} processos, backend com 2 workers uvicorn\n")
    print(f"{'Cenário':<44}{'conc':>5}{'req/s':>9}{'p50 ms':>9}{'p95 ms':>9}{'p99 ms':>9}{'erros':>7}")
    for name in scenarios(*args):
        for conc in (1, 32):
            rps, p50, p95, p99, err, n = measure(name, conc, args)
            print(f"{name:<44}{conc:>5}{rps:>9.0f}{p50:>9.2f}{p95:>9.2f}{p99:>9.2f}{err:>7}", flush=True)
    print("\nCurva de saturação: GET /products/{id} (cache hit)")
    for conc in (1, 4, 8, 16, 32, 64, 128):
        rps, p50, p95, p99, err, n = measure("GET /products/{id} (cache hit)", conc, args)
        print(f"{'':<44}{conc:>5}{rps:>9.0f}{p50:>9.2f}{p95:>9.2f}{p99:>9.2f}{err:>7}", flush=True)


if __name__ == "__main__":
    main()
