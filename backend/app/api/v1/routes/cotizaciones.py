import uuid
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentContext, branch_scope, ensure_branch_access, require_permission
from app.db.session import get_db
from app.models.cliente import Cliente
from app.models.cotizacion import Cotizacion, CotizacionItem
from app.models.inventario import (
    Existencia,
    MovimientoInventario,
    Producto,
    ReservaInventario,
)
from app.models.inspeccion import Inspeccion
from app.models.orden import OrdenServicio, OrdenTrabajo, Servicio
from app.models.vehiculo import Vehiculo
from app.schemas.cotizacion import (
    CotizacionCreate,
    CotizacionEstadoUpdate,
    CotizacionOpciones,
    CotizacionRead,
)
from app.services.auditoria import record_audit
from app.services.notificaciones import notify
from app.services.ordenes import record_order_status

router = APIRouter()
MONEY = Decimal("0.01")


def base_query(empresa_id: uuid.UUID):
    return (
        select(
            Cotizacion,
            OrdenTrabajo.numero.label("orden_numero"),
            func.coalesce(
                Cliente.razon_social,
                func.trim(func.concat(Cliente.nombres, " ", Cliente.apellidos)),
            ).label("cliente_nombre"),
            Vehiculo.placa.label("vehiculo_placa"),
        )
        .join(OrdenTrabajo, OrdenTrabajo.id == Cotizacion.orden_id)
        .join(Cliente, Cliente.id == OrdenTrabajo.cliente_id)
        .join(Vehiculo, Vehiculo.id == OrdenTrabajo.vehiculo_id)
        .where(
            Cotizacion.empresa_id == empresa_id,
            OrdenTrabajo.empresa_id == empresa_id,
        )
    )


async def serialize(db: AsyncSession, row) -> CotizacionRead:
    quote = row[0]
    items = list(
        (
            await db.scalars(
                select(CotizacionItem)
                .where(
                    CotizacionItem.cotizacion_id == quote.id,
                    CotizacionItem.empresa_id == quote.empresa_id,
                )
                .order_by(CotizacionItem.orden_visual)
            )
        ).all()
    )
    reservations = list(
        (
            await db.scalars(
                select(ReservaInventario).where(
                    ReservaInventario.cotizacion_id == quote.id,
                    ReservaInventario.empresa_id == quote.empresa_id,
                )
            )
        ).all()
    )
    reservation_by_item = {
        reservation.cotizacion_item_id: reservation for reservation in reservations
    }
    serialized_items = []
    for item in items:
        reservation = reservation_by_item.get(item.id)
        serialized_items.append(
            {
                **{
                    column.name: getattr(item, column.name)
                    for column in CotizacionItem.__table__.columns
                },
                "reserva_id": reservation.id if reservation else None,
                "reserva_estado": reservation.estado if reservation else None,
            }
        )
    return CotizacionRead(
        **{
            column.name: getattr(quote, column.name)
            for column in Cotizacion.__table__.columns
        },
        orden_numero=row.orden_numero,
        cliente_nombre=row.cliente_nombre or "Cliente",
        vehiculo_placa=row.vehiculo_placa,
        items=serialized_items,
    )


async def find_row(db: AsyncSession, quote_id: uuid.UUID, context):
    row = (
        await db.execute(
            base_query(context.empresa_id).where(
                Cotizacion.id == quote_id,
                branch_scope(context, OrdenTrabajo.sucursal_id),
            )
        )
    ).one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Cotización no encontrada")
    return row


