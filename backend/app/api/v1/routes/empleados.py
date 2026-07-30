import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentContext, branch_scope, ensure_branch_access
from app.db.session import get_db
from app.models.empleado import Empleado, EmpleadoSucursal, OrdenEmpleado
from app.models.empresa import Sucursal
from app.models.orden import OrdenTrabajo
from app.schemas.empleado import (
    AsignacionCreate,
    AsignacionRead,
    EmpleadoCreate,
    EmpleadoRead,
    EmpleadoUpdate,
)
from app.services.auditoria import record_audit

router = APIRouter()


def employee_query(empresa_id: uuid.UUID):
    return (
        select(
            Empleado,
            EmpleadoSucursal.sucursal_id,
            Sucursal.nombre.label("sucursal_nombre"),
        )
        .outerjoin(
            EmpleadoSucursal,
            (EmpleadoSucursal.empleado_id == Empleado.id)
            & EmpleadoSucursal.es_principal.is_(True),
        )
        .outerjoin(Sucursal, Sucursal.id == EmpleadoSucursal.sucursal_id)
        .where(Empleado.empresa_id == empresa_id)
    )


def employee_read(row) -> EmpleadoRead:
    employee = row[0]
    return EmpleadoRead(
        **{column.name: getattr(employee, column.name) for column in Empleado.__table__.columns},
        sucursal_id=row.sucursal_id,
        sucursal_nombre=row.sucursal_nombre,
    )


async def find_employee(db: AsyncSession, employee_id: uuid.UUID, empresa_id: uuid.UUID):
    row = (
        await db.execute(
            employee_query(empresa_id).where(Empleado.id == employee_id)
        )
    ).one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")
    return row


@router.get("", response_model=list[EmpleadoRead])
async def list_employees(
    context: CurrentContext,
    incluir_inactivos: bool = False,
    sucursal_id: uuid.UUID | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    query = employee_query(context.empresa_id).order_by(Empleado.nombres, Empleado.apellidos)
    query = query.where(
        Empleado.id.in_(
            select(EmpleadoSucursal.empleado_id).where(
                branch_scope(context, EmpleadoSucursal.sucursal_id)
            )
        )
    )
    if not incluir_inactivos:
        query = query.where(Empleado.estado == "activo")
    if sucursal_id:
        ensure_branch_access(context, sucursal_id)
        query = query.where(
            Empleado.id.in_(
                select(EmpleadoSucursal.empleado_id).where(
                    EmpleadoSucursal.sucursal_id == sucursal_id
                )
            )
        )
    return [employee_read(row) for row in (await db.execute(query)).all()]


@router.post("", response_model=EmpleadoRead, status_code=status.HTTP_201_CREATED)
async def create_employee(
    payload: EmpleadoCreate,
    context: CurrentContext,
    db: AsyncSession = Depends(get_db),
):
    ensure_branch_access(context, payload.sucursal_id)
    branch = await db.scalar(
        select(Sucursal).where(
            Sucursal.id == payload.sucursal_id,
            Sucursal.empresa_id == context.empresa_id,
            Sucursal.estado == "activo",
        )
    )
    if not branch:
        raise HTTPException(status_code=404, detail="Sucursal no encontrada")
    values = payload.model_dump(exclude={"sucursal_id"})
    values = {key: value.strip() if isinstance(value, str) else value for key, value in values.items()}
    employee = Empleado(empresa_id=context.empresa_id, **values)
    db.add(employee)
    try:
        await db.flush()
        db.add(EmpleadoSucursal(empleado_id=employee.id, sucursal_id=payload.sucursal_id, es_principal=True))
        record_audit(db, context, "crear", "empleados", employee.id, after={"codigo": employee.codigo})
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail="El código del empleado ya existe") from exc
    return employee_read(await find_employee(db, employee.id, context.empresa_id))


@router.patch("/{employee_id}", response_model=EmpleadoRead)
async def update_employee(
    employee_id: uuid.UUID,
    payload: EmpleadoUpdate,
    context: CurrentContext,
    db: AsyncSession = Depends(get_db),
):
    row = await find_employee(db, employee_id, context.empresa_id)
    if row.sucursal_id:
        ensure_branch_access(context, row.sucursal_id)
    employee = row[0]
    before = {"codigo": employee.codigo, "nombres": employee.nombres, "apellidos": employee.apellidos}
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(employee, key, value.strip() if isinstance(value, str) else value)
    try:
        record_audit(db, context, "actualizar", "empleados", employee.id, before=before, after=payload.model_dump(mode="json", exclude_unset=True))
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail="El código del empleado ya existe") from exc
    return employee_read(await find_employee(db, employee.id, context.empresa_id))


@router.delete("/{employee_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_employee(
    employee_id: uuid.UUID,
    context: CurrentContext,
    db: AsyncSession = Depends(get_db),
):
    row = await find_employee(db, employee_id, context.empresa_id)
    if row.sucursal_id:
        ensure_branch_access(context, row.sucursal_id)
    employee = row[0]
    employee.estado = "inactivo"
    await db.execute(
        update(OrdenEmpleado)
        .where(
            OrdenEmpleado.empresa_id == context.empresa_id,
            OrdenEmpleado.empleado_id == employee.id,
            OrdenEmpleado.fecha_fin.is_(None),
        )
        .values(fecha_fin=datetime.now(timezone.utc), es_responsable=False)
    )
    record_audit(db, context, "desactivar", "empleados", employee.id, after={"estado": "inactivo"})
    await db.commit()


