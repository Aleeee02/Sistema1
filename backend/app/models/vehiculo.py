import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, SmallInteger, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Vehiculo(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "vehiculos"

    empresa_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("empresas.id")
    )
    placa: Mapped[str] = mapped_column(String(15))
    vin: Mapped[str | None] = mapped_column(String(50))
    marca: Mapped[str | None] = mapped_column(String(80))
    modelo: Mapped[str | None] = mapped_column(String(80))
    anio: Mapped[int | None] = mapped_column(SmallInteger)
    color: Mapped[str | None] = mapped_column(String(50))
    combustible: Mapped[str | None] = mapped_column(String(30))
    motor: Mapped[str | None] = mapped_column(String(100))
    cilindrada: Mapped[str | None] = mapped_column(String(30))
    estado: Mapped[str] = mapped_column(String(20), server_default="activo")


class VehiculoCliente(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "vehiculos_clientes"

    empresa_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("empresas.id")
    )
    vehiculo_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("vehiculos.id")
    )
    cliente_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clientes.id")
    )
    fecha_inicio: Mapped[date] = mapped_column(Date, server_default=func.current_date())
    fecha_fin: Mapped[date | None] = mapped_column(Date)
    es_actual: Mapped[bool] = mapped_column(Boolean, server_default="true")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
