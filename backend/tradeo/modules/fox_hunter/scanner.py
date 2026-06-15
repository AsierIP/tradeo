from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from tradeo.core.config import Settings
from tradeo.modules.shared.entry_scanner import PatternEntryScanner
from tradeo.research.novel_pattern_matcher import NovelPatternMatcher


@dataclass(slots=True)
class FoxHunterScanner:
    """FoxHunter facade for production-pattern entry scans."""

    settings: Settings | None = None
    matcher: NovelPatternMatcher | None = None

    def _scanner(self) -> PatternEntryScanner:
        return PatternEntryScanner(settings=self.settings, matcher=self.matcher)

    def scan(
        self,
        db: Session,
        *,
        symbols: list[str] | None = None,
        limit: int | None = None,
        max_patterns: int | None = None,
        max_results: int | None = None,
        similarity_threshold: float | None = None,
        store_signals: bool | None = None,
        execute_orders: bool | None = None,
    ) -> dict[str, Any]:
        return self._scanner().scan(
            db,
            module="fox_hunter",
            symbols=symbols,
            limit=limit,
            max_patterns=max_patterns,
            max_results=max_results,
            similarity_threshold=similarity_threshold,
            store_signals=store_signals,
            execute_orders=execute_orders,
        )

    def status(self, db: Session) -> dict[str, Any]:
        return self._scanner().status(db)["fox_hunter"]
