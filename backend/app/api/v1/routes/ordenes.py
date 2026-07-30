import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select, text, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentContext, branch_scope, ensure_branch_access, require_permission
from app.db.session import get_db
from app.models.cliente import Cliente
from app.models.cotizacion import Cotizacion, CotizacionItem
from app.models.inventario import ReservaInventario
from app.models.inspeccion import Inspeccion
from app.models.empresa import Sucursal
from app.models.orden import OrdenEstadoHistorial, OrdenServicio, OrdenTrabajo
from app.models.usuario import Usuario
from app.models.vehiculo import Vehiculo, VehiculoCliente
from app.schemas.orden import (
    ESTADOS_ORDEN,
    OrdenCreate,
    OrdenEstadoUpdate,
    OrdenOptions,
    OrdenRead,
    OrdenEstadoHistorialRead,
    OrdenServicioEstadoUpdate,
    OrdenServicioRead,
    OrdenUpdate,
)
from app.services.auditoria import record_audit
from app.services.notificaciones import notify
from app.services.ordenes import record_order_status

router = APIRouter()

TRANSICIONES = {
    "borrador": {"recepcion", "cancelada"},
    "recepcion": {"diagnostico", "cancelada"},
    "diagnostico": {"esperando_aprobacion", "cancelada"},
    "esperando_aprobacion": {"aprobada", "cancelada"},
    "aprobada": {"en_proceso", "cancelada"},
    "en_proceso": {"terminada", "cancelada"},
    "terminada": {"entregada", "en_proceso"},
    "entregada": set(),
    "cancelada": set(),
}


def name_expression():
    return func.coalesce(
        Cliente.razon_social,
        func.trim(func.concat(Cliente.nombres, " ", Cliente.apellidos)),
    )


def order_query(empresa_id: uuid.UUID):
    return (
        select(
            OrdenTrabajo,
            name_expression().label("cliente_nombre"),
            Cliente.numero_documento.label("cliente_documento"),
            Vehiculo.placa.label("vehiculo_placa"),
            func.trim(func.concat(Vehiculo.marca, " ", Vehiculo.modelo)).label(
                "vehiculo_descripcion"
            ),
            Sucursal.nombre.label("sucursal_nombre"),
        )
        .join(Cliente, Cliente.id == OrdenTrabajo.cliente_id)
        .join(Vehiculo, Vehiculo.id == OrdenTrabajo.vehiculo_id)
        .join(Sucursal, Sucursal.id == OrdenTrabajo.sucursal_id)
        .where(
            OrdenTrabajo.empresa_id == empresa_id,
            Cliente.empresa_id == empresa_id,
            Vehiculo.empresa_id == empresa_id,
            Sucursal.empresa_id == empresa_id,
        )
    )


def serialize(row) -> OrdenRead:
    order = row[0]
    values = {
        column.name: getattr(order, column.name)
        for column in OrdenTrabajo.__table__.columns
    }
    return OrdenRead(
        **values,
        cliente_nombre=row.cliente_nombre or "Cliente",
        cliente_documento=row.cliente_documento,
        vehiculo_placa=row.vehiculo_placa,
        vehiculo_descripcion=row.vehiculo_descripcion or "Vehículo",
        sucursal_nombre=row.sucursal_nombre,
    )


async def get_row(db: AsyncSession, order_id: uuid.UUID, context):
    row = (
        await db.execute(
            order_query(context.empresa_id).where(
                OrdenTrabajo.id == order_id,
                branch_scope(context, OrdenTrabajo.sucursal_id),
            )
        )
    ).one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    return row


@router.get("/opciones", response_model=OrdenOptions)
async def options(
    context: CurrentContext,
    db: AsyncSession = Depends(get_db),
) -> OrdenOptions:
    branches = list(
        (
            await db.scalars(
                select(Sucursal)
                .where(
                    Sucursal.empresa_id == context.empresa_id,
                    Sucursal.estado == "activo",
                    branch_scope(context, Sucursal.id),
                )
                .order_by(Sucursal.es_principal.desc(), Sucursal.nombre)
            )
        ).all()
    )
    return OrdenOptions(
        sucursales=[
            {"id": branch.id, "nombre": branch.nombre, "es_principal": branch.es_principal}
            for branch in branches
        ]
    )


