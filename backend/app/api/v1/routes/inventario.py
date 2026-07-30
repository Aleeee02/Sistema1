import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentContext, ensure_branch_access
from app.db.session import get_db
from app.models.empresa import Sucursal
from app.models.inventario import Existencia, MovimientoInventario, Producto
from app.schemas.inventario import (
    InventarioRead,
    MovimientoCreate,
    MovimientoRead,
    ProductoCreate,
    ProductoUpdate,
)
from app.services.auditoria import record_audit
from app.services.notificaciones import notify

router = APIRouter()


async def valid_branch(db: AsyncSession, branch_id: uuid.UUID, empresa_id: uuid.UUID):
    branch = await db.scalar(
        select(Sucursal).where(
            Sucursal.id == branch_id,
            Sucursal.empresa_id == empresa_id,
            Sucursal.estado == "activo",
        )
    )
    if not branch:
        raise HTTPException(status_code=404, detail="Sucursal no encontrada")
    return branch


@router.get("", response_model=list[InventarioRead])
async def list_inventory(
    context: CurrentContext,
    sucursal_id: uuid.UUID,
    search: str | None = Query(default=None, max_length=100),
    db: AsyncSession = Depends(get_db),
):
    ensure_branch_access(context, sucursal_id)
    await valid_branch(db, sucursal_id, context.empresa_id)
    query = (
        select(Producto, Existencia)
        .outerjoin(
            Existencia,
            (Existencia.producto_id == Producto.id)
            & (Existencia.sucursal_id == sucursal_id)
            & (Existencia.empresa_id == context.empresa_id),
        )
        .where(Producto.empresa_id == context.empresa_id, Producto.estado == "activo")
        .order_by(Producto.nombre)
    )
    if search and search.strip():
        term = f"%{search.strip()}%"
        query = query.where(or_(Producto.sku.ilike(term), Producto.nombre.ilike(term), Producto.categoria.ilike(term)))
    rows = (await db.execute(query)).all()
    return [
        InventarioRead(
            **{column.name: getattr(row[0], column.name) for column in Producto.__table__.columns},
            existencia_id=row[1].id if row[1] else None,
            sucursal_id=sucursal_id,
            stock_actual=row[1].stock_actual if row[1] else Decimal("0"),
            stock_minimo=row[1].stock_minimo if row[1] else Decimal("0"),
            stock_maximo=row[1].stock_maximo if row[1] else None,
        )
        for row in rows
    ]


@router.post("/productos", response_model=InventarioRead, status_code=status.HTTP_201_CREATED)
async def create_product(
    payload: ProductoCreate,
    context: CurrentContext,
    sucursal_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    ensure_branch_access(context, sucursal_id)
    await valid_branch(db, sucursal_id, context.empresa_id)
    values = payload.model_dump(exclude={"stock_minimo"})
    for key, value in values.items():
        if isinstance(value, str):
            values[key] = value.strip() or None
    values["sku"] = payload.sku.strip().upper()
    product = Producto(empresa_id=context.empresa_id, **values)
    db.add(product)
    try:
        await db.flush()
        existence = Existencia(
            empresa_id=context.empresa_id,
            sucursal_id=sucursal_id,
            producto_id=product.id,
            stock_minimo=payload.stock_minimo,
        )
        db.add(existence)
        record_audit(db, context, "crear", "productos", product.id, after={"sku": product.sku, "nombre": product.nombre})
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail="El SKU ya existe en la empresa") from exc
    return (await list_inventory(context, sucursal_id, product.sku, db))[0]


@router.patch("/productos/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def update_product(
    product_id: uuid.UUID,
    payload: ProductoUpdate,
    context: CurrentContext,
    db: AsyncSession = Depends(get_db),
):
    product = await db.scalar(select(Producto).where(Producto.id == product_id, Producto.empresa_id == context.empresa_id))
    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    for key, value in payload.model_dump(exclude_unset=True).items():
        if isinstance(value, str):
            value = value.strip() or None
        if key == "sku" and value:
            value = value.upper()
        setattr(product, key, value)
    try:
        record_audit(db, context, "actualizar", "productos", product.id, after=payload.model_dump(mode="json", exclude_unset=True))
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail="El SKU ya existe") from exc


