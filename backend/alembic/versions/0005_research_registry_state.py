"""Move research registry state into database tables.

Revision ID: 0005_research_registry_state
Revises: 0004_research_window_history
Create Date: 2026-07-08
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

revision = "0005_research_registry_state"
down_revision = "0004_research_window_history"
branch_labels = None
depends_on = None


def _json_type() -> sa.types.TypeEngine:
    return postgresql.JSONB().with_variant(sa.JSON(), "sqlite")


def _has_table(table_name: str) -> bool:
    return inspect(op.get_bind()).has_table(table_name)


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
    if not _has_table("research_experiment_registry_experiments"):
        op.create_table(
            "research_experiment_registry_experiments",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("experiment_id", sa.String(length=500), nullable=False),
            sa.Column("family_id", sa.String(length=160), nullable=False, server_default=""),
            sa.Column("pattern_key", sa.String(length=160), nullable=False, server_default=""),
            sa.Column("variant_id", sa.String(length=160), nullable=False, server_default=""),
            sa.Column("side", sa.String(length=8), nullable=False, server_default=""),
            sa.Column("timeframe", sa.String(length=16), nullable=False, server_default=""),
            sa.Column("window_size", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("first_run_id", sa.String(length=80), nullable=False, server_default=""),
            sa.Column("latest_run_id", sa.String(length=80), nullable=False, server_default=""),
            sa.Column("replication_count", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("candidate_trial_count", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("global_trial_count_after", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("edge_claim", sa.String(length=40), nullable=False, server_default="NO_DEMOSTRADO"),
            sa.Column("payload_json", json_type, nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("experiment_id", name="uq_research_registry_experiment_id"),
        )

    if not _has_table("research_experiment_registry_runs"):
        op.create_table(
            "research_experiment_registry_runs",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("run_id", sa.String(length=80), nullable=False),
            sa.Column("registered_at", sa.String(length=80), nullable=False, server_default=""),
            sa.Column("candidate_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("new_experiments", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("repeated_experiments", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("previous_registry_hash", sa.String(length=80), nullable=False, server_default=""),
            sa.Column("run_manifest_hash", sa.String(length=80), nullable=False, server_default=""),
            sa.Column("registry_hash", sa.String(length=80), nullable=False, server_default=""),
            sa.Column("params_json", json_type, nullable=False),
            sa.Column("payload_json", json_type, nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("run_id", name="uq_research_registry_run_id"),
        )

    if not _has_table("research_experiment_registry_snapshots"):
        op.create_table(
            "research_experiment_registry_snapshots",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("registry_hash", sa.String(length=80), nullable=False),
            sa.Column("previous_registry_hash", sa.String(length=80), nullable=False, server_default=""),
            sa.Column("run_manifest_hash", sa.String(length=80), nullable=False, server_default=""),
            sa.Column("global_trial_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("experiment_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("run_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("payload_json", json_type, nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("registry_hash", name="uq_research_registry_snapshot_hash"),
        )

    if not _has_table("research_artifact_retention"):
        op.create_table(
            "research_artifact_retention",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("source_registry", sa.String(length=500), nullable=False, server_default=""),
            sa.Column("path", sa.String(length=500), nullable=False, server_default=""),
            sa.Column("content_hash", sa.String(length=80), nullable=False, server_default=""),
            sa.Column("kind", sa.String(length=80), nullable=False, server_default=""),
            sa.Column("bytes", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("mtime", sa.String(length=80), nullable=False, server_default=""),
            sa.Column("params_hash", sa.String(length=80), nullable=False, server_default=""),
            sa.Column("parse_ok", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("pattern_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("params_json", json_type, nullable=False),
            sa.Column("patterns_json", json_type, nullable=False),
            sa.Column("payload_json", json_type, nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )

    if not _has_table("research_director_artifacts"):
        op.create_table(
            "research_director_artifacts",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("run_id", sa.String(length=80), nullable=False, server_default=""),
            sa.Column("kind", sa.String(length=80), nullable=False, server_default=""),
            sa.Column("path", sa.String(length=500), nullable=False, server_default=""),
            sa.Column("content_hash", sa.String(length=80), nullable=False, server_default=""),
            sa.Column("payload_json", json_type, nullable=False),
            sa.Column("content_text", sa.Text(), nullable=False, server_default=""),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )

    for table, indexes in {
        "research_experiment_registry_experiments": [
            ("ix_research_registry_experiments_experiment_id", ["experiment_id"], True),
            ("ix_research_registry_experiments_family", ["family_id"], False),
            ("ix_research_registry_experiments_pattern", ["pattern_key"], False),
            ("ix_research_registry_experiments_latest_run", ["latest_run_id"], False),
            ("ix_research_registry_experiments_side_timeframe", ["side", "timeframe"], False),
        ],
        "research_experiment_registry_runs": [
            ("ix_research_registry_runs_run_id", ["run_id"], True),
            ("ix_research_registry_runs_registered_at", ["registered_at"], False),
            ("ix_research_registry_runs_run_manifest_hash", ["run_manifest_hash"], False),
            ("ix_research_registry_runs_registry_hash", ["registry_hash"], False),
        ],
        "research_experiment_registry_snapshots": [
            ("ix_research_registry_snapshots_registry_hash", ["registry_hash"], True),
            ("ix_research_registry_snapshots_created_at", ["created_at"], False),
            ("ix_research_registry_snapshots_run_manifest_hash", ["run_manifest_hash"], False),
        ],
        "research_artifact_retention": [
            ("ix_research_artifact_retention_source_registry", ["source_registry"], False),
            ("ix_research_artifact_retention_kind", ["kind"], False),
            ("ix_research_artifact_retention_params_hash", ["params_hash"], False),
            ("ix_research_artifact_retention_path", ["path"], False),
            ("ix_research_artifact_retention_content_hash", ["content_hash"], False),
            ("ix_research_artifact_retention_mtime", ["mtime"], False),
        ],
        "research_director_artifacts": [
            ("ix_research_director_artifacts_run_id", ["run_id"], False),
            ("ix_research_director_artifacts_kind", ["kind"], False),
            ("ix_research_director_artifacts_path", ["path"], False),
            ("ix_research_director_artifacts_content_hash", ["content_hash"], False),
        ],
    }.items():
        for index_name, columns, unique in indexes:
            _create_index_if_missing(index_name, table, columns, unique=unique)


def downgrade() -> None:
    raise NotImplementedError("Downgrades are blocked for Tradeo safety migrations")
