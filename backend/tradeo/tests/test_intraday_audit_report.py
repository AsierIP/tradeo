from __future__ import annotations

from tradeo.modules.intraday.reports import REASON_CODES, build_intraday_session_report


def test_intraday_session_report_summarizes_reasons_ev_and_flat() -> None:
    report = build_intraday_session_report(
        session_id="2026-06-22",
        mode="shadow",
        candidates=[
            {"expected_ev_r": 0.2, "reason_codes": []},
            {"expected_ev_r": -0.1, "reason_codes": ["spread_too_wide"]},
        ],
        trades=[
            {"pnl_usd": 12.34, "r_multiple": 0.4, "reason_codes": ["intraday_eod_flat"]},
            {"pnl_usd": -2.0, "r_multiple": -0.1, "reason_codes": []},
        ],
        flat_status="FLAT_CONFIRMED",
    )

    payload = report.to_dict()
    assert payload["candidates_total"] == 2
    assert payload["trades_total"] == 2
    assert payload["pnl_usd"] == 10.34
    assert payload["realized_ev_r"] == 0.3
    assert payload["expected_ev_r"] == 0.1
    assert payload["flat_compliant"] is True
    assert payload["reason_counts"]["spread_too_wide"] == 1


def test_intraday_reason_codes_cover_operational_failures() -> None:
    assert {"pacing_exhausted", "reduce_only_exit_failed", "hard_flat_deadline_unresolved"}.issubset(
        REASON_CODES
    )
