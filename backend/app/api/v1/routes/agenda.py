import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentContext, branch_scope, ensure_branch_access, require_permission
from app.db.session import get_db
from app.models.agenda import Bahia, Cita
from app.models.cliente import Cliente
from app.models.empleado import Empleado, EmpleadoSucursal
from app.models.empresa import Sucursal
from app.models.vehiculo import Vehiculo, VehiculoCliente
from app.schemas.agenda import BahiaCreate, BahiaRead, BahiaUpdate, CitaCreate, CitaEstadoUpdate, CitaRead, AgendaOpciones
from app.services.auditoria import record_audit

router = APIRouter()


def client_name():
    return func.coalesce(Cliente.razon_social, func.trim(func.concat(Cliente.nombres, " ", Cliente.apellidos)))


def appointment_query(empresa_id: uuid.UUID):
    return (
        select(
            Cita,
            Sucursal.nombre.label("sucursal_nombre"),
            client_name().label("cliente_nombre"),
            Vehiculo.placa.label("vehiculo_placa"),
            func.trim(func.concat(Vehiculo.marca, " ", Vehiculo.modelo)).label("vehiculo_descripcion"),
            Bahia.nombre.label("bahia_nombre"),
            func.trim(func.concat(Empleado.nombres, " ", Empleado.apellidos)).label("empleado_nombre"),
        )
        .join(Sucursal, Sucursal.id == Cita.sucursal_id)
        .join(Cliente, Cliente.id == Cita.cliente_id)
        .join(Vehiculo, Vehiculo.id == Cita.vehiculo_id)
        .outerjoin(Bahia, Bahia.id == Cita.bahia_id)
        .outerjoin(Empleado, Empleado.id == Cita.empleado_id)
        .where(Cita.empresa_id == empresa_id)
    )


def cita_read(row) -> CitaRead:
    cita = row[0]
    return CitaRead(
        **{column.name: getattr(cita, column.name) for column in Cita.__table__.columns},
        sucursal_nombre=row.sucursal_nombre, cliente_nombre=row.cliente_nombre,
        vehiculo_placa=row.vehiculo_placa, vehiculo_descripcion=row.vehiculo_descripcion,
        bahia_nombre=row.bahia_nombre, empleado_nombre=row.empleado_nombre,
    )


@router.get("/bahias", response_model=list[BahiaRead])
async def list_bays(context: CurrentContext, sucursal_id: uuid.UUID | None = None, db: AsyncSession = Depends(get_db)):
    query = select(Bahia, Sucursal.nombre.label("sucursal_nombre")).join(Sucursal, Sucursal.id == Bahia.sucursal_id).where(Bahia.empresa_id == context.empresa_id, branch_scope(context, Bahia.sucursal_id))
    if sucursal_id:
        ensure_branch_access(context, sucursal_id)
        query = query.where(Bahia.sucursal_id == sucursal_id)
    return [BahiaRead(**{column.name: getattr(row[0], column.name) for column in Bahia.__table__.columns}, sucursal_nombre=row.sucursal_nombre) for row in (await db.execute(query.order_by(Sucursal.nombre, Bahia.codigo))).all()]


@router.post("/bahias", response_model=BahiaRead, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_permission("agenda.configurar"))])
async def create_bay(payload: BahiaCreate, context: CurrentContext, db: AsyncSession = Depends(get_db)):
    ensure_branch_access(context, payload.sucursal_id)
    branch = await db.scalar(select(Sucursal).where(Sucursal.id == payload.sucursal_id, Sucursal.empresa_id == context.empresa_id, Sucursal.estado == "activo"))
    if not branch:
        raise HTTPException(status_code=404, detail="Sucursal no encontrada")
    bay = Bahia(empresa_id=context.empresa_id, sucursal_id=branch.id, nombre=payload.nombre.strip(), codigo=payload.codigo.strip().upper(), descripcion=payload.descripcion)
    db.add(bay)
    try:
        await db.flush(); record_audit(db, context, "crear", "bahias", bay.id, after={"codigo": bay.codigo}); await db.commit(); await db.refresh(bay)
    except IntegrityError as exc:
        await db.rollback(); raise HTTPException(status_code=409, detail="El código de bahía ya existe en esta sucursal") from exc
    return BahiaRead(**{column.name: getattr(bay, column.name) for column in Bahia.__table__.columns}, sucursal_nombre=branch.nombre)


