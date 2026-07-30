from pathlib import Path

from scripts.backup_database import cleanup_old_backups
from scripts.migrate import checksum, migration_files


def test_migrations_are_sorted_and_have_checksums() -> None:
    files = migration_files()
    assert files
    assert [path.name for path in files] == sorted(path.name for path in files)
    assert all(len(checksum(path)) == 64 for path in files)


def test_backup_cleanup_ignores_unrelated_files(tmp_path: Path) -> None:
    unrelated = tmp_path / "documento.txt"
    unrelated.write_text("conservar", encoding="utf-8")

    removed = cleanup_old_backups(tmp_path.resolve(), retention_days=30)

    assert removed == 0
    assert unrelated.exists()
