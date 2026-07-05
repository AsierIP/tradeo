from __future__ import annotations

import csv
from datetime import date, timedelta
from pathlib import Path
from typing import Any

INDEPENDENCE_DAY_OBSERVED_2026 = date(2026, 7, 3)


def repo_root(repo: Path | None = None) -> Path:
    if repo is not None:
        return repo.resolve()
    return Path(__file__).resolve().parents[4]


def last_valid_trading_day(run_date: date) -> date:
    candidate = run_date - timedelta(days=1)
    holidays = {INDEPENDENCE_DAY_OBSERVED_2026}
    while candidate.weekday() >= 5 or candidate in holidays:
        candidate -= timedelta(days=1)
    return candidate


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})
