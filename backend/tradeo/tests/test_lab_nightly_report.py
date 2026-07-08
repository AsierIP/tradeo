from __future__ import annotations

import importlib.util
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "scripts/build_lab_nightly_report.py"

spec = importlib.util.spec_from_file_location("build_lab_nightly_report", SCRIPT)
assert spec is not None
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


def test_summarize_runtime_counts_redacted_orders(tmp_path: Path) -> None:
    day = tmp_path / "2026-07-06"
    day.mkdir()
    (day / "session.json").write_text(
        json.dumps(
            {
                "decision": "LAB_PAPER_PROBE_RTH_NO_TRADE_NO_TRIGGER",
                "paper_orders_executed": 0,
                "live_orders_executed": 0,
                "orders_filled": 0,
                "no_trade_reason": "NO_TRADE_NO_TRIGGER",
            }
        ),
        encoding="utf-8",
    )

    summary = module._summarize_runtime(day)

    assert summary["orders_submitted"] == 0
    assert summary["live_orders"] == 0
    assert "NO_TRADE_NO_TRIGGER" in summary["no_trade_reasons"]


def test_decision_payload_never_promotes() -> None:
    payload = module._decision_payload(
        trading_day=module.datetime.fromisoformat("2026-07-06").date(),
        state={"state": "POST_CLOSE_ANALYZED", "probes": {}},
        summary={"orders_attempted": 0, "orders_submitted": 0, "orders_filled": 0, "orders_cancelled": 0, "orders_rejected": 0, "live_orders": 0, "no_trade_reasons": []},
        dry_run=True,
    )

    assert payload["decision"] == "LAB_AUTOMATION_READY"
    assert payload["foxhunter_promotion"] is False
    assert payload["live_candidate_created"] is False
