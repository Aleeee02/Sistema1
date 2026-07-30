import uuid
from datetime import datetime

from pydantic import Field

from app.schemas.common import ORMModel


class EmpleadoCreate(ORMModel):
    codigo: str = Field(min_length=1, max_length=30)
    nombres: str = Field(min_length=1, max_length=100)
    apellidos: str = Field(min_length=1, max_length=100)
    cargo: str = Field(min_length=1, max_length=50)
    especialidad: str | None = Field(default=None, max_length=150)
    telefono: str | None = Field(default=None, max_length=30)
    sucursal_id: uuid.UUID


class EmpleadoUpdate(ORMModel):
    codigo: str | None = Field(default=None, min_length=1, max_length=30)
    nombres: str | None = Field(default=None, min_length=1, max_length=100)
    apellidos: str | None = Field(default=None, min_length=1, max_length=100)
    cargo: str | None = Field(default=None, min_length=1, max_length=50)
    especialidad: str | None = Field(default=None, max_length=150)
    telefono: str | None = Field(default=None, max_length=30)


class EmpleadoRead(ORMModel):
    id: uuid.UUID
    codigo: str
    nombres: str
    apellidos: str
    cargo: str
    especialidad: str | None
    telefono: str | None
    estado: str
    created_at: datetime
    sucursal_id: uuid.UUID | None
    sucursal_nombre: str | None


class AsignacionCreate(ORMModel):
    orden_id: uuid.UUID
    empleado_id: uuid.UUID
    es_responsable: bool = False
    observaciones: str | None = None


class AsignacionRead(ORMModel):
    id: uuid.UUID
    orden_id: uuid.UUID
    empleado_id: uuid.UUID
    empleado_nombre: str
    cargo: str
    es_responsable: bool
    fecha_inicio: datetime
    observaciones: str | None
