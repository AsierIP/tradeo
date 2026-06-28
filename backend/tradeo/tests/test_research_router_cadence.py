from __future__ import annotations

from types import SimpleNamespace

from tradeo.db.models import DiscoveredPatternStatus
from tradeo.routers.research import _GREEN_RESEARCH_STATUSES, _research_cadence_from_interval, _research_cadence_from_run


def test_research_cadence_from_interval_splits_daily_and_intraday() -> None:
    assert _research_cadence_from_interval("1d") == "daily"
    assert _research_cadence_from_interval("daily") == "daily"
    assert _research_cadence_from_interval("5m") == "intraday"
    assert _research_cadence_from_interval("15m") == "intraday"
    assert _research_cadence_from_interval("1h") == "intraday"


def test_research_cadence_from_run_prefers_explicit_cadence() -> None:
    daily = SimpleNamespace(params_json={"cadence": "daily", "interval": "5m"})
    intraday = SimpleNamespace(params_json={"interval": "15m"})

    assert _research_cadence_from_run(daily) == "daily"
    assert _research_cadence_from_run(intraday) == "intraday"


def test_green_research_statuses_include_confirmation_but_not_rejected() -> None:
    assert DiscoveredPatternStatus.LAB_WATCHLIST in _GREEN_RESEARCH_STATUSES
    assert DiscoveredPatternStatus.NEEDS_CONFIRMATION in _GREEN_RESEARCH_STATUSES
    assert DiscoveredPatternStatus.REJECTED not in _GREEN_RESEARCH_STATUSES
    assert DiscoveredPatternStatus.FAILED_CONFIRMATION not in _GREEN_RESEARCH_STATUSES
