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
        / "2026_07_29_roles_personalizados.sql"
    ).read_text(encoding="utf-8")
    connection = await asyncpg.connect(
        database_url,
        ssl="require" if settings.database_ssl else None,
    )
    try:
        await connection.execute(sql)
        table_name = await connection.fetchval(
            "SELECT to_regclass('public.roles_permisos')::text"
        )
        if table_name != "roles_permisos":
            raise RuntimeError("La migración de roles no pudo verificarse")
        print("Migración aplicada: roles personalizados y permisos")
    finally:
        await connection.close()


if __name__ == "__main__":
    asyncio.run(main())
