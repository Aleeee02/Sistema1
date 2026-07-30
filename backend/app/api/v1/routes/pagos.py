import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentContext, branch_scope, ensure_branch_access, require_permission
from app.db.session import get_db
from app.models.cliente import Cliente
from app.models.empresa import Sucursal
from app.models.orden import OrdenTrabajo
from app.models.pago import MetodoPagoConfig, Pago
from app.models.vehiculo import Vehiculo
from app.schemas.pago import CuentaCobrar, MetodoPagoConfigRead, MetodoPagoConfigUpdate, PagoAnular, PagoCreate, PagoRead
from app.services.auditoria import record_audit

router = APIRouter()
DEFAULT_METHODS = {
    "efectivo": "Efectivo", "tarjeta": "Tarjeta / POS", "transferencia": "Transferencia",
    "yape": "Yape", "plin": "Plin", "otro": "Otro",
}


@router.get("/metodos", response_model=list[MetodoPagoConfigRead])
async def list_methods(context: CurrentContext, db: AsyncSession = Depends(get_db)):
    rows = {row.metodo: row for row in (await db.scalars(select(MetodoPagoConfig).where(MetodoPagoConfig.empresa_id == context.empresa_id))).all()}
    return [MetodoPagoConfigRead(id=rows[key].id if key in rows else None, metodo=key, activo=rows[key].activo if key in rows else key == "efectivo", nombre_mostrar=rows[key].nombre_mostrar if key in rows else label, configuracion=rows[key].configuracion if key in rows else {}) for key, label in DEFAULT_METHODS.items()]


@router.put("/metodos", response_model=list[MetodoPagoConfigRead], dependencies=[Depends(require_permission("pagos.configurar"))])
async def save_methods(payload: list[MetodoPagoConfigUpdate], context: CurrentContext, db: AsyncSession = Depends(get_db)):
    if len({item.metodo for item in payload}) != len(payload):
        raise HTTPException(status_code=422, detail="Hay métodos duplicados")
    for item in payload:
        config = item.configuracion
        if item.activo and item.metodo in {"yape", "plin"} and not (config.get("numero") or config.get("qr_url")):
            raise HTTPException(status_code=422, detail=f"{item.nombre_mostrar} necesita un número o una URL de QR")
        if item.activo and item.metodo == "transferencia" and not (config.get("cuenta") or config.get("cci")):
            raise HTTPException(status_code=422, detail="La transferencia necesita número de cuenta o CCI")
    existing = {row.metodo: row for row in (await db.scalars(select(MetodoPagoConfig).where(MetodoPagoConfig.empresa_id == context.empresa_id))).all()}
    for item in payload:
        values = item.model_dump()
        if item.metodo in existing:
            for key, value in values.items(): setattr(existing[item.metodo], key, value)
            existing[item.metodo].updated_at = datetime.now(timezone.utc)
        else:
            db.add(MetodoPagoConfig(empresa_id=context.empresa_id, **values))
    await db.commit()
    return await list_methods(context, db)


def customer_name():
    return func.coalesce(Cliente.razon_social, func.trim(func.concat(Cliente.nombres, " ", Cliente.apellidos)))


def payment_query(empresa_id: uuid.UUID):
    return (
        select(Pago, OrdenTrabajo.numero.label("orden_numero"), customer_name().label("cliente_nombre"), Vehiculo.placa.label("vehiculo_placa"), Sucursal.nombre.label("sucursal_nombre"))
        .join(OrdenTrabajo, OrdenTrabajo.id == Pago.orden_id)
        .join(Cliente, Cliente.id == OrdenTrabajo.cliente_id)
        .join(Vehiculo, Vehiculo.id == OrdenTrabajo.vehiculo_id)
        .join(Sucursal, Sucursal.id == Pago.sucursal_id)
        .where(Pago.empresa_id == empresa_id)
    )


def payment_read(row) -> PagoRead:
    payment = row[0]
    return PagoRead(**{column.name: getattr(payment, column.name) for column in Pago.__table__.columns}, orden_numero=row.orden_numero, cliente_nombre=row.cliente_nombre, vehiculo_placa=row.vehiculo_placa, sucursal_nombre=row.sucursal_nombre)


@router.get("/cuentas", response_model=list[CuentaCobrar])
async def accounts(context: CurrentContext, db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(
        select(OrdenTrabajo, customer_name().label("cliente_nombre"), Vehiculo.placa.label("vehiculo_placa"), Sucursal.nombre.label("sucursal_nombre"))
        .join(Cliente, Cliente.id == OrdenTrabajo.cliente_id).join(Vehiculo, Vehiculo.id == OrdenTrabajo.vehiculo_id).join(Sucursal, Sucursal.id == OrdenTrabajo.sucursal_id)
        .where(OrdenTrabajo.empresa_id == context.empresa_id, branch_scope(context, OrdenTrabajo.sucursal_id), OrdenTrabajo.total > 0, OrdenTrabajo.estado.not_in(("borrador", "recepcion", "diagnostico", "esperando_aprobacion", "cancelada")))
        .order_by(OrdenTrabajo.saldo.desc(), OrdenTrabajo.fecha_recepcion.desc())
    )).all()
    return [CuentaCobrar(orden_id=row[0].id, orden_numero=row[0].numero, sucursal_id=row[0].sucursal_id, sucursal_nombre=row.sucursal_nombre, cliente_nombre=row.cliente_nombre, vehiculo_placa=row.vehiculo_placa, estado=row[0].estado, total=row[0].total, saldo=row[0].saldo) for row in rows]


