from __future__ import annotations

from tradeo.modules.intraday.execution import IntradayPaperExecutionService, IntradayPaperOrderRequest


def test_intraday_paper_execution_requires_director_and_flat_plan() -> None:
    result = IntradayPaperExecutionService().evaluate(
        IntradayPaperOrderRequest(
            symbol="SOUN",
            pattern_state="INTRADAY_LAB",
            director_approved=False,
            paper_enabled=True,
            has_flat_plan=False,
            expected_ev_r=0.2,
        )
    )

    assert result.allowed is False
    assert result.reason_codes == ("director_not_approved", "flat_plan_required")


def test_intraday_paper_execution_records_net_fill_metrics() -> None:
    result = IntradayPaperExecutionService().evaluate(
        IntradayPaperOrderRequest(
            symbol="SOUN",
            pattern_state="INTRADAY_PRODUCTION",
            director_approved=True,
            paper_enabled=True,
            has_flat_plan=True,
            expected_ev_r=0.2,
            expected_price=10.0,
            fill_price=10.05,
            commission=1.0,
            requested_qty=10,
            partial_fill_qty=5,
        )
    )

    assert result.allowed is True
    assert result.reason_codes == ()
    assert result.metrics["slippage_bps"] == 50.0
    assert result.metrics["fill_ratio"] == 0.5
    assert result.metrics["commission"] == 1.0
