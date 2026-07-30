import io
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, status
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentContext, branch_scope, ensure_branch_access
from app.db.session import get_db
from app.models.cliente import Cliente
from app.models.comprobante import Comprobante, ComprobanteItem
from app.models.cotizacion import Cotizacion, CotizacionItem
from app.models.empresa import Sucursal
from app.models.orden import OrdenTrabajo
from app.models.vehiculo import Vehiculo
from app.schemas.comprobante import ComprobanteAnular, ComprobanteCreate, ComprobanteRead, OrdenComprobanteOpcion
from app.services.auditoria import record_audit

router = APIRouter()


def client_name():
    return func.coalesce(Cliente.razon_social, func.trim(func.concat(Cliente.nombres, " ", Cliente.apellidos)))


def base_query(empresa_id):
    return select(Comprobante, Sucursal.nombre.label("sucursal_nombre")).join(Sucursal, Sucursal.id == Comprobante.sucursal_id).where(Comprobante.empresa_id == empresa_id)


def serialize(row):
    value = row[0]
    return ComprobanteRead(
        id=value.id, orden_id=value.orden_id, sucursal_id=value.sucursal_id,
        sucursal_nombre=row.sucursal_nombre, tipo=value.tipo, serie=value.serie,
        numero=value.numero, estado=value.estado, cliente_nombre=value.cliente_nombre,
        cliente_documento=value.cliente_documento, moneda=value.moneda,
        total=value.total, emitido_at=value.emitido_at,
        motivo_anulacion=value.motivo_anulacion,
    )


async def find_row(db, comprobante_id, context):
    row = (await db.execute(base_query(context.empresa_id).where(Comprobante.id == comprobante_id, branch_scope(context, Comprobante.sucursal_id)))).one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Comprobante no encontrado")
    return row


@router.get("/ordenes-disponibles", response_model=list[OrdenComprobanteOpcion])
async def available_orders(context: CurrentContext, db: AsyncSession = Depends(get_db)):
    issued = select(Comprobante.orden_id).where(Comprobante.empresa_id == context.empresa_id, Comprobante.estado == "emitido")
    rows = (await db.execute(
        select(OrdenTrabajo, Sucursal.nombre.label("sucursal_nombre"), client_name().label("cliente_nombre"), Cliente.numero_documento)
        .join(Sucursal, Sucursal.id == OrdenTrabajo.sucursal_id)
        .join(Cliente, Cliente.id == OrdenTrabajo.cliente_id)
        .where(
            OrdenTrabajo.empresa_id == context.empresa_id,
            branch_scope(context, OrdenTrabajo.sucursal_id),
            OrdenTrabajo.total > 0, OrdenTrabajo.saldo == 0,
            OrdenTrabajo.id.not_in(issued),
        ).order_by(OrdenTrabajo.fecha_recepcion.desc())
    )).all()
    return [OrdenComprobanteOpcion(id=row[0].id, numero=row[0].numero, sucursal_nombre=row.sucursal_nombre, cliente_nombre=row.cliente_nombre, cliente_documento=row.numero_documento, total=row[0].total) for row in rows]


@router.get("", response_model=list[ComprobanteRead])
async def list_receipts(context: CurrentContext, db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(base_query(context.empresa_id).where(branch_scope(context, Comprobante.sucursal_id)).order_by(Comprobante.emitido_at.desc()))).all()
    return [serialize(row) for row in rows]


@router.post("", response_model=ComprobanteRead, status_code=status.HTTP_201_CREATED)
async def create_receipt(payload: ComprobanteCreate, context: CurrentContext, db: AsyncSession = Depends(get_db)):
    row = (await db.execute(
        select(OrdenTrabajo, Cliente)
        .join(Cliente, Cliente.id == OrdenTrabajo.cliente_id)
        .where(OrdenTrabajo.id == payload.orden_id, OrdenTrabajo.empresa_id == context.empresa_id)
        .with_for_update()
    )).one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    order, customer = row
    ensure_branch_access(context, order.sucursal_id)
    if order.total <= 0 or order.saldo != 0:
        raise HTTPException(status_code=409, detail="La orden debe estar pagada completamente")
    if payload.tipo == "factura" and (customer.tipo_documento != "ruc" or len(customer.numero_documento) != 11 or not customer.razon_social):
        raise HTTPException(status_code=422, detail="La factura requiere un cliente con RUC y razón social")
    if await db.scalar(select(Comprobante.id).where(Comprobante.orden_id == order.id, Comprobante.estado == "emitido")):
        raise HTTPException(status_code=409, detail="La orden ya tiene un comprobante emitido")
    quote = await db.scalar(select(Cotizacion).where(Cotizacion.orden_id == order.id, Cotizacion.empresa_id == context.empresa_id, Cotizacion.estado == "aprobada").order_by(Cotizacion.version.desc()))
    if not quote:
        raise HTTPException(status_code=409, detail="La orden no tiene una cotización aprobada")
    prefix = {"boleta": "B", "factura": "F", "nota_venta": "N"}[payload.tipo]
    series = f"{prefix}{str(order.sucursal_id).replace('-', '')[:3].upper()}"
    await db.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"), {"key": f"comprobante:{context.empresa_id}:{series}"})
    number = int(await db.scalar(select(func.coalesce(func.max(Comprobante.numero), 0)).where(Comprobante.empresa_id == context.empresa_id, Comprobante.serie == series)) or 0) + 1
    name = customer.razon_social or f"{customer.nombres or ''} {customer.apellidos or ''}".strip()
    receipt = Comprobante(
        empresa_id=context.empresa_id, sucursal_id=order.sucursal_id,
        orden_id=order.id, cliente_id=customer.id, tipo=payload.tipo,
        serie=series, numero=number, cliente_nombre=name,
        cliente_documento=customer.numero_documento,
        cliente_direccion=customer.direccion, moneda=context.empresa.moneda,
        subtotal=order.subtotal, descuento=order.descuento,
        impuesto=order.impuesto, total=order.total,
        observaciones=payload.observaciones, emitido_por=context.usuario.id,
    )
    db.add(receipt); await db.flush()
    items = (await db.scalars(select(CotizacionItem).where(CotizacionItem.cotizacion_id == quote.id, CotizacionItem.es_cobrable.is_(True)).order_by(CotizacionItem.orden_visual))).all()
    for item in items:
        db.add(ComprobanteItem(empresa_id=context.empresa_id, comprobante_id=receipt.id, descripcion=item.descripcion, cantidad=item.cantidad, precio_unitario=item.precio_unitario, descuento=item.descuento, total=item.total))
    record_audit(db, context, "emitir", "comprobantes", receipt.id, after={"tipo": receipt.tipo, "serie": series, "numero": number})
    await db.commit()
    return serialize(await find_row(db, receipt.id, context))


