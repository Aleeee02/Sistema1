import re
import uuid
import unicodedata

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentContext
from app.core.permissions import ACTION_PERMISSIONS
from app.db.session import get_db
from app.models.usuario import Rol, RolPermiso, UsuarioEmpresa
from app.schemas.usuario import PermisoOpcion, RolCreate, RolDetalle, RolUpdate
from app.services.auditoria import record_audit

router = APIRouter()

MODULE_NAMES = {
    "dashboard": "Dashboard", "agenda": "Agenda y bahías",
    "clientes": "Clientes", "vehiculos": "Vehículos",
    "ordenes": "Órdenes de trabajo", "cotizaciones": "Cotizaciones",
    "inspecciones": "Inspecciones", "pagos": "Pagos",
    "servicios": "Servicios", "inventario": "Inventario",
    "transferencias": "Transferencias", "empleados": "Empleados",
    "sucursales": "Sucursales", "usuarios": "Usuarios",
    "estadisticas": "Estadísticas", "reportes": "Reportes",
    "configuracion": "Configuración de empresa",
    "comprobantes": "Comprobantes internos",
    "auditoria": "Auditoría",
}
MODULE_PERMISSIONS = {
    f"{module}.{action}"
    for module in MODULE_NAMES
    for action in ("ver", "gestionar")
}
KNOWN_PERMISSIONS = MODULE_PERMISSIONS | ACTION_PERMISSIONS


def require_admin(context):
    if context.rol.codigo not in {"administrador", "superadmin"}:
        raise HTTPException(status_code=403, detail="Solo un administrador puede gestionar roles")


def permission_name(code: str) -> str:
    action = code.split(".", 1)[1]
    names = {
        "ver": "Ver módulo", "gestionar": "Gestionar módulo",
        "configurar": "Configurar", "citas": "Gestionar citas",
        "editar": "Crear y editar", "avanzar": "Cambiar estado",
        "cambiar_estado": "Aprobar o rechazar", "recibir": "Recibir repuestos",
        "consumir": "Consumir reserva", "registrar": "Registrar pagos",
        "anular": "Anular pagos",
    }
    return names.get(action, action.replace("_", " ").capitalize())


def validate_permissions(values: list[str]) -> set[str]:
    permissions = set(values)
    invalid = permissions - KNOWN_PERMISSIONS
    if invalid:
        raise HTTPException(status_code=422, detail=f"Permiso no reconocido: {sorted(invalid)[0]}")
    for permission in tuple(permissions):
        module, action = permission.split(".", 1)
        if action not in {"ver", "gestionar"}:
            permissions.update({f"{module}.ver", f"{module}.gestionar"})
    return permissions


async def role_detail(db: AsyncSession, role: Rol, empresa_id: uuid.UUID) -> RolDetalle:
    permissions = list((await db.scalars(select(RolPermiso.permiso).where(RolPermiso.rol_id == role.id).order_by(RolPermiso.permiso))).all())
    users = int(await db.scalar(select(func.count(UsuarioEmpresa.id)).where(UsuarioEmpresa.rol_id == role.id, UsuarioEmpresa.empresa_id == empresa_id, UsuarioEmpresa.estado == "activo")) or 0)
    return RolDetalle(
        id=role.id, codigo=role.codigo, nombre=role.nombre,
        descripcion=role.descripcion, empresa_id=role.empresa_id,
        es_sistema=role.es_sistema, estado=role.estado,
        permisos=permissions, usuarios_asignados=users,
    )


async def find_custom_role(db: AsyncSession, role_id: uuid.UUID, empresa_id: uuid.UUID) -> Rol:
    role = await db.scalar(select(Rol).where(Rol.id == role_id, Rol.empresa_id == empresa_id, Rol.es_sistema.is_(False)))
    if not role:
        raise HTTPException(status_code=404, detail="Rol personalizado no encontrado")
    return role


