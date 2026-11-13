import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Boolean, CheckConstraint, Computed, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import DateTime

PK = dict(primary_key=True, server_default=text("gen_random_uuid()"))
NOW = dict(server_default=text("now()"))


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), **PK)
    name: Mapped[str] = mapped_column(String(150))
    email: Mapped[str] = mapped_column(String(255), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    phone: Mapped[Optional[str]] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), **NOW)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), **NOW)


class Address(Base):
    __tablename__ = "addresses"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), **PK)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    street: Mapped[str] = mapped_column(String(200))
    number: Mapped[str] = mapped_column(String(20))
    complement: Mapped[Optional[str]] = mapped_column(String(100))
    city: Mapped[str] = mapped_column(String(100))
    state: Mapped[str] = mapped_column(String(2))
    zip_code: Mapped[str] = mapped_column(String(10))
    is_default: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))


class Category(Base):
    __tablename__ = "categories"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), **PK)
    parent_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("categories.id", ondelete="SET NULL"))
    name: Mapped[str] = mapped_column(String(100))
    slug: Mapped[str] = mapped_column(String(120), unique=True)


class Product(Base):
    __tablename__ = "products"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), **PK)
    category_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("categories.id"))
    sku: Mapped[str] = mapped_column(String(50), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[Optional[str]] = mapped_column(Text)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    active: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), **NOW)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), **NOW)
    images: Mapped[list["ProductImage"]] = relationship(order_by="ProductImage.position", lazy="raise")


class ProductImage(Base):
    __tablename__ = "product_images"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), **PK)
    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"))
    url: Mapped[str] = mapped_column(String(500))
    position: Mapped[int] = mapped_column(Integer, server_default=text("0"))


class Inventory(Base):
    __tablename__ = "inventory"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), **PK)
    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), unique=True)
    quantity: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    reserved_quantity: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), **NOW)


class Order(Base):
    __tablename__ = "orders"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), **PK)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    address_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("addresses.id"))
    status: Mapped[str] = mapped_column(String(20), server_default=text("'pending'"))
    total_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), server_default=text("0"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), **NOW)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), **NOW)
    items: Mapped[list["OrderItem"]] = relationship(lazy="raise")


class OrderItem(Base):
    __tablename__ = "order_items"
    __table_args__ = (UniqueConstraint("order_id", "product_id", name="uq_order_items_order_product"),)
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), **PK)
    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"))
    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("products.id"))
    quantity: Mapped[int] = mapped_column(Integer)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    subtotal: Mapped[Decimal] = mapped_column(Numeric(10, 2), Computed("quantity * unit_price", persisted=True))


class Payment(Base):
    __tablename__ = "payments"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), **PK)
    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orders.id"), unique=True)
    method: Mapped[str] = mapped_column(String(30))
    status: Mapped[str] = mapped_column(String(20), server_default=text("'pending'"))
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    transaction_id: Mapped[Optional[str]] = mapped_column(String(100))
    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
