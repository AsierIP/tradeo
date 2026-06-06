from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


class VisionGeometryScorer:
    """Visual geometry scorer for cup-like price paths.

    This is intentionally separate from the rule detector. It looks at the normalized
    silhouette of the recent chart and scores whether the path is visually close to a
    rounded cup with a shallow handle.
    """

    def score(self, closes: pd.Series, handle_bars: int = 12) -> tuple[float, dict[str, Any]]:
        values = closes.dropna().to_numpy(dtype=float)
        if len(values) < 35:
            return 0.0, {"reason": "not_enough_points"}
        values = values[-min(len(values), 180) :]
        y = (values - values.min()) / max(1e-9, values.max() - values.min())
        x = np.linspace(-1, 1, len(y))
        # A rounded cup has higher sides and a lower middle. This template is not used
        # for execution alone; it is one vote in the supervisor ensemble.
        template = 1 - (1 - x**2)
        template = (template - template.min()) / max(1e-9, template.max() - template.min())
        corr = float(np.corrcoef(y, template)[0, 1]) if np.std(y) > 1e-9 else 0.0
        corr_score = max(0.0, corr)
        diffs = np.diff(y)
        roughness = float(np.mean(np.abs(np.diff(diffs)))) if len(diffs) > 2 else 1.0
        smooth_score = float(max(0.0, min(1.0, 1 - roughness * 8)))
        handle = y[-handle_bars:] if len(y) > handle_bars else y[-5:]
        handle_range = float(handle.max() - handle.min())
        handle_score = float(max(0.0, min(1.0, 1 - handle_range * 2.5)))
        score = 0.5 * corr_score + 0.3 * smooth_score + 0.2 * handle_score
        return float(max(0.0, min(1.0, score))), {
            "template_correlation": corr,
            "smooth_score": smooth_score,
            "handle_visual_score": handle_score,
        }


def render_pattern_chart(
    df: pd.DataFrame,
    symbol: str,
    output_dir: str | Path,
    entry: float | None = None,
    stop: float | None = None,
    target: float | None = None,
) -> str:
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{symbol}_pattern.png"
    window = df.tail(180)
    fig = plt.figure(figsize=(10, 5))
    ax = fig.add_subplot(111)
    ax.plot(window.index, window["close"], linewidth=1.4)
    if entry is not None:
        ax.axhline(entry, linestyle="--", linewidth=1, label="entry")
    if stop is not None:
        ax.axhline(stop, linestyle=":", linewidth=1, label="stop")
    if target is not None:
        ax.axhline(target, linestyle="-.", linewidth=1, label="target")
    ax.set_title(f"{symbol} pattern candidate")
    ax.set_xlabel("date")
    ax.set_ylabel("price")
    ax.grid(True, alpha=0.25)
    ax.legend(loc="best")
    fig.tight_layout()
    fig.savefig(path, dpi=140)
    plt.close(fig)
    return str(path)
