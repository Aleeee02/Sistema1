import asyncio
import logging
from datetime import date, datetime, timedelta, UTC

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from app.db.session import AsyncSessionLocal
from app.models.empresa import AlertaSuscripcion, Empresa
from app.models.usuario import Rol, Usuario, UsuarioEmpresa
from app.services.email import send_subscription_alert_email

logger = logging.getLogger(__name__)


def _alert_for(company: Empresa, today: date) -> tuple[str, str, str] | None:
    if not company.suscripcion_fin or company.suscripcion_estado == "cancelada":
        return None
    days = (company.suscripcion_fin - today).days
    if days == 7:
        return "vence_7_dias", "Tu suscripción vence en 7 días", f"Tu plan vence el {company.suscripcion_fin:%d/%m/%Y}."
    if days == 3:
        return "vence_3_dias", "Tu suscripción vence en 3 días", f"Tu plan vence el {company.suscripcion_fin:%d/%m/%Y}."
    if days == 0:
        return "vence_hoy", "Tu suscripción vence hoy", "Renueva tu plan para mantener el acceso al sistema."
    if days < 0 and today <= company.suscripcion_fin + timedelta(days=company.dias_gracia):
        return "periodo_gracia", "Tu suscripción está en periodo de gracia", f"Dispones de {company.dias_gracia} días de gracia antes del bloqueo."
    if days < -company.dias_gracia:
        return "acceso_bloqueado", "Acceso suspendido por vencimiento", "El periodo de gracia terminó. Renueva el plan para reactivar el acceso."
    return None


async def process_subscription_alerts() -> dict[str, int]:
    created = sent = failed = 0
    async with AsyncSessionLocal() as db:
        companies = (
            await db.scalars(
                select(Empresa).where(
                    Empresa.estado == "activo",
                    Empresa.suscripcion_fin.is_not(None),
                )
            )
        ).all()
        today = date.today()
        for company in companies:
            alert_data = _alert_for(company, today)
            if not alert_data:
                continue
            alert_type, subject, text = alert_data
            recipient = company.email or await db.scalar(
                select(Usuario.email)
                .join(UsuarioEmpresa, UsuarioEmpresa.usuario_id == Usuario.id)
                .join(Rol, Rol.id == UsuarioEmpresa.rol_id)
                .where(
                    UsuarioEmpresa.empresa_id == company.id,
                    UsuarioEmpresa.estado == "activo",
                    Rol.codigo == "administrador",
                )
                .order_by(UsuarioEmpresa.created_at)
                .limit(1)
            )
            if not recipient:
                continue
            alert_id = await db.scalar(
                insert(AlertaSuscripcion)
                .values(
                    empresa_id=company.id,
                    tipo=alert_type,
                    fecha_vencimiento=company.suscripcion_fin,
                    destinatario=recipient,
                )
                .on_conflict_do_nothing(
                    index_elements=["empresa_id", "tipo", "fecha_vencimiento"]
                )
                .returning(AlertaSuscripcion.id)
            )
            await db.commit()
            if not alert_id:
                alert = await db.scalar(
                    select(AlertaSuscripcion).where(
                        AlertaSuscripcion.empresa_id == company.id,
                        AlertaSuscripcion.tipo == alert_type,
                        AlertaSuscripcion.fecha_vencimiento == company.suscripcion_fin,
                    )
                )
                if not alert or alert.estado != "error":
                    continue
                alert.estado = "pendiente"
                alert.error = None
                await db.commit()
            else:
                created += 1
                alert = await db.get(AlertaSuscripcion, alert_id)
            try:
                delivered = await send_subscription_alert_email(recipient, company.nombre_comercial, subject, text)
                alert.estado = "enviada" if delivered else "error"
                alert.error = None if delivered else "Servicio de correo no configurado"
                alert.enviado_at = datetime.now(UTC) if delivered else None
                sent += int(delivered)
                failed += int(not delivered)
            except Exception as exc:
                logger.exception("No fue posible enviar una alerta de suscripción")
                alert.estado = "error"
                alert.error = str(exc)[:1000]
                failed += 1
            await db.commit()
    return {"creadas": created, "enviadas": sent, "errores": failed}


async def subscription_alert_loop() -> None:
    while True:
        try:
            await process_subscription_alerts()
        except Exception:
            logger.exception("Falló la revisión periódica de suscripciones")
        await asyncio.sleep(6 * 60 * 60)
