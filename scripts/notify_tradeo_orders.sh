#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATE_DIR="${ROOT_DIR}/.openclaw/runtime"
STATE_FILE="${STATE_DIR}/telegram_order_notifications.last"
SENT_FILLS_FILE="${STATE_DIR}/telegram_order_notifications.fills.sent"
LOCK_FILE="${STATE_FILE}.lock"
DB_CONTAINER="${TRADEO_NOTIFY_DB_CONTAINER:-tradeo-db}"
DB_USER="${TRADEO_NOTIFY_DB_USER:-tradeo}"
DB_NAME="${TRADEO_NOTIFY_DB_NAME:-tradeo}"
TELEGRAM_ACCOUNT="${TRADEO_NOTIFY_TELEGRAM_ACCOUNT:-tradeo}"
TELEGRAM_TARGET="${TRADEO_NOTIFY_TELEGRAM_TARGET:-1600299362}"
OPENCLAW_BIN="${OPENCLAW_BIN:-openclaw}"

mkdir -p "$STATE_DIR"
exec 9>"$LOCK_FILE"
flock -n 9 || exit 0

max_id_sql="SELECT COALESCE(MAX(id), 0) FROM audit_logs WHERE action IN ('ibkr_bracket_submitted', 'paper_trade_opened', 'ibkr_fills_ingested');"
current_max="$(docker exec "$DB_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -Atc "$max_id_sql" | tr -dc '0-9')"
current_max="${current_max:-0}"
touch "$SENT_FILLS_FILE"

if [[ ! -f "$STATE_FILE" ]]; then
  printf '%s\n' "$current_max" > "$STATE_FILE"
  exit 0
fi

last_id="$(tr -dc '0-9' < "$STATE_FILE")"
last_id="${last_id:-0}"

read -r -d '' query <<SQL || true
SELECT json_build_object(
  'id', a.id,
  'timestamp', a.timestamp,
  'action', a.action,
  'signal_id', s.id,
  'symbol', COALESCE(s.symbol, a.details_json->>'symbol'),
  'side', s.side,
  'qty', COALESCE(t.qty, NULLIF(a.details_json->>'qty', '')::int),
  'entry', COALESCE(t.entry, s.entry),
  'stop', COALESCE(t.stop, s.stop),
  'target', COALESCE(t.target, s.target),
  'broker_order_id', t.broker_order_id,
  'trading_mode', a.details_json->>'trading_mode',
  'reason', a.details_json->>'reason',
  'order_ids', a.details_json->'order_ids',
  'perm_ids', a.details_json->'perm_ids'
)::text
FROM audit_logs a
LEFT JOIN signals s
  ON CASE WHEN a.entity_id ~ '^[0-9]+$' THEN a.entity_id::int ELSE NULL END = s.id
LEFT JOIN LATERAL (
  SELECT *
  FROM trades t
  WHERE t.signal_id = s.id
  ORDER BY t.opened_at DESC, t.id DESC
  LIMIT 1
) t ON true
WHERE a.id > ${last_id}
  AND a.action IN ('ibkr_bracket_submitted', 'paper_trade_opened')
ORDER BY a.id ASC;
SQL

rows="$(docker exec "$DB_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -Atc "$query")"

new_last="$last_id"
if [[ -n "${rows// }" ]]; then
  while IFS= read -r row; do
    [[ -n "$row" ]] || continue
    message="$(ROW="$row" python3 - <<'PY'
import json
import os

row = json.loads(os.environ["ROW"])
event_id = int(row.get("id") or 0)
action = str(row.get("action") or "")
symbol = str(row.get("symbol") or "?").upper()
side = str(row.get("side") or "?").upper()
mode = str(row.get("trading_mode") or "paper").upper()
qty = row.get("qty")
entry = row.get("entry")
stop = row.get("stop")
target = row.get("target")
broker_order_id = row.get("broker_order_id")
reason = row.get("reason") or "auto"
order_ids = row.get("order_ids") or []

verb = "ORDEN IBKR" if action == "ibkr_bracket_submitted" else "PAPER SIM"
lines = [
    f"Tradeo: {verb} {mode}",
    f"{side} {symbol} x{qty or '?'}",
]
if entry is not None:
    lines.append(f"Entrada {entry} | Stop {stop} | Target {target}")
if broker_order_id:
    lines.append(f"Broker order: {broker_order_id}")
elif order_ids:
    lines.append("Order ids: " + ", ".join(str(x) for x in order_ids))
lines.append(f"Reason: {reason}")
lines.append(f"AuditLog #{event_id}")
print("\n".join(lines))
PY
)"
    "$OPENCLAW_BIN" message send \
      --channel telegram \
      --account "$TELEGRAM_ACCOUNT" \
      --target "$TELEGRAM_TARGET" \
      --message "$message" >/dev/null
    new_last="$(ROW="$row" python3 - <<'PY'
