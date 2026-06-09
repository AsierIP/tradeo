#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

mkdir -p artifacts reports/research

LOG_FILE="${TRADEO_RESEARCH_FOREVER_LOG:-artifacts/research_forever.log}"
PID_FILE="${TRADEO_RESEARCH_FOREVER_PID:-artifacts/research_forever.pid}"
STOP_FILE="${TRADEO_RESEARCH_FOREVER_STOP:-artifacts/research_forever.stop}"

DISCOVERY_LIMIT="${TRADEO_RESEARCH_DISCOVERY_LIMIT:-40}"
MAX_TOTAL_WINDOWS="${TRADEO_RESEARCH_MAX_TOTAL_WINDOWS:-6000}"
MAX_WINDOWS_PER_SYMBOL="${TRADEO_RESEARCH_MAX_WINDOWS_PER_SYMBOL:-250}"
MATCH_LIMIT="${TRADEO_RESEARCH_MATCH_LIMIT:-80}"
MAX_PATTERNS="${TRADEO_RESEARCH_MAX_PATTERNS:-40}"
SLEEP_SECONDS="${TRADEO_RESEARCH_SLEEP_SECONDS:-60}"

if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

ADMIN_USER="${TRADEO_ADMIN_USERNAME:-admin}"
ADMIN_PASS="${TRADEO_ADMIN_PASSWORD:-change-me}"
API_URL="${TRADEO_API_URL:-http://localhost:8000/api}"

timestamp() {
  date -u +"%Y-%m-%dT%H:%M:%SZ"
}

log() {
  printf '[%s] %s\n' "$(timestamp)" "$*" | tee -a "$LOG_FILE"
}

api_post() {
  local path="$1"
  local payload="$2"
  curl -fsS \
    -u "${ADMIN_USER}:${ADMIN_PASS}" \
    -H "Content-Type: application/json" \
    -X POST "${API_URL}${path}" \
    -d "$payload"
}

api_get() {
  local path="$1"
  curl -fsS -u "${ADMIN_USER}:${ADMIN_PASS}" "${API_URL}${path}"
}

echo "$$" > "$PID_FILE"
rm -f "$STOP_FILE"

log "research forever started pid=$$ provider=${TRADEO_MARKET_DATA_PROVIDER:-unknown} synthetic=${TRADEO_ALLOW_SYNTHETIC_MARKET_DATA:-unknown} mode=${TRADEO_TRADING_MODE:-unknown} readonly=${TRADEO_IBKR_READONLY:-unknown} live=${TRADEO_LIVE_TRADING_ENABLED:-unknown}"

cycle=0
while [[ ! -f "$STOP_FILE" ]]; do
  cycle=$((cycle + 1))
  if latest_run="$(api_get '/research/runs?limit=1' 2>&1)" && printf '%s' "$latest_run" | grep -q '"status":"running"'; then
    log "cycle=$cycle existing discovery still running; sleep ${SLEEP_SECONDS}s"
    sleep "$SLEEP_SECONDS"
    continue
  fi

  log "cycle=$cycle discovery start limit=$DISCOVERY_LIMIT max_total_windows=$MAX_TOTAL_WINDOWS max_windows_per_symbol=$MAX_WINDOWS_PER_SYMBOL"

  discovery_payload=$(printf '{"limit":%s,"max_total_windows":%s,"max_windows_per_symbol":%s}' \
    "$DISCOVERY_LIMIT" "$MAX_TOTAL_WINDOWS" "$MAX_WINDOWS_PER_SYMBOL")

  if discovery_result="$(api_post /research/run-discovery "$discovery_payload" 2>&1)"; then
    printf '%s\n' "$discovery_result" >> "$LOG_FILE"
    log "cycle=$cycle discovery ok"
  else
    log "cycle=$cycle discovery failed: $discovery_result"
    sleep "$SLEEP_SECONDS"
    continue
  fi

  log "cycle=$cycle match-current start"
  match_payload=$(printf '{"limit":%s,"max_patterns":%s,"store":true}' "$MATCH_LIMIT" "$MAX_PATTERNS")
  if match_result="$(api_post /research/match-current "$match_payload" 2>&1)"; then
    printf '%s\n' "$match_result" >> "$LOG_FILE"
    log "cycle=$cycle match-current ok"
  else
    log "cycle=$cycle match-current failed: $match_result"
  fi

  if runs="$(api_get '/research/runs?limit=3' 2>&1)"; then
    printf '%s\n' "$runs" > artifacts/research_forever_latest_runs.json
  fi
  if patterns="$(api_get '/research/discovered-patterns?status=accepted&limit=20' 2>&1)"; then
    printf '%s\n' "$patterns" > artifacts/research_forever_accepted_patterns.json
  fi
  if matches="$(api_get '/research/current-matches?limit=50' 2>&1)"; then
    printf '%s\n' "$matches" > artifacts/research_forever_current_matches.json
  fi

  log "cycle=$cycle sleep ${SLEEP_SECONDS}s"
  sleep "$SLEEP_SECONDS"
done

log "research forever stopped by $STOP_FILE"
