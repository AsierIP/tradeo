from __future__ import annotations

from datetime import datetime, timedelta, timezone

from tradeo.modules.intraday.candidates import IntradayCandidateBuilder, IntradayCandidateRules


NOW = datetime(2026, 6, 22, 14, 35, tzinfo=timezone.utc)
FLAT_BY = datetime(2026, 6, 22, 19, 55, tzinfo=timezone.utc)


def _match(**overrides):
    payload = {
        "symbol": "SOUN",
        "pattern_key": "intraday_breakout",
        "side": "long",
        "timeframe": "5m",
        "entry": 10.0,
        "stop": 9.5,
        "target": 12.0,
        "score": 0.82,
        "closed_bar": True,
        "window_end": NOW.isoformat(),
        "session_bucket": "open",
        "spread_bps": 20.0,
        "dollar_volume": 1_500_000,
        "entry_variant_id": "v1",
        "paper_allowed": True,
    }
    payload.update(overrides)
    return payload


def test_intraday_candidate_builder_accepts_shadow_and_metadata() -> None:
    batch = IntradayCandidateBuilder().build(
        [_match()],
        now=NOW,
        session_id="2026-06-22",
        current_bucket="open",
        flat_by=FLAT_BY,
    )

    candidate = batch.candidates[0]
    assert candidate.status == "shadow"
    assert candidate.reason_codes == ()
    assert candidate.expires_at == NOW + timedelta(minutes=10)
    assert candidate.metadata["intraday"]["session_id"] == "2026-06-22"
    assert candidate.metadata["intraday"]["expiry_bars"] == 2


def test_intraday_candidate_builder_blocks_hard_gates() -> None:
    batch = IntradayCandidateBuilder().build(
        [
            _match(symbol="WIDE", spread_bps=90.0),
            _match(symbol="LOWD", dollar_volume=100_000),
            _match(symbol="LIVE", closed_bar=False),
            _match(symbol="STALE", window_end=(NOW - timedelta(minutes=20)).isoformat()),
            _match(symbol="COOL", cooldown_until=(NOW + timedelta(minutes=5)).isoformat()),
            _match(symbol="BUCK", allowed_session_buckets=("midday",)),
        ],
        now=NOW,
        session_id="2026-06-22",
        current_bucket="open",
        flat_by=FLAT_BY,
    )

    reasons = {candidate.symbol: candidate.reason_code for candidate in batch.blocked}
    assert reasons == {
        "WIDE": "spread_too_wide",
        "LOWD": "low_dollar_volume",
        "LIVE": "bar_not_closed",
        "COOL": "cooldown_active",
        "BUCK": "bucket_not_allowed",
    }
    assert {candidate.symbol: candidate.reason_code for candidate in batch.expired} == {
        "STALE": "expired"
    }


def test_intraday_candidate_builder_expires_and_dedupes_exposure() -> None:
    batch = IntradayCandidateBuilder(
        IntradayCandidateRules(paper_enabled=True, max_candidates_per_symbol=1)
    ).build(
        [
            _match(symbol="SOUN", exposure_key="same", paper_allowed=True),
            _match(symbol="SOUN", exposure_key="same", paper_allowed=True),
            _match(symbol="OLD", window_end=(NOW - timedelta(minutes=30)).isoformat()),
        ],
        now=NOW,
        session_id="2026-06-22",
        current_bucket="open",
        flat_by=FLAT_BY,
    )

    assert batch.candidates[0].status == "paper_eligible"
    assert batch.candidates[1].status == "blocked"
    assert batch.candidates[1].reason_code == "duplicate_exposure"
    assert batch.candidates[2].status == "expired"
    assert batch.candidates[2].reason_code == "expired"