import json
import os
print(int(json.loads(os.environ["ROW"]).get("id") or 0))
PY
)"
  done <<< "$rows"
fi

read -r -d '' fill_query <<SQL || true
WITH fill_audits AS (
  SELECT
    a.id AS audit_id,
    a.timestamp AS audit_timestamp,
    jsonb_array_elements_text(COALESCE(a.details_json->'updated_trade_ids', '[]'::jsonb))::int AS trade_id
  FROM audit_logs a
  WHERE a.id > ${last_id}
    AND a.action = 'ibkr_fills_ingested'
),
fill_rows AS (
  SELECT
    fa.audit_id,
    fa.audit_timestamp,
    t.id AS trade_id,
    t.symbol,
    t.side AS trade_side,
    t.qty AS requested_qty,
    t.entry,
    t.stop,
    t.target,
    t.status,
    t.broker_order_id,
    fill
  FROM fill_audits fa
  JOIN trades t ON t.id = fa.trade_id
  CROSS JOIN LATERAL jsonb_array_elements(COALESCE(t.metadata_json->'ibkr_fills', '[]'::jsonb)) AS fill
  WHERE COALESCE(fill->>'fill_id_hash', fill->>'broker_execution_hash', '') <> ''
)
SELECT json_build_object(
  'audit_id', audit_id,
  'audit_timestamp', audit_timestamp,
  'trade_id', trade_id,
  'symbol', COALESCE(fill->>'symbol', symbol),
  'trade_side', trade_side,
  'fill_side', fill->>'side',
  'leg', fill->>'leg',
  'price', NULLIF(fill->>'price', '')::float,
  'qty', NULLIF(fill->>'quantity', '')::float,
  'requested_qty', requested_qty,
  'entry', entry,
  'stop', stop,
  'target', target,
  'status', status,
  'broker_order_id', broker_order_id,
  'order_id', fill->>'order_id',
  'perm_id', fill->>'perm_id',
  'commission', NULLIF(fill->>'commission', '')::float,
  'execution_time', fill->>'execution_time',
  'fill_id_hash', COALESCE(fill->>'fill_id_hash', fill->>'broker_execution_hash')
)::text
FROM fill_rows
ORDER BY audit_id ASC, COALESCE(fill->>'execution_time', '') ASC;
SQL

fill_rows="$(docker exec "$DB_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -Atc "$fill_query")"
if [[ -n "${fill_rows// }" ]]; then
  while IFS= read -r row; do
    [[ -n "$row" ]] || continue
    fill_hash="$(ROW="$row" python3 - <<'PY'
import json
import os
print(json.loads(os.environ["ROW"]).get("fill_id_hash") or "")
PY
)"
    [[ -n "$fill_hash" ]] || continue
    if grep -Fxq "$fill_hash" "$SENT_FILLS_FILE"; then
      continue
    fi
    message="$(ROW="$row" python3 - <<'PY'
import json
import os

row = json.loads(os.environ["ROW"])
event_id = int(row.get("audit_id") or 0)
symbol = str(row.get("symbol") or "?").upper()
fill_side = str(row.get("fill_side") or row.get("trade_side") or "?").upper()
leg = str(row.get("leg") or "fill").upper()
qty = row.get("qty") or row.get("requested_qty") or "?"
price = row.get("price")
commission = row.get("commission")
execution_time = row.get("execution_time") or row.get("audit_timestamp") or "?"
order_id = row.get("order_id") or row.get("broker_order_id")
status = str(row.get("status") or "?").upper()

lines = [
    "Tradeo: FILL IBKR",
    f"{fill_side} {symbol} x{qty} @ {price if price is not None else '?'}",
    f"Leg: {leg} | Trade #{row.get('trade_id')} | Estado {status}",
]
if order_id:
    lines.append(f"Order id: {order_id}")
if commission is not None:
    lines.append(f"Comision: {commission}")
lines.append(f"Hora: {execution_time}")
lines.append(f"AuditLog #{event_id}")
print("\n".join(lines))
PY
)"
    "$OPENCLAW_BIN" message send \
      --channel telegram \
      --account "$TELEGRAM_ACCOUNT" \
      --target "$TELEGRAM_TARGET" \
      --message "$message" >/dev/null
    printf '%s\n' "$fill_hash" >> "$SENT_FILLS_FILE"
    new_last="$(ROW="$row" python3 - <<'PY'
import json
import os
print(int(json.loads(os.environ["ROW"]).get("audit_id") or 0))
PY
)"
  done <<< "$fill_rows"
fi

printf '%s\n' "$current_max" > "$STATE_FILE"
