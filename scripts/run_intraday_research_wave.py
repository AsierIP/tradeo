#!/usr/bin/env python3
from __future__ import annotations

import argparse
from dataclasses import asdict
from hashlib import sha256
import json
import os
from pathlib import Path
import sys
import time
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from tradeo.core.config import get_settings  # noqa: E402
from tradeo.services.data_provider import UNIVERSE_POLICY_CHOICES, normalize_universe_policy  # noqa: E402
from tradeo.services.intraday_research_readiness import (  # noqa: E402
    IntradayResearchReadinessGate,
    IntradayResearchWaveSpec,
)
from tradeo.tasks import worker  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run an intraday research wave only if cache/data readiness passes."
    )
    parser.add_argument("--execute", action="store_true", help="Actually run scouting after readiness passes.")
    parser.add_argument("--allow-recent-duplicates", action="store_true")
    parser.add_argument(
        "--store-rejected",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Persist rejected/near-miss candidates during --execute diagnostic scouting. Default: true.",
    )
    parser.add_argument("--universe-file", default=None)
    parser.add_argument(
        "--product-policy",
        "--universe-policy",
        dest="product_policy",
        choices=UNIVERSE_POLICY_CHOICES,
        default=None,
        help="Universe product policy label. Defaults to settings.",
    )
    parser.add_argument("--period", default=None)
    parser.add_argument("--timeframes", default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--window-sizes", default=None)
    parser.add_argument("--forward-bars", default=None)
    parser.add_argument("--max-total-windows", type=int, default=None)
    parser.add_argument("--max-windows-per-symbol", type=int, default=None)
    parser.add_argument("--min-cache-coverage", type=float, default=0.90)
    parser.add_argument("--min-rows-per-symbol", type=int, default=1)
    parser.add_argument("--manifest-path", default=None)
    parser.add_argument("--json-only", action="store_true")
    args = parser.parse_args()

    _apply_settings_env_overrides(args)
    settings = get_settings()
    product_policy = normalize_universe_policy(
        args.product_policy or getattr(settings, "intraday_universe_policy", "stock_only")
    )
    spec = IntradayResearchWaveSpec.from_settings(
        settings,
        universe_file=args.universe_file,
        universe_policy=product_policy,
        period=args.period,
        timeframes=tuple(_csv_str(args.timeframes)) if args.timeframes else None,
        limit=args.limit,
        window_sizes=tuple(_csv_int(args.window_sizes)) if args.window_sizes else None,
        forward_bars=tuple(_csv_int(args.forward_bars)) if args.forward_bars else None,
        max_total_windows=args.max_total_windows,
        max_windows_per_symbol=args.max_windows_per_symbol,
        min_cache_coverage=args.min_cache_coverage,
        min_rows_per_symbol=args.min_rows_per_symbol,
    )
    gate = IntradayResearchReadinessGate(settings=settings)
    readiness = gate.evaluate(spec)
    readiness_spec = _execution_spec_from_wave_spec(spec, store_rejected=bool(args.store_rejected))
    execution_spec = _execution_spec_from_settings(settings, store_rejected=bool(args.store_rejected))
    readiness_spec_hash = _stable_spec_hash(readiness_spec)
    execution_spec_hash = _stable_spec_hash(execution_spec)
    specs_match = readiness_spec_hash == execution_spec_hash
    wave_result: dict[str, Any] = {
        "schema_version": 1,
        "mode": "execute" if args.execute else "dry_run",
        "readiness": readiness.manifest,
        "execution_spec": execution_spec,
        "readiness_spec_hash": readiness_spec_hash,
        "execution_spec_hash": execution_spec_hash,
        "specs_match": specs_match,
        "research_result": None,
    }
    status_code = 0
    if not readiness.ready:
        wave_result["decision"] = "blocked_data_missing"
        status_code = 2
    elif not args.execute:
        wave_result["decision"] = "ready_dry_run"
    elif not specs_match:
        wave_result["decision"] = "blocked_spec_mismatch"
        wave_result["spec_mismatch"] = {
            "readiness_spec": readiness_spec,
            "execution_spec": execution_spec,
        }
        status_code = 3
    else:
        started = time.monotonic()
        result = worker._run_intraday_research_process_pool(
            settings,
            allow_recent_duplicates=bool(args.allow_recent_duplicates),
            store_rejected=bool(args.store_rejected),
        )
        wave_result["research_result"] = result
        wave_result["elapsed_wall_s"] = round(time.monotonic() - started, 3)
        wave_result["decision"] = "executed"
        status_code = 0 if result.get("status") in {"ok", "degraded"} else 1

    manifest_hash = readiness.manifest_hash
    manifest_path = Path(
        args.manifest_path
        or settings.artifacts_path
        / "runtime"
        / f"intraday_research_wave_{manifest_hash[:12]}.json"
    )
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(wave_result, indent=2, sort_keys=True, default=str), encoding="utf-8")
    summary = {
        "decision": wave_result["decision"],
        "manifest_path": str(manifest_path),
        "ready": readiness.ready,
        "coverage": readiness.coverage,
        "ok": readiness.ok,
        "total": readiness.total,
        "execute": bool(args.execute),
        "execution_spec": execution_spec,
        "readiness_spec_hash": readiness_spec_hash,
        "execution_spec_hash": execution_spec_hash,
        "specs_match": specs_match,
        "product_policy": product_policy,
        "research_status": (wave_result.get("research_result") or {}).get("status"),
        "store_rejected": bool(args.store_rejected) if args.execute else None,
    }
    if not args.json_only:
        print(
            f"decision={summary['decision']} ready={summary['ready']} "
            f"coverage={summary['coverage']:.2%} ok={summary['ok']}/{summary['total']} "
            f"manifest={manifest_path}"
        )
        print("JSON:")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return status_code


