import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Producto(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "productos"

    empresa_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("empresas.id"))
    sku: Mapped[str] = mapped_column(String(50))
    nombre: Mapped[str] = mapped_column(String(150))
    descripcion: Mapped[str | None] = mapped_column(Text)
    categoria: Mapped[str | None] = mapped_column(String(80))
    unidad_medida: Mapped[str] = mapped_column(String(20), server_default="unidad")
    costo_promedio: Mapped[Decimal] = mapped_column(Numeric(12, 2), server_default="0")
    precio_venta: Mapped[Decimal] = mapped_column(Numeric(12, 2), server_default="0")
    estado: Mapped[str] = mapped_column(String(20), server_default="activo")


class Existencia(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "existencias"

    empresa_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("empresas.id"))
    sucursal_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sucursales.id"))
    producto_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("productos.id"))
    stock_actual: Mapped[Decimal] = mapped_column(Numeric(12, 2), server_default="0")
    stock_minimo: Mapped[Decimal] = mapped_column(Numeric(12, 2), server_default="0")
    stock_maximo: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class MovimientoInventario(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "movimientos_inventario"

    empresa_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("empresas.id"))
    existencia_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("existencias.id"))
    orden_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("ordenes_trabajo.id"))
    tipo: Mapped[str] = mapped_column(String(20))
    cantidad: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    costo_unitario: Mapped[Decimal] = mapped_column(Numeric(12, 2), server_default="0")
    stock_anterior: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    stock_resultante: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    motivo: Mapped[str | None] = mapped_column(Text)
    movimiento_origen_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("movimientos_inventario.id"))
    usuario_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("usuarios.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ReservaInventario(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "reservas_inventario"

    empresa_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("empresas.id"))
    sucursal_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sucursales.id"))
    producto_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("productos.id"))
    cotizacion_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("cotizaciones.id"))
    cotizacion_item_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("cotizaciones_items.id"))
    orden_trabajo_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("ordenes_trabajo.id"))
    cantidad: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    estado: Mapped[str] = mapped_column(String(20), server_default="activa")
    reservada_por: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("usuarios.id"))
    fecha_reserva: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    fecha_liberacion: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    fecha_consumo: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    observaciones: Mapped[str | None] = mapped_column(Text)


class TransferenciaInventario(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "transferencias_inventario"

    empresa_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("empresas.id"))
    sucursal_origen_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sucursales.id"))
    sucursal_destino_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sucursales.id"))
    estado: Mapped[str] = mapped_column(String(30), server_default="solicitada")
    solicitada_por: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("usuarios.id"))
    aprobada_por: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("usuarios.id"))
    despachada_por: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("usuarios.id"))
    recibida_por: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("usuarios.id"))
    fecha_solicitud: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    fecha_aprobacion: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    fecha_despacho: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    fecha_recepcion: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    observaciones: Mapped[str | None] = mapped_column(Text)


class TransferenciaInventarioItem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "transferencias_inventario_items"

    empresa_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("empresas.id"))
    transferencia_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("transferencias_inventario.id"))
    producto_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("productos.id"))
    cantidad_solicitada: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    cantidad_despachada: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    cantidad_recibida: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    observaciones: Mapped[str | None] = mapped_column(Text)
