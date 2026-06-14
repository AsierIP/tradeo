#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."

backup_dir="${TRADEO_BACKUP_DIR:-backups}"
timestamp="$(date +%Y%m%d_%H%M%S)"
mkdir -p "$backup_dir"

archive="$backup_dir/tradeo_backup_${timestamp}.tar.gz"
pg_dump_file="$backup_dir/tradeo_postgres_${timestamp}.dump"
manifest="$backup_dir/tradeo_backup_${timestamp}.manifest"

database_url="${TRADEO_DATABASE_URL:-}"
if [[ -z "$database_url" && -f .env ]]; then
  database_url="$(
    awk -F= '/^TRADEO_DATABASE_URL=/ {print substr($0, index($0, "=") + 1); exit}' .env
  )"
fi
pg_url="${database_url/postgresql+psycopg:\/\//postgresql:\/\/}"
pg_url="${pg_url/postgresql+psycopg2:\/\//postgresql:\/\/}"

pg_dump_status="skipped"
if [[ "${TRADEO_BACKUP_POSTGRES:-auto}" != "false" ]]; then
  if [[ -n "$pg_url" && "$pg_url" == postgresql://* ]] && command -v pg_dump >/dev/null 2>&1; then
    pg_dump --format=custom --no-owner --no-acl --file="$pg_dump_file" "$pg_url"
    pg_dump_status="ok"
  elif [[ "${TRADEO_BACKUP_POSTGRES:-auto}" == "required" ]]; then
    echo "PostgreSQL backup required but pg_dump or TRADEO_DATABASE_URL is unavailable" >&2
    exit 1
  fi
fi

tar_args=(reports data config .env docker-compose.yml README.md docs)
if [[ -f "$pg_dump_file" ]]; then
  tar_args+=("$pg_dump_file")
fi
tar --ignore-failed-read -czf "$archive" "${tar_args[@]}" 2>/dev/null || true

{
  echo "archive=$archive"
  echo "postgres_dump=$pg_dump_status"
  if [[ -f "$pg_dump_file" ]]; then
    echo "postgres_dump_file=$pg_dump_file"
  fi
} > "$manifest"

echo "$archive"
