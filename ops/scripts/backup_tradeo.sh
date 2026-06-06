#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
mkdir -p backups
archive="backups/tradeo_backup_$(date +%Y%m%d_%H%M%S).tar.gz"
tar -czf "$archive" reports data config .env docker-compose.yml README.md docs || true
echo "$archive"
