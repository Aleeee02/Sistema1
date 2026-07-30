import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import UUIDPrimaryKeyMixin


class Cotizacion(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "cotizaciones"

    empresa_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("empresas.id"))
    orden_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("ordenes_trabajo.id"))
    numero: Mapped[int] = mapped_column()
    version: Mapped[int] = mapped_column(Integer, server_default="1")
    estado: Mapped[str] = mapped_column(String(20), server_default="borrador")
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2), server_default="0")
    descuento: Mapped[Decimal] = mapped_column(Numeric(12, 2), server_default="0")
    impuesto: Mapped[Decimal] = mapped_column(Numeric(12, 2), server_default="0")
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2), server_default="0")
    valida_hasta: Mapped[date | None] = mapped_column(Date)
    enviada_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    aprobada_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    aprobada_por: Mapped[str | None] = mapped_column(String(150))
    token_aprobacion: Mapped[str | None] = mapped_column(String(255))
    observaciones: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("usuarios.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CotizacionItem(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "cotizaciones_items"

    empresa_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("empresas.id"))
    cotizacion_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("cotizaciones.id"))
    tipo: Mapped[str] = mapped_column(String(20))
    servicio_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("servicios.id"))
    # La base mantiene esta FK. Se deja como UUID en el ORM hasta incorporar
    # el modelo Producto en el módulo de inventario.
    producto_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("productos.id"))
    descripcion: Mapped[str] = mapped_column(String(250))
    cantidad: Mapped[Decimal] = mapped_column(Numeric(10, 2), server_default="1")
    precio_unitario: Mapped[Decimal] = mapped_column(Numeric(12, 2), server_default="0")
    descuento: Mapped[Decimal] = mapped_column(Numeric(12, 2), server_default="0")
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2), server_default="0")
    orden_visual: Mapped[int] = mapped_column(Integer, server_default="0")
    origen: Mapped[str | None] = mapped_column(String(20))
    es_cobrable: Mapped[bool] = mapped_column(Boolean, server_default="true")
    proveedor_nombre: Mapped[str | None] = mapped_column(String(150))
    referencia_externa: Mapped[str | None] = mapped_column(String(100))
    responsable_garantia: Mapped[str | None] = mapped_column(String(20))
    recibido_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
