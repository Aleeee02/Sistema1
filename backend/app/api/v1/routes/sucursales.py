import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentContext, branch_scope, ensure_branch_access
from app.db.session import get_db
from app.models.empleado import Empleado, EmpleadoSucursal
from app.models.empresa import Sucursal
from app.models.orden import OrdenTrabajo
from app.schemas.sucursal import SucursalCreate, SucursalRead, SucursalUpdate
from app.services.auditoria import record_audit

router = APIRouter()


async def read_branch(db: AsyncSession, branch: Sucursal) -> SucursalRead:
    employees = await db.scalar(
        select(func.count(func.distinct(Empleado.id)))
        .join(EmpleadoSucursal, EmpleadoSucursal.empleado_id == Empleado.id)
        .where(
            EmpleadoSucursal.sucursal_id == branch.id,
            Empleado.empresa_id == branch.empresa_id,
            Empleado.estado == "activo",
        )
    )
    orders = await db.scalar(
        select(func.count(OrdenTrabajo.id)).where(
            OrdenTrabajo.sucursal_id == branch.id,
            OrdenTrabajo.empresa_id == branch.empresa_id,
            OrdenTrabajo.estado.not_in(("entregada", "cancelada")),
        )
    )
    return SucursalRead.model_validate(
        {
            **{column.name: getattr(branch, column.name) for column in Sucursal.__table__.columns},
            "empleados_activos": employees or 0,
            "ordenes_activas": orders or 0,
        }
    )


async def find_branch(db: AsyncSession, branch_id: uuid.UUID, context):
    ensure_branch_access(context, branch_id)
    branch = await db.scalar(
        select(Sucursal).where(
            Sucursal.id == branch_id,
            Sucursal.empresa_id == context.empresa_id,
        )
    )
    if not branch:
        raise HTTPException(status_code=404, detail="Sucursal no encontrada")
    return branch


async def set_principal(db: AsyncSession, branch: Sucursal) -> None:
    await db.execute(
        update(Sucursal)
        .where(
            Sucursal.empresa_id == branch.empresa_id,
            Sucursal.id != branch.id,
            Sucursal.es_principal.is_(True),
        )
        .values(es_principal=False)
    )
    branch.es_principal = True


@router.get("", response_model=list[SucursalRead])
async def list_branches(
    context: CurrentContext,
    incluir_inactivas: bool = False,
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(Sucursal)
        .where(
            Sucursal.empresa_id == context.empresa_id,
            branch_scope(context, Sucursal.id),
        )
        .order_by(Sucursal.es_principal.desc(), Sucursal.nombre)
    )
    if not incluir_inactivas:
        query = query.where(Sucursal.estado == "activo")
    return [await read_branch(db, branch) for branch in (await db.scalars(query)).all()]


@router.post("", response_model=SucursalRead, status_code=status.HTTP_201_CREATED)
async def create_branch(
    payload: SucursalCreate,
    context: CurrentContext,
    db: AsyncSession = Depends(get_db),
):
    active_count = await db.scalar(
        select(func.count(Sucursal.id)).where(
            Sucursal.empresa_id == context.empresa_id,
            Sucursal.estado == "activo",
        )
    )
    values = payload.model_dump()
    for key, value in values.items():
        if isinstance(value, str):
            values[key] = value.strip() or None
    values["codigo"] = payload.codigo.strip().upper()
    values["es_principal"] = payload.es_principal or not active_count
    branch = Sucursal(empresa_id=context.empresa_id, **values)
    try:
        if branch.es_principal:
            await db.execute(
                update(Sucursal)
                .where(
                    Sucursal.empresa_id == context.empresa_id,
                    Sucursal.es_principal.is_(True),
                )
                .values(es_principal=False)
            )
        db.add(branch)
        await db.flush()
        record_audit(db, context, "crear", "sucursales", branch.id, after={"codigo": branch.codigo, "nombre": branch.nombre})
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail="El código de sucursal ya existe") from exc
    await db.refresh(branch)
    return await read_branch(db, branch)


@router.patch("/{branch_id}", response_model=SucursalRead)
async def update_branch(
    branch_id: uuid.UUID,
    payload: SucursalUpdate,
    context: CurrentContext,
    db: AsyncSession = Depends(get_db),
):
    branch = await find_branch(db, branch_id, context)
    before = {"nombre": branch.nombre, "codigo": branch.codigo, "es_principal": branch.es_principal}
    values = payload.model_dump(exclude_unset=True)
    if values.get("es_principal") is False and branch.es_principal:
        raise HTTPException(status_code=409, detail="Primero establece otra sucursal como principal")
    for key, value in values.items():
        if isinstance(value, str):
            value = value.strip() or None
        if key == "codigo" and value:
            value = value.upper()
        setattr(branch, key, value)
    try:
        if values.get("es_principal") is True:
            await set_principal(db, branch)
        record_audit(db, context, "actualizar", "sucursales", branch.id, before=before, after=payload.model_dump(mode="json", exclude_unset=True))
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail="El código de sucursal ya existe") from exc
    await db.refresh(branch)
    return await read_branch(db, branch)


@router.delete("/{branch_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_branch(
    branch_id: uuid.UUID,
    context: CurrentContext,
    db: AsyncSession = Depends(get_db),
):
    branch = await find_branch(db, branch_id, context)
    if branch.es_principal:
        raise HTTPException(status_code=409, detail="No puedes desactivar la sucursal principal")
    active_orders = await db.scalar(
        select(func.count(OrdenTrabajo.id)).where(
            OrdenTrabajo.empresa_id == context.empresa_id,
            OrdenTrabajo.sucursal_id == branch.id,
            OrdenTrabajo.estado.not_in(("entregada", "cancelada")),
        )
    )
    if active_orders:
        raise HTTPException(status_code=409, detail="La sucursal tiene órdenes activas")
    branch.estado = "inactivo"
    record_audit(db, context, "desactivar", "sucursales", branch.id, after={"estado": "inactivo"})
    await db.commit()
