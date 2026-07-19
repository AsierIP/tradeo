#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

REQUESTS_ROOT = Path("research/audit_bridge/requests")
REQUIRED_FILES = (
    "manifest.json",
    "director_gate_result.json",
    "director_gate_result.md",
    "internal_auditor_agent_review.json",
    "internal_auditor_agent_review.md",
    "director_audit_run.json",
    "director_audit_run.md",
)
PARTIAL_OR_FAILED_DISCOVERY_STATUSES = {
    "partial_failed",
    "partial_skipped",
    "failed",
    "skipped",
}
PASSED_SCHEMA_STATUSES = {"passed", "valid"}
BLOCKED_GATE_STATUSES = {"blocked"}
PASSED_GATE_STATUSES = {"passed", "approved"}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fail-closed integrity guard for a complete Tradeo Director audit chain."
    )
    parser.add_argument(
        "--package",
        default="latest",
        help="Package directory, manifest path, or 'latest'.",
    )
    parser.add_argument(
        "--tracked-only",
        action="store_true",
        help="Resolve and accept only packages tracked by git.",
    )
    parser.add_argument(
        "--max-age-hours",
        type=float,
        default=None,
        help="Reject packages older than this many hours.",
    )
    parser.add_argument(
        "--require-head-commit",
        action="store_true",
        help="Require manifest.repo_commit to equal the current HEAD.",
    )
    parser.add_argument(
        "--require-discovery-status",
        action="store_true",
        help="Require a completed source discovery status and reject partial/failed/skipped runs.",
    )
    parser.add_argument(
        "--normalize-review",
        action="store_true",
        help="Write missing required status fields into internal_auditor_agent_review.json/.md.",
    )
    args = parser.parse_args()

    root = repo_root()
    package = resolve_package(root, args.package, tracked_only=args.tracked_only)
    if package is None:
        return 1

    errors: list[str] = []
    missing = [name for name in REQUIRED_FILES if not (package / name).is_file()]
    if missing:
        errors.extend(f"missing required audit-chain artifact: {name}" for name in missing)
        return emit_result(package, errors=errors)

    manifest = read_json(package / "manifest.json", errors)
    gate = read_json(package / "director_gate_result.json", errors)
    run = read_json(package / "director_audit_run.json", errors)
    review = read_json(package / "internal_auditor_agent_review.json", errors)
    if errors:
        return emit_result(package, errors=errors)

    audit_id = str(manifest.get("audit_id", "")).strip()
    if not audit_id:
        errors.append("manifest.audit_id is required")
    elif audit_id != package.name:
        errors.append(f"manifest.audit_id must match package directory: {audit_id} != {package.name}")

    created_at = parse_aware_datetime(manifest.get("created_at"), "manifest.created_at", errors)
    now = datetime.now(timezone.utc)
    if created_at is not None:
        if created_at > now + timedelta(minutes=5):
            errors.append("manifest.created_at is more than five minutes in the future")
        if args.max_age_hours is not None:
            max_age = timedelta(hours=max(args.max_age_hours, 0.0))
            if now - created_at > max_age:
                errors.append(
                    f"audit package is stale: age exceeds {args.max_age_hours:g} hours"
                )

    repo_commit = str(manifest.get("repo_commit", "")).strip()
    if not repo_commit:
        errors.append("manifest.repo_commit is required")
    elif args.require_head_commit:
        head = git_output(root, "rev-parse", "HEAD", errors=errors)
        if head and repo_commit != head:
            errors.append(f"manifest.repo_commit does not match HEAD: {repo_commit} != {head}")

    schema_status = derive_schema_status(run)
    gate_status = derive_gate_status(gate, run)
    validate_index, gate_index = audit_stage_indexes(run)
    if validate_index is None:
        errors.append("audit run does not record the validate stage")
    if gate_index is None:
        errors.append("audit run does not record the director_gate stage")
    if validate_index is not None and gate_index is not None and validate_index > gate_index:
        errors.append("audit stages are out of order: validate must run before director_gate")
    if schema_status not in PASSED_SCHEMA_STATUSES:
        errors.append(f"schema validation is not passed: {schema_status}")
    if gate_status not in PASSED_GATE_STATUSES | BLOCKED_GATE_STATUSES:
        errors.append(f"promotion gate has no fail-closed terminal status: {gate_status}")

    discovery_status = derive_discovery_status(manifest, run)
    if args.require_discovery_status:
        if not discovery_status:
            errors.append("source discovery status is required")
        elif discovery_status != "completed":
            errors.append(f"source discovery status is not completed: {discovery_status}")
    elif discovery_status in PARTIAL_OR_FAILED_DISCOVERY_STATUSES:
        errors.append(f"partial/failed source discovery cannot support promotion: {discovery_status}")

    normalized_review = normalize_review(
        review,
        audit_id=audit_id or package.name,
        schema_status=schema_status,
        gate_status=gate_status,
        errors=errors,
    )
    if args.normalize_review and not errors:
        write_json(package / "internal_auditor_agent_review.json", normalized_review)
        write_review_markdown(package / "internal_auditor_agent_review.md", normalized_review)

    summary = {
        "package": display_path(root, package),
        "audit_id": audit_id or package.name,
        "created_at": manifest.get("created_at"),
        "repo_commit": repo_commit,
        "schema_validation_status": schema_status,
        "promotion_gate_status": gate_status,
        "source_discovery_status": discovery_status or "not_recorded",
        "promotion_decision": normalized_review.get("promotion_decision"),
        "audit_chain_complete": not errors,
    }
    return emit_result(package, errors=errors, summary=summary)


