from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from tradeo.core.config import get_settings
from tradeo.db.init_db import init_db, seed_db
from tradeo.db.session import SessionLocal
from tradeo.routers import backtests, dashboard, health, reports, research, risk, scan, self_improvement, signals


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    db = SessionLocal()
    try:
        seed_db(db)
    finally:
        db.close()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health.router, prefix=settings.api_prefix)
    app.include_router(dashboard.router, prefix=settings.api_prefix)
    app.include_router(scan.router, prefix=settings.api_prefix)
    app.include_router(signals.router, prefix=settings.api_prefix)
    app.include_router(backtests.router, prefix=settings.api_prefix)
    app.include_router(risk.router, prefix=settings.api_prefix)
    app.include_router(reports.router, prefix=settings.api_prefix)
    app.include_router(research.router, prefix=settings.api_prefix)
    app.include_router(self_improvement.router, prefix=settings.api_prefix)
    return app


app = create_app()
