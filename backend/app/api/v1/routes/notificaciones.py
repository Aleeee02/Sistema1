import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import CurrentContext, branch_scope
from app.db.session import get_db
from app.models.notificacion import Notificacion
from app.schemas.notificacion import NotificacionRead

router = APIRouter()

def scope(context):
    return (
        Notificacion.empresa_id == context.empresa_id,
        or_(Notificacion.usuario_id.is_(None), Notificacion.usuario_id == context.usuario.id),
        or_(Notificacion.sucursal_id.is_(None), branch_scope(context, Notificacion.sucursal_id)),
    )

@router.get("", response_model=list[NotificacionRead])
async def list_notifications(context: CurrentContext, db: AsyncSession = Depends(get_db)):
    return list((await db.scalars(select(Notificacion).where(*scope(context)).order_by(Notificacion.created_at.desc()).limit(30))).all())

@router.patch("/{notification_id}/leer", status_code=status.HTTP_204_NO_CONTENT)
async def read_notification(notification_id: uuid.UUID, context: CurrentContext, db: AsyncSession = Depends(get_db)):
    item = await db.scalar(select(Notificacion).where(Notificacion.id == notification_id, *scope(context)))
    if not item: raise HTTPException(status_code=404, detail="Notificación no encontrada")
    item.leida = True; item.leida_at = datetime.now(timezone.utc); await db.commit()

@router.post("/leer-todas", status_code=status.HTTP_204_NO_CONTENT)
async def read_all(context: CurrentContext, db: AsyncSession = Depends(get_db)):
    await db.execute(update(Notificacion).where(*scope(context), Notificacion.leida.is_(False)).values(leida=True, leida_at=datetime.now(timezone.utc))); await db.commit()
