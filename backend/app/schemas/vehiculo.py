import uuid
from datetime import datetime

from pydantic import Field, field_validator

from app.schemas.common import ORMModel


def normalize_plate(value: str) -> str:
    return value.strip().upper().replace(" ", "")


class VehiculoBase(ORMModel):
    placa: str = Field(min_length=3, max_length=15)
    vin: str | None = Field(default=None, max_length=50)
    marca: str | None = Field(default=None, max_length=80)
    modelo: str | None = Field(default=None, max_length=80)
    anio: int | None = Field(default=None, ge=1900, le=2100)
    color: str | None = Field(default=None, max_length=50)
    combustible: str | None = Field(default=None, max_length=30)
    motor: str | None = Field(default=None, max_length=100)
    cilindrada: str | None = Field(default=None, max_length=30)

    @field_validator("placa")
    @classmethod
    def validate_plate(cls, value: str) -> str:
        return normalize_plate(value)

    @field_validator("vin")
    @classmethod
    def normalize_vin(cls, value: str | None) -> str | None:
        return value.strip().upper() if value else None


class VehiculoCreate(VehiculoBase):
    pass


class VehiculoUpdate(ORMModel):
    placa: str | None = Field(default=None, min_length=3, max_length=15)
    vin: str | None = Field(default=None, max_length=50)
    marca: str | None = Field(default=None, max_length=80)
    modelo: str | None = Field(default=None, max_length=80)
    anio: int | None = Field(default=None, ge=1900, le=2100)
    color: str | None = Field(default=None, max_length=50)
    combustible: str | None = Field(default=None, max_length=30)
    motor: str | None = Field(default=None, max_length=100)
    cilindrada: str | None = Field(default=None, max_length=30)

    @field_validator("placa")
    @classmethod
    def validate_plate(cls, value: str | None) -> str | None:
        return normalize_plate(value) if value else None

    @field_validator("vin")
    @classmethod
    def normalize_vin(cls, value: str | None) -> str | None:
        return value.strip().upper() if value else None


class VehiculoRead(VehiculoBase):
    id: uuid.UUID
    empresa_id: uuid.UUID
    estado: str
    created_at: datetime
    updated_at: datetime


class CambiarPropietarioRequest(ORMModel):
    cliente_id: uuid.UUID
