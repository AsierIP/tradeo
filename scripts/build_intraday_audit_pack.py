from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

try:
    from tradeo.core.config import Settings
except ModuleNotFoundError as exc:  # pragma: no cover - exercised by system python.
    venv_python = ROOT / "backend/.venv/bin/python"
    if exc.name == "pydantic" and venv_python.exists() and Path(sys.executable) != venv_python:
        os.execv(str(venv_python), [str(venv_python), *sys.argv])
    raise


SECURITY_EXCLUSIONS = [
    ".env files",
    "account identifiers",
    "tokens",
    "passwords",
    "API keys",
    "broker credentials",
    "raw logs",
    "database dumps",
    "runtime caches",
]

SAFE_REDACTED_VALUES = {"", None, "<redacted>", "***REDACTED***", "redacted", False}
SENSITIVE_KEY_MARKERS = (
    "ACCOUNT",
    "API_KEY",
    "BROKER_CREDENTIAL",
    "PASSWORD",
    "PRIVATE_KEY",
    "SECRET",
    "TOKEN",
)
SECRET_METADATA_KEYS = {"secret_policy", "secret_scan", "secrets_included"}
SECRET_VALUE_PATTERNS = (
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b"),
    re.compile(r"(?i)\b(password|passwd|token|api[_-]?key|secret)\s*[:=]\s*[^\s,'\"]{4,}"),
)

