from __future__ import annotations

from sqlalchemy.orm import Session

from tradeo.core.config import get_settings
from tradeo.schemas import ScanRequest, ScanResponse, SupervisorDecision
from tradeo.services.data_provider import MarketDataProvider, pick_symbols
from tradeo.services.pattern_detector import CupPatternDetector
from tradeo.services.provider_factory import get_market_data_provider
from tradeo.services.strategy_config import load_strategy_config
from tradeo.services.supervisor import TradeSupervisor


class MarketScanner:
    def __init__(self, provider: MarketDataProvider | None = None) -> None:
        self.settings = get_settings()
        cfg = load_strategy_config(self.settings.strategy_config_file)
        self.detector = CupPatternDetector.from_config(cfg)
        self.supervisor = TradeSupervisor(self.settings)
        self.provider = provider or get_market_data_provider()

    def run(self, request: ScanRequest, db: Session, store: bool = True) -> ScanResponse:
        symbols = pick_symbols(request.limit, request.force_symbols)
        period = request.period or self.settings.scan_period
        interval = request.interval or self.settings.scan_interval
        decisions: list[SupervisorDecision] = []
        stored = 0
        rejected = 0
        for symbol in symbols:
            df = self.provider.fetch_ohlcv(symbol, period=period, interval=interval)
            candidate = self.detector.detect(symbol, df, timeframe=interval)
            if candidate is None:
                continue
            decision = self.supervisor.review_candidate(candidate, db)
            decisions.append(decision)
            if decision.status == "rejected":
                rejected += 1
            elif store:
                signal = self.supervisor.store_decision(decision, db)
                if signal:
                    stored += 1
        return ScanResponse(
            scanned=len(symbols),
            candidates=len(decisions),
            stored_signals=stored,
            rejected=rejected,
            decisions=decisions,
        )
