#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


UNITS = {
    "premarket": ("09:00", ".venv/bin/python scripts/check_lab_paper_readiness.py"),
    "session": ("09:35", "/bin/bash scripts/run_lab_daily_session.sh"),
    "mid_collector": ("09:45", ".venv/bin/python scripts/build_lab_nightly_report.py --phase mid-session"),
    "close_collector": (
        "16:05",
        ".venv/bin/python scripts/build_lab_nightly_report.py --phase close-collector",
    ),
    "nightly_report": ("16:20", ".venv/bin/python scripts/build_lab_nightly_report.py --phase post-close"),
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Render Tradeo Lab daily systemd user units.")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    output_dir = Path(args.output_dir or root / "ops" / "systemd" / "user")
    output_dir.mkdir(parents=True, exist_ok=True)
    rendered = []
    for name, (time_et, command) in UNITS.items():
        service = f"tradeo-lab-daily-{name}.service"
        timer = f"tradeo-lab-daily-{name}.timer"
        service_text = service_unit(root, name, command)
        timer_text = timer_unit(name, time_et, service)
        if args.write:
            (output_dir / service).write_text(service_text, encoding="utf-8")
            (output_dir / timer).write_text(timer_text, encoding="utf-8")
        rendered.append({"name": name, "time_new_york": time_et, "service": service, "timer": timer})
    print(json.dumps({"schema": "tradeo.lab_automation.systemd.v1", "units": rendered}, indent=2))
    return 0


def service_unit(root: Path, name: str, command: str) -> str:
    return f"""[Unit]
Description=Tradeo Lab daily {name}

[Service]
Type=oneshot
WorkingDirectory={root}
Environment=TRADEO_LAB_AUTOMATION_ONLY=1
Environment=TRADEO_NO_LIVE=1
ExecStart={command_for_systemd(root, command)}
"""


def timer_unit(name: str, time_et: str, service: str) -> str:
    return f"""[Unit]
Description=Tradeo Lab daily {name} timer

[Timer]
OnCalendar=Mon..Fri *-*-* {time_et}:00 America/New_York
Persistent=false
Unit={service}

[Install]
WantedBy=timers.target
"""


def command_for_systemd(root: Path, command: str) -> str:
    parts = command.split()
    resolved = [str(root / parts[0]) if parts[0].startswith(".") or parts[0] == "scripts/check_lab_paper_readiness.py" else parts[0]]
    resolved.extend(str(root / item) if item.startswith("scripts/") else item for item in parts[1:])
    return " ".join(resolved)


if __name__ == "__main__":
    raise SystemExit(main())