@router.get("/opciones/{order_id}", response_model=CotizacionOpciones)
async def quote_options(
    order_id: uuid.UUID,
    context: CurrentContext,
    db: AsyncSession = Depends(get_db),
):
    order = await db.scalar(
        select(OrdenTrabajo).where(
            OrdenTrabajo.id == order_id,
            OrdenTrabajo.empresa_id == context.empresa_id,
        )
    )
    if not order:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    ensure_branch_access(context, order.sucursal_id)
    reserved = (
        select(
            ReservaInventario.producto_id,
            func.sum(ReservaInventario.cantidad).label("cantidad"),
        )
        .where(
            ReservaInventario.empresa_id == context.empresa_id,
            ReservaInventario.sucursal_id == order.sucursal_id,
            ReservaInventario.estado == "activa",
        )
        .group_by(ReservaInventario.producto_id)
        .subquery()
    )
    rows = (
        await db.execute(
            select(
                Producto,
                Existencia.stock_actual,
                func.coalesce(reserved.c.cantidad, 0).label("stock_reservado"),
            )
            .join(
                Existencia,
                (Existencia.producto_id == Producto.id)
                & (Existencia.sucursal_id == order.sucursal_id)
                & (Existencia.empresa_id == context.empresa_id),
            )
            .outerjoin(reserved, reserved.c.producto_id == Producto.id)
            .where(
                Producto.empresa_id == context.empresa_id,
                Producto.estado == "activo",
            )
            .order_by(Producto.nombre)
        )
    ).all()
    return CotizacionOpciones(
        sucursal_id=order.sucursal_id,
        productos=[
            {
                "id": row[0].id,
                "sku": row[0].sku,
                "nombre": row[0].nombre,
                "unidad_medida": row[0].unidad_medida,
                "precio_venta": row[0].precio_venta,
                "stock_actual": row.stock_actual,
                "stock_reservado": row.stock_reservado,
                "stock_disponible": row.stock_actual - row.stock_reservado,
            }
            for row in rows
        ],
        servicios=list(
            (
                await db.scalars(
                    select(Servicio)
                    .where(
                        Servicio.empresa_id == context.empresa_id,
                        Servicio.estado == "activo",
                    )
                    .order_by(Servicio.categoria, Servicio.nombre)
                )
            ).all()
        ),
    )


@router.get("", response_model=list[CotizacionRead])
async def list_quotes(
    context: CurrentContext, db: AsyncSession = Depends(get_db)
):
    rows = (
        await db.execute(
            base_query(context.empresa_id)
            .where(branch_scope(context, OrdenTrabajo.sucursal_id))
            .order_by(Cotizacion.created_at.desc())
        )
    ).all()
    return [await serialize(db, row) for row in rows]


async def normalize_quote_items(db, payload, order, context):
    normalized = []
    for item in payload.items:
        unit_price, description = item.precio_unitario, item.descripcion.strip()
        tipo, origen, product_id, service_id = "libre", None, None, None
        chargeable, warranty = True, item.responsable_garantia
        if item.clase == "servicio":
            service = await db.scalar(select(Servicio).where(Servicio.id == item.servicio_id, Servicio.empresa_id == context.empresa_id, Servicio.estado == "activo"))
            if not service: raise HTTPException(status_code=404, detail="Servicio no encontrado")
            tipo, service_id, description, unit_price = "servicio", service.id, service.nombre, service.precio_referencia
        elif item.clase == "inventario":
            product = await db.scalar(select(Producto).where(Producto.id == item.producto_id, Producto.empresa_id == context.empresa_id, Producto.estado == "activo"))
            existence = await db.scalar(select(Existencia).where(Existencia.empresa_id == context.empresa_id, Existencia.sucursal_id == order.sucursal_id, Existencia.producto_id == item.producto_id))
            if not product or not existence: raise HTTPException(status_code=409, detail=f"{description}: no existe en el inventario de la sucursal")
            tipo, origen, product_id, description, unit_price, warranty = "producto", "inventario", product.id, product.nombre, product.precio_venta, warranty or "taller"
        elif item.clase == "cliente":
            origen, chargeable, unit_price, warranty = "cliente", False, Decimal("0"), warranty or "cliente"
        elif item.clase == "proveedor":
            origen, warranty = "proveedor", warranty or "proveedor"
        total = (item.cantidad * unit_price - item.descuento).quantize(MONEY, rounding=ROUND_HALF_UP)
        if total < 0: raise HTTPException(status_code=422, detail=f"El descuento de {description} supera su importe")
        normalized.append({"tipo": tipo, "origen": origen, "producto_id": product_id, "servicio_id": service_id, "descripcion": description, "cantidad": item.cantidad, "precio_unitario": unit_price, "descuento": item.descuento, "total": total, "es_cobrable": chargeable, "proveedor_nombre": item.proveedor_nombre, "referencia_externa": item.referencia_externa, "responsable_garantia": warranty})
    return normalized


