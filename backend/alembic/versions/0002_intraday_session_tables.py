"""Add intraday session state tables and signal dedupe index.

Revision ID: 0002_intraday_sessions
Revises: 0001_baseline
Create Date: 2026-06-22
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

revision = "0002_intraday_sessions"
down_revision = "0001_baseline"
branch_labels = None
depends_on = None


def _json_type() -> sa.types.TypeEngine:
    return postgresql.JSONB().with_variant(sa.JSON(), "sqlite")


def _has_table(table_name: str) -> bool:
    return inspect(op.get_bind()).has_table(table_name)


def _create_signal_intraday_dedupe_index() -> None:
    dialect = op.get_bind().dialect.name
    if dialect == "postgresql":
        op.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS uq_signals_intraday_dedupe_pg
            ON signals (
                symbol,
                pattern,
                timeframe,
                COALESCE(
                    metadata_json -> 'intraday' ->> 'entry_variant',
                    metadata_json -> 'intraday' ->> 'entry_variant_id'
                ),
                metadata_json -> 'intraday' ->> 'window_end',
                metadata_json -> 'intraday' ->> 'session_id'
            )
            WHERE metadata_json ? 'intraday'
              AND metadata_json -> 'intraday' ->> 'session_id' IS NOT NULL
              AND COALESCE(
                    metadata_json -> 'intraday' ->> 'entry_variant',
                    metadata_json -> 'intraday' ->> 'entry_variant_id'
                  ) IS NOT NULL
              AND metadata_json -> 'intraday' ->> 'window_end' IS NOT NULL
            """
        )
    elif dialect == "sqlite":
        op.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS uq_signals_intraday_dedupe_sqlite
            ON signals (
                symbol,
                pattern,
                timeframe,
                COALESCE(
                    json_extract(metadata_json, '$.intraday.entry_variant'),
                    json_extract(metadata_json, '$.intraday.entry_variant_id')
                ),
                json_extract(metadata_json, '$.intraday.window_end'),
                json_extract(metadata_json, '$.intraday.session_id')
            )
            WHERE json_extract(metadata_json, '$.intraday.session_id') IS NOT NULL
              AND COALESCE(
                    json_extract(metadata_json, '$.intraday.entry_variant'),
                    json_extract(metadata_json, '$.intraday.entry_variant_id')
                  ) IS NOT NULL
              AND json_extract(metadata_json, '$.intraday.window_end') IS NOT NULL
            """
        )


def _drop_signal_intraday_dedupe_index() -> None:
    dialect = op.get_bind().dialect.name
    if dialect == "postgresql":
        op.execute("DROP INDEX IF EXISTS uq_signals_intraday_dedupe_pg")
    elif dialect == "sqlite":
        op.execute("DROP INDEX IF EXISTS uq_signals_intraday_dedupe_sqlite")


def upgrade() -> None:
    json_type = _json_type()

    if not _has_table("intraday_sessions"):
        op.create_table(
            "intraday_sessions",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("session_date", sa.Date(), nullable=False),
            sa.Column("market", sa.String(length=24), nullable=False),
            sa.Column("timezone", sa.String(length=64), nullable=False),
            sa.Column("regular_open_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("regular_close_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("is_half_day", sa.Boolean(), nullable=False),
            sa.Column("no_new_entries_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("cancel_entries_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("force_flat_start_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("hard_flat_deadline_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("state", sa.String(length=40), nullable=False),
            sa.Column("flat_status", sa.String(length=40), nullable=False),
            sa.Column("flat_confirmed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("flat_failed_reason", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("session_date", "market", name="uq_intraday_sessions_date_market"),
        )
        op.create_index("ix_intraday_sessions_session_date", "intraday_sessions", ["session_date"])
        op.create_index("ix_intraday_sessions_state", "intraday_sessions", ["state"])
        op.create_index("ix_intraday_sessions_flat_status", "intraday_sessions", ["flat_status"])
        op.create_index(
            "ix_intraday_sessions_session_date_state",
            "intraday_sessions",
            ["session_date", "state"],
        )
        op.create_index(
            "ix_intraday_sessions_session_date_flat_status",
            "intraday_sessions",
            ["session_date", "flat_status"],
        )

    if not _has_table("intraday_universe_snapshots"):
        op.create_table(
            "intraday_universe_snapshots",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("session_id", sa.Integer(), nullable=False),
            sa.Column("session_date", sa.Date(), nullable=False),
            sa.Column("bucket", sa.String(length=40), nullable=False),
            sa.Column("timeframe", sa.String(length=16), nullable=False),
            sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("symbols_json", json_type, nullable=False),
            sa.Column("filters_json", json_type, nullable=False),
            sa.Column("excluded_json", json_type, nullable=False),
            sa.Column("pacing_budget_json", json_type, nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["session_id"], ["intraday_sessions.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "session_id",
                "bucket",
                "timeframe",
                "generated_at",
                name="uq_intraday_universe_snapshot_version",
            ),
        )
        op.create_index(
            "ix_intraday_universe_snapshots_session_id",
            "intraday_universe_snapshots",
            ["session_id"],
        )
        op.create_index(
            "ix_intraday_universe_snapshots_session_date",
            "intraday_universe_snapshots",
            ["session_date"],
        )
        op.create_index(
            "ix_intraday_universe_snapshots_bucket",
            "intraday_universe_snapshots",
            ["bucket"],
        )
        op.create_index(
            "ix_intraday_universe_snapshots_timeframe",
            "intraday_universe_snapshots",
            ["timeframe"],
        )
        op.create_index(
            "ix_intraday_universe_snapshots_generated_at",
            "intraday_universe_snapshots",
            ["generated_at"],
        )
        op.create_index(
            "ix_intraday_universe_snapshots_session_date_bucket",
            "intraday_universe_snapshots",
            ["session_date", "bucket"],
        )

    if not _has_table("intraday_symbol_state"):
        op.create_table(
            "intraday_symbol_state",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("session_id", sa.Integer(), nullable=False),
            sa.Column("session_date", sa.Date(), nullable=False),
            sa.Column("symbol", sa.String(length=24), nullable=False),
            sa.Column("timeframe", sa.String(length=16), nullable=False),
            sa.Column("status", sa.String(length=40), nullable=False),
            sa.Column("trades_today", sa.Integer(), nullable=False),
            sa.Column("signals_today", sa.Integer(), nullable=False),
            sa.Column("open_position_qty", sa.Float(), nullable=False),
            sa.Column("cooldown_until", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_stop_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_signal_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("blocked_reason", sa.Text(), nullable=False),
            sa.Column("risk_used_usd", sa.Float(), nullable=False),
            sa.Column("realized_r", sa.Float(), nullable=False),
            sa.Column("unrealized_r", sa.Float(), nullable=False),
            sa.Column("metadata_json", json_type, nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["session_id"], ["intraday_sessions.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "session_id",
                "symbol",
                "timeframe",
                name="uq_intraday_symbol_state_symbol_timeframe",
            ),
        )
        op.create_index("ix_intraday_symbol_state_session_id", "intraday_symbol_state", ["session_id"])
        op.create_index("ix_intraday_symbol_state_session_date", "intraday_symbol_state", ["session_date"])
        op.create_index("ix_intraday_symbol_state_symbol", "intraday_symbol_state", ["symbol"])
        op.create_index("ix_intraday_symbol_state_timeframe", "intraday_symbol_state", ["timeframe"])
        op.create_index("ix_intraday_symbol_state_status", "intraday_symbol_state", ["status"])
        op.create_index(
            "ix_intraday_symbol_state_session_date_symbol",
            "intraday_symbol_state",
            ["session_date", "symbol"],
        )
        op.create_index(
            "ix_intraday_symbol_state_session_date_status",
            "intraday_symbol_state",
            ["session_date", "status"],
        )

    if not _has_table("intraday_pacing_ledger"):
        op.create_table(
            "intraday_pacing_ledger",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("session_id", sa.Integer(), nullable=True),
            sa.Column("session_date", sa.Date(), nullable=True),
            sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
            sa.Column("request_type", sa.String(length=60), nullable=False),
            sa.Column("symbol", sa.String(length=24), nullable=True),
            sa.Column("timeframe", sa.String(length=16), nullable=False),
            sa.Column("status", sa.String(length=40), nullable=False),
            sa.Column("allowed", sa.Boolean(), nullable=False),
            sa.Column("budget_remaining", sa.Integer(), nullable=False),
            sa.Column("blocked_reason", sa.Text(), nullable=False),
            sa.Column("ibkr_error_code", sa.String(length=40), nullable=True),
            sa.Column("payload_json", json_type, nullable=False),
            sa.ForeignKeyConstraint(["session_id"], ["intraday_sessions.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_intraday_pacing_ledger_session_id", "intraday_pacing_ledger", ["session_id"])
        op.create_index("ix_intraday_pacing_ledger_session_date", "intraday_pacing_ledger", ["session_date"])
        op.create_index("ix_intraday_pacing_ledger_timestamp", "intraday_pacing_ledger", ["timestamp"])
        op.create_index("ix_intraday_pacing_ledger_request_type", "intraday_pacing_ledger", ["request_type"])
        op.create_index("ix_intraday_pacing_ledger_symbol", "intraday_pacing_ledger", ["symbol"])
        op.create_index("ix_intraday_pacing_ledger_timeframe", "intraday_pacing_ledger", ["timeframe"])
        op.create_index("ix_intraday_pacing_ledger_status", "intraday_pacing_ledger", ["status"])
        op.create_index("ix_intraday_pacing_ledger_allowed", "intraday_pacing_ledger", ["allowed"])
        op.create_index(
            "ix_intraday_pacing_ledger_ibkr_error_code",
            "intraday_pacing_ledger",
            ["ibkr_error_code"],
        )
        op.create_index(
            "ix_intraday_pacing_ledger_session_date_symbol",
            "intraday_pacing_ledger",
            ["session_date", "symbol"],
        )
        op.create_index(
            "ix_intraday_pacing_ledger_timeframe_status",
            "intraday_pacing_ledger",
            ["timeframe", "status"],
        )
        op.create_index(
            "ix_intraday_pacing_ledger_request_type_timestamp",
            "intraday_pacing_ledger",
            ["request_type", "timestamp"],
        )

    if not _has_table("intraday_risk_ledger"):
        op.create_table(
            "intraday_risk_ledger",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("session_id", sa.Integer(), nullable=False),
            sa.Column("session_date", sa.Date(), nullable=False),
            sa.Column("event_type", sa.String(length=60), nullable=False),
            sa.Column("symbol", sa.String(length=24), nullable=True),
            sa.Column("timeframe", sa.String(length=16), nullable=False),
            sa.Column("status", sa.String(length=40), nullable=False),
            sa.Column("scope", sa.String(length=20), nullable=False),
            sa.Column("source_signal_id", sa.Integer(), nullable=True),
            sa.Column("trade_id", sa.Integer(), nullable=True),
            sa.Column("delta_risk_usd", sa.Float(), nullable=False),
            sa.Column("daily_loss_used_usd", sa.Float(), nullable=False),
            sa.Column("payload_json", json_type, nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["session_id"], ["intraday_sessions.id"]),
            sa.ForeignKeyConstraint(["source_signal_id"], ["signals.id"]),
            sa.ForeignKeyConstraint(["trade_id"], ["trades.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_intraday_risk_ledger_session_id", "intraday_risk_ledger", ["session_id"])
        op.create_index("ix_intraday_risk_ledger_session_date", "intraday_risk_ledger", ["session_date"])
        op.create_index("ix_intraday_risk_ledger_event_type", "intraday_risk_ledger", ["event_type"])
        op.create_index("ix_intraday_risk_ledger_symbol", "intraday_risk_ledger", ["symbol"])
        op.create_index("ix_intraday_risk_ledger_timeframe", "intraday_risk_ledger", ["timeframe"])
        op.create_index("ix_intraday_risk_ledger_status", "intraday_risk_ledger", ["status"])
        op.create_index("ix_intraday_risk_ledger_scope", "intraday_risk_ledger", ["scope"])
        op.create_index("ix_intraday_risk_ledger_source_signal_id", "intraday_risk_ledger", ["source_signal_id"])
        op.create_index("ix_intraday_risk_ledger_trade_id", "intraday_risk_ledger", ["trade_id"])
        op.create_index("ix_intraday_risk_ledger_created_at", "intraday_risk_ledger", ["created_at"])
        op.create_index(
            "ix_intraday_risk_ledger_session_date_symbol",
            "intraday_risk_ledger",
            ["session_date", "symbol"],
        )
        op.create_index(
            "ix_intraday_risk_ledger_timeframe_status",
            "intraday_risk_ledger",
            ["timeframe", "status"],
        )

    if not _has_table("intraday_flatten_attempts"):
        op.create_table(
            "intraday_flatten_attempts",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("session_id", sa.Integer(), nullable=False),
            sa.Column("session_date", sa.Date(), nullable=False),
            sa.Column("trade_id", sa.Integer(), nullable=True),
            sa.Column("source_signal_id", sa.Integer(), nullable=True),
            sa.Column("symbol", sa.String(length=24), nullable=False),
            sa.Column("timeframe", sa.String(length=16), nullable=False),
            sa.Column("broker_position_qty_before", sa.Float(), nullable=False),
            sa.Column("db_position_qty_before", sa.Float(), nullable=False),
            sa.Column("action", sa.String(length=60), nullable=False),
            sa.Column("order_id", sa.String(length=120), nullable=True),
            sa.Column("perm_id", sa.String(length=120), nullable=True),
            sa.Column("side", sa.String(length=8), nullable=False),
            sa.Column("qty", sa.Float(), nullable=False),
            sa.Column("limit_price", sa.Float(), nullable=True),
            sa.Column("status", sa.String(length=40), nullable=False),
            sa.Column("broker_response_json", json_type, nullable=False),
            sa.Column("verified_position_qty_after", sa.Float(), nullable=True),
            sa.Column("reason_code", sa.String(length=80), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(["session_id"], ["intraday_sessions.id"]),
            sa.ForeignKeyConstraint(["trade_id"], ["trades.id"]),
            sa.ForeignKeyConstraint(["source_signal_id"], ["signals.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_intraday_flatten_attempts_session_id", "intraday_flatten_attempts", ["session_id"])
        op.create_index("ix_intraday_flatten_attempts_session_date", "intraday_flatten_attempts", ["session_date"])
        op.create_index("ix_intraday_flatten_attempts_trade_id", "intraday_flatten_attempts", ["trade_id"])
        op.create_index(
            "ix_intraday_flatten_attempts_source_signal_id",
            "intraday_flatten_attempts",
            ["source_signal_id"],
        )
        op.create_index("ix_intraday_flatten_attempts_symbol", "intraday_flatten_attempts", ["symbol"])
        op.create_index("ix_intraday_flatten_attempts_timeframe", "intraday_flatten_attempts", ["timeframe"])
        op.create_index("ix_intraday_flatten_attempts_action", "intraday_flatten_attempts", ["action"])
        op.create_index("ix_intraday_flatten_attempts_order_id", "intraday_flatten_attempts", ["order_id"])
        op.create_index("ix_intraday_flatten_attempts_perm_id", "intraday_flatten_attempts", ["perm_id"])
        op.create_index("ix_intraday_flatten_attempts_status", "intraday_flatten_attempts", ["status"])
        op.create_index("ix_intraday_flatten_attempts_reason_code", "intraday_flatten_attempts", ["reason_code"])
        op.create_index("ix_intraday_flatten_attempts_created_at", "intraday_flatten_attempts", ["created_at"])
        op.create_index(
            "ix_intraday_flatten_attempts_session_date_status",
            "intraday_flatten_attempts",
            ["session_date", "status"],
        )
        op.create_index(
            "ix_intraday_flatten_attempts_symbol_status",
            "intraday_flatten_attempts",
            ["symbol", "status"],
        )

    _create_signal_intraday_dedupe_index()


def downgrade() -> None:
    _drop_signal_intraday_dedupe_index()
    for table_name in (
        "intraday_flatten_attempts",
        "intraday_risk_ledger",
        "intraday_pacing_ledger",
        "intraday_symbol_state",
        "intraday_universe_snapshots",
        "intraday_sessions",
    ):
        if _has_table(table_name):
            op.drop_table(table_name)
