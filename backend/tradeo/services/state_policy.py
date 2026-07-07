from __future__ import annotations

from tradeo.db.models import DiscoveredPatternStatus

LAB_RUNTIME_STATES = {
    DiscoveredPatternStatus.LAB,
    DiscoveredPatternStatus.LAB_WATCHLIST,
    DiscoveredPatternStatus.LAB_CANDIDATE,
    DiscoveredPatternStatus.DIRECTOR_REVIEW,
}
REVIEW_TRIGGER_STATES = {
    DiscoveredPatternStatus.LAB,
    DiscoveredPatternStatus.LAB_WATCHLIST,
    DiscoveredPatternStatus.LAB_CANDIDATE,
}
LEGACY_PROMOTION_STATES = {
    DiscoveredPatternStatus.PAPER_CANDIDATE,
    DiscoveredPatternStatus.PREMIUM_CANDIDATE,
}
DAILY_RUNTIME_STATES = {
    DiscoveredPatternStatus.CONFIRMED_CANDIDATE,
    DiscoveredPatternStatus.PAPER_CANDIDATE,
    DiscoveredPatternStatus.PREMIUM_CANDIDATE,
}
PRODUCTION_RUNTIME_STATES = {DiscoveredPatternStatus.PRODUCTION}


def is_legacy_promotion_state(status: DiscoveredPatternStatus | str) -> bool:
    value = status.value if hasattr(status, "value") else str(status)
    return value in {item.value for item in LEGACY_PROMOTION_STATES}
