from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import gzip
import hashlib
import json
import math
from pathlib import Path
from statistics import mean, median
from typing import Any, Iterable

import pandas as pd

from tradeo.research.intraday_vwap_features import build_intraday_vwap_features
from tradeo.services.technical_indicators import atr

SCHEMA_VERSION = "tradeo.vwap_candidate_confirmation.v1"
OVERLAYS = (
    "baseline_existing",
    "exit_on_vwap_loss",
    "exit_on_failed_reclaim",
    "exit_on_close_below_vwap_after_entry",
    "exit_on_vwap_loss_or_time_stop",
    "exit_on_vwap_loss_or_4R_takeprofit",
)


@dataclass(frozen=True, slots=True)
class CandidateEvent:
    run_id: int
    pattern_key: str
    candidate_id: int | None
    pattern_id: int | None
    side: str
    symbol: str
    timeframe: str
    window_size: int | None
    window_start: str | None
    window_end: str | None
    entry_ts: str | None
    entry_price: float | None
    risk_proxy: float | None
    outcome_r: float | None
    mfe_r: float | None
    mae_r: float | None
    forward_end: str | None
    split: str | None
    execution_cost_r: float | None
    vwap_at_entry: float | None
    price_vs_vwap_bps: float | None
    vwap_slope_bps: float | None
    session_bucket: str | None
    month: str | None
    source: str
    data_quality: str
    raw: dict[str, Any]


def analyze_vwap_candidate_confirmation(
    *,
    run_id: int,
    pattern_key: str,
    wave_manifest: str | Path,
    forensics_json: str | Path,
    evidence_json: str | Path,
    ohlcv_cache_dir: str | Path,
    min_event_count: int = 30,
) -> dict[str, Any]:
    forensics = _read_json(forensics_json)
    evidence = _read_json(evidence_json)
    wave = _read_json(wave_manifest)
    candidate = _candidate_metadata(forensics, evidence, run_id=run_id, pattern_key=pattern_key)
    scope = _scope_integrity(wave, forensics, evidence, run_id=run_id)
    ledger_events, ledger_status = _load_ledger_events(
        forensics_json=forensics_json,
        run_id=run_id,
        pattern_key=pattern_key,
    )
    artifact_events = _load_artifact_events(evidence_json, run_id=run_id, pattern_key=pattern_key)
    expected_sample_count = _int_or_none(candidate.get("sample_count"))
    db_events: list[dict[str, Any]] = []
    db_read = {"attempted": False, "row_count": 0, "error": None}
    if not ledger_events and (
        len(artifact_events) < min_event_count
        or (expected_sample_count is not None and len(artifact_events) < expected_sample_count)
    ):
        db_events, db_read = _load_db_events(run_id=run_id, pattern_key=pattern_key)
    raw_events = ledger_events or _deduplicate_events([*artifact_events, *db_events])
    events = reconstruct_candidate_events(
        raw_events,
        run_id=run_id,
        pattern_key=pattern_key,
        ohlcv_cache_dir=ohlcv_cache_dir,
    )
    overlay_results = simulate_overlays(events)
    best_overlay = choose_best_overlay(overlay_results)
    decision = confirmation_decision(
        overlay_results=overlay_results,
        best_overlay=best_overlay,
        event_count=len(events),
        min_event_count=min_event_count,
    )
    report = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(UTC).isoformat(),
        "candidate": candidate,
        "scope_integrity": {**scope, "ledger": ledger_status, "db_read": db_read},
        "event_dataset": _event_dataset_summary(events, expected_sample_count=candidate.get("sample_count")),
        "overlay_results": overlay_results,
        "best_overlay": best_overlay,
        "confirmation_decision": decision,
        "safety": {
            "live_allowed": False,
            "paper_allowed": False,
            "orders_allowed": False,
            "wave_executed": False,
            "ibkr_used": False,
            "db_write_allowed": False,
        },
    }
    return report


