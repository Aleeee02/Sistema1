import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import UUIDPrimaryKeyMixin


class Empleado(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "empleados"

    empresa_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("empresas.id"))
    usuario_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("usuarios.id"))
    codigo: Mapped[str] = mapped_column(String(30))
    nombres: Mapped[str] = mapped_column(String(100))
    apellidos: Mapped[str] = mapped_column(String(100))
    cargo: Mapped[str] = mapped_column(String(50))
    especialidad: Mapped[str | None] = mapped_column(String(150))
    telefono: Mapped[str | None] = mapped_column(String(30))
    estado: Mapped[str] = mapped_column(String(20), server_default="activo")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EmpleadoSucursal(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "empleados_sucursales"

    empleado_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("empleados.id"))
    sucursal_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sucursales.id"))
    es_principal: Mapped[bool] = mapped_column(Boolean, server_default="false")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class OrdenEmpleado(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "ordenes_empleados"

    empresa_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("empresas.id"))
    orden_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("ordenes_trabajo.id"))
    empleado_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("empleados.id"))
    es_responsable: Mapped[bool] = mapped_column(Boolean, server_default="false")
    fecha_inicio: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    fecha_fin: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    observaciones: Mapped[str | None] = mapped_column(Text)
