"""Persist analyzed research chart windows.

Revision ID: 0004_research_window_history
Revises: 0003_intraday_work_queue
Create Date: 2026-07-08
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

revision = "0004_research_window_history"
down_revision = "0003_intraday_work_queue"
branch_labels = None
depends_on = None


def _json_type() -> sa.types.TypeEngine:
    return postgresql.JSONB().with_variant(sa.JSON(), "sqlite")


def _has_table(table_name: str) -> bool:
    return inspect(op.get_bind()).has_table(table_name)


def _column_names(table_name: str) -> set[str]:
    if not _has_table(table_name):
        return set()
    return {column["name"] for column in inspect(op.get_bind()).get_columns(table_name)}


def _add_column_if_missing(table_name: str, column: sa.Column) -> None:
    if column.name not in _column_names(table_name):
        op.add_column(table_name, column)


def _create_index_if_missing(
    index_name: str,
    table_name: str,
    columns: list[str],
    *,
    unique: bool = False,
) -> None:
    indexes = {index["name"] for index in inspect(op.get_bind()).get_indexes(table_name)}
    if index_name not in indexes:
        op.create_index(index_name, table_name, columns, unique=unique)


def upgrade() -> None:
    json_type = _json_type()
    if not _has_table("research_analyzed_windows"):
        op.create_table(
            "research_analyzed_windows",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("fingerprint", sa.String(length=80), nullable=False),
            sa.Column("run_id", sa.Integer(), nullable=True),
            sa.Column("cadence", sa.String(length=24), nullable=False),
            sa.Column("universe_key", sa.String(length=160), nullable=False),
            sa.Column("universe_scope", sa.String(length=80), nullable=False),
            sa.Column("universe_file", sa.String(length=500), nullable=False),
            sa.Column("universe_hash", sa.String(length=80), nullable=False),
            sa.Column("symbol", sa.String(length=24), nullable=False),
            sa.Column("timeframe", sa.String(length=16), nullable=False),
            sa.Column("window_start", sa.String(length=80), nullable=False),
            sa.Column("window_end", sa.String(length=80), nullable=False),
            sa.Column("window_size", sa.Integer(), nullable=False),
            sa.Column("forward_end", sa.String(length=80), nullable=False),
            sa.Column("data_period", sa.String(length=40), nullable=False),
            sa.Column("data_manifest_hash", sa.String(length=80), nullable=False),
            sa.Column("data_artifact_path", sa.String(length=500), nullable=False),
            sa.Column("data_artifact_sha256", sa.String(length=80), nullable=False),
            sa.Column("data_rows", sa.Integer(), nullable=False),
            sa.Column("source_kind", sa.String(length=40), nullable=False),
            sa.Column("source_artifact_path", sa.String(length=500), nullable=False),
            sa.Column("metadata_json", json_type, nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["run_id"], ["discovery_runs.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("fingerprint", name="uq_research_analyzed_windows_fingerprint"),
        )
    else:
        defaults = {
            "cadence": "VARCHAR(24) DEFAULT '' NOT NULL",
            "universe_key": "VARCHAR(160) DEFAULT '' NOT NULL",
            "universe_scope": "VARCHAR(80) DEFAULT '' NOT NULL",
            "universe_file": "VARCHAR(500) DEFAULT '' NOT NULL",
            "universe_hash": "VARCHAR(80) DEFAULT '' NOT NULL",
            "forward_end": "VARCHAR(80) DEFAULT '' NOT NULL",
            "data_period": "VARCHAR(40) DEFAULT '' NOT NULL",
            "data_manifest_hash": "VARCHAR(80) DEFAULT '' NOT NULL",
            "data_artifact_path": "VARCHAR(500) DEFAULT '' NOT NULL",
            "data_artifact_sha256": "VARCHAR(80) DEFAULT '' NOT NULL",
            "data_rows": "INTEGER DEFAULT 0 NOT NULL",
            "source_kind": "VARCHAR(40) DEFAULT 'sampler' NOT NULL",
            "source_artifact_path": "VARCHAR(500) DEFAULT '' NOT NULL",
        }
        existing = _column_names("research_analyzed_windows")
        bind = op.get_bind()
        for name, ddl in defaults.items():
            if name not in existing:
                bind.execute(sa.text(f"ALTER TABLE research_analyzed_windows ADD COLUMN {name} {ddl}"))
        if "metadata_json" not in existing:
            op.add_column(
                "research_analyzed_windows",
                sa.Column("metadata_json", json_type, nullable=False, server_default=sa.text("'{}'")),
            )

    _create_index_if_missing(
        "ix_research_analyzed_windows_fingerprint",
        "research_analyzed_windows",
        ["fingerprint"],
        unique=True,
    )
    _create_index_if_missing(
        "ix_research_analyzed_windows_universe_symbol_timeframe",
        "research_analyzed_windows",
        ["universe_key", "symbol", "timeframe"],
    )
    _create_index_if_missing(
        "ix_research_analyzed_windows_window_end",
        "research_analyzed_windows",
        ["window_end"],
    )
    _create_index_if_missing(
        "ix_research_analyzed_windows_run_id",
        "research_analyzed_windows",
        ["run_id"],
    )
    _create_index_if_missing(
        "ix_research_analyzed_windows_universe_key",
        "research_analyzed_windows",
        ["universe_key"],
    )
    _create_index_if_missing(
        "ix_research_analyzed_windows_source_kind",
        "research_analyzed_windows",
        ["source_kind"],
    )
    _create_index_if_missing(
        "ix_research_analyzed_windows_source_artifact",
        "research_analyzed_windows",
        ["source_artifact_path"],
    )


def downgrade() -> None:
    raise NotImplementedError("Downgrades are blocked for Tradeo safety migrations")
