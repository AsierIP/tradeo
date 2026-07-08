#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="${ROOT}/.venv/bin/python"
MODE="${1:-}"
DATE="$("${PYTHON}" - <<'PY'
from datetime import datetime
from zoneinfo import ZoneInfo
print(datetime.now(ZoneInfo("America/New_York")).date().isoformat())
PY
)"
RUNTIME_DIR="${ROOT}/artifacts/runtime/lab_paper_probe/${DATE}"
REPORTS_DIR="${ROOT}/research/lab_foxhunter"

case "${MODE}" in
  premarket)
    exec "${PYTHON}" "${ROOT}/scripts/check_lab_probe_state.py" \
      --root "${ROOT}" \
      --trading-day "${DATE}" \
      --phase SESSION_ARMED
    ;;
  session-runner)
    exec /bin/bash "${ROOT}/scripts/run_lab_daily_session.sh"
    ;;
  mid-collector|close-collector)
    exec "${PYTHON}" "${ROOT}/scripts/build_lab_nightly_report.py" \
      --root "${ROOT}" \
      --trading-day "${DATE}" \
      --phase "${MODE}" \
      --dry-run
    ;;
  nightly-report)
    exec "${PYTHON}" "${ROOT}/scripts/build_lab_nightly_report.py" \
      --root "${ROOT}" \
      --trading-day "${DATE}" \
      --phase post-close
    ;;
  *)
    echo "usage: $0 {premarket|session-runner|mid-collector|close-collector|nightly-report}" >&2
    exit 2
    ;;
esac
