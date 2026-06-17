"""DB <-> IBKR reconciliation with automatic kill switch (informe §4.5).

On every run we compare what the database believes is open against what IBKR
reports (positions + open orders). Any confirmed divergence means the system's
model of its own exposure is wrong, which is exactly the failure mode the kill
switch exists for — so divergence activates the runtime kill switch and the
order paths stop until a human investigates.

Beyond symbol existence, reconciliation is explicit about *how much* and
*which order*:

- ``position_qty_mismatch_at_broker``: per symbol, the signed broker position
  is compared against the signed quantity the DB expects (sum of open IBKR
  trades, shorts negative). A position larger than expected, on the wrong
  side, or smaller with no open orders that could still fill it, is a
  divergence. A smaller-than-expected position *with* pending open orders on
  the symbol is the normal partial-entry state, so it is recorded as a
  warning, not a divergence.
- ``db_order_id_missing_at_broker``: a DB trade whose symbol shows up at the
  broker only through open orders must find its ``broker_order_id`` among
  those orders (as order id, perm id, or the parent id bracket children point
  to); otherwise the orders the broker holds are not the orders we think we
  placed.
- ``partial_fill_open_order``: an open order with ``0 < filled < quantity``
  is a legitimate transient state, never a divergence — it is surfaced as a
  warning and audited so partial fills are observable instead of silent.

Connection failures are NOT divergences: the broker being unreachable proves
nothing about state mismatch. They are audited and surfaced, never escalated
to the kill switch automatically. Warnings likewise never trip the kill
switch.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from loguru import logger
from sqlalchemy.orm import Session

from tradeo.core.config import Settings, get_settings
from tradeo.db.models import AuditLog, Trade, TradeStatus
from tradeo.services.evidence import EvidenceQuality, EvidenceType, FillProvenance
from tradeo.services.execution_quality import persist_execution_quality
from tradeo.services.ibkr_broker import IBKRBroker
from tradeo.services.system_controls import (
    activate_runtime_kill_switch,
    runtime_kill_switch_active,
)

__all__ = ["ReconciliationService"]


def _is_ibkr_trade(trade: Trade) -> bool:
    metadata = trade.metadata_json or {}
    return str(metadata.get("execution_mode") or "") == "ibkr"


def _signed_qty(trade: Trade) -> float:
    sign = -1.0 if str(trade.side or "").lower().strip() == "short" else 1.0
    return sign * abs(float(trade.qty or 0))


def _order_matches_trade(order: dict[str, Any], broker_order_id: str) -> bool:
    """True when an open-order row references the trade's broker order id.

    Bracket children carry their own ids but point back to the parent via
    ``parent_order_id``, so a trade whose parent leg already filled is still
    matched through its surviving child legs.
    """
    for key in ("order_id", "perm_id", "parent_order_id"):
        value = order.get(key)
        if value is not None and str(value) == broker_order_id:
            return True
    return False


def _broker_fills(broker: Any) -> list[dict[str, Any]]:
    fills = getattr(broker, "fills", None)
    if not callable(fills):
        return []
    rows = fills()
    if rows is None:
        return []
    return list(rows)


def _parse_ts(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        parsed = value
    else:
        text = str(value).strip()
        if not text:
            return None
        if text.endswith("Z"):
            text = f"{text[:-1]}+00:00"
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError:
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _iso_ts(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def _float_or_none(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _str_set(*values: Any) -> set[str]:
    output: set[str] = set()
    for value in values:
        if isinstance(value, (list, tuple, set)):
            output.update(_str_set(*value))
            continue
        if value is None:
            continue
        text = str(value).strip()
        if text:
            output.add(text)
    return output


def _stable_hash(payload: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()


def _fill_hash(fill: dict[str, Any]) -> str:
    existing = fill.get("fill_id_hash") or fill.get("broker_execution_hash")
    if existing:
        return str(existing)
    return _stable_hash(
        {
            "exec_id": fill.get("exec_id"),
            "order_id": fill.get("order_id"),
            "perm_id": fill.get("perm_id"),
            "symbol": fill.get("symbol"),
            "time": fill.get("execution_time") or fill.get("time"),
            "price": fill.get("price"),
            "quantity": fill.get("quantity"),
        }
    )


def _normal_action(value: Any) -> str:
    action = str(value or "").upper().strip()
    if action in {"BOT", "BUY", "BOUGHT"}:
        return "BUY"
    if action in {"SLD", "SELL", "SOLD"}:
        return "SELL"
    return action


def _entry_action(trade: Trade) -> str:
    return "SELL" if str(trade.side or "").lower().strip() == "short" else "BUY"


def _exit_action(trade: Trade) -> str:
    return "BUY" if _entry_action(trade) == "SELL" else "SELL"


def _metadata_order_ids(metadata: dict[str, Any], leg: str | None = None) -> set[str]:
    if leg is None:
        return _str_set(metadata.get("broker_order_id"), metadata.get("parent_order_id"), metadata.get("order_ids"))
    ids: set[str] = set()
    if leg is not None:
        ids.update(_str_set(metadata.get(f"{leg}_order_id")))
        legs = metadata.get("bracket_legs")
        if isinstance(legs, dict) and isinstance(legs.get(leg), dict):
            ids.update(_str_set(legs[leg].get("order_id")))
        order_ids = metadata.get("order_ids")
        if isinstance(order_ids, list):
            if leg == "entry" and len(order_ids) >= 1:
                ids.update(_str_set(order_ids[0]))
            elif leg == "target" and len(order_ids) >= 2:
                ids.update(_str_set(order_ids[1]))
            elif leg == "stop" and len(order_ids) >= 3:
                ids.update(_str_set(order_ids[2]))
        if leg == "entry":
            ids.update(_str_set(metadata.get("broker_order_id"), metadata.get("parent_order_id")))
    return ids


def _metadata_perm_ids(metadata: dict[str, Any], leg: str | None = None) -> set[str]:
    if leg is None:
        return _str_set(metadata.get("perm_ids"))
    ids: set[str] = set()
    if leg is not None:
        ids.update(_str_set(metadata.get(f"{leg}_perm_id")))
        legs = metadata.get("bracket_legs")
        if isinstance(legs, dict) and isinstance(legs.get(leg), dict):
            ids.update(_str_set(legs[leg].get("perm_id")))
        perm_ids = metadata.get("perm_ids")
        if isinstance(perm_ids, list):
            if leg == "entry" and len(perm_ids) >= 1:
                ids.update(_str_set(perm_ids[0]))
            elif leg == "target" and len(perm_ids) >= 2:
                ids.update(_str_set(perm_ids[1]))
            elif leg == "stop" and len(perm_ids) >= 3:
                ids.update(_str_set(perm_ids[2]))
    return ids


def _fill_matches_trade(fill: dict[str, Any], trade: Trade) -> bool:
    metadata = trade.metadata_json or {}
    fill_order_ids = _str_set(fill.get("order_id"))
    fill_perm_ids = _str_set(fill.get("perm_id"))
    if fill_order_ids & _metadata_order_ids(metadata):
        return True
    if fill_perm_ids & _metadata_perm_ids(metadata):
        return True
    if trade.broker_order_id and str(trade.broker_order_id) in fill_order_ids:
        return True
    return False


def _fill_has_broker_identity(fill: dict[str, Any]) -> bool:
    return bool(
        _str_set(
            fill.get("order_id"),
            fill.get("perm_id"),
            fill.get("exec_id"),
            fill.get("fill_id"),
            fill.get("fill_id_hash"),
            fill.get("broker_execution_hash"),
        )
    )


def _fill_not_before_trade(fill: dict[str, Any], trade: Trade) -> bool:
    fill_time = _parse_ts(fill.get("execution_time") or fill.get("time"))
    if fill_time is None:
        return False
    metadata = trade.metadata_json or {}
    trade_time = _parse_ts(metadata.get("submitted_at")) or _parse_ts(trade.opened_at)
    return trade_time is not None and fill_time >= trade_time


def _fill_timestamp_not_before_trade_if_present(fill: dict[str, Any], trade: Trade) -> bool:
    fill_time = _parse_ts(fill.get("execution_time") or fill.get("time"))
    if fill_time is None:
        return True
    metadata = trade.metadata_json or {}
    trade_time = _parse_ts(metadata.get("submitted_at")) or _parse_ts(trade.opened_at)
    return trade_time is None or fill_time >= trade_time


def _match_fill_to_trade(fill: dict[str, Any], trades: list[Trade]) -> Trade | None:
    exact = [
        trade
        for trade in trades
        if _fill_matches_trade(fill, trade)
        and _fill_timestamp_not_before_trade_if_present(fill, trade)
    ]
    if len(exact) == 1:
        return exact[0]
    if len(exact) > 1:
        return None
    if _fill_has_broker_identity(fill):
        return None
    symbol = str(fill.get("symbol") or "").upper().strip()
    if not symbol:
        return None
    same_symbol = [
        trade
        for trade in trades
        if trade.status == TradeStatus.OPEN
        and trade.symbol.upper() == symbol
        and _is_ibkr_trade(trade)
        and _fill_not_before_trade(fill, trade)
    ]
    return same_symbol[0] if len(same_symbol) == 1 else None


def _leg_for_fill(fill: dict[str, Any], trade: Trade, metadata: dict[str, Any]) -> str:
    order_ids = _str_set(fill.get("order_id"))
    perm_ids = _str_set(fill.get("perm_id"))
    if order_ids & _metadata_order_ids(metadata, "entry") or perm_ids & _metadata_perm_ids(metadata, "entry"):
        return "entry"
    if order_ids & (
        _metadata_order_ids(metadata, "target") | _metadata_order_ids(metadata, "stop")
    ) or perm_ids & (_metadata_perm_ids(metadata, "target") | _metadata_perm_ids(metadata, "stop")):
        return "exit"
    action = _normal_action(fill.get("side") or fill.get("action"))
    if action == _entry_action(trade):
        return "entry"
    if action == _exit_action(trade):
        return "exit"
    entry_qty = _float_or_none(metadata.get("entry_fill_qty")) or 0.0
    return "entry" if entry_qty < abs(float(trade.qty or 0)) else "exit"


def _fill_record(fill: dict[str, Any], trade: Trade, leg: str) -> dict[str, Any]:
    fill_hash = _fill_hash(fill)
    return {
        "fill_id_hash": fill_hash,
        "broker_execution_hash": fill_hash,
        "leg": leg,
        "symbol": str(fill.get("symbol") or trade.symbol).upper(),
        "side": _normal_action(fill.get("side") or fill.get("action")),
        "quantity": _float_or_none(fill.get("quantity") or fill.get("shares")) or 0.0,
        "price": _float_or_none(fill.get("price") or fill.get("avg_price")) or 0.0,
        "execution_time": fill.get("execution_time") or fill.get("time"),
        "order_id": None if fill.get("order_id") is None else str(fill.get("order_id")),
        "perm_id": None if fill.get("perm_id") is None else str(fill.get("perm_id")),
        "exec_id_hash": _stable_hash({"exec_id": fill.get("exec_id")}) if fill.get("exec_id") else fill_hash,
        "commission": _float_or_none(fill.get("commission")),
        "commission_currency": fill.get("commission_currency") or fill.get("currency"),
        "realized_pnl": _float_or_none(fill.get("realized_pnl")),
        "exchange": fill.get("exchange"),
        "account_id_redacted": True,
    }


def _merge_fill_records(existing: list[dict[str, Any]], incoming: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_hash: dict[str, dict[str, Any]] = {}
    for record in existing + incoming:
        fill_hash = str(record.get("fill_id_hash") or record.get("broker_execution_hash") or "")
        if not fill_hash:
            continue
        current = by_hash.get(fill_hash, {})
        by_hash[fill_hash] = {**current, **{key: value for key, value in record.items() if value is not None}}
    return sorted(
        by_hash.values(),
        key=lambda row: (
            _parse_ts(row.get("execution_time")) or datetime.min.replace(tzinfo=timezone.utc),
            str(row.get("fill_id_hash") or ""),
        ),
    )


def _leg_summary(records: list[dict[str, Any]], leg: str) -> dict[str, Any] | None:
    rows = [row for row in records if row.get("leg") == leg]
    if not rows:
        return None
    qty = sum(abs(float(row.get("quantity") or 0.0)) for row in rows)
    priced_qty = sum(
        abs(float(row.get("quantity") or 0.0))
        for row in rows
        if float(row.get("price") or 0.0) > 0
    )
    if priced_qty <= 0:
        return None
    avg_price = (
        sum(
            abs(float(row.get("quantity") or 0.0)) * float(row.get("price") or 0.0)
            for row in rows
            if float(row.get("price") or 0.0) > 0
        )
        / priced_qty
    )
    timestamps = [_parse_ts(row.get("execution_time")) for row in rows]
    timestamps = [value for value in timestamps if value is not None]
    commissions = [row.get("commission") for row in rows if row.get("commission") is not None]
    return {
        "qty": qty,
        "avg_price": avg_price,
        "first_time": min(timestamps) if timestamps else None,
        "last_time": max(timestamps) if timestamps else None,
        "commission": sum(float(value) for value in commissions) if commissions else None,
        "hashes": [row["fill_id_hash"] for row in rows if row.get("fill_id_hash")],
        "missing_commission_count": len(rows) - len(commissions),
        "missing_timestamp_count": len(rows) - len(timestamps),
    }


def _exit_reason_for_fill(trade: Trade, records: list[dict[str, Any]], exit_price: float) -> str:
    metadata = trade.metadata_json or {}
    exit_order_ids = _metadata_order_ids(metadata, "target")
    exit_perm_ids = _metadata_perm_ids(metadata, "target")
    stop_order_ids = _metadata_order_ids(metadata, "stop")
    stop_perm_ids = _metadata_perm_ids(metadata, "stop")
    for record in records:
        if record.get("leg") != "exit":
            continue
        order_ids = _str_set(record.get("order_id"))
        perm_ids = _str_set(record.get("perm_id"))
        if order_ids & exit_order_ids or perm_ids & exit_perm_ids:
            return "target_hit"
        if order_ids & stop_order_ids or perm_ids & stop_perm_ids:
            return "stop_hit"
    target_delta = abs(exit_price - float(trade.target or 0.0))
    stop_delta = abs(exit_price - float(trade.stop or 0.0))
    return "target_hit" if target_delta <= stop_delta else "stop_hit"


def _metadata_entry_variant_id(metadata: dict[str, Any]) -> str:
    direct = str(metadata.get("entry_variant_id") or "").strip()
    if direct:
        return direct
    variant = metadata.get("entry_variant")
    if isinstance(variant, dict):
        return str(variant.get("id") or "").strip()
    return ""


def _metadata_regime_key(metadata: dict[str, Any]) -> str:
    direct = str(metadata.get("regime_key") or "").strip()
    if direct:
        return direct
    regime = metadata.get("regime")
    if isinstance(regime, dict):
        return str(regime.get("regime_key") or "").strip()
    return ""


def _apply_fill_records(trade: Trade, records: list[dict[str, Any]], now: datetime) -> bool:
    metadata = dict(trade.metadata_json or {})
    existing = metadata.get("ibkr_fills") if isinstance(metadata.get("ibkr_fills"), list) else []
    existing = [record for record in existing if _fill_matches_trade(record, trade)]
    merged_records = _merge_fill_records(existing, records)
    previous_records = metadata.get("ibkr_fills") if isinstance(metadata.get("ibkr_fills"), list) else []
    if merged_records == previous_records:
        return False

    entry = _leg_summary(merged_records, "entry")
    exit_leg = _leg_summary(merged_records, "exit")
    metadata["ibkr_fills"] = merged_records
    metadata["fill_provenance"] = FillProvenance.BROKER_EXECUTION.value
    metadata["fill_provenance_reconciled"] = True
    metadata["last_fill_reconciled_at"] = now.isoformat()
    metadata["broker_execution_hash"] = merged_records[0]["broker_execution_hash"]
    metadata["fill_id_hash"] = merged_records[0]["fill_id_hash"]
    entry_variant_id = _metadata_entry_variant_id(metadata)
    regime_key = _metadata_regime_key(metadata)
    if entry_variant_id:
        metadata["entry_variant_id"] = entry_variant_id
    else:
        metadata["entry_variant_missing"] = True
    if regime_key:
        metadata["regime_key"] = regime_key
    else:
        metadata["regime_key_missing"] = True

    total_commission = 0.0
    commission_seen = False
    missing_commission_count = 0
    missing_timestamp_count = 0
    for summary in (entry, exit_leg):
        if summary is None:
            continue
        missing_commission_count += int(summary["missing_commission_count"])
        missing_timestamp_count += int(summary["missing_timestamp_count"])
        if summary["commission"] is not None:
            total_commission += float(summary["commission"])
            commission_seen = True
    if commission_seen:
        metadata["commission"] = round(total_commission, 6)
        metadata["commission_usd"] = round(total_commission, 6)
        metadata["commission_source"] = "ibkr_commission_report"
        metadata["cost_provenance_reconciled"] = missing_commission_count == 0
        if missing_commission_count:
            metadata["commission_missing"] = True
            metadata["commission_missing_fill_count"] = missing_commission_count
        else:
            metadata.pop("commission_missing", None)
            metadata["commission_missing_fill_count"] = 0
    else:
        metadata["commission_missing"] = True
        metadata["commission_missing_fill_count"] = missing_commission_count
    if missing_timestamp_count:
        metadata["broker_timestamp_missing"] = True
        metadata["broker_timestamp_missing_fill_count"] = missing_timestamp_count
        metadata["timestamp_provenance_reconciled"] = False
    else:
        metadata.pop("broker_timestamp_missing", None)
        metadata["broker_timestamp_missing_fill_count"] = 0
        metadata["timestamp_provenance_reconciled"] = True

    if entry is not None:
        all_provenance_present = (
            commission_seen
            and missing_commission_count == 0
            and missing_timestamp_count == 0
        )
        metadata["entry_fill_price"] = round(float(entry["avg_price"]), 6)
        metadata["entry_fill_qty"] = round(float(entry["qty"]), 6)
        metadata["entry_fill_time"] = _iso_ts(entry["first_time"])
        metadata["entry_broker_execution_time"] = _iso_ts(entry["first_time"])
        metadata["entry_broker_execution_hash"] = entry["hashes"][0]
        metadata["entry_fill_id_hash"] = entry["hashes"][0]
        metadata["evidence_type"] = (
            EvidenceType.LIVE_FILL.value
            if metadata.get("ibkr_mode") == "live"
            else EvidenceType.IBKR_PAPER_FILL.value
        )
        metadata["evidence_quality"] = EvidenceQuality.NORMAL.value if all_provenance_present else EvidenceQuality.DEGRADED.value
        trade.evidence_type = metadata["evidence_type"]
        trade.evidence_quality = metadata["evidence_quality"]
        if trade.opened_at is None and entry["first_time"] is not None:
            trade.opened_at = entry["first_time"]

    if exit_leg is not None:
        exit_price = round(float(exit_leg["avg_price"]), 6)
        exit_time = exit_leg["last_time"] or exit_leg["first_time"]
        metadata["exit_fill_price"] = exit_price
        metadata["exit_fill_qty"] = round(float(exit_leg["qty"]), 6)
        metadata["exit_fill_time"] = _iso_ts(exit_time)
        metadata["exit_broker_execution_time"] = _iso_ts(exit_time)
        metadata["exit_broker_execution_hash"] = exit_leg["hashes"][-1]
        metadata["exit_fill_id_hash"] = exit_leg["hashes"][-1]
        metadata["exit_reason"] = _exit_reason_for_fill(trade, merged_records, exit_price)
        if entry is not None and float(exit_leg["qty"]) >= min(abs(float(trade.qty or 0)), float(entry["qty"])):
            trade.status = TradeStatus.CLOSED
            trade.closed_at = exit_time or now
            trade.exit_price = exit_price
            sign = -1.0 if str(trade.side or "").lower().strip() == "short" else 1.0
            entry_price = float(entry["avg_price"])
            gross_pnl = (exit_price - entry_price) * sign * abs(float(trade.qty or 0))
            risk_per_share = abs(float(trade.entry or 0.0) - float(trade.stop or 0.0))
            trade.pnl_usd = round(gross_pnl, 6)
            trade.r_multiple = round(gross_pnl / (risk_per_share * abs(float(trade.qty or 0))), 6) if risk_per_share > 0 and trade.qty else 0.0
            opened_at = _parse_ts(trade.opened_at)
            closed_at = _parse_ts(trade.closed_at)
            metadata["holding_period_seconds"] = (
                round((closed_at - opened_at).total_seconds(), 3)
                if closed_at is not None and opened_at is not None
                else None
            )

    if entry is not None:
        sign = -1.0 if str(trade.side or "").lower().strip() == "short" else 1.0
        theoretical_entry = float(trade.entry or 0.0)
        if theoretical_entry > 0:
            entry_shortfall = (float(entry["avg_price"]) - theoretical_entry) * sign
            metadata["realized_entry_slippage_usd"] = round(entry_shortfall, 6)
            metadata["realized_entry_slippage_bps"] = round(entry_shortfall / theoretical_entry * 10_000.0, 6)
            metadata["slippage_source"] = "ibkr_fill_vs_signal_entry"
            metadata["slippage_provenance_reconciled"] = True
        else:
            metadata["slippage_missing"] = True
            metadata["slippage_provenance_reconciled"] = False
    if "estimated_spread_cost" not in metadata:
        metadata["estimated_spread_cost"] = 0.0
    if "estimated_slippage" not in metadata:
        metadata["estimated_slippage"] = 0.0
    metadata.setdefault("spread_cost_source", "not_captured_zero_default")
    metadata.setdefault("slippage_source", "ibkr_fill_vs_signal_entry")

    trade.metadata_json = metadata
    persist_execution_quality([trade])
    return True


@dataclass(slots=True)
class ReconciliationService:
    settings: Settings | None = None
    broker: IBKRBroker | None = None

    def __post_init__(self) -> None:
        self.settings = self.settings or get_settings()
        self.broker = self.broker or IBKRBroker(self.settings)

    def _ingest_recent_fills(
        self,
        db: Session,
        fills: list[dict[str, Any]],
        *,
        now: datetime,
    ) -> dict[str, Any]:
        candidate_trades = db.query(Trade).all()
        matched: dict[int, list[dict[str, Any]]] = {}
        unmatched: list[dict[str, Any]] = []
        for fill in fills:
            trade = _match_fill_to_trade(fill, candidate_trades)
            if trade is None:
                unmatched.append(
                    {
                        "symbol": fill.get("symbol"),
                        "order_id": fill.get("order_id"),
                        "perm_id": fill.get("perm_id"),
                        "fill_id_hash": _fill_hash(fill),
                    }
                )
                continue
            metadata = dict(trade.metadata_json or {})
            leg = _leg_for_fill(fill, trade, metadata)
            matched.setdefault(int(trade.id), []).append(_fill_record(fill, trade, leg))

        updated_trades: list[int] = []
        closed_trades: list[int] = []
        for trade_id, records in matched.items():
            trade = next((row for row in candidate_trades if int(row.id) == trade_id), None)
            if trade is None:
                continue
            previous_status = trade.status
            if _apply_fill_records(trade, records, now):
                updated_trades.append(trade_id)
                if previous_status != TradeStatus.CLOSED and trade.status == TradeStatus.CLOSED:
                    closed_trades.append(trade_id)

        if updated_trades or unmatched:
            db.add(
                AuditLog(
                    actor="reconciliation",
                    action="ibkr_fills_ingested",
                    entity_type="system",
                    entity_id="ibkr",
                    details_json={
                        "broker_fill_count": len(fills),
                        "matched_trade_count": len(updated_trades),
                        "closed_trade_count": len(closed_trades),
                        "updated_trade_ids": updated_trades,
                        "closed_trade_ids": closed_trades,
                        "unmatched_fill_count": len(unmatched),
                        "unmatched_fills": unmatched[:20],
                    },
                )
            )
        return {
            "broker_fills": len(fills),
            "fills_ingested": sum(len(records) for records in matched.values()),
            "trades_updated_from_fills": len(updated_trades),
            "trades_closed_from_fills": len(closed_trades),
            "unmatched_fills": len(unmatched),
        }

    def reconcile(self, db: Session) -> dict[str, Any]:
        settings = self.settings
        assert settings is not None
        now = datetime.now(timezone.utc)
        pre_fill_open_trades = (
            db.query(Trade)
            .filter(Trade.status == TradeStatus.OPEN)
            .all()
        )
        pre_fill_open_ibkr_count = len([trade for trade in pre_fill_open_trades if _is_ibkr_trade(trade)])
        assert self.broker is not None
        fill_fetch_error: str | None = None
        try:
            fills = _broker_fills(self.broker)
        except Exception as exc:  # noqa: BLE001
            fills = []
            fill_fetch_error = f"{type(exc).__name__}: {exc}"
            logger.warning("reconciliation fill import skipped: {}", exc)
            db.add(
                AuditLog(
                    actor="reconciliation",
                    action="ibkr_fills_unavailable",
                    entity_type="system",
                    entity_id="ibkr",
                    details_json={
                        "error": fill_fetch_error,
                        "db_open_ibkr_trades": pre_fill_open_ibkr_count,
                    },
                )
            )
        try:
            positions = self.broker.positions()
            open_orders = self.broker.open_orders()
        except Exception as exc:  # noqa: BLE001
            # Unreachable broker is an availability problem, not a state
            # divergence; never auto-trip the kill switch on it.
            logger.warning("reconciliation skipped: broker unreachable: {}", exc)
            db.add(
                AuditLog(
                    actor="reconciliation",
                    action="reconciliation_broker_unreachable",
                    entity_type="system",
                    entity_id="ibkr",
                    details_json={
                        "error": f"{type(exc).__name__}: {exc}",
                        "db_open_ibkr_trades": pre_fill_open_ibkr_count,
                    },
                )
            )
            db.commit()
            return {
                "ok": False,
                "checked_at": now.isoformat(),
                "db_open_ibkr_trades": pre_fill_open_ibkr_count,
                "broker_positions": 0,
                "broker_open_orders": 0,
                "broker_fills": 0,
                "fills_ingested": 0,
                "trades_updated_from_fills": 0,
                "trades_closed_from_fills": 0,
                "unmatched_fills": 0,
                "divergences": [],
                "warnings": [
                    {"kind": "broker_fills_unavailable", "error": fill_fetch_error}
                ]
                if fill_fetch_error
                else [],
                "kill_switch_activated": False,
                "kill_switch_already_active": runtime_kill_switch_active(db),
                "error": f"broker_unreachable: {exc}",
            }

        fill_ingestion = self._ingest_recent_fills(db, fills, now=now)
        open_trades = (
            db.query(Trade)
            .filter(Trade.status == TradeStatus.OPEN)
            .all()
        )
        db_ibkr_trades = [trade for trade in open_trades if _is_ibkr_trade(trade)]
        result: dict[str, Any] = {
            "ok": True,
            "checked_at": now.isoformat(),
            "db_open_ibkr_trades": len(db_ibkr_trades),
            "broker_positions": 0,
            "broker_open_orders": 0,
            **fill_ingestion,
            "fill_fetch_error": fill_fetch_error,
            "divergences": [],
            "warnings": [],
            "kill_switch_activated": False,
            "kill_switch_already_active": runtime_kill_switch_active(db),
        }

        position_qty: dict[str, float] = {}
        for row in positions:
            symbol = str(row.get("symbol") or "").upper()
            qty = float(row.get("position") or 0.0)
            if symbol and abs(qty) > 0:
                position_qty[symbol] = position_qty.get(symbol, 0.0) + qty
        position_symbols = set(position_qty)
        orders_by_symbol: dict[str, list[dict[str, Any]]] = {}
        for row in open_orders:
            symbol = str(row.get("symbol") or "").upper()
            orders_by_symbol.setdefault(symbol, []).append(row)
        order_symbols = set(orders_by_symbol)
        db_symbols = {trade.symbol.upper() for trade in db_ibkr_trades}
        result["broker_positions"] = len(position_symbols)
        result["broker_open_orders"] = len(open_orders)

        divergences: list[dict[str, Any]] = []
        warnings: list[dict[str, Any]] = []
        if fill_fetch_error:
            warnings.append({"kind": "broker_fills_unavailable", "error": fill_fetch_error})
        for trade in db_ibkr_trades:
            symbol = trade.symbol.upper()
            if symbol not in position_symbols and symbol not in order_symbols:
                divergences.append(
                    {
                        "kind": "db_open_trade_missing_at_broker",
                        "symbol": symbol,
                        "trade_id": trade.id,
                        "broker_order_id": trade.broker_order_id,
                    }
                )
            elif (
                symbol not in position_symbols
                and trade.broker_order_id
                and not any(
                    _order_matches_trade(order, str(trade.broker_order_id))
                    for order in orders_by_symbol.get(symbol, [])
                )
            ):
                divergences.append(
                    {
                        "kind": "db_order_id_missing_at_broker",
                        "symbol": symbol,
                        "trade_id": trade.id,
                        "broker_order_id": trade.broker_order_id,
                        "broker_open_order_ids": sorted(
                            str(order.get("order_id"))
                            for order in orders_by_symbol.get(symbol, [])
                            if order.get("order_id") is not None
                        ),
                    }
                )
        for symbol in sorted(position_symbols - db_symbols):
            divergences.append(
                {
                    "kind": "broker_position_not_in_db",
                    "symbol": symbol,
                }
            )

        expected_qty: dict[str, float] = {}
        for trade in db_ibkr_trades:
            symbol = trade.symbol.upper()
            expected_qty[symbol] = expected_qty.get(symbol, 0.0) + _signed_qty(trade)
        for symbol in sorted(position_symbols & set(expected_qty)):
            broker_qty = position_qty[symbol]
            db_qty = expected_qty[symbol]
            if broker_qty == db_qty:
                continue
            detail = {
                "symbol": symbol,
                "db_signed_qty": db_qty,
                "broker_signed_qty": broker_qty,
            }
            wrong_side = (broker_qty > 0) != (db_qty > 0)
            larger_than_expected = abs(broker_qty) > abs(db_qty)
            if not wrong_side and not larger_than_expected and symbol in order_symbols:
                # Smaller position with orders still working: the normal
                # partial-entry state, observable but not a divergence.
                warnings.append(
                    {"kind": "position_qty_below_db_pending_orders", **detail}
                )
                continue
            divergences.append({"kind": "position_qty_mismatch_at_broker", **detail})

        for symbol in sorted(order_symbols):
            for order in orders_by_symbol[symbol]:
                try:
                    filled = float(order.get("filled") or 0.0)
                    quantity = float(order.get("quantity") or 0.0)
                except (TypeError, ValueError):
                    continue
                if 0 < filled < quantity:
                    warnings.append(
                        {
                            "kind": "partial_fill_open_order",
                            "symbol": symbol,
                            "order_id": order.get("order_id"),
                            "filled": filled,
                            "quantity": quantity,
                            "remaining": order.get("remaining"),
                        }
                    )
        result["divergences"] = divergences
        result["warnings"] = warnings

        db.add(
            AuditLog(
                actor="reconciliation",
                action="reconciliation_completed",
                entity_type="system",
                entity_id="ibkr",
                details_json={
                    "db_open_ibkr_trades": len(db_ibkr_trades),
                    "broker_positions": sorted(position_symbols),
                    "broker_open_order_count": len(open_orders),
                    "divergence_count": len(divergences),
                    "divergences": divergences,
                    "warning_count": len(warnings),
                    "warnings": warnings,
                },
            )
        )
        if divergences and settings.reconciliation_auto_kill_switch:
            activate_runtime_kill_switch(
                db,
                reason="reconciliation divergence between DB open trades and IBKR state",
                actor="reconciliation",
                details={"divergences": divergences},
            )
            result["kill_switch_activated"] = True
            logger.error(
                "reconciliation divergence: kill switch activated ({} divergences)",
                len(divergences),
            )
        else:
            db.commit()
        return result
