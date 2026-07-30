import uuid
from datetime import datetime

from pydantic import Field

from app.schemas.common import ORMModel


class InspeccionItemCreate(ORMModel):
    codigo: str = Field(min_length=1, max_length=50)
    nombre: str = Field(min_length=2, max_length=150)
    estado: str = Field(pattern="^(bueno|regular|malo|no_aplica)$")
    observacion: str | None = None


class InspeccionCreate(ORMModel):
    orden_id: uuid.UUID
    tipo: str = Field(pattern="^(recepcion|diagnostico|entrega)$")
    kilometraje: int | None = Field(default=None, ge=0)
    nivel_combustible: int | None = Field(default=None, ge=0, le=100)
    observaciones: str | None = None
    items: list[InspeccionItemCreate] = Field(min_length=1)


class InspeccionItemRead(InspeccionItemCreate):
    id: uuid.UUID
    orden_visual: int


class ArchivoRead(ORMModel):
    id: uuid.UUID
    nombre_original: str
    mime_type: str | None
    tamano_bytes: int | None
    url: str | None
    created_at: datetime


class InspeccionRead(ORMModel):
    id: uuid.UUID
    orden_id: uuid.UUID
    tipo: str
    kilometraje: int | None
    nivel_combustible: int | None
    observaciones: str | None
    confirmada_at: datetime | None
    created_at: datetime
    items: list[InspeccionItemRead]
    archivos: list[ArchivoRead]


class InspeccionConfirmar(ORMModel):
    confirmar: bool = True
