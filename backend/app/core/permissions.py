from collections.abc import Iterable


ROLE_PERMISSIONS: dict[str, set[str]] = {
    "superadmin": {"*"},
    "administrador": {"*"},
    "recepcionista": {
        "dashboard.ver", "agenda.ver", "agenda.gestionar",
        "clientes.ver", "clientes.gestionar", "vehiculos.ver",
        "vehiculos.gestionar", "ordenes.ver", "ordenes.gestionar",
        "cotizaciones.ver", "cotizaciones.gestionar", "inspecciones.ver",
        "pagos.ver", "pagos.gestionar", "servicios.ver", "inventario.ver",
        "comprobantes.ver", "comprobantes.gestionar",
        "agenda.citas", "ordenes.editar", "ordenes.avanzar",
        "cotizaciones.editar", "cotizaciones.cambiar_estado", "pagos.registrar",
    },
    "asesor": {
        "dashboard.ver", "agenda.ver", "agenda.gestionar",
        "clientes.ver", "clientes.gestionar", "vehiculos.ver",
        "vehiculos.gestionar", "ordenes.ver", "ordenes.gestionar",
        "cotizaciones.ver", "cotizaciones.gestionar", "inspecciones.ver",
        "pagos.ver", "servicios.ver", "inventario.ver",
        "agenda.citas", "ordenes.editar", "ordenes.avanzar",
        "cotizaciones.editar", "cotizaciones.cambiar_estado",
    },
    "mecanico": {
        "dashboard.ver", "agenda.ver", "ordenes.ver", "ordenes.gestionar",
        "cotizaciones.ver", "inspecciones.ver", "inspecciones.gestionar",
        "servicios.ver", "inventario.ver",
        "ordenes.avanzar",
    },
    "tecnico": {
        "dashboard.ver", "agenda.ver", "ordenes.ver", "ordenes.gestionar",
        "cotizaciones.ver", "inspecciones.ver", "inspecciones.gestionar",
        "servicios.ver", "inventario.ver",
        "ordenes.avanzar",
    },
    "almacen": {
        "dashboard.ver", "ordenes.ver", "cotizaciones.ver",
        "cotizaciones.gestionar", "inventario.ver", "inventario.gestionar",
        "transferencias.ver", "transferencias.gestionar", "servicios.ver",
        "cotizaciones.recibir", "reservas.consumir",
    },
    "cajero": {
        "dashboard.ver", "clientes.ver", "ordenes.ver", "cotizaciones.ver",
        "pagos.ver", "pagos.gestionar", "reportes.ver",
        "comprobantes.ver", "comprobantes.gestionar",
        "pagos.registrar",
    },
}

DASHBOARD_READ_PERMISSIONS = {
    "dashboard.ver",
    "estadisticas.ver",
    "sucursales.ver",
    "ordenes.ver",
    "inventario.ver",
}

ACTION_PERMISSIONS = {
    "agenda.configurar", "agenda.citas",
    "ordenes.editar", "ordenes.avanzar",
    "cotizaciones.editar", "cotizaciones.cambiar_estado",
    "cotizaciones.recibir", "reservas.consumir",
    "pagos.registrar", "pagos.configurar", "pagos.anular",
}


def permissions_for_role(role_code: str) -> set[str]:
    permissions = ROLE_PERMISSIONS.get(role_code.lower())
    if permissions is None:
        return set()
    if "*" in permissions:
        return permissions
    return permissions | DASHBOARD_READ_PERMISSIONS


def has_permission(role_code: str, permission: str) -> bool:
    permissions = permissions_for_role(role_code)
    return "*" in permissions or permission in permissions


def visible_permissions(role_code: str, all_permissions: Iterable[str]) -> list[str]:
    permissions = permissions_for_role(role_code)
    return sorted(set(all_permissions) if "*" in permissions else permissions)
