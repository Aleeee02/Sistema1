import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import UUIDPrimaryKeyMixin


class Comprobante(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "comprobantes"

    empresa_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("empresas.id"))
    sucursal_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sucursales.id"))
    orden_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("ordenes_trabajo.id"))
    cliente_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("clientes.id"))
    tipo: Mapped[str] = mapped_column(String(20))
    serie: Mapped[str] = mapped_column(String(10))
    numero: Mapped[int] = mapped_column(BigInteger)
    estado: Mapped[str] = mapped_column(String(20), server_default="emitido")
    cliente_nombre: Mapped[str] = mapped_column(String(200))
    cliente_documento: Mapped[str] = mapped_column(String(20))
    cliente_direccion: Mapped[str | None] = mapped_column(Text)
    moneda: Mapped[str] = mapped_column(String(3), server_default="PEN")
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    descuento: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    impuesto: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    observaciones: Mapped[str | None] = mapped_column(Text)
    emitido_por: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("usuarios.id"))
    emitido_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    anulado_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    motivo_anulacion: Mapped[str | None] = mapped_column(Text)


class ComprobanteItem(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "comprobantes_items"

    empresa_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("empresas.id"))
    comprobante_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("comprobantes.id"))
    descripcion: Mapped[str] = mapped_column(String(250))
    cantidad: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    precio_unitario: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    descuento: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2))
