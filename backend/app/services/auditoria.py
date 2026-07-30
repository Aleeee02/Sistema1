import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import AuthContext
from app.models.auditoria import Auditoria


def record_audit(
    db: AsyncSession,
    context: AuthContext,
    action: str,
    entity: str,
    entity_id: uuid.UUID,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
) -> None:
    db.add(
        Auditoria(
            empresa_id=context.empresa_id,
            usuario_id=context.usuario.id,
            accion=action,
            entidad=entity,
            entidad_id=entity_id,
            datos_anteriores=before,
            datos_nuevos=after,
        )
    )