def repo_root() -> Path:
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        print(result.stderr.strip() or "Not inside a git repository.", file=sys.stderr)
        raise SystemExit(1)
    return Path(result.stdout.strip()).resolve()


def resolve_package(root: Path, value: str, *, tracked_only: bool) -> Path | None:
    if not value or value == "latest":
        return latest_package(root, tracked_only=tracked_only)

    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = root / candidate
    candidate = candidate.resolve()
    if candidate.name == "manifest.json":
        candidate = candidate.parent
    requests_root = (root / REQUESTS_ROOT).resolve()
    if not is_under(candidate, requests_root):
        print(f"Audit package must live under {REQUESTS_ROOT}: {candidate}", file=sys.stderr)
        return None
    if tracked_only and not package_is_tracked(root, candidate):
        print(f"Audit package is not tracked by git: {display_path(root, candidate)}", file=sys.stderr)
        return None
    return candidate


def latest_package(root: Path, *, tracked_only: bool) -> Path | None:
    manifests: list[Path]
    if tracked_only:
        result = subprocess.run(
            ["git", "ls-files", str(REQUESTS_ROOT)],
            cwd=root,
            text=True,
            capture_output=True,
            check=False,
        )
        if result.returncode != 0:
            print(result.stderr.strip(), file=sys.stderr)
            return None
        manifests = [root / line for line in result.stdout.splitlines() if line.endswith("/manifest.json")]
    else:
        manifests = list((root / REQUESTS_ROOT).glob("*/manifest.json"))

    candidates: list[tuple[datetime, Path]] = []
    for manifest_path in manifests:
        try:
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
            created_at = datetime.fromisoformat(str(payload["created_at"]).replace("Z", "+00:00"))
            if created_at.tzinfo is None or created_at.utcoffset() is None:
                continue
        except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
            continue
        candidates.append((created_at.astimezone(timezone.utc), manifest_path.parent.resolve()))
    if not candidates:
        mode = "tracked " if tracked_only else ""
        print(f"No {mode}audit package manifests found under {REQUESTS_ROOT}.", file=sys.stderr)
        return None
    candidates.sort(key=lambda item: (item[0], item[1].name))
    return candidates[-1][1]


def package_is_tracked(root: Path, package: Path) -> bool:
    rel = display_path(root, package / "manifest.json")
    result = subprocess.run(
        ["git", "ls-files", "--error-unmatch", "--", rel],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    return result.returncode == 0


def read_json(path: Path, errors: list[str]) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"invalid JSON {path.name}: {type(exc).__name__}: {exc}")
        return {}
    if not isinstance(payload, dict):
        errors.append(f"{path.name} must contain a JSON object")
        return {}
    return payload


def parse_aware_datetime(value: Any, field: str, errors: list[str]) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        errors.append(f"{field} must be a valid ISO-8601 datetime")
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        errors.append(f"{field} must include an explicit timezone")
        return None
    return parsed.astimezone(timezone.utc)


def audit_stage_indexes(run: dict[str, Any]) -> tuple[int | None, int | None]:
    commands = run.get("commands")
    if not isinstance(commands, list):
        return None, None
    validate_index: int | None = None
    gate_index: int | None = None
    for index, command in enumerate(commands):
        if not isinstance(command, dict):
            continue
        name = str(command.get("name", "")).strip()
        if name == "validate" and validate_index is None:
            validate_index = index
        if name == "director_gate" and gate_index is None:
            gate_index = index
    return validate_index, gate_index


