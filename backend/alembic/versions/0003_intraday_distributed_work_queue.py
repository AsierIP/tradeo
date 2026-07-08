"""Add intraday distributed Research/Lab work queue tables.

Revision ID: 0003_intraday_work_queue
Revises: 0002_intraday_sessions
Create Date: 2026-06-27
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

revision = "0003_intraday_work_queue"
down_revision = "0002_intraday_sessions"
branch_labels = None
depends_on = None


def _json_type() -> sa.types.TypeEngine:
    return postgresql.JSONB().with_variant(sa.JSON(), "sqlite")


def _has_table(table_name: str) -> bool:
    return inspect(op.get_bind()).has_table(table_name)


def upgrade() -> None:
    json_type = _json_type()

    if not _has_table("intraday_work_items"):
        op.create_table(
            "intraday_work_items",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("scope", sa.String(length=24), nullable=False),
            sa.Column("lane", sa.String(length=48), nullable=False),
            sa.Column("symbol", sa.String(length=24), nullable=False),
            sa.Column("session_id", sa.String(length=40), nullable=False),
            sa.Column("timeframe", sa.String(length=16), nullable=False),
            sa.Column("pattern_key", sa.String(length=160), nullable=False),
            sa.Column("entry_variant_id", sa.String(length=120), nullable=False),
            sa.Column("window_start", sa.String(length=80), nullable=False),
            sa.Column("window_end", sa.String(length=80), nullable=False),
            sa.Column("work_fingerprint", sa.String(length=80), nullable=False),
            sa.Column("data_manifest_hash", sa.String(length=80), nullable=False),
            sa.Column("params_hash", sa.String(length=80), nullable=False),
            sa.Column("split_id", sa.String(length=80), nullable=False),
            sa.Column("priority", sa.Float(), nullable=False),
            sa.Column("status", sa.String(length=40), nullable=False),
            sa.Column("lease_owner", sa.String(length=120), nullable=False),
            sa.Column("lease_until", sa.DateTime(timezone=True), nullable=True),
            sa.Column("attempt_count", sa.Integer(), nullable=False),
            sa.Column("max_attempts", sa.Integer(), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("payload_json", json_type, nullable=False),
            sa.Column("result_json", json_type, nullable=False),
            sa.Column("reason_codes_json", json_type, nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("work_fingerprint", name="uq_intraday_work_items_fingerprint"),
        )
        op.create_index("ix_intraday_work_items_id", "intraday_work_items", ["id"])
        op.create_index("ix_intraday_work_items_scope", "intraday_work_items", ["scope"])
        op.create_index("ix_intraday_work_items_lane", "intraday_work_items", ["lane"])
        op.create_index("ix_intraday_work_items_symbol", "intraday_work_items", ["symbol"])
        op.create_index("ix_intraday_work_items_session_id", "intraday_work_items", ["session_id"])
        op.create_index("ix_intraday_work_items_timeframe", "intraday_work_items", ["timeframe"])
        op.create_index("ix_intraday_work_items_pattern_key", "intraday_work_items", ["pattern_key"])
        op.create_index("ix_intraday_work_items_window_end", "intraday_work_items", ["window_end"])
        op.create_index("ix_intraday_work_items_work_fingerprint", "intraday_work_items", ["work_fingerprint"], unique=True)
        op.create_index("ix_intraday_work_items_priority", "intraday_work_items", ["priority"])
        op.create_index("ix_intraday_work_items_status", "intraday_work_items", ["status"])
        op.create_index("ix_intraday_work_items_lease_owner", "intraday_work_items", ["lease_owner"])
        op.create_index("ix_intraday_work_items_lease_until", "intraday_work_items", ["lease_until"])
        op.create_index("ix_intraday_work_items_expires_at", "intraday_work_items", ["expires_at"])
        op.create_index("ix_intraday_work_items_created_at", "intraday_work_items", ["created_at"])
        op.create_index(
            "ix_intraday_work_items_scope_status_priority",
            "intraday_work_items",
            ["scope", "status", "priority"],
        )
        op.create_index("ix_intraday_work_items_lane_status", "intraday_work_items", ["lane", "status"])
        op.create_index(
            "ix_intraday_work_items_session_symbol_status",
            "intraday_work_items",
            ["session_id", "symbol", "status"],
        )

    if not _has_table("intraday_worker_heartbeats"):
        op.create_table(
            "intraday_worker_heartbeats",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("worker_id", sa.String(length=120), nullable=False),
            sa.Column("scope", sa.String(length=24), nullable=False),
            sa.Column("lane", sa.String(length=48), nullable=False),
            sa.Column("status", sa.String(length=40), nullable=False),
            sa.Column("capacity", sa.Integer(), nullable=False),
            sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("metadata_json", json_type, nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_intraday_worker_heartbeats_id", "intraday_worker_heartbeats", ["id"])
        op.create_index("ix_intraday_worker_heartbeats_worker_id", "intraday_worker_heartbeats", ["worker_id"], unique=True)
        op.create_index("ix_intraday_worker_heartbeats_scope", "intraday_worker_heartbeats", ["scope"])
        op.create_index("ix_intraday_worker_heartbeats_lane", "intraday_worker_heartbeats", ["lane"])
        op.create_index("ix_intraday_worker_heartbeats_status", "intraday_worker_heartbeats", ["status"])
        op.create_index("ix_intraday_worker_heartbeats_last_seen_at", "intraday_worker_heartbeats", ["last_seen_at"])
        op.create_index("ix_intraday_worker_heartbeats_last_seen", "intraday_worker_heartbeats", ["last_seen_at"])
        op.create_index(
            "ix_intraday_worker_heartbeats_scope_lane_status",
            "intraday_worker_heartbeats",
            ["scope", "lane", "status"],
        )


def downgrade() -> None:
    raise NotImplementedError("Downgrades are blocked for Tradeo safety migrations")
