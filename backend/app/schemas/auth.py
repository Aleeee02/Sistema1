import uuid

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    empresa_id: uuid.UUID | None = None


class RefreshRequest(BaseModel):
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    password_actual: str = Field(min_length=8, max_length=128)
    password_nueva: str = Field(min_length=8, max_length=128)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ForgotPasswordResponse(BaseModel):
    mensaje: str
    recovery_token: str | None = None


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=32, max_length=512)
    password_nueva: str = Field(min_length=8, max_length=128)


class EmpresaSesion(BaseModel):
    id: uuid.UUID
    nombre: str
    rol: str
    logo_url: str | None = None
    color_primario: str = "#2563EB"


class UsuarioSesion(BaseModel):
    id: uuid.UUID
    email: EmailStr
    nombres: str
    apellidos: str
    empresa: EmpresaSesion
    permisos: list[str]
    es_superadmin: bool = False


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    usuario: UsuarioSesion
