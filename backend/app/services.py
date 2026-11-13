import uuid
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session

from . import redis_routines as rr
from .models import Address, Category, Inventory, Order, OrderItem, Product, ProductImage

PAGE_SIZE = 20
CATEGORY_CACHED_IDS = 200


def load_product(db: Session, product_id: str) -> dict | None:
    try:
        pid = uuid.UUID(product_id)
    except ValueError:
        return None
    p = db.get(Product, pid)
    if p is None or not p.active:
        return None
    imgs = db.scalars(select(ProductImage.url).where(ProductImage.product_id == pid)
                      .order_by(ProductImage.position)).all()
    return _product_dict(p, list(imgs))


def load_products(db: Session, product_ids: list[str]) -> dict[str, dict]:
    pids = []
    for i in product_ids:
        try:
            pids.append(uuid.UUID(i))
        except ValueError:
            pass
    if not pids:
        return {}
    prods = db.scalars(select(Product).where(Product.id.in_(pids), Product.active)).all()
    imgs: dict[uuid.UUID, list[str]] = {p.id: [] for p in prods}
    for pid, url in db.execute(select(ProductImage.product_id, ProductImage.url)
                               .where(ProductImage.product_id.in_(list(imgs)))
                               .order_by(ProductImage.product_id, ProductImage.position)):
        imgs[pid].append(url)
    return {str(p.id): _product_dict(p, imgs[p.id]) for p in prods}


def _product_dict(p: Product, images: list[str]) -> dict:
    return {"id": str(p.id), "category_id": str(p.category_id), "sku": p.sku, "name": p.name,
            "description": p.description, "price": str(p.price), "images": images}


def load_category_ids(db: Session, category_id: str, limit: int = PAGE_SIZE, offset: int = 0) -> list[str]:
    try:
        cid = uuid.UUID(category_id)
    except ValueError:
        return []
    rows = db.scalars(select(Product.id).where(Product.category_id == cid, Product.active)
                      .order_by(Product.name).limit(limit).offset(offset)).all()
    return [str(i) for i in rows]


def list_categories(db: Session) -> list[dict]:
    rows = db.execute(select(Category.id, Category.parent_id, Category.name, Category.slug)
                      .order_by(Category.name)).all()
    return [{"id": str(r.id), "parent_id": str(r.parent_id) if r.parent_id else None,
             "name": r.name, "slug": r.slug} for r in rows]


def category_products(r, db: Session, category_id: str, page: int = 1) -> list[dict]:
    ids = rr.get_category_page(r, category_id, page, PAGE_SIZE, CATEGORY_CACHED_IDS,
                               lambda c: load_category_ids(db, c, CATEGORY_CACHED_IDS),
                               lambda c, off, lim: load_category_ids(db, c, lim, off))
    return rr.get_products(r, ids, lambda miss: load_products(db, miss))


LISTING_FIELDS = {"name", "active", "category_id"}


def update_product(r, db: Session, product_id: str, changes: dict) -> dict | None:
    try:
        pid = uuid.UUID(product_id)
    except ValueError:
        return None
    p = db.get(Product, pid)
    if p is None:
        return None
    old_category = str(p.category_id)
    if "category_id" in changes:
        try:
            cid = uuid.UUID(str(changes["category_id"]))
        except ValueError:
            raise HTTPException(422, "Categoria inválida")
        if db.get(Category, cid) is None:
            raise HTTPException(422, "Categoria não encontrada")
        changes["category_id"] = cid
    for field, value in changes.items():
        setattr(p, field, value)
    db.commit()
    db.refresh(p)

    rr.invalidate_product(r, product_id)
    if LISTING_FIELDS & changes.keys():
        rr.invalidate_category(r, old_category)
        if str(p.category_id) != old_category:
            rr.invalidate_category(r, str(p.category_id))

    imgs = db.scalars(select(ProductImage.url).where(ProductImage.product_id == pid)
                      .order_by(ProductImage.position)).all()
    return {**_product_dict(p, list(imgs)), "active": p.active,
            "updated_at": p.updated_at.isoformat()}


def cart_detail(r, db: Session, user_id: str) -> dict:
    cart = rr.cart_get(r, user_id)
    items, total = [], Decimal("0")
    for pid, qty in cart.items():
        p = rr.get_product(r, pid, lambda i: load_product(db, i))
        if p is None:
            continue
        sub = Decimal(p["price"]) * qty
        total += sub
        items.append({"product_id": pid, "name": p["name"], "price": p["price"],
                      "quantity": qty, "subtotal": str(sub),
                      "available": stock_of(db, pid) or 0})
    return {"items": items, "total": str(total)}


