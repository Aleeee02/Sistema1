"""Valida, sin modificar datos, las tablas requeridas por clientes y vehículos."""

import asyncio

from sqlalchemy import text

from app.db.session import engine

REQUIRED = {
    "clientes": {
        "id", "empresa_id", "tipo_persona", "tipo_documento",
        "numero_documento", "nombres", "apellidos", "razon_social",
        "telefono", "email", "direccion", "autoriza_contacto",
        "observaciones", "estado", "created_at", "updated_at",
    },
    "vehiculos": {
        "id", "empresa_id", "placa", "vin", "marca", "modelo", "anio",
        "color", "combustible", "motor", "cilindrada", "estado",
        "created_at", "updated_at",
    },
    "vehiculos_clientes": {
        "id", "empresa_id", "vehiculo_id", "cliente_id", "fecha_inicio",
        "fecha_fin", "es_actual", "created_at",
    },
    "auditoria": {
        "id", "empresa_id", "usuario_id", "accion", "entidad", "entidad_id",
        "datos_anteriores", "datos_nuevos", "ip", "user_agent", "created_at",
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
                    WHERE table_schema = 'public'
                      AND table_name = ANY(:tables)
                    ORDER BY table_name, ordinal_position
                    """
                ),
                {"tables": list(REQUIRED)},
            )
        ).all()
        available: dict[str, set[str]] = {table: set() for table in REQUIRED}
        for table, column in rows:
            available[table].add(column)

        failed = False
        for table, expected in REQUIRED.items():
            missing = sorted(expected - available[table])
            if missing:
                failed = True
                print(f"{table}: FALTAN {', '.join(missing)}")
            else:
                print(f"{table}: OK ({len(expected)} columnas)")

        if failed:
            raise SystemExit(1)
        print("STATUS=CLIENTES_MODULE_READY")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