@router.get("", response_model=list[OrdenRead])
async def list_ordenes(
    context: CurrentContext,
    estado: str | None = None,
    search: str | None = Query(default=None, max_length=100),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> list[OrdenRead]:
    query = (
        order_query(context.empresa_id)
        .where(branch_scope(context, OrdenTrabajo.sucursal_id))
        .order_by(OrdenTrabajo.fecha_recepcion.desc())
        .limit(limit)
        .offset(offset)
    )
    if estado:
        if estado not in ESTADOS_ORDEN:
            raise HTTPException(status_code=422, detail="Estado inválido")
        query = query.where(OrdenTrabajo.estado == estado)
    if search and search.strip():
        term = f"%{search.strip()}%"
        query = query.where(
            or_(
                Vehiculo.placa.ilike(term),
                Cliente.numero_documento.ilike(term),
                Cliente.nombres.ilike(term),
                Cliente.apellidos.ilike(term),
                Cliente.razon_social.ilike(term),
                OrdenTrabajo.falla_reportada.ilike(term),
            )
        )
    return [serialize(row) for row in (await db.execute(query)).all()]


@router.post("", response_model=OrdenRead, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_permission("ordenes.editar"))])
async def create_orden(
    payload: OrdenCreate,
    context: CurrentContext,
    db: AsyncSession = Depends(get_db),
) -> OrdenRead:
    ensure_branch_access(context, payload.sucursal_id)
    branch = await db.scalar(
        select(Sucursal).where(
            Sucursal.id == payload.sucursal_id,
            Sucursal.empresa_id == context.empresa_id,
            Sucursal.estado == "activo",
        )
    )
    ownership = await db.scalar(
        select(VehiculoCliente)
        .join(Cliente, Cliente.id == VehiculoCliente.cliente_id)
        .join(Vehiculo, Vehiculo.id == VehiculoCliente.vehiculo_id)
        .where(
            VehiculoCliente.empresa_id == context.empresa_id,
            VehiculoCliente.cliente_id == payload.cliente_id,
            VehiculoCliente.vehiculo_id == payload.vehiculo_id,
            VehiculoCliente.es_actual.is_(True),
            Cliente.empresa_id == context.empresa_id,
            Cliente.estado == "activo",
            Vehiculo.empresa_id == context.empresa_id,
            Vehiculo.estado == "activo",
        )
    )
    if not branch:
        raise HTTPException(status_code=404, detail="Sucursal no encontrada")
    if not ownership:
        raise HTTPException(
            status_code=409,
            detail="El vehículo no pertenece actualmente al cliente seleccionado",
        )

    await db.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
        {"key": f"orden:{context.empresa_id}:{payload.sucursal_id}"},
    )
    last_number = await db.scalar(
        select(func.coalesce(func.max(OrdenTrabajo.numero), 0)).where(
            OrdenTrabajo.empresa_id == context.empresa_id,
            OrdenTrabajo.sucursal_id == payload.sucursal_id,
        )
    )
    order = OrdenTrabajo(
        empresa_id=context.empresa_id,
        numero=int(last_number or 0) + 1,
        created_by=context.usuario.id,
        estado="recepcion",
        **payload.model_dump(),
    )
    db.add(order)
    try:
        await db.flush()
        record_order_status(
            db,
            empresa_id=context.empresa_id,
            orden_id=order.id,
            previous=None,
            current=order.estado,
            usuario_id=context.usuario.id,
            reason="Orden creada",
        )
        record_audit(
            db,
            context,
            "crear",
            "ordenes_trabajo",
            order.id,
            after={"numero": order.numero, "estado": order.estado},
        )
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=409,
            detail="No se pudo crear la orden por una restricción de los datos",
        ) from exc
    return serialize(await get_row(db, order.id, context))


@router.get("/{order_id}", response_model=OrdenRead)
async def get_orden(
    order_id: uuid.UUID,
    context: CurrentContext,
    db: AsyncSession = Depends(get_db),
) -> OrdenRead:
    return serialize(await get_row(db, order_id, context))


