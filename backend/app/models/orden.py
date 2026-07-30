import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, Numeric, SmallInteger, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class OrdenTrabajo(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "ordenes_trabajo"

    empresa_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("empresas.id")
    )
    sucursal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sucursales.id")
    )
    numero: Mapped[int] = mapped_column(BigInteger)
    cliente_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clientes.id")
    )
    vehiculo_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("vehiculos.id")
    )
    cita_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    bahia_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    estado: Mapped[str] = mapped_column(String(30), server_default="borrador")
    kilometraje: Mapped[int | None] = mapped_column(Integer)
    nivel_combustible: Mapped[int | None] = mapped_column(SmallInteger)
    falla_reportada: Mapped[str | None] = mapped_column(Text)
    diagnostico: Mapped[str | None] = mapped_column(Text)
    observaciones: Mapped[str | None] = mapped_column(Text)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2), server_default="0")
    descuento: Mapped[Decimal] = mapped_column(Numeric(12, 2), server_default="0")
    impuesto: Mapped[Decimal] = mapped_column(Numeric(12, 2), server_default="0")
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2), server_default="0")
    saldo: Mapped[Decimal] = mapped_column(Numeric(12, 2), server_default="0")
    fecha_recepcion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    fecha_estimada_entrega: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    fecha_entrega: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))


class Servicio(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "servicios"

    empresa_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("empresas.id")
    )
    codigo: Mapped[str] = mapped_column(String(30))
    nombre: Mapped[str] = mapped_column(String(150))
    descripcion: Mapped[str | None] = mapped_column(Text)
    categoria: Mapped[str | None] = mapped_column(String(80))
    precio_referencia: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), server_default="0"
    )
    duracion_minutos: Mapped[int | None] = mapped_column(Integer)
    estado: Mapped[str] = mapped_column(String(20), server_default="activo")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class OrdenEstadoHistorial(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "ordenes_estados_historial"

    empresa_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("empresas.id"))
    orden_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("ordenes_trabajo.id"))
    estado_anterior: Mapped[str | None] = mapped_column(String(30))
    estado_nuevo: Mapped[str] = mapped_column(String(30))
    motivo: Mapped[str | None] = mapped_column(Text)
    usuario_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("usuarios.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class OrdenServicio(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "ordenes_servicios"

    empresa_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("empresas.id"))
    orden_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("ordenes_trabajo.id"))
    servicio_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("servicios.id"))
    descripcion: Mapped[str] = mapped_column(String(250))
    cantidad: Mapped[Decimal] = mapped_column(Numeric(10, 2), server_default="1")
    precio_unitario: Mapped[Decimal] = mapped_column(Numeric(12, 2), server_default="0")
    descuento: Mapped[Decimal] = mapped_column(Numeric(12, 2), server_default="0")
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2), server_default="0")
    estado: Mapped[str] = mapped_column(String(20), server_default="pendiente")
