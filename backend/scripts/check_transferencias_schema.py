"""Comprueba las tablas de transferencias sin modificar datos."""

import asyncio

from sqlalchemy import text

from app.db.session import engine


async def main() -> None:
    async with engine.connect() as connection:
        tables = (
            await connection.execute(
                text(
                    """
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                      AND table_name IN (
                        'transferencias_inventario',
                        'transferencias_inventario_items'
                      )
                    ORDER BY table_name
                    """
                )
            )
        ).scalars().all()
        constraints = (
            await connection.execute(
                text(
                    """
                    SELECT tc.table_name, tc.constraint_name, tc.constraint_type
                    FROM information_schema.table_constraints tc
                    WHERE tc.table_schema = 'public'
                      AND tc.table_name IN (
                        'transferencias_inventario',
                        'transferencias_inventario_items'
                      )
                    ORDER BY tc.table_name, tc.constraint_name
                    """
                )
            )
        ).all()
        rls = (
            await connection.execute(
                text(
                    """
                    SELECT relname, relrowsecurity
                    FROM pg_class
                    WHERE relname IN (
                        'transferencias_inventario',
                        'transferencias_inventario_items'
                    )
                    """
                )
            )
        ).all()

        print("TABLES=" + ",".join(tables))
        print(f"CONSTRAINTS={len(constraints)}")
        for table, name, kind in constraints:
            print(f"{table}|{kind}|{name}")
        for table, enabled in rls:
            print(f"RLS_{table}={enabled}")

        expected = {
            "transferencias_inventario",
            "transferencias_inventario_items",
        }
        if set(tables) != expected:
            raise SystemExit(1)
        print("STATUS=TRANSFERENCIAS_SCHEMA_READY")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
