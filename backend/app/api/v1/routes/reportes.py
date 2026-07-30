import csv
import io
import uuid
from datetime import date, datetime, time, timedelta, timezone

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentContext, branch_scope, ensure_branch_access
from app.db.session import get_db
from app.models.cliente import Cliente
from app.models.empresa import Sucursal
from app.models.inventario import Existencia, Producto
from app.models.orden import OrdenTrabajo
from app.models.pago import Pago
from app.models.vehiculo import Vehiculo

router = APIRouter()


def csv_response(filename: str, headers: list[str], rows: list[list]) -> Response:
    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")
    writer.writerow(headers)
    writer.writerows(rows)
    content = "\ufeff" + output.getvalue()
    return Response(content=content.encode("utf-8"), media_type="text/csv; charset=utf-8", headers={"Content-Disposition": f'attachment; filename="{filename}"'})


def bounds(desde: date | None, hasta: date | None):
    end_date = hasta or datetime.now(timezone.utc).date()
    start_date = desde or end_date - timedelta(days=29)
    return datetime.combine(start_date, time.min, tzinfo=timezone.utc), datetime.combine(end_date + timedelta(days=1), time.min, tzinfo=timezone.utc)


def customer_name():
    return func.coalesce(Cliente.razon_social, func.trim(func.concat(Cliente.nombres, " ", Cliente.apellidos)))


@router.get("/ordenes")
async def orders_report(context: CurrentContext, desde: date | None = None, hasta: date | None = None, sucursal_id: uuid.UUID | None = Query(default=None), db: AsyncSession = Depends(get_db)):
    start, end = bounds(desde, hasta)
    query = select(OrdenTrabajo, customer_name().label("cliente"), Vehiculo.placa, Sucursal.nombre.label("sucursal")).join(Cliente, Cliente.id == OrdenTrabajo.cliente_id).join(Vehiculo, Vehiculo.id == OrdenTrabajo.vehiculo_id).join(Sucursal, Sucursal.id == OrdenTrabajo.sucursal_id).where(OrdenTrabajo.empresa_id == context.empresa_id, branch_scope(context, OrdenTrabajo.sucursal_id), OrdenTrabajo.fecha_recepcion >= start, OrdenTrabajo.fecha_recepcion < end).order_by(OrdenTrabajo.fecha_recepcion)
    if sucursal_id:
        ensure_branch_access(context, sucursal_id)
        query = query.where(OrdenTrabajo.sucursal_id == sucursal_id)
    data = (await db.execute(query)).all()
    rows = [[row[0].numero, row.sucursal, row.cliente, row.placa, row[0].estado, row[0].falla_reportada or "", row[0].total, row[0].saldo, row[0].fecha_recepcion.isoformat(), row[0].fecha_entrega.isoformat() if row[0].fecha_entrega else ""] for row in data]
    return csv_response("ordenes_trabajo.csv", ["OT", "Sucursal", "Cliente", "Placa", "Estado", "Falla reportada", "Total", "Saldo", "Recepción", "Entrega"], rows)


@router.get("/pagos")
async def payments_report(context: CurrentContext, desde: date | None = None, hasta: date | None = None, sucursal_id: uuid.UUID | None = Query(default=None), db: AsyncSession = Depends(get_db)):
    start, end = bounds(desde, hasta)
    query = select(Pago, OrdenTrabajo.numero.label("ot"), customer_name().label("cliente"), Vehiculo.placa, Sucursal.nombre.label("sucursal")).join(OrdenTrabajo, OrdenTrabajo.id == Pago.orden_id).join(Cliente, Cliente.id == OrdenTrabajo.cliente_id).join(Vehiculo, Vehiculo.id == OrdenTrabajo.vehiculo_id).join(Sucursal, Sucursal.id == Pago.sucursal_id).where(Pago.empresa_id == context.empresa_id, branch_scope(context, Pago.sucursal_id), Pago.created_at >= start, Pago.created_at < end).order_by(Pago.created_at)
    if sucursal_id:
        ensure_branch_access(context, sucursal_id)
        query = query.where(Pago.sucursal_id == sucursal_id)
    data = (await db.execute(query)).all()
    rows = [[row[0].numero, row.ot, row.sucursal, row.cliente, row.placa, row[0].metodo, row[0].monto, row[0].referencia or "", row[0].estado, row[0].created_at.isoformat(), row[0].motivo_anulacion or ""] for row in data]
    return csv_response("pagos.csv", ["Pago", "OT", "Sucursal", "Cliente", "Placa", "Método", "Monto", "Referencia", "Estado", "Fecha", "Motivo anulación"], rows)


@router.get("/inventario")
async def inventory_report(context: CurrentContext, sucursal_id: uuid.UUID | None = Query(default=None), db: AsyncSession = Depends(get_db)):
    query = select(Producto, Existencia, Sucursal.nombre.label("sucursal")).join(Existencia, Existencia.producto_id == Producto.id).join(Sucursal, Sucursal.id == Existencia.sucursal_id).where(Producto.empresa_id == context.empresa_id, Existencia.empresa_id == context.empresa_id, branch_scope(context, Existencia.sucursal_id)).order_by(Sucursal.nombre, Producto.nombre)
    if sucursal_id:
        ensure_branch_access(context, sucursal_id)
        query = query.where(Existencia.sucursal_id == sucursal_id)
    data = (await db.execute(query)).all()
    rows = [[row.sucursal, row[0].sku, row[0].nombre, row[0].categoria or "", row[0].unidad_medida, row[1].stock_actual, row[1].stock_minimo, row[1].stock_maximo or "", row[0].costo_promedio, row[0].precio_venta, row[1].stock_actual * row[0].costo_promedio, "BAJO" if row[1].stock_actual <= row[1].stock_minimo else "OK"] for row in data]
    return csv_response("inventario.csv", ["Sucursal", "SKU", "Producto", "Categoría", "Unidad", "Stock", "Mínimo", "Máximo", "Costo", "Precio venta", "Valor a costo", "Nivel"], rows)
