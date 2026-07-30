from app.models.orden import OrdenTrabajo


def test_fecha_recepcion_uses_database_default() -> None:
    column = OrdenTrabajo.__table__.c.fecha_recepcion
    assert column.nullable is False
    assert column.server_default is not None
