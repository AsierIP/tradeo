from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass, field, replace
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Literal, Mapping
import hashlib
import json
import math

SCHEMA_VERSION = "tradeo.daily_swing.setup_watchlist.v1"
EVALUATION_SCHEMA_VERSION = "tradeo.daily_swing.setup_watchlist_evaluation.v1"
ARTIFACT_SCHEMA_VERSION = "tradeo.daily_swing.setup_watchlist_artifact.v1"
DAILY_SETUP_ARTIFACT_SCHEMA_VERSION = "tradeo.daily_swing.setup_watchlist.status.v1"
LAB_PAPER_PROBE_REQUEST_SCHEMA_VERSION = "tradeo.daily_swing.lab_paper_probe_request.v1"

WatchlistState = Literal[
    "watchlist",
    "entry_ready",
    "cooldown",
    "blocked",
    "expired",
    "rejected",
]
Side = Literal["long", "short"]
DailySetupStatus = Literal[
    "detected",
    "watching",
    "waiting_for_confirmation",
    "armed",
    "entry_ready",
    "expired",
    "invalidated",
]

WATCHLIST_STATES = frozenset(
    {
        "watchlist",
        "entry_ready",
        "cooldown",
        "blocked",
        "expired",
        "rejected",
    }
)
TERMINAL_STATES = frozenset({"blocked", "expired", "rejected"})
FORBIDDEN_CLASSIC_CANDIDATES = frozenset({"paper_candidate", "live_candidate"})
FORBIDDEN_DAILY_SETUP_STATUSES = frozenset({"paper_candidate", "live_candidate"})
DATA_READY_STATUSES = frozenset({"DATA_OK", "DATA_READY"})
STOCK_PRODUCT_CLASSES = frozenset({"STK", "STOCK"})
MIN_REWARD_RISK = 3.0
ACTIVE_DAILY_SETUP_STATUSES = frozenset(
    {"detected", "watching", "waiting_for_confirmation", "armed", "entry_ready"}
)
DAILY_SETUP_ALLOWED_TRANSITIONS: dict[str, frozenset[str]] = {
    "detected": frozenset({"detected", "watching", "expired", "invalidated"}),
    "watching": frozenset({"watching", "waiting_for_confirmation", "expired", "invalidated"}),
    "waiting_for_confirmation": frozenset(
        {"waiting_for_confirmation", "armed", "expired", "invalidated"}
    ),
    "armed": frozenset({"armed", "entry_ready", "expired", "invalidated"}),
    "entry_ready": frozenset({"entry_ready", "expired", "invalidated"}),
    "expired": frozenset({"expired"}),
    "invalidated": frozenset({"invalidated"}),
}
ENTRY_READY_GATE_ORDER = (
    "setup_signal_active",
    "entry_window_open",
    "data_quality_ok",
    "stock_only",
    "stock_operational",
    "liquidity_ok",
    "risk_ok",
    "price_available",
    "not_stale",
    "not_invalidated",
    "not_safety_blocked",
)
ALLOWED_TRANSITIONS: dict[str, frozenset[str]] = {
    "watchlist": frozenset(
        {
            "watchlist",
            "entry_ready",
            "cooldown",
            "blocked",
            "expired",
            "rejected",
        }
    ),
    "entry_ready": frozenset(
        {
            "entry_ready",
            "watchlist",
            "cooldown",
            "blocked",
            "expired",
            "rejected",
        }
    ),
    "cooldown": frozenset({"cooldown", "watchlist", "blocked", "expired", "rejected"}),
    "blocked": frozenset({"blocked"}),
    "expired": frozenset({"expired"}),
    "rejected": frozenset({"rejected"}),
}
SENSITIVE_KEY_PARTS = ("secret", "token", "password", "api_key", "account", "username")


@dataclass(frozen=True, slots=True)
class SetupEvaluation:
    recoverable_reasons: tuple[str, ...] = ()
    non_recoverable_reasons: tuple[str, ...] = ()
    reward_risk: float | None = None
    entry_gate_passed: bool = False
    entry_score: float = 0.0
    trigger_score: float = 0.0
    stop_context_broken: bool = False
    invalidation_reason: str | None = None


