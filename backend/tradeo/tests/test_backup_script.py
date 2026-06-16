from __future__ import annotations

import os
import subprocess
import tarfile
from pathlib import Path


def _repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "ops/scripts/backup_tradeo.sh").exists():
            return parent
    raise AssertionError("could not find repository root")


def test_backup_script_includes_pg_dump_when_available(tmp_path: Path) -> None:
    repo_root = _repo_root()
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    pg_dump = fake_bin / "pg_dump"
    pg_dump.write_text(
        """#!/usr/bin/env bash
set -euo pipefail
for arg in "$@"; do
  case "$arg" in
    --file=*) dump="${arg#--file=}" ;;
  esac
done
echo fake-postgres-dump > "$dump"
""",
        encoding="utf-8",
    )
    pg_dump.chmod(0o755)

    env = {
        **os.environ,
        "PATH": f"{fake_bin}:{os.environ['PATH']}",
        "TRADEO_BACKUP_DIR": str(tmp_path / "backups"),
        "TRADEO_DATABASE_URL": "postgresql+psycopg://tradeo:tradeo@db:5432/tradeo",
    }

    result = subprocess.run(
        ["ops/scripts/backup_tradeo.sh"],
        cwd=repo_root,
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )

    archive = Path(result.stdout.strip())
    assert archive.exists()
    manifest = archive.with_name(archive.name.removesuffix(".tar.gz") + ".manifest")
    assert manifest.exists()
    assert "postgres_dump=ok" in manifest.read_text(encoding="utf-8")
    with tarfile.open(archive, "r:gz") as tar:
        names = tar.getnames()
    assert any(name.endswith(".dump") for name in names)
