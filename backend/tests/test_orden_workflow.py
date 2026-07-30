from app.api.v1.routes.ordenes import TRANSICIONES


def test_diagnostico_cannot_start_work_directly() -> None:
    assert "en_proceso" not in TRANSICIONES["diagnostico"]


def test_only_approved_order_can_start_work() -> None:
    assert "en_proceso" in TRANSICIONES["aprobada"]
    assert "en_proceso" not in TRANSICIONES["esperando_aprobacion"]
