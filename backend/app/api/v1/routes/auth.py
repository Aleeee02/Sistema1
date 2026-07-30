import uuid
import hashlib
import logging
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import AuthContext, get_current_context
from app.core.config import settings
from app.core.permissions import ACTION_PERMISSIONS, visible_permissions
from app.core.security import (
    create_password_reset_token,
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
    hash_password,
)
from app.db.session import get_db
from app.models.empresa import Empresa
from app.models.usuario import PasswordResetToken, Rol, Usuario, UsuarioEmpresa
from app.schemas.auth import (
    EmpresaSesion,
    ChangePasswordRequest,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    LoginRequest,
    RefreshRequest,
    ResetPasswordRequest,
    TokenResponse,
    UsuarioSesion,
)
from app.services.email import send_password_reset_email

router = APIRouter(prefix="/auth", tags=["autenticación"])
logger = logging.getLogger(__name__)

ALL_PERMISSIONS = {
    f"{module}.{action}"
    for module in (
        "dashboard", "agenda", "clientes", "vehiculos", "ordenes",
        "cotizaciones", "inspecciones", "pagos", "servicios", "inventario",
        "transferencias", "empleados", "sucursales", "usuarios",
        "estadisticas", "reportes", "configuracion", "comprobantes", "auditoria",
    )
    for action in ("ver", "gestionar")
}
ALL_PERMISSIONS.update(ACTION_PERMISSIONS)


def build_user_response(
    usuario: Usuario,
    empresa: Empresa,
    rol: Rol,
    custom_permissions: set[str] | frozenset[str] = frozenset(),
) -> UsuarioSesion:
    return UsuarioSesion(
        id=usuario.id,
        email=usuario.email,
        nombres=usuario.nombres,
        apellidos=usuario.apellidos,
        permisos=sorted(set(visible_permissions(rol.codigo, ALL_PERMISSIONS)) | set(custom_permissions)),
        empresa=EmpresaSesion(
            id=empresa.id,
            nombre=empresa.nombre_comercial,
            rol=rol.codigo,
            logo_url=empresa.logo_url,
            color_primario=empresa.color_primario,
        ),
    )


def issue_tokens(
    usuario: Usuario,
    membresia: UsuarioEmpresa,
    empresa: Empresa,
    rol: Rol,
) -> TokenResponse:
    claims = {
        "empresa_id": str(empresa.id),
        "membresia_id": str(membresia.id),
        "rol": rol.codigo,
    }
    return TokenResponse(
        access_token=create_access_token(str(usuario.id), claims),
        refresh_token=create_refresh_token(str(usuario.id), claims),
        expires_in=settings.access_token_expire_minutes * 60,
        usuario=build_user_response(usuario, empresa, rol),
    )


async def find_session_membership(
    db: AsyncSession,
    usuario_id: uuid.UUID,
    empresa_id: uuid.UUID | None = None,
) -> tuple[Usuario, UsuarioEmpresa, Empresa, Rol] | None:
    query = (
        select(Usuario, UsuarioEmpresa, Empresa, Rol)
        .join(UsuarioEmpresa, UsuarioEmpresa.usuario_id == Usuario.id)
        .join(Empresa, Empresa.id == UsuarioEmpresa.empresa_id)
        .join(Rol, Rol.id == UsuarioEmpresa.rol_id)
        .where(
            Usuario.id == usuario_id,
            Usuario.estado == "activo",
            UsuarioEmpresa.estado == "activo",
            Empresa.estado == "activo",
            Rol.estado == "activo",
        )
        .order_by(Empresa.nombre_comercial)
    )
    if empresa_id:
        query = query.where(UsuarioEmpresa.empresa_id == empresa_id)
    return (await db.execute(query)).first()


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    usuario = await db.scalar(
        select(Usuario).where(
            func.lower(Usuario.email) == payload.email.lower(),
            Usuario.estado == "activo",
        )
    )
    now = datetime.now(UTC)
    if usuario and usuario.bloqueado_hasta and usuario.bloqueado_hasta > now:
        raise HTTPException(status_code=429, detail="Cuenta bloqueada temporalmente. Intenta más tarde")
    if (
        not usuario
        or not usuario.password_hash
        or not verify_password(payload.password, usuario.password_hash)
    ):
        if usuario:
            usuario.intentos_fallidos = (usuario.intentos_fallidos or 0) + 1
            if usuario.intentos_fallidos >= 5:
                usuario.bloqueado_hasta = now + timedelta(minutes=15)
                usuario.intentos_fallidos = 0
            await db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Correo o contraseña incorrectos",
        )

    row = await find_session_membership(db, usuario.id, payload.empresa_id)
    if not row:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El usuario no tiene acceso a una empresa activa",
        )

    usuario, membresia, empresa, rol = row
    usuario.intentos_fallidos = 0
    usuario.bloqueado_hasta = None
    usuario.ultimo_acceso_at = datetime.now(UTC)
    await db.commit()
    return issue_tokens(usuario, membresia, empresa, rol)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    payload: RefreshRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    try:
        claims = decode_token(payload.refresh_token, expected_type="refresh")
        usuario_id = uuid.UUID(claims["sub"])
        empresa_id = uuid.UUID(claims["empresa_id"])
    except (ValueError, KeyError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de renovación inválido o vencido",
        ) from None

    row = await find_session_membership(db, usuario_id, empresa_id)
    if not row:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="La sesión ya no tiene acceso",
        )
    return issue_tokens(*row)


