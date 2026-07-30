import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import Field

from app.schemas.common import ORMModel


class PagoCreate(ORMModel):
    orden_id: uuid.UUID
    metodo: str = Field(pattern="^(efectivo|tarjeta|transferencia|yape|plin|otro)$")
    monto: Decimal = Field(gt=0)
    referencia: str | None = Field(default=None, max_length=100)
    efectivo_confirmado: bool = False


class MetodoPagoConfigUpdate(ORMModel):
    metodo: str = Field(pattern="^(efectivo|tarjeta|transferencia|yape|plin|otro)$")
    activo: bool
    nombre_mostrar: str = Field(min_length=2, max_length=80)
    configuracion: dict = Field(default_factory=dict)


class MetodoPagoConfigRead(MetodoPagoConfigUpdate):
    id: uuid.UUID | None = None


class PagoAnular(ORMModel):
    motivo: str = Field(min_length=3)


class PagoRead(ORMModel):
    id: uuid.UUID
    sucursal_id: uuid.UUID
    sucursal_nombre: str
    orden_id: uuid.UUID
    orden_numero: int
    cliente_nombre: str
    vehiculo_placa: str
    numero: int
    metodo: str
    monto: Decimal
    moneda: str
    referencia: str | None
    estado: str
    motivo_anulacion: str | None
    anulado_at: datetime | None
    created_at: datetime


class CuentaCobrar(ORMModel):
    orden_id: uuid.UUID
    orden_numero: int
    sucursal_id: uuid.UUID
    sucursal_nombre: str
    cliente_nombre: str
    vehiculo_placa: str
    estado: str
    total: Decimal
    saldo: Decimal