@router.patch("/bahias/{bay_id}", response_model=BahiaRead, dependencies=[Depends(require_permission("agenda.configurar"))])
async def update_bay(bay_id: uuid.UUID, payload: BahiaUpdate, context: CurrentContext, db: AsyncSession = Depends(get_db)):
    row = (await db.execute(select(Bahia, Sucursal.nombre.label("sucursal_nombre")).join(Sucursal).where(Bahia.id == bay_id, Bahia.empresa_id == context.empresa_id))).one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Bahía no encontrada")
    bay = row[0]
    ensure_branch_access(context, bay.sucursal_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        if isinstance(value, str): value = value.strip()
        if key == "codigo": value = value.upper()
        setattr(bay, key, value)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback(); raise HTTPException(status_code=409, detail="El código de bahía ya existe") from exc
    await db.refresh(bay)
    return BahiaRead(**{column.name: getattr(bay, column.name) for column in Bahia.__table__.columns}, sucursal_nombre=row.sucursal_nombre)


@router.get("/opciones", response_model=AgendaOpciones)
async def options(context: CurrentContext, db: AsyncSession = Depends(get_db)):
    clients = (await db.execute(select(Cliente.id, client_name().label("nombre")).where(Cliente.empresa_id == context.empresa_id, Cliente.estado == "activo").order_by("nombre"))).all()
    vehicles = (await db.execute(select(Vehiculo.id, VehiculoCliente.cliente_id, Vehiculo.placa, func.trim(func.concat(Vehiculo.marca, " ", Vehiculo.modelo)).label("descripcion")).join(VehiculoCliente, and_(VehiculoCliente.vehiculo_id == Vehiculo.id, VehiculoCliente.es_actual.is_(True))).where(Vehiculo.empresa_id == context.empresa_id, Vehiculo.estado == "activo"))).all()
    employees = (await db.execute(select(Empleado.id, EmpleadoSucursal.sucursal_id, func.trim(func.concat(Empleado.nombres, " ", Empleado.apellidos)).label("nombre")).join(EmpleadoSucursal, EmpleadoSucursal.empleado_id == Empleado.id).where(Empleado.empresa_id == context.empresa_id, Empleado.estado == "activo", branch_scope(context, EmpleadoSucursal.sucursal_id)))).all()
    return AgendaOpciones(clientes=[{"id": r.id, "nombre": r.nombre} for r in clients], vehiculos=[{"id": r.id, "cliente_id": r.cliente_id, "placa": r.placa, "descripcion": r.descripcion} for r in vehicles], empleados=[{"id": r.id, "sucursal_id": r.sucursal_id, "nombre": r.nombre} for r in employees])


@router.get("/citas", response_model=list[CitaRead])
async def list_appointments(context: CurrentContext, desde: datetime | None = Query(default=None), hasta: datetime | None = Query(default=None), sucursal_id: uuid.UUID | None = None, db: AsyncSession = Depends(get_db)):
    query = appointment_query(context.empresa_id).where(branch_scope(context, Cita.sucursal_id))
    if desde: query = query.where(Cita.fecha_fin > desde)
    if hasta: query = query.where(Cita.fecha_inicio < hasta)
    if sucursal_id:
        ensure_branch_access(context, sucursal_id)
        query = query.where(Cita.sucursal_id == sucursal_id)
    return [cita_read(row) for row in (await db.execute(query.order_by(Cita.fecha_inicio))).all()]


@router.post("/citas", response_model=CitaRead, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_permission("agenda.citas"))])
async def create_appointment(payload: CitaCreate, context: CurrentContext, db: AsyncSession = Depends(get_db)):
    ensure_branch_access(context, payload.sucursal_id)
    branch = await db.scalar(select(Sucursal.id).where(Sucursal.id == payload.sucursal_id, Sucursal.empresa_id == context.empresa_id, Sucursal.estado == "activo"))
    owner = await db.scalar(select(VehiculoCliente.id).join(Vehiculo, Vehiculo.id == VehiculoCliente.vehiculo_id).where(VehiculoCliente.cliente_id == payload.cliente_id, VehiculoCliente.vehiculo_id == payload.vehiculo_id, VehiculoCliente.es_actual.is_(True), Vehiculo.empresa_id == context.empresa_id))
    if not branch or not owner:
        raise HTTPException(status_code=422, detail="Sucursal, cliente o vehículo no válidos")
    if payload.bahia_id and not await db.scalar(select(Bahia.id).where(Bahia.id == payload.bahia_id, Bahia.sucursal_id == payload.sucursal_id, Bahia.empresa_id == context.empresa_id, Bahia.estado == "activo")):
        raise HTTPException(status_code=422, detail="La bahía no está disponible en esta sucursal")
    if payload.empleado_id and not await db.scalar(select(EmpleadoSucursal.id).join(Empleado, Empleado.id == EmpleadoSucursal.empleado_id).where(EmpleadoSucursal.empleado_id == payload.empleado_id, EmpleadoSucursal.sucursal_id == payload.sucursal_id, Empleado.empresa_id == context.empresa_id, Empleado.estado == "activo")):
        raise HTTPException(status_code=422, detail="El empleado no pertenece a esta sucursal")
    conflict = await db.scalar(select(Cita.id).where(Cita.empresa_id == context.empresa_id, Cita.estado.not_in(("cancelada", "no_asistio")), Cita.fecha_inicio < payload.fecha_fin, Cita.fecha_fin > payload.fecha_inicio, or_(and_(payload.bahia_id is not None, Cita.bahia_id == payload.bahia_id), and_(payload.empleado_id is not None, Cita.empleado_id == payload.empleado_id))))
    if conflict:
        raise HTTPException(status_code=409, detail="La bahía o el empleado ya tienen una cita en ese horario")
    cita = Cita(empresa_id=context.empresa_id, created_by=context.usuario.id, **payload.model_dump())
    db.add(cita); await db.flush(); record_audit(db, context, "crear", "citas", cita.id, after={"fecha_inicio": payload.fecha_inicio.isoformat()}); await db.commit()
    return cita_read((await db.execute(appointment_query(context.empresa_id).where(Cita.id == cita.id))).one())


@router.patch("/citas/{appointment_id}/estado", response_model=CitaRead, dependencies=[Depends(require_permission("agenda.citas"))])
async def update_status(appointment_id: uuid.UUID, payload: CitaEstadoUpdate, context: CurrentContext, db: AsyncSession = Depends(get_db)):
    cita = await db.scalar(select(Cita).where(Cita.id == appointment_id, Cita.empresa_id == context.empresa_id))
    if not cita: raise HTTPException(status_code=404, detail="Cita no encontrada")
    ensure_branch_access(context, cita.sucursal_id)
    cita.estado = payload.estado; await db.commit()
    return cita_read((await db.execute(appointment_query(context.empresa_id).where(Cita.id == cita.id))).one())
