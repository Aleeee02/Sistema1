import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import CurrentContext
from app.db.session import get_db
from app.models.auditoria import Auditoria
from app.models.usuario import Usuario
from app.schemas.auditoria import AuditoriaOpciones, AuditoriaRead

router=APIRouter()

@router.get("/opciones",response_model=AuditoriaOpciones)
async def options(context:CurrentContext,db:AsyncSession=Depends(get_db)):
    actions=list((await db.scalars(select(Auditoria.accion).where(Auditoria.empresa_id==context.empresa_id).distinct().order_by(Auditoria.accion))).all())
    entities=list((await db.scalars(select(Auditoria.entidad).where(Auditoria.empresa_id==context.empresa_id).distinct().order_by(Auditoria.entidad))).all())
    return AuditoriaOpciones(acciones=actions,entidades=entities)

@router.get("",response_model=list[AuditoriaRead])
async def list_audit(context:CurrentContext,accion:str|None=None,entidad:str|None=None,usuario_id:uuid.UUID|None=None,desde:datetime|None=None,hasta:datetime|None=None,limit:int=Query(default=100,ge=1,le=300),db:AsyncSession=Depends(get_db)):
    name=func.trim(func.concat(Usuario.nombres," ",Usuario.apellidos))
    query=select(Auditoria,name.label("usuario_nombre")).outerjoin(Usuario,Usuario.id==Auditoria.usuario_id).where(Auditoria.empresa_id==context.empresa_id)
    if accion: query=query.where(Auditoria.accion==accion)
    if entidad: query=query.where(Auditoria.entidad==entidad)
    if usuario_id: query=query.where(Auditoria.usuario_id==usuario_id)
    if desde: query=query.where(Auditoria.created_at>=desde)
    if hasta: query=query.where(Auditoria.created_at<=hasta)
    rows=(await db.execute(query.order_by(Auditoria.created_at.desc()).limit(limit))).all()
    return [AuditoriaRead(id=r[0].id,usuario_id=r[0].usuario_id,usuario_nombre=r.usuario_nombre or "Sistema",accion=r[0].accion,entidad=r[0].entidad,entidad_id=r[0].entidad_id,datos_anteriores=r[0].datos_anteriores,datos_nuevos=r[0].datos_nuevos,ip=str(r[0].ip) if r[0].ip else None,created_at=r[0].created_at) for r in rows]