@router.get("/{order_id}/historial", response_model=list[OrdenEstadoHistorialRead])
async def get_order_history(
    order_id: uuid.UUID,
    context: CurrentContext,
    db: AsyncSession = Depends(get_db),
):
    await get_row(db, order_id, context)
    name = func.trim(func.concat(Usuario.nombres, " ", Usuario.apellidos))
    rows = (
        await db.execute(
            select(OrdenEstadoHistorial, name.label("usuario_nombre"))
            .join(Usuario, Usuario.id == OrdenEstadoHistorial.usuario_id)
            .where(
                OrdenEstadoHistorial.empresa_id == context.empresa_id,
                OrdenEstadoHistorial.orden_id == order_id,
            )
            .order_by(OrdenEstadoHistorial.created_at)
        )
    ).all()
    return [
        OrdenEstadoHistorialRead(
            **{column.name: getattr(item, column.name) for column in OrdenEstadoHistorial.__table__.columns},
            usuario_nombre=row.usuario_nombre,
        )
        for row in rows
        for item in [row[0]]
    ]


@router.get("/{order_id}/servicios", response_model=list[OrdenServicioRead])
async def get_order_services(
    order_id: uuid.UUID,
    context: CurrentContext,
    db: AsyncSession = Depends(get_db),
):
    await get_row(db, order_id, context)
    return list(
        (
            await db.scalars(
                select(OrdenServicio)
                .where(
                    OrdenServicio.empresa_id == context.empresa_id,
                    OrdenServicio.orden_id == order_id,
                )
                .order_by(OrdenServicio.descripcion)
            )
        ).all()
    )


@router.patch("/{order_id}/servicios/{service_id}", response_model=OrdenServicioRead, dependencies=[Depends(require_permission("ordenes.avanzar"))])
async def update_order_service(
    order_id: uuid.UUID,
    service_id: uuid.UUID,
    payload: OrdenServicioEstadoUpdate,
    context: CurrentContext,
    db: AsyncSession = Depends(get_db),
):
    row = await get_row(db, order_id, context)
    order = row[0]
    if order.estado not in {"aprobada", "en_proceso", "terminada"}:
        raise HTTPException(status_code=409, detail="La orden no está disponible para ejecutar servicios")
    service = await db.scalar(
        select(OrdenServicio).where(
            OrdenServicio.id == service_id,
            OrdenServicio.orden_id == order_id,
            OrdenServicio.empresa_id == context.empresa_id,
        )
    )
    if not service:
        raise HTTPException(status_code=404, detail="Servicio de la orden no encontrado")
    service.estado = payload.estado
    await db.commit()
    await db.refresh(service)
    return service


@router.patch("/{order_id}", response_model=OrdenRead, dependencies=[Depends(require_permission("ordenes.editar"))])
async def update_orden(
    order_id: uuid.UUID,
    payload: OrdenUpdate,
    context: CurrentContext,
    db: AsyncSession = Depends(get_db),
) -> OrdenRead:
    row = await get_row(db, order_id, context)
    order = row[0]
    if order.estado in {"entregada", "cancelada"}:
        raise HTTPException(status_code=409, detail="La orden ya está cerrada")
    before = serialize(row).model_dump(mode="json")
    for key, value in payload.model_dump(exclude_unset=True).items():
        if isinstance(value, str):
            value = value.strip() or None
        setattr(order, key, value)
    await db.flush()
    record_audit(
        db,
        context,
        "actualizar",
        "ordenes_trabajo",
        order.id,
        before=before,
        after={"estado": order.estado, **payload.model_dump(mode="json", exclude_unset=True)},
    )
    await db.commit()
    return serialize(await get_row(db, order.id, context))


