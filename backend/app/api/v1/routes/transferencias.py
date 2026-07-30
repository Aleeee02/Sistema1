import uuid
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentContext
from app.db.session import get_db
from app.models.empresa import Sucursal
from app.models.inventario import (
    Existencia,
    MovimientoInventario,
    Producto,
    ReservaInventario,
    TransferenciaInventario,
    TransferenciaInventarioItem,
)
from app.schemas.transferencia import TransferenciaCreate, TransferenciaEstado, TransferenciaRead
from app.services.auditoria import record_audit
from app.services.notificaciones import notify

router = APIRouter()


@router.get("/opciones")
async def transfer_options(context: CurrentContext, db: AsyncSession = Depends(get_db)):
    branches = (
        await db.execute(
            select(Sucursal.id, Sucursal.nombre, Sucursal.es_principal)
            .where(Sucursal.empresa_id == context.empresa_id, Sucursal.estado == "activo")
            .order_by(Sucursal.es_principal.desc(), Sucursal.nombre)
        )
    ).all()
    return [
        {"id": row.id, "nombre": row.nombre, "es_principal": row.es_principal}
        for row in branches
    ]


@router.get("/productos-origen/{branch_id}")
async def origin_products(branch_id: uuid.UUID, context: CurrentContext, db: AsyncSession = Depends(get_db)):
    branch = await db.scalar(select(Sucursal.id).where(Sucursal.id == branch_id, Sucursal.empresa_id == context.empresa_id, Sucursal.estado == "activo"))
    if not branch:
        raise HTTPException(status_code=404, detail="Sucursal no encontrada")
    rows = (
        await db.execute(
            select(Producto, Existencia.stock_actual)
            .join(Existencia, Existencia.producto_id == Producto.id)
            .where(
                Producto.empresa_id == context.empresa_id,
                Producto.estado == "activo",
                Existencia.empresa_id == context.empresa_id,
                Existencia.sucursal_id == branch_id,
                Existencia.stock_actual > 0,
            )
            .order_by(Producto.nombre)
        )
    ).all()
    return [
        {
            "id": row[0].id,
            "sku": row[0].sku,
            "nombre": row[0].nombre,
            "stock_actual": row.stock_actual,
            "unidad_medida": row[0].unidad_medida,
        }
        for row in rows
    ]


async def transfer_read(db: AsyncSession, transfer: TransferenciaInventario) -> TransferenciaRead:
    origin = await db.scalar(select(Sucursal.nombre).where(Sucursal.id == transfer.sucursal_origen_id))
    destination = await db.scalar(select(Sucursal.nombre).where(Sucursal.id == transfer.sucursal_destino_id))
    rows = (
        await db.execute(
            select(TransferenciaInventarioItem, Producto)
            .join(Producto, Producto.id == TransferenciaInventarioItem.producto_id)
            .where(
                TransferenciaInventarioItem.transferencia_id == transfer.id,
                TransferenciaInventarioItem.empresa_id == transfer.empresa_id,
            )
            .order_by(Producto.nombre)
        )
    ).all()
    return TransferenciaRead(
        **{column.name: getattr(transfer, column.name) for column in TransferenciaInventario.__table__.columns},
        sucursal_origen_nombre=origin or "Sucursal",
        sucursal_destino_nombre=destination or "Sucursal",
        items=[
            {
                **{column.name: getattr(row[0], column.name) for column in TransferenciaInventarioItem.__table__.columns},
                "producto_sku": row[1].sku,
                "producto_nombre": row[1].nombre,
                "unidad_medida": row[1].unidad_medida,
            }
            for row in rows
        ],
    )


async def find_transfer(db: AsyncSession, transfer_id: uuid.UUID, context):
    transfer = await db.scalar(
        select(TransferenciaInventario).where(
            TransferenciaInventario.id == transfer_id,
            TransferenciaInventario.empresa_id == context.empresa_id,
        )
    )
    if not transfer:
        raise HTTPException(status_code=404, detail="Transferencia no encontrada")
    if context.sucursal_ids and not (
        transfer.sucursal_origen_id in context.sucursal_ids
        or transfer.sucursal_destino_id in context.sucursal_ids
    ):
        raise HTTPException(status_code=403, detail="No tienes acceso a esta transferencia")
    return transfer


