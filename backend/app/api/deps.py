import uuid
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import ColumnElement, select, true
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_token
from app.core.permissions import has_permission
from app.db.session import get_db
from app.models.empresa import Empresa, PlanSaaS
from app.models.usuario import Rol, RolPermiso, Usuario, UsuarioEmpresa, UsuarioSucursal

bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class AuthContext:
    usuario: Usuario
    membresia: UsuarioEmpresa
    empresa: Empresa
    rol: Rol
    sucursal_ids: frozenset[uuid.UUID]
    permisos: frozenset[str]
    modulos_plan: frozenset[str]

    @property
    def empresa_id(self) -> uuid.UUID:
        return self.empresa.id


async def get_current_context(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(bearer_scheme)
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AuthContext:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Sesión inválida o vencida",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not credentials:
        raise unauthorized

    try:
        payload = decode_token(credentials.credentials, expected_type="access")
        usuario_id = uuid.UUID(payload["sub"])
        empresa_id = uuid.UUID(payload["empresa_id"])
    except (ValueError, KeyError, TypeError):
        raise unauthorized from None

    row = (
        await db.execute(
            select(Usuario, UsuarioEmpresa, Empresa, Rol)
            .join(UsuarioEmpresa, UsuarioEmpresa.usuario_id == Usuario.id)
            .join(Empresa, Empresa.id == UsuarioEmpresa.empresa_id)
            .join(Rol, Rol.id == UsuarioEmpresa.rol_id)
            .where(
                Usuario.id == usuario_id,
                Usuario.estado == "activo",
                UsuarioEmpresa.empresa_id == empresa_id,
                UsuarioEmpresa.estado == "activo",
                Empresa.estado == "activo",
                Rol.estado == "activo",
            )
        )
    ).one_or_none()
    if not row:
        raise unauthorized
    branch_ids = frozenset(
        (
            await db.scalars(
                select(UsuarioSucursal.sucursal_id).where(
                    UsuarioSucursal.usuario_empresa_id == row[1].id
                )
            )
        ).all()
    )
    custom_permissions = frozenset(
        (
            await db.scalars(
                select(RolPermiso.permiso).where(
                    RolPermiso.empresa_id == empresa_id,
                    RolPermiso.rol_id == row[3].id,
                )
            )
        ).all()
    )
    plan_modules = frozenset(
        await db.scalar(
            select(PlanSaaS.modulos).where(
                PlanSaaS.codigo == row[2].plan_codigo,
                PlanSaaS.estado == "activo",
            )
        )
        or []
    )
    return AuthContext(*row, branch_ids, custom_permissions, plan_modules)


async def get_empresa_id(
    context: Annotated[AuthContext, Depends(get_current_context)],
) -> uuid.UUID:
    return context.empresa_id


CurrentContext = Annotated[AuthContext, Depends(get_current_context)]
EmpresaId = Annotated[uuid.UUID, Depends(get_empresa_id)]


async def require_superadmin(
    context: Annotated[AuthContext, Depends(get_current_context)],
) -> AuthContext:
    if not context.usuario.es_superadmin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acceso exclusivo para el administrador de la plataforma",
        )
    return context


SuperadminContext = Annotated[AuthContext, Depends(require_superadmin)]


def branch_scope(context: AuthContext, column) -> ColumnElement[bool]:
    if not context.sucursal_ids:
        return true()
    return column.in_(context.sucursal_ids)


def ensure_branch_access(context: AuthContext, branch_id: uuid.UUID) -> None:
    if context.sucursal_ids and branch_id not in context.sucursal_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes acceso a esta sucursal",
        )


def require_module(module: str):
    async def dependency(
        request: Request,
        context: Annotated[AuthContext, Depends(get_current_context)],
    ) -> AuthContext:
        if context.modulos_plan and module not in context.modulos_plan:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"El módulo {module} no está incluido en el plan de la empresa",
            )
        action = "ver" if request.method in {"GET", "HEAD", "OPTIONS"} else "gestionar"
        if not context_has_permission(context, f"{module}.{action}"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tu rol no tiene permiso para realizar esta operación",
            )
        return context

    return dependency


def require_permission(permission: str):
    async def dependency(
        context: Annotated[AuthContext, Depends(get_current_context)],
    ) -> AuthContext:
        if not context_has_permission(context, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tu rol no tiene permiso para realizar esta acción",
            )
        return context

    return dependency


def context_has_permission(context: AuthContext, permission: str) -> bool:
    return permission in context.permisos or has_permission(context.rol.codigo, permission)
