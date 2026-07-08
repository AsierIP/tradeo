from __future__ import annotations

import csv
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SEED_FILES = {
    "daily_mega_caps": REPO_ROOT / "data" / "universe_daily_mega_caps.csv",
    "daily_large_caps": REPO_ROOT / "data" / "universe_daily_large_caps.csv",
    "daily_mid_caps": REPO_ROOT / "data" / "universe_daily_mid_caps.csv",
}
EXPECTED_COLUMNS = {"symbol", "name", "universe_key", "cap_segment", "note"}


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames is not None
        assert EXPECTED_COLUMNS.issubset(reader.fieldnames)
        return list(reader)


def test_daily_cap_seed_files_are_modest_marked_and_non_small_cap() -> None:
    all_symbols: set[str] = set()

    for universe_key, path in SEED_FILES.items():
        rows = _rows(path)
        assert 1 <= len(rows) <= 12

        symbols = [row["symbol"] for row in rows]
        assert symbols == [symbol.upper().strip() for symbol in symbols]
        assert len(symbols) == len(set(symbols))

        for row in rows:
            assert row["universe_key"] == universe_key
            assert row["cap_segment"] in {"mega_cap_seed", "large_cap_seed", "mid_cap_seed"}
            assert row["cap_segment"] != "small_cap_seed"
            note = row["note"].lower()
            assert "seed" in note
            assert "not a recommendation" in note

        overlap = all_symbols.intersection(symbols)
        assert overlap == set()
        all_symbols.update(symbols)


def test_daily_universe_seed_workflow_is_documented() -> None:
    env_example = (REPO_ROOT / ".env.example").read_text(encoding="utf-8")
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    lab_docs = (REPO_ROOT / "docs" / "pattern_discovery_lab.md").read_text(
        encoding="utf-8"
    )

    for path in SEED_FILES.values():
        container_path = f"/app/data/{path.name}"
        assert container_path in env_example
        assert f"data/{path.name}" in readme
        assert f"data/{path.name}" in lab_docs

    documented_policy = f"{readme}\n{lab_docs}".lower()
    assert "separate discovery per universe" in documented_policy
    assert "no cross-universe promotion" in documented_policy
