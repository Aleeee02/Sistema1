import uuid

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Cliente(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "clientes"

    empresa_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("empresas.id")
    )
    tipo_persona: Mapped[str] = mapped_column(String(20))
    tipo_documento: Mapped[str] = mapped_column(String(10))
    numero_documento: Mapped[str] = mapped_column(String(20))
    nombres: Mapped[str | None] = mapped_column(String(150))
    apellidos: Mapped[str | None] = mapped_column(String(150))
    razon_social: Mapped[str | None] = mapped_column(String(200))
    telefono: Mapped[str | None] = mapped_column(String(30))
    email: Mapped[str | None] = mapped_column(String(255))
    direccion: Mapped[str | None] = mapped_column(Text)
    autoriza_contacto: Mapped[bool] = mapped_column(Boolean, server_default="false")
    observaciones: Mapped[str | None] = mapped_column(Text)
    estado: Mapped[str] = mapped_column(String(20), server_default="activo")

