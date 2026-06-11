"""Entry-quality execution audit tests (informe §4.3 fallback path).

No real-time microstructure feed exists, so the auditable surface is the
broker fill record itself: fill price vs theoretical entry, submit->fill
latency and commissions. These tests pin down that arithmetic, the
shadow-fill exclusion, the idempotent persistence and the pattern-level
summary the Director gate stores as a diagnostic.
"""

from __future__ import annotations

from tradeo.db.models import Trade, TradeStatus
from tradeo.services.evidence import FillProvenance
from tradeo.services.execution_quality import (
    EXECUTION_QUALITY_METHOD,
    pattern_execution_quality_summary,
    persist_execution_quality,
    trade_execution_quality,
)


def make_trade(
    *,
    side: str = "long",
    entry: float = 10.0,
    stop: float = 9.0,
    qty: int = 5,
    metadata: dict | None = None,
) -> Trade:
    return Trade(
        id=1,
        symbol="AAPL",
        pattern="cup_handle",
        side=side,
        qty=qty,
        entry=entry,
        stop=stop,
        target=14.0,
        status=TradeStatus.CLOSED,
        metadata_json={
            "fill_provenance": FillProvenance.BROKER_EXECUTION.value,
            "entry_fill_price": 10.05,
            **(metadata or {}),
        },
    )


# ---------------------------------------------------------------------------
# Per-trade report arithmetic
# ---------------------------------------------------------------------------


def test_long_fill_above_theoretical_entry_is_positive_slippage() -> None:
    report = trade_execution_quality(make_trade())

    assert report is not None
    assert report["method"] == EXECUTION_QUALITY_METHOD
    # (10.05 - 10.00) / 10.00 * 10_000 = 50 bps worse than theoretical.
    assert report["entry_slippage_bps"] == 50.0
    # risk per share = 1.0 -> 0.05 R
    assert report["entry_slippage_r"] == 0.05


def test_short_fill_below_theoretical_entry_is_positive_slippage() -> None:
    trade = make_trade(side="short", stop=11.0, metadata={"entry_fill_price": 9.95})

    report = trade_execution_quality(trade)

    assert report is not None
    # Short filled lower than theoretical = worse entry -> positive slippage.
    assert report["entry_slippage_bps"] == 50.0
    assert report["entry_slippage_r"] == 0.05


def test_better_than_theoretical_fill_reports_negative_slippage() -> None:
    trade = make_trade(metadata={"entry_fill_price": 9.98})

    report = trade_execution_quality(trade)

    assert report is not None
    assert report["entry_slippage_bps"] == -20.0


def test_time_to_fill_from_submitted_at_and_fill_time() -> None:
    trade = make_trade(
        metadata={
            "submitted_at": "2026-06-01T15:00:00+00:00",
            "entry_fill_time": "2026-06-01T15:00:42+00:00",
        }
    )

    report = trade_execution_quality(trade)

    assert report is not None
    assert report["time_to_fill_s"] == 42.0


def test_time_to_fill_falls_back_to_broker_execution_time() -> None:
    trade = make_trade(
        metadata={
            "submitted_at": "2026-06-01T15:00:00+00:00",
            "broker_execution_time": "2026-06-01T15:01:00+00:00",
        }
    )

    report = trade_execution_quality(trade)

    assert report is not None
    assert report["time_to_fill_s"] == 60.0


def test_negative_fill_latency_is_rejected_not_reported() -> None:
    trade = make_trade(
        metadata={
            "submitted_at": "2026-06-01T15:01:00+00:00",
            "entry_fill_time": "2026-06-01T15:00:00+00:00",
        }
    )

    report = trade_execution_quality(trade)

    assert report is not None
    assert report["time_to_fill_s"] is None


def test_commission_bps_relative_to_fill_notional() -> None:
    trade = make_trade(metadata={"commission": 1.005})

    report = trade_execution_quality(trade)

    assert report is not None
    assert report["commission_usd"] == 1.005
    # notional = 10.05 * 5 = 50.25 -> 1.005 / 50.25 = 2% = 200 bps
    assert report["commission_bps"] == 200.0


