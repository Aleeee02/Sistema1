import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, SmallInteger, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import UUIDPrimaryKeyMixin


class Inspeccion(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "inspecciones"
    empresa_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("empresas.id"))
    orden_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("ordenes_trabajo.id"))
    tipo: Mapped[str] = mapped_column(String(30))
    kilometraje: Mapped[int | None] = mapped_column(Integer)
    nivel_combustible: Mapped[int | None] = mapped_column(SmallInteger)
    observaciones: Mapped[str | None] = mapped_column(Text)
    firma_url: Mapped[str | None] = mapped_column(Text)
    confirmada_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    confirmada_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("usuarios.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class InspeccionItem(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "inspecciones_items"
    empresa_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("empresas.id"))
    inspeccion_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("inspecciones.id"))
    codigo: Mapped[str] = mapped_column(String(50))
    nombre: Mapped[str] = mapped_column(String(150))
    estado: Mapped[str] = mapped_column(String(30))
    observacion: Mapped[str | None] = mapped_column(Text)
    orden_visual: Mapped[int] = mapped_column(Integer, server_default="0")


class Archivo(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "archivos"
    empresa_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("empresas.id"))
    orden_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("ordenes_trabajo.id"))
    inspeccion_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("inspecciones.id"))
    cotizacion_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("cotizaciones.id"))
    tipo: Mapped[str] = mapped_column(String(30))
    nombre_original: Mapped[str] = mapped_column(String(255))
    storage_path: Mapped[str] = mapped_column(Text)
    mime_type: Mapped[str | None] = mapped_column(String(100))
    tamano_bytes: Mapped[int | None] = mapped_column(BigInteger)
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("usuarios.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
