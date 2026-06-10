from __future__ import annotations

from sqlalchemy.orm import Session
from loguru import logger

from tradeo.db.models import AuditLog
from tradeo.core.config import get_settings
from tradeo.schemas import ScanRequest, ScanResponse, SupervisorDecision
from tradeo.services.data_provider import MarketDataProvider, pick_symbols
from tradeo.services.data_quality import assess_ohlcv_quality_from_settings
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
        data_errors = 0
        data_quality_skips = 0
        for symbol in symbols:
            try:
                df = self.provider.fetch_ohlcv(symbol, period=period, interval=interval)
            except Exception as exc:  # noqa: BLE001
                data_errors += 1
                logger.warning("skipping {} after market data error: {}", symbol, exc)
                if store:
                    db.add(
                        AuditLog(
                            actor="scanner",
                            action="market_data_error",
                            entity_type="symbol",
                            entity_id=symbol,
                            details_json={"error": str(exc), "period": period, "interval": interval},
                        )
                    )
                continue
            if self.settings.data_quality_filter_enabled:
                quality = assess_ohlcv_quality_from_settings(df, symbol, interval, self.settings)
                if not quality.research_grade:
                    data_quality_skips += 1
                    logger.warning(
                        "skipping {}: OHLCV not research grade ({})",
                        symbol,
                        ",".join(quality.issues),
                    )
                    if store:
                        db.add(
                            AuditLog(
                                actor="scanner",
                                action="market_data_quality_reject",
                                entity_type="symbol",
                                entity_id=symbol,
                                details_json=quality.to_dict(),
                            )
                        )
                    continue
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
            data_errors=data_errors,
            data_quality_skips=data_quality_skips,
        )