@router.get("", response_model=list[PagoRead])
async def list_payments(context: CurrentContext, db: AsyncSession = Depends(get_db)):
    query = payment_query(context.empresa_id).where(branch_scope(context, Pago.sucursal_id)).order_by(Pago.created_at.desc())
    return [payment_read(row) for row in (await db.execute(query)).all()]


@router.post("", response_model=PagoRead, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_permission("pagos.registrar"))])
async def create_payment(payload: PagoCreate, context: CurrentContext, db: AsyncSession = Depends(get_db)):
    method = await db.scalar(select(MetodoPagoConfig).where(MetodoPagoConfig.empresa_id == context.empresa_id, MetodoPagoConfig.metodo == payload.metodo))
    configured_count = await db.scalar(select(func.count(MetodoPagoConfig.id)).where(MetodoPagoConfig.empresa_id == context.empresa_id))
    if (method and not method.activo) or (not method and (configured_count or payload.metodo != "efectivo")):
        raise HTTPException(status_code=409, detail="Este método de pago no está habilitado")
    if payload.metodo == "efectivo" and not payload.efectivo_confirmado:
        raise HTTPException(status_code=422, detail="Confirma que recibiste el efectivo")
    if payload.metodo in {"tarjeta", "transferencia", "yape", "plin"} and not payload.referencia:
        raise HTTPException(status_code=422, detail="Registra el número o código de operación")
    order = await db.scalar(select(OrdenTrabajo).where(OrdenTrabajo.id == payload.orden_id, OrdenTrabajo.empresa_id == context.empresa_id).with_for_update())
    if not order or order.estado == "cancelada" or order.total <= 0:
        raise HTTPException(status_code=409, detail="La orden no está disponible para cobro")
    ensure_branch_access(context, order.sucursal_id)
    if payload.monto > order.saldo:
        raise HTTPException(status_code=409, detail=f"El pago supera el saldo pendiente de S/ {order.saldo}")
    await db.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"), {"key": f"pago:{context.empresa_id}:{order.sucursal_id}"})
    number = int(await db.scalar(select(func.coalesce(func.max(Pago.numero), 0)).where(Pago.empresa_id == context.empresa_id, Pago.sucursal_id == order.sucursal_id)) or 0) + 1
    payment = Pago(empresa_id=context.empresa_id, sucursal_id=order.sucursal_id, orden_id=order.id, numero=number, metodo=payload.metodo, monto=payload.monto, referencia=payload.referencia.strip() if payload.referencia else None, registrado_by=context.usuario.id)
    order.saldo -= payload.monto
    db.add(payment)
    try:
        await db.flush(); record_audit(db, context, "registrar", "pagos", payment.id, after={"monto": str(payment.monto), "metodo": payment.metodo}); await db.commit()
    except IntegrityError as exc:
        await db.rollback(); raise HTTPException(status_code=409, detail="No se pudo registrar el pago") from exc
    return payment_read((await db.execute(payment_query(context.empresa_id).where(Pago.id == payment.id))).one())


@router.post("/{payment_id}/anular", response_model=PagoRead, dependencies=[Depends(require_permission("pagos.anular"))])
async def cancel_payment(payment_id: uuid.UUID, payload: PagoAnular, context: CurrentContext, db: AsyncSession = Depends(get_db)):
    payment = await db.scalar(select(Pago).where(Pago.id == payment_id, Pago.empresa_id == context.empresa_id).with_for_update())
    if not payment:
        raise HTTPException(status_code=404, detail="Pago no encontrado")
    ensure_branch_access(context, payment.sucursal_id)
    if payment.estado == "anulado":
        raise HTTPException(status_code=409, detail="El pago ya fue anulado")
    order = await db.scalar(select(OrdenTrabajo).where(OrdenTrabajo.id == payment.orden_id, OrdenTrabajo.empresa_id == context.empresa_id).with_for_update())
    if not order:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    payment.estado = "anulado"; payment.motivo_anulacion = payload.motivo.strip(); payment.anulado_at = datetime.now(timezone.utc); payment.anulado_by = context.usuario.id
    order.saldo += payment.monto
    record_audit(db, context, "anular", "pagos", payment.id, after={"motivo": payment.motivo_anulacion}); await db.commit()
    return payment_read((await db.execute(payment_query(context.empresa_id).where(Pago.id == payment.id))).one())
