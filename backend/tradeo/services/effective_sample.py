"""Effective-sample weights for Director paper-fill evidence (informe §4.7).

Paper fills that share the same symbol and trading day are not independent
observations of the edge: a burst of five AAPL fills on one afternoon is much
closer to one sample than to five. The Director gates therefore need an
*effective* sample size, not a raw fill count.

The weighting scheme is deliberately simple so it can be audited by hand:

- Each closed paper fill belongs to a cluster keyed by ``(symbol, trading
  day)`` where the day comes from ``closed_at`` (falling back to
  ``opened_at``).
- Each fill weighs ``1 / cluster_size``, so every cluster contributes exactly
  one effective sample regardless of how many fills landed in it.
- ``n_eff`` is the sum of weights, which equals the number of distinct
  clusters, and is the number gates compare against their minimums. The Kish
  effective sample size is reported alongside as a secondary diagnostic of
  weight inequality only (with equal weights it returns the raw count), so it
  is always >= ``n_eff`` and never used as the binding number.

Weights are persisted on each trade's ``metadata_json["effective_sample"]``
and the full per-trade breakdown is stored in the pattern's ``lab_execution``
metrics, so any ``n_eff`` used by a gate decision can be reproduced from the
stored rows alone.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable

from tradeo.db.models import Trade

EFFECTIVE_SAMPLE_METHOD = "inverse_symbol_day_cluster_size_v1"

__all__ = [
    "EFFECTIVE_SAMPLE_METHOD",
    "trade_cluster_key",
    "effective_sample_summary",
    "persist_effective_sample_weights",
]


def trade_cluster_key(trade: Trade) -> str:
    moment = trade.closed_at or trade.opened_at
    day = moment.date().isoformat() if moment is not None else "unknown"
    return f"{(trade.symbol or '').upper()}|{day}"


def effective_sample_summary(trades: Iterable[Trade]) -> dict[str, Any]:
    """Compute auditable per-trade weights and the resulting n_eff."""
    trades = list(trades)
    cluster_sizes: dict[str, int] = {}
    for trade in trades:
        key = trade_cluster_key(trade)
        cluster_sizes[key] = cluster_sizes.get(key, 0) + 1
    weights: list[dict[str, Any]] = []
    weight_values: list[float] = []
    for trade in trades:
        key = trade_cluster_key(trade)
        size = cluster_sizes[key]
        weight = 1.0 / size
        weight_values.append(weight)
        weights.append(
            {
                "trade_id": trade.id,
                "symbol": trade.symbol,
                "cluster_key": key,
                "cluster_size": size,
                "weight": round(weight, 6),
            }
        )
    total = sum(weight_values)
    sum_sq = sum(value * value for value in weight_values)
    kish = (total * total) / sum_sq if sum_sq > 0 else 0.0
    return {
        "method": EFFECTIVE_SAMPLE_METHOD,
        "n_trades": len(trades),
        "n_eff": round(total, 6),
        "kish_n_eff": round(kish, 6),
        "cluster_count": len(cluster_sizes),
        "cluster_sizes": dict(sorted(cluster_sizes.items())),
        "weights": weights,
    }


def persist_effective_sample_weights(
    trades: Iterable[Trade],
    summary: dict[str, Any],
) -> int:
    """Store each trade's weight in its metadata_json. Returns rows touched.

    The weight depends on the cluster composition at evaluation time, so the
    stored entry records the method and timestamp that produced it.
    """
    by_trade_id = {entry["trade_id"]: entry for entry in summary.get("weights", [])}
    now = datetime.now(timezone.utc).isoformat()
    touched = 0
    for trade in trades:
        entry = by_trade_id.get(trade.id)
        if entry is None:
            continue
        record = {
            "method": summary["method"],
            "cluster_key": entry["cluster_key"],
            "cluster_size": entry["cluster_size"],
            "weight": entry["weight"],
            "computed_at": now,
        }
        existing = (trade.metadata_json or {}).get("effective_sample")
        if existing and all(
            existing.get(key) == record[key]
            for key in ("method", "cluster_key", "cluster_size", "weight")
        ):
            continue
        trade.metadata_json = {**(trade.metadata_json or {}), "effective_sample": record}
        touched += 1
    return touched