@router.post("", response_model=CotizacionRead, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_permission("cotizaciones.editar"))])
async def create_quote(
    payload: CotizacionCreate,
    context: CurrentContext,
    db: AsyncSession = Depends(get_db),
):
    order = await db.scalar(
        select(OrdenTrabajo).where(
            OrdenTrabajo.id == payload.orden_id,
            OrdenTrabajo.empresa_id == context.empresa_id,
            OrdenTrabajo.estado.not_in(("entregada", "cancelada")),
        )
    )
    if not order:
        raise HTTPException(status_code=404, detail="Orden activa no encontrada")
    ensure_branch_access(context, order.sucursal_id)

    normalized = []
    for item in payload.items:
        unit_price = item.precio_unitario
        description = item.descripcion.strip()
        tipo = "libre"
        origen = None
        product_id = None
        chargeable = True
        warranty = item.responsable_garantia
        service_id = None
        if item.clase == "servicio":
            service = await db.scalar(
                select(Servicio).where(
                    Servicio.id == item.servicio_id,
                    Servicio.empresa_id == context.empresa_id,
                    Servicio.estado == "activo",
                )
            )
            if not service:
                raise HTTPException(status_code=404, detail="Servicio no encontrado")
            tipo, service_id = "servicio", service.id
            description, unit_price = service.nombre, service.precio_referencia
        elif item.clase == "inventario":
            product = await db.scalar(
                select(Producto).where(
                    Producto.id == item.producto_id,
                    Producto.empresa_id == context.empresa_id,
                    Producto.estado == "activo",
                )
            )
            existence = await db.scalar(
                select(Existencia).where(
                    Existencia.empresa_id == context.empresa_id,
                    Existencia.sucursal_id == order.sucursal_id,
                    Existencia.producto_id == item.producto_id,
                )
            )
            if not product or not existence:
                raise HTTPException(
                    status_code=409,
                    detail=f"{description}: no existe en el inventario de la sucursal",
                )
            tipo, origen, product_id = "producto", "inventario", product.id
            description = product.nombre
            unit_price = product.precio_venta
            warranty = warranty or "taller"
        elif item.clase == "cliente":
            origen, chargeable, unit_price, warranty = (
                "cliente",
                False,
                Decimal("0"),
                warranty or "cliente",
            )
        elif item.clase == "proveedor":
            origen = "proveedor"
            warranty = warranty or "proveedor"
        total = (
            item.cantidad * unit_price - item.descuento
        ).quantize(MONEY, rounding=ROUND_HALF_UP)
        if total < 0:
            raise HTTPException(
                status_code=422,
                detail=f"El descuento de {description} supera su importe",
            )
        normalized.append(
            {
                "tipo": tipo,
                "origen": origen,
                "producto_id": product_id,
                "servicio_id": service_id,
                "descripcion": description,
                "cantidad": item.cantidad,
                "precio_unitario": unit_price,
                "descuento": item.descuento,
                "total": total,
                "es_cobrable": chargeable,
                "proveedor_nombre": item.proveedor_nombre,
                "referencia_externa": item.referencia_externa,
                "responsable_garantia": warranty,
            }
        )

    await db.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
        {"key": f"cotizacion:{context.empresa_id}"},
    )
    number = int(
        await db.scalar(
            select(func.coalesce(func.max(Cotizacion.numero), 0)).where(
                Cotizacion.empresa_id == context.empresa_id
            )
        )
        or 0
    ) + 1
    version = int(
        await db.scalar(
            select(func.coalesce(func.max(Cotizacion.version), 0)).where(
                Cotizacion.orden_id == payload.orden_id
            )
        )
        or 0
    ) + 1
    subtotal = sum((item["total"] for item in normalized), Decimal("0"))
    if payload.descuento > subtotal:
        raise HTTPException(status_code=422, detail="El descuento supera el subtotal")
    taxable = subtotal - payload.descuento
    tax = (
        taxable * context.empresa.porcentaje_impuesto / Decimal("100")
    ).quantize(MONEY, rounding=ROUND_HALF_UP)
    quote = Cotizacion(
        empresa_id=context.empresa_id,
        orden_id=payload.orden_id,
        numero=number,
        version=version,
        subtotal=subtotal,
        descuento=payload.descuento,
        impuesto=tax,
        total=taxable + tax,
        valida_hasta=payload.valida_hasta,
        observaciones=payload.observaciones,
        created_by=context.usuario.id,
    )
    db.add(quote)
    try:
        await db.flush()
        for index, values in enumerate(normalized):
            db.add(
                CotizacionItem(
                    empresa_id=context.empresa_id,
                    cotizacion_id=quote.id,
                    orden_visual=index,
                    **values,
                )
            )
        record_audit(
            db,
            context,
            "crear",
            "cotizaciones",
            quote.id,
            after={"numero": number, "version": version, "total": str(quote.total)},
        )
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=409,
            detail="No se pudo guardar la cotización por una restricción de los datos",
        ) from exc
    return await serialize(
        db, await find_row(db, quote.id, context)
    )


