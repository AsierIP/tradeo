"""Test-session environment defaults.

Settings path properties (reports, artifacts, market data cache, universe
snapshots) create their directories on first access. The shipped defaults
live under ``/app`` which only exists inside the Docker image, so local test
runs would fail with ``PermissionError``. Point them at a temp dir unless the
environment already overrides them.
"""

from __future__ import annotations

import os
import tempfile

_TEST_DATA_ROOT = tempfile.mkdtemp(prefix="tradeo-tests-")

for _name, _sub in (
    ("TRADEO_MARKET_DATA_CACHE_DIR", "ohlcv_cache"),
    ("TRADEO_UNIVERSE_SNAPSHOT_DIR", "universe_snapshots"),
    ("TRADEO_REPORTS_DIR", "reports"),
    ("TRADEO_ARTIFACTS_DIR", "artifacts"),
):
    os.environ.setdefault(_name, os.path.join(_TEST_DATA_ROOT, _sub))

# No IBKR is reachable in tests: the per-signal spread snapshot would attempt
# a broker connection for every stored signal. Tests that exercise it inject
# a fake provider and enable the flag explicitly on their own Settings.
os.environ.setdefault("TRADEO_SIGNAL_SPREAD_SNAPSHOT_ENABLED", "false")
