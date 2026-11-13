import threading
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db import engine
from app.main import app, get_redis

client = TestClient(app)


def _user():
    email = f"t{uuid.uuid4().hex[:10]}@example.com"
    r = client.post("/auth/register", json={"name": "Teste", "email": email, "password": "senha123"})
    assert r.status_code == 201, r.text
    h = {"Authorization": f"Bearer {r.json()['session_id']}"}
    a = client.post("/addresses", headers=h, json={"street": "Rua A", "number": "1", "city": "Penedo",
                                                   "state": "AL", "zip_code": "57200-000"})
    assert a.status_code == 201
    return h, a.json()["id"], email


def _product(qty):
    with engine.begin() as c:
        cat = c.execute(text("SELECT id FROM categories LIMIT 1")).scalar()
        pid = c.execute(text("INSERT INTO products (category_id, sku, name, price) "
                             "VALUES (:c, :s, 'Produto de teste', 10.00) RETURNING id"),
                        {"c": cat, "s": "T-" + uuid.uuid4().hex[:12]}).scalar()
        c.execute(text("INSERT INTO inventory (product_id, quantity) VALUES (:p, :q)"), {"p": pid, "q": qty})
    return str(pid)


def stock(pid):
    with engine.connect() as c:
        return c.execute(text("SELECT quantity FROM inventory WHERE product_id=:p"), {"p": pid}).scalar()


def test_health():
    assert client.get("/health").json() == {"postgres": "ok", "redis": "ok"}


def test_auth_flow():
    h, _, email = _user()
    assert client.get("/auth/me", headers=h).status_code == 200
    assert client.post("/auth/login", json={"email": email, "password": "errada"}).status_code == 401
    assert client.post("/auth/login", json={"email": email, "password": "senha123"}).status_code == 200
    assert client.post("/auth/register", json={"name": "x", "email": email, "password": "senha123"}).status_code == 409
    client.post("/auth/logout", headers=h)
    assert client.get("/auth/me", headers=h).status_code == 401
    assert client.get("/cart").status_code == 401


def test_catalog_and_cache():
    r = get_redis()
    cats = client.get("/categories").json()
    leaf = next(c for c in cats if c["parent_id"])
    r.delete(f"cache:category:{leaf['id']}:products")
    lst = client.get(f"/categories/{leaf['id']}/products").json()
    assert len(lst) == 20
    assert r.llen(f"cache:category:{leaf['id']}:products") == 200
    assert 0 < r.ttl(f"cache:category:{leaf['id']}:products") <= 300
    assert client.get(f"/categories/{leaf['id']}/products").json() == lst
    pid = lst[0]["id"]
    assert client.get(f"/products/{pid}").json()["id"] == pid
    assert r.exists(f"cache:product:{pid}") == 1
    assert client.get(f"/products/{uuid.uuid4()}").status_code == 404
    assert client.get("/products/nao-e-uuid").status_code == 404


def test_cart_and_successful_checkout():
    h, addr, _ = _user()
    pid = _product(5)
    r = client.put(f"/cart/items/{pid}", headers=h, json={"quantity": 2})
    assert r.json()["total"] == "20.00"
    uid = client.get("/auth/me", headers=h).json()["id"]
    assert get_redis().exists(f"cart:{uid}") == 1
    c = client.post("/checkout", headers=h, json={"address_id": addr, "method": "pix"})
    assert c.status_code == 201, c.text
    assert c.json()["status"] == "paid" and c.json()["total"] == "20.00"
    assert stock(pid) == 3
    assert get_redis().exists(f"cart:{uid}") == 0
    assert client.get("/orders", headers=h).json()[0]["status"] == "paid"
    assert client.post("/checkout", headers=h, json={"address_id": addr}).status_code == 400


def test_insufficient_stock_rolls_back_and_keeps_cart():
    h, addr, _ = _user()
    pid = _product(2)
    assert client.put(f"/cart/items/{pid}", headers=h, json={"quantity": 2}).status_code == 200
    with engine.begin() as c:
        c.execute(text("UPDATE inventory SET quantity = 1 WHERE product_id = :p"), {"p": pid})
    uid = client.get("/auth/me", headers=h).json()["id"]
    c = client.post("/checkout", headers=h, json={"address_id": addr})
    assert c.status_code == 409 and "Estoque" in c.json()["detail"]
    assert stock(pid) == 1
    assert client.get("/orders", headers=h).json() == []
    assert get_redis().exists(f"cart:{uid}") == 1


