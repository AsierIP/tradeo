from __future__ import annotations

from fastapi import APIRouter, Depends

from tradeo.core.config import get_settings
from tradeo.core.security import require_admin
from tradeo.schemas import BacktestMetrics, BacktestRequest
from tradeo.services.backtester import Backtester
from tradeo.services.data_provider import pick_symbols
from tradeo.services.provider_factory import get_market_data_provider

router = APIRouter(prefix="/backtests", tags=["backtests"])


@router.post("/run", response_model=BacktestMetrics)
def run_backtest(request: BacktestRequest, _: str = Depends(require_admin)) -> BacktestMetrics:
    settings = get_settings()
    symbols = request.symbols or pick_symbols(limit=request.max_symbols, interval=request.interval)
    return Backtester(provider=get_market_data_provider(), starting_equity=settings.initial_capital_usd).run(
        symbols=symbols[: request.max_symbols], period=request.period, interval=request.interval
    )
