import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentContext
from app.db.session import get_db
from app.models.orden import Servicio
from app.schemas.servicio import ServicioCreate, ServicioRead, ServicioUpdate
from app.services.auditoria import record_audit

router = APIRouter()


async def find_service(db: AsyncSession, service_id: uuid.UUID, empresa_id: uuid.UUID):
    service = await db.scalar(
        select(Servicio).where(
            Servicio.id == service_id,
            Servicio.empresa_id == empresa_id,
        )
    )
    if not service:
        raise HTTPException(status_code=404, detail="Servicio no encontrado")
    return service


@router.get("", response_model=list[ServicioRead])
async def list_services(
    context: CurrentContext,
    incluir_inactivos: bool = False,
    db: AsyncSession = Depends(get_db),
):
    query = select(Servicio).where(Servicio.empresa_id == context.empresa_id)
    if not incluir_inactivos:
        query = query.where(Servicio.estado == "activo")
    return list((await db.scalars(query.order_by(Servicio.categoria, Servicio.nombre))).all())


@router.post("", response_model=ServicioRead, status_code=status.HTTP_201_CREATED)
async def create_service(
    payload: ServicioCreate,
    context: CurrentContext,
    db: AsyncSession = Depends(get_db),
):
    values = payload.model_dump()
    for key, value in values.items():
        if isinstance(value, str):
            values[key] = value.strip() or None
    values["codigo"] = payload.codigo.strip().upper()
    service = Servicio(empresa_id=context.empresa_id, **values)
    db.add(service)
    try:
        await db.flush()
        record_audit(db, context, "crear", "servicios", service.id, after={"codigo": service.codigo, "nombre": service.nombre})
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail="El código del servicio ya existe") from exc
    await db.refresh(service)
    return service


@router.patch("/{service_id}", response_model=ServicioRead)
async def update_service(
    service_id: uuid.UUID,
    payload: ServicioUpdate,
    context: CurrentContext,
    db: AsyncSession = Depends(get_db),
):
    service = await find_service(db, service_id, context.empresa_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        if isinstance(value, str):
            value = value.strip() or None
        if key == "codigo" and value:
            value = value.upper()
        setattr(service, key, value)
    try:
        record_audit(db, context, "actualizar", "servicios", service.id, after=payload.model_dump(mode="json", exclude_unset=True))
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail="El código del servicio ya existe") from exc
    await db.refresh(service)
    return service


@router.delete("/{service_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_service(
    service_id: uuid.UUID,
    context: CurrentContext,
    db: AsyncSession = Depends(get_db),
):
    service = await find_service(db, service_id, context.empresa_id)
    service.estado = "inactivo"
    record_audit(db, context, "desactivar", "servicios", service.id, after={"estado": "inactivo"})
    await db.commit()