@router.patch("/{quote_id}", response_model=CotizacionRead, dependencies=[Depends(require_permission("cotizaciones.editar"))])
async def update_quote(
    quote_id: uuid.UUID,
    payload: CotizacionCreate,
    context: CurrentContext,
    db: AsyncSession = Depends(get_db),
):
    row = await find_row(db, quote_id, context)
    quote = row[0]
    if quote.estado != "borrador":
        raise HTTPException(status_code=409, detail="Solo se puede editar una cotización en borrador")
    if payload.orden_id != quote.orden_id:
        raise HTTPException(status_code=409, detail="No se puede cambiar la OT de la cotización")
    order = await db.scalar(select(OrdenTrabajo).where(OrdenTrabajo.id == quote.orden_id, OrdenTrabajo.empresa_id == context.empresa_id, OrdenTrabajo.estado.not_in(("entregada", "cancelada"))))
    if not order:
        raise HTTPException(status_code=404, detail="Orden activa no encontrada")
    normalized = await normalize_quote_items(db, payload, order, context)
    subtotal = sum((item["total"] for item in normalized), Decimal("0"))
    if payload.descuento > subtotal:
        raise HTTPException(status_code=422, detail="El descuento supera el subtotal")
    taxable = subtotal - payload.descuento
    tax = (taxable * context.empresa.porcentaje_impuesto / Decimal("100")).quantize(MONEY, rounding=ROUND_HALF_UP)
    await db.execute(delete(CotizacionItem).where(CotizacionItem.cotizacion_id == quote.id, CotizacionItem.empresa_id == context.empresa_id))
    quote.subtotal, quote.descuento, quote.impuesto, quote.total = subtotal, payload.descuento, tax, taxable + tax
    quote.valida_hasta, quote.observaciones = payload.valida_hasta, payload.observaciones
    for index, values in enumerate(normalized):
        db.add(CotizacionItem(empresa_id=context.empresa_id, cotizacion_id=quote.id, orden_visual=index, **values))
    record_audit(db, context, "actualizar", "cotizaciones", quote.id, after={"total": str(quote.total), "items": len(normalized)})
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail="No se pudo actualizar la cotización") from exc
    return await serialize(db, await find_row(db, quote.id, context))


async def create_reservations(
    db: AsyncSession,
    quote: Cotizacion,
    order: OrdenTrabajo,
    context: CurrentContext,
) -> None:
    items = list(
        (
            await db.scalars(
                select(CotizacionItem).where(
                    CotizacionItem.cotizacion_id == quote.id,
                    CotizacionItem.empresa_id == context.empresa_id,
                    CotizacionItem.origen == "inventario",
                )
            )
        ).all()
    )
    for item in items:
        existence = await db.scalar(
            select(Existencia)
            .where(
                Existencia.empresa_id == context.empresa_id,
                Existencia.sucursal_id == order.sucursal_id,
                Existencia.producto_id == item.producto_id,
            )
            .with_for_update()
        )
        if not existence:
            raise HTTPException(status_code=409, detail=f"Sin existencia: {item.descripcion}")
        reserved = await db.scalar(
            select(func.coalesce(func.sum(ReservaInventario.cantidad), 0)).where(
                ReservaInventario.empresa_id == context.empresa_id,
                ReservaInventario.sucursal_id == order.sucursal_id,
                ReservaInventario.producto_id == item.producto_id,
                ReservaInventario.estado == "activa",
            )
        )
        available = existence.stock_actual - Decimal(reserved or 0)
        if available < item.cantidad:
            raise HTTPException(
                status_code=409,
                detail=f"Stock insuficiente para {item.descripcion}. Disponible: {available}",
            )
        db.add(
            ReservaInventario(
                empresa_id=context.empresa_id,
                sucursal_id=order.sucursal_id,
                producto_id=item.producto_id,
                cotizacion_id=quote.id,
                cotizacion_item_id=item.id,
                orden_trabajo_id=order.id,
                cantidad=item.cantidad,
                reservada_por=context.usuario.id,
                estado="activa",
            )
        )


