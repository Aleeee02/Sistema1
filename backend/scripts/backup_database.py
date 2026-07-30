import argparse
from datetime import UTC, datetime, timedelta
import os
from pathlib import Path
import shutil
import subprocess
import sys

from sqlalchemy.engine import make_url

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import settings


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BACKUP_DIR = ROOT / "backups"


def pg_tools() -> tuple[str, str | None]:
    pg_dump = shutil.which("pg_dump")
    pg_restore = shutil.which("pg_restore")
    if not pg_dump and os.name == "nt":
        postgresql_root = Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "PostgreSQL"
        versions = sorted(
            (path for path in postgresql_root.glob("*") if path.is_dir()),
            key=lambda path: tuple(
                int(part) if part.isdigit() else 0 for part in path.name.split(".")
            ),
            reverse=True,
        )
        for version in versions:
            candidate_dump = version / "bin" / "pg_dump.exe"
            if candidate_dump.exists():
                pg_dump = str(candidate_dump)
                candidate_restore = version / "bin" / "pg_restore.exe"
                pg_restore = str(candidate_restore) if candidate_restore.exists() else None
                break
    if not pg_dump:
        raise RuntimeError(
            "No se encontró pg_dump. Instala PostgreSQL Client Tools y vuelve "
            "a ejecutar el respaldo."
        )
    return pg_dump, pg_restore


def safe_backup_dir(value: str | None) -> Path:
    backup_dir = Path(value).resolve() if value else DEFAULT_BACKUP_DIR.resolve()
    backup_dir.mkdir(parents=True, exist_ok=True)
    return backup_dir


def cleanup_old_backups(backup_dir: Path, retention_days: int) -> int:
    cutoff = datetime.now(UTC) - timedelta(days=retention_days)
    removed = 0
    for path in backup_dir.glob("taller_*.dump"):
        if not path.is_file() or path.resolve().parent != backup_dir:
            continue
        modified = datetime.fromtimestamp(path.stat().st_mtime, tz=UTC)
        if modified < cutoff:
            path.unlink()
            removed += 1
    return removed


def create_backup(output_dir: str | None, retention_days: int) -> Path:
    pg_dump, pg_restore = pg_tools()
    backup_dir = safe_backup_dir(output_dir)
    database = make_url(settings.database_url)
    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    output = backup_dir / f"taller_{timestamp}.dump"

    environment = os.environ.copy()
    if database.password:
        environment["PGPASSWORD"] = database.password

    command = [
        pg_dump,
        "--host",
        database.host or "",
        "--port",
        str(database.port or 5432),
        "--username",
        database.username or "",
        "--dbname",
        database.database or "postgres",
        "--format",
        "custom",
        "--no-owner",
        "--no-privileges",
        "--file",
        str(output),
    ]
    subprocess.run(command, env=environment, check=True)

    if not output.exists() or output.stat().st_size == 0:
        raise RuntimeError("El archivo de respaldo quedó vacío")
    if pg_restore:
        subprocess.run(
            [pg_restore, "--list", str(output)],
            check=True,
            stdout=subprocess.DEVNULL,
        )

    removed = cleanup_old_backups(backup_dir, retention_days)
    print(f"Respaldo creado: {output}")
    print(f"Tamaño: {output.stat().st_size / 1024 / 1024:.2f} MB")
    print(f"Respaldos antiguos eliminados: {removed}")
    return output


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Crea y verifica un respaldo PostgreSQL en formato custom."
    )
    parser.add_argument("--output-dir")
    parser.add_argument("--retention-days", type=int, default=30)
    arguments = parser.parse_args()
    if arguments.retention_days < 1:
        parser.error("--retention-days debe ser mayor que cero")
    return arguments


if __name__ == "__main__":
    args = parse_args()
    try:
        create_backup(args.output_dir, args.retention_days)
    except (RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