INTRADAY_PURPOSES = {
    "backend/tradeo/modules/intraday/__init__.py": "Package boundary for the intraday lane.",
    "backend/tradeo/modules/intraday/candidates.py": (
        "Normalizes scanner output into session-aware shadow/paper candidates with expiry, "
        "exposure de-duplication and reason codes."
    ),
    "backend/tradeo/modules/intraday/data_sync.py": (
        "Validates OHLCV bars, serves only closed bars and emits a compact data-quality manifest."
    ),
    "backend/tradeo/modules/intraday/director.py": (
        "Gates lab, paper-candidate and production promotion from evidence thresholds."
    ),
    "backend/tradeo/modules/intraday/execution.py": (
        "Evaluates paper-order eligibility and records fill/slippage metrics without a broker."
    ),
    "backend/tradeo/modules/intraday/features.py": (
        "Builds deterministic closed-bar intraday features such as VWAP, RVOL, ATR and buckets."
    ),
    "backend/tradeo/modules/intraday/flat_service.py": (
        "Runs the end-of-day flat state machine with reduce-only exit orders and kill-switch signals."
    ),
    "backend/tradeo/modules/intraday/lab.py": (
        "Measures shadow/lab outcomes, holding bars, MFE/MAE and EOD-flat exit reasons."
    ),
    "backend/tradeo/modules/intraday/reports.py": (
        "Builds redacted session reports with trades, EV, flat status and reason-code counts."
    ),
    "backend/tradeo/modules/intraday/risk.py": (
        "Applies session-scoped risk limits, reduce-only handling and ledger summaries."
    ),
    "backend/tradeo/modules/intraday/universe.py": (
        "Selects the intraday universe from session metrics with liquidity, spread and watchlist filters."
    ),
    "backend/tradeo/services/intraday_calendar.py": (
        "Provides NYSE session/cutoff metadata with local fallback and fail-closed semantics."
    ),
    "backend/tradeo/routers/intraday.py": (
        "Exposes admin-only intraday status, pacing, risk and flat-preview endpoints."
    ),
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _redacted_intraday_config(settings: Settings) -> dict[str, Any]:
    return {
        key: value
        for key, value in settings.redacted_config_snapshot().items()
        if key.startswith("TRADEO_INTRADAY_")
    }


def _git(*args: str) -> str | None:
    result = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def _git_metadata() -> dict[str, Any]:
    status = _git("status", "--porcelain") or ""
    return {
        "available": bool(_git("rev-parse", "--is-inside-work-tree")),
        "branch": _git("rev-parse", "--abbrev-ref", "HEAD"),
        "commit": _git("rev-parse", "HEAD"),
        "short_commit": _git("rev-parse", "--short", "HEAD"),
        "commit_subject": _git("log", "-1", "--pretty=%s"),
        "dirty": bool(status),
        "status_counts": _git_status_counts(status),
    }


def _git_status_counts(status: str) -> dict[str, int]:
    counts = {
        "added": 0,
        "deleted": 0,
        "modified": 0,
        "renamed": 0,
        "untracked": 0,
        "other": 0,
    }
    for line in status.splitlines():
        if line.startswith("??"):
            counts["untracked"] += 1
            continue
        code = line[:2]
        matched = False
        if "A" in code:
            counts["added"] += 1
            matched = True
        if "D" in code:
            counts["deleted"] += 1
            matched = True
        if "M" in code:
            counts["modified"] += 1
            matched = True
        if "R" in code:
            counts["renamed"] += 1
            matched = True
        if not matched:
            counts["other"] += 1
    return counts


def _makefile_target_commands(target: str) -> list[str]:
    makefile = ROOT / "Makefile"
    if not makefile.exists():
        return []
    raw_commands: list[str] = []
    in_target = False
    for line in makefile.read_text(encoding="utf-8").splitlines():
        if not in_target:
            if re.match(rf"^{re.escape(target)}\s*:", line):
                in_target = True
            continue
        if line.startswith("\t"):
            raw_commands.append(line[1:].rstrip())
            continue
        if line.strip() == "":
            continue
        break
    return _join_make_continuations(raw_commands)


def _join_make_continuations(lines: list[str]) -> list[str]:
    commands: list[str] = []
    buffer = ""
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.endswith("\\"):
            buffer += stripped[:-1].rstrip() + " "
            continue
        buffer += stripped
        commands.append(re.sub(r"\s+", " ", buffer).strip())
        buffer = ""
    if buffer:
        commands.append(re.sub(r"\s+", " ", buffer).strip())
    return commands


def _test_files_from_commands(commands: list[str]) -> list[str]:
    seen: set[str] = set()
    files: list[str] = []
    for command in commands:
        for match in re.findall(r"(?:^|\s)(tradeo/tests/test_[^\s]+\.py)", command):
            path = f"backend/{match}"
            if path not in seen:
                seen.add(path)
                files.append(path)
    return files


def _discover_intraday_test_files() -> list[str]:
    test_dir = ROOT / "backend/tradeo/tests"
    files = sorted(test_dir.glob("test_intraday*.py"))
    pacing = test_dir / "test_ibkr_pacing.py"
    if pacing.exists():
        files.append(pacing)
    return [str(path.relative_to(ROOT)) for path in files]


def _executable_tests() -> list[dict[str, Any]]:
    test_safety_commands = _makefile_target_commands("test-safety")
    intraday_test_files = _discover_intraday_test_files()
    backend_test_args = " ".join(path.removeprefix("backend/") for path in intraday_test_files)
    targeted_command = (
        "cd backend && TRADEO_DATABASE_URL='sqlite:///:memory:' "
        f".venv/bin/python -m pytest -q {backend_test_args}"
    )
    return [
        {
            "name": "intraday_audit_pack_dry_run",
            "kind": "script",
            "command": "python3 scripts/build_intraday_audit_pack.py --dry-run",
            "working_directory": ".",
            "available": (ROOT / "scripts/build_intraday_audit_pack.py").exists(),
        },
        {
            "name": "test_safety_make_target",
            "kind": "make",
            "command": "make test-safety",
            "working_directory": ".",
            "available": bool(test_safety_commands),
            "expanded_commands": test_safety_commands,
            "test_files": _test_files_from_commands(test_safety_commands),
        },
        {
            "name": "intraday_targeted_pytest",
            "kind": "pytest",
            "command": targeted_command,
            "working_directory": ".",
            "available": bool(intraday_test_files) and (ROOT / "backend/.venv/bin/python").exists(),
            "test_files": intraday_test_files,
        },
    ]


def _intraday_source_files() -> list[Path]:
    files = sorted((ROOT / "backend/tradeo/modules/intraday").glob("*.py"))
    files.extend(
        [
            ROOT / "backend/tradeo/services/intraday_calendar.py",
            ROOT / "backend/tradeo/routers/intraday.py",
        ]
    )
    return [path for path in files if path.exists()]


def _intraday_module_summary() -> dict[str, Any]:
    modules = [_module_info(path) for path in _intraday_source_files()]
    return {
        "source": "static_ast_no_imports",
        "module_count": len(modules),
        "modules": modules,
    }


def _module_info(path: Path) -> dict[str, Any]:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    rel_path = str(path.relative_to(ROOT))
    classes = []
    functions = []
    constants = []
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and not node.name.startswith("_"):
            classes.append(_class_info(node))
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and not node.name.startswith("_"):
            functions.append(node.name)
        elif isinstance(node, ast.Assign):
            constants.extend(_public_constant_names(node.targets))
        elif isinstance(node, ast.AnnAssign):
            constants.extend(_public_constant_names([node.target]))
    info: dict[str, Any] = {
        "path": rel_path,
        "purpose": INTRADAY_PURPOSES.get(rel_path, "Intraday source file."),
        "sha256": _sha256(path),
        "line_count": len(source.splitlines()),
        "public_classes": classes,
        "public_functions": functions,
        "public_constants": sorted(set(constants)),
    }
    docstring = ast.get_docstring(tree)
    if docstring:
        info["docstring"] = _one_line(docstring)
    return info


def _class_info(node: ast.ClassDef) -> dict[str, Any]:
    methods = [
        item.name
        for item in node.body
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and not item.name.startswith("_")
    ]
    info: dict[str, Any] = {
        "name": node.name,
        "dataclass": any(_decorator_name(decorator) == "dataclass" for decorator in node.decorator_list),
    }
    if methods:
        info["public_methods"] = methods
    docstring = ast.get_docstring(node)
    if docstring:
        info["docstring"] = _one_line(docstring)
    return info


def _public_constant_names(targets: list[ast.expr]) -> list[str]:
    names = []
    for target in targets:
        if isinstance(target, ast.Name) and target.id.isupper() and not target.id.startswith("_"):
            names.append(target.id)
        elif isinstance(target, (ast.Tuple, ast.List)):
            names.extend(_public_constant_names(list(target.elts)))
    return names


def _decorator_name(node: ast.expr) -> str:
    if isinstance(node, ast.Call):
        return _decorator_name(node.func)
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return ""


def _one_line(value: str, *, limit: int = 240) -> str:
    text = re.sub(r"\s+", " ", value).strip()
    return text if len(text) <= limit else text[: limit - 3].rstrip() + "..."


def _secret_findings(value: Any, *, path: str = "$") -> list[str]:
    findings: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            child_path = f"{path}.{key}"
            if _is_sensitive_key(str(key)) and str(key).lower() not in SECRET_METADATA_KEYS:
                if item not in SAFE_REDACTED_VALUES:
                    findings.append(f"{child_path}: sensitive key is not redacted")
            findings.extend(_secret_findings(item, path=child_path))
        return findings
    if isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            findings.extend(_secret_findings(item, path=f"{path}[{index}]"))
        return findings
    if isinstance(value, str):
        for pattern in SECRET_VALUE_PATTERNS:
            if pattern.search(value):
                findings.append(f"{path}: value matches secret pattern")
                break
    return findings


def _is_sensitive_key(key: str) -> bool:
    upper = key.upper()
    return any(marker in upper for marker in SENSITIVE_KEY_MARKERS)


def build_pack(*, dry_run: bool) -> dict[str, Any]:
    settings = Settings()
    files = [
        ROOT / "scripts/build_intraday_audit_pack.py",
        ROOT / "docs/security.md",
        ROOT / "docs/intraday_audit_pack.md",
        ROOT / "docs/intraday_implementation_changelog.md",
        ROOT / "backend/tradeo/core/config.py",
        ROOT / "backend/tradeo/db/models.py",
        ROOT / "backend/tradeo/services/intraday_calendar.py",
        ROOT / "backend/tradeo/services/ibkr_pacing.py",
        ROOT / "docs/intraday_no_regression_contract.md",
    ]
    files.extend(_intraday_source_files())
    executable_tests = _executable_tests()
    payload = {
        "schema_version": 2,
        "generated_at": datetime.now(UTC).isoformat(),
        "dry_run": dry_run,
        "redacted": True,
        "secret_policy": {
            "source": "docs/security.md",
            "excluded": SECURITY_EXCLUSIONS,
            "runtime_sources_collected": False,
        },
        "git": _git_metadata(),
        "intraday_config": _redacted_intraday_config(settings),
        "file_hashes": {str(path.relative_to(ROOT)): _sha256(path) for path in files if path.exists()},
        "intraday_module_summary": _intraday_module_summary(),
        "required_tests": [
            "make test-safety",
            "python3 scripts/build_intraday_audit_pack.py --dry-run",
        ],
        "executable_tests": executable_tests,
        "session_report": {
            "available": False,
            "reason": "dry_run_no_session_events" if dry_run else "not_collected",
        },
        "secrets_included": False,
    }
    findings = _secret_findings(payload)
    payload["secret_scan"] = {"checked": True, "findings": findings}
    if findings:
        raise ValueError(f"audit pack secret guard failed: {findings}")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--output", default="reports/intraday_audit_pack.json")
    args = parser.parse_args()

    payload = build_pack(dry_run=args.dry_run)
    if args.dry_run:
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0
    output = ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
