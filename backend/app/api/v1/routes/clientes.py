import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentContext
from app.db.session import get_db
from app.models.cliente import Cliente
from app.models.vehiculo import Vehiculo, VehiculoCliente
from app.schemas.cliente import ClienteCreate, ClienteRead, ClienteUpdate
from app.schemas.vehiculo import VehiculoCreate, VehiculoRead
from app.services.auditoria import record_audit

router = APIRouter()


def cliente_snapshot(cliente: Cliente) -> dict:
    return ClienteRead.model_validate(cliente).model_dump(mode="json")


def vehiculo_snapshot(vehiculo: Vehiculo) -> dict:
    return VehiculoRead.model_validate(vehiculo).model_dump(mode="json")


def clean_values(values: dict) -> dict:
    for key, value in values.items():
        if isinstance(value, str):
            value = value.strip()
            values[key] = value or None
    if values.get("tipo_documento"):
        values["tipo_documento"] = values["tipo_documento"].upper()
    if values.get("numero_documento"):
        values["numero_documento"] = values["numero_documento"].upper()
    if values.get("email"):
        values["email"] = values["email"].lower()
    return values


async def find_cliente(
    db: AsyncSession, cliente_id: uuid.UUID, empresa_id: uuid.UUID
) -> Cliente:
    cliente = await db.scalar(
        select(Cliente).where(
            Cliente.id == cliente_id,
            Cliente.empresa_id == empresa_id,
        )
    )
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return cliente


@router.get("", response_model=list[ClienteRead])
async def list_clientes(
    context: CurrentContext,
    search: str | None = Query(default=None, max_length=100),
    incluir_inactivos: bool = False,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> list[Cliente]:
    query = (
        select(Cliente)
        .where(Cliente.empresa_id == context.empresa_id)
        .order_by(Cliente.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    if not incluir_inactivos:
        query = query.where(Cliente.estado == "activo")
    if search and search.strip():
        term = f"%{search.strip()}%"
        query = query.where(
            or_(
                Cliente.nombres.ilike(term),
                Cliente.apellidos.ilike(term),
                Cliente.razon_social.ilike(term),
                Cliente.numero_documento.ilike(term),
                Cliente.telefono.ilike(term),
                Cliente.email.ilike(term),
            )
        )
    return list((await db.scalars(query)).all())


@router.post("", response_model=ClienteRead, status_code=status.HTTP_201_CREATED)
async def create_cliente(
    payload: ClienteCreate,
    context: CurrentContext,
    db: AsyncSession = Depends(get_db),
) -> Cliente:
    cliente = Cliente(
        empresa_id=context.empresa_id,
        **clean_values(payload.model_dump()),
    )
    db.add(cliente)
    try:
        await db.flush()
        record_audit(
            db, context, "crear", "clientes", cliente.id, after=cliente_snapshot(cliente)
        )
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Ya existe un cliente con ese tipo y número de documento",
        ) from exc
    await db.refresh(cliente)
    return cliente


@router.get("/{cliente_id}/vehiculos", response_model=list[VehiculoRead])
async def list_cliente_vehiculos(
    cliente_id: uuid.UUID,
    context: CurrentContext,
    db: AsyncSession = Depends(get_db),
) -> list[Vehiculo]:
    await find_cliente(db, cliente_id, context.empresa_id)
    query = (
        select(Vehiculo)
        .join(VehiculoCliente, VehiculoCliente.vehiculo_id == Vehiculo.id)
        .where(
            Vehiculo.empresa_id == context.empresa_id,
            Vehiculo.estado == "activo",
            VehiculoCliente.empresa_id == context.empresa_id,
            VehiculoCliente.cliente_id == cliente_id,
            VehiculoCliente.es_actual.is_(True),
        )
        .order_by(Vehiculo.created_at.desc())
    )
    return list((await db.scalars(query)).all())


@router.post(
    "/{cliente_id}/vehiculos",
    response_model=VehiculoRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_cliente_vehiculo(
    cliente_id: uuid.UUID,
    payload: VehiculoCreate,
    context: CurrentContext,
    db: AsyncSession = Depends(get_db),
) -> Vehiculo:
    cliente = await find_cliente(db, cliente_id, context.empresa_id)
    if cliente.estado != "activo":
        raise HTTPException(status_code=409, detail="El cliente está inactivo")

    vehiculo = Vehiculo(empresa_id=context.empresa_id, **payload.model_dump())
    db.add(vehiculo)
    try:
        await db.flush()
        db.add(
            VehiculoCliente(
                empresa_id=context.empresa_id,
                vehiculo_id=vehiculo.id,
                cliente_id=cliente_id,
                es_actual=True,
            )
        )
        record_audit(
            db,
            context,
            "crear",
            "vehiculos",
            vehiculo.id,
            after=vehiculo_snapshot(vehiculo),
        )
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Ya existe un vehículo con esa placa en la empresa",
        ) from exc
    await db.refresh(vehiculo)
    return vehiculo


@router.get("/{cliente_id}", response_model=ClienteRead)
async def get_cliente(
    cliente_id: uuid.UUID,
    context: CurrentContext,
    db: AsyncSession = Depends(get_db),
) -> Cliente:
    return await find_cliente(db, cliente_id, context.empresa_id)


@router.patch("/{cliente_id}", response_model=ClienteRead)
async def update_cliente(
    cliente_id: uuid.UUID,
    payload: ClienteUpdate,
    context: CurrentContext,
    db: AsyncSession = Depends(get_db),
) -> Cliente:
    cliente = await find_cliente(db, cliente_id, context.empresa_id)
    before = cliente_snapshot(cliente)
    values = clean_values(payload.model_dump(exclude_unset=True))
    merged = {**before, **values}
    if merged["tipo_persona"] == "natural" and not merged.get("nombres"):
        raise HTTPException(status_code=422, detail="El cliente requiere nombres")
    if merged["tipo_persona"] == "juridica" and not merged.get("razon_social"):
        raise HTTPException(status_code=422, detail="El cliente requiere razón social")
    for key, value in values.items():
        setattr(cliente, key, value)
    try:
        await db.flush()
        record_audit(
            db,
            context,
            "actualizar",
            "clientes",
            cliente.id,
            before=before,
            after=cliente_snapshot(cliente),
        )
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Ya existe un cliente con ese tipo y número de documento",
        ) from exc
    await db.refresh(cliente)
    return cliente


@router.delete("/{cliente_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_cliente(
    cliente_id: uuid.UUID,
    context: CurrentContext,
    db: AsyncSession = Depends(get_db),
) -> None:
    cliente = await find_cliente(db, cliente_id, context.empresa_id)
    if cliente.estado != "inactivo":
        before = cliente_snapshot(cliente)
        cliente.estado = "inactivo"
        await db.flush()
        record_audit(
            db,
            context,
            "desactivar",
            "clientes",
            cliente.id,
            before=before,
            after=cliente_snapshot(cliente),
        )
        await db.commit()
