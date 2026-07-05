from __future__ import annotations

from tradeo.modules.daily_swing.gap_protocol import protocol_summary, signal_family_specs, validate_protocol_inert


def test_gap_protocol_blocks_ibkr() -> None:
    summary = protocol_summary()
    assert summary["guardrails"]["no_ibkr"] is True
    assert validate_protocol_inert()["ok"] is True


def test_gap_protocol_blocks_orders() -> None:
    guardrails = protocol_summary()["guardrails"]
    assert guardrails["no_order_surface"] is True
    assert guardrails["no_backtest"] is True


def test_gap_protocol_blocks_preview() -> None:
    guardrails = protocol_summary()["guardrails"]
    assert guardrails["no_preview_output"] is True
    assert guardrails["no_signal_output"] is True


def test_gap_protocol_same_day_does_not_use_close_for_open_signal() -> None:
    same_day = [spec for spec in signal_family_specs() if spec.family_id.endswith("SAME_DAY")]
    assert same_day
    for spec in same_day:
        assert spec.signal_known_at == "open_t"
        assert "close_t" not in spec.allowed_signal_inputs
        assert {"high_t", "low_t", "close_t"} <= set(spec.forbidden_signal_inputs)


def test_gap_protocol_next_day_uses_close_after_decision() -> None:
    next_day = [spec for spec in signal_family_specs() if spec.family_id.endswith("NEXT_DAY")]
    assert next_day
    for spec in next_day:
        assert spec.signal_known_at == "after_close_t"
        assert "close_t" in spec.allowed_signal_inputs
        assert spec.entry_model == "open_t_plus_1_with_adverse_slippage"


def test_gap_protocol_requires_stock_only() -> None:
    guardrails = protocol_summary()["guardrails"]
    assert guardrails["product_policy"] == "stock_only"
    assert guardrails["allowed_product_types"] == ("STK",)
    assert guardrails["benchmarks_only"] == ("SPY", "QQQ")


def test_gap_protocol_declares_no_paper_candidate() -> None:
    guardrails = protocol_summary()["guardrails"]
    assert guardrails["no_paper_candidate"] is True
    assert guardrails["no_live_candidate"] is True
    assert protocol_summary()["research_pass_blocked_until_backtest_task"] is True
