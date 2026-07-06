#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from tradeo.modules.lab_foxhunter.paper_probe import (  # noqa: E402
    LabPaperProbeBatchRequest,
    LabPaperProbeEnvironment,
    build_lab_gap_probe_manifests,
    prepare_lab_paper_probe_batch,
    render_lab_paper_probe_batch_markdown,
)


def _load_env(path: Path | None) -> dict[str, str]:
    if path is None or not path.exists():
        return {}
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key.startswith("TRADEO_"):
            values[key.strip()] = value.strip().strip("'\"")
    return values


def _truthy(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _environment_from_args(args: argparse.Namespace) -> LabPaperProbeEnvironment:
    env = _load_env(Path(args.env_file) if args.env_file else None)
    return LabPaperProbeEnvironment(
        explicit_paper_probe_mode=args.paper_probe_mode,
        director_approved=args.director_approved,
        ibkr_readonly=_truthy(env.get("TRADEO_IBKR_READONLY", "true")),
        laboratory_auto_submit_paper_orders=_truthy(
            env.get("TRADEO_LABORATORY_AUTO_SUBMIT_PAPER_ORDERS", "false")
        ),
        foxhunter_auto_submit_live_orders=_truthy(
            env.get("TRADEO_FOX_HUNTER_AUTO_SUBMIT_LIVE_ORDERS", "false")
        ),
        live_trading_enabled=_truthy(env.get("TRADEO_LIVE_TRADING_ENABLED", "false")),
        live_armed=_truthy(env.get("TRADEO_LIVE_ARMED", "false")),
        kill_switch_available=not _truthy(env.get("TRADEO_KILL_SWITCH_MISSING", "false")),
        risk_limits_available=not _truthy(env.get("TRADEO_RISK_LIMITS_MISSING", "false")),
        broker_submit_enabled=False,
        cron_trading_enabled=False,
        order_preview_enabled=False,
        signal_generation_enabled=False,
    )


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    request = LabPaperProbeBatchRequest(
        batch_id=args.batch_id,
        probes=build_lab_gap_probe_manifests(),
    )
    return prepare_lab_paper_probe_batch(request, _environment_from_args(args))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Prepare a supervised Lab paper-probe batch without orders/signals/previews."
    )
    parser.add_argument("--batch-id", default="LAB-PAPER-PROBE-002")
    parser.add_argument("--env-file")
    parser.add_argument("--paper-probe-mode", action="store_true")
    parser.add_argument("--director-approved", action="store_true")
    parser.add_argument("--json-out")
    parser.add_argument("--md-out")
    args = parser.parse_args()

    report = build_report(args)
    payload = json.dumps(report, indent=2, sort_keys=True)
    if args.json_out:
        Path(args.json_out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json_out).write_text(payload + "\n", encoding="utf-8")
    if args.md_out:
        Path(args.md_out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.md_out).write_text(
            render_lab_paper_probe_batch_markdown(report),
            encoding="utf-8",
        )
    print(payload)
    return 0 if report["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