@router.delete("/productos/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_product(
    product_id: uuid.UUID,
    context: CurrentContext,
    db: AsyncSession = Depends(get_db),
):
    product = await db.scalar(select(Producto).where(Producto.id == product_id, Producto.empresa_id == context.empresa_id))
    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    total_stock = await db.scalar(select(func.coalesce(func.sum(Existencia.stock_actual), 0)).where(Existencia.empresa_id == context.empresa_id, Existencia.producto_id == product.id))
    if total_stock > 0:
        raise HTTPException(status_code=409, detail="No se puede desactivar un producto con existencias")
    product.estado = "inactivo"
    await db.commit()


@router.post("/movimientos", response_model=MovimientoRead, status_code=status.HTTP_201_CREATED)
async def create_movement(
    payload: MovimientoCreate,
    context: CurrentContext,
    db: AsyncSession = Depends(get_db),
):
    ensure_branch_access(context, payload.sucursal_id)
    await valid_branch(db, payload.sucursal_id, context.empresa_id)
    product = await db.scalar(select(Producto).where(Producto.id == payload.producto_id, Producto.empresa_id == context.empresa_id, Producto.estado == "activo"))
    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    existence = await db.scalar(
        select(Existencia)
        .where(Existencia.empresa_id == context.empresa_id, Existencia.sucursal_id == payload.sucursal_id, Existencia.producto_id == product.id)
        .with_for_update()
    )
    if not existence:
        existence = Existencia(empresa_id=context.empresa_id, sucursal_id=payload.sucursal_id, producto_id=product.id)
        db.add(existence)
        await db.flush()
    previous = Decimal(existence.stock_actual)
    if payload.tipo == "entrada":
        resulting = previous + Decimal(payload.cantidad or 0)
    elif payload.tipo == "salida":
        resulting = previous - Decimal(payload.cantidad or 0)
        if resulting < 0:
            raise HTTPException(status_code=409, detail="Stock insuficiente en esta sucursal")
    else:
        resulting = Decimal(payload.stock_nuevo or 0)
    quantity = abs(resulting - previous)
    if quantity == 0:
        raise HTTPException(status_code=422, detail="El movimiento no cambia el stock")
    movement = MovimientoInventario(
        empresa_id=context.empresa_id,
        existencia_id=existence.id,
        tipo=payload.tipo,
        cantidad=quantity,
        costo_unitario=payload.costo_unitario,
        stock_anterior=previous,
        stock_resultante=resulting,
        motivo=payload.motivo.strip(),
        usuario_id=context.usuario.id,
    )
    existence.stock_actual = resulting
    if resulting <= existence.stock_minimo:
        notify(db, context.empresa_id, "stock_bajo", "Stock bajo", f"{product.nombre} quedó con {resulting} {product.unidad_medida}.", "/inventario", payload.sucursal_id)
    if payload.tipo == "entrada" and payload.costo_unitario > 0:
        product.costo_promedio = ((previous * product.costo_promedio + quantity * payload.costo_unitario) / resulting) if resulting else payload.costo_unitario
    db.add(movement)
    await db.flush()
    record_audit(db, context, "movimiento", "existencias", existence.id, before={"stock": str(previous)}, after={"stock": str(resulting), "tipo": payload.tipo})
    await db.commit()
    await db.refresh(movement)
    return MovimientoRead(
        **{column.name: getattr(movement, column.name) for column in MovimientoInventario.__table__.columns},
        producto_nombre=product.nombre,
        producto_sku=product.sku,
    )


@router.get("/movimientos", response_model=list[MovimientoRead])
async def list_movements(
    context: CurrentContext,
    sucursal_id: uuid.UUID,
    limit: int = Query(default=50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    ensure_branch_access(context, sucursal_id)
    rows = (
        await db.execute(
            select(MovimientoInventario, Producto.nombre.label("producto_nombre"), Producto.sku.label("producto_sku"))
            .join(Existencia, Existencia.id == MovimientoInventario.existencia_id)
            .join(Producto, Producto.id == Existencia.producto_id)
            .where(MovimientoInventario.empresa_id == context.empresa_id, Existencia.sucursal_id == sucursal_id)
            .order_by(MovimientoInventario.created_at.desc())
            .limit(limit)
        )
    ).all()
    return [MovimientoRead(**{column.name: getattr(row[0], column.name) for column in MovimientoInventario.__table__.columns}, producto_nombre=row.producto_nombre, producto_sku=row.producto_sku) for row in rows]