@router.patch("/{order_id}/estado", response_model=OrdenRead, dependencies=[Depends(require_permission("ordenes.avanzar"))])
async def change_status(
    order_id: uuid.UUID,
    payload: OrdenEstadoUpdate,
    context: CurrentContext,
    db: AsyncSession = Depends(get_db),
) -> OrdenRead:
    row = await get_row(db, order_id, context)
    order = row[0]
    if context.rol.codigo in {"mecanico", "tecnico"}:
        technician_transitions = {
            ("aprobada", "en_proceso"),
            ("en_proceso", "terminada"),
            ("terminada", "en_proceso"),
        }
        if (order.estado, payload.estado) not in technician_transitions:
            raise HTTPException(
                status_code=403,
                detail="El técnico solo puede iniciar, terminar o reabrir el trabajo",
            )
    if payload.estado not in TRANSICIONES[order.estado]:
        raise HTTPException(
            status_code=409,
            detail=f"No se puede cambiar de {order.estado} a {payload.estado}",
        )
    required_inspection = {
        "diagnostico": "recepcion",
        "entregada": "entrega",
    }.get(payload.estado)
    if required_inspection:
        inspection = await db.scalar(
            select(Inspeccion.id).where(
                Inspeccion.empresa_id == context.empresa_id,
                Inspeccion.orden_id == order.id,
                Inspeccion.tipo == required_inspection,
                Inspeccion.confirmada_at.is_not(None),
            )
        )
        if not inspection:
            raise HTTPException(
                status_code=409,
                detail=f"Primero registra y confirma la inspección de {required_inspection}",
            )
    if payload.estado == "esperando_aprobacion":
        sent_quote = await db.scalar(
            select(Cotizacion.id).where(
                Cotizacion.empresa_id == context.empresa_id,
                Cotizacion.orden_id == order.id,
                Cotizacion.estado == "enviada",
            )
        )
        if not sent_quote:
            raise HTTPException(
                status_code=409,
                detail="La orden necesita una cotización enviada",
            )
    if payload.estado in {"en_proceso", "terminada", "entregada"}:
        approved_quote = await db.scalar(
            select(Cotizacion.id).where(
                Cotizacion.empresa_id == context.empresa_id,
                Cotizacion.orden_id == order.id,
                Cotizacion.estado == "aprobada",
            )
        )
        if not approved_quote:
            raise HTTPException(
                status_code=409,
                detail="La orden requiere una cotización aprobada para continuar",
            )
    if payload.estado == "terminada":
        unfinished = await db.scalar(
            select(func.count(OrdenServicio.id)).where(
                OrdenServicio.empresa_id == context.empresa_id,
                OrdenServicio.orden_id == order.id,
                OrdenServicio.estado.not_in(("terminado", "cancelado")),
            )
        )
        if unfinished:
            raise HTTPException(
                status_code=409,
                detail="Completa todos los servicios de la orden antes de terminarla",
            )
    if payload.estado == "en_proceso":
        pending_external = await db.scalar(
            select(func.count(CotizacionItem.id))
            .join(Cotizacion, Cotizacion.id == CotizacionItem.cotizacion_id)
            .where(
                Cotizacion.empresa_id == context.empresa_id,
                Cotizacion.orden_id == order.id,
                Cotizacion.estado == "aprobada",
                CotizacionItem.origen.in_(("cliente", "proveedor")),
                CotizacionItem.recibido_at.is_(None),
            )
        )
        if pending_external:
            raise HTTPException(
                status_code=409,
                detail="Aún faltan repuestos externos por recibir",
            )
    previous = order.estado
    order.estado = payload.estado
    record_order_status(
        db,
        empresa_id=context.empresa_id,
        orden_id=order.id,
        previous=previous,
        current=order.estado,
        usuario_id=context.usuario.id,
    )
    if payload.estado == "cancelada":
        now = datetime.now(timezone.utc)
        await db.execute(
            update(ReservaInventario)
            .where(
                ReservaInventario.empresa_id == context.empresa_id,
                ReservaInventario.orden_trabajo_id == order.id,
                ReservaInventario.estado == "activa",
            )
            .values(estado="cancelada", fecha_liberacion=now)
        )
    if payload.estado == "entregada":
        order.fecha_entrega = datetime.now(timezone.utc)
    if payload.estado == "terminada":
        notify(db, context.empresa_id, "orden_terminada", "Orden terminada", f"La OT-{order.numero:05d} está lista para entrega.", "/ordenes", order.sucursal_id)
    record_audit(
        db,
        context,
        "cambiar_estado",
        "ordenes_trabajo",
        order.id,
        before={"estado": previous},
        after={"estado": order.estado},
    )
    await db.commit()
    return serialize(await get_row(db, order.id, context))
