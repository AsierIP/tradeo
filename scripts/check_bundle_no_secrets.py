from __future__ import annotations

import re
import sys
import zipfile
from pathlib import Path

SECRET_PATH_RE = re.compile(r"(^|/)\.env($|[./])|(^|/)(id_rsa|id_ed25519|credentials?)(\.|$)", re.IGNORECASE)
SECRET_VALUE_RE = re.compile(
    r"(TRADEO_[A-Z0-9_]*(PASSWORD|SECRET|TOKEN|API_KEY|ACCOUNT)[A-Z0-9_]*\s*=\s*)"
    r"(?!$|replace|your-|changeme|change-me|<|una-|un-|sk-\.\.\.)",
    re.IGNORECASE,
)


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: check_bundle_no_secrets.py <bundle.zip>", file=sys.stderr)
        return 2
    bundle = Path(sys.argv[1])
    if not bundle.exists():
        print(f"bundle not found: {bundle}", file=sys.stderr)
        return 2
    failures: list[str] = []
    with zipfile.ZipFile(bundle) as zf:
        for info in zf.infolist():
            name = info.filename
            if SECRET_PATH_RE.search(name):
                failures.append(f"sensitive path: {name}")
                continue
            if info.file_size > 2_000_000:
                continue
            try:
                data = zf.read(info).decode("utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            if SECRET_VALUE_RE.search(data):
                failures.append(f"sensitive-looking assignment: {name}")
    if failures:
        print("bundle rejected:")
        for failure in failures:
            print(f" - {failure}")
        return 1
    print("bundle ok: no .env or sensitive patterns found")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
