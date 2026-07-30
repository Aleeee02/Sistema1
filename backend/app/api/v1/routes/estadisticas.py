from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentContext, branch_scope
from app.db.session import get_db
from app.models.cotizacion import Cotizacion, CotizacionItem
from app.models.orden import OrdenTrabajo
from app.models.pago import Pago
from app.schemas.estadistica import EstadisticasRead

router = APIRouter()


@router.get("", response_model=EstadisticasRead)
async def statistics(
    context: CurrentContext,
    desde: date | None = Query(default=None),
    hasta: date | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    end_date = hasta or datetime.now(timezone.utc).date()
    start_date = desde or end_date - timedelta(days=29)
    start = datetime.combine(start_date, time.min, tzinfo=timezone.utc)
    end = datetime.combine(end_date + timedelta(days=1), time.min, tzinfo=timezone.utc)

    income = Decimal(await db.scalar(select(func.coalesce(func.sum(Pago.monto), 0)).where(Pago.empresa_id == context.empresa_id, branch_scope(context, Pago.sucursal_id), Pago.estado == "confirmado", Pago.created_at >= start, Pago.created_at < end)) or 0)
    receivable = Decimal(await db.scalar(select(func.coalesce(func.sum(OrdenTrabajo.saldo), 0)).where(OrdenTrabajo.empresa_id == context.empresa_id, branch_scope(context, OrdenTrabajo.sucursal_id), OrdenTrabajo.estado != "cancelada")) or 0)
    created = int(await db.scalar(select(func.count(OrdenTrabajo.id)).where(OrdenTrabajo.empresa_id == context.empresa_id, branch_scope(context, OrdenTrabajo.sucursal_id), OrdenTrabajo.created_at >= start, OrdenTrabajo.created_at < end)) or 0)
    closed = int(await db.scalar(select(func.count(OrdenTrabajo.id)).where(OrdenTrabajo.empresa_id == context.empresa_id, branch_scope(context, OrdenTrabajo.sucursal_id), OrdenTrabajo.estado == "entregada", OrdenTrabajo.fecha_entrega >= start, OrdenTrabajo.fecha_entrega < end)) or 0)
    active = int(await db.scalar(select(func.count(OrdenTrabajo.id)).where(OrdenTrabajo.empresa_id == context.empresa_id, branch_scope(context, OrdenTrabajo.sucursal_id), OrdenTrabajo.estado.not_in(("entregada", "cancelada")))) or 0)
    payments_count = int(await db.scalar(select(func.count(Pago.id)).where(Pago.empresa_id == context.empresa_id, branch_scope(context, Pago.sucursal_id), Pago.estado == "confirmado", Pago.created_at >= start, Pago.created_at < end)) or 0)

    day = func.date_trunc("day", Pago.created_at).label("day")
    daily_rows = (await db.execute(select(day, func.sum(Pago.monto).label("value")).where(Pago.empresa_id == context.empresa_id, branch_scope(context, Pago.sucursal_id), Pago.estado == "confirmado", Pago.created_at >= start, Pago.created_at < end).group_by(day).order_by(day))).all()
    state_rows = (await db.execute(select(OrdenTrabajo.estado, func.count(OrdenTrabajo.id).label("quantity")).where(OrdenTrabajo.empresa_id == context.empresa_id, branch_scope(context, OrdenTrabajo.sucursal_id)).group_by(OrdenTrabajo.estado).order_by(func.count(OrdenTrabajo.id).desc()))).all()
    service_rows = (await db.execute(select(CotizacionItem.descripcion, func.sum(CotizacionItem.cantidad).label("quantity"), func.sum(CotizacionItem.total).label("value")).join(Cotizacion, Cotizacion.id == CotizacionItem.cotizacion_id).join(OrdenTrabajo, OrdenTrabajo.id == Cotizacion.orden_id).where(Cotizacion.empresa_id == context.empresa_id, branch_scope(context, OrdenTrabajo.sucursal_id), Cotizacion.estado == "aprobada", Cotizacion.aprobada_at >= start, Cotizacion.aprobada_at < end, CotizacionItem.tipo == "servicio").group_by(CotizacionItem.descripcion).order_by(func.sum(CotizacionItem.total).desc()).limit(5))).all()
    method_rows = (await db.execute(select(Pago.metodo, func.count(Pago.id).label("quantity"), func.sum(Pago.monto).label("value")).where(Pago.empresa_id == context.empresa_id, branch_scope(context, Pago.sucursal_id), Pago.estado == "confirmado", Pago.created_at >= start, Pago.created_at < end).group_by(Pago.metodo).order_by(func.sum(Pago.monto).desc()))).all()

    return EstadisticasRead(
        ingresos=income, por_cobrar=receivable, ordenes_creadas=created,
        ordenes_cerradas=closed, ordenes_activas=active,
        ticket_promedio=income / payments_count if payments_count else Decimal("0"),
        ingresos_diarios=[{"fecha": row.day.date(), "valor": row.value} for row in daily_rows],
        ordenes_por_estado=[{"nombre": row.estado, "cantidad": row.quantity, "valor": 0} for row in state_rows],
        servicios_principales=[{"nombre": row.descripcion, "cantidad": row.quantity, "valor": row.value} for row in service_rows],
        pagos_por_metodo=[{"nombre": row.metodo, "cantidad": row.quantity, "valor": row.value} for row in method_rows],
    )
