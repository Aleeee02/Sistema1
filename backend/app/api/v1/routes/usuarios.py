import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentContext
from app.core.security import hash_password
from app.db.session import get_db
from app.models.empresa import Sucursal
from app.models.usuario import Rol, Usuario, UsuarioEmpresa, UsuarioSucursal
from app.schemas.usuario import UsuarioEmpresaCreate, UsuarioEmpresaRead, UsuarioEmpresaUpdate, UsuariosOpciones
from app.services.auditoria import record_audit

router = APIRouter()


def require_admin(context: CurrentContext):
    if context.rol.codigo not in {"administrador", "superadmin"}:
        raise HTTPException(status_code=403, detail="Solo un administrador puede gestionar usuarios")


async def validate_role(db, role_id, context):
    role = await db.scalar(select(Rol).where(Rol.id == role_id))
    if (
        not role
        or role.estado != "activo"
        or (role.empresa_id is not None and role.empresa_id != context.empresa_id)
        or (role.codigo == "superadmin" and context.rol.codigo != "superadmin")
    ):
        raise HTTPException(status_code=422, detail="Rol no permitido")
    return role


async def validate_branches(db, branch_ids, empresa_id):
    if not branch_ids: return []
    branches = list((await db.scalars(select(Sucursal).where(Sucursal.id.in_(set(branch_ids)), Sucursal.empresa_id == empresa_id, Sucursal.estado == "activo"))).all())
    if len(branches) != len(set(branch_ids)): raise HTTPException(status_code=422, detail="Una sucursal no pertenece a la empresa")
    return branches


async def serialize(db, row):
    user, membership, role = row
    branches = (await db.execute(select(Sucursal.id, Sucursal.nombre).join(UsuarioSucursal, UsuarioSucursal.sucursal_id == Sucursal.id).where(UsuarioSucursal.usuario_empresa_id == membership.id).order_by(Sucursal.nombre))).all()
    return UsuarioEmpresaRead(id=user.id, membresia_id=membership.id, email=user.email, nombres=user.nombres, apellidos=user.apellidos, telefono=user.telefono, rol_id=role.id, rol_codigo=role.codigo, rol_nombre=role.nombre, estado=membership.estado, ultimo_acceso_at=user.ultimo_acceso_at, sucursal_ids=[item.id for item in branches], sucursal_nombres=[item.nombre for item in branches], created_at=membership.created_at)


def base_query(empresa_id):
    return select(Usuario, UsuarioEmpresa, Rol).join(UsuarioEmpresa, UsuarioEmpresa.usuario_id == Usuario.id).join(Rol, Rol.id == UsuarioEmpresa.rol_id).where(UsuarioEmpresa.empresa_id == empresa_id)


@router.get("/opciones", response_model=UsuariosOpciones)
async def options(context: CurrentContext, db: AsyncSession = Depends(get_db)):
    require_admin(context)
    query = select(Rol).where(
        (Rol.empresa_id == context.empresa_id) | (Rol.empresa_id.is_(None)),
        Rol.estado == "activo",
    ).order_by(Rol.nombre)
    if context.rol.codigo != "superadmin": query = query.where(Rol.codigo != "superadmin")
    return UsuariosOpciones(roles=list((await db.scalars(query)).all()))


@router.get("", response_model=list[UsuarioEmpresaRead])
async def list_users(context: CurrentContext, db: AsyncSession = Depends(get_db)):
    require_admin(context)
    return [await serialize(db, row) for row in (await db.execute(base_query(context.empresa_id).order_by(Usuario.nombres, Usuario.apellidos))).all()]


@router.post("", response_model=UsuarioEmpresaRead, status_code=status.HTTP_201_CREATED)
async def create_user(payload: UsuarioEmpresaCreate, context: CurrentContext, db: AsyncSession = Depends(get_db)):
    require_admin(context); await validate_role(db, payload.rol_id, context); branches = await validate_branches(db, payload.sucursal_ids, context.empresa_id)
    active_users = await db.scalar(select(func.count(UsuarioEmpresa.id)).where(UsuarioEmpresa.empresa_id == context.empresa_id, UsuarioEmpresa.estado == "activo"))
    if (active_users or 0) >= context.empresa.max_usuarios:
        raise HTTPException(status_code=409, detail=f"Tu plan permite hasta {context.empresa.max_usuarios} usuarios activos")
    if await db.scalar(select(Usuario.id).where(func.lower(Usuario.email) == payload.email.lower())):
        raise HTTPException(status_code=409, detail="El correo ya está registrado")
    user = Usuario(email=payload.email.lower(), password_hash=hash_password(payload.password), nombres=payload.nombres.strip(), apellidos=payload.apellidos.strip(), telefono=payload.telefono)
    db.add(user)
    try:
        await db.flush(); membership = UsuarioEmpresa(usuario_id=user.id, empresa_id=context.empresa_id, rol_id=payload.rol_id); db.add(membership); await db.flush()
        for branch in branches: db.add(UsuarioSucursal(usuario_empresa_id=membership.id, sucursal_id=branch.id))
        record_audit(db, context, "crear", "usuarios_empresas", membership.id, after={"email": user.email}); await db.commit()
    except IntegrityError as exc:
        await db.rollback(); raise HTTPException(status_code=409, detail="No se pudo crear el usuario") from exc
    return await serialize(db, (user, membership, await db.get(Rol, membership.rol_id)))


@router.patch("/{user_id}", response_model=UsuarioEmpresaRead)
async def update_user(user_id: uuid.UUID, payload: UsuarioEmpresaUpdate, context: CurrentContext, db: AsyncSession = Depends(get_db)):
    require_admin(context)
    row = (await db.execute(base_query(context.empresa_id).where(Usuario.id == user_id))).one_or_none()
    if not row: raise HTTPException(status_code=404, detail="Usuario no encontrado")
    user, membership, _ = row
    values = payload.model_dump(exclude_unset=True)
    if values.get("estado") != "activo" and user.id == context.usuario.id: raise HTTPException(status_code=409, detail="No puedes suspender tu propio acceso")
    if "rol_id" in values: await validate_role(db, values["rol_id"], context); membership.rol_id = values.pop("rol_id")
    branch_ids = values.pop("sucursal_ids", None)
    if branch_ids is not None:
        branches = await validate_branches(db, branch_ids, context.empresa_id)
        await db.execute(delete(UsuarioSucursal).where(UsuarioSucursal.usuario_empresa_id == membership.id))
        for branch in branches: db.add(UsuarioSucursal(usuario_empresa_id=membership.id, sucursal_id=branch.id))
    if "estado" in values: membership.estado = values.pop("estado")
    for key, value in values.items(): setattr(user, key, value.strip() if isinstance(value, str) else value)
    record_audit(db, context, "actualizar", "usuarios_empresas", membership.id, after=payload.model_dump(mode="json", exclude_unset=True)); await db.commit()
    role = await db.get(Rol, membership.rol_id)
    return await serialize(db, (user, membership, role))
