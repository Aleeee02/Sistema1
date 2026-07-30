import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import UUIDPrimaryKeyMixin


class Pago(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "pagos"

    empresa_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("empresas.id"))
    sucursal_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sucursales.id"))
    orden_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("ordenes_trabajo.id"))
    numero: Mapped[int] = mapped_column(BigInteger)
    metodo: Mapped[str] = mapped_column(String(30))
    monto: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    moneda: Mapped[str] = mapped_column(String(3), server_default="PEN")
    referencia: Mapped[str | None] = mapped_column(String(100))
    estado: Mapped[str] = mapped_column(String(20), server_default="confirmado")
    motivo_anulacion: Mapped[str | None] = mapped_column(Text)
    anulado_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    anulado_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("usuarios.id"))
    registrado_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("usuarios.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class MetodoPagoConfig(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "metodos_pago_config"

    empresa_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("empresas.id"))
    metodo: Mapped[str] = mapped_column(String(30))
    activo: Mapped[bool] = mapped_column(Boolean, server_default="true")
    nombre_mostrar: Mapped[str] = mapped_column(String(80))
    configuracion: Mapped[dict] = mapped_column(JSONB, server_default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
