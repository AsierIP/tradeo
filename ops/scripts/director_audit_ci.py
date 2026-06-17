#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


REQUESTS_ROOT = Path("research/audit_bridge/requests")
VALIDATOR = Path("research/audit_bridge/validate_audit_package.py")
DIRECTOR_GATE = Path("research/audit_bridge/director_gate.py")
MAX_COMMAND_OUTPUT_LINES = 180


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run reproducible Director audit checks on a tracked audit package."
    )
    parser.add_argument(
        "--package",
        default="latest",
        help="Audit package directory, manifest path, or 'latest' for newest tracked manifest.",
    )
    parser.add_argument(
        "--allow-untracked-requests",
        action="store_true",
        help="Developer-only escape hatch for inspecting an uncommitted package before adding it.",
    )
    args = parser.parse_args()

    root = repo_root()
    if not args.allow_untracked_requests:
        untracked = untracked_request_files(root)
        if untracked:
            print("Untracked audit evidence under research/audit_bridge/requests blocks Director CI.")
            for path in untracked[:12]:
                print(f"- {path}")
            if len(untracked) > 12:
                print(f"- ... {len(untracked) - 12} more")
            print("Add the full package, move it out of requests, or rerun with --allow-untracked-requests locally.")
            return 1

    package = resolve_package(root, args.package, allow_untracked=args.allow_untracked_requests)
    if package is None:
        return 1

    manifest = load_manifest(package)
    if manifest is None:
        return 1
    if not validate_manifest_identity(root, package, manifest):
        return 1
    if not args.allow_untracked_requests and not package_is_tracked(root, package):
        print(f"Selected package is not tracked by git: {relpath(root, package)}")
        return 1
    if not verify_file_hashes(package, manifest):
        return 1

    audit_id = manifest.get("audit_id", package.name)
    created_at = manifest.get("created_at", "unknown")
    repo_commit = manifest.get("repo_commit", "unknown")
    print(f"Director audit package: {relpath(root, package)}")
    print(f"Audit id: {audit_id}")
    print(f"Created at: {created_at}")
    print(f"Package repo commit: {repo_commit}")

    validator_code = run_command([sys.executable, str(root / VALIDATOR), str(package)], cwd=root)
    if validator_code != 0:
        return validator_code

    gate_code = run_command([sys.executable, str(root / DIRECTOR_GATE), str(package)], cwd=root)
    if gate_code == 2:
        print("Director gate is BLOCKED; this is valid CI output for a non-promotable paper package.")
        return 0
    return gate_code


def repo_root() -> Path:
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        print(result.stderr.strip() or "Not inside a git repository.")
        sys.exit(1)
    return Path(result.stdout.strip()).resolve()


def run_git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=root, text=True, capture_output=True, check=False)


def untracked_request_files(root: Path) -> list[str]:
    result = run_git(root, "status", "--porcelain", "--untracked-files=all", "--", str(REQUESTS_ROOT))
    if result.returncode != 0:
        print(result.stderr.strip())
        sys.exit(result.returncode)
    paths: list[str] = []
    for line in result.stdout.splitlines():
        if line.startswith("?? "):
            paths.append(line[3:])
    return paths


def resolve_package(root: Path, value: str, *, allow_untracked: bool) -> Path | None:
    if not value or value == "latest":
        return latest_tracked_package(root)

    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = root / candidate
    candidate = candidate.resolve()
    if candidate.name == "manifest.json":
        candidate = candidate.parent
    if not (candidate / "manifest.json").exists():
        print(f"Audit package has no manifest.json: {candidate}")
        return None
    if not is_under(candidate, root / REQUESTS_ROOT):
        print(f"Audit package must live under {REQUESTS_ROOT}: {candidate}")
        return None
    if not allow_untracked and not package_is_tracked(root, candidate):
        print(f"Requested package is not fully tracked: {relpath(root, candidate)}")
        return None
    return candidate


def latest_tracked_package(root: Path) -> Path | None:
    result = run_git(root, "ls-files", str(REQUESTS_ROOT))
    if result.returncode != 0:
        print(result.stderr.strip())
        return None

    manifests = [Path(line) for line in result.stdout.splitlines() if line.endswith("/manifest.json")]
    packages: list[tuple[datetime, Path]] = []
    for rel_manifest in manifests:
        path = root / rel_manifest
        try:
            manifest = json.loads(path.read_text(encoding="utf-8"))
            created_at = parse_datetime(str(manifest.get("created_at", "")))
        except Exception as exc:  # noqa: BLE001
            print(f"{rel_manifest}: invalid manifest created_at: {exc}")
            return None
        packages.append((created_at, path.parent))

    if not packages:
        print(f"No tracked audit package manifests found under {REQUESTS_ROOT}.")
        return None
    packages.sort(key=lambda item: (item[0], item[1].name))
    return packages[-1][1]


