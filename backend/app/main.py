import uuid
from contextlib import asynccontextmanager
from decimal import Decimal
from typing import Annotated

import redis
from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from . import redis_routines as rr
from . import services
from .config import settings
from .db import get_db
from .models import Address, User
from .security import hash_password, verify_password

_redis: redis.Redis | None = None


def get_redis() -> redis.Redis:
    global _redis
    if _redis is None:
        _redis = rr.connect(settings.redis_url)
    return _redis


app = FastAPI(title="E-commerce de Alto Tráfego (BD II)", version="1.0")
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins.split(","),
                   allow_methods=["*"], allow_headers=["*"])

DB = Annotated[Session, Depends(get_db)]
R = Annotated[redis.Redis, Depends(get_redis)]


def current_user(r: R, authorization: str | None = Header(default=None)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Não autenticado")
    sid = authorization[7:]
    sess = rr.get_session(r, sid)
    if not sess:
        raise HTTPException(401, "Sessão expirada")
    return {**sess, "session_id": sid}


User_ = Annotated[dict, Depends(current_user)]


def admin_user(db: DB, user: User_) -> dict:
    admins = {e.strip().lower() for e in settings.admin_emails.split(",") if e.strip()}
    email = db.scalar(select(User.email).where(User.id == uuid.UUID(user["user_id"])))
    if not email or email.lower() not in admins:
        raise HTTPException(403, "Acesso restrito ao administrador")
    return user


Admin_ = Annotated[dict, Depends(admin_user)]


class RegisterIn(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class AddressIn(BaseModel):
    street: str = Field(max_length=200)
    number: str = Field(max_length=20)
    complement: str | None = Field(default=None, max_length=100)
    city: str = Field(max_length=100)
    state: str = Field(min_length=2, max_length=2)
    zip_code: str = Field(max_length=10)


class CartItemIn(BaseModel):
    quantity: int = Field(ge=0, le=999)


class ProductUpdateIn(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    price: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    active: bool | None = None
    category_id: str | None = None


class CheckoutIn(BaseModel):
    address_id: str
    method: str = Field(default="pix", pattern="^(pix|credit_card|boleto)$")


@app.get("/health")
def health(db: DB, r: R):
    db.execute(text("SELECT 1"))
    r.ping()
    return {"postgres": "ok", "redis": "ok"}


@app.post("/auth/register", status_code=201)
def register(body: RegisterIn, db: DB, r: R):
    if db.scalar(select(User.id).where(User.email == body.email.lower())):
        raise HTTPException(409, "E-mail já cadastrado")
    u = User(name=body.name, email=body.email.lower(), password_hash=hash_password(body.password))
    db.add(u)
    db.commit()
    sid = rr.create_session(r, str(u.id), {"name": u.name})
    return {"session_id": sid, "user": {"id": str(u.id), "name": u.name, "email": u.email}}


@app.post("/auth/login")
def login(body: LoginIn, db: DB, r: R):
    u = db.scalar(select(User).where(User.email == body.email.lower()))
    if not u or not verify_password(body.password, u.password_hash):
        raise HTTPException(401, "Credenciais inválidas")
    sid = rr.create_session(r, str(u.id), {"name": u.name})
    return {"session_id": sid, "user": {"id": str(u.id), "name": u.name, "email": u.email}}


@app.post("/auth/logout", status_code=204)
def logout(r: R, user: User_):
    rr.destroy_session(r, user["session_id"])


@app.get("/auth/me")
def me(user: User_):
    return {"id": user["user_id"], "name": user.get("name")}


@app.get("/categories")
def categories(db: DB):
    return services.list_categories(db)


@app.get("/categories/{category_id}/products")
def category_products(category_id: str, db: DB, r: R, page: int = Query(1, ge=1)):
    return services.category_products(r, db, category_id, page)


@app.get("/products/{product_id}")
def product(product_id: str, db: DB, r: R):
    p = rr.get_product(r, product_id, lambda i: services.load_product(db, i))
    if p is None:
        raise HTTPException(404, "Produto não encontrado")
    return p


@app.patch("/products/{product_id}")
def update_product(product_id: str, body: ProductUpdateIn, db: DB, r: R, _: Admin_):
    p = services.update_product(r, db, product_id, body.model_dump(exclude_unset=True))
    if p is None:
        raise HTTPException(404, "Produto não encontrado")
    return p


@app.get("/products/{product_id}/stock")
def product_stock(product_id: str, db: DB):
    q = services.product_stock(db, product_id)
    if q is None:
        raise HTTPException(404, "Produto não encontrado")
    return {"product_id": product_id, "available": q}


@app.get("/addresses")
def addresses(db: DB, user: User_):
    rows = db.scalars(select(Address).where(Address.user_id == uuid.UUID(user["user_id"]))).all()
    return [{"id": str(a.id), "street": a.street, "number": a.number, "complement": a.complement,
             "city": a.city, "state": a.state, "zip_code": a.zip_code, "is_default": a.is_default} for a in rows]


@app.post("/addresses", status_code=201)
def add_address(body: AddressIn, db: DB, user: User_):
    a = Address(user_id=uuid.UUID(user["user_id"]), **body.model_dump())
    db.add(a)
    db.commit()
    return {"id": str(a.id)}


@app.get("/cart")
def get_cart(db: DB, r: R, user: User_):
    return services.cart_detail(r, db, user["user_id"])


@app.put("/cart/items/{product_id}")
def set_cart_item(product_id: str, body: CartItemIn, db: DB, r: R, user: User_):
    if body.quantity > 0 and rr.get_product(r, product_id, lambda i: services.load_product(db, i)) is None:
        raise HTTPException(404, "Produto não encontrado")
    if body.quantity > 0:
        available = services.stock_of(db, product_id) or 0
        if body.quantity > available:
            raise HTTPException(409, f"Só há {available} {'unidade' if available == 1 else 'unidades'} em estoque")
    rr.cart_set(r, user["user_id"], product_id, body.quantity)
    return services.cart_detail(r, db, user["user_id"])


@app.delete("/cart", status_code=204)
def clear_cart(r: R, user: User_):
    rr.cart_clear(r, user["user_id"])


@app.post("/checkout", status_code=201)
def checkout(body: CheckoutIn, db: DB, r: R, user: User_):
    return services.checkout(r, db, user["user_id"], body.address_id, body.method)


@app.get("/orders")
def orders(db: DB, user: User_):
    return services.list_orders(db, user["user_id"])


@app.get("/orders/{order_id}")
def order(order_id: str, db: DB, user: User_):
    o = services.order_detail(db, user["user_id"], order_id)
    if o is None:
        raise HTTPException(404, "Pedido não encontrado")
    return o