def checkout(r, db: Session, user_id: str, address_id: str, method: str) -> dict:
    cart = rr.cart_get(r, user_id)
    if not cart:
        raise HTTPException(400, "Carrinho vazio")
    try:
        uid, aid = uuid.UUID(user_id), uuid.UUID(address_id)
        pids = {uuid.UUID(p): q for p, q in cart.items()}
    except ValueError:
        raise HTTPException(422, "Identificador inválido")
    try:
        addr = db.get(Address, aid)
        if addr is None or addr.user_id != uid:
            raise HTTPException(404, "Endereço não encontrado")
        prods = {p.id: p for p in db.scalars(select(Product).where(Product.id.in_(pids), Product.active))}
        missing = [str(p) for p in pids if p not in prods]
        if missing:
            raise HTTPException(409, f"Produto indisponível: {', '.join(missing)}")
        order = Order(user_id=uid, address_id=aid)
        db.add(order)
        db.flush()
        for pid in sorted(pids):
            db.add(OrderItem(order_id=order.id, product_id=pid, quantity=pids[pid], unit_price=prods[pid].price))
        db.flush()
        row = db.execute(text("CALL sp_checkout(CAST(:o AS uuid), :m, CAST(NULL AS varchar), CAST(NULL AS uuid))"),
                         {"o": str(order.id), "m": method}).one()
        payment_id = str(row[0]) if row and row[0] else None
        total = db.scalar(select(Order.total_amount).where(Order.id == order.id))
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except (DBAPIError, IntegrityError) as e:
        db.rollback()
        code = getattr(e.orig, "pgcode", None)
        if code == "EST01":
            raise HTTPException(409, "Estoque insuficiente")
        if code == "EST02":
            raise HTTPException(400, "Pedido inválido")
        raise
    rr.cart_clear(r, user_id)
    return {"order_id": str(order.id), "payment_id": payment_id, "status": "paid", "total": str(total)}


def list_orders(db: Session, user_id: str) -> list[dict]:
    rows = db.execute(select(Order.id, Order.status, Order.total_amount, Order.created_at)
                      .where(Order.user_id == uuid.UUID(user_id)).order_by(Order.created_at.desc()).limit(20)).all()
    return [{"id": str(r.id), "status": r.status, "total": str(r.total_amount),
             "created_at": r.created_at.isoformat()} for r in rows]


def order_detail(db: Session, user_id: str, order_id: str) -> dict | None:
    try:
        oid, uid = uuid.UUID(order_id), uuid.UUID(user_id)
    except ValueError:
        return None
    s = db.execute(text("SELECT order_id, created_at, order_status, distinct_items, total_units, "
                        "items_total, total_amount, payment_method, payment_status "
                        "FROM vw_order_summary WHERE order_id = :o AND user_id = :u"),
                   {"o": oid, "u": uid}).one_or_none()
    if s is None:
        return None
    items = db.execute(select(OrderItem.product_id, Product.name, OrderItem.quantity,
                              OrderItem.unit_price, OrderItem.subtotal)
                       .join(Product, Product.id == OrderItem.product_id)
                       .where(OrderItem.order_id == oid).order_by(Product.name)).all()
    return {"id": str(s.order_id), "created_at": s.created_at.isoformat(), "status": s.order_status,
            "total": str(s.total_amount), "items_total": str(s.items_total),
            "distinct_items": s.distinct_items, "total_units": int(s.total_units),
            "payment": {"method": s.payment_method, "status": s.payment_status},
            "items": [{"product_id": str(i.product_id), "name": i.name, "quantity": i.quantity,
                       "unit_price": str(i.unit_price), "subtotal": str(i.subtotal)} for i in items]}


def product_stock(db: Session, product_id: str) -> int | None:
    try:
        pid = uuid.UUID(product_id)
    except ValueError:
        return None
    return db.scalar(select(Inventory.quantity).join(Product, Product.id == Inventory.product_id)
                     .where(Product.id == pid, Product.active))


def stock_of(db: Session, product_id: str) -> int | None:
    return db.scalar(select(Inventory.quantity).where(Inventory.product_id == uuid.UUID(product_id)))
