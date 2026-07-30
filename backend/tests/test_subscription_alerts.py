from datetime import date, timedelta

from app.models.empresa import Empresa
from app.services.alertas_suscripciones import _alert_for


def company_ending(days: int, grace: int = 5) -> Empresa:
    return Empresa(
        nombre_comercial="Taller",
        razon_social="Taller SAC",
        ruc="20123456789",
        suscripcion_fin=date.today() + timedelta(days=days),
        suscripcion_estado="activa",
        dias_gracia=grace,
    )


def test_alerts_before_expiration() -> None:
    assert _alert_for(company_ending(7), date.today())[0] == "vence_7_dias"
    assert _alert_for(company_ending(3), date.today())[0] == "vence_3_dias"
    assert _alert_for(company_ending(0), date.today())[0] == "vence_hoy"


def test_alert_during_grace_period() -> None:
    assert _alert_for(company_ending(-2), date.today())[0] == "periodo_gracia"


def test_alert_after_grace_period() -> None:
    assert _alert_for(company_ending(-6), date.today())[0] == "acceso_bloqueado"