@router.post("/{comprobante_id}/anular", response_model=ComprobanteRead)
async def cancel_receipt(comprobante_id: uuid.UUID, payload: ComprobanteAnular, context: CurrentContext, db: AsyncSession = Depends(get_db)):
    row = await find_row(db, comprobante_id, context)
    receipt = row[0]
    if receipt.estado == "anulado":
        raise HTTPException(status_code=409, detail="El comprobante ya está anulado")
    receipt.estado = "anulado"; receipt.anulado_at = datetime.now(timezone.utc); receipt.motivo_anulacion = payload.motivo.strip()
    record_audit(db, context, "anular", "comprobantes", receipt.id, after={"motivo": receipt.motivo_anulacion})
    await db.commit()
    return serialize(await find_row(db, receipt.id, context))


@router.get("/{comprobante_id}/pdf")
async def receipt_pdf(comprobante_id: uuid.UUID, context: CurrentContext, db: AsyncSession = Depends(get_db)):
    row = await find_row(db, comprobante_id, context)
    receipt = row[0]
    order_number = await db.scalar(
        select(OrdenTrabajo.numero).where(
            OrdenTrabajo.id == receipt.orden_id,
            OrdenTrabajo.empresa_id == context.empresa_id,
        )
    )
    if order_number is None:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    items = (await db.scalars(select(ComprobanteItem).where(ComprobanteItem.comprobante_id == receipt.id).order_by(ComprobanteItem.descripcion))).all()
    buffer = io.BytesIO()
    document = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=18*mm, leftMargin=18*mm, topMargin=16*mm, bottomMargin=16*mm)
    styles = getSampleStyleSheet()
    title = {"boleta": "BOLETA INTERNA", "factura": "FACTURA INTERNA", "nota_venta": "NOTA DE VENTA"}[receipt.tipo]
    story = [Paragraph(context.empresa.nombre_comercial, styles["Title"]), Paragraph(context.empresa.razon_social, styles["Normal"]), Paragraph(f"RUC: {context.empresa.ruc}", styles["Normal"]), Spacer(1, 6*mm), Paragraph(title, styles["Heading1"]), Paragraph(f"{receipt.serie}-{receipt.numero:08d}", styles["Heading2"]), Paragraph("<b>SIN VALIDEZ TRIBUTARIA - NO ES COMPROBANTE SUNAT</b>", styles["Normal"]), Spacer(1, 5*mm), Paragraph(f"Cliente: {receipt.cliente_nombre}", styles["Normal"]), Paragraph(f"Documento: {receipt.cliente_documento}", styles["Normal"]), Paragraph(f"OT: {context.empresa.prefijo_orden}-{order_number:05d}", styles["Normal"]), Spacer(1, 5*mm)]
    data = [["Descripción", "Cant.", "P. unit.", "Desc.", "Total"]] + [[item.descripcion, f"{item.cantidad:.2f}", f"S/ {item.precio_unitario:.2f}", f"S/ {item.descuento:.2f}", f"S/ {item.total:.2f}"] for item in items]
    table = Table(data, colWidths=[82*mm, 18*mm, 25*mm, 22*mm, 25*mm], repeatRows=1)
    table.setStyle(TableStyle([("BACKGROUND", (0,0), (-1,0), colors.HexColor(context.empresa.color_primario)), ("TEXTCOLOR", (0,0), (-1,0), colors.white), ("GRID", (0,0), (-1,-1), .4, colors.grey), ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"), ("ALIGN", (1,1), (-1,-1), "RIGHT"), ("VALIGN", (0,0), (-1,-1), "TOP"), ("FONTSIZE", (0,0), (-1,-1), 8), ("PADDING", (0,0), (-1,-1), 5)]))
    story += [table, Spacer(1, 5*mm), Table([["Subtotal", f"S/ {receipt.subtotal:.2f}"], ["Descuento", f"S/ {receipt.descuento:.2f}"], ["Impuesto", f"S/ {receipt.impuesto:.2f}"], ["TOTAL", f"S/ {receipt.total:.2f}"]], colWidths=[120*mm, 35*mm], style=[("ALIGN", (1,0), (1,-1), "RIGHT"), ("FONTNAME", (0,-1), (-1,-1), "Helvetica-Bold"), ("LINEABOVE", (0,-1), (-1,-1), 1, colors.black)])]
    if receipt.estado == "anulado":
        story += [Spacer(1, 8*mm), Paragraph(f"ANULADO: {receipt.motivo_anulacion}", styles["Heading2"])]
    document.build(story)
    return Response(buffer.getvalue(), media_type="application/pdf", headers={"Content-Disposition": f'inline; filename="{receipt.serie}-{receipt.numero:08d}.pdf"'})
