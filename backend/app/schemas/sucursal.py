import uuid
from datetime import datetime

from pydantic import Field

from app.schemas.common import ORMModel


class SucursalCreate(ORMModel):
    nombre: str = Field(min_length=2, max_length=100)
    codigo: str = Field(min_length=1, max_length=20)
    direccion: str | None = None
    telefono: str | None = Field(default=None, max_length=30)
    es_principal: bool = False


class SucursalUpdate(ORMModel):
    nombre: str | None = Field(default=None, min_length=2, max_length=100)
    codigo: str | None = Field(default=None, min_length=1, max_length=20)
    direccion: str | None = None
    telefono: str | None = Field(default=None, max_length=30)
    es_principal: bool | None = None


class SucursalRead(ORMModel):
    id: uuid.UUID
    empresa_id: uuid.UUID
    nombre: str
    codigo: str
    direccion: str | None
    telefono: str | None
    es_principal: bool
    estado: str
    created_at: datetime
    empleados_activos: int = 0
    ordenes_activas: int = 0