def derive_schema_status(run: dict[str, Any]) -> str:
    commands = run.get("commands")
    if isinstance(commands, list):
        for command in commands:
            if isinstance(command, dict) and command.get("name") == "validate":
                try:
                    return "passed" if int(command.get("exit_code", 1)) == 0 else "failed"
                except (TypeError, ValueError):
                    return "failed"
    review = run.get("agent_review")
    if isinstance(review, dict):
        value = str(review.get("schema_validation_status", "")).strip().lower()
        if value:
            return value
    return "not_run"


def derive_gate_status(gate: dict[str, Any], run: dict[str, Any]) -> str:
    for key in ("promotion_gate_status", "director_gate_status", "status"):
        value = str(gate.get(key, "")).strip().lower()
        if value:
            return value
    value = str(run.get("director_gate_status", "")).strip().lower()
    return value or "not_run"


def derive_discovery_status(manifest: dict[str, Any], run: dict[str, Any]) -> str:
    keys = (
        "source_discovery_status",
        "aggregate_discovery_status",
        "discovery_status",
    )
    for source in (manifest, run):
        for key in keys:
            value = str(source.get(key, "")).strip().lower()
            if value:
                return value
    return ""


def normalize_review(
    review: dict[str, Any],
    *,
    audit_id: str,
    schema_status: str,
    gate_status: str,
    errors: Iterable[str],
) -> dict[str, Any]:
    normalized = dict(review)
    top_blockers = normalized.get("top_blockers")
    if not isinstance(top_blockers, list):
        top_blockers = []
    errors_list = list(errors)
    for error in errors_list:
        if error not in top_blockers:
            top_blockers.append(error)

    terminal_gate = gate_status in PASSED_GATE_STATUSES | BLOCKED_GATE_STATUSES
    passed_chain = schema_status in PASSED_SCHEMA_STATUSES and terminal_gate and not errors_list
    promotion_decision = (
        "eligible_for_director_review"
        if passed_chain and gate_status in PASSED_GATE_STATUSES
        else "stay_in_research"
    )

    normalized.update(
        {
            "audit_id": normalized.get("audit_id") or audit_id,
            "cadence": normalized.get("cadence") or "unknown",
            "agent": normalized.get("agent") or "tradeo-internal-daily-auditor",
            "status": gate_status if passed_chain else "invalid",
            "schema_validation_status": schema_status,
            "promotion_gate_status": gate_status,
            "priority": "P0" if not passed_chain or gate_status in BLOCKED_GATE_STATUSES else normalized.get("priority", "P2"),
            "blocker_count": len(top_blockers),
            "top_blockers": top_blockers,
            "promotion_decision": promotion_decision,
            "required_next_actions": normalized.get("required_next_actions") or [],
            "director_handoff": normalized.get("director_handoff")
            or "Director review is required before any promotion.",
        }
    )
    return normalized


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_review_markdown(path: Path, review: dict[str, Any]) -> None:
    blockers = review.get("top_blockers") if isinstance(review.get("top_blockers"), list) else []
    actions = review.get("required_next_actions") if isinstance(review.get("required_next_actions"), list) else []
    lines = [
        "# Internal Auditor Agent Review",
        "",
        f"- Audit ID: `{review.get('audit_id', '')}`",
        f"- Status: `{review.get('status', '')}`",
        f"- Schema validation: `{review.get('schema_validation_status', '')}`",
        f"- Promotion gate: `{review.get('promotion_gate_status', '')}`",
        f"- Priority: `{review.get('priority', '')}`",
        f"- Promotion decision: `{review.get('promotion_decision', '')}`",
        "",
        "## Top blockers",
        "",
    ]
    lines.extend(f"- {item}" for item in blockers) if blockers else lines.append("- None")
    lines.extend(["", "## Required next actions", ""])
    lines.extend(f"- {item}" for item in actions) if actions else lines.append("- None")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def git_output(root: Path, *args: str, errors: list[str]) -> str:
    result = subprocess.run(["git", *args], cwd=root, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        errors.append(result.stderr.strip() or f"git {' '.join(args)} failed")
        return ""
    return result.stdout.strip()


def is_under(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def display_path(root: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path)


def emit_result(
    package: Path,
    *,
    errors: list[str],
    summary: dict[str, Any] | None = None,
) -> int:
    payload = summary or {"package": str(package), "audit_chain_complete": False}
    payload["errors"] = errors
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