@router.patch("/{quote_id}/estado", response_model=CotizacionRead, dependencies=[Depends(require_permission("cotizaciones.cambiar_estado"))])
async def change_quote_status(
    quote_id: uuid.UUID,
    payload: CotizacionEstadoUpdate,
    context: CurrentContext,
    db: AsyncSession = Depends(get_db),
):
    row = await find_row(db, quote_id, context)
    quote = row[0]
    allowed = {"borrador": {"enviada"}, "enviada": {"aprobada", "rechazada"}}
    if payload.estado not in allowed.get(quote.estado, set()):
        raise HTTPException(status_code=409, detail="Cambio de estado no permitido")
    order = await db.scalar(
        select(OrdenTrabajo).where(
            OrdenTrabajo.id == quote.orden_id,
            OrdenTrabajo.empresa_id == context.empresa_id,
        )
    )
    if not order:
        raise HTTPException(status_code=404, detail="Orden vinculada no encontrada")
    if payload.estado in {"enviada", "aprobada"}:
        service_item = await db.scalar(
            select(CotizacionItem.id).where(
                CotizacionItem.cotizacion_id == quote.id,
                CotizacionItem.empresa_id == context.empresa_id,
                CotizacionItem.tipo == "servicio",
                CotizacionItem.servicio_id.is_not(None),
            )
        )
        if not service_item:
            raise HTTPException(
                status_code=409,
                detail="La cotización necesita al menos un servicio de mano de obra",
            )
        confirmed_inspection = await db.scalar(
            select(Inspeccion.id).where(
                Inspeccion.empresa_id == context.empresa_id,
                Inspeccion.orden_id == order.id,
                Inspeccion.tipo == "diagnostico",
                Inspeccion.confirmada_at.is_not(None),
            )
        )
        if not confirmed_inspection:
            raise HTTPException(
                status_code=409,
                detail="Primero registra y confirma la inspección de diagnóstico de la OT",
            )
    if payload.estado == "enviada" and order.estado != "diagnostico":
        raise HTTPException(
            status_code=409,
            detail="La orden debe estar en diagnóstico para enviar la cotización",
        )
    if (
        payload.estado in {"aprobada", "rechazada"}
        and order.estado != "esperando_aprobacion"
    ):
        raise HTTPException(status_code=409, detail="La orden no está esperando aprobación")
    previous = quote.estado
    order_previous = order.estado
    now = datetime.now(timezone.utc)
    if payload.estado == "enviada":
        quote.enviada_at = now
        order.estado = "esperando_aprobacion"
    elif payload.estado == "aprobada":
        await create_reservations(db, quote, order, context)
        await db.execute(
            delete(OrdenServicio).where(
                OrdenServicio.empresa_id == context.empresa_id,
                OrdenServicio.orden_id == order.id,
            )
        )
        approved_services = (
            await db.scalars(
                select(CotizacionItem).where(
                    CotizacionItem.empresa_id == context.empresa_id,
                    CotizacionItem.cotizacion_id == quote.id,
                    CotizacionItem.tipo == "servicio",
                )
            )
        ).all()
        for item in approved_services:
            db.add(
                OrdenServicio(
                    empresa_id=context.empresa_id,
                    orden_id=order.id,
                    servicio_id=item.servicio_id,
                    descripcion=item.descripcion,
                    cantidad=item.cantidad,
                    precio_unitario=item.precio_unitario,
                    descuento=item.descuento,
                    total=item.total,
                    estado="pendiente",
                )
            )
        quote.aprobada_at = now
        quote.aprobada_por = payload.aprobada_por or "Cliente"
        order.estado = "aprobada"
        order.subtotal, order.descuento = quote.subtotal, quote.descuento
        order.impuesto, order.total, order.saldo = quote.impuesto, quote.total, quote.total
    else:
        order.estado = "diagnostico"
    quote.estado = payload.estado
    record_order_status(
        db,
        empresa_id=context.empresa_id,
        orden_id=order.id,
        previous=order_previous,
        current=order.estado,
        usuario_id=context.usuario.id,
        reason=f"Cotización {payload.estado}",
    )
    if payload.estado in {"aprobada", "rechazada"}:
        notify(db, context.empresa_id, f"cotizacion_{payload.estado}", f"Cotización {payload.estado}", f"La cotización COT-{quote.numero:05d} fue {payload.estado}.", "/cotizaciones", order.sucursal_id)
    record_audit(
        db,
        context,
        "cambiar_estado",
        "cotizaciones",
        quote.id,
        before={"estado": previous},
        after={"estado": quote.estado},
    )
    await db.commit()
    return await serialize(db, await find_row(db, quote.id, context))


