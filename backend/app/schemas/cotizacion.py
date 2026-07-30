import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import Field, model_validator

from app.schemas.common import ORMModel


class CotizacionItemCreate(ORMModel):
    clase: str = Field(pattern="^(servicio|inventario|cliente|proveedor)$")
    descripcion: str = Field(min_length=2, max_length=250)
    cantidad: Decimal = Field(gt=0)
    precio_unitario: Decimal = Field(default=Decimal("0"), ge=0)
    descuento: Decimal = Field(default=Decimal("0"), ge=0)
    producto_id: uuid.UUID | None = None
    servicio_id: uuid.UUID | None = None
    proveedor_nombre: str | None = Field(default=None, max_length=150)
    referencia_externa: str | None = Field(default=None, max_length=100)
    responsable_garantia: str | None = Field(
        default=None, pattern="^(taller|cliente|proveedor)$"
    )

    @model_validator(mode="after")
    def validate_origin(self) -> "CotizacionItemCreate":
        if self.clase == "inventario" and not self.producto_id:
            raise ValueError("Selecciona un producto del inventario")
        if self.clase != "inventario" and self.producto_id:
            raise ValueError("Solo el inventario puede referenciar un producto")
        if self.clase == "servicio" and not self.servicio_id:
            raise ValueError("Selecciona un servicio del catálogo")
        if self.clase != "servicio" and self.servicio_id:
            raise ValueError("Servicio inválido para este tipo de concepto")
        if self.clase == "proveedor" and not self.proveedor_nombre:
            raise ValueError("Indica el proveedor")
        if self.clase == "cliente" and (
            self.precio_unitario != 0 or self.descuento != 0
        ):
            raise ValueError("Los repuestos del cliente no son cobrables")
        return self


class CotizacionCreate(ORMModel):
    orden_id: uuid.UUID
    valida_hasta: date | None = None
    descuento: Decimal = Field(default=Decimal("0"), ge=0)
    observaciones: str | None = None
    items: list[CotizacionItemCreate] = Field(min_length=1)

    @model_validator(mode="after")
    def require_service(self) -> "CotizacionCreate":
        if not any(item.clase == "servicio" for item in self.items):
            raise ValueError("La cotización debe incluir al menos un servicio de mano de obra")
        return self


class CotizacionEstadoUpdate(ORMModel):
    estado: str = Field(pattern="^(enviada|aprobada|rechazada)$")
    aprobada_por: str | None = Field(default=None, max_length=150)


class CotizacionItemRead(ORMModel):
    id: uuid.UUID
    tipo: str
    producto_id: uuid.UUID | None
    servicio_id: uuid.UUID | None
    descripcion: str
    cantidad: Decimal
    precio_unitario: Decimal
    descuento: Decimal
    total: Decimal
    orden_visual: int
    origen: str | None
    es_cobrable: bool
    proveedor_nombre: str | None
    referencia_externa: str | None
    responsable_garantia: str | None
    recibido_at: datetime | None
    reserva_id: uuid.UUID | None = None
    reserva_estado: str | None = None


class CotizacionRead(ORMModel):
    id: uuid.UUID
    orden_id: uuid.UUID
    numero: int
    version: int
    estado: str
    subtotal: Decimal
    descuento: Decimal
    impuesto: Decimal
    total: Decimal
    valida_hasta: date | None
    enviada_at: datetime | None
    aprobada_at: datetime | None
    aprobada_por: str | None
    observaciones: str | None
    created_at: datetime
    orden_numero: int
    cliente_nombre: str
    vehiculo_placa: str
    items: list[CotizacionItemRead] = Field(default_factory=list)


class ProductoCotizable(ORMModel):
    id: uuid.UUID
    sku: str
    nombre: str
    unidad_medida: str
    precio_venta: Decimal
    stock_actual: Decimal
    stock_reservado: Decimal
    stock_disponible: Decimal


class ServicioCotizable(ORMModel):
    id: uuid.UUID
    codigo: str
    nombre: str
    categoria: str | None
    precio_referencia: Decimal
    duracion_minutos: int | None


class CotizacionOpciones(ORMModel):
    sucursal_id: uuid.UUID
    productos: list[ProductoCotizable]
    servicios: list[ServicioCotizable]
