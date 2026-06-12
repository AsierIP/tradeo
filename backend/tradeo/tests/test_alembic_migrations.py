"""Alembic migration tree tests (informe §6.1, D-T1)."""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect

alembic_command = pytest.importorskip("alembic.command")
from alembic.config import Config  # noqa: E402

BACKEND_DIR = Path(__file__).resolve().parents[2]


def _alembic_config(database_url: str) -> Config:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


def test_alembic_upgrade_head_creates_all_metadata_tables(tmp_path) -> None:
    """`alembic upgrade head` on a fresh DB must yield the full model schema."""
    from tradeo.db.session import Base

    db_path = tmp_path / "alembic_fresh.sqlite"
    url = f"sqlite:///{db_path}"
    alembic_command.upgrade(_alembic_config(url), "head")

    engine = create_engine(url)
    try:
        created = set(inspect(engine).get_table_names())
    finally:
        engine.dispose()

    expected = set(Base.metadata.tables.keys())
    missing = expected - created
    assert not missing, f"migration head is missing tables: {sorted(missing)}"
    assert "alembic_version" in created
    assert "agent_messages" in created


def test_alembic_upgrade_head_is_idempotent_on_existing_schema(tmp_path) -> None:
    """Databases born via create_all adopt the tree without errors (baseline)."""
    from tradeo.db.session import Base

    db_path = tmp_path / "alembic_existing.sqlite"
    url = f"sqlite:///{db_path}"
    engine = create_engine(url)
    try:
        Base.metadata.create_all(engine)
    finally:
        engine.dispose()

    alembic_command.upgrade(_alembic_config(url), "head")

    engine = create_engine(url)
    try:
        tables = set(inspect(engine).get_table_names())
    finally:
        engine.dispose()
    assert "alembic_version" in tables


def test_baseline_downgrade_is_blocked(tmp_path) -> None:
    db_path = tmp_path / "alembic_downgrade.sqlite"
    url = f"sqlite:///{db_path}"
    config = _alembic_config(url)
    alembic_command.upgrade(config, "head")
    with pytest.raises(NotImplementedError):
        alembic_command.downgrade(config, "base")
