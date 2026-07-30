import uuid
from datetime import datetime

from pydantic import Field, model_validator

from app.schemas.common import ORMModel


class BahiaCreate(ORMModel):
    sucursal_id: uuid.UUID
    nombre: str = Field(min_length=2, max_length=80)
    codigo: str = Field(min_length=1, max_length=20)
    descripcion: str | None = None


class BahiaUpdate(ORMModel):
    nombre: str | None = Field(default=None, min_length=2, max_length=80)
    codigo: str | None = Field(default=None, min_length=1, max_length=20)
    descripcion: str | None = None
    estado: str | None = Field(default=None, pattern="^(activo|inactivo|mantenimiento)$")


class BahiaRead(ORMModel):
    id: uuid.UUID
    sucursal_id: uuid.UUID
    sucursal_nombre: str
    nombre: str
    codigo: str
    descripcion: str | None
    estado: str
    created_at: datetime


class CitaCreate(ORMModel):
    sucursal_id: uuid.UUID
    cliente_id: uuid.UUID
    vehiculo_id: uuid.UUID
    bahia_id: uuid.UUID | None = None
    empleado_id: uuid.UUID | None = None
    fecha_inicio: datetime
    fecha_fin: datetime
    motivo: str = Field(min_length=3)
    observaciones: str | None = None

    @model_validator(mode="after")
    def valid_dates(self):
        if self.fecha_fin <= self.fecha_inicio:
            raise ValueError("La hora de fin debe ser posterior al inicio")
        return self


class CitaEstadoUpdate(ORMModel):
    estado: str = Field(pattern="^(programada|confirmada|atendida|cancelada|no_asistio)$")


class CitaRead(ORMModel):
    id: uuid.UUID
    sucursal_id: uuid.UUID
    sucursal_nombre: str
    cliente_id: uuid.UUID
    cliente_nombre: str
    vehiculo_id: uuid.UUID
    vehiculo_placa: str
    vehiculo_descripcion: str
    bahia_id: uuid.UUID | None
    bahia_nombre: str | None
    empleado_id: uuid.UUID | None
    empleado_nombre: str | None
    fecha_inicio: datetime
    fecha_fin: datetime
    motivo: str
    estado: str
    observaciones: str | None
    created_at: datetime


class AgendaVehiculo(ORMModel):
    id: uuid.UUID
    cliente_id: uuid.UUID
    placa: str
    descripcion: str


class AgendaCliente(ORMModel):
    id: uuid.UUID
    nombre: str


class AgendaEmpleado(ORMModel):
    id: uuid.UUID
    sucursal_id: uuid.UUID
    nombre: str


class AgendaOpciones(ORMModel):
    clientes: list[AgendaCliente]
    vehiculos: list[AgendaVehiculo]
    empleados: list[AgendaEmpleado]
