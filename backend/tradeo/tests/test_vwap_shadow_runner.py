from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from tradeo.core.config import Settings
from tradeo.modules.laboratory.vwap_shadow_recorder import ShadowQuote
from tradeo.modules.laboratory.vwap_shadow_runner import (
    ShadowBatchRequest,
    load_symbols,
    run_shadow_batch,
    write_shadow_batch_artifacts,
)


def _forget_broker_modules() -> None:
    sys.modules.pop("tradeo.services.ibkr_broker", None)
    sys.modules.pop("tradeo.services.paper_broker", None)


def test_load_symbols_from_inline_and_universe_file(tmp_path: Path) -> None:
    universe = tmp_path / "universe.csv"
    universe.write_text("symbol,name\nmsft,Microsoft\nNVDA,Nvidia\n", encoding="utf-8")

    symbols = load_symbols(symbols="AAPL, MSFT", universe_file=universe, limit=3)

    assert symbols == ["AAPL", "MSFT", "NVDA"]


def test_shadow_batch_generates_jsonl_and_summary(tmp_path: Path) -> None:
    request = ShadowBatchRequest(
        symbols=("AAPL", "MSFT"),
        side="long",
        vwap_condition="vwap_reclaim_long",
        timeframe="1m",
        market_open=True,
    )

    records, summary = run_shadow_batch(
        request,
        quote_provider=lambda symbol: ShadowQuote(bid=100.0, ask=100.02, last=100.01, source=f"mock:{symbol}"),
    )
    write_shadow_batch_artifacts(
        records,
        summary,
        jsonl_out=tmp_path / "events.jsonl",
        summary_json=tmp_path / "summary.json",
        summary_md=tmp_path / "summary.md",
    )

    lines = (tmp_path / "events.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0])["schema_version"] == "tradeo.lab_vwap_shadow.v1"
    assert summary["events"] == 2
    assert summary["decisions"] == {"shadow_recorded": 2}
    assert summary["forbidden_outcomes"] == 0
    assert (tmp_path / "summary.md").exists()


def test_market_closed_and_quote_unavailable_do_not_fail_or_submit() -> None:
    request = ShadowBatchRequest(
        symbols=("AAPL",),
        side="long",
        vwap_condition="vwap_reclaim_long",
        timeframe="1m",
        market_open=False,
    )

    records, summary = run_shadow_batch(request)

    assert records[0]["decision"] == "market_closed"
    assert records[0]["quote_status"] == "unavailable"
    assert records[0]["orders_allowed"] is False
    assert records[0]["paper_allowed"] is False
    assert records[0]["live_allowed"] is False
    assert records[0]["submit_order_called"] is False
    assert summary["forbidden_outcomes"] == 0


def test_shadow_batch_blocks_unsafe_settings() -> None:
    request = ShadowBatchRequest(
        symbols=("AAPL",),
        side="long",
        vwap_condition="vwap_reclaim_long",
        timeframe="1m",
        market_open=True,
    )

    records, summary = run_shadow_batch(
        request,
        quote_provider=lambda _: ShadowQuote(bid=100.0, ask=100.02, last=100.01),
        settings=Settings(live_trading_enabled=True),
    )

    assert records[0]["decision"] == "blocked_safety"
    assert records[0]["decision_reason"] == "live_trading_enabled"
    assert summary["forbidden_outcomes"] == 0


def test_runner_does_not_import_broker_or_paper_paths() -> None:
    _forget_broker_modules()

    request = ShadowBatchRequest(
        symbols=("AAPL",),
        side="long",
        vwap_condition="vwap_reclaim_long",
        timeframe="1m",
        market_open=True,
    )

    run_shadow_batch(request)

    assert "tradeo.services.ibkr_broker" not in sys.modules
    assert "tradeo.services.paper_broker" not in sys.modules


def test_shadow_loop_defaults_to_single_bounded_iteration(tmp_path: Path) -> None:
    script = Path(__file__).resolve().parents[3] / "scripts" / "run_vwap_shadow_loop.py"
    jsonl = tmp_path / "events.jsonl"
    summary_json = tmp_path / "summary.json"
    summary_md = tmp_path / "summary.md"

    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--symbols",
            "AAPL,MSFT",
            "--conditions",
            "vwap_reclaim_long:long,vwap_reject_short:short",
            "--jsonl-out",
            str(jsonl),
            "--summary-json",
            str(summary_json),
            "--summary-md",
            str(summary_md),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    events = jsonl.read_text(encoding="utf-8").splitlines()
    summary = json.loads(summary_json.read_text(encoding="utf-8"))
    assert len(events) == 4
    assert summary["iterations_requested"] == 1
    assert summary["iterations_completed"] == 1
    assert summary["forbidden_outcomes"] == 0
    assert summary["orders_allowed"] is False
    assert summary["paper_allowed"] is False
    assert summary["live_allowed"] is False
    assert summary_md.exists()


def test_shadow_loop_respects_existing_stop_file(tmp_path: Path) -> None:
    script = Path(__file__).resolve().parents[3] / "scripts" / "run_vwap_shadow_loop.py"
    stop_file = tmp_path / "STOP"
    stop_file.write_text("stop\n", encoding="utf-8")
    jsonl = tmp_path / "events.jsonl"
    summary_json = tmp_path / "summary.json"

    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--symbols",
            "AAPL",
            "--stop-file",
            str(stop_file),
            "--jsonl-out",
            str(jsonl),
            "--summary-json",
            str(summary_json),
            "--summary-md",
            str(tmp_path / "summary.md"),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    summary = json.loads(summary_json.read_text(encoding="utf-8"))
    assert summary["stopped_by_file"] is True
    assert summary["iterations_completed"] == 0
    assert summary["forbidden_outcomes"] == 0
    assert not jsonl.exists()
