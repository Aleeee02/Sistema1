import argparse
import asyncio
import hashlib
from pathlib import Path
import sys

import asyncpg

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import settings


ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS_DIR = ROOT / "sql"
LOCK_ID = 741_852_963


def migration_files() -> list[Path]:
    return sorted(MIGRATIONS_DIR.glob("*.sql"), key=lambda path: path.name)


def checksum(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


async def connect() -> asyncpg.Connection:
    database_url = settings.database_url.replace(
        "postgresql+asyncpg://", "postgresql://", 1
    )
    return await asyncpg.connect(
        database_url,
        ssl="require" if settings.database_ssl else None,
    )


async def status() -> int:
    connection = await connect()
    try:
        table_exists = await connection.fetchval(
            "SELECT to_regclass('public.schema_migrations') IS NOT NULL"
        )
        applied = {}
        if table_exists:
            rows = await connection.fetch(
                "SELECT version, checksum FROM public.schema_migrations"
            )
            applied = {row["version"]: row["checksum"] for row in rows}

        invalid = False
        for path in migration_files():
            current_checksum = checksum(path)
            saved_checksum = applied.get(path.name)
            if saved_checksum is None:
                state = "pendiente"
            elif saved_checksum == current_checksum:
                state = "aplicada"
            else:
                state = "MODIFICADA"
                invalid = True
            print(f"{state:10} {path.name}")
        return 1 if invalid else 0
    finally:
        await connection.close()


async def apply() -> int:
    connection = await connect()
    try:
        await connection.execute(
            """
            CREATE TABLE IF NOT EXISTS public.schema_migrations (
                version VARCHAR(255) PRIMARY KEY,
                checksum VARCHAR(64) NOT NULL,
                applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
        await connection.execute("SELECT pg_advisory_lock($1)", LOCK_ID)
        try:
            rows = await connection.fetch(
                "SELECT version, checksum FROM public.schema_migrations"
            )
            applied = {row["version"]: row["checksum"] for row in rows}
            applied_count = 0

            for path in migration_files():
                current_checksum = checksum(path)
                saved_checksum = applied.get(path.name)
                if saved_checksum:
                    if saved_checksum != current_checksum:
                        raise RuntimeError(
                            f"La migración aplicada {path.name} fue modificada"
                        )
                    print(f"omitida    {path.name}")
                    continue

                async with connection.transaction():
                    await connection.execute(path.read_text(encoding="utf-8"))
                    await connection.execute(
                        """
                        INSERT INTO public.schema_migrations (version, checksum)
                        VALUES ($1, $2)
                        """,
                        path.name,
                        current_checksum,
                    )
                applied_count += 1
                print(f"aplicada   {path.name}")

            print(f"Migraciones nuevas aplicadas: {applied_count}")
            return 0
        finally:
            await connection.execute("SELECT pg_advisory_unlock($1)", LOCK_ID)
    finally:
        await connection.close()


async def baseline() -> int:
    connection = await connect()
    try:
        async with connection.transaction():
            await connection.execute(
                """
                CREATE TABLE IF NOT EXISTS public.schema_migrations (
                    version VARCHAR(255) PRIMARY KEY,
                    checksum VARCHAR(64) NOT NULL,
                    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
            registered = 0
            for path in migration_files():
                result = await connection.execute(
                    """
                    INSERT INTO public.schema_migrations (version, checksum)
                    VALUES ($1, $2)
                    ON CONFLICT (version) DO NOTHING
                    """,
                    path.name,
                    checksum(path),
                )
                if result.endswith("1"):
                    registered += 1
                print(f"registrada {path.name}")
        print(f"Migraciones adoptadas en el registro: {registered}")
        return 0
    finally:
        await connection.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Aplica en orden las migraciones SQL pendientes."
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--status",
        action="store_true",
        help="Muestra el estado sin modificar la base de datos.",
    )
    mode.add_argument(
        "--baseline",
        action="store_true",
        help="Registra migraciones ya aplicadas sin ejecutar su SQL.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    arguments = parse_args()
    operation = baseline() if arguments.baseline else status() if arguments.status else apply()
    raise SystemExit(asyncio.run(operation))
