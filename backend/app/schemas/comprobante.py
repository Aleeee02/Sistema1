import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import Field

from app.schemas.common import ORMModel


class ComprobanteCreate(ORMModel):
    orden_id: uuid.UUID
    tipo: str = Field(pattern="^(boleta|factura|nota_venta)$")
    observaciones: str | None = Field(default=None, max_length=500)


class ComprobanteAnular(ORMModel):
    motivo: str = Field(min_length=3, max_length=500)


class ComprobanteRead(ORMModel):
    id: uuid.UUID
    orden_id: uuid.UUID
    sucursal_id: uuid.UUID
    sucursal_nombre: str
    tipo: str
    serie: str
    numero: int
    estado: str
    cliente_nombre: str
    cliente_documento: str
    moneda: str
    total: Decimal
    emitido_at: datetime
    motivo_anulacion: str | None


class OrdenComprobanteOpcion(ORMModel):
    id: uuid.UUID
    numero: int
    sucursal_nombre: str
    cliente_nombre: str
    cliente_documento: str
    total: Decimal