@dataclass(slots=True)
class DailySetup:
    setup_id: str
    symbol: str
    side: Side
    pattern_id: object | None
    pattern_key: str | None
    detected_at: str
    status: DailySetupStatus
    reward_risk: float | None
    source_evidence_hash: str
    recoverable_reasons: tuple[str, ...] = ()
    non_recoverable_reasons: tuple[str, ...] = ()
    entry_score: float = 0.0
    trigger_score: float = 0.0
    timeframe: str = "1d"
    entry: float | None = None
    stop: float | None = None
    target: float | None = None
    lab_paper_probe_request: dict[str, Any] | None = None
    invalidation_reason: str | None = None
    last_evaluated_at: str | None = None
    next_evaluation_at: str | None = None
    expires_at: str | None = None
    setup_age_days: int = 0
    entry_candidate_price: float | None = None
    volume_confirmation: str = "unknown"
    trend_context: str = "unknown"
    regime_context: str = "unknown"
    liquidity_context: str = "unknown"
    entry_gate_reasons: tuple[str, ...] = ()
    next_action: str = "reevaluate_after_close"
    source_match_snapshot: Mapping[str, Any] = field(default_factory=dict)
    entry_gate_version: str = "entry_gate_v1"
    risk_gate_version: str = "risk_gate_v1"
    created_by: str = "daily_setup_watchlist"
    created_at: str | None = None
    updated_at: str | None = None
    transitions: list[dict[str, Any]] = field(default_factory=list)
    source_payload: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.status = _validate_daily_setup_status(self.status)
        self.symbol = str(self.symbol).strip().upper()
        side = str(self.side).lower()
        if side not in {"long", "short"}:
            raise ValueError(f"unsupported setup side: {self.side}")
        self.side = side  # type: ignore[assignment]
        self.timeframe = "1d"

    def transition_to(
        self,
        status: str,
        *,
        reason: str = "manual_transition",
        now: datetime | None = None,
    ) -> None:
        target = _validate_daily_setup_status(status)
        allowed = DAILY_SETUP_ALLOWED_TRANSITIONS[self.status]
        if target not in allowed:
            raise ValueError(f"transition {self.status}->{target} is not allowed")
        generated_at = _iso(now)
        self.transitions.append(
            _json_safe(
                {
                    "at": generated_at,
                    "from_status": self.status,
                    "to_status": target,
                    "reason": reason,
                }
            )
        )
        self.status = target
        self.updated_at = generated_at

    def to_dict(self) -> dict[str, Any]:
        return _json_safe(
            {
                "schema_version": SCHEMA_VERSION,
                "setup_id": self.setup_id,
                "symbol": self.symbol,
                "side": self.side,
                "pattern_id": self.pattern_id,
                "pattern_key": self.pattern_key,
                "detected_at": self.detected_at,
                "last_evaluated_at": self.last_evaluated_at,
                "next_evaluation_at": self.next_evaluation_at,
                "expires_at": self.expires_at,
                "setup_age_days": self.setup_age_days,
                "status": self.status,
                "timeframe": "1d",
                "reward_risk": self.reward_risk,
                "entry_score": self.entry_score,
                "trigger_score": self.trigger_score,
                "entry_candidate_price": (
                    self.entry_candidate_price
                    if self.entry_candidate_price is not None
                    else self.entry
                ),
                "entry": self.entry,
                "stop": self.stop,
                "target": self.target,
                "volume_confirmation": self.volume_confirmation,
                "trend_context": self.trend_context,
                "regime_context": self.regime_context,
                "liquidity_context": self.liquidity_context,
                "recoverable_reasons": self.recoverable_reasons,
                "non_recoverable_reasons": self.non_recoverable_reasons,
                "entry_gate_reasons": self.entry_gate_reasons,
                "source_evidence_hash": self.source_evidence_hash,
                "source_match_snapshot": self.source_match_snapshot,
                "entry_gate_version": self.entry_gate_version,
                "risk_gate_version": self.risk_gate_version,
                "created_by": self.created_by,
                "lab_paper_probe_request": self.lab_paper_probe_request,
                "invalidation_reason": self.invalidation_reason,
                "next_action": self.next_action,
                "created_at": self.created_at,
                "updated_at": self.updated_at,
                "transitions": self.transitions,
                "source_payload": self.source_payload,
                "entry_ready": self.status == "entry_ready",
                "orders_allowed": False,
                "paper_allowed": False,
                "live_allowed": False,
                "submit_order_called": False,
                "candidate_approval": False,
            }
        )


