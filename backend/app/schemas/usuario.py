import uuid
from datetime import datetime

from pydantic import EmailStr, Field

from app.schemas.common import ORMModel


class RolRead(ORMModel):
    id: uuid.UUID
    codigo: str
    nombre: str
    descripcion: str | None
    empresa_id: uuid.UUID | None = None
    es_sistema: bool = True
    estado: str = "activo"


class RolDetalle(RolRead):
    permisos: list[str]
    usuarios_asignados: int = 0


class RolCreate(ORMModel):
    nombre: str = Field(min_length=2, max_length=80)
    descripcion: str | None = Field(default=None, max_length=500)
    permisos: list[str] = Field(default_factory=list)


class RolUpdate(ORMModel):
    nombre: str | None = Field(default=None, min_length=2, max_length=80)
    descripcion: str | None = Field(default=None, max_length=500)
    permisos: list[str] | None = None


class PermisoOpcion(ORMModel):
    codigo: str
    modulo: str
    nombre: str


class UsuarioEmpresaCreate(ORMModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    nombres: str = Field(min_length=2, max_length=100)
    apellidos: str = Field(min_length=2, max_length=100)
    telefono: str | None = Field(default=None, max_length=30)
    rol_id: uuid.UUID
    sucursal_ids: list[uuid.UUID] = Field(default_factory=list)


class UsuarioEmpresaUpdate(ORMModel):
    nombres: str | None = Field(default=None, min_length=2, max_length=100)
    apellidos: str | None = Field(default=None, min_length=2, max_length=100)
    telefono: str | None = Field(default=None, max_length=30)
    rol_id: uuid.UUID | None = None
    sucursal_ids: list[uuid.UUID] | None = None
    estado: str | None = Field(default=None, pattern="^(activo|inactivo|suspendido)$")


class UsuarioEmpresaRead(ORMModel):
    id: uuid.UUID
    membresia_id: uuid.UUID
    email: EmailStr
    nombres: str
    apellidos: str
    telefono: str | None
    rol_id: uuid.UUID
    rol_codigo: str
    rol_nombre: str
    estado: str
    ultimo_acceso_at: datetime | None
    sucursal_ids: list[uuid.UUID]
    sucursal_nombres: list[str]
    created_at: datetime


class UsuariosOpciones(ORMModel):
    roles: list[RolRead]
