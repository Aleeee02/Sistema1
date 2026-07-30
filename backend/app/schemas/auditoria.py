import uuid
from datetime import datetime
from typing import Any
from app.schemas.common import ORMModel

class AuditoriaRead(ORMModel):
    id: uuid.UUID
    usuario_id: uuid.UUID | None
    usuario_nombre: str
    accion: str
    entidad: str
    entidad_id: uuid.UUID | None
    datos_anteriores: dict[str, Any] | None
    datos_nuevos: dict[str, Any] | None
    ip: str | None
    created_at: datetime

class AuditoriaOpciones(ORMModel):
    acciones: list[str]
    entidades: list[str]
