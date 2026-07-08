from __future__ import annotations

from pathlib import Path

from tradeo.agents.pattern_discovery_lab_agent import PatternDiscoveryLabAgent
from tradeo.core.config import Settings
from tradeo.schemas import DiscoveryRunRequest
from tradeo.services.discovery_params import (
    discovery_universe_key,
    resolve_discovery_run_params,
)


def test_public_resolver_matches_agent_for_daily_segments(tmp_path: Path) -> None:
    mega = tmp_path / "mega.csv"
    large = tmp_path / "large.csv"
    mid = tmp_path / "mid.csv"
    mega.write_text("symbol\nMEGA1\n", encoding="utf-8")
    large.write_text("symbol\nLARGE1\n", encoding="utf-8")
    mid.write_text("symbol\nMID1\n", encoding="utf-8")
    settings = Settings(
        daily_mega_universe_file=str(mega),
        daily_large_universe_file=str(large),
        daily_mid_universe_file=str(mid),
        daily_universe_cap_segments="mega,large,mid",
        reports_dir=str(tmp_path / "reports"),
    )
    agent = PatternDiscoveryLabAgent(settings=settings, provider=object())

    for segment in ("mega", "large", "mid"):
        request = DiscoveryRunRequest(interval="1d", daily_cap_segment=segment, symbols=[" aapl ", ""])

        public = resolve_discovery_run_params(settings, request)

        assert public == agent._resolve_params(request)
        assert public["daily_cap_segment"] == segment
        assert public["symbols"] == ["AAPL"]


def test_public_resolver_matches_agent_for_intraday(tmp_path: Path) -> None:
    small = tmp_path / "small.csv"
    small.write_text("symbol\nSML1\n", encoding="utf-8")
    settings = Settings(
        intraday_universe_file=str(small),
        reports_dir=str(tmp_path / "reports"),
        discovery_daily_event_min_gain_pct=0.2,
    )
    request = DiscoveryRunRequest(
        interval="5m",
        daily_cap_segment="mega",
        daily_event_min_gain_pct=0.5,
    )
    agent = PatternDiscoveryLabAgent(settings=settings, provider=object())

    public = resolve_discovery_run_params(settings, request)

    assert public == agent._resolve_params(request)
    assert public["cadence"] == "intraday"
    assert public["daily_cap_segment"] is None
    assert public["daily_event_min_gain_pct"] == 0.0


def test_public_resolver_uses_same_hash_for_universe_hash_and_key(tmp_path: Path) -> None:
    mega = tmp_path / "mega.csv"
    mega.write_text("symbol\nMEGA1\n", encoding="utf-8")
    settings = Settings(
        daily_mega_universe_file=str(mega),
        reports_dir=str(tmp_path / "reports"),
    )
    request = DiscoveryRunRequest(interval="1d", daily_cap_segment="mega")

    params = resolve_discovery_run_params(settings, request, file_hasher=lambda _path: "abc123")

    assert params["universe_hash"] == "abc123"
    assert params["universe_key"] == discovery_universe_key(
        scope=params["universe_scope"],
        universe_file=params["universe_file"],
        universe_hash="abc123",
    )