class DailySetupWatchlist:
    def __init__(self, settings: Any | None = None) -> None:
        self.settings = settings if settings is not None else get_settings()

    def consider_setup(
        self,
        source: Mapping[str, Any],
        evaluation: SetupEvaluation,
        *,
        now: datetime | None = None,
    ) -> DailySetup | None:
        if not bool(_setting(self.settings, "daily_setup_watchlist_enabled", True)):
            return None
        if evaluation.non_recoverable_reasons:
            return None
        if not _reward_risk_ok(evaluation.reward_risk):
            return None
        if not evaluation.entry_gate_passed and not evaluation.recoverable_reasons:
            return None

        generated_at = _iso(now)
        status: DailySetupStatus = "entry_ready" if evaluation.entry_gate_passed else "watching"
        detected_at = _safe_optional_text(source.get("detected_at")) or generated_at
        max_age_days = int(_setting(self.settings, "daily_setup_max_age_days", 5) or 5)
        setup = DailySetup(
            setup_id=_setup_id(source, generated_at),
            symbol=str(source.get("symbol", "")).strip().upper(),
            side=str(source.get("side", "long")).lower(),  # type: ignore[arg-type]
            pattern_id=source.get("pattern_id"),
            pattern_key=_safe_optional_text(source.get("pattern_key")),
            detected_at=detected_at,
            status=status,
            reward_risk=evaluation.reward_risk,
            recoverable_reasons=evaluation.recoverable_reasons,
            non_recoverable_reasons=evaluation.non_recoverable_reasons,
            entry_score=evaluation.entry_score,
            trigger_score=evaluation.trigger_score,
            entry=_optional_float(source.get("entry")),
            stop=_optional_float(source.get("stop")),
            target=_optional_float(source.get("target")),
            entry_candidate_price=_optional_float(source.get("entry_candidate_price"))
            or _optional_float(source.get("entry")),
            source_evidence_hash=stable_source_evidence_hash(source),
            lab_paper_probe_request=None,
            last_evaluated_at=generated_at,
            next_evaluation_at=_iso(_parse_datetime(generated_at) + _one_day()),
            expires_at=_iso(_parse_datetime(detected_at) + _days(max_age_days)),
            setup_age_days=max(
                0,
                (_parse_datetime(generated_at) - _parse_datetime(detected_at)).days,
            ),
            source_match_snapshot=source,
            created_at=generated_at,
            updated_at=generated_at,
            source_payload=source,
        )
        if setup.status == "entry_ready":
            setup.lab_paper_probe_request = self._lab_paper_probe_request(setup, generated_at)
        return setup

    def reevaluate(
        self,
        setup: DailySetup,
        evaluation: SetupEvaluation,
        *,
        now: datetime | None = None,
    ) -> DailySetup:
        if setup.status not in ACTIVE_DAILY_SETUP_STATUSES:
            return setup
        generated_at = _iso(now)
        setup.updated_at = generated_at
        setup.last_evaluated_at = generated_at
        setup.next_evaluation_at = _iso(_parse_datetime(generated_at) + _one_day())
        setup.setup_age_days = max(
            0,
            (_parse_datetime(generated_at) - _parse_datetime(setup.detected_at)).days,
        )
        setup.reward_risk = evaluation.reward_risk
        setup.entry_score = evaluation.entry_score
        setup.trigger_score = evaluation.trigger_score
        setup.recoverable_reasons = evaluation.recoverable_reasons
        setup.non_recoverable_reasons = evaluation.non_recoverable_reasons

        if evaluation.stop_context_broken or evaluation.invalidation_reason:
            setup.invalidation_reason = evaluation.invalidation_reason or "setup_context_broken"
            setup.transition_to("invalidated", reason=setup.invalidation_reason, now=now)
            return setup
        if evaluation.non_recoverable_reasons or not _reward_risk_ok(evaluation.reward_risk):
            setup.invalidation_reason = "non_recoverable_or_reward_risk_failed"
            setup.transition_to("invalidated", reason=setup.invalidation_reason, now=now)
            return setup
        if self._is_expired(setup, now):
            setup.transition_to("expired", reason="max_age_days_exceeded", now=now)
            return setup
        if evaluation.entry_gate_passed:
            if setup.status in {"watching"}:
                setup.transition_to(
                    "waiting_for_confirmation",
                    reason="entry_gate_progressing",
                    now=now,
                )
            if setup.status == "waiting_for_confirmation":
                setup.transition_to("armed", reason="entry_gate_progressing", now=now)
            if setup.status == "armed":
                setup.transition_to("entry_ready", reason="entry_gate_passed", now=now)
            setup.lab_paper_probe_request = self._lab_paper_probe_request(setup, generated_at)
        return setup

    def enforce_max_active(self, setups: list[DailySetup], *, now: datetime | None = None) -> None:
        max_active = int(_setting(self.settings, "daily_setup_max_active", 100) or 0)
        if max_active <= 0:
            max_active = 0
        active = [setup for setup in setups if setup.status in ACTIVE_DAILY_SETUP_STATUSES]
        ranked = sorted(
            active,
            key=lambda item: (item.entry_score, item.detected_at, item.setup_id),
            reverse=True,
        )
        for setup in ranked[max_active:]:
            setup.transition_to("expired", reason="daily_setup_max_active_exceeded", now=now)

    def write_artifacts(
        self,
        setups: list[DailySetup],
        *,
        generated_at: datetime | None = None,
    ) -> dict[str, Any]:
        artifact = self.build_artifact(setups, generated_at=generated_at)
        json_path = self.artifact_json_path
        md_path = self.artifact_markdown_path
        json_path.parent.mkdir(parents=True, exist_ok=True)
        md_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(
            json.dumps(artifact, indent=2, sort_keys=True, allow_nan=False) + "\n",
            encoding="utf-8",
        )
        md_path.write_text(self.render_markdown(artifact), encoding="utf-8")
        return artifact

    def load_artifact(self) -> dict[str, Any] | None:
        path = self.artifact_json_path
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def find_setup(self, setup_id: str) -> dict[str, Any] | None:
        artifact = self.load_artifact()
        if not artifact:
            return None
        for setup in artifact.get("setups", []):
            if str(setup.get("setup_id")) == setup_id:
                return setup
        return None

    def summary(self) -> dict[str, Any]:
        artifact = self.load_artifact()
        if not artifact:
            return _daily_setup_summary([], generated_at=_iso(None))
        return artifact.get(
            "summary",
            _daily_setup_summary([], generated_at=artifact.get("generated_at")),
        )

    def build_artifact(
        self,
        setups: list[DailySetup],
        *,
        generated_at: datetime | None = None,
    ) -> dict[str, Any]:
        generated = _iso(generated_at)
        records = [setup.to_dict() for setup in setups]
        return _json_safe(
            {
                "schema_version": DAILY_SETUP_ARTIFACT_SCHEMA_VERSION,
                "generated_at": generated,
                "read_only": True,
                "cadence": "daily",
                "timeframe": "1d",
                "setups": records,
                "items": records,
                "summary": _daily_setup_summary(records, generated_at=generated),
                "state_counts": _state_counts_from_status(records),
                "entry_ready_count": sum(
                    1 for item in records if item.get("status") == "entry_ready"
                ),
                "orders_allowed": False,
                "paper_allowed": False,
                "live_allowed": False,
                "submit_order_called": False,
                "candidate_approval": False,
                "safety": _safety_flags(),
            }
        )

    def render_markdown(self, artifact: Mapping[str, Any]) -> str:
        summary = artifact.get("summary", {})
        lines = [
            "# Daily Setup Watchlist",
            "",
            f"- active_count: `{summary.get('active_count', 0)}`",
            f"- entry_ready_count: `{summary.get('entry_ready_count', 0)}`",
            f"- orders_allowed: `{artifact.get('orders_allowed')}`",
            f"- paper_allowed: `{artifact.get('paper_allowed')}`",
            f"- live_allowed: `{artifact.get('live_allowed')}`",
            f"- submit_order_called: `{artifact.get('submit_order_called')}`",
            "",
            "Read-only daily setup metadata. Entry-ready records do not submit orders.",
        ]
        return "\n".join(lines).rstrip() + "\n"

    @property
    def artifact_json_path(self) -> Path:
        return self.artifact_dir / "latest.json"

    @property
    def artifact_markdown_path(self) -> Path:
        return self.artifact_dir / "latest.md"

    @property
    def artifact_dir(self) -> Path:
        artifacts_dir = Path(str(_setting(self.settings, "artifacts_dir", "artifacts")))
        return artifacts_dir / "runtime" / "daily_setup_watchlist"

    def _is_expired(self, setup: DailySetup, now: datetime | None) -> bool:
        max_age = int(_setting(self.settings, "daily_setup_max_age_days", 5) or 0)
        detected = _parse_datetime(setup.detected_at)
        current = now or datetime.now(timezone.utc)
        if current.tzinfo is None:
            current = current.replace(tzinfo=timezone.utc)
        return (current.astimezone(timezone.utc) - detected).days >= max_age

    def _lab_paper_probe_request(self, setup: DailySetup, generated_at: str) -> dict[str, Any]:
        return {
            "schema_version": LAB_PAPER_PROBE_REQUEST_SCHEMA_VERSION,
            "generated_at": generated_at,
            "setup_id": setup.setup_id,
            "symbol": setup.symbol,
            "side": setup.side,
            "route": "lab_paper_probe",
            "enabled": bool(_setting(self.settings, "daily_setup_route_entry_ready_to_lab", False)),
            "submits_order": False,
            "allow_paper_on_entry_ready": False,
            "orders_allowed": False,
            "paper_allowed": False,
            "live_allowed": False,
            "submit_order_called": False,
        }