@router.get("", response_model=list[TransferenciaRead])
async def list_transfers(context: CurrentContext, db: AsyncSession = Depends(get_db)):
    transfers = list(
        (
            await db.scalars(
                select(TransferenciaInventario)
                .where(
                    TransferenciaInventario.empresa_id == context.empresa_id,
                    or_(
                        not context.sucursal_ids,
                        TransferenciaInventario.sucursal_origen_id.in_(context.sucursal_ids),
                        TransferenciaInventario.sucursal_destino_id.in_(context.sucursal_ids),
                    ),
                )
                .order_by(TransferenciaInventario.fecha_solicitud.desc())
            )
        ).all()
    )
    return [await transfer_read(db, transfer) for transfer in transfers]


@router.post("", response_model=TransferenciaRead, status_code=status.HTTP_201_CREATED)
async def create_transfer(
    payload: TransferenciaCreate,
    context: CurrentContext,
    db: AsyncSession = Depends(get_db),
):
    if payload.sucursal_origen_id == payload.sucursal_destino_id:
        raise HTTPException(status_code=422, detail="Origen y destino deben ser diferentes")
    if context.sucursal_ids and not (
        payload.sucursal_origen_id in context.sucursal_ids
        or payload.sucursal_destino_id in context.sucursal_ids
    ):
        raise HTTPException(status_code=403, detail="La transferencia no incluye una sucursal permitida")
    branches = list(
        (
            await db.scalars(
                select(Sucursal).where(
                    Sucursal.empresa_id == context.empresa_id,
                    Sucursal.id.in_((payload.sucursal_origen_id, payload.sucursal_destino_id)),
                    Sucursal.estado == "activo",
                )
            )
        ).all()
    )
    if len(branches) != 2:
        raise HTTPException(status_code=404, detail="Sucursal no encontrada")
    if len({item.producto_id for item in payload.items}) != len(payload.items):
        raise HTTPException(status_code=422, detail="No repitas productos")
    product_ids = [item.producto_id for item in payload.items]
    products = list(
        (
            await db.scalars(
                select(Producto).where(
                    Producto.empresa_id == context.empresa_id,
                    Producto.id.in_(product_ids),
                    Producto.estado == "activo",
                )
            )
        ).all()
    )
    if len(products) != len(product_ids):
        raise HTTPException(status_code=404, detail="Uno de los productos no existe")
    transfer = TransferenciaInventario(
        empresa_id=context.empresa_id,
        sucursal_origen_id=payload.sucursal_origen_id,
        sucursal_destino_id=payload.sucursal_destino_id,
        solicitada_por=context.usuario.id,
        observaciones=payload.observaciones,
    )
    db.add(transfer)
    try:
        await db.flush()
        for item in payload.items:
            db.add(
                TransferenciaInventarioItem(
                    empresa_id=context.empresa_id,
                    transferencia_id=transfer.id,
                    producto_id=item.producto_id,
                    cantidad_solicitada=item.cantidad,
                    observaciones=item.observaciones,
                )
            )
        record_audit(db, context, "solicitar", "transferencias_inventario", transfer.id, after={"estado": "solicitada"})
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail="No se pudo crear la transferencia") from exc
    return await transfer_read(db, transfer)


