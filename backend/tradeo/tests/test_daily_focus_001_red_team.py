from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
import json
import subprocess

import pandas as pd
import pytest

from tradeo.core.config import Settings
from tradeo.modules.daily_swing.research_bucket_matrix import (
    BUCKETS,
    GLOBAL_APPROVED_SUMMARY_ONLY,
    GLOBAL_DENIED_FOR_BUCKET_TEST,
    ROW_SCOPE_BUCKET_TEST,
    ROW_SCOPE_SUMMARY_ONLY,
    SUMMARY_BUCKET,
    ResearchBucketMatrixError,
    default_research_bucket_matrix,
    validate_research_bucket_matrix,
)
from tradeo.modules.daily_swing.setup_watchlist import DailySetupWatchlist, SetupEvaluation
from tradeo.modules.resource_policy.enforcement import (
    DENY_INTRADAY_FROZEN_DAILY_FOCUS,
    assert_job_allowed,
    blocked_job_status,
)
from tradeo.modules.resource_policy.market_session_resource_policy import (
    JobType,
    MarketSessionResourcePolicy,
    SessionState,
)
from tradeo.services.intraday_universe_builder import (
    IntradayUniverseBuilder,
    IntradayUniverseThresholds,
)

REPO_ROOT = Path(__file__).resolve().parents[3]


class FakeProvider:
    def __init__(self, frames: dict[str, pd.DataFrame]) -> None:
        self.frames = frames

    def fetch_ohlcv(self, symbol: str, period: str = "2y", interval: str = "1d") -> pd.DataFrame:
        return self.frames[symbol].copy()


def _daily_policy(tmp_path: Path) -> MarketSessionResourcePolicy:
    return MarketSessionResourcePolicy(
        settings=Settings(artifacts_dir=str(tmp_path), focus_mode="daily_only"),
        forced_session_state=SessionState.MARKET_CLOSED,
    )


def _frame(price: float, volume: float, *, rows: int = 160) -> pd.DataFrame:
    index = pd.date_range("2026-01-01", periods=rows, freq="30min", tz="UTC")
    close = pd.Series([price * (1.0 + (idx % 5) * 0.0001) for idx in range(rows)], index=index)
    return pd.DataFrame(
        {
            "open": close * 0.999,
            "high": close * 1.003,
            "low": close * 0.997,
            "close": close,
            "volume": volume,
        },
        index=index,
    )


def test_daily_focus_freezes_intraday_heavy_lab_paper_and_submit_paths(
    tmp_path: Path,
) -> None:
    policy = _daily_policy(tmp_path)

    frozen_jobs = (
        JobType.RESEARCH_HEAVY,
        JobType.HEAVY_BACKTEST,
        JobType.LARGE_SCANNER,
        JobType.LAB_PAPER_PROBE,
        JobType.INTRADAY_LAB,
        JobType.INTRADAY_SHADOW,
        JobType.INTRADAY_CAPACITY,
        JobType.PAPER_SUBMIT,
    )
    for job_type in frozen_jobs:
        decision = assert_job_allowed(job_type, "red_team", policy=policy)
        assert decision.allowed is False
        assert decision.can_submit_orders is False
        assert decision.deny_reason == DENY_INTRADAY_FROZEN_DAILY_FOCUS
        assert blocked_job_status(decision)["reason"] == DENY_INTRADAY_FROZEN_DAILY_FOCUS

    report = policy.decide_job(JobType.INTRADAY_READ_ONLY_REPORT)
    assert report.allowed is True
    assert report.budget.focus_mode == "daily_only"
    assert report.budget.heavy_research_allowed is False
    assert report.budget.lab_paper_probe_allowed is False


def test_bucket_matrix_blocks_global_aggregate_rescue_and_missing_buckets() -> None:
    rows = default_research_bucket_matrix()
    validation = validate_research_bucket_matrix(rows)
    bucket_rows = [row for row in rows if row.row_scope == ROW_SCOPE_BUCKET_TEST]
    summary_rows = [row for row in rows if row.row_scope == ROW_SCOPE_SUMMARY_ONLY]

    assert validation.execution_surface_blocked is True
    assert len(summary_rows) == 1
    assert summary_rows[0].bucket == SUMMARY_BUCKET
    assert summary_rows[0].global_aggregate_allowed is True
    assert summary_rows[0].global_aggregate_approval == GLOBAL_APPROVED_SUMMARY_ONLY
    assert not any(row.global_aggregate_allowed for row in bucket_rows)
    assert {row.global_aggregate_approval for row in bucket_rows} == {
        GLOBAL_DENIED_FOR_BUCKET_TEST
    }

    with pytest.raises(ResearchBucketMatrixError, match="global aggregate"):
        validate_research_bucket_matrix(
            [replace(rows[0], global_aggregate_allowed=True), *rows[1:]]
        )

    missing_bucket = [row for row in rows if row.bucket != BUCKETS[0]]
    with pytest.raises(ResearchBucketMatrixError, match="missing buckets"):
        validate_research_bucket_matrix(missing_bucket)


