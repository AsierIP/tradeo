from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from tradeo.core.config import Settings


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _redacted_intraday_config(settings: Settings) -> dict[str, Any]:
    return {
        key: value
        for key, value in settings.redacted_config_snapshot().items()
        if key.startswith("TRADEO_INTRADAY_")
    }


def build_pack(*, dry_run: bool) -> dict[str, Any]:
    settings = Settings()
    files = [
        ROOT / "backend/tradeo/core/config.py",
        ROOT / "backend/tradeo/db/models.py",
        ROOT / "backend/tradeo/services/intraday_calendar.py",
        ROOT / "backend/tradeo/services/ibkr_pacing.py",
        ROOT / "docs/intraday_no_regression_contract.md",
    ]
    payload = {
        "schema_version": 1,
        "generated_at": datetime.now(UTC).isoformat(),
        "dry_run": dry_run,
        "redacted": True,
        "intraday_config": _redacted_intraday_config(settings),
        "file_hashes": {str(path.relative_to(ROOT)): _sha256(path) for path in files if path.exists()},
        "required_tests": [
            "make test-safety",
            "pytest -q backend/tradeo/tests/test_intraday_config.py backend/tradeo/tests/test_intraday_models.py backend/tradeo/tests/test_intraday_calendar.py backend/tradeo/tests/test_ibkr_pacing.py",
        ],
        "session_report": {
            "available": False,
            "reason": "dry_run_no_session_events" if dry_run else "not_collected",
        },
        "secrets_included": False,
    }
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--output", default="reports/intraday_audit_pack.json")
    args = parser.parse_args()

    payload = build_pack(dry_run=args.dry_run)
    if args.dry_run:
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0
    output = ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