@router.get("/asignaciones/orden/{order_id}", response_model=list[AsignacionRead])
async def list_assignments(
    order_id: uuid.UUID,
    context: CurrentContext,
    db: AsyncSession = Depends(get_db),
):
    order = await db.scalar(select(OrdenTrabajo).where(OrdenTrabajo.id == order_id, OrdenTrabajo.empresa_id == context.empresa_id))
    if not order:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    ensure_branch_access(context, order.sucursal_id)
    rows = (
        await db.execute(
            select(
                OrdenEmpleado,
                func.trim(func.concat(Empleado.nombres, " ", Empleado.apellidos)).label("empleado_nombre"),
                Empleado.cargo,
            )
            .join(Empleado, Empleado.id == OrdenEmpleado.empleado_id)
            .where(
                OrdenEmpleado.empresa_id == context.empresa_id,
                OrdenEmpleado.orden_id == order_id,
                OrdenEmpleado.fecha_fin.is_(None),
                Empleado.empresa_id == context.empresa_id,
                Empleado.estado == "activo",
            )
            .order_by(OrdenEmpleado.es_responsable.desc(), Empleado.nombres)
        )
    ).all()
    return [
        AsignacionRead(
            **{column.name: getattr(row[0], column.name) for column in OrdenEmpleado.__table__.columns},
            empleado_nombre=row.empleado_nombre,
            cargo=row.cargo,
        )
        for row in rows
    ]


@router.post("/asignaciones", response_model=AsignacionRead, status_code=status.HTTP_201_CREATED)
async def assign_employee(
    payload: AsignacionCreate,
    context: CurrentContext,
    db: AsyncSession = Depends(get_db),
):
    order = await db.scalar(
        select(OrdenTrabajo).where(
            OrdenTrabajo.id == payload.orden_id,
            OrdenTrabajo.empresa_id == context.empresa_id,
            OrdenTrabajo.estado.in_(("aprobada", "en_proceso")),
        )
    )
    if not order:
        raise HTTPException(status_code=409, detail="La OT debe estar aprobada o en proceso")
    ensure_branch_access(context, order.sucursal_id)
    employee = await db.scalar(
        select(Empleado)
        .join(EmpleadoSucursal, EmpleadoSucursal.empleado_id == Empleado.id)
        .where(
            Empleado.id == payload.empleado_id,
            Empleado.empresa_id == context.empresa_id,
            Empleado.estado == "activo",
            EmpleadoSucursal.sucursal_id == order.sucursal_id,
        )
    )
    if not employee:
        raise HTTPException(status_code=409, detail="El empleado no pertenece a la sucursal de la OT")
    if payload.es_responsable:
        await db.execute(
            update(OrdenEmpleado)
            .where(
                OrdenEmpleado.empresa_id == context.empresa_id,
                OrdenEmpleado.orden_id == payload.orden_id,
                OrdenEmpleado.fecha_fin.is_(None),
            )
            .values(es_responsable=False)
        )
    assignment = await db.scalar(
        select(OrdenEmpleado).where(
            OrdenEmpleado.orden_id == payload.orden_id,
            OrdenEmpleado.empleado_id == payload.empleado_id,
        )
    )
    if assignment:
        assignment.fecha_fin = None
        assignment.es_responsable = payload.es_responsable
        assignment.observaciones = payload.observaciones
        assignment.fecha_inicio = datetime.now(timezone.utc)
    else:
        assignment = OrdenEmpleado(empresa_id=context.empresa_id, **payload.model_dump())
        db.add(assignment)
    await db.flush()
    record_audit(db, context, "asignar_empleado", "ordenes_trabajo", order.id, after={"empleado_id": str(employee.id), "responsable": payload.es_responsable})
    await db.commit()
    rows = await list_assignments(payload.orden_id, context, db)
    return next(item for item in rows if item.empleado_id == payload.empleado_id)


@router.delete("/asignaciones/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def finish_assignment(
    assignment_id: uuid.UUID,
    context: CurrentContext,
    db: AsyncSession = Depends(get_db),
):
    assignment = await db.scalar(
        select(OrdenEmpleado).where(
            OrdenEmpleado.id == assignment_id,
            OrdenEmpleado.empresa_id == context.empresa_id,
            OrdenEmpleado.fecha_fin.is_(None),
        )
    )
    if not assignment:
        raise HTTPException(status_code=404, detail="Asignación no encontrada")
    order = await db.scalar(select(OrdenTrabajo).where(OrdenTrabajo.id == assignment.orden_id, OrdenTrabajo.empresa_id == context.empresa_id))
    if not order:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    ensure_branch_access(context, order.sucursal_id)
    assignment.fecha_fin = datetime.now(timezone.utc)
    assignment.es_responsable = False
    await db.commit()
