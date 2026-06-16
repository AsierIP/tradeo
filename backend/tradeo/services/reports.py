from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from tradeo.core.config import Settings, get_settings
from tradeo.db.models import AuditLog, EquityPoint, PatternMetric, Signal, Trade
from tradeo.services.runtime_status import entry_scan_status, worker_runtime_status
from tradeo.services.system_controls import runtime_kill_switch


class ReportService:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def generate_review_pack(self, db: Session) -> dict[str, Any]:
        now = datetime.now(timezone.utc)
        row_limits = {
            "signals": 50,
            "trades": 50,
            "equity": 200,
            "audit_tail": 100,
        }
        signals = (
            db.query(Signal).order_by(Signal.created_at.desc()).limit(row_limits["signals"]).all()
        )
        trades = db.query(Trade).order_by(Trade.opened_at.desc()).limit(row_limits["trades"]).all()
        metrics = db.query(PatternMetric).all()
        equity = (
            db.query(EquityPoint)
            .order_by(EquityPoint.timestamp.desc())
            .limit(row_limits["equity"])
            .all()
        )
        audits = (
            db.query(AuditLog)
            .order_by(AuditLog.timestamp.desc())
            .limit(row_limits["audit_tail"])
            .all()
        )
        runtime_control = runtime_kill_switch(db)
        pack: dict[str, Any] = {
            "generated_at_utc": now.isoformat(),
            "mode": self.settings.trading_mode,
            "live_armed": self.settings.live_armed,
            "kill_switch_enabled": self.settings.kill_switch_enabled,
            "runtime_kill_switch_enabled": bool(runtime_control and runtime_control.enabled),
            "runtime_kill_switch": self._runtime_kill_switch_to_dict(runtime_control),
            "runtime_status": {
                "worker": worker_runtime_status(self.settings),
                "entry_scans": {
                    "laboratory": entry_scan_status("laboratory", self.settings),
                    "fox_hunter": entry_scan_status("fox_hunter", self.settings),
                },
            },
            "report_metadata": {
                "schema_version": 1,
                "row_limits": row_limits,
                "returned_counts": {
                    "signals": len(signals),
                    "trades": len(trades),
                    "metrics": len(metrics),
                    "equity": len(equity),
                    "audit_tail": len(audits),
                },
            },
            "risk_policy": {
                "initial_capital_usd": self.settings.initial_capital_usd,
                "risk_per_trade_pct": self.settings.risk_per_trade_pct,
                "risk_per_trade_usd": self.settings.account_risk_usd,
                "daily_loss_limit_pct": self.settings.daily_loss_limit_pct,
                "min_reward_risk": self.settings.min_reward_risk,
                "max_open_positions": self.settings.max_open_positions,
                "allow_shorts": self.settings.allow_shorts,
                "allow_options": self.settings.allow_options,
                "allow_margin": self.settings.allow_margin,
            },
            "signals": [self._signal_to_dict(s) for s in signals],
            "trades": [self._trade_to_dict(t) for t in trades],
            "metrics": [self._metric_to_dict(m) for m in metrics],
            "equity": [
                {
                    "timestamp": e.timestamp.isoformat(),
                    "equity": e.equity,
                    "cash": e.cash,
                    "open_risk": e.open_risk,
                }
                for e in reversed(equity)
            ],
            "audit_tail": [
                {
                    "timestamp": a.timestamp.isoformat(),
                    "actor": a.actor,
                    "action": a.action,
                    "entity_type": a.entity_type,
                    "entity_id": a.entity_id,
                    "details": a.details_json,
                }
                for a in audits
            ],
            "director_prompt": self._director_prompt(),
        }
        json_path = self._write_json(pack, now)
        md_path = self._write_markdown(pack, now)
        pack["paths"] = {"json": str(json_path), "markdown": str(md_path)}
        return pack

    def latest_report(self) -> dict[str, Any] | None:
        reports = sorted(self.settings.reports_path.glob("tradeo_review_*.json"), reverse=True)
        skipped_invalid: list[dict[str, str]] = []
        for path in reports:
            try:
                report = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                skipped_invalid.append({"path": str(path), "reason": exc.__class__.__name__})
                continue
            if not isinstance(report, dict):
                skipped_invalid.append({"path": str(path), "reason": "non_object_json"})
                continue
            report["_latest_report_read"] = {
                "path": str(path),
                "skipped_invalid_count": len(skipped_invalid),
                "skipped_invalid_reports": skipped_invalid[:5],
            }
            return report
        return None

    def _write_json(self, pack: dict[str, Any], now: datetime) -> Path:
        path = self.settings.reports_path / f"tradeo_review_{now:%Y%m%d_%H%M%S}.json"
        _write_text_atomic(path, json.dumps(pack, indent=2, default=str))
        return path

    def _write_markdown(self, pack: dict[str, Any], now: datetime) -> Path:
        path = self.settings.reports_path / f"tradeo_review_{now:%Y%m%d_%H%M%S}.md"
        runtime = pack["runtime_status"]
        lines = [
            f"# Tradeo review pack - {pack['generated_at_utc']}",
            "",
            "## Estado",
            f"- Modo: {pack['mode']}",
            f"- Live armado: {pack['live_armed']}",
            f"- Kill switch env: {pack['kill_switch_enabled']}",
            f"- Kill switch runtime: {pack['runtime_kill_switch_enabled']}",
            f"- Worker: {runtime['worker']['state']} ({runtime['worker']['reason']})",
            "",
            "## Riesgo",
            f"- Capital inicial: {pack['risk_policy']['initial_capital_usd']} USD",
            f"- Riesgo por operación: {pack['risk_policy']['risk_per_trade_usd']} USD",
            f"- R:R mínimo: {pack['risk_policy']['min_reward_risk']}",
            "",
            "## Señales recientes",
        ]
        for s in pack["signals"][:15]:
            lines.append(
                f"- {s['symbol']} {s['side']} {s['pattern']} status={s['status']} "
                f"entry={s['entry']} stop={s['stop']} target={s['target']} "
                f"RR={s['reward_risk']} conf={s['confidence']}"
            )
        lines.extend(["", "## Prompt para revisión externa", "", pack["director_prompt"]])
        _write_text_atomic(path, "\n".join(lines))
        return path

    def _director_prompt(self) -> str:
        return (
            "Actúa como Director General de Tradeo. Revisa este paquete JSON. "
            "Evalúa si cada patrón técnico tiene coherencia geométrica, riesgo controlado, "
            "R:R mínimo 1:4, liquidez suficiente y ausencia de inconsistencias. "
            "No apruebes operativa real si hay menos de 40 operaciones históricas por versión, "
            "profit factor < 1.8, expectancy <= 0.25R o drawdown máximo > 12%. "
            "Devuelve: aprobar/rechazar, razones, cambios propuestos y próximos experimentos."
        )

    def _signal_to_dict(self, s: Signal) -> dict[str, Any]:
        return {
            "id": s.id,
            "symbol": s.symbol,
            "pattern": s.pattern,
            "side": s.side,
            "timeframe": s.timeframe,
            "entry": s.entry,
            "stop": s.stop,
            "target": s.target,
            "reward_risk": s.reward_risk,
            "confidence": s.confidence,
            "status": s.status.value,
            "human_approved": s.human_approved,
            "created_at": s.created_at.isoformat(),
            "notes": s.supervisor_notes,
            "metadata": s.metadata_json,
        }

    def _trade_to_dict(self, t: Trade) -> dict[str, Any]:
        return {
            "id": t.id,
            "symbol": t.symbol,
            "pattern": t.pattern,
            "side": t.side,
            "qty": t.qty,
            "entry": t.entry,
            "stop": t.stop,
            "target": t.target,
            "status": t.status.value,
            "pnl_usd": t.pnl_usd,
            "r_multiple": t.r_multiple,
            "opened_at": t.opened_at.isoformat(),
            "closed_at": t.closed_at.isoformat() if t.closed_at else None,
        }

    def _metric_to_dict(self, m: PatternMetric) -> dict[str, Any]:
        return {
            "pattern": m.pattern,
            "strategy_version": m.strategy_version,
            "total_trades": m.total_trades,
            "win_rate": m.win_rate,
            "profit_factor": m.profit_factor,
            "expectancy_r": m.expectancy_r,
            "max_drawdown_pct": m.max_drawdown_pct,
            "avg_r_multiple": m.avg_r_multiple,
        }

    @staticmethod
    def _runtime_kill_switch_to_dict(control: Any | None) -> dict[str, Any]:
        if control is None:
            return {
                "enabled": False,
                "reason": None,
                "actor": None,
                "updated_at": None,
                "details": {},
            }
        return {
            "enabled": bool(control.enabled),
            "reason": control.reason,
            "actor": control.actor,
            "updated_at": control.updated_at.isoformat() if control.updated_at else None,
            "details": control.details_json or {},
        }


def _write_text_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
        os.replace(tmp_name, path)
    except Exception:
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass
        raise
