"""Comprueba la estructura de reservas y cotizaciones sin modificar datos."""

import asyncio

from sqlalchemy import text

from app.db.session import engine

EXPECTED_CONSTRAINTS = {
    "ck_reserva_estado_fechas",
    "ck_reserva_referencia",
    "uq_cotizaciones_empresa_id",
    "uq_cotizaciones_items_empresa_cotizacion_id",
    "fk_reserva_empresa_cotizacion",
    "fk_reserva_empresa_cotizacion_item",
    "fk_reserva_empresa_sucursal_orden",
    "ck_cotizaciones_items_origen",
    "ck_cotizaciones_items_garantia",
    "ck_cotizaciones_items_origen_tipo",
    "ck_cotizaciones_items_cliente_no_cobrable",
    "ck_cotizaciones_items_origen_cobrable",
    "ck_cotizaciones_items_garantia_origen",
    "ck_cotizaciones_items_recibido_origen",
}

EXPECTED_COLUMNS = {
    "origen",
    "es_cobrable",
    "proveedor_nombre",
    "referencia_externa",
    "responsable_garantia",
    "recibido_at",
}


async def main() -> None:
    async with engine.connect() as connection:
        table_exists = await connection.scalar(
            text("SELECT to_regclass('public.reservas_inventario') IS NOT NULL")
        )
        columns = set(
            (
                await connection.execute(
                    text(
                        """
                        SELECT column_name
                        FROM information_schema.columns
                        WHERE table_schema = 'public'
                          AND table_name = 'cotizaciones_items'
                        """
                    )
                )
            ).scalars()
        )
        rows = (
            await connection.execute(
                text(
                    """
                    SELECT conname, conrelid::regclass::text,
                           pg_get_constraintdef(oid)
                    FROM pg_constraint
                    WHERE conname = ANY(:names)
                    ORDER BY conname
                    """
                ),
                {"names": sorted(EXPECTED_CONSTRAINTS)},
            )
        ).all()
        index_definition = await connection.scalar(
            text(
                """
                SELECT indexdef
                FROM pg_indexes
                WHERE schemaname = 'public'
                  AND tablename = 'reservas_inventario'
                  AND indexname = 'uq_reserva_activa_cotizacion_item'
                """
            )
        )
        rls = await connection.scalar(
            text(
                """
                SELECT relrowsecurity
                FROM pg_class
                WHERE oid = 'public.reservas_inventario'::regclass
                """
            )
        )

        found_constraints = {row.conname for row in rows}
        print(f"TABLE_RESERVAS={table_exists}")
        print(f"COLUMNS_OK={EXPECTED_COLUMNS.issubset(columns)}")
        print("MISSING_COLUMNS=" + ",".join(sorted(EXPECTED_COLUMNS - columns)))
        print(f"CONSTRAINTS={len(found_constraints)}/{len(EXPECTED_CONSTRAINTS)}")
        for name, table, definition in rows:
            print(f"{name}|{table}|{definition}")
        print(f"ACTIVE_RESERVATION_INDEX={index_definition is not None}")
        print(f"RLS_RESERVAS={rls}")

        ready = (
            table_exists
            and EXPECTED_COLUMNS.issubset(columns)
            and found_constraints == EXPECTED_CONSTRAINTS
            and index_definition is not None
            and rls is True
        )
        if not ready:
            missing = sorted(EXPECTED_CONSTRAINTS - found_constraints)
            if missing:
                print("MISSING=" + ",".join(missing))
            raise SystemExit(1)
        print("STATUS=RESERVAS_SCHEMA_READY")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
