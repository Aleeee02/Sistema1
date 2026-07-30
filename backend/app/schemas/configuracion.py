from decimal import Decimal

from pydantic import EmailStr, Field, HttpUrl

from app.schemas.common import ORMModel


class EmpresaConfigRead(ORMModel):
    nombre_comercial: str
    razon_social: str
    ruc: str
    logo_url: str | None
    direccion_fiscal: str | None
    telefono: str | None
    email: str | None
    sitio_web: str | None
    color_primario: str
    moneda: str
    porcentaje_impuesto: Decimal
    zona_horaria: str
    prefijo_orden: str
    prefijo_cotizacion: str


class EmpresaConfigUpdate(ORMModel):
    nombre_comercial: str = Field(min_length=2, max_length=150)
    razon_social: str = Field(min_length=2, max_length=200)
    ruc: str = Field(pattern=r"^\d{11}$")
    logo_url: str | None = Field(default=None, max_length=1000)
    direccion_fiscal: str | None = Field(default=None, max_length=500)
    telefono: str | None = Field(default=None, max_length=30)
    email: EmailStr | None = None
    sitio_web: str | None = Field(default=None, max_length=255)
    color_primario: str = Field(pattern=r"^#[0-9A-Fa-f]{6}$")
    moneda: str = Field(pattern=r"^[A-Z]{3}$")
    porcentaje_impuesto: Decimal = Field(ge=0, le=100)
    zona_horaria: str = Field(min_length=3, max_length=50)
    prefijo_orden: str = Field(min_length=1, max_length=10, pattern=r"^[A-Za-z0-9-]+$")
    prefijo_cotizacion: str = Field(min_length=1, max_length=10, pattern=r"^[A-Za-z0-9-]+$")
