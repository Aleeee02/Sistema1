import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentContext
from app.db.session import get_db
from app.models.cliente import Cliente
from app.models.vehiculo import Vehiculo, VehiculoCliente
from app.schemas.vehiculo import (
    CambiarPropietarioRequest,
    VehiculoRead,
    VehiculoUpdate,
)
from app.services.auditoria import record_audit

router = APIRouter()


def snapshot(vehiculo: Vehiculo) -> dict:
    return VehiculoRead.model_validate(vehiculo).model_dump(mode="json")


async def find_vehiculo(
    db: AsyncSession, vehiculo_id: uuid.UUID, empresa_id: uuid.UUID
) -> Vehiculo:
    vehiculo = await db.scalar(
        select(Vehiculo).where(
            Vehiculo.id == vehiculo_id,
            Vehiculo.empresa_id == empresa_id,
        )
    )
    if not vehiculo:
        raise HTTPException(status_code=404, detail="Vehículo no encontrado")
    return vehiculo


@router.get("/{vehiculo_id}", response_model=VehiculoRead)
async def get_vehiculo(
    vehiculo_id: uuid.UUID,
    context: CurrentContext,
    db: AsyncSession = Depends(get_db),
) -> Vehiculo:
    return await find_vehiculo(db, vehiculo_id, context.empresa_id)


@router.patch("/{vehiculo_id}", response_model=VehiculoRead)
async def update_vehiculo(
    vehiculo_id: uuid.UUID,
    payload: VehiculoUpdate,
    context: CurrentContext,
    db: AsyncSession = Depends(get_db),
) -> Vehiculo:
    vehiculo = await find_vehiculo(db, vehiculo_id, context.empresa_id)
    before = snapshot(vehiculo)
    for key, value in payload.model_dump(exclude_unset=True).items():
        if isinstance(value, str):
            value = value.strip() or None
        setattr(vehiculo, key, value)
    try:
        await db.flush()
        record_audit(
            db,
            context,
            "actualizar",
            "vehiculos",
            vehiculo.id,
            before=before,
            after=snapshot(vehiculo),
        )
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=409, detail="Ya existe un vehículo con esa placa"
        ) from exc
    await db.refresh(vehiculo)
    return vehiculo


@router.post("/{vehiculo_id}/cambiar-propietario", response_model=VehiculoRead)
async def cambiar_propietario(
    vehiculo_id: uuid.UUID,
    payload: CambiarPropietarioRequest,
    context: CurrentContext,
    db: AsyncSession = Depends(get_db),
) -> Vehiculo:
    vehiculo = await find_vehiculo(db, vehiculo_id, context.empresa_id)
    cliente = await db.scalar(
        select(Cliente).where(
            Cliente.id == payload.cliente_id,
            Cliente.empresa_id == context.empresa_id,
            Cliente.estado == "activo",
        )
    )
    if not cliente:
        raise HTTPException(status_code=404, detail="Nuevo propietario no encontrado")

    actual = await db.scalar(
        select(VehiculoCliente)
        .where(
            VehiculoCliente.vehiculo_id == vehiculo_id,
            VehiculoCliente.empresa_id == context.empresa_id,
            VehiculoCliente.es_actual.is_(True),
        )
        .with_for_update()
    )
    if actual and actual.cliente_id == payload.cliente_id:
        raise HTTPException(status_code=409, detail="El cliente ya es el propietario")
    propietario_anterior = str(actual.cliente_id) if actual else None
    if actual:
        actual.es_actual = False
        actual.fecha_fin = date.today()
    db.add(
        VehiculoCliente(
            empresa_id=context.empresa_id,
            vehiculo_id=vehiculo_id,
            cliente_id=payload.cliente_id,
            es_actual=True,
        )
    )
    record_audit(
        db,
        context,
        "cambiar_propietario",
        "vehiculos",
        vehiculo.id,
        before={"cliente_id": propietario_anterior},
        after={"cliente_id": str(payload.cliente_id)},
    )
    await db.commit()
    await db.refresh(vehiculo)
    return vehiculo


@router.delete("/{vehiculo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_vehiculo(
    vehiculo_id: uuid.UUID,
    context: CurrentContext,
    db: AsyncSession = Depends(get_db),
) -> None:
    vehiculo = await find_vehiculo(db, vehiculo_id, context.empresa_id)
    if vehiculo.estado != "inactivo":
        before = snapshot(vehiculo)
        vehiculo.estado = "inactivo"
        await db.flush()
        record_audit(
            db,
            context,
            "desactivar",
            "vehiculos",
            vehiculo.id,
            before=before,
            after=snapshot(vehiculo),
        )
        await db.commit()