@dataclass(frozen=True, slots=True)
class SetupWatchlistItem:
    setup_id: str
    symbol: str
    side: Side
    created_at: str
    state: WatchlistState = "watchlist"
    source: str = "daily_swing"
    setup_family: str = "daily_setup"
    updated_at: str | None = None
    last_evaluated_at: str | None = None
    revision: int = 1
    entry_ready: bool = False
    block_reason: str | None = None
    transition_history: tuple[dict[str, Any], ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        state = _validate_state(self.state)
        side = str(self.side).lower()
        if side not in {"long", "short"}:
            raise ValueError(f"unsupported setup side: {self.side}")
        object.__setattr__(self, "state", state)
        object.__setattr__(self, "side", side)
        object.__setattr__(self, "symbol", str(self.symbol).strip().upper())
        object.__setattr__(self, "entry_ready", state == "entry_ready")


@dataclass(frozen=True, slots=True)
class SetupReevaluationInput:
    setup_signal_active: bool = False
    entry_window_open: bool = False
    data_quality_status: str = "UNKNOWN"
    product_class: str = "UNKNOWN"
    is_stock_operational: bool = False
    liquidity_ok: bool = False
    risk_ok: bool = False
    price_available: bool = False
    stale: bool = False
    invalidated: bool = False
    cooldown_active: bool = False
    safety_block_reason: str | None = None
    as_of: str | date | datetime | None = None
    metrics: Mapping[str, Any] = field(default_factory=dict)
    notes: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class SetupReevaluationResult:
    item: SetupWatchlistItem
    evaluation: dict[str, Any]
    transitioned: bool


def create_setup_watchlist_item(
    *,
    symbol: str,
    side: Side,
    setup_id: str | None = None,
    setup_family: str = "daily_setup",
    source: str = "daily_swing",
    metadata: Mapping[str, Any] | None = None,
    now: datetime | None = None,
) -> SetupWatchlistItem:
    generated_at = _iso(now)
    normalized_symbol = str(symbol).strip().upper()
    item_id = setup_id or f"{normalized_symbol}:{str(side).lower()}:{generated_at[:10]}"
    return SetupWatchlistItem(
        setup_id=item_id,
        symbol=normalized_symbol,
        side=side,
        created_at=generated_at,
        updated_at=generated_at,
        setup_family=setup_family,
        source=source,
        metadata=metadata or {},
    )


def transition_setup_state(
    item: SetupWatchlistItem,
    to_state: str,
    *,
    reason: str,
    now: datetime | None = None,
    details: Mapping[str, Any] | None = None,
) -> SetupWatchlistItem:
    from_state = _validate_state(item.state)
    target = _validate_state(to_state)
    allowed = ALLOWED_TRANSITIONS[from_state]
    if target not in allowed:
        raise ValueError(
            f"transition {from_state}->{target} is not allowed for daily setup watchlist"
        )
    generated_at = _iso(now)
    transition = _json_safe(
        {
            "at": generated_at,
            "from_state": from_state,
            "to_state": target,
            "reason": reason,
            "details": details or {},
        }
    )
    return replace(
        item,
        state=target,
        updated_at=generated_at,
        last_evaluated_at=generated_at,
        revision=item.revision + 1,
        entry_ready=target == "entry_ready",
        block_reason=reason if target == "blocked" else None,
        transition_history=item.transition_history + (transition,),
    )


def reevaluate_setup_watchlist(
    item: SetupWatchlistItem,
    observation: SetupReevaluationInput,
    *,
    now: datetime | None = None,
) -> SetupReevaluationResult:
    generated_at = _iso(now)
    gates = entry_ready_gates(observation)
    gate_failures = tuple(name for name in ENTRY_READY_GATE_ORDER if not gates[name])
    target, reason = _target_state(item, observation, gates, gate_failures)
    transitioned = target != item.state
    if transitioned:
        updated = transition_setup_state(
            item,
            target,
            reason=reason,
            now=now,
            details={"gate_failures": gate_failures, "as_of": _as_of(observation.as_of)},
        )
    else:
        updated = replace(
            item,
            updated_at=generated_at,
            last_evaluated_at=generated_at,
            revision=item.revision + 1,
            entry_ready=target == "entry_ready",
            block_reason=reason if target == "blocked" else item.block_reason,
        )
    evaluation = _evaluation_record(
        before=item,
        after=updated,
        observation=observation,
        gates=gates,
        gate_failures=gate_failures,
        reason=reason,
        generated_at=generated_at,
        transitioned=transitioned,
    )
    return SetupReevaluationResult(item=updated, evaluation=evaluation, transitioned=transitioned)


def entry_ready_gates(observation: SetupReevaluationInput) -> dict[str, bool]:
    return {
        "setup_signal_active": bool(observation.setup_signal_active),
        "entry_window_open": bool(observation.entry_window_open),
        "data_quality_ok": str(observation.data_quality_status).upper() in DATA_READY_STATUSES,
        "stock_only": str(observation.product_class).upper() in STOCK_PRODUCT_CLASSES,
        "stock_operational": bool(observation.is_stock_operational),
        "liquidity_ok": bool(observation.liquidity_ok),
        "risk_ok": bool(observation.risk_ok),
        "price_available": bool(observation.price_available),
        "not_stale": not bool(observation.stale),
        "not_invalidated": not bool(observation.invalidated),
        "not_safety_blocked": observation.safety_block_reason in {None, ""},
    }


def watchlist_item_record(item: SetupWatchlistItem) -> dict[str, Any]:
    record = asdict(item)
    record.update(
        {
            "schema_version": SCHEMA_VERSION,
            "entry_ready": item.state == "entry_ready",
            "order_intent": "none",
            "orders_allowed": False,
            "paper_allowed": False,
            "live_allowed": False,
            "submit_order_called": False,
            "paper_order_submitted": False,
            "live_order_submitted": False,
            "no_order_reason": "daily_setup_watchlist_observation_only",
            "candidate_approval": False,
        }
    )
    return _json_safe(record)


def build_watchlist_artifact(
    items: list[SetupWatchlistItem],
    *,
    evaluations: list[dict[str, Any]] | None = None,
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    generated = _iso(generated_at)
    item_records = [watchlist_item_record(item) for item in items]
    state_counts = Counter(str(record.get("state")) for record in item_records)
    forbidden = [record for record in item_records if _has_forbidden_outcome(record)]
    payload = {
        "schema_version": ARTIFACT_SCHEMA_VERSION,
        "generated_at": generated,
        "status": "blocked_safety" if forbidden else "ok",
        "items": item_records,
        "evaluations": [_json_safe(item) for item in evaluations or []],
        "state_counts": dict(sorted(state_counts.items())),
        "entry_ready_count": state_counts.get("entry_ready", 0),
        "orders_allowed": False,
        "paper_allowed": False,
        "live_allowed": False,
        "submit_order_called": False,
        "paper_order_submitted": False,
        "live_order_submitted": False,
        "candidate_approval": False,
        "forbidden_outcomes": len(forbidden),
        "safety": _safety_flags(),
    }
    return _json_safe(payload)


def write_watchlist_artifacts(
    items: list[SetupWatchlistItem],
    *,
    evaluations: list[dict[str, Any]] | None = None,
    json_out: str | Path,
    md_out: str | Path,
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    artifact = build_watchlist_artifact(items, evaluations=evaluations, generated_at=generated_at)
    json_path = Path(json_out)
    md_path = Path(md_out)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(
        json.dumps(artifact, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    md_path.write_text(render_watchlist_markdown(artifact), encoding="utf-8")
    return artifact


def render_watchlist_markdown(artifact: Mapping[str, Any]) -> str:
    state_counts = artifact.get("state_counts", {})
    lines = [
        "# Daily Setup Watchlist",
        "",
        f"- status: `{artifact.get('status')}`",
        f"- items: `{len(artifact.get('items', []))}`",
        f"- entry_ready_count: `{artifact.get('entry_ready_count')}`",
        f"- state_counts: `{state_counts}`",
        f"- orders_allowed: `{artifact.get('orders_allowed')}`",
        f"- paper_allowed: `{artifact.get('paper_allowed')}`",
        f"- live_allowed: `{artifact.get('live_allowed')}`",
        f"- submit_order_called: `{artifact.get('submit_order_called')}`",
        f"- forbidden_outcomes: `{artifact.get('forbidden_outcomes')}`",
        "",
        "Entry-ready rows are observation-only watchlist records. This backend does not "
        "submit orders or create classic candidate states.",
    ]
    return "\n".join(lines).rstrip() + "\n"


def _target_state(
    item: SetupWatchlistItem,
    observation: SetupReevaluationInput,
    gates: Mapping[str, bool],
    gate_failures: tuple[str, ...],
) -> tuple[WatchlistState, str]:
    if item.state in TERMINAL_STATES:
        return item.state, "terminal_state_no_auto_reopen"
    if observation.safety_block_reason:
        return "blocked", f"blocked_safety:{_safe_reason(observation.safety_block_reason)}"
    if observation.invalidated:
        return "rejected", "setup_invalidated"
    if observation.stale:
        return "expired", "setup_observation_stale"
    if observation.cooldown_active:
        return "cooldown", "setup_cooldown_active"
    if all(gates.values()):
        return "entry_ready", "entry_ready_watchlist_only"
    if item.state == "entry_ready":
        return "watchlist", "entry_ready_revoked:" + ",".join(gate_failures)
    return "watchlist", "watchlist_pending:" + ",".join(gate_failures)


def _evaluation_record(
    *,
    before: SetupWatchlistItem,
    after: SetupWatchlistItem,
    observation: SetupReevaluationInput,
    gates: Mapping[str, bool],
    gate_failures: tuple[str, ...],
    reason: str,
    generated_at: str,
    transitioned: bool,
) -> dict[str, Any]:
    return _json_safe(
        {
            "schema_version": EVALUATION_SCHEMA_VERSION,
            "generated_at": generated_at,
            "setup_id": before.setup_id,
            "symbol": before.symbol,
            "side": before.side,
            "before_state": before.state,
            "after_state": after.state,
            "transitioned": transitioned,
            "entry_ready": after.state == "entry_ready",
            "reason": reason,
            "gates": {name: bool(gates[name]) for name in ENTRY_READY_GATE_ORDER},
            "gate_failures": list(gate_failures),
            "observation": {
                "as_of": _as_of(observation.as_of),
                "data_quality_status": observation.data_quality_status,
                "product_class": observation.product_class,
                "metrics": observation.metrics,
                "notes": observation.notes,
            },
            "order_intent": "none",
            "orders_allowed": False,
            "paper_allowed": False,
            "live_allowed": False,
            "submit_order_called": False,
            "paper_order_submitted": False,
            "live_order_submitted": False,
            "candidate_approval": False,
            "safety": _safety_flags(),
        }
    )


def _validate_state(state: str) -> WatchlistState:
    normalized = str(state).strip().lower()
    if normalized in FORBIDDEN_CLASSIC_CANDIDATES:
        raise ValueError(
            f"classic candidate state is forbidden for daily setup watchlist: {normalized}"
        )
    if normalized not in WATCHLIST_STATES:
        raise ValueError(f"unsupported daily setup watchlist state: {state}")
    return normalized  # type: ignore[return-value]


def _validate_daily_setup_status(status: str) -> DailySetupStatus:
    normalized = str(status).strip().lower()
    if normalized in FORBIDDEN_DAILY_SETUP_STATUSES:
        raise ValueError(f"daily setup status is not order/candidate capable: {normalized}")
    if normalized not in DAILY_SETUP_ALLOWED_TRANSITIONS:
        raise ValueError(f"unsupported daily setup status: {status}")
    return normalized  # type: ignore[return-value]


def stable_source_evidence_hash(source: Mapping[str, Any]) -> str:
    payload = json.dumps(
        _json_safe(source),
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def get_settings() -> Any:
    from tradeo.core.config import get_settings as _get_settings

    return _get_settings()


def _safety_flags() -> dict[str, bool]:
    return {
        "no_orders": True,
        "no_paper_orders": True,
        "no_live_orders": True,
        "no_broker_submit": True,
        "no_candidate_approval": True,
        "watchlist_only": True,
    }


def _has_forbidden_outcome(record: Mapping[str, Any]) -> bool:
    return bool(
        record.get("orders_allowed")
        or record.get("submit_order_called")
        or record.get("paper_order_submitted")
        or record.get("live_order_submitted")
        or record.get("candidate_approval")
    )


def _daily_setup_summary(
    records: list[dict[str, Any]],
    *,
    generated_at: str | None,
) -> dict[str, Any]:
    counts = _state_counts_from_status(records)
    active_count = sum(
        1 for record in records if record.get("status") in ACTIVE_DAILY_SETUP_STATUSES
    )
    return {
        "schema_version": DAILY_SETUP_ARTIFACT_SCHEMA_VERSION,
        "generated_at": generated_at,
        "total_count": len(records),
        "active_count": active_count,
        "watching_count": counts.get("watching", 0),
        "entry_ready_count": counts.get("entry_ready", 0),
        "expired_count": counts.get("expired", 0),
        "invalidated_count": counts.get("invalidated", 0),
        "orders_allowed": False,
        "paper_allowed": False,
        "live_allowed": False,
        "submit_order_called": False,
        "candidate_approval": False,
        "safety": _safety_flags(),
    }


def _state_counts_from_status(records: list[dict[str, Any]]) -> dict[str, int]:
    counts = Counter(str(record.get("status") or "unknown") for record in records)
    return dict(sorted(counts.items()))


def _setup_id(source: Mapping[str, Any], generated_at: str) -> str:
    explicit = _safe_optional_text(source.get("setup_id"))
    if explicit:
        return explicit
    symbol = _safe_optional_text(source.get("symbol")) or "UNKNOWN"
    side = _safe_optional_text(source.get("side")) or "long"
    digest = stable_source_evidence_hash(source)[:12]
    return f"{symbol.upper()}:{side.lower()}:{generated_at[:10]}:{digest}"


def _reward_risk_ok(value: float | None) -> bool:
    if value is None:
        return False
    return _optional_float(value) is not None and float(value) >= MIN_REWARD_RISK


def _parse_datetime(value: str | datetime) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    else:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _one_day() -> timedelta:
    return timedelta(days=1)


def _days(value: int) -> timedelta:
    return timedelta(days=max(1, int(value)))


def _safe_optional_text(value: Any) -> str | None:
    if value in (None, ""):
        return None
    return str(_json_safe(value))


def _optional_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _setting(settings: Any, name: str, default: Any) -> Any:
    if isinstance(settings, Mapping):
        return settings.get(name, default)
    return getattr(settings, name, default)


def _iso(value: datetime | None = None) -> str:
    generated = value or datetime.now(timezone.utc)
    if generated.tzinfo is None:
        generated = generated.replace(tzinfo=timezone.utc)
    return generated.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _as_of(value: str | date | datetime | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return _iso(value)
    if isinstance(value, date):
        return value.isoformat()
    return str(value)


def _safe_reason(reason: str) -> str:
    return str(_json_safe(reason)).replace(" ", "_")


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        safe: dict[str, Any] = {}
        for key, item in value.items():
            key_text = str(key)
            if any(part in key_text.lower() for part in SENSITIVE_KEY_PARTS):
                safe[key_text] = "<redacted>"
            else:
                safe[key_text] = _json_safe(item)
        return safe
    if isinstance(value, (tuple, list)):
        return [_json_safe(item) for item in value]
    if isinstance(value, datetime):
        return _iso(value)
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    return value
