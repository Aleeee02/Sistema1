import uuid
from datetime import datetime
from app.schemas.common import ORMModel

class NotificacionRead(ORMModel):
    id: uuid.UUID
    tipo: str
    titulo: str
    mensaje: str
    enlace: str | None
    leida: bool
    created_at: datetime