@router.post("/{quote_id}/items/{item_id}/recibir", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_permission("cotizaciones.recibir"))])
async def receive_external_item(
    quote_id: uuid.UUID,
    item_id: uuid.UUID,
    context: CurrentContext,
    db: AsyncSession = Depends(get_db),
):
    item = await db.scalar(
        select(CotizacionItem)
        .join(Cotizacion, Cotizacion.id == CotizacionItem.cotizacion_id)
        .where(
            CotizacionItem.id == item_id,
            CotizacionItem.cotizacion_id == quote_id,
            CotizacionItem.empresa_id == context.empresa_id,
            CotizacionItem.origen.in_(("cliente", "proveedor")),
        )
    )
    if not item:
        raise HTTPException(status_code=404, detail="Repuesto externo no encontrado")
    quote = await db.scalar(select(Cotizacion).where(Cotizacion.id == quote_id, Cotizacion.empresa_id == context.empresa_id))
    order = await db.scalar(select(OrdenTrabajo).where(OrdenTrabajo.id == quote.orden_id, OrdenTrabajo.empresa_id == context.empresa_id)) if quote else None
    if not order:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    ensure_branch_access(context, order.sucursal_id)
    item.recibido_at = datetime.now(timezone.utc)
    await db.commit()


@router.post("/reservas/{reservation_id}/consumir", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_permission("reservas.consumir"))])
async def consume_reservation(
    reservation_id: uuid.UUID,
    context: CurrentContext,
    db: AsyncSession = Depends(get_db),
):
    reservation = await db.scalar(
        select(ReservaInventario)
        .where(
            ReservaInventario.id == reservation_id,
            ReservaInventario.empresa_id == context.empresa_id,
            ReservaInventario.estado == "activa",
        )
        .with_for_update()
    )
    if not reservation:
        raise HTTPException(status_code=404, detail="Reserva activa no encontrada")
    ensure_branch_access(context, reservation.sucursal_id)
    existence = await db.scalar(
        select(Existencia)
        .where(
            Existencia.empresa_id == context.empresa_id,
            Existencia.sucursal_id == reservation.sucursal_id,
            Existencia.producto_id == reservation.producto_id,
        )
        .with_for_update()
    )
    if not existence or existence.stock_actual < reservation.cantidad:
        raise HTTPException(status_code=409, detail="Stock físico insuficiente")
    previous = existence.stock_actual
    resulting = previous - reservation.cantidad
    existence.stock_actual = resulting
    reservation.estado = "consumida"
    reservation.fecha_consumo = datetime.now(timezone.utc)
    db.add(
        MovimientoInventario(
            empresa_id=context.empresa_id,
            existencia_id=existence.id,
            orden_id=reservation.orden_trabajo_id,
            tipo="salida",
            cantidad=reservation.cantidad,
            costo_unitario=0,
            stock_anterior=previous,
            stock_resultante=resulting,
            motivo="Consumo de repuesto reservado para OT",
            usuario_id=context.usuario.id,
        )
    )
    await db.commit()