def reconstruct_candidate_events(
    rows: Iterable[dict[str, Any]],
    *,
    run_id: int,
    pattern_key: str,
    ohlcv_cache_dir: str | Path,
) -> list[CandidateEvent]:
    events: list[CandidateEvent] = []
    cache_dir = Path(ohlcv_cache_dir)
    for row in rows:
        symbol = str(row.get("symbol") or "").upper()
        timeframe = str(row.get("timeframe") or "30m")
        bars = _load_feature_frame(cache_dir, symbol=symbol, timeframe=timeframe)
        enriched = dict(row)
        enriched["_feature_frame"] = bars
        event = _event_from_row(enriched, run_id=run_id, pattern_key=pattern_key, feature_frame=bars)
        events.append(event)
    return events


def simulate_overlays(events: list[CandidateEvent]) -> list[dict[str, Any]]:
    outcomes_by_overlay: dict[str, list[dict[str, Any]]] = {name: [] for name in OVERLAYS}
    for event in events:
        feature_frame = _feature_frame_from_event(event)
        outcomes_by_overlay["baseline_existing"].append(
            _outcome_row(event, event.outcome_r, "existing_outcome_r", event.mfe_r, event.mae_r)
        )
        for overlay in OVERLAYS:
            if overlay == "baseline_existing":
                continue
            outcomes_by_overlay[overlay].append(_simulate_overlay(event, overlay, feature_frame))
    return [_metrics_for_overlay(name, rows) for name, rows in outcomes_by_overlay.items()]


def choose_best_overlay(overlay_results: list[dict[str, Any]]) -> dict[str, Any]:
    candidates = [row for row in overlay_results if row["overlay"] != "baseline_existing"]
    if not candidates:
        return {}
    return max(
        candidates,
        key=lambda row: (
            row.get("decision_eligible") is True,
            -(row.get("max_drawdown_r") or 10**9),
            row.get("expectancy_r") or -10**9,
            row.get("profit_factor") or -10**9,
        ),
    )


def confirmation_decision(
    *,
    overlay_results: list[dict[str, Any]],
    best_overlay: dict[str, Any],
    event_count: int,
    min_event_count: int,
) -> str:
    if event_count < min_event_count:
        return "insufficient_event_data"
    if best_overlay.get("decision_eligible") is True:
        return "confirm_candidate_ready_for_narrow_wave"
    if any(row.get("computable_count", 0) > 0 for row in overlay_results if row["overlay"] != "baseline_existing"):
        return "reject_drawdown_unmitigated"
    return "needs_engine_support"


