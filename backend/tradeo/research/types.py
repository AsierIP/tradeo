from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

import numpy as np

Side = Literal["long", "short"]


@dataclass(slots=True)
class ForwardOutcome:
    """Forward path statistics measured in R units.

    R is calculated with a technical risk proxy at the end of the input window.
    For discovery we do not know the final execution stop yet, so this proxy is
    intentionally conservative and consistent across every window.
    """

    forward_returns: dict[int, float]
    entry_price: float
    risk_proxy: float
    forward_end: str
    long_mfe_r: float
    long_mae_r: float
    long_outcome_r: float
    long_hit_4r: bool
    short_mfe_r: float
    short_mae_r: float
    short_outcome_r: float
    short_hit_4r: bool
    forward_highs: list[float] = field(default_factory=list)
    forward_lows: list[float] = field(default_factory=list)
    forward_closes: list[float] = field(default_factory=list)
    execution_cost_r: float = 0.0
    long_label: str = "timeout"
    short_label: str = "timeout"
    long_time_to_target: int | None = None
    long_time_to_stop: int | None = None
    short_time_to_target: int | None = None
    short_time_to_stop: int | None = None
    long_mfe_before_mae: bool = False
    short_mfe_before_mae: bool = False
    long_gap_adverse_r: float = 0.0
    short_gap_adverse_r: float = 0.0
    long_strong_close_without_target: bool = False
    short_strong_close_without_target: bool = False
    long_speed_label: str = "unknown"
    short_speed_label: str = "unknown"
    execution: dict[str, float] = field(default_factory=dict)

    def outcome_for(self, side: Side) -> float:
        return self.long_outcome_r if side == "long" else self.short_outcome_r

    def mfe_for(self, side: Side) -> float:
        return self.long_mfe_r if side == "long" else self.short_mfe_r

    def mae_for(self, side: Side) -> float:
        return self.long_mae_r if side == "long" else self.short_mae_r

    def hit_4r_for(self, side: Side) -> bool:
        return self.long_hit_4r if side == "long" else self.short_hit_4r

    def label_for(self, side: Side) -> str:
        return self.long_label if side == "long" else self.short_label

    def time_to_target_for(self, side: Side) -> int | None:
        return self.long_time_to_target if side == "long" else self.short_time_to_target

    def time_to_stop_for(self, side: Side) -> int | None:
        return self.long_time_to_stop if side == "long" else self.short_time_to_stop

    def speed_label_for(self, side: Side) -> str:
        return self.long_speed_label if side == "long" else self.short_speed_label


@dataclass(slots=True)
class WindowSample:
    symbol: str
    timeframe: str
    window_size: int
    start: str
    end: str
    year: int
    vector: np.ndarray
    outcome: ForwardOutcome
    chart: dict[str, Any]
    features: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ClusterCandidate:
    pattern_key: str
    name: str
    side: Side
    timeframe: str
    window_size: int
    cluster_id: int
    centroid: list[float]
    sample_count: int
    symbol_count: int
    year_count: int
    score: float
    validation_passed: bool
    validation_reasons: list[str]
    metrics: dict[str, Any]
    feature_summary: dict[str, Any]
    examples: list[dict[str, Any]]


def freeze_json(value: Any) -> Any:
    """Return a tuple-only representation for immutable research packages."""
    if isinstance(value, dict):
        return tuple((str(key), freeze_json(value[key])) for key in sorted(value, key=str))
    if isinstance(value, list | tuple):
        return tuple(freeze_json(item) for item in value)
    if isinstance(value, np.generic):
        return value.item()
    return value


def thaw_json(value: Any) -> Any:
    if isinstance(value, tuple):
        if all(isinstance(item, tuple) and len(item) == 2 and isinstance(item[0], str) for item in value):
            return {key: thaw_json(child) for key, child in value}
        return [thaw_json(item) for item in value]
    return value


@dataclass(frozen=True, slots=True)
class HypothesisPackage:
    """Immutable research handoff for a candidate hypothesis.

    The package deliberately keeps `edge_claim` at NO_DEMOSTRADO. Any later
    paper/live promotion must be backed by separate Director evidence.
    """

    version: str
    pattern_key: str
    family_id: str
    variant_id: str
    edge_claim: Literal["NO_DEMOSTRADO"]
    falsifiable: bool
    thesis: str
    rule: str
    causal_mechanism: str
    works_when: tuple[str, ...]
    fails_when: tuple[str, ...]
    kill_conditions: tuple[str, ...]
    selection_split: Any
    fit_scope: Any
    train_metrics: Any
    out_of_sample_metrics: Any
    walk_forward_metrics: Any
    global_trial_count: int
    event_ledger_hash: str
    nested_discovery_replay: Any
    evidence_accumulated: Any
    falsification_tests: tuple[str, ...]
    current_verdict: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "pattern_key": self.pattern_key,
            "family_id": self.family_id,
            "variant_id": self.variant_id,
            "edge_claim": self.edge_claim,
            "falsifiable": self.falsifiable,
            "thesis": self.thesis,
            "rule": self.rule,
            "causal_mechanism": self.causal_mechanism,
            "works_when": list(self.works_when),
            "fails_when": list(self.fails_when),
            "kill_conditions": list(self.kill_conditions),
            "kill_criteria": list(self.kill_conditions),
            "selection_split": thaw_json(self.selection_split),
            "fit_scope": thaw_json(self.fit_scope),
            "train_metrics": thaw_json(self.train_metrics),
            "out_of_sample_metrics": thaw_json(self.out_of_sample_metrics),
            "walk_forward_metrics": thaw_json(self.walk_forward_metrics),
            "global_trial_count": self.global_trial_count,
            "event_ledger_hash": self.event_ledger_hash,
            "nested_discovery_replay": thaw_json(self.nested_discovery_replay),
            "evidence_accumulated": thaw_json(self.evidence_accumulated),
            "falsification_tests": list(self.falsification_tests),
            "current_verdict": self.current_verdict,
        }