def parse_datetime(value: str) -> datetime:
    if not value:
        raise ValueError("missing created_at")
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def load_manifest(package: Path) -> dict[str, Any] | None:
    try:
        manifest = json.loads((package / "manifest.json").read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        print(f"{package / 'manifest.json'}: invalid JSON: {exc}")
        return None
    if not isinstance(manifest, dict):
        print(f"{package / 'manifest.json'}: manifest must be a JSON object")
        return None
    return manifest


def validate_manifest_identity(root: Path, package: Path, manifest: dict[str, Any]) -> bool:
    audit_id = str(manifest.get("audit_id", "")).strip()
    if not audit_id:
        print("manifest.audit_id is required")
        return False
    if audit_id != package.name:
        print(f"manifest.audit_id must match package directory: {audit_id} != {package.name}")
        return False
    try:
        parse_datetime(str(manifest.get("created_at", "")))
    except ValueError as exc:
        print(f"{relpath(root, package / 'manifest.json')}: invalid created_at: {exc}")
        return False
    return True


def package_is_tracked(root: Path, package: Path) -> bool:
    rel = relpath(root, package)
    result = run_git(root, "ls-files", "--", f"{rel}/manifest.json")
    return result.returncode == 0 and bool(result.stdout.strip())


def verify_file_hashes(package: Path, manifest: dict[str, Any]) -> bool:
    hash_file = package / "file_hashes.sha256"
    if not hash_file.exists():
        print("file_hashes.sha256 is required for reproducible Director CI.")
        return False

    entries: dict[str, str] = {}
    ok = True
    for line_number, raw_line in enumerate(hash_file.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        try:
            expected_hash, rel = line.split(None, 1)
        except ValueError:
            print(f"file_hashes.sha256:{line_number}: expected '<sha256>  <relative_path>'")
            ok = False
            continue
        rel = rel.strip()
        if not is_safe_relative_path(rel):
            print(f"file_hashes.sha256:{line_number}: unsafe path {rel}")
            ok = False
            continue
        path = package / rel
        if not path.exists():
            print(f"file_hashes.sha256:{line_number}: missing file {rel}")
            ok = False
            continue
        actual_hash = sha256_file(path)
        if actual_hash != expected_hash:
            print(f"file_hashes.sha256:{line_number}: hash mismatch for {rel}")
            ok = False
        entries[rel] = expected_hash

    manifest_paths = {
        str(item.get("path", "")).strip()
        for item in manifest.get("files", [])
        if isinstance(item, dict) and str(item.get("path", "")).strip()
    }
    missing_hashes = sorted(manifest_paths - {"file_hashes.sha256"} - set(entries))
    extra_hashes = sorted(set(entries) - manifest_paths)
    if missing_hashes:
        print("file_hashes.sha256 missing manifest paths:")
        for rel in missing_hashes:
            print(f"- {rel}")
        ok = False
    if extra_hashes:
        print("file_hashes.sha256 contains paths not listed in manifest.files:")
        for rel in extra_hashes:
            print(f"- {rel}")
        ok = False
    return ok


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def is_safe_relative_path(value: str) -> bool:
    path = Path(value)
    return not path.is_absolute() and ".." not in path.parts


def is_under(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def relpath(root: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(root))
    except ValueError:
        return str(path)


def run_command(command: list[str], *, cwd: Path) -> int:
    print("+ " + " ".join(str(part) for part in command), flush=True)
    result = subprocess.run(command, cwd=cwd, text=True, capture_output=True, check=False)
    emit_command_output(result.stdout, stream=sys.stdout)
    emit_command_output(result.stderr, stream=sys.stderr)
    return result.returncode


def emit_command_output(output: str, *, stream: Any) -> None:
    if not output:
        return
    lines = output.splitlines()
    if len(lines) <= MAX_COMMAND_OUTPUT_LINES:
        print(output, end="" if output.endswith("\n") else "\n", file=stream)
        return
    keep_head = MAX_COMMAND_OUTPUT_LINES // 2
    keep_tail = MAX_COMMAND_OUTPUT_LINES - keep_head
    for line in lines[:keep_head]:
        print(line, file=stream)
    print(f"... truncated {len(lines) - MAX_COMMAND_OUTPUT_LINES} lines ...", file=stream)
    for line in lines[-keep_tail:]:
        print(line, file=stream)


if __name__ == "__main__":
    raise SystemExit(main())
