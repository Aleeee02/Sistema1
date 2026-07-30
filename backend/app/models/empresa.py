import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Empresa(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "empresas"

    nombre_comercial: Mapped[str] = mapped_column(String(150))
    razon_social: Mapped[str] = mapped_column(String(200))
    ruc: Mapped[str] = mapped_column(String(11))
    logo_url: Mapped[str | None] = mapped_column(Text)
    direccion_fiscal: Mapped[str | None] = mapped_column(Text)
    telefono: Mapped[str | None] = mapped_column(String(30))
    email: Mapped[str | None] = mapped_column(String(255))
    sitio_web: Mapped[str | None] = mapped_column(String(255))
    color_primario: Mapped[str] = mapped_column(String(7), server_default="#2563EB")
    prefijo_orden: Mapped[str] = mapped_column(String(10), server_default="OT")
    prefijo_cotizacion: Mapped[str] = mapped_column(String(10), server_default="COT")
    moneda: Mapped[str] = mapped_column(String(3), server_default="PEN")
    porcentaje_impuesto: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), server_default="18.00"
    )
    zona_horaria: Mapped[str] = mapped_column(
        String(50), server_default="America/Lima"
    )
    estado: Mapped[str] = mapped_column(String(20), server_default="activo")


class Sucursal(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "sucursales"

    empresa_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("empresas.id")
    )
    nombre: Mapped[str] = mapped_column(String(100))
    codigo: Mapped[str] = mapped_column(String(20))
    direccion: Mapped[str | None] = mapped_column(Text)
    telefono: Mapped[str | None] = mapped_column(String(30))
    es_principal: Mapped[bool] = mapped_column(Boolean, server_default="false")
    estado: Mapped[str] = mapped_column(String(20), server_default="activo")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