def test_address_of_other_user_is_rejected():
    h1, _, _ = _user()
    _, addr2, _ = _user()
    pid = _product(3)
    client.put(f"/cart/items/{pid}", headers=h1, json={"quantity": 1})
    assert client.post("/checkout", headers=h1, json={"address_id": addr2}).status_code == 404


def test_concurrent_last_unit_sells_once():
    pid = _product(1)
    users = [_user() for _ in range(6)]
    for h, _, _ in users:
        client.put(f"/cart/items/{pid}", headers=h, json={"quantity": 1})
    codes = []

    def go(h, addr):
        codes.append(client.post("/checkout", headers=h, json={"address_id": addr}).status_code)

    ts = [threading.Thread(target=go, args=(h, a)) for h, a, _ in users]
    [t.start() for t in ts]
    [t.join() for t in ts]
    assert sorted(codes) == [201] + [409] * 5, codes
    assert stock(pid) == 0


def _leaf():
    return next(c for c in client.get("/categories").json() if c["parent_id"])


def test_category_pagination():
    r = get_redis()
    leaf = _leaf()
    key = f"cache:category:{leaf['id']}:products"
    r.delete(key)
    p1 = client.get(f"/categories/{leaf['id']}/products").json()
    assert client.get(f"/categories/{leaf['id']}/products?page=1").json() == p1
    p2 = client.get(f"/categories/{leaf['id']}/products?page=2").json()
    assert len(p2) == 20 and not {p["id"] for p in p1} & {p["id"] for p in p2}
    assert r.lrange(key, 0, 39) == [p["id"] for p in p1 + p2]
    p11 = client.get(f"/categories/{leaf['id']}/products?page=11").json()
    assert len(p11) == 20 and p11[0]["id"] not in r.lrange(key, 0, -1)
    assert list(r.scan_iter(f"cache:category:{leaf['id']}*")) == [key]
    assert r.llen(key) == 200 and 0 < r.ttl(key) <= 300
    assert client.get(f"/categories/{leaf['id']}/products?page=1000").json() == []
    for bad in ("0", "-1", "abc"):
        assert client.get(f"/categories/{leaf['id']}/products?page={bad}").status_code == 422


def test_stock_is_read_from_postgres_without_cache():
    h, addr, _ = _user()
    pid = _product(5)
    assert client.get(f"/products/{pid}").status_code == 200
    assert client.get(f"/products/{pid}/stock").json() == {"product_id": pid, "available": 5}
    client.put(f"/cart/items/{pid}", headers=h, json={"quantity": 2})
    assert client.post("/checkout", headers=h, json={"address_id": addr}).status_code == 201
    assert client.get(f"/products/{pid}/stock").json()["available"] == 3
    r = get_redis()
    assert "available" not in r.get(f"cache:product:{pid}") and "quantity" not in r.get(f"cache:product:{pid}")
    assert [k for k in r.scan_iter(f"*{pid}*") if k != f"cache:product:{pid}"] == []
    assert client.get(f"/products/{uuid.uuid4()}/stock").status_code == 404
    assert client.get("/products/nao-e-uuid/stock").status_code == 404


def test_order_detail():
    h, addr, _ = _user()
    pa, pb = _product(5), _product(5)
    client.put(f"/cart/items/{pa}", headers=h, json={"quantity": 2})
    client.put(f"/cart/items/{pb}", headers=h, json={"quantity": 1})
    oid = client.post("/checkout", headers=h, json={"address_id": addr, "method": "boleto"}).json()["order_id"]
    with engine.begin() as c:
        c.execute(text("UPDATE products SET price = 99.99 WHERE id = :p"), {"p": pa})
    d = client.get(f"/orders/{oid}", headers=h)
    assert d.status_code == 200, d.text
    d = d.json()
    assert d["id"] == oid and d["status"] == "paid" and d["total"] == "30.00"
    assert d["distinct_items"] == 2 and d["total_units"] == 3
    assert d["payment"] == {"method": "boleto", "status": "approved"}
    assert sum(float(i["subtotal"]) for i in d["items"]) == 30.0
    assert {i["unit_price"] for i in d["items"]} == {"10.00"}
    h2, _, _ = _user()
    assert client.get(f"/orders/{oid}", headers=h2).status_code == 404
    assert client.get(f"/orders/{oid}").status_code == 401
    assert client.get(f"/orders/{uuid.uuid4()}", headers=h).status_code == 404
    assert client.get("/orders/nao-e-uuid", headers=h).status_code == 404


