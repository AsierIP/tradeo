#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json

FAMILIES = [
    ("5m", "20", "raw_edge_short_w20"),
    ("15m", "100", "normal_long_w100"),
    ("15m", "20", "oos_positive_w20"),
    ("15m", "50", "wf_positive_w50"),
]


def main() -> int:
    p = argparse.ArgumentParser(description="Print quality-first intraday scouting commands.")
    p.add_argument("--periods", default="30d,60d")
    p.add_argument("--limits", default="60,60")
    p.add_argument("--families", default="")
    p.add_argument("--json-only", action="store_true")
    args = p.parse_args()
    periods = [x.strip() for x in args.periods.split(",") if x.strip()]
    limits = [int(x.strip()) for x in args.limits.split(",") if x.strip()]
    if len(limits) == 1:
        limits = limits * len(periods)
    families = parse_families(args.families) if args.families else FAMILIES
    waves = []
    for period, limit in zip(periods, limits, strict=True):
        for timeframe, window, reason in families:
            waves.append(make_wave(period, limit, timeframe, window, reason))
    payload = {
        "policy": "no bajar filtros; confirmar familias con mas simbolos/historico y menos hipotesis por run",
        "waves": waves,
    }
    if not args.json_only:
        for i, wave in enumerate(waves, 1):
            print(f"\n[{i}] {wave['name']} - {wave['reason']}")
            print("warmup:")
            print(wave["warmup"])
            print("scouting:")
            print(wave["scouting"])
            print("diagnostic:")
            print(wave["diagnostic"])
        print("\nJSON:")
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def parse_families(raw: str) -> list[tuple[str, str, str]]:
    out = []
    for item in raw.split(","):
        parts = [p.strip() for p in item.split(":")]
        if len(parts) < 2:
            continue
        out.append((parts[0], parts[1], parts[2] if len(parts) > 2 else item.replace(":", "_")))
    return out


def make_wave(period: str, limit: int, timeframe: str, window: str, reason: str) -> dict[str, str | int]:
    mult = max(1, int(period.removesuffix("d")) // 30) if period.endswith("d") else 1
    total = min(80000, max(30000, 30000 * mult))
    per_symbol = min(2400, max(900, 900 * mult))
    common = "-e TRADEO_MARKET_DATA_CACHE_DIR=/app/artifacts/runtime/ohlcv_cache -e TRADEO_UNIVERSE_SNAPSHOT_DIR=/app/artifacts/runtime/universe_snapshots"
    warmup = (
        f"docker compose run --rm -T {common} -e TRADEO_MARKET_DATA_UPSTREAM_MAX_CONCURRENCY=1 "
        f"backend python /app/scripts/warm_intraday_cache_resilient.py --period {period} --limit {limit} --timeframes {timeframe} "
        "--timeout-s 45 --retries 1 --sleep-s 3 --retry-sleep-s 10 --max-failures 20"
    )
    scouting = (
        f"docker compose run --rm -T {common} "
        "-e TRADEO_INTRADAY_RESEARCH_REFRESH_MARKET_DATA_ENABLED=false "
        "-e TRADEO_DISCOVERY_STORE_REJECTED=true "
        f"-e TRADEO_INTRADAY_TIMEFRAMES={timeframe} "
        f"-e TRADEO_INTRADAY_RESEARCH_WINDOW_SIZES={window} "
        "-e TRADEO_INTRADAY_RESEARCH_PROCESS_WORKERS=10 "
        "-e TRADEO_INTRADAY_RESEARCH_NATIVE_THREADS_PER_PROCESS=1 "
        "-e TRADEO_INTRADAY_RESEARCH_PARALLEL_SYMBOL_CHUNKS=6 "
        "-e TRADEO_INTRADAY_RESEARCH_ADAPTIVE_CHUNKS=false "
        f"-e TRADEO_INTRADAY_RESEARCH_PERIOD={period} "
        f"-e TRADEO_INTRADAY_RESEARCH_LIMIT_DEFAULT={limit} "
        f"-e TRADEO_INTRADAY_RESEARCH_MAX_TOTAL_WINDOWS={total} "
        f"-e TRADEO_INTRADAY_RESEARCH_MAX_WINDOWS_PER_SYMBOL={per_symbol} "
        "backend python /app/scripts/run_intraday_scouting_process_pool.py --allow-recent-duplicates --store-rejected"
    )
    diagnostic = f"docker compose run --rm -T {common} backend python /app/scripts/diagnose_intraday_pattern_funnel.py --hours 96 --top 50"
    return {
        "name": f"{period}_{limit}s_{timeframe}_w{window}_{reason}",
        "period": period,
        "limit": limit,
        "timeframe": timeframe,
        "window": int(window),
        "reason": reason,
        "warmup": warmup,
        "scouting": scouting,
        "diagnostic": diagnostic,
    }


if __name__ == "__main__":
    raise SystemExit(main())
