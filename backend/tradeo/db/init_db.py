from __future__ import annotations

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from tradeo.core.config import get_settings
from tradeo.db.models import EquityPoint, StrategyVersion
from tradeo.db.session import Base, engine
from tradeo.services.strategy_config import load_strategy_config


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    _migrate_discovered_patterns()


def _migrate_discovered_patterns() -> None:
    inspector = inspect(engine)
    if "discovered_patterns" not in inspector.get_table_names():
        return
    if engine.dialect.name == "postgresql":
        enum_values = ["LAB_WATCHLIST", "LAB_CANDIDATE", "PREMIUM_CANDIDATE", "PAPER_CANDIDATE"]
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
        "preferred_rr_passed": "BOOLEAN DEFAULT FALSE",
        "premium_rr_passed": "BOOLEAN DEFAULT FALSE",
        "promotion_status": "VARCHAR(40) DEFAULT 'rejected'",
        "promotion_reason": "TEXT DEFAULT ''",
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
