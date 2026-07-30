import uuid
from datetime import datetime

from pydantic import EmailStr, Field, model_validator

from app.schemas.common import ORMModel


class ClienteBase(ORMModel):
    tipo_persona: str = Field(pattern="^(natural|juridica)$")
    tipo_documento: str = Field(min_length=1, max_length=10)
    numero_documento: str = Field(min_length=1, max_length=20)
    nombres: str | None = Field(default=None, max_length=150)
    apellidos: str | None = Field(default=None, max_length=150)
    razon_social: str | None = Field(default=None, max_length=200)
    telefono: str | None = Field(default=None, max_length=30)
    email: EmailStr | None = None
    direccion: str | None = None
    autoriza_contacto: bool = False
    observaciones: str | None = None

    @model_validator(mode="after")
    def validate_person_data(self) -> "ClienteBase":
        if self.tipo_persona == "natural" and not self.nombres:
            raise ValueError("Una persona natural requiere nombres")
        if self.tipo_persona == "juridica" and not self.razon_social:
            raise ValueError("Una persona jurídica requiere razón social")
        return self


class ClienteCreate(ClienteBase):
    pass


class ClienteUpdate(ORMModel):
    tipo_persona: str | None = Field(default=None, pattern="^(natural|juridica)$")
    tipo_documento: str | None = Field(default=None, min_length=1, max_length=10)
    numero_documento: str | None = Field(default=None, min_length=1, max_length=20)
    nombres: str | None = Field(default=None, max_length=150)
    apellidos: str | None = Field(default=None, max_length=150)
    razon_social: str | None = Field(default=None, max_length=200)
    telefono: str | None = Field(default=None, max_length=30)
    email: EmailStr | None = None
    direccion: str | None = None
    autoriza_contacto: bool | None = None
    observaciones: str | None = None


class ClienteRead(ClienteBase):
    id: uuid.UUID
    empresa_id: uuid.UUID
    estado: str
    created_at: datetime
    updated_at: datetime
