#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DAY="$(TZ=America/New_York date +%F)"
RUNTIME_DIR="${ROOT}/artifacts/runtime/lab_paper_probe/${DAY}"
RUNTIME_OUT="${RUNTIME_DIR}/session_runner.json"

mkdir -p "${RUNTIME_DIR}"
"${ROOT}/.venv/bin/python" "${ROOT}/scripts/check_lab_probe_state.py" \
  --root "${ROOT}" \
  --trading-day "${DAY}" \
  --acquire-session-lock \
  --phase SESSION_RUNNING
trap '"${ROOT}/.venv/bin/python" "${ROOT}/scripts/check_lab_probe_state.py" --root "${ROOT}" --trading-day "${DAY}" --release-session-lock >/dev/null 2>&1 || true' EXIT

"${ROOT}/scripts/run_lab_paper_probe_005_rth_safe.sh" \
  --runtime-out "${RUNTIME_OUT}" \
  --reports-dir "${ROOT}/research/lab_foxhunter" \
  --overlay-file "/tmp/tradeo_lab_paper_write_overlay_${DAY//-/}_daily.env" \
  --probe-manifest "${ROOT}/research/lab_foxhunter/probes/LAB-GAP-REV-001.json" \
  --probe-manifest "${ROOT}/research/lab_foxhunter/probes/LAB-GAP-REV-002.json" \
  --max-orders-total 0
