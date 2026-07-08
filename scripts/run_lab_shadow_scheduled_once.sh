#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
CODE_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
RUNTIME_ROOT="${TRADEO_RUNTIME_ROOT:-/home/vboxuser/tradeo}"
ENV_FILE="${TRADEO_ENV_FILE:-${RUNTIME_ROOT}/.env}"
UNIVERSE_FILE="${TRADEO_SHADOW_UNIVERSE_FILE:-${RUNTIME_ROOT}/artifacts/runtime/universe_intraday_stock_only_v3.csv}"
OUTPUT_DIR="${TRADEO_SHADOW_OUTPUT_DIR:-${CODE_ROOT}/artifacts/runtime/lab_shadow}"
LIMIT="${TRADEO_SHADOW_LIMIT:-20}"
TIMEFRAME="${TRADEO_SHADOW_TIMEFRAME:-1m}"
CONDITIONS="${TRADEO_SHADOW_CONDITIONS:-vwap_reclaim_long:long,vwap_reject_short:short}"
INTERVAL_SECONDS="${TRADEO_SHADOW_INTERVAL_SECONDS:-60}"
MAX_ITERATIONS="${TRADEO_SHADOW_MAX_ITERATIONS:-1}"
TODAY="$(TZ=America/New_York date +%Y%m%d)"

if [[ "${TRADEO_SHADOW_REQUIRE_NY_SESSION:-false}" =~ ^(1|true|yes|on)$ ]]; then
  ny_iso="$(TZ=America/New_York date --iso-8601=seconds)"
  ny_dow="$(TZ=America/New_York date +%u)"
  ny_hm="$(TZ=America/New_York date +%H%M)"
  if (( ny_dow > 5 || 10#$ny_hm < 930 || 10#$ny_hm >= 1600 )); then
    echo "skipped_outside_ny_session now=${ny_iso} window=Mon-Fri_09:30-16:00_America/New_York"
    exit 0
  fi
fi

python3 - "$ENV_FILE" <<'PY'
from pathlib import Path
import sys

env_path = Path(sys.argv[1])
required = {
    "TRADEO_IBKR_READONLY": "true",
    "TRADEO_INTRADAY_PAPER_ENABLED": "false",
    "TRADEO_INTRADAY_LIVE_ENABLED": "false",
    "TRADEO_LABORATORY_AUTO_SUBMIT_PAPER_ORDERS": "false",
    "TRADEO_LABORATORY_ALLOW_WATCHLIST_PAPER_ORDERS": "false",
    "TRADEO_IBKR_ALLOW_MARKET_ORDERS": "false",
    "TRADEO_LIVE_TRADING_ENABLED": "false",
}
values: dict[str, str] = {}
for line in env_path.read_text(encoding="utf-8").splitlines():
    raw = line.strip()
    if not raw or raw.startswith("#") or "=" not in line:
        continue
    key, value = line.split("=", 1)
    values[key.strip()] = value.strip()
bad = {key: values.get(key) for key, expected in required.items() if values.get(key) != expected}
if bad:
    print(f"unsafe runtime flags: {sorted(bad)}", file=sys.stderr)
    raise SystemExit(2)
PY

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

cd "$CODE_ROOT"
python3 scripts/check_tradeo_operability.py --env-file "$ENV_FILE" --json-only >/dev/null

python3 scripts/run_vwap_shadow_loop.py \
  --universe-file "$UNIVERSE_FILE" \
  --limit "$LIMIT" \
  --conditions "$CONDITIONS" \
  --timeframe "$TIMEFRAME" \
  --interval-seconds "$INTERVAL_SECONDS" \
  --max-iterations "$MAX_ITERATIONS" \
  --jsonl-out "${OUTPUT_DIR}/scheduled_shadow_${TODAY}.jsonl" \
  --summary-json "${OUTPUT_DIR}/scheduled_shadow_latest.json" \
  --summary-md "${OUTPUT_DIR}/scheduled_shadow_latest.md"
