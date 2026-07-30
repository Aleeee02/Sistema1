import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.notificacion import Notificacion

def notify(db: AsyncSession, empresa_id: uuid.UUID, tipo: str, titulo: str, mensaje: str, enlace: str | None = None, sucursal_id: uuid.UUID | None = None, usuario_id: uuid.UUID | None = None):
    db.add(Notificacion(empresa_id=empresa_id, sucursal_id=sucursal_id, usuario_id=usuario_id, tipo=tipo, titulo=titulo, mensaje=mensaje, enlace=enlace))
