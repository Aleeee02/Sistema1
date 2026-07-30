from app.models.cotizacion import CotizacionItem


def test_cotizacion_item_mapper_can_be_configured() -> None:
    """Evita referencias ORM a tablas aún no mapeadas."""
    assert CotizacionItem.__mapper__.local_table.name == "cotizaciones_items"
    assert CotizacionItem.__table__.c.producto_id.type.python_type is not None
