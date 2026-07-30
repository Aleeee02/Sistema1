import uuid
from datetime import date, datetime

from pydantic import EmailStr, Field
from decimal import Decimal

from app.schemas.common import ORMModel


class EmpresaPlataformaCreate(ORMModel):
    nombre_comercial: str = Field(min_length=2, max_length=150)
    razon_social: str = Field(min_length=2, max_length=200)
    ruc: str = Field(pattern=r"^\d{11}$")
    email: EmailStr | None = None
    telefono: str | None = Field(default=None, max_length=30)
    plan_codigo: str = Field(default="basico", pattern="^(basico|profesional|empresarial)$")
    suscripcion_fin: date | None = None
    max_usuarios: int = Field(default=5, ge=1, le=10000)
    max_sucursales: int = Field(default=1, ge=1, le=1000)
    admin_email: EmailStr
    admin_password: str = Field(min_length=8, max_length=128)
    admin_nombres: str = Field(min_length=2, max_length=100)
    admin_apellidos: str = Field(min_length=2, max_length=100)


class EmpresaPlataformaUpdate(ORMModel):
    nombre_comercial: str | None = Field(default=None, min_length=2, max_length=150)
    razon_social: str | None = Field(default=None, min_length=2, max_length=200)
    email: EmailStr | None = None
    telefono: str | None = Field(default=None, max_length=30)
    estado: str | None = Field(default=None, pattern="^(activo|suspendido|inactivo)$")
    plan_codigo: str | None = Field(default=None, pattern="^(basico|profesional|empresarial)$")
    suscripcion_estado: str | None = Field(default=None, pattern="^(prueba|activa|vencida|cancelada)$")
    suscripcion_fin: date | None = None
    max_usuarios: int | None = Field(default=None, ge=1, le=10000)
    max_sucursales: int | None = Field(default=None, ge=1, le=1000)
    notas_internas: str | None = Field(default=None, max_length=2000)


class EmpresaPlataformaRead(ORMModel):
    id: uuid.UUID
    nombre_comercial: str
    razon_social: str
    ruc: str
    email: str | None
    telefono: str | None
    estado: str
    plan_codigo: str
    suscripcion_estado: str
    suscripcion_inicio: date
    suscripcion_fin: date | None
    max_usuarios: int
    max_sucursales: int
    notas_internas: str | None
    usuarios_activos: int
    sucursales_activas: int
    ordenes_total: int
    created_at: datetime


class ResumenPlataforma(ORMModel):
    empresas_total: int
    empresas_activas: int
    empresas_prueba: int
    empresas_vencidas: int
    usuarios_activos: int


class PlanSaaSRead(ORMModel):
    id: uuid.UUID
    codigo: str
    nombre: str
    descripcion: str | None
    precio_mensual: Decimal
    max_usuarios: int
    max_sucursales: int
    modulos: list[str]
    estado: str


class PlanSaaSUpdate(ORMModel):
    nombre: str | None = Field(default=None, min_length=2, max_length=80)
    descripcion: str | None = Field(default=None, max_length=500)
    precio_mensual: Decimal | None = Field(default=None, ge=0)
    max_usuarios: int | None = Field(default=None, ge=1, le=10000)
    max_sucursales: int | None = Field(default=None, ge=1, le=1000)
    modulos: list[str] | None = None
    estado: str | None = Field(default=None, pattern="^(activo|inactivo)$")
