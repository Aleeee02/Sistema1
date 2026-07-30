import uuid
from datetime import datetime, timezone
from pathlib import Path

import httpx
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentContext, branch_scope, ensure_branch_access
from app.core.config import settings
from app.db.session import get_db
from app.models.inspeccion import Archivo, Inspeccion, InspeccionItem
from app.models.orden import OrdenTrabajo
from app.schemas.inspeccion import ArchivoRead, InspeccionConfirmar, InspeccionCreate, InspeccionRead
from app.services.auditoria import record_audit

router = APIRouter()
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_SIZE = 8 * 1024 * 1024


async def storage_url(path: str) -> str | None:
    if not settings.supabase_url or not settings.supabase_service_role_key:
        return None
    endpoint = f"{settings.supabase_url}/storage/v1/object/sign/{settings.supabase_storage_bucket}/{path}"
    headers = {"Authorization": f"Bearer {settings.supabase_service_role_key}", "apikey": settings.supabase_service_role_key}
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(endpoint, headers=headers, json={"expiresIn": 3600})
    if response.is_success:
        value = response.json().get("signedURL")
        return f"{settings.supabase_url}/storage/v1{value}" if value else None
    return None


async def serialize(db: AsyncSession, inspection: Inspeccion) -> InspeccionRead:
    items = list((await db.scalars(select(InspeccionItem).where(InspeccionItem.inspeccion_id == inspection.id).order_by(InspeccionItem.orden_visual))).all())
    files = list((await db.scalars(select(Archivo).where(Archivo.inspeccion_id == inspection.id).order_by(Archivo.created_at))).all())
    return InspeccionRead(**{column.name: getattr(inspection, column.name) for column in Inspeccion.__table__.columns}, items=items, archivos=[ArchivoRead(id=file.id, nombre_original=file.nombre_original, mime_type=file.mime_type, tamano_bytes=file.tamano_bytes, created_at=file.created_at, url=await storage_url(file.storage_path)) for file in files])


@router.get("/orden/{order_id}", response_model=list[InspeccionRead])
async def list_order_inspections(order_id: uuid.UUID, context: CurrentContext, db: AsyncSession = Depends(get_db)):
    order = await db.scalar(select(OrdenTrabajo.id).where(OrdenTrabajo.id == order_id, OrdenTrabajo.empresa_id == context.empresa_id, branch_scope(context, OrdenTrabajo.sucursal_id)))
    if not order: raise HTTPException(status_code=404, detail="Orden no encontrada")
    rows = (await db.scalars(select(Inspeccion).where(Inspeccion.orden_id == order_id, Inspeccion.empresa_id == context.empresa_id).order_by(Inspeccion.created_at.desc()))).all()
    return [await serialize(db, row) for row in rows]


@router.post("", response_model=InspeccionRead, status_code=status.HTTP_201_CREATED)
async def create_inspection(payload: InspeccionCreate, context: CurrentContext, db: AsyncSession = Depends(get_db)):
    order = await db.scalar(select(OrdenTrabajo).where(OrdenTrabajo.id == payload.orden_id, OrdenTrabajo.empresa_id == context.empresa_id))
    if not order: raise HTTPException(status_code=404, detail="Orden no encontrada")
    ensure_branch_access(context, order.sucursal_id)
    inspection = Inspeccion(empresa_id=context.empresa_id, **payload.model_dump(exclude={"items"}))
    db.add(inspection); await db.flush()
    for index, item in enumerate(payload.items): db.add(InspeccionItem(empresa_id=context.empresa_id, inspeccion_id=inspection.id, orden_visual=index, **item.model_dump()))
    record_audit(db, context, "crear", "inspecciones", inspection.id, after={"tipo": inspection.tipo}); await db.commit(); await db.refresh(inspection)
    return await serialize(db, inspection)


@router.post("/{inspection_id}/confirmar", response_model=InspeccionRead)
async def confirm_inspection(inspection_id: uuid.UUID, payload: InspeccionConfirmar, context: CurrentContext, db: AsyncSession = Depends(get_db)):
    inspection = await db.scalar(select(Inspeccion).where(Inspeccion.id == inspection_id, Inspeccion.empresa_id == context.empresa_id))
    if not inspection: raise HTTPException(status_code=404, detail="Inspección no encontrada")
    order = await db.scalar(select(OrdenTrabajo).where(OrdenTrabajo.id == inspection.orden_id, OrdenTrabajo.empresa_id == context.empresa_id))
    if not order: raise HTTPException(status_code=404, detail="Orden no encontrada")
    ensure_branch_access(context, order.sucursal_id)
    if inspection.confirmada_at: raise HTTPException(status_code=409, detail="La inspección ya está confirmada")
    inspection.confirmada_at = datetime.now(timezone.utc); inspection.confirmada_by = context.usuario.id
    await db.commit(); return await serialize(db, inspection)


@router.post("/{inspection_id}/archivos", response_model=ArchivoRead, status_code=status.HTTP_201_CREATED)
async def upload_file(inspection_id: uuid.UUID, context: CurrentContext, archivo: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    inspection = await db.scalar(select(Inspeccion).where(Inspeccion.id == inspection_id, Inspeccion.empresa_id == context.empresa_id))
    if not inspection: raise HTTPException(status_code=404, detail="Inspección no encontrada")
    order = await db.scalar(select(OrdenTrabajo).where(OrdenTrabajo.id == inspection.orden_id, OrdenTrabajo.empresa_id == context.empresa_id))
    if not order: raise HTTPException(status_code=404, detail="Orden no encontrada")
    ensure_branch_access(context, order.sucursal_id)
    if archivo.content_type not in ALLOWED_TYPES: raise HTTPException(status_code=422, detail="Solo se permiten imágenes JPG, PNG o WebP")
    content = await archivo.read(MAX_SIZE + 1)
    if len(content) > MAX_SIZE: raise HTTPException(status_code=422, detail="La imagen supera 8 MB")
    if not settings.supabase_url or not settings.supabase_service_role_key: raise HTTPException(status_code=503, detail="Supabase Storage no está configurado")
    extension = Path(archivo.filename or "").suffix.lower() or ".jpg"
    path = f"{context.empresa_id}/ordenes/{inspection.orden_id}/inspecciones/{inspection.id}/{uuid.uuid4()}{extension}"
    endpoint = f"{settings.supabase_url}/storage/v1/object/{settings.supabase_storage_bucket}/{path}"
    headers = {"Authorization": f"Bearer {settings.supabase_service_role_key}", "apikey": settings.supabase_service_role_key, "Content-Type": archivo.content_type, "x-upsert": "false"}
    async with httpx.AsyncClient(timeout=30) as client: response = await client.post(endpoint, headers=headers, content=content)
    if not response.is_success: raise HTTPException(status_code=502, detail="No se pudo guardar la imagen en Supabase Storage")
    file = Archivo(empresa_id=context.empresa_id, orden_id=None, inspeccion_id=inspection.id, tipo="foto", nombre_original=archivo.filename or "imagen", storage_path=path, mime_type=archivo.content_type, tamano_bytes=len(content), created_by=context.usuario.id)
    db.add(file); await db.commit(); await db.refresh(file)
    return ArchivoRead(id=file.id, nombre_original=file.nombre_original, mime_type=file.mime_type, tamano_bytes=file.tamano_bytes, created_at=file.created_at, url=await storage_url(path))
