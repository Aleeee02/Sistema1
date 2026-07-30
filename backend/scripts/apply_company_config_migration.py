import asyncio
from pathlib import Path
import sys

import asyncpg

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import settings


async def main() -> None:
    database_url = settings.database_url.replace(
        "postgresql+asyncpg://", "postgresql://", 1
    )
    sql = (
        Path(__file__).resolve().parents[1]
        / "sql"
        / "2026_07_29_configuracion_empresa.sql"
    ).read_text(encoding="utf-8")
    connection = await asyncpg.connect(
        database_url,
        ssl="require" if settings.database_ssl else None,
    )
    try:
        await connection.execute(sql)
        exists = await connection.fetchval(
            """
            SELECT count(*) = 7
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = 'empresas'
              AND column_name IN (
                'direccion_fiscal', 'telefono', 'email', 'sitio_web',
                'color_primario', 'prefijo_orden', 'prefijo_cotizacion'
              )
            """
        )
        if not exists:
            raise RuntimeError("La configuración de empresa no pudo verificarse")
        print("Migración aplicada: configuración de empresa")
    finally:
        await connection.close()


if __name__ == "__main__":
    asyncio.run(main())
