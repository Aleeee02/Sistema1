from fastapi import APIRouter, Depends

from app.api.deps import require_module

from app.api.v1.routes import agenda, auditoria, auth, clientes, comprobantes, configuracion, cotizaciones, empleados, estadisticas, health, inspecciones, inventario, notificaciones, ordenes, pagos, reportes, roles, servicios, sucursales, transferencias, usuarios, vehiculos

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(agenda.router, prefix="/agenda", tags=["agenda"], dependencies=[Depends(require_module("agenda"))])
api_router.include_router(pagos.router, prefix="/pagos", tags=["pagos"], dependencies=[Depends(require_module("pagos"))])
api_router.include_router(inspecciones.router, prefix="/inspecciones", tags=["inspecciones"], dependencies=[Depends(require_module("inspecciones"))])
api_router.include_router(estadisticas.router, prefix="/estadisticas", tags=["estadísticas"], dependencies=[Depends(require_module("estadisticas"))])
api_router.include_router(reportes.router, prefix="/reportes", tags=["reportes"], dependencies=[Depends(require_module("reportes"))])
api_router.include_router(usuarios.router, prefix="/usuarios", tags=["usuarios"], dependencies=[Depends(require_module("usuarios"))])
api_router.include_router(roles.router, prefix="/roles", tags=["roles"], dependencies=[Depends(require_module("usuarios"))])
api_router.include_router(configuracion.router, prefix="/configuracion", tags=["configuración"], dependencies=[Depends(require_module("configuracion"))])
api_router.include_router(comprobantes.router, prefix="/comprobantes", tags=["comprobantes"], dependencies=[Depends(require_module("comprobantes"))])
api_router.include_router(notificaciones.router, prefix="/notificaciones", tags=["notificaciones"])
api_router.include_router(auditoria.router, prefix="/auditoria", tags=["auditoría"], dependencies=[Depends(require_module("auditoria"))])
api_router.include_router(auth.router)
api_router.include_router(clientes.router, prefix="/clientes", tags=["clientes"], dependencies=[Depends(require_module("clientes"))])
api_router.include_router(cotizaciones.router, prefix="/cotizaciones", tags=["cotizaciones"], dependencies=[Depends(require_module("cotizaciones"))])
api_router.include_router(empleados.router, prefix="/empleados", tags=["empleados"], dependencies=[Depends(require_module("empleados"))])
api_router.include_router(sucursales.router, prefix="/sucursales", tags=["sucursales"], dependencies=[Depends(require_module("sucursales"))])
api_router.include_router(inventario.router, prefix="/inventario", tags=["inventario"], dependencies=[Depends(require_module("inventario"))])
api_router.include_router(transferencias.router, prefix="/transferencias", tags=["transferencias"], dependencies=[Depends(require_module("transferencias"))])
api_router.include_router(servicios.router, prefix="/servicios", tags=["servicios"], dependencies=[Depends(require_module("servicios"))])
api_router.include_router(vehiculos.router, prefix="/vehiculos", tags=["vehículos"], dependencies=[Depends(require_module("vehiculos"))])
api_router.include_router(ordenes.router, prefix="/ordenes", tags=["órdenes"], dependencies=[Depends(require_module("ordenes"))])
