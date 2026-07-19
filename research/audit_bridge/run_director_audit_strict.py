#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
BRIDGE = ROOT / "research" / "audit_bridge"
REQUESTS = BRIDGE / "requests"
LEGACY_RUNNER = BRIDGE / "run_director_audit.py"
CHAIN_GUARD = ROOT / "ops" / "scripts" / "director_audit_chain_guard.py"


def main() -> int:
    args = parse_args()
    legacy = load_module("tradeo_legacy_audit_runner", LEGACY_RUNNER)
    guard = load_module("tradeo_director_audit_chain_guard", CHAIN_GUARD)

    audit_id = args.audit_id or legacy.build_audit_id(args.cadence)
    package = REQUESTS / audit_id
    package.mkdir(parents=True, exist_ok=True)
    api_url = args.api_url or os.environ.get("TRADEO_API_URL") or legacy.default_api_url()
    created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    source_discovery_status = (
        args.source_discovery_status
        or os.environ.get("TRADEO_SOURCE_DISCOVERY_STATUS", "")
    ).strip().lower()
    source_discovery_run_ids = parse_run_ids(
        args.source_discovery_run_ids
        or os.environ.get("TRADEO_SOURCE_DISCOVERY_RUN_IDS", "")
    )

    runs: list[Any] = []
    gate_result: dict[str, Any] = {}
    runtime_status: dict[str, Any] = {"available": False, "reason": "not_collected"}
    runner_error: dict[str, str] | None = None

    try:
        runtime_run, runtime_status = legacy.collect_compose_status()
        runs.append(runtime_run)
        if not args.skip_export:
            runs.append(
                legacy.run_exporter(audit_id, api_url, args.pattern_limit, args.match_limit)
            )

        validate_run = legacy.run_subprocess(
            "validate",
            [sys.executable, str(BRIDGE / "validate_audit_package.py"), str(package)],
        )
        runs.append(validate_run)

        gate_json = package / "director_gate_result.json"
        gate_md = package / "director_gate_result.md"
        if validate_run.exit_code == 0:
            gate_run = legacy.run_subprocess(
                "director_gate",
                [
                    sys.executable,
                    str(BRIDGE / "director_gate.py"),
                    str(package),
                    "--json-output",
                    str(gate_json),
                    "--markdown-output",
                    str(gate_md),
                    "--allow-blocked-exit-zero",
                ],
            )
            runs.append(gate_run)
            gate_result = legacy.read_json(gate_json)
        else:
            gate_result = {
                "status": "invalid",
                "blockers": ["schema_validation_failed_gate_not_run"],
            }
            write_json(gate_json, gate_result)
            gate_md.write_text(
                "# Director Gate Result\n\n- Status: `invalid`\n- Blocker: schema validation failed; gate was not run.\n",
                encoding="utf-8",
            )
            runs.append(
                legacy.CommandRun(
                    "director_gate",
                    [],
                    1,
                    stderr="not run because schema validation failed",
                )
            )
    except Exception as exc:  # noqa: BLE001
        runner_error = {"type": type(exc).__name__, "message": str(exc)}
        runs.append(
            legacy.CommandRun(
                "runner_error",
                [],
                1,
                stderr=f"{type(exc).__name__}: {exc}",
            )
        )
        gate_result = {
            "status": "invalid",
            "blockers": [f"runner_error: {type(exc).__name__}: {exc}"],
        }
        write_json(package / "director_gate_result.json", gate_result)
        (package / "director_gate_result.md").write_text(
            "# Director Gate Result\n\n- Status: `invalid`\n- Blocker: audit runner error.\n",
            encoding="utf-8",
        )

    raw_review = legacy.deterministic_review(audit_id, args.cadence, gate_result, runs)
    schema_status = guard.derive_schema_status({"commands": [asdict(run) for run in runs]})
    gate_status = guard.derive_gate_status(gate_result, {})
    chain_errors: list[str] = []
    if not source_discovery_status:
        chain_errors.append("source discovery status is required")
    elif source_discovery_status != "completed":
        chain_errors.append(
            f"source discovery status is not completed: {source_discovery_status}"
        )
    review = guard.normalize_review(
        raw_review,
        audit_id=audit_id,
        schema_status=schema_status,
        gate_status=gate_status,
        errors=chain_errors,
    )

    result = {
        "audit_id": audit_id,
        "cadence": args.cadence,
        "created_at": created_at,
        "package": legacy.display_path(package),
        "api_url": api_url,
        "source_discovery_status": source_discovery_status or "unknown",
        "source_discovery_run_ids": source_discovery_run_ids,
        "schema_validation_status": schema_status,
        "director_gate_status": gate_status,
        "runtime_status": runtime_status,
        "commands": [asdict(run) for run in runs],
        "agent_review": review,
        "artifact_paths": {
            "run_json": legacy.display_path(package / "director_audit_run.json"),
            "run_markdown": legacy.display_path(package / "director_audit_run.md"),
            "agent_review_json": legacy.display_path(
                package / "internal_auditor_agent_review.json"
            ),
            "agent_review_markdown": legacy.display_path(
                package / "internal_auditor_agent_review.md"
            ),
        },
    }
    if runner_error is not None:
        result["runner_error"] = runner_error

    try:
        write_json(package / "internal_auditor_agent_review.json", review)
        guard.write_review_markdown(
            package / "internal_auditor_agent_review.md", review
        )
        write_json(package / "director_audit_run.json", result)
        legacy.write_md(package / "director_audit_run.md", result)
    except Exception as exc:  # noqa: BLE001
        print(
            f"failed to write strict audit artifacts in {package}: {type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        return 1

    export_failed = any(run.name == "export" and run.exit_code != 0 for run in runs)
    validation_failed = schema_status != "passed"
    gate_invalid = gate_status not in {"passed", "blocked"}
    if export_failed or validation_failed or gate_invalid or chain_errors or runner_error:
        return 1
    if gate_status == "blocked" and args.fail_on_blocked:
        return 2
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the Tradeo audit chain in fail-closed validate-before-gate order."
    )
    parser.add_argument("--audit-id", default=None)
    parser.add_argument("--cadence", choices=["daily", "weekly", "manual"], default="daily")
    parser.add_argument("--api-url", default=None)
    parser.add_argument("--pattern-limit", type=int, default=500)
    parser.add_argument("--match-limit", type=int, default=500)
    parser.add_argument("--skip-export", action="store_true")
    parser.add_argument("--fail-on-blocked", action="store_true")
    parser.add_argument(
        "--source-discovery-status",
        choices=["completed", "partial_failed", "partial_skipped", "failed", "skipped"],
        default=None,
    )
    parser.add_argument(
        "--source-discovery-run-ids",
        default=None,
        help="Comma-separated discovery run IDs that produced this package.",
    )
    return parser.parse_args()


def parse_run_ids(value: str) -> list[int]:
    run_ids: list[int] = []
    for raw in value.split(","):
        text = raw.strip()
        if not text:
            continue
        try:
            run_ids.append(int(text))
        except ValueError as exc:
            raise ValueError(f"invalid source discovery run ID: {text}") from exc
    return run_ids


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if not spec or not spec.loader:
        raise RuntimeError(f"cannot import module from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    raise SystemExit(main())
