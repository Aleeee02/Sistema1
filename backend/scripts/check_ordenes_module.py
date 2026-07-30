"""Comprueba, sin modificar datos, la estructura necesaria para órdenes."""

import asyncio

from sqlalchemy import text

from app.db.session import engine

REQUIRED = {
    "sucursales": {"id", "empresa_id", "nombre", "es_principal", "estado"},
    "ordenes_trabajo": {
        "id", "empresa_id", "sucursal_id", "numero", "cliente_id",
        "vehiculo_id", "estado", "kilometraje", "nivel_combustible",
        "falla_reportada", "diagnostico", "observaciones", "subtotal",
        "descuento", "impuesto", "total", "saldo", "fecha_recepcion",
        "fecha_estimada_entrega", "fecha_entrega", "created_by",
        "created_at", "updated_at",
    },
}


async def main() -> None:
    async with engine.connect() as connection:
        rows = (
            await connection.execute(
                text(
                    """
                    SELECT table_name, column_name
                    FROM information_schema.columns
                    WHERE table_schema = 'public' AND table_name = ANY(:tables)
                    """
                ),
                {"tables": list(REQUIRED)},
            )
        ).all()
        found = {table: set() for table in REQUIRED}
        for table, column in rows:
            found[table].add(column)
        failed = False
        for table, columns in REQUIRED.items():
            missing = sorted(columns - found[table])
            if missing:
                failed = True
                print(f"{table}: FALTAN {', '.join(missing)}")
            else:
                print(f"{table}: OK ({len(columns)} columnas)")
        if failed:
            raise SystemExit(1)
        print("STATUS=ORDENES_MODULE_READY")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
