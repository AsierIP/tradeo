from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

DSS_GAP_001_SCHEMA_VERSION = "tradeo.daily_swing.dss_gap_001.protocol.v1"
PATTERN_ID = "DSS-GAP-001"
DECISION = "DSS_GAP_001_PROTOCOL_READY"

ProductPolicy = Literal["stock_only"]
SignalFamily = Literal[
    "GAP_CONTINUATION_SAME_DAY",
    "GAP_REVERSAL_SAME_DAY",
    "GAP_CONTINUATION_NEXT_DAY",
    "GAP_REVERSAL_NEXT_DAY",
]


@dataclass(frozen=True)
class GapProtocolGuardrails:
    blocks_execute: bool = True
    no_order_surface: bool = True
    no_ibkr: bool = True
    no_signal_output: bool = True
    no_preview_output: bool = True
    no_paper_candidate: bool = True
    no_live_candidate: bool = True
    no_backtest: bool = True
    product_policy: ProductPolicy = "stock_only"
    benchmarks_only: tuple[str, ...] = ("SPY", "QQQ")
    allowed_product_types: tuple[str, ...] = ("STK",)


@dataclass(frozen=True)
class GapSignalFamilySpec:
    family_id: SignalFamily
    signal_known_at: str
    allowed_signal_inputs: tuple[str, ...]
    forbidden_signal_inputs: tuple[str, ...]
    entry_model: str
    target_return: str


SAME_DAY_SIGNAL_INPUTS = (
    "close_t_minus_1",
    "open_t",
    "volume_history_t_minus_1",
    "atr14_pct_t_minus_1",
    "prior_return_5d_t_minus_1",
    "prior_return_20d_t_minus_1",
    "benchmark_return_20d_t_minus_1",
)
SAME_DAY_FORBIDDEN_INPUTS = ("high_t", "low_t", "close_t", "volume_t", "gap_fill_ratio_t")
NEXT_DAY_SIGNAL_INPUTS = (
    "close_t_minus_1",
    "open_t",
    "high_t",
    "low_t",
    "close_t",
    "volume_t",
    "atr14_pct_t_minus_1",
    "prior_return_5d_t_minus_1",
    "prior_return_20d_t_minus_1",
    "benchmark_return_20d_t_minus_1",
)


def guardrails() -> GapProtocolGuardrails:
    return GapProtocolGuardrails()


def signal_family_specs() -> tuple[GapSignalFamilySpec, ...]:
    return (
        GapSignalFamilySpec(
            family_id="GAP_CONTINUATION_SAME_DAY",
            signal_known_at="open_t",
            allowed_signal_inputs=SAME_DAY_SIGNAL_INPUTS,
            forbidden_signal_inputs=SAME_DAY_FORBIDDEN_INPUTS,
            entry_model="open_t_with_adverse_slippage",
            target_return="open_t_to_close_t_in_gap_direction",
        ),
        GapSignalFamilySpec(
            family_id="GAP_REVERSAL_SAME_DAY",
            signal_known_at="open_t",
            allowed_signal_inputs=SAME_DAY_SIGNAL_INPUTS,
            forbidden_signal_inputs=SAME_DAY_FORBIDDEN_INPUTS,
            entry_model="open_t_with_adverse_slippage",
            target_return="open_t_to_close_t_against_gap_direction",
        ),
        GapSignalFamilySpec(
            family_id="GAP_CONTINUATION_NEXT_DAY",
            signal_known_at="after_close_t",
            allowed_signal_inputs=NEXT_DAY_SIGNAL_INPUTS,
            forbidden_signal_inputs=(),
            entry_model="open_t_plus_1_with_adverse_slippage",
            target_return="post_close_t_continuation",
        ),
        GapSignalFamilySpec(
            family_id="GAP_REVERSAL_NEXT_DAY",
            signal_known_at="after_close_t",
            allowed_signal_inputs=NEXT_DAY_SIGNAL_INPUTS,
            forbidden_signal_inputs=(),
            entry_model="open_t_plus_1_with_adverse_slippage",
            target_return="post_close_t_reversal",
        ),
    )


def protocol_summary() -> dict[str, object]:
    guards = guardrails()
    return {
        "schema_version": DSS_GAP_001_SCHEMA_VERSION,
        "pattern_id": PATTERN_ID,
        "decision": DECISION,
        "hypothesis": "Daily overnight gaps may continue or reverse conditional on regime, gap size, direction, prior volatility, liquidity, and benchmark context.",
        "guardrails": guards.__dict__,
        "variables": [
            "gap_pct = open_t / close_t_minus_1 - 1",
            "abs_gap_pct",
            "gap_direction",
            "atr14_pct_t_minus_1",
            "gap_vs_atr",
            "prior_return_5d",
            "prior_return_20d",
            "benchmark_return_20d",
            "open_to_close_return",
            "next_open_to_close_return",
        ],
        "families": [spec.__dict__ for spec in signal_family_specs()],
        "research_pass_blocked_until_backtest_task": True,
    }


def validate_protocol_inert() -> dict[str, object]:
    guards = guardrails()
    failures: list[str] = []
    for name, value in guards.__dict__.items():
        if name in {"product_policy", "benchmarks_only", "allowed_product_types"}:
            continue
        if value is not True:
            failures.append(name)
    if guards.product_policy != "stock_only":
        failures.append("product_policy")
    if set(guards.allowed_product_types) != {"STK"}:
        failures.append("allowed_product_types")
    return {"ok": not failures, "failures": failures, "decision": DECISION}
