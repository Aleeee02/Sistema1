import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import Field

from app.schemas.common import ORMModel


class ServicioCreate(ORMModel):
    codigo: str = Field(min_length=1, max_length=30)
    nombre: str = Field(min_length=2, max_length=150)
    descripcion: str | None = None
    categoria: str | None = Field(default=None, max_length=80)
    precio_referencia: Decimal = Field(default=Decimal("0"), ge=0)
    duracion_minutos: int | None = Field(default=None, gt=0)


class ServicioUpdate(ORMModel):
    codigo: str | None = Field(default=None, min_length=1, max_length=30)
    nombre: str | None = Field(default=None, min_length=2, max_length=150)
    descripcion: str | None = None
    categoria: str | None = Field(default=None, max_length=80)
    precio_referencia: Decimal | None = Field(default=None, ge=0)
    duracion_minutos: int | None = Field(default=None, gt=0)


class ServicioRead(ORMModel):
    id: uuid.UUID
    codigo: str
    nombre: str
    descripcion: str | None
    categoria: str | None
    precio_referencia: Decimal
    duracion_minutos: int | None
    estado: str
    created_at: datetime
