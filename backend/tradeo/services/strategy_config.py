from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_strategy_config(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    if p.exists():
        return json.loads(p.read_text())
    return {
        "name": "cup_v0",
        "pattern": "mid_small_cap_cup_breakout",
        "target_r_multiple": 4.0,
        "min_confidence": 0.68,
        "min_composite_score": 0.70,
        "max_holding_bars": 30,
    }
