import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import Field, model_validator

from app.schemas.common import ORMModel


class ProductoCreate(ORMModel):
    sku: str = Field(min_length=1, max_length=50)
    nombre: str = Field(min_length=2, max_length=150)
    descripcion: str | None = None
    categoria: str | None = Field(default=None, max_length=80)
    unidad_medida: str = Field(default="unidad", min_length=1, max_length=20)
    costo_promedio: Decimal = Field(default=Decimal("0"), ge=0)
    precio_venta: Decimal = Field(default=Decimal("0"), ge=0)
    stock_minimo: Decimal = Field(default=Decimal("0"), ge=0)


class ProductoUpdate(ORMModel):
    sku: str | None = Field(default=None, min_length=1, max_length=50)
    nombre: str | None = Field(default=None, min_length=2, max_length=150)
    descripcion: str | None = None
    categoria: str | None = Field(default=None, max_length=80)
    unidad_medida: str | None = Field(default=None, min_length=1, max_length=20)
    costo_promedio: Decimal | None = Field(default=None, ge=0)
    precio_venta: Decimal | None = Field(default=None, ge=0)


class InventarioRead(ORMModel):
    id: uuid.UUID
    sku: str
    nombre: str
    descripcion: str | None
    categoria: str | None
    unidad_medida: str
    costo_promedio: Decimal
    precio_venta: Decimal
    estado: str
    existencia_id: uuid.UUID | None
    sucursal_id: uuid.UUID
    stock_actual: Decimal
    stock_minimo: Decimal
    stock_maximo: Decimal | None


class MovimientoCreate(ORMModel):
    sucursal_id: uuid.UUID
    producto_id: uuid.UUID
    tipo: str = Field(pattern="^(entrada|salida|ajuste)$")
    cantidad: Decimal | None = Field(default=None, gt=0)
    stock_nuevo: Decimal | None = Field(default=None, ge=0)
    costo_unitario: Decimal = Field(default=Decimal("0"), ge=0)
    motivo: str = Field(min_length=2)

    @model_validator(mode="after")
    def validate_quantity(self) -> "MovimientoCreate":
        if self.tipo == "ajuste" and self.stock_nuevo is None:
            raise ValueError("Un ajuste requiere el stock nuevo")
        if self.tipo != "ajuste" and self.cantidad is None:
            raise ValueError("El movimiento requiere una cantidad")
        return self


class MovimientoRead(ORMModel):
    id: uuid.UUID
    tipo: str
    cantidad: Decimal
    costo_unitario: Decimal
    stock_anterior: Decimal
    stock_resultante: Decimal
    motivo: str | None
    created_at: datetime
    producto_nombre: str
    producto_sku: str
