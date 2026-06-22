#!/usr/bin/env bash
set -euo pipefail

DRY_RUN=false
if [[ "${1:-}" == "--dry-run" ]]; then
  DRY_RUN=true
fi

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DIST="$ROOT/dist"
OUT="$DIST/tradeo_codex_bundle.zip"

EXCLUDES=(
  "*.env"
  ".env"
  ".env.*"
  "*/.env"
  "*/.env.*"
  ".git/*"
  "backend/.venv/*"
  "**/__pycache__/*"
  "**/.pytest_cache/*"
  "**/.ruff_cache/*"
  "artifacts/*"
  "backend/artifacts/*"
  "backups/*"
  "reports/*"
  "backend/reports/*"
  "research/audit_bridge/requests/*"
  "dist/*"
  "*.sqlite"
  "*.sqlite3"
  "*.db"
  "*.dump"
  "*.log"
  "*.bak"
  "*.backup"
  "openclaw-workspace-state.json"
)

mkdir -p "$DIST"

if [[ "$DRY_RUN" == true ]]; then
  echo "Would create $OUT with exclusions:"
  printf ' - %s\n' "${EXCLUDES[@]}"
  exit 0
fi

cd "$ROOT"
ZIP_ARGS=()
for pattern in "${EXCLUDES[@]}"; do
  ZIP_ARGS+=("-x" "$pattern")
done
zip -qr "$OUT" . "${ZIP_ARGS[@]}"
python3 scripts/check_bundle_no_secrets.py "$OUT"
echo "$OUT"
