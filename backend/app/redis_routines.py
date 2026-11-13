import json
import uuid
from typing import Callable, Optional

import redis

SESSION_TTL = 30 * 60
CART_TTL = 7 * 24 * 60 * 60
CACHE_TTL = 5 * 60


def k_session(session_id: str) -> str:
    return f"session:{session_id}"


def k_cart(user_id: str) -> str:
    return f"cart:{user_id}"


def k_product(product_id: str) -> str:
    return f"cache:product:{product_id}"


def k_category(category_id: str) -> str:
    return f"cache:category:{category_id}:products"


def connect(url: str = "redis://localhost:6379/0") -> redis.Redis:
    return redis.Redis.from_url(url, decode_responses=True)


def _dumps(obj) -> str:
    return json.dumps(obj, default=str, ensure_ascii=False)


def create_session(r: redis.Redis, user_id: str, extra: Optional[dict] = None) -> str:
    session_id = uuid.uuid4().hex
    data = {"user_id": user_id, **(extra or {})}
    r.set(k_session(session_id), _dumps(data), ex=SESSION_TTL)
    return session_id


def get_session(r: redis.Redis, session_id: str) -> Optional[dict]:
    key = k_session(session_id)
    pipe = r.pipeline()
    pipe.get(key)
    pipe.expire(key, SESSION_TTL)
    raw, _ = pipe.execute()
    return json.loads(raw) if raw else None


def destroy_session(r: redis.Redis, session_id: str) -> bool:
    return r.delete(k_session(session_id)) == 1


def cart_add(r: redis.Redis, user_id: str, product_id: str, qty: int = 1) -> int:
    if qty <= 0:
        raise ValueError("qty deve ser positivo")
    key = k_cart(user_id)
    pipe = r.pipeline()
    pipe.hincrby(key, product_id, qty)
    pipe.expire(key, CART_TTL)
    new_qty, _ = pipe.execute()
    return new_qty


def cart_set(r: redis.Redis, user_id: str, product_id: str, qty: int) -> None:
    key = k_cart(user_id)
    if qty <= 0:
        r.hdel(key, product_id)
        return
    pipe = r.pipeline()
    pipe.hset(key, product_id, qty)
    pipe.expire(key, CART_TTL)
    pipe.execute()


def cart_remove(r: redis.Redis, user_id: str, product_id: str) -> bool:
    return r.hdel(k_cart(user_id), product_id) == 1


def cart_get(r: redis.Redis, user_id: str) -> dict:
    return {pid: int(q) for pid, q in r.hgetall(k_cart(user_id)).items()}


def cart_clear(r: redis.Redis, user_id: str) -> None:
    r.delete(k_cart(user_id))


def get_product(r: redis.Redis, product_id: str,
                loader: Callable[[str], Optional[dict]]) -> Optional[dict]:
    key = k_product(product_id)
    raw = r.get(key)
    if raw is not None:
        return json.loads(raw)
    product = loader(product_id)
    if product is not None:
        r.set(key, _dumps(product), ex=CACHE_TTL)
    return product


def get_products(r: redis.Redis, product_ids: list,
                 loader: Callable[[list], dict]) -> list:
    if not product_ids:
        return []
    raws = r.mget([k_product(pid) for pid in product_ids])
    cached = {pid: json.loads(raw) for pid, raw in zip(product_ids, raws) if raw is not None}
    missing = [pid for pid in product_ids if pid not in cached]
    if missing:
        loaded = loader(missing)
        if loaded:
            pipe = r.pipeline()
            for pid, product in loaded.items():
                pipe.set(k_product(pid), _dumps(product), ex=CACHE_TTL)
            pipe.execute()
        cached.update(loaded)
    return [cached[pid] for pid in product_ids if pid in cached]


def invalidate_product(r: redis.Redis, product_id: str) -> None:
    r.delete(k_product(product_id))


def get_category_products(r: redis.Redis, category_id: str,
                          loader: Callable[[str], list]) -> list:
    key = k_category(category_id)
    cached = r.lrange(key, 0, -1)
    if cached:
        return cached
    ids = [str(i) for i in loader(category_id)]
    if ids:
        pipe = r.pipeline()
        pipe.delete(key)
        pipe.rpush(key, *ids)
        pipe.expire(key, CACHE_TTL)
        pipe.execute()
    return ids


def get_category_page(r: redis.Redis, category_id: str, page: int, page_size: int, cached_ids: int,
                      loader: Callable[[str], list],
                      page_loader: Callable[[str, int, int], list]) -> list:
    key = k_category(category_id)
    start = (page - 1) * page_size
    end = start + page_size - 1
    if end < cached_ids:
        ids = r.lrange(key, start, end)
        if ids:
            return ids
        if r.exists(key):
            return []
        return _fill_category(r, key, loader(category_id))[start:end + 1]
    n = r.llen(key)
    if n == 0:
        n = len(_fill_category(r, key, loader(category_id)))
    if n < cached_ids:
        return []
    return [str(i) for i in page_loader(category_id, start, page_size)]


def _fill_category(r: redis.Redis, key: str, ids: list) -> list:
    ids = [str(i) for i in ids]
    if ids:
        pipe = r.pipeline()
        pipe.delete(key)
        pipe.rpush(key, *ids)
        pipe.expire(key, CACHE_TTL)
        pipe.execute()
    return ids


def invalidate_category(r: redis.Redis, category_id: str) -> None:
    r.delete(k_category(category_id))
