from sqlalchemy.ext.asyncio import AsyncSession

from app.models.orden import OrdenEstadoHistorial


def record_order_status(
    db: AsyncSession,
    *,
    empresa_id,
    orden_id,
    previous: str | None,
    current: str,
    usuario_id,
    reason: str | None = None,
) -> None:
    if previous == current:
        return
    db.add(
        OrdenEstadoHistorial(
            empresa_id=empresa_id,
            orden_id=orden_id,
            estado_anterior=previous,
            estado_nuevo=current,
            motivo=reason,
            usuario_id=usuario_id,
        )
    )