def render_markdown(report: dict[str, Any]) -> str:
    candidate = report.get("candidate") or {}
    dataset = report.get("event_dataset") or {}
    best = report.get("best_overlay") or {}
    lines = [
        "# VWAP Candidate Confirmation",
        "",
        "## Candidate",
        f"- run_id: `{candidate.get('run_id')}`",
        f"- pattern_key: `{candidate.get('pattern_key')}`",
        f"- side/timeframe/window: `{candidate.get('side')}` / `{candidate.get('timeframe')}` / `{candidate.get('window_size')}`",
        "",
        "## Scope",
        f"- exact_scope: `{(report.get('scope_integrity') or {}).get('exact_scope')}`",
        f"- run_id_in_scope: `{(report.get('scope_integrity') or {}).get('run_id_in_scope')}`",
        "",
        "## Baseline",
        f"- expected_sample_count: `{dataset.get('expected_sample_count')}`",
        f"- event_count: `{dataset.get('event_count')}`",
        f"- data_completeness: `{dataset.get('data_completeness')}`",
        "",
        "## Overlay results",
    ]
    for row in report.get("overlay_results") or []:
        lines.append(
            f"- {row['overlay']}: n `{row['sample_count']}`, exp `{row.get('expectancy_r')}`, "
            f"PF `{row.get('profit_factor')}`, DD `{row.get('max_drawdown_r')}`, eligible `{row.get('decision_eligible')}`"
        )
    lines.extend(
        [
            "",
            "## Best overlay",
            f"- overlay: `{best.get('overlay')}`",
            f"- max_drawdown_r: `{best.get('max_drawdown_r')}`",
            f"- expectancy_r: `{best.get('expectancy_r')}`",
            f"- profit_factor: `{best.get('profit_factor')}`",
            "",
            "## Decision",
            f"`{report.get('confirmation_decision')}`",
            "",
            "## Safety",
            f"`{report.get('safety')}`",
            "",
            "## Director note",
            "Read-only confirmation only. No wave, Shadow, paper, live, orders, IBKR, or DB writes.",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def _event_from_row(
    row: dict[str, Any],
    *,
    run_id: int,
    pattern_key: str,
    feature_frame: pd.DataFrame | None,
) -> CandidateEvent:
    entry_ts = _string_or_none(row.get("entry_ts") or row.get("window_end_ts") or row.get("window_end"))
    side = str(row.get("side") or "long")
    forward_end = _string_or_none(row.get("exit_ts") or row.get("forward_end") or row.get("forward_end_ts"))
    entry_price = _float_or_none(row.get("entry_price"))
    if entry_price is None and feature_frame is not None:
        entry_bar_for_price = _nearest_bar(feature_frame, entry_ts)
        entry_price = _float_or_none(entry_bar_for_price.get("close")) if entry_bar_for_price is not None else None
    outcome_r = _float_or_none(row.get("outcome_r") or row.get("result_r"))
    entry_bar = _nearest_bar(feature_frame, entry_ts) if feature_frame is not None else None
    exit_bar = _nearest_bar(feature_frame, forward_end) if feature_frame is not None else None
    risk_proxy = _float_or_none(row.get("risk_proxy"))
    if risk_proxy is None:
        risk_proxy = _risk_proxy_from_frame(feature_frame, entry_ts, entry_price)
    if risk_proxy is None and entry_price is not None and outcome_r not in (None, 0.0) and exit_bar is not None:
        exit_close = _float_or_none(exit_bar.get("close"))
        if exit_close is not None:
            risk_proxy = abs((exit_close - entry_price) / outcome_r)
    mfe_r, mae_r = _mfe_mae(feature_frame, entry_ts, forward_end, entry_price, risk_proxy)
    vwap_at_entry = _float_or_none(entry_bar.get("vwap")) if entry_bar is not None else None
    price_vs_vwap_bps = None
    if entry_price is not None and vwap_at_entry not in (None, 0.0):
        price_vs_vwap_bps = round((entry_price / vwap_at_entry - 1.0) * 10_000.0, 5)
    data_quality = "reconstructed" if feature_frame is not None else "example_only"
    if risk_proxy is None:
        data_quality = f"{data_quality}_missing_risk_proxy"
    return CandidateEvent(
        run_id=int(row.get("run_id") or run_id),
        pattern_key=str(row.get("pattern_key") or pattern_key),
        candidate_id=_int_or_none(row.get("candidate_id")),
        pattern_id=_int_or_none(row.get("pattern_id")),
        side=side,
        symbol=str(row.get("symbol") or "").upper(),
        timeframe=str(row.get("timeframe") or "30m"),
        window_size=_int_or_none(row.get("window_size")),
        window_start=_string_or_none(row.get("window_start_ts") or row.get("window_start")),
        window_end=_string_or_none(row.get("window_end_ts") or row.get("window_end")),
        entry_ts=entry_ts,
        entry_price=entry_price,
        risk_proxy=risk_proxy,
        outcome_r=outcome_r,
        mfe_r=mfe_r,
        mae_r=mae_r,
        forward_end=forward_end,
        split=_string_or_none(row.get("split")),
        execution_cost_r=_float_or_none(row.get("execution_cost_r")),
        vwap_at_entry=vwap_at_entry,
        price_vs_vwap_bps=price_vs_vwap_bps,
        vwap_slope_bps=_float_or_none(entry_bar.get("vwap_slope_bps")) if entry_bar is not None else None,
        session_bucket=_string_or_none(row.get("session_bucket") or (entry_bar or {}).get("session_bucket")),
        month=_string_or_none(row.get("month") or (entry_ts or "")[:7]),
        source=str(row.get("source") or "example"),
        data_quality=data_quality,
        raw=row,
    )


def _simulate_overlay(event: CandidateEvent, overlay: str, feature_frame: pd.DataFrame | None) -> dict[str, Any]:
    if feature_frame is None or event.entry_ts is None or event.entry_price is None or event.risk_proxy in (None, 0.0):
        return _outcome_row(event, None, "not_computable_missing_event_data", None, None)
    window = _event_window(feature_frame, event.entry_ts, event.forward_end)
    if window.empty:
        return _outcome_row(event, None, "not_computable_empty_window", None, None)
    exit_reason = "time_stop"
    exit_r: float | None = None
    rows_after_entry = window.iloc[1:] if len(window) > 1 else window.iloc[0:0]
    if overlay in {
        "exit_on_vwap_loss",
        "exit_on_close_below_vwap_after_entry",
        "exit_on_vwap_loss_or_time_stop",
        "exit_on_vwap_loss_or_4R_takeprofit",
    }:
        for _, bar in rows_after_entry.iterrows():
            if overlay == "exit_on_vwap_loss_or_4R_takeprofit":
                high = _float_or_none(bar.get("high"))
                target_price = event.entry_price + _side_multiplier(event.side) * 4.0 * event.risk_proxy
                target_hit = high is not None and high >= target_price
                if _side_multiplier(event.side) < 0:
                    low = _float_or_none(bar.get("low"))
                    target_hit = low is not None and low <= target_price
                if target_hit:
                    exit_r = _round(4.0 - (event.execution_cost_r or 0.0))
                    exit_reason = "takeprofit_4r"
                    break
            if _vwap_loss_bar(bar, event.side):
                exit_r = _price_to_r(_float_or_none(bar.get("close")), event)
                exit_reason = "vwap_loss"
                break
    elif overlay == "exit_on_failed_reclaim":
        first_two = rows_after_entry.head(2)
        for _, bar in first_two.iterrows():
            if not _favorable_vwap_bar(bar, event.side):
                exit_r = _price_to_r(_float_or_none(bar.get("close")), event)
                exit_reason = "failed_reclaim_n2"
                break
    if exit_r is None:
        exit_r = _price_to_r(_float_or_none(window.iloc[-1].get("close")), event)
    mfe_r, mae_r = _mfe_mae_from_window(window, event.entry_price, event.risk_proxy)
    return _outcome_row(event, exit_r, exit_reason, mfe_r, mae_r)


def _metrics_for_overlay(name: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    values = [row["outcome_r"] for row in rows if row.get("outcome_r") is not None]
    wins = [value for value in values if value > 0]
    losses = [value for value in values if value < 0]
    symbols = [row.get("symbol") for row in rows if row.get("symbol")]
    months = [row.get("month") for row in rows if row.get("month")]
    result = {
        "overlay": name,
        "sample_count": len(rows),
        "computable_count": len(values),
        "expectancy_r": _round(mean(values)) if values else None,
        "profit_factor": _profit_factor(wins, losses),
        "win_rate": _round(len(wins) / len(values)) if values else None,
        "max_drawdown_r": _round(_max_drawdown(values)) if values else None,
        "median_r": _round(median(values)) if values else None,
        "p10_r": _quantile(values, 0.10),
        "p90_r": _quantile(values, 0.90),
        "avg_mfe_r": _round(mean([row["mfe_r"] for row in rows if row.get("mfe_r") is not None]))
        if any(row.get("mfe_r") is not None for row in rows)
        else None,
        "avg_mae_r": _round(mean([row["mae_r"] for row in rows if row.get("mae_r") is not None]))
        if any(row.get("mae_r") is not None for row in rows)
        else None,
        "oos_expectancy_r": _split_expectancy(rows, "holdout"),
        "oos_profit_factor": _split_profit_factor(rows, "holdout"),
        "symbol_count": len(set(symbols)),
        "month_count": len(set(months)),
        "concentration_top_symbol_pct": _top_concentration(symbols),
        "concentration_top_month_pct": _top_concentration(months),
        "event_outcomes": rows,
    }
    result["decision_eligible"] = _decision_eligible(result)
    return result


def _decision_eligible(row: dict[str, Any]) -> bool:
    return (
        row.get("overlay") != "baseline_existing"
        and (row.get("max_drawdown_r") is not None and row["max_drawdown_r"] <= 12.0)
        and (row.get("expectancy_r") is not None and row["expectancy_r"] > 0.0)
        and (row.get("profit_factor") is not None and row["profit_factor"] > 1.2)
        and row.get("symbol_count", 0) >= 6
        and (row.get("concentration_top_symbol_pct") or 1.0) <= 0.5
        and (row.get("concentration_top_month_pct") or 1.0) <= 0.5
    )


def _load_artifact_events(evidence_json: str | Path, *, run_id: int, pattern_key: str) -> list[dict[str, Any]]:
    evidence_path = Path(evidence_json)
    payload_path = evidence_path.parent / "evidence_payloads" / f"run_{run_id}" / f"candidate_{pattern_key}.jsonl"
    if not payload_path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with payload_path.open(encoding="utf-8") as handle:
        for line in handle:
            text = line.strip()
            if text:
                rows.append(json.loads(text))
    return rows


def _load_ledger_events(
    *,
    forensics_json: str | Path,
    run_id: int,
    pattern_key: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    ledger_path = _default_ledger_path(forensics_json, run_id=run_id, pattern_key=pattern_key)
    status: dict[str, Any] = {"attempted": True, "path": str(ledger_path), "row_count": 0, "sha256": None, "error": None}
    if not ledger_path.exists():
        status["error"] = "ledger_not_found"
        return [], status
    try:
        compressed = ledger_path.read_bytes()
        payload = gzip.decompress(compressed)
        status["sha256"] = hashlib.sha256(payload).hexdigest()
        ledger = json.loads(payload.decode("utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        status["error"] = f"ledger_read_failed:{exc.__class__.__name__}"
        return [], status
    if int(ledger.get("run_id") or -1) != int(run_id) or str(ledger.get("pattern_key")) != pattern_key:
        status["error"] = "ledger_scope_mismatch"
        return [], status
    rows = []
    for event in ledger.get("events") or []:
        if not isinstance(event, dict):
            continue
        rows.append(
            {
                **event,
                "run_id": run_id,
                "pattern_key": pattern_key,
                "side": event.get("side") or ledger.get("side"),
                "timeframe": ledger.get("timeframe"),
                "window_size": ledger.get("window_size"),
                "entry_ts": event.get("window_end"),
                "window_end": event.get("window_end"),
                "outcome_r": event.get("result_r"),
                "source": "event_ledger",
            }
        )
    status["row_count"] = len(rows)
    status["event_count_declared"] = _int_or_none(ledger.get("event_count"))
    return rows, status


def _default_ledger_path(forensics_json: str | Path, *, run_id: int, pattern_key: str) -> Path:
    root = Path(forensics_json).resolve()
    for parent in root.parents:
        candidate = parent / "reports" / "research" / "event_ledgers" / f"run_{run_id}" / f"{pattern_key}.json.gz"
        if candidate.exists():
            return candidate
    return (
        Path("/home/vboxuser/tradeo-worktrees/research-vwap-reclaim-wave-20260702")
        / "reports"
        / "research"
        / "event_ledgers"
        / f"run_{run_id}"
        / f"{pattern_key}.json.gz"
    )


def _load_db_events(*, run_id: int, pattern_key: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    status: dict[str, Any] = {"attempted": True, "row_count": 0, "error": None}
    try:
        from sqlalchemy import text

        from tradeo.db.session import SessionLocal
    except Exception as exc:  # pragma: no cover - depends on runtime DB stack
        status["error"] = f"db_import_failed:{exc.__class__.__name__}"
        return [], status

    statement = text(
        """
        SELECT
            p.id AS pattern_id,
            p.run_id AS run_id,
            p.pattern_key AS pattern_key,
            p.side AS side,
            p.timeframe AS pattern_timeframe,
            p.window_size AS window_size,
            e.id AS example_id,
            e.symbol AS symbol,
            e.timeframe AS timeframe,
            e.window_start AS window_start,
            e.window_end AS window_end,
            e.forward_end AS forward_end,
            e.entry_price AS entry_price,
            e.risk_proxy AS risk_proxy,
            e.outcome_r AS outcome_r,
            e.mfe_r AS mfe_r,
            e.mae_r AS mae_r,
            e.chart_json AS chart_json,
            e.features_json AS features_json
        FROM discovered_patterns p
        JOIN discovered_pattern_examples e ON e.pattern_id = p.id
        WHERE p.run_id = :run_id
          AND p.pattern_key = :pattern_key
        ORDER BY e.id ASC
        """
    )
    try:
        with SessionLocal() as db:
            result = db.execute(statement, {"run_id": int(run_id), "pattern_key": pattern_key})
            rows = [_db_row_to_event(row._mapping) for row in result]
            status["row_count"] = len(rows)
            return rows, status
    except Exception as exc:  # pragma: no cover - exercised only with live DB
        status["error"] = f"db_read_failed:{exc.__class__.__name__}"
        return [], status


def _db_row_to_event(row: Any) -> dict[str, Any]:
    features = _json_dict(row.get("features_json"))
    chart = _json_dict(row.get("chart_json"))
    return {
        "run_id": row.get("run_id"),
        "pattern_key": row.get("pattern_key"),
        "candidate_id": row.get("pattern_id"),
        "pattern_id": row.get("pattern_id"),
        "symbol": row.get("symbol"),
        "timeframe": row.get("timeframe") or row.get("pattern_timeframe"),
        "window_size": row.get("window_size"),
        "window_start": row.get("window_start"),
        "window_end": row.get("window_end"),
        "entry_ts": features.get("entry_ts") or row.get("window_end"),
        "exit_ts": features.get("exit_ts") or row.get("forward_end"),
        "forward_end": row.get("forward_end"),
        "entry_price": row.get("entry_price"),
        "exit_price": features.get("exit_price") or chart.get("exit_price"),
        "risk_proxy": row.get("risk_proxy"),
        "outcome_r": row.get("outcome_r"),
        "mfe_r": row.get("mfe_r"),
        "mae_r": row.get("mae_r"),
        "split": features.get("split") or chart.get("split"),
        "session_bucket": features.get("session_bucket"),
        "month": features.get("month") or str(row.get("window_end") or "")[:7],
        "source": "db",
    }


def _deduplicate_events(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    selected: dict[tuple[Any, ...], dict[str, Any]] = {}
    for row in rows:
        key = (
            row.get("pattern_key"),
            row.get("symbol"),
            row.get("entry_ts") or row.get("window_end_ts") or row.get("window_end"),
            row.get("window_start_ts") or row.get("window_start"),
        )
        if key not in selected or selected[key].get("source") != "db":
            selected[key] = row
    return list(selected.values())


def _json_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            decoded = json.loads(value)
        except json.JSONDecodeError:
            return {}
        return decoded if isinstance(decoded, dict) else {}
    return {}


def _load_feature_frame(cache_dir: Path, *, symbol: str, timeframe: str) -> pd.DataFrame | None:
    if not symbol:
        return None
    paths = sorted(cache_dir.glob(f"{symbol}_{timeframe}_*.csv"))
    if not paths:
        return None
    bars = pd.read_csv(paths[0])
    try:
        return build_intraday_vwap_features(bars, timestamp_column="timestamp").frame
    except (KeyError, ValueError, pd.errors.ParserError):
        return None


def _risk_proxy_from_frame(frame: pd.DataFrame | None, entry_ts: str | None, entry_price: float | None) -> float | None:
    if frame is None or entry_ts is None or entry_price is None:
        return None
    target = _to_ny_timestamp(entry_ts)
    try:
        pos = frame.index.get_indexer([target], method="nearest")[0]
    except (KeyError, TypeError, ValueError):
        return None
    if pos < 0:
        return None
    atr_series = atr(frame.reset_index(), 14).bfill().fillna(frame["close"] * 0.015)
    atr_value = _float_or_none(atr_series.iloc[int(pos)])
    if atr_value is None:
        return None
    return max(atr_value * 1.5, entry_price * 0.015, 0.01)


def _feature_frame_from_event(event: CandidateEvent) -> pd.DataFrame | None:
    raw_frame = event.raw.get("_feature_frame")
    return raw_frame if isinstance(raw_frame, pd.DataFrame) else None


def _nearest_bar(frame: pd.DataFrame | None, timestamp: str | None) -> dict[str, Any] | None:
    if frame is None or not timestamp:
        return None
    target = pd.Timestamp(timestamp)
    if target.tzinfo is None:
        target = target.tz_localize("America/New_York")
    else:
        target = target.tz_convert("America/New_York")
    try:
        pos = frame.index.get_indexer([target], method="nearest")[0]
    except (KeyError, TypeError, ValueError):
        return None
    if pos < 0:
        return None
    return frame.iloc[int(pos)].to_dict()


def _event_window(frame: pd.DataFrame, entry_ts: str, forward_end: str | None) -> pd.DataFrame:
    start = _to_ny_timestamp(entry_ts)
    end = _to_ny_timestamp(forward_end) if forward_end else None
    if end is None:
        return frame.loc[frame.index >= start]
    return frame.loc[(frame.index >= start) & (frame.index <= end)]


def _mfe_mae(
    frame: pd.DataFrame | None,
    entry_ts: str | None,
    forward_end: str | None,
    entry_price: float | None,
    risk_proxy: float | None,
) -> tuple[float | None, float | None]:
    if frame is None or entry_ts is None or entry_price is None or risk_proxy in (None, 0.0):
        return None, None
    return _mfe_mae_from_window(_event_window(frame, entry_ts, forward_end), entry_price, risk_proxy)


def _mfe_mae_from_window(
    window: pd.DataFrame,
    entry_price: float | None,
    risk_proxy: float | None,
) -> tuple[float | None, float | None]:
    if window.empty or entry_price is None or risk_proxy in (None, 0.0):
        return None, None
    high = pd.to_numeric(window["high"], errors="coerce").max()
    low = pd.to_numeric(window["low"], errors="coerce").min()
    return _round((float(high) - entry_price) / risk_proxy), _round((float(low) - entry_price) / risk_proxy)


def _price_to_r(price: float | None, event: CandidateEvent) -> float | None:
    if price is None or event.entry_price is None or event.risk_proxy in (None, 0.0):
        return None
    gross = _side_multiplier(event.side) * (price - event.entry_price) / event.risk_proxy
    return _round(gross - (event.execution_cost_r or 0.0))


def _outcome_row(
    event: CandidateEvent,
    outcome_r: float | None,
    exit_reason: str,
    mfe_r: float | None,
    mae_r: float | None,
) -> dict[str, Any]:
    return {
        "run_id": event.run_id,
        "pattern_key": event.pattern_key,
        "symbol": event.symbol,
        "month": event.month,
        "entry_ts": event.entry_ts,
        "split": event.split,
        "outcome_r": _round(outcome_r),
        "exit_reason": exit_reason,
        "mfe_r": _round(mfe_r),
        "mae_r": _round(mae_r),
        "data_quality": event.data_quality,
    }


def _event_dataset_summary(events: list[CandidateEvent], *, expected_sample_count: Any) -> dict[str, Any]:
    qualities: dict[str, int] = {}
    for event in events:
        qualities[event.data_quality] = qualities.get(event.data_quality, 0) + 1
    return {
        "event_count": len(events),
        "expected_sample_count": _int_or_none(expected_sample_count),
        "data_completeness": qualities,
        "events": [_event_to_dict(event) for event in events],
    }


def _event_to_dict(event: CandidateEvent) -> dict[str, Any]:
    return {field: getattr(event, field) for field in event.__dataclass_fields__ if field != "raw"}


def _side_multiplier(side: str | None) -> int:
    return -1 if str(side or "").lower() == "short" else 1


def _favorable_vwap_bar(bar: Any, side: str | None) -> bool:
    return bool(bar.get("below_vwap")) if _side_multiplier(side) < 0 else bool(bar.get("above_vwap"))


def _vwap_loss_bar(bar: Any, side: str | None) -> bool:
    return bool(bar.get("above_vwap")) if _side_multiplier(side) < 0 else bool(bar.get("below_vwap"))


def _split_expectancy(rows: list[dict[str, Any]], split: str) -> float | None:
    values = [
        row["outcome_r"]
        for row in rows
        if row.get("outcome_r") is not None and str(row.get("split") or "").lower() == split
    ]
    return _round(mean(values)) if values else None


def _split_profit_factor(rows: list[dict[str, Any]], split: str) -> float | None:
    values = [
        row["outcome_r"]
        for row in rows
        if row.get("outcome_r") is not None and str(row.get("split") or "").lower() == split
    ]
    wins = [value for value in values if value > 0]
    losses = [value for value in values if value < 0]
    return _profit_factor(wins, losses)


def _candidate_metadata(
    forensics: dict[str, Any],
    evidence: dict[str, Any],
    *,
    run_id: int,
    pattern_key: str,
) -> dict[str, Any]:
    rows = list(forensics.get("candidate_forensics") or []) + list(evidence.get("candidate_manifests") or [])
    selected = next(
        (
            row
            for row in rows
            if int(row.get("run_id") or -1) == int(run_id) and str(row.get("pattern_key")) == pattern_key
        ),
        {},
    )
    return {
        "run_id": run_id,
        "pattern_key": pattern_key,
        "side": selected.get("side"),
        "timeframe": selected.get("timeframe"),
        "window_size": selected.get("window_size"),
        "sample_count": selected.get("sample_count"),
        "symbol_count": selected.get("symbol_count"),
        "expectancy_r": selected.get("expectancy_r"),
        "profit_factor": selected.get("profit_factor"),
        "oos_expectancy_r": selected.get("oos_expectancy_r"),
        "oos_profit_factor": selected.get("oos_profit_factor"),
        "drawdown_r": selected.get("drawdown_r"),
        "rejection_reasons": selected.get("rejection_reasons") or [],
    }


def _scope_integrity(
    wave: dict[str, Any],
    forensics: dict[str, Any],
    evidence: dict[str, Any],
    *,
    run_id: int,
) -> dict[str, Any]:
    manifest_ids = _run_ids_from_wave(wave)
    forensics_ids = sorted(int(item) for item in ((forensics.get("scope") or {}).get("run_ids") or []))
    evidence_ids = sorted(int(item) for item in ((evidence.get("scope") or {}).get("run_ids") or []))
    return {
        "exact_scope": bool(run_id in manifest_ids and set(forensics_ids or manifest_ids) <= set(manifest_ids)),
        "run_id_in_scope": int(run_id) in set(manifest_ids),
        "manifest_run_ids": manifest_ids,
        "forensics_run_ids": forensics_ids,
        "evidence_run_ids": evidence_ids,
    }


def _run_ids_from_wave(wave: dict[str, Any]) -> list[int]:
    rows = (((wave.get("research_result") or {}).get("details") or {}).get("runs") or [])
    return sorted({int(row["run_id"]) for row in rows if row.get("run_id") is not None})


def _read_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _to_ny_timestamp(value: str | None) -> pd.Timestamp:
    ts = pd.Timestamp(value)
    if ts.tzinfo is None:
        return ts.tz_localize("America/New_York")
    return ts.tz_convert("America/New_York")


def _profit_factor(wins: list[float], losses: list[float]) -> float | None:
    if not wins and not losses:
        return None
    loss_total = abs(sum(losses))
    if loss_total == 0:
        return None
    return _round(sum(wins) / loss_total)


def _max_drawdown(values: list[float]) -> float:
    equity = 0.0
    peak = 0.0
    drawdown = 0.0
    for value in values:
        equity += value
        peak = max(peak, equity)
        drawdown = max(drawdown, peak - equity)
    return drawdown


def _quantile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    series = pd.Series(values)
    return _round(float(series.quantile(q)))


def _top_concentration(values: list[str | None]) -> float | None:
    clean = [value for value in values if value]
    if not clean:
        return None
    counts: dict[str, int] = {}
    for value in clean:
        counts[value] = counts.get(value, 0) + 1
    return _round(max(counts.values()) / len(clean))


def _float_or_none(value: Any) -> float | None:
    if value in (None, "", "not_available"):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _int_or_none(value: Any) -> int | None:
    if value in (None, "", "not_available"):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _string_or_none(value: Any) -> str | None:
    if value in (None, "", "not_available"):
        return None
    return str(value)


def _round(value: float | None) -> float | None:
    if value is None:
        return None
    number = float(value)
    if not math.isfinite(number):
        return None
    return round(number, 5)
