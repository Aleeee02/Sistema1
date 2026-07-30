import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import Field

from app.schemas.common import ORMModel


class TransferenciaItemCreate(ORMModel):
    producto_id: uuid.UUID
    cantidad: Decimal = Field(gt=0)
    observaciones: str | None = None


class TransferenciaCreate(ORMModel):
    sucursal_origen_id: uuid.UUID
    sucursal_destino_id: uuid.UUID
    observaciones: str | None = None
    items: list[TransferenciaItemCreate] = Field(min_length=1)


class TransferenciaEstado(ORMModel):
    estado: str = Field(pattern="^(aprobada|en_transito|recibida|rechazada|cancelada)$")


class TransferenciaItemRead(ORMModel):
    id: uuid.UUID
    producto_id: uuid.UUID
    producto_sku: str
    producto_nombre: str
    unidad_medida: str
    cantidad_solicitada: Decimal
    cantidad_despachada: Decimal | None
    cantidad_recibida: Decimal | None
    observaciones: str | None


class TransferenciaRead(ORMModel):
    id: uuid.UUID
    estado: str
    sucursal_origen_id: uuid.UUID
    sucursal_origen_nombre: str
    sucursal_destino_id: uuid.UUID
    sucursal_destino_nombre: str
    fecha_solicitud: datetime
    fecha_aprobacion: datetime | None
    fecha_despacho: datetime | None
    fecha_recepcion: datetime | None
    observaciones: str | None
    items: list[TransferenciaItemRead]