def _csv_str(raw: str) -> list[str]:
    return [item.strip() for item in str(raw).split(",") if item.strip()]


def _csv_int(raw: str) -> list[int]:
    return [int(item.strip()) for item in str(raw).split(",") if item.strip()]


def _apply_settings_env_overrides(args: argparse.Namespace) -> None:
    changed = False
    if args.universe_file:
        os.environ["TRADEO_INTRADAY_UNIVERSE_FILE"] = str(args.universe_file)
        changed = True
    if args.product_policy:
        os.environ["TRADEO_INTRADAY_UNIVERSE_POLICY"] = str(args.product_policy)
        changed = True
    if args.period:
        os.environ["TRADEO_INTRADAY_RESEARCH_PERIOD"] = str(args.period)
        changed = True
    if args.timeframes:
        os.environ["TRADEO_INTRADAY_TIMEFRAMES"] = str(args.timeframes)
        changed = True
    if args.limit is not None:
        os.environ["TRADEO_INTRADAY_RESEARCH_LIMIT_DEFAULT"] = str(args.limit)
        changed = True
    if args.window_sizes:
        os.environ["TRADEO_INTRADAY_RESEARCH_WINDOW_SIZES"] = str(args.window_sizes)
        changed = True
    if args.forward_bars:
        os.environ["TRADEO_INTRADAY_RESEARCH_FORWARD_BARS"] = str(args.forward_bars)
        changed = True
    if args.max_total_windows is not None:
        os.environ["TRADEO_INTRADAY_RESEARCH_MAX_TOTAL_WINDOWS"] = str(args.max_total_windows)
        changed = True
    if args.max_windows_per_symbol is not None:
        os.environ["TRADEO_INTRADAY_RESEARCH_MAX_WINDOWS_PER_SYMBOL"] = str(args.max_windows_per_symbol)
        changed = True
    if changed:
        _clear_settings_cache()


def _clear_settings_cache() -> None:
    cache_clear = getattr(get_settings, "cache_clear", None)
    if callable(cache_clear):
        get_settings.cache_clear()


def _execution_spec_from_wave_spec(
    spec: IntradayResearchWaveSpec, *, store_rejected: bool
) -> dict[str, Any]:
    raw = asdict(spec)
    return _normalize_execution_spec(
        {
            "universe_file": raw["universe_file"],
            "product_policy": raw["universe_policy"],
            "period": raw["period"],
            "timeframes": raw["timeframes"],
            "limit": raw["limit"],
            "window_sizes": raw["window_sizes"],
            "forward_bars": raw["forward_bars"],
            "max_total_windows": raw["max_total_windows"],
            "max_windows_per_symbol": raw["max_windows_per_symbol"],
            "store_rejected": store_rejected,
        }
    )


def _execution_spec_from_settings(settings: Any, *, store_rejected: bool) -> dict[str, Any]:
    return _normalize_execution_spec(
        {
            "universe_file": str(settings.intraday_universe_file),
            "product_policy": normalize_universe_policy(
                getattr(settings, "intraday_universe_policy", "stock_only")
            ),
            "period": str(settings.intraday_research_period),
            "timeframes": tuple(settings.intraday_timeframe_list),
            "limit": int(settings.intraday_research_limit_default),
            "window_sizes": tuple(settings.intraday_research_window_size_list),
            "forward_bars": tuple(settings.intraday_research_forward_bar_list),
            "max_total_windows": int(settings.intraday_research_max_total_windows),
            "max_windows_per_symbol": int(settings.intraday_research_max_windows_per_symbol),
            "store_rejected": store_rejected,
        }
    )


def _normalize_execution_spec(spec: dict[str, Any]) -> dict[str, Any]:
    return {
        "universe_file": str(spec["universe_file"]),
        "product_policy": normalize_universe_policy(str(spec["product_policy"])),
        "period": str(spec["period"]),
        "timeframes": [str(item) for item in spec["timeframes"]],
        "limit": int(spec["limit"]),
        "window_sizes": [int(item) for item in spec["window_sizes"]],
        "forward_bars": [int(item) for item in spec["forward_bars"]],
        "max_total_windows": int(spec["max_total_windows"]),
        "max_windows_per_symbol": int(spec["max_windows_per_symbol"]),
        "store_rejected": bool(spec["store_rejected"]),
    }


def _stable_spec_hash(spec: dict[str, Any]) -> str:
    return sha256(json.dumps(spec, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


if __name__ == "__main__":
    raise SystemExit(main())
