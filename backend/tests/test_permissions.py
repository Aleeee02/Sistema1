from app.core.permissions import has_permission, permissions_for_role


def test_administrator_has_every_permission() -> None:
    assert has_permission("administrador", "usuarios.gestionar")
    assert has_permission("administrador", "inventario.gestionar")


def test_operational_roles_have_limited_write_access() -> None:
    assert has_permission("mecanico", "inspecciones.gestionar")
    assert not has_permission("mecanico", "pagos.gestionar")
    assert has_permission("almacen", "transferencias.gestionar")
    assert not has_permission("almacen", "usuarios.ver")
    assert has_permission("cajero", "pagos.registrar")
    assert not has_permission("cajero", "pagos.anular")
    assert not has_permission("cajero", "pagos.configurar")
    assert has_permission("recepcionista", "cotizaciones.editar")
    assert not has_permission("mecanico", "cotizaciones.editar")


def test_dashboard_dependencies_are_read_only() -> None:
    permissions = permissions_for_role("cajero")
    assert "estadisticas.ver" in permissions
    assert "inventario.ver" in permissions
    assert "inventario.gestionar" not in permissions


def test_unknown_role_has_no_permissions() -> None:
    assert permissions_for_role("rol_desconocido") == set()