@router.patch("/{transfer_id}/estado", response_model=TransferenciaRead)
async def change_transfer_status(
    transfer_id: uuid.UUID,
    payload: TransferenciaEstado,
    context: CurrentContext,
    db: AsyncSession = Depends(get_db),
):
    transfer = await find_transfer(db, transfer_id, context)
    allowed = {
        "solicitada": {"aprobada", "rechazada", "cancelada"},
        "aprobada": {"en_transito", "cancelada"},
        "en_transito": {"recibida"},
    }
    if payload.estado not in allowed.get(transfer.estado, set()):
        raise HTTPException(status_code=409, detail="Cambio de estado no permitido")
    required_branch = (
        transfer.sucursal_destino_id
        if payload.estado == "recibida"
        else transfer.sucursal_origen_id
    )
    if context.sucursal_ids and required_branch not in context.sucursal_ids:
        action = "recibir" if payload.estado == "recibida" else "aprobar o despachar"
        raise HTTPException(
            status_code=403,
            detail=f"Solo la sucursal responsable puede {action} esta transferencia",
        )
    now = datetime.now(timezone.utc)
    previous = transfer.estado
    if payload.estado in {"aprobada", "en_transito", "recibida", "rechazada"}:
        notify(db, context.empresa_id, f"transferencia_{payload.estado}", "Transferencia actualizada", f"La transferencia cambió a {payload.estado.replace('_', ' ')}.", "/transferencias", transfer.sucursal_destino_id if payload.estado in {"en_transito", "recibida"} else transfer.sucursal_origen_id)
    items = list(
        (
            await db.scalars(
                select(TransferenciaInventarioItem).where(
                    TransferenciaInventarioItem.transferencia_id == transfer.id,
                    TransferenciaInventarioItem.empresa_id == context.empresa_id,
                )
            )
        ).all()
    )
    if payload.estado == "aprobada":
        transfer.aprobada_por = context.usuario.id
        transfer.fecha_aprobacion = now
    elif payload.estado == "en_transito":
        for item in items:
            existence = await db.scalar(
                select(Existencia)
                .where(
                    Existencia.empresa_id == context.empresa_id,
                    Existencia.sucursal_id == transfer.sucursal_origen_id,
                    Existencia.producto_id == item.producto_id,
                )
                .with_for_update()
            )
            if not existence:
                raise HTTPException(status_code=409, detail="Producto sin existencia en origen")
            reserved = await db.scalar(
                select(func.coalesce(func.sum(ReservaInventario.cantidad), 0)).where(
                    ReservaInventario.empresa_id == context.empresa_id,
                    ReservaInventario.sucursal_id == transfer.sucursal_origen_id,
                    ReservaInventario.producto_id == item.producto_id,
                    ReservaInventario.estado == "activa",
                )
            )
            available = existence.stock_actual - Decimal(reserved or 0)
            if available < item.cantidad_solicitada:
                product_name = await db.scalar(select(Producto.nombre).where(Producto.id == item.producto_id))
                raise HTTPException(status_code=409, detail=f"Stock disponible insuficiente para {product_name}")
            previous_stock = existence.stock_actual
            existence.stock_actual -= item.cantidad_solicitada
            item.cantidad_despachada = item.cantidad_solicitada
            db.add(
                MovimientoInventario(
                    empresa_id=context.empresa_id,
                    existencia_id=existence.id,
                    tipo="transferencia",
                    cantidad=item.cantidad_solicitada,
                    costo_unitario=0,
                    stock_anterior=previous_stock,
                    stock_resultante=existence.stock_actual,
                    motivo=f"Despacho transferencia {transfer.id}",
                    usuario_id=context.usuario.id,
                )
            )
        transfer.despachada_por = context.usuario.id
        transfer.fecha_despacho = now
    elif payload.estado == "recibida":
        for item in items:
            if item.cantidad_despachada is None:
                raise HTTPException(status_code=409, detail="Producto no despachado")
            existence = await db.scalar(
                select(Existencia)
                .where(
                    Existencia.empresa_id == context.empresa_id,
                    Existencia.sucursal_id == transfer.sucursal_destino_id,
                    Existencia.producto_id == item.producto_id,
                )
                .with_for_update()
            )
            if not existence:
                existence = Existencia(
                    empresa_id=context.empresa_id,
                    sucursal_id=transfer.sucursal_destino_id,
                    producto_id=item.producto_id,
                )
                db.add(existence)
                await db.flush()
            previous_stock = existence.stock_actual
            existence.stock_actual += item.cantidad_despachada
            item.cantidad_recibida = item.cantidad_despachada
            db.add(
                MovimientoInventario(
                    empresa_id=context.empresa_id,
                    existencia_id=existence.id,
                    tipo="transferencia",
                    cantidad=item.cantidad_recibida,
                    costo_unitario=0,
                    stock_anterior=previous_stock,
                    stock_resultante=existence.stock_actual,
                    motivo=f"Recepción transferencia {transfer.id}",
                    usuario_id=context.usuario.id,
                )
            )
        transfer.recibida_por = context.usuario.id
        transfer.fecha_recepcion = now
    transfer.estado = payload.estado
    record_audit(db, context, "cambiar_estado", "transferencias_inventario", transfer.id, before={"estado": previous}, after={"estado": transfer.estado})
    await db.commit()
    return await transfer_read(db, transfer)
