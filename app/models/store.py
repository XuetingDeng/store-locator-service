from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Numeric, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Store(Base):
    __tablename__ = "stores"
    __table_args__ = (
        CheckConstraint("store_type IN ('flagship', 'regular', 'outlet', 'express')"),
        CheckConstraint("status IN ('active', 'inactive', 'temporarily_closed')"),
        CheckConstraint("latitude BETWEEN -90 AND 90"),
        CheckConstraint("longitude BETWEEN -180 AND 180"),
        Index("idx_stores_latitude_longitude", "latitude", "longitude"),
        Index("idx_stores_status", "status"),
        Index("idx_stores_store_type", "store_type"),
        Index("idx_stores_address_postal_code", "address_postal_code"),
    )

    store_id: Mapped[str] = mapped_column(String(5), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    store_type: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    latitude: Mapped[Decimal] = mapped_column(Numeric(9, 6), nullable=False)
    longitude: Mapped[Decimal] = mapped_column(Numeric(9, 6), nullable=False)
    address_street: Mapped[str] = mapped_column(String(255), nullable=False)
    address_city: Mapped[str] = mapped_column(String(120), nullable=False)
    address_state: Mapped[str] = mapped_column(String(2), nullable=False)
    address_postal_code: Mapped[str] = mapped_column(String(5), nullable=False)
    address_country: Mapped[str] = mapped_column(String(3), nullable=False, default="USA")
    phone: Mapped[str] = mapped_column(String(12), nullable=False)
    hours: Mapped[dict[str, str]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    services: Mapped[list["StoreService"]] = relationship(back_populates="store", cascade="all, delete-orphan")


class Service(Base):
    __tablename__ = "services"

    service_key: Mapped[str] = mapped_column(String(32), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(80), nullable=False)

    stores: Mapped[list["StoreService"]] = relationship(back_populates="service")


class StoreService(Base):
    __tablename__ = "store_services"

    store_id: Mapped[str] = mapped_column(ForeignKey("stores.store_id", ondelete="CASCADE"), primary_key=True)
    service_key: Mapped[str] = mapped_column(ForeignKey("services.service_key"), primary_key=True)

    store: Mapped[Store] = relationship(back_populates="services")
    service: Mapped[Service] = relationship(back_populates="stores")
