import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import Field, model_validator

from app.schemas.common import ORMModel

ESTADOS_ORDEN = (
    "borrador",
    "recepcion",
    "diagnostico",
    "esperando_aprobacion",
    "aprobada",
    "en_proceso",
    "terminada",
    "entregada",
    "cancelada",
)


class OrdenCreate(ORMModel):
    sucursal_id: uuid.UUID
    cliente_id: uuid.UUID
    vehiculo_id: uuid.UUID
    kilometraje: int | None = Field(default=None, ge=0)
    nivel_combustible: int | None = Field(default=None, ge=0, le=100)
    falla_reportada: str = Field(min_length=3)
    observaciones: str | None = None
    fecha_estimada_entrega: datetime | None = None


class OrdenUpdate(ORMModel):
    kilometraje: int | None = Field(default=None, ge=0)
    nivel_combustible: int | None = Field(default=None, ge=0, le=100)
    falla_reportada: str | None = Field(default=None, min_length=3)
    diagnostico: str | None = None
    observaciones: str | None = None
    fecha_estimada_entrega: datetime | None = None


class OrdenEstadoUpdate(ORMModel):
    estado: str

    @model_validator(mode="after")
    def validate_estado(self) -> "OrdenEstadoUpdate":
        if self.estado not in ESTADOS_ORDEN:
            raise ValueError("Estado de orden inválido")
        return self


class OrdenRead(ORMModel):
    id: uuid.UUID
    empresa_id: uuid.UUID
    sucursal_id: uuid.UUID
    numero: int
    cliente_id: uuid.UUID
    vehiculo_id: uuid.UUID
    estado: str
    kilometraje: int | None
    nivel_combustible: int | None
    falla_reportada: str | None
    diagnostico: str | None
    observaciones: str | None
    subtotal: Decimal
    descuento: Decimal
    impuesto: Decimal
    total: Decimal
    saldo: Decimal
    fecha_recepcion: datetime
    fecha_estimada_entrega: datetime | None
    fecha_entrega: datetime | None
    created_at: datetime
    updated_at: datetime
    cliente_nombre: str
    cliente_documento: str
    vehiculo_placa: str
    vehiculo_descripcion: str
    sucursal_nombre: str


class SucursalOption(ORMModel):
    id: uuid.UUID
    nombre: str
    es_principal: bool


class OrdenOptions(ORMModel):
    sucursales: list[SucursalOption]
