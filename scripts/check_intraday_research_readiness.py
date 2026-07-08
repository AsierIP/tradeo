#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from tradeo.core.config import get_settings
from tradeo.research.intraday_context_filters import (
    BENCHMARK_REGIME_FILTER_CHOICES,
    normalize_context_filter_spec,
)
from tradeo.services.intraday_research_readiness import (
    IntradayResearchReadinessGate,
    IntradayResearchWaveSpec,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Check data readiness for an intraday research wave.")
    parser.add_argument("--universe-file", default=None)
    parser.add_argument("--period", default=None)
    parser.add_argument("--timeframes", default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--window-sizes", default=None)
    parser.add_argument("--forward-bars", default=None)
    parser.add_argument("--max-total-windows", type=int, default=None)
    parser.add_argument("--max-windows-per-symbol", type=int, default=None)
    parser.add_argument(
        "--benchmark-regime-filter",
        choices=sorted(BENCHMARK_REGIME_FILTER_CHOICES),
        default=None,
    )
    parser.add_argument("--benchmark-symbols", default=None)
    parser.add_argument("--min-cache-coverage", type=float, default=0.90)
    parser.add_argument("--min-rows-per-symbol", type=int, default=1)
    parser.add_argument("--manifest-path", default=None)
    parser.add_argument("--json-only", action="store_true")
    args = parser.parse_args()

    settings = get_settings()
    benchmark_spec = normalize_context_filter_spec(
        benchmark_regime_filter=args.benchmark_regime_filter,
        benchmark_symbols=args.benchmark_symbols,
    )
    spec = IntradayResearchWaveSpec.from_settings(
        settings,
        universe_file=args.universe_file,
        period=args.period,
        timeframes=tuple(_csv_str(args.timeframes)) if args.timeframes else None,
        limit=args.limit,
        window_sizes=tuple(_csv_int(args.window_sizes)) if args.window_sizes else None,
        forward_bars=tuple(_csv_int(args.forward_bars)) if args.forward_bars else None,
        max_total_windows=args.max_total_windows,
        max_windows_per_symbol=args.max_windows_per_symbol,
        min_cache_coverage=args.min_cache_coverage,
        min_rows_per_symbol=args.min_rows_per_symbol,
        benchmark_regime_filter=benchmark_spec.benchmark_regime_filter,
        benchmark_symbols=benchmark_spec.benchmark_symbols,
    )
    gate = IntradayResearchReadinessGate(settings=settings)
    result = gate.evaluate(spec)
    manifest_path = Path(
        args.manifest_path
        or settings.artifacts_path
        / "runtime"
        / f"intraday_research_readiness_{result.manifest_hash[:12]}.json"
    )
    gate.write_manifest(result, manifest_path)
    payload = {
        "status": result.status,
        "ready": result.ready,
        "coverage": result.coverage,
        "ok": result.ok,
        "total": result.total,
        "missing_or_bad": result.missing_or_bad,
        "manifest_hash": result.manifest_hash,
        "manifest_path": str(manifest_path),
        "missing_preview": result.manifest["missing_preview"],
        "spec": result.manifest["spec"],
    }
    if not args.json_only:
        print(
            f"readiness={result.status} ready={result.ready} coverage={result.coverage:.2%} "
            f"ok={result.ok}/{result.total} manifest={manifest_path}"
        )
        if result.missing_or_bad:
            print("missing_or_bad preview:")
            for row in payload["missing_preview"][:25]:
                print(f"- {row['symbol']} {row['timeframe']} {row['period']} {row['reason']} {row['path']}")
        print("JSON:")
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if result.ready else 2


def _csv_str(raw: str) -> list[str]:
    return [item.strip() for item in str(raw).split(",") if item.strip()]


def _csv_int(raw: str) -> list[int]:
    return [int(item.strip()) for item in str(raw).split(",") if item.strip()]


if __name__ == "__main__":
    raise SystemExit(main())