def test_estimated_vs_realized_compares_pretrade_estimates() -> None:
    trade = make_trade(
        metadata={"estimated_slippage": 0.02, "estimated_spread_cost": 0.01}
    )

    report = trade_execution_quality(trade)

    assert report is not None
    comparison = report["estimated_vs_realized"]
    assert comparison is not None
    assert comparison["realized_entry_shortfall_per_share_usd"] == 0.05
    assert comparison["estimate_error_per_share_usd"] == 0.02


def test_data_basis_markers_declare_missing_microstructure_feed() -> None:
    report = trade_execution_quality(make_trade())

    assert report is not None
    assert report["data_basis"] == "broker_fill_record_eod_daily"
    assert report["microstructure_feed"] == "none_available"


# ---------------------------------------------------------------------------
# Exclusions: shadow fills and unusable inputs never produce a report
# ---------------------------------------------------------------------------


def test_shadow_fill_provenance_is_excluded() -> None:
    for provenance in (
        FillProvenance.SIMULATED_CLOSE.value,
        FillProvenance.SHADOW_CLOSE.value,
        "",
    ):
        trade = make_trade(metadata={"fill_provenance": provenance})
        assert trade_execution_quality(trade) is None


def test_missing_or_nonpositive_entry_fill_price_is_excluded() -> None:
    assert trade_execution_quality(make_trade(metadata={"entry_fill_price": None})) is None
    assert trade_execution_quality(make_trade(metadata={"entry_fill_price": 0.0})) is None
    assert trade_execution_quality(make_trade(metadata={"entry_fill_price": "n/a"})) is None


def test_zero_risk_reports_bps_but_not_r() -> None:
    trade = make_trade(stop=10.0)

    report = trade_execution_quality(trade)

    assert report is not None
    assert report["entry_slippage_bps"] == 50.0
    assert report["entry_slippage_r"] is None


# ---------------------------------------------------------------------------
# Persistence: idempotent metadata writes
# ---------------------------------------------------------------------------


def test_persist_execution_quality_writes_metadata_once() -> None:
    trade = make_trade()

    first = persist_execution_quality([trade])
    record = trade.metadata_json["execution_quality"]
    second = persist_execution_quality([trade])

    assert first == 1
    assert second == 0
    assert trade.metadata_json["execution_quality"] == record
    assert record["method"] == EXECUTION_QUALITY_METHOD
    assert "computed_at" in record


def test_persist_execution_quality_skips_shadow_trades() -> None:
    trade = make_trade(metadata={"fill_provenance": FillProvenance.SHADOW_CLOSE.value})

    touched = persist_execution_quality([trade])

    assert touched == 0
    assert "execution_quality" not in trade.metadata_json


def test_persist_execution_quality_rewrites_when_fill_data_changes() -> None:
    trade = make_trade()
    persist_execution_quality([trade])

    trade.metadata_json = {**trade.metadata_json, "entry_fill_price": 10.10}
    touched = persist_execution_quality([trade])

    assert touched == 1
    assert trade.metadata_json["execution_quality"]["entry_fill_price"] == 10.1


# ---------------------------------------------------------------------------
# Pattern-level summary
# ---------------------------------------------------------------------------


def test_pattern_summary_aggregates_real_fills_only() -> None:
    real_a = make_trade()
    real_b = make_trade(metadata={"entry_fill_price": 10.15})
    shadow = make_trade(metadata={"fill_provenance": FillProvenance.SHADOW_CLOSE.value})

    summary = pattern_execution_quality_summary([real_a, shadow, real_b])

    assert summary["count"] == 2
    assert summary["median_entry_slippage_bps"] == 100.0
    assert summary["worst_entry_slippage_bps"] == 150.0
    assert summary["microstructure_feed"] == "none_available"
    assert len(summary["per_trade"]) == 2


def test_pattern_summary_empty_when_no_real_fills() -> None:
    shadow = make_trade(metadata={"fill_provenance": FillProvenance.SHADOW_CLOSE.value})

    summary = pattern_execution_quality_summary([shadow])

    assert summary["count"] == 0
    assert summary["median_entry_slippage_bps"] is None
    assert summary["per_trade"] == []