def test_category_listing_mget_mixes_hits_and_misses():
    r = get_redis()
    leaf = _leaf()
    key = f"cache:category:{leaf['id']}:products"
    first = client.get(f"/categories/{leaf['id']}/products").json()
    ids = r.lrange(key, 0, 19)
    r.delete(*[f"cache:product:{pid}" for pid in ids[::2]])
    lst = client.get(f"/categories/{leaf['id']}/products").json()
    assert [p["id"] for p in lst] == ids
    assert lst == first
    for pid in ids:
        assert 0 < r.ttl(f"cache:product:{pid}") <= 300
    assert lst[3] == client.get(f"/products/{ids[3]}").json()


def test_batch_loader_matches_single_and_uses_two_queries():
    from sqlalchemy import event
    from app import services
    from app.db import SessionLocal
    r = get_redis()
    leaf = _leaf()
    ids = [p["id"] for p in client.get(f"/categories/{leaf['id']}/products").json()]
    with SessionLocal() as db:
        lote = services.load_products(db, ids + [str(uuid.uuid4()), "nao-e-uuid"])
        assert set(lote) == set(ids)
        assert all(lote[i] == services.load_product(db, i) for i in ids)
    r.delete(*[f"cache:product:{pid}" for pid in ids])
    stmts = []
    listen = lambda conn, cur, stmt, *a: stmts.append(stmt)
    event.listen(engine, "before_cursor_execute", listen)
    try:
        lst = client.get(f"/categories/{leaf['id']}/products").json()
    finally:
        event.remove(engine, "before_cursor_execute", listen)
    assert [p["id"] for p in lst] == ids
    assert len([s for s in stmts if "FROM products" in s or "FROM product_images" in s]) == 2
    assert all(0 < r.ttl(f"cache:product:{pid}") <= 300 for pid in ids)


def test_product_update_requires_admin_and_invalidates_cache(monkeypatch):
    from app.config import settings
    r = get_redis()
    pid = _product(5)
    cat = client.get(f"/products/{pid}").json()["category_id"]
    client.get(f"/categories/{cat}/products")
    kp, kc = f"cache:product:{pid}", f"cache:category:{cat}:products"
    assert r.exists(kp) == 1 and r.exists(kc) == 1

    h, _, email = _user()
    assert client.patch(f"/products/{pid}", json={"price": "1.00"}).status_code == 401
    monkeypatch.setattr(settings, "admin_emails", "")
    assert client.patch(f"/products/{pid}", headers=h, json={"price": "1.00"}).status_code == 403
    monkeypatch.setattr(settings, "admin_emails", f"outro@example.com, {email.upper()}")

    u = client.patch(f"/products/{pid}", headers=h, json={"price": "12.34"})
    assert u.status_code == 200 and u.json()["price"] == "12.34"
    assert r.exists(kp) == 0 and r.exists(kc) == 1
    assert client.get(f"/products/{pid}").json()["price"] == "12.34"
    assert r.exists(kp) == 1

    assert client.patch(f"/products/{pid}", headers=h, json={"name": "Produto renomeado"}).status_code == 200
    assert r.exists(kp) == 0 and r.exists(kc) == 0

    novo = next(c["id"] for c in client.get("/categories").json() if c["id"] != cat)
    client.get(f"/categories/{cat}/products"); client.get(f"/categories/{novo}/products")
    assert client.patch(f"/products/{pid}", headers=h, json={"category_id": novo}).json()["category_id"] == novo
    assert r.exists(kc) == 0 and r.exists(f"cache:category:{novo}:products") == 0

    assert client.patch(f"/products/{pid}", headers=h, json={"active": False}).json()["active"] is False
    assert client.get(f"/products/{pid}").status_code == 404
    assert client.patch(f"/products/{pid}", headers=h, json={"active": True}).status_code == 200
    assert client.get(f"/products/{pid}").json()["name"] == "Produto renomeado"

    assert client.patch(f"/products/{pid}", headers=h, json={"price": "-1"}).status_code == 422
    assert client.patch(f"/products/{pid}", headers=h, json={"category_id": str(uuid.uuid4())}).status_code == 422
    assert client.patch(f"/products/{uuid.uuid4()}", headers=h, json={"price": "1"}).status_code == 404
    assert stock(pid) == 5