@router.get("/me", response_model=UsuarioSesion)
async def me(
    context: Annotated[AuthContext, Depends(get_current_context)],
) -> UsuarioSesion:
    return build_user_response(
        context.usuario, context.empresa, context.rol, context.permisos
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout() -> Response:
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/cambiar-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(payload: ChangePasswordRequest, context: Annotated[AuthContext, Depends(get_current_context)], db: Annotated[AsyncSession, Depends(get_db)]):
    if not context.usuario.password_hash or not verify_password(payload.password_actual, context.usuario.password_hash):
        raise HTTPException(status_code=422, detail="La contraseña actual no es correcta")
    if verify_password(payload.password_nueva, context.usuario.password_hash):
        raise HTTPException(status_code=422, detail="La nueva contraseña debe ser diferente")
    context.usuario.password_hash = hash_password(payload.password_nueva)
    context.usuario.password_changed_at = datetime.now(UTC)
    await db.commit()


@router.post("/recuperar-password", response_model=ForgotPasswordResponse)
async def forgot_password(payload: ForgotPasswordRequest, db: Annotated[AsyncSession, Depends(get_db)]):
    message = "Si el correo está registrado, recibirás instrucciones para recuperar tu contraseña"
    user = await db.scalar(select(Usuario).where(func.lower(Usuario.email) == payload.email.lower(), Usuario.estado == "activo"))
    if not user:
        return ForgotPasswordResponse(mensaje=message)
    recent_token = await db.scalar(
        select(PasswordResetToken.id).where(
            PasswordResetToken.usuario_id == user.id,
            PasswordResetToken.created_at > datetime.now(UTC) - timedelta(seconds=60),
        )
    )
    if recent_token:
        return ForgotPasswordResponse(mensaje=message)
    token = create_password_reset_token(str(user.id))
    db.add(PasswordResetToken(usuario_id=user.id, token_hash=hashlib.sha256(token.encode()).hexdigest(), expires_at=datetime.now(UTC) + timedelta(minutes=30)))
    await db.commit()
    try:
        await send_password_reset_email(user.email, token)
    except Exception:
        logger.exception("No fue posible enviar el correo de recuperación")
    return ForgotPasswordResponse(mensaje=message, recovery_token=token if settings.app_env != "production" else None)


@router.post("/restablecer-password", status_code=status.HTTP_204_NO_CONTENT)
async def reset_password(payload: ResetPasswordRequest, db: Annotated[AsyncSession, Depends(get_db)]):
    try:
        claims = decode_token(payload.token, expected_type="password_reset")
        user_id = uuid.UUID(claims["sub"])
    except (ValueError, KeyError, TypeError):
        raise HTTPException(status_code=422, detail="El enlace es inválido o venció") from None
    token_hash = hashlib.sha256(payload.token.encode()).hexdigest()
    record = await db.scalar(select(PasswordResetToken).where(PasswordResetToken.usuario_id == user_id, PasswordResetToken.token_hash == token_hash, PasswordResetToken.used_at.is_(None), PasswordResetToken.expires_at > datetime.now(UTC)).with_for_update())
    user = await db.get(Usuario, user_id)
    if not record or not user:
        raise HTTPException(status_code=422, detail="El enlace es inválido o ya fue utilizado")
    user.password_hash = hash_password(payload.password_nueva)
    user.password_changed_at = datetime.now(UTC)
    user.intentos_fallidos = 0
    user.bloqueado_hasta = None
    record.used_at = datetime.now(UTC)
    await db.commit()