def test_bucket_matrix_requires_exact_daily_universe_v2_buckets_and_families() -> None:
    rows = default_research_bucket_matrix()

    bucket_rows = [row for row in rows if row.row_scope == ROW_SCOPE_BUCKET_TEST]
    assert {row.bucket for row in bucket_rows} == set(BUCKETS)
    assert {row.family for row in bucket_rows} == {
        "pullback_in_trend",
        "gap_continuation_reversal_daily",
        "volatility_contraction_breakout",
        "relative_strength_sector_leadership",
    }
    assert any(row.variant == "W20" and row.exit_horizon == "3d" for row in bucket_rows)
    assert any(row.variant == "W50" and row.exit_horizon == "10d" for row in bucket_rows)
    assert any(row.variant == "W100" and row.exit_horizon == "20d" for row in bucket_rows)
    assert any(row.variant == "same_day_close" for row in bucket_rows)
    assert any(row.variant == "next_day_close" for row in bucket_rows)
    assert any(row.variant == "3_day_follow_through" for row in bucket_rows)
    assert any(row.variant == "5_day_follow_through" for row in bucket_rows)
    assert all(row.timeframe == "1d" for row in bucket_rows)


def test_entry_ready_focus_metadata_cannot_become_direct_order_or_foxhunter(
    tmp_path: Path,
) -> None:
    watchlist = DailySetupWatchlist(
        Settings(artifacts_dir=str(tmp_path), daily_setup_route_entry_ready_to_lab=True)
    )
    setup = watchlist.consider_setup(
        {
            "symbol": "TMDX",
            "side": "long",
            "pattern_id": 7,
            "pattern_key": "daily_gap_follow_through",
            "detected_at": "2026-07-01T21:00:00+00:00",
            "entry": 100.0,
            "stop": 95.0,
            "target": 120.0,
            "universe_bucket": "daily_focus_core",
            "bucket_reason": "post close daily focus universe",
            "bucket_version": "daily_focus_universe_v1",
            "pattern_family_key": "family_daily_gap_follow_through",
        },
        SetupEvaluation(entry_gate_passed=True, reward_risk=4.5, entry_score=0.9),
        now=datetime(2026, 7, 1, 21, 5, tzinfo=timezone.utc),
    )

    assert setup is not None
    record = setup.to_dict()
    request = setup.lab_paper_probe_request
    assert request is not None
    assert record["status"] == "entry_ready"
    assert record["lab_probe_allowed"] is True
    assert request["lab_probe_allowed"] is True
    assert request["submits_order"] is False
    assert request["allow_paper_on_entry_ready"] is False

    for payload in (record, request):
        assert payload["orders_allowed"] is False
        assert payload["paper_allowed"] is False
        assert payload["live_allowed"] is False
        assert payload["submit_order_called"] is False
        assert payload.get("candidate_approval", False) is False

    serialized = json.dumps(record, sort_keys=True).lower()
    assert "foxhunter" not in serialized
    assert "live_order_submitted" not in serialized
    assert "paper_order_submitted" not in serialized


def test_stock_only_universe_rejects_etf_and_thin_smallcap_with_reason(
    tmp_path: Path,
) -> None:
    seed = tmp_path / "seed.csv"
    seed.write_text(
        "symbol,name,cap_segment,sector,note,product_class,security_type\n"
        "ACME,Acme Software,smallcap,technology,common stock,common_stock,stock\n"
        "THIN,Thin Smallcap,smallcap,technology,common stock,common_stock,stock\n"
        "SPY,SPDR S&P 500 ETF,largecap,funds,index ETF,etf,etf\n",
        encoding="utf-8",
    )
    frames = {
        "ACME": _frame(25.0, 800_000),
        "THIN": _frame(25.0, 10_000),
        "SPY": _frame(500.0, 2_000_000),
    }
    builder = IntradayUniverseBuilder(
        settings=Settings(market_data_cache_dir=str(tmp_path / "cache")),
        provider_factory=lambda *, cache_refresh_enabled: FakeProvider(frames),
    )

    result = builder.build(
        seed_files=[seed],
        output_path=tmp_path / "universe.csv",
        limit=10,
        thresholds=IntradayUniverseThresholds(
            min_median_dollar_volume=10_000_000,
            min_rows=120,
        ),
        product_policy="stock_only",
        rotation_salt="red-team",
    )

    rows = pd.read_csv(result.output_path).set_index("symbol")
    assert result.selected_symbols == ["ACME"]
    assert rows.loc["SPY", "status"] == "rejected"
    assert rows.loc["SPY", "reason_codes"] == "product_policy:stock_only_excludes_etf"
    assert rows.loc["THIN", "status"] == "rejected"
    assert "dollar_volume_below_min" in rows.loc["THIN", "reason_codes"]
    assert bool(rows.loc["THIN", "selected"]) is False


def test_no_runtime_artifacts_are_tracked() -> None:
    if not (REPO_ROOT / ".git").exists():
        pytest.skip("git metadata unavailable")
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    tracked_runtime = [
        path
        for path in result.stdout.splitlines()
        if "/artifacts/runtime/" in f"/{path}" or path.startswith("artifacts/runtime/")
    ]
    assert tracked_runtime == []
