from __future__ import annotations

import json

from tradeo.research.intraday_research_evidence import (
    ResearchEvidenceWriter,
    session_bucket,
    summarize_evidence_directory,
)


def _record(symbol: str, entry_ts: str, outcome_r: float = 1.0) -> dict[str, object]:
    return {
        "pattern_key": "p1",
        "cluster_id": 1,
        "symbol": symbol,
        "timeframe": "1h",
        "window_size": 50,
        "forward_bars": 4,
        "side": "long",
        "window_start_ts": "2026-01-02T08:30:00",
        "window_end_ts": entry_ts,
        "entry_ts": entry_ts,
        "exit_ts": "2026-01-02T16:00:00",
        "entry_price": 100.0,
        "exit_price": 101.0,
        "forward_return": 0.01,
        "outcome_r": outcome_r,
        "split": "train",
        "cost_base_r": 0.05,
        "cost_x2_r": 0.10,
        "source": "rejected",
    }


def test_writer_respects_sample_limit(tmp_path) -> None:
    writer = ResearchEvidenceWriter(enabled=True, output_dir=tmp_path, max_samples_per_candidate=2)

    manifest = writer.write(run_id=7, evidence_by_candidate={"c1": [_record("AAPL", "2026-01-02T09:45:00")] * 4})

    assert manifest.record_count == 2
    rows = list((tmp_path / "run_7" / "candidate_c1.jsonl").read_text(encoding="utf-8").splitlines())
    assert len(rows) == 2


def test_writer_handles_missing_fields(tmp_path) -> None:
    writer = ResearchEvidenceWriter(enabled=True, output_dir=tmp_path)

    manifest = writer.write(run_id=8, evidence_by_candidate={"c2": [{"symbol": "MSFT"}]})

    assert manifest.errors == ()
    payload = json.loads((tmp_path / "run_8" / "candidate_c2.jsonl").read_text(encoding="utf-8"))
    assert payload["symbol"] == "MSFT"
    assert payload["session_bucket"] == "unknown"


def test_session_bucket_open_mid_close_unknown() -> None:
    assert session_bucket("2026-01-02T09:30:00") == "open"
    assert session_bucket("2026-01-02T11:00:00") == "mid"
    assert session_bucket("2026-01-02T15:00:00") == "close"
    assert session_bucket("not-a-time") == "unknown"


def test_summarizer_generates_symbol_time_month_summaries(tmp_path) -> None:
    writer = ResearchEvidenceWriter(enabled=True, output_dir=tmp_path)
    writer.write(
        run_id=9,
        evidence_by_candidate={
            "c1": [
                _record("AAPL", "2026-01-02T09:45:00", 1.0),
                _record("AAPL", "2026-01-03T11:30:00", -0.5),
                _record("MSFT", "2026-02-02T15:30:00", 0.25),
            ]
        },
    )

    summary = summarize_evidence_directory(tmp_path)

    assert summary["evidence_coverage"]["record_count"] == 3
    assert summary["symbol_contribution"][0]["symbol"] == "AAPL"
    assert {row["session_bucket"] for row in summary["time_of_day_summary"]} >= {"open", "mid", "close"}
    assert {row["month"] for row in summary["month_summary"]} == {"2026-01", "2026-02"}


def test_output_is_read_only_safety_contract(tmp_path) -> None:
    writer = ResearchEvidenceWriter(enabled=True, output_dir=tmp_path)
    manifest = writer.write(run_id=10, evidence_by_candidate={"c1": [_record("AAPL", "2026-01-02T09:45:00")]})

    assert manifest.record_count == 1
    text = (tmp_path / "run_10" / "manifest.json").read_text(encoding="utf-8").lower()
    assert "paper" not in text
    assert "live" not in text
    assert "order" not in text
    assert "gate" not in text
