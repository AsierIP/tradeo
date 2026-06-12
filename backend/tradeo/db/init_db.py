from __future__ import annotations

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from tradeo.core.config import get_settings
from tradeo.db.models import EquityPoint, StrategyVersion
from tradeo.db.session import Base, engine
from tradeo.services.strategy_config import load_strategy_config


ALEMBIC_BASELINE_REVISION = "0001_baseline"


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    _migrate_trades_evidence_columns()
    _migrate_discovered_patterns()
    _stamp_alembic_baseline()


def _stamp_alembic_baseline() -> None:
    """Adopt the database into the Alembic migration tree (informe §6.1).

    ``create_all`` above already produced the baseline schema, so databases
    that have no Alembic version yet are stamped at the baseline revision.
    Databases already past the baseline are left untouched — from then on
    ``alembic upgrade head`` is the canonical migration path.
    """
    with engine.begin() as conn:
        conn.execute(
            text(
                "CREATE TABLE IF NOT EXISTS alembic_version ("
                "version_num VARCHAR(32) NOT NULL, "
                "CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num))"
            )
        )
        existing = conn.execute(text("SELECT version_num FROM alembic_version")).fetchall()
        if not existing:
            conn.execute(
                text("INSERT INTO alembic_version (version_num) VALUES (:rev)"),
                {"rev": ALEMBIC_BASELINE_REVISION},
            )


def _migrate_trades_evidence_columns() -> None:
    inspector = inspect(engine)
    if "trades" not in inspector.get_table_names():
        return
    existing = {col["name"] for col in inspector.get_columns("trades")}
    columns = {
        "evidence_type": "VARCHAR(40)",
        "evidence_quality": "VARCHAR(40)",
    }
    with engine.begin() as conn:
        for name, ddl in columns.items():
            if name not in existing:
                conn.execute(text(f"ALTER TABLE trades ADD COLUMN {name} {ddl}"))
        if engine.dialect.name == "postgresql":
            conn.execute(
                text(
                    "UPDATE trades "
                    "SET evidence_type = NULLIF(metadata_json ->> 'evidence_type', '') "
                    "WHERE evidence_type IS NULL "
                    "AND NULLIF(metadata_json ->> 'evidence_type', '') IS NOT NULL"
                )
            )
            conn.execute(
                text(
                    "UPDATE trades "
                    "SET evidence_quality = NULLIF(metadata_json ->> 'evidence_quality', '') "
                    "WHERE evidence_quality IS NULL "
                    "AND NULLIF(metadata_json ->> 'evidence_quality', '') IS NOT NULL"
                )
            )
        else:
            conn.execute(
                text(
                    "UPDATE trades "
                    "SET evidence_type = NULLIF(json_extract(metadata_json, '$.evidence_type'), '') "
                    "WHERE evidence_type IS NULL "
                    "AND NULLIF(json_extract(metadata_json, '$.evidence_type'), '') IS NOT NULL"
                )
            )
            conn.execute(
                text(
                    "UPDATE trades "
                    "SET evidence_quality = NULLIF(json_extract(metadata_json, '$.evidence_quality'), '') "
                    "WHERE evidence_quality IS NULL "
                    "AND NULLIF(json_extract(metadata_json, '$.evidence_quality'), '') IS NOT NULL"
                )
            )


def _migrate_discovered_patterns() -> None:
    inspector = inspect(engine)
    if "discovered_patterns" not in inspector.get_table_names():
        return
    if engine.dialect.name == "postgresql":
        enum_values = [
            "LAB_WATCHLIST",
            "LAB_CANDIDATE",
            "NEEDS_CONFIRMATION",
            "CONFIRMED_CANDIDATE",
            "FAILED_CONFIRMATION",
            "DIRECTOR_REVIEW",
            "PREMIUM_CANDIDATE",
            "PAPER_CANDIDATE",
            "PRODUCTION",
        ]
        with engine.begin() as conn:
            for value in enum_values:
                conn.execute(
                    text(
                        "DO $$ BEGIN "
                        f"ALTER TYPE discoveredpatternstatus ADD VALUE IF NOT EXISTS '{value}'; "
                        "EXCEPTION WHEN undefined_object THEN NULL; END $$;"
                    )
                )
    existing = {col["name"] for col in inspector.get_columns("discovered_patterns")}
    json_type_name = "JSONB" if engine.dialect.name == "postgresql" else "JSON"
    columns = {
        "best_rr": "DOUBLE PRECISION DEFAULT 0",
        "best_tested_rr": "DOUBLE PRECISION DEFAULT 0",
        "best_expectancy_r": "DOUBLE PRECISION DEFAULT 0",
        "best_profit_factor": "DOUBLE PRECISION DEFAULT 0",
        "best_win_rate": "DOUBLE PRECISION DEFAULT 0",
        "best_max_drawdown_r": "DOUBLE PRECISION DEFAULT 0",
        "pattern_family_key": "VARCHAR(160) DEFAULT ''",
        "canonical_pattern_key": "VARCHAR(160) DEFAULT ''",
        "variant_key": "VARCHAR(160) DEFAULT ''",
        "variant_count": "INTEGER DEFAULT 1",
        "drift_status": "VARCHAR(40) DEFAULT 'stable'",
        "drift_score": "DOUBLE PRECISION DEFAULT 0",
        "preferred_rr_passed": "BOOLEAN DEFAULT FALSE",
        "premium_rr_passed": "BOOLEAN DEFAULT FALSE",
        "promotion_status": "VARCHAR(40) DEFAULT 'rejected'",
        "promotion_reason": "TEXT DEFAULT ''",
        "confirmation_status": "VARCHAR(40) DEFAULT ''",
        "confirmation_priority_score": "DOUBLE PRECISION DEFAULT 0",
        "confirmation_reason": "TEXT DEFAULT ''",
        "confirmation_next_action": "TEXT DEFAULT ''",
        "confirmation_attempts": "INTEGER DEFAULT 0",
        "rr_metrics_json": f"{json_type_name} DEFAULT " + ("'{}'::jsonb" if engine.dialect.name == "postgresql" else "'{}'"),
        "rejection_reasons_json": f"{json_type_name} DEFAULT " + ("'[]'::jsonb" if engine.dialect.name == "postgresql" else "'[]'"),
        "in_sample_expectancy_r": "DOUBLE PRECISION DEFAULT 0",
        "in_sample_profit_factor": "DOUBLE PRECISION DEFAULT 0",
        "out_of_sample_win_rate": "DOUBLE PRECISION DEFAULT 0",
        "out_of_sample_max_drawdown_r": "DOUBLE PRECISION DEFAULT 0",
    }
    with engine.begin() as conn:
        for name, ddl in columns.items():
            if name not in existing:
                conn.execute(text(f"ALTER TABLE discovered_patterns ADD COLUMN {name} {ddl}"))


def seed_db(db: Session) -> None:
    settings = get_settings()
    if db.query(EquityPoint).count() == 0:
        db.add(EquityPoint(equity=settings.initial_capital_usd, cash=settings.initial_capital_usd))
    if db.query(StrategyVersion).filter(StrategyVersion.name == "cup_v0").count() == 0:
        params = load_strategy_config(settings.strategy_config_file)
        db.add(StrategyVersion(name="cup_v0", state="paper", params_json=params))
    db.commit()