@router.get("/permisos", response_model=list[PermisoOpcion])
async def list_permissions(context: CurrentContext):
    require_admin(context)
    return [
        PermisoOpcion(codigo=code, modulo=MODULE_NAMES[code.split(".", 1)[0]], nombre=permission_name(code))
        for code in sorted(KNOWN_PERMISSIONS, key=lambda value: (MODULE_NAMES[value.split(".", 1)[0]], value))
    ]


@router.get("", response_model=list[RolDetalle])
async def list_roles(context: CurrentContext, db: AsyncSession = Depends(get_db)):
    require_admin(context)
    query = select(Rol).where(
        (Rol.empresa_id == context.empresa_id) | (Rol.empresa_id.is_(None)),
        Rol.codigo != "superadmin" if context.rol.codigo != "superadmin" else True,
    ).order_by(Rol.es_sistema.desc(), Rol.nombre)
    return [await role_detail(db, role, context.empresa_id) for role in (await db.scalars(query)).all()]


@router.post("", response_model=RolDetalle, status_code=status.HTTP_201_CREATED)
async def create_role(payload: RolCreate, context: CurrentContext, db: AsyncSession = Depends(get_db)):
    require_admin(context)
    permissions = validate_permissions(payload.permisos)
    normalized = unicodedata.normalize("NFKD", payload.nombre).encode("ascii", "ignore").decode().lower()
    slug = re.sub(r"[^a-z0-9]+", "_", normalized).strip("_")[:13] or "rol"
    role = Rol(
        empresa_id=context.empresa_id,
        codigo=f"custom_{context.empresa_id.hex[:8]}_{slug}",
        nombre=payload.nombre.strip(),
        descripcion=payload.descripcion.strip() if payload.descripcion else None,
        es_sistema=False,
        estado="activo",
    )
    db.add(role)
    try:
        await db.flush()
        for permission in permissions:
            db.add(RolPermiso(empresa_id=context.empresa_id, rol_id=role.id, permiso=permission))
        record_audit(db, context, "crear", "roles", role.id, after={"nombre": role.nombre, "permisos": sorted(permissions)})
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Ya existe un rol con ese nombre") from exc
    return await role_detail(db, role, context.empresa_id)


@router.patch("/{role_id}", response_model=RolDetalle)
async def update_role(role_id: uuid.UUID, payload: RolUpdate, context: CurrentContext, db: AsyncSession = Depends(get_db)):
    require_admin(context)
    role = await find_custom_role(db, role_id, context.empresa_id)
    values = payload.model_dump(exclude_unset=True)
    permissions = values.pop("permisos", None)
    if "nombre" in values:
        values["nombre"] = values["nombre"].strip()
    if values.get("descripcion"):
        values["descripcion"] = values["descripcion"].strip()
    for key, value in values.items():
        setattr(role, key, value)
    if permissions is not None:
        permissions = validate_permissions(permissions)
        await db.execute(delete(RolPermiso).where(RolPermiso.rol_id == role.id, RolPermiso.empresa_id == context.empresa_id))
        for permission in permissions:
            db.add(RolPermiso(empresa_id=context.empresa_id, rol_id=role.id, permiso=permission))
    try:
        record_audit(db, context, "actualizar", "roles", role.id, after=payload.model_dump(mode="json", exclude_unset=True))
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Ya existe un rol con ese nombre") from exc
    return await role_detail(db, role, context.empresa_id)


@router.delete("/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_role(role_id: uuid.UUID, context: CurrentContext, db: AsyncSession = Depends(get_db)):
    require_admin(context)
    role = await find_custom_role(db, role_id, context.empresa_id)
    assigned = await db.scalar(select(func.count(UsuarioEmpresa.id)).where(UsuarioEmpresa.rol_id == role.id, UsuarioEmpresa.estado == "activo"))
    if assigned:
        raise HTTPException(status_code=409, detail="Primero asigna otro rol a sus usuarios")
    role.estado = "inactivo"
    record_audit(db, context, "desactivar", "roles", role.id, after={"estado": "inactivo"})
    await db.commit()
