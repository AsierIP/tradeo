from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import sys
import time
from types import SimpleNamespace


_OVERRIDE_ENV_KEYS = [
    "TRADEO_INTRADAY_UNIVERSE_FILE",
    "TRADEO_INTRADAY_UNIVERSE_POLICY",
    "TRADEO_INTRADAY_RESEARCH_PERIOD",
    "TRADEO_INTRADAY_TIMEFRAMES",
    "TRADEO_INTRADAY_RESEARCH_LIMIT_DEFAULT",
    "TRADEO_INTRADAY_RESEARCH_WINDOW_SIZES",
    "TRADEO_INTRADAY_RESEARCH_FORWARD_BARS",
    "TRADEO_INTRADAY_RESEARCH_MAX_TOTAL_WINDOWS",
    "TRADEO_INTRADAY_RESEARCH_MAX_WINDOWS_PER_SYMBOL",
    "TRADEO_INTRADAY_RESEARCH_VWAP_CONDITION",
    "TRADEO_INTRADAY_RESEARCH_VWAP_SIDE_BIAS",
    "TRADEO_INTRADAY_RESEARCH_VWAP_MAX_DISTANCE_BPS",
    "TRADEO_INTRADAY_RESEARCH_VWAP_MIN_SLOPE_BPS",
    "TRADEO_INTRADAY_RESEARCH_SESSION_FILTER",
    "TRADEO_INTRADAY_RESEARCH_COST_FILTER",
    "TRADEO_INTRADAY_RESEARCH_MAX_EXECUTION_COST_R",
    "TRADEO_INTRADAY_RESEARCH_BENCHMARK_REGIME_FILTER",
    "TRADEO_INTRADAY_RESEARCH_BENCHMARK_SYMBOLS",
]


def _load_runner_module():
    script_path = next(
        (
            parent / "scripts" / "run_intraday_research_wave.py"
            for parent in Path(__file__).resolve().parents
            if (parent / "scripts" / "run_intraday_research_wave.py").exists()
        ),
        None,
    )
    assert script_path is not None
    spec = importlib.util.spec_from_file_location("run_intraday_research_wave", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class _FakeSettings:
    def __init__(
        self,
        *,
        artifacts_path: Path,
        universe_file: str = "/tmp/universe.csv",
        product_policy: str = "stock_only",
        period: str = "60d",
        timeframes: str = "30m",
        limit: int = 117,
        window_sizes: str = "100",
        forward_bars: str = "8,13,21",
        max_total_windows: int = 120000,
        max_windows_per_symbol: int = 1200,
        benchmark_regime_filter: str = "none",
        benchmark_symbols: str = "SPY,QQQ",
    ) -> None:
        self.artifacts_path = artifacts_path
        self.intraday_universe_file = universe_file
        self.intraday_universe_policy = product_policy
        self.intraday_research_period = period
        self.intraday_timeframes = timeframes
        self.intraday_research_limit_default = limit
        self.intraday_research_window_sizes = window_sizes
        self.intraday_research_forward_bars = forward_bars
        self.intraday_research_max_total_windows = max_total_windows
        self.intraday_research_max_windows_per_symbol = max_windows_per_symbol
        self.intraday_research_benchmark_regime_filter = benchmark_regime_filter
        self.intraday_research_benchmark_symbols = benchmark_symbols

    @property
    def intraday_timeframe_list(self) -> list[str]:
        return [item.strip() for item in self.intraday_timeframes.split(",") if item.strip()]

    @property
    def intraday_research_window_size_list(self) -> list[int]:
        return [int(item.strip()) for item in self.intraday_research_window_sizes.split(",") if item.strip()]

    @property
    def intraday_research_forward_bar_list(self) -> list[int]:
        return [int(item.strip()) for item in self.intraday_research_forward_bars.split(",") if item.strip()]


class _FakeReadinessGate:
    def __init__(self, settings) -> None:
        self.settings = settings

    def evaluate(self, spec):
        return SimpleNamespace(
            ready=True,
            coverage=1.0,
            ok=117,
            total=117,
            manifest={"status": "DATA_READY", "ready": True, "spec": runner_asdict(spec)},
            manifest_hash="readiness-hash",
        )


def runner_asdict(spec) -> dict:
    return {
        "universe_file": spec.universe_file,
        "universe_policy": spec.universe_policy,
        "period": spec.period,
        "timeframes": list(spec.timeframes),
        "limit": spec.limit,
        "window_sizes": list(spec.window_sizes),
        "forward_bars": list(spec.forward_bars),
        "max_total_windows": spec.max_total_windows,
        "max_windows_per_symbol": spec.max_windows_per_symbol,
        "min_cache_coverage": spec.min_cache_coverage,
        "min_rows_per_symbol": spec.min_rows_per_symbol,
        "benchmark_regime_filter": spec.benchmark_regime_filter,
        "benchmark_symbols": list(spec.benchmark_symbols),
    }


def _run_main(monkeypatch, runner, argv: list[str]) -> int:
    monkeypatch.setattr(sys, "argv", ["run_intraday_research_wave.py", *argv])
    previous_env = {key: os.environ.get(key) for key in _OVERRIDE_ENV_KEYS}
    try:
        return int(runner.main())
    finally:
        for key, value in previous_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def test_cli_arguments_apply_exact_env_before_settings_and_worker(monkeypatch, tmp_path: Path) -> None:
    runner = _load_runner_module()
    touched_env: dict[str, str | None] = {}
    for key in _OVERRIDE_ENV_KEYS:
        touched_env[key] = os.environ.pop(key, None)

    def fake_get_settings():
        assert os.environ["TRADEO_INTRADAY_UNIVERSE_FILE"] == "/tmp/universe.csv"
        assert os.environ["TRADEO_INTRADAY_UNIVERSE_POLICY"] == "stock_only"
        assert os.environ["TRADEO_INTRADAY_RESEARCH_PERIOD"] == "60d"
        assert os.environ["TRADEO_INTRADAY_TIMEFRAMES"] == "30m"
        assert os.environ["TRADEO_INTRADAY_RESEARCH_LIMIT_DEFAULT"] == "117"
        assert os.environ["TRADEO_INTRADAY_RESEARCH_WINDOW_SIZES"] == "100"
        assert os.environ["TRADEO_INTRADAY_RESEARCH_FORWARD_BARS"] == "8,13,21"
        assert os.environ["TRADEO_INTRADAY_RESEARCH_MAX_TOTAL_WINDOWS"] == "120000"
        assert os.environ["TRADEO_INTRADAY_RESEARCH_MAX_WINDOWS_PER_SYMBOL"] == "1200"
        assert os.environ["TRADEO_INTRADAY_RESEARCH_VWAP_CONDITION"] == "vwap_reclaim_long"
        assert os.environ["TRADEO_INTRADAY_RESEARCH_VWAP_SIDE_BIAS"] == "long"
        assert os.environ["TRADEO_INTRADAY_RESEARCH_VWAP_MAX_DISTANCE_BPS"] == "150.0"
        assert os.environ["TRADEO_INTRADAY_RESEARCH_VWAP_MIN_SLOPE_BPS"] == "0.0"
        assert os.environ["TRADEO_INTRADAY_RESEARCH_SESSION_FILTER"] == "mid"
        assert os.environ["TRADEO_INTRADAY_RESEARCH_COST_FILTER"] == "low_cost"
        assert os.environ["TRADEO_INTRADAY_RESEARCH_MAX_EXECUTION_COST_R"] == "0.15"
        assert os.environ["TRADEO_INTRADAY_RESEARCH_BENCHMARK_REGIME_FILTER"] == "spy_qqq_positive"
        assert os.environ["TRADEO_INTRADAY_RESEARCH_BENCHMARK_SYMBOLS"] == "SPY,QQQ"
        return _FakeSettings(artifacts_path=tmp_path / "artifacts")

    worker_calls: list[dict] = []

    def fake_worker(settings, *, allow_recent_duplicates, store_rejected):
        worker_calls.append(
            {
                "settings": settings,
                "allow_recent_duplicates": allow_recent_duplicates,
                "store_rejected": store_rejected,
            }
        )
        return {"status": "ok"}

    monkeypatch.setattr(runner, "get_settings", fake_get_settings)
    monkeypatch.setattr(runner, "IntradayResearchReadinessGate", _FakeReadinessGate)
    monkeypatch.setattr(runner.worker, "_run_intraday_research_process_pool", fake_worker)

    try:
        code = _run_main(
            monkeypatch,
            runner,
            [
                "--execute",
                "--universe-file",
                "/tmp/universe.csv",
                "--product-policy",
                "stock_only",
                "--period",
                "60d",
                "--timeframes",
                "30m",
                "--limit",
                "117",
                "--window-sizes",
                "100",
                "--forward-bars",
                "8,13,21",
                "--max-total-windows",
                "120000",
                "--max-windows-per-symbol",
                "1200",
                "--vwap-condition",
                "vwap_reclaim_long",
                "--vwap-side-bias",
                "long",
                "--vwap-max-distance-bps",
                "150",
                "--vwap-min-slope-bps",
                "0",
                "--session-filter",
                "mid",
                "--cost-filter",
                "low_cost",
                "--max-execution-cost-r",
                "0.15",
                "--benchmark-regime-filter",
                "spy_qqq_positive",
                "--benchmark-symbols",
                "SPY,QQQ",
                "--manifest-path",
                str(tmp_path / "manifest.json"),
                "--json-only",
            ],
        )
    finally:
        for key, value in touched_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    assert code == 0
    assert len(worker_calls) == 1
    assert worker_calls[0]["store_rejected"] is True


def test_summary_and_manifest_include_execution_spec_and_matching_hashes(
    monkeypatch, tmp_path: Path, capsys
) -> None:
    runner = _load_runner_module()
    manifest_path = tmp_path / "dry_run.json"
    monkeypatch.setattr(
        runner,
        "get_settings",
        lambda: _FakeSettings(artifacts_path=tmp_path / "artifacts"),
    )
    monkeypatch.setattr(runner, "IntradayResearchReadinessGate", _FakeReadinessGate)

    code = _run_main(
        monkeypatch,
        runner,
        [
            "--universe-file",
            "/tmp/universe.csv",
            "--product-policy",
            "stock_only",
            "--period",
            "60d",
            "--timeframes",
            "30m",
            "--limit",
            "117",
            "--window-sizes",
            "100",
            "--forward-bars",
            "8,13,21",
            "--max-total-windows",
            "120000",
            "--max-windows-per-symbol",
            "1200",
            "--store-rejected",
            "--manifest-path",
            str(manifest_path),
            "--json-only",
        ],
    )

    summary = json.loads(capsys.readouterr().out)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert code == 0
    assert summary["decision"] == "ready_dry_run"
    assert summary["specs_match"] is True
    assert summary["execution_spec"]["limit"] == 117
    assert summary["execution_spec"]["store_rejected"] is True
    assert summary["execution_spec"]["vwap_condition"] == "none"
    assert summary["execution_spec"]["session_filter"] == "none"
    assert summary["execution_spec"]["cost_filter"] == "none"
    assert summary["execution_spec"]["max_execution_cost_r"] is None
    assert summary["execution_spec"]["benchmark_regime_filter"] == "none"
    assert summary["execution_spec"]["benchmark_symbols"] == ["SPY", "QQQ"]
    assert manifest["execution_spec"] == summary["execution_spec"]


def test_context_filters_are_included_in_execution_spec(monkeypatch, tmp_path: Path, capsys) -> None:
    runner = _load_runner_module()
    manifest_path = tmp_path / "dry_run_context.json"
    monkeypatch.setattr(
        runner,
        "get_settings",
        lambda: _FakeSettings(artifacts_path=tmp_path / "artifacts"),
    )
    monkeypatch.setattr(runner, "IntradayResearchReadinessGate", _FakeReadinessGate)

    code = _run_main(
        monkeypatch,
        runner,
        [
            "--universe-file",
            "/tmp/universe.csv",
            "--product-policy",
            "stock_only",
            "--period",
            "60d",
            "--timeframes",
            "30m",
            "--limit",
            "117",
            "--window-sizes",
            "100",
            "--forward-bars",
            "8,13,21",
            "--session-filter",
            "mid",
            "--cost-filter",
            "low_cost",
            "--max-execution-cost-r",
            "0.15",
            "--benchmark-regime-filter",
            "spy_qqq_positive",
            "--benchmark-symbols",
            "SPY,QQQ",
            "--manifest-path",
            str(manifest_path),
            "--json-only",
        ],
    )

    summary = json.loads(capsys.readouterr().out)

    assert code == 0
    assert summary["specs_match"] is True
    assert summary["execution_spec"]["session_filter"] == "mid"
    assert summary["execution_spec"]["cost_filter"] == "low_cost"
    assert summary["execution_spec"]["max_execution_cost_r"] == 0.15
    assert summary["execution_spec"]["benchmark_regime_filter"] == "spy_qqq_positive"
    assert summary["execution_spec"]["benchmark_symbols"] == ["SPY", "QQQ"]


def test_spec_hash_changes_when_session_filter_or_cost_threshold_changes() -> None:
    runner = _load_runner_module()
    base = {
        "universe_file": "/tmp/universe.csv",
        "product_policy": "stock_only",
        "period": "60d",
        "timeframes": ["30m"],
        "limit": 117,
        "window_sizes": [50],
        "forward_bars": [4, 8, 13],
        "max_total_windows": 120000,
        "max_windows_per_symbol": 1200,
        "vwap_condition": "vwap_above_rising",
        "vwap_side_bias": "long",
        "vwap_max_distance_bps": 250.0,
        "vwap_min_slope_bps": 0.0,
        "session_filter": "none",
        "cost_filter": "low_cost",
        "max_execution_cost_r": 0.15,
        "benchmark_regime_filter": "none",
        "benchmark_symbols": ["SPY", "QQQ"],
        "store_rejected": True,
    }

    base_hash = runner._stable_spec_hash(runner._normalize_execution_spec(base))
    session_hash = runner._stable_spec_hash(
        runner._normalize_execution_spec({**base, "session_filter": "mid"})
    )
    threshold_hash = runner._stable_spec_hash(
        runner._normalize_execution_spec({**base, "max_execution_cost_r": 0.12})
    )
    benchmark_hash = runner._stable_spec_hash(
        runner._normalize_execution_spec({**base, "benchmark_regime_filter": "spy_qqq_positive"})
    )

    assert session_hash != base_hash
    assert threshold_hash != base_hash
    assert benchmark_hash != base_hash


def test_execute_blocks_mismatch_and_does_not_call_worker(monkeypatch, tmp_path: Path) -> None:
    runner = _load_runner_module()
    manifest_path = tmp_path / "mismatch.json"
    worker_calls: list[bool] = []
    monkeypatch.setattr(
        runner,
        "get_settings",
        lambda: _FakeSettings(artifacts_path=tmp_path / "artifacts"),
    )
    monkeypatch.setattr(runner, "IntradayResearchReadinessGate", _FakeReadinessGate)
    monkeypatch.setattr(
        runner,
        "_execution_spec_from_settings",
        lambda settings, *, store_rejected: {
            "universe_file": "/tmp/universe.csv",
            "product_policy": "stock_only",
            "period": "60d",
            "timeframes": ["30m"],
            "limit": 25,
            "window_sizes": [100],
            "forward_bars": [8, 13, 21],
            "max_total_windows": 120000,
            "max_windows_per_symbol": 1200,
            "vwap_condition": "none",
            "vwap_side_bias": None,
            "vwap_max_distance_bps": None,
            "vwap_min_slope_bps": None,
            "session_filter": "none",
            "cost_filter": "none",
            "max_execution_cost_r": None,
            "benchmark_regime_filter": "none",
            "benchmark_symbols": ["SPY", "QQQ"],
            "store_rejected": store_rejected,
        },
    )
    monkeypatch.setattr(
        runner.worker,
        "_run_intraday_research_process_pool",
        lambda *args, **kwargs: worker_calls.append(True),
    )

    code = _run_main(
        monkeypatch,
        runner,
        [
            "--execute",
            "--universe-file",
            "/tmp/universe.csv",
            "--product-policy",
            "stock_only",
            "--period",
            "60d",
            "--timeframes",
            "30m",
            "--limit",
            "117",
            "--window-sizes",
            "100",
            "--forward-bars",
            "8,13,21",
            "--max-total-windows",
            "120000",
            "--max-windows-per-symbol",
            "1200",
            "--manifest-path",
            str(manifest_path),
            "--json-only",
        ],
    )

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert code == 3
    assert worker_calls == []
    assert manifest["decision"] == "blocked_spec_mismatch"
    assert manifest["specs_match"] is False
    assert manifest["spec_mismatch"]["execution_spec"]["limit"] == 25


def test_execute_blocks_vwap_spec_mismatch_and_does_not_call_worker(monkeypatch, tmp_path: Path) -> None:
    runner = _load_runner_module()
    manifest_path = tmp_path / "vwap_mismatch.json"
    worker_calls: list[bool] = []
    monkeypatch.setattr(
        runner,
        "get_settings",
        lambda: _FakeSettings(artifacts_path=tmp_path / "artifacts"),
    )
    monkeypatch.setattr(runner, "IntradayResearchReadinessGate", _FakeReadinessGate)
    monkeypatch.setattr(
        runner,
        "_execution_spec_from_settings",
        lambda settings, *, store_rejected: {
            "universe_file": "/tmp/universe.csv",
            "product_policy": "stock_only",
            "period": "60d",
            "timeframes": ["30m"],
            "limit": 117,
            "window_sizes": [100],
            "forward_bars": [8, 13, 21],
            "max_total_windows": 120000,
            "max_windows_per_symbol": 1200,
            "vwap_condition": "vwap_reject_short",
            "vwap_side_bias": "short",
            "vwap_max_distance_bps": 150.0,
            "vwap_min_slope_bps": 0.0,
            "session_filter": "none",
            "cost_filter": "none",
            "max_execution_cost_r": None,
            "benchmark_regime_filter": "none",
            "benchmark_symbols": ["SPY", "QQQ"],
            "store_rejected": store_rejected,
        },
    )
    monkeypatch.setattr(
        runner.worker,
        "_run_intraday_research_process_pool",
        lambda *args, **kwargs: worker_calls.append(True),
    )

    code = _run_main(
        monkeypatch,
        runner,
        [
            "--execute",
            "--universe-file",
            "/tmp/universe.csv",
            "--product-policy",
            "stock_only",
            "--period",
            "60d",
            "--timeframes",
            "30m",
            "--limit",
            "117",
            "--window-sizes",
            "100",
            "--forward-bars",
            "8,13,21",
            "--max-total-windows",
            "120000",
            "--max-windows-per-symbol",
            "1200",
            "--vwap-condition",
            "vwap_reclaim_long",
            "--vwap-side-bias",
            "long",
            "--vwap-max-distance-bps",
            "150",
            "--vwap-min-slope-bps",
            "0",
            "--manifest-path",
            str(manifest_path),
            "--json-only",
        ],
    )

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert code == 3
    assert worker_calls == []
    assert manifest["decision"] == "blocked_spec_mismatch"
    assert manifest["spec_mismatch"]["readiness_spec"]["vwap_condition"] == "vwap_reclaim_long"
    assert manifest["spec_mismatch"]["execution_spec"]["vwap_condition"] == "vwap_reject_short"


def test_spec_hash_changes_when_vwap_condition_changes() -> None:
    runner = _load_runner_module()
    base = {
        "universe_file": "/tmp/universe.csv",
        "product_policy": "stock_only",
        "period": "60d",
        "timeframes": ["30m"],
        "limit": 117,
        "window_sizes": [100],
        "forward_bars": [8, 13, 21],
        "max_total_windows": 120000,
        "max_windows_per_symbol": 1200,
        "vwap_condition": "none",
        "vwap_side_bias": None,
        "vwap_max_distance_bps": None,
        "vwap_min_slope_bps": None,
        "benchmark_regime_filter": "none",
        "benchmark_symbols": ["SPY", "QQQ"],
        "store_rejected": True,
    }
    conditioned = base | {"vwap_condition": "vwap_reclaim_long", "vwap_side_bias": "long"}

    assert runner._stable_spec_hash(base) != runner._stable_spec_hash(conditioned)


def test_store_rejected_false_is_reflected_in_execution_spec(monkeypatch, tmp_path: Path, capsys) -> None:
    runner = _load_runner_module()
    monkeypatch.setattr(
        runner,
        "get_settings",
        lambda: _FakeSettings(artifacts_path=tmp_path / "artifacts"),
    )
    monkeypatch.setattr(runner, "IntradayResearchReadinessGate", _FakeReadinessGate)

    code = _run_main(
        monkeypatch,
        runner,
        [
            "--no-store-rejected",
            "--universe-file",
            "/tmp/universe.csv",
            "--product-policy",
            "stock_only",
            "--period",
            "60d",
            "--timeframes",
            "30m",
            "--limit",
            "117",
            "--window-sizes",
            "100",
            "--forward-bars",
            "8,13,21",
            "--max-total-windows",
            "120000",
            "--max-windows-per-symbol",
            "1200",
            "--manifest-path",
            str(tmp_path / "manifest.json"),
            "--json-only",
        ],
    )

    summary = json.loads(capsys.readouterr().out)
    assert code == 0
    assert summary["execution_spec"]["store_rejected"] is False


def test_env_overrides_do_not_enable_live_paper_orders_or_gates(monkeypatch) -> None:
    runner = _load_runner_module()
    protected_keys = {
        "TRADEO_LIVE_TRADING_ENABLED",
        "TRADEO_INTRADAY_PAPER_ENABLED",
        "TRADEO_INTRADAY_LIVE_ENABLED",
        "TRADEO_LABORATORY_AUTO_SUBMIT_PAPER_ORDERS",
        "TRADEO_FOX_HUNTER_AUTO_SUBMIT_LIVE_ORDERS",
        "TRADEO_IBKR_ALLOW_MARKET_ORDERS",
    }
    before = {key: os.environ.get(key) for key in protected_keys}
    previous_env = {key: os.environ.get(key) for key in _OVERRIDE_ENV_KEYS}
    args = SimpleNamespace(
        universe_file="/tmp/universe.csv",
        product_policy="stock_only",
        period="60d",
        timeframes="30m",
        limit=117,
        window_sizes="100",
        forward_bars="8,13,21",
        max_total_windows=120000,
        max_windows_per_symbol=1200,
        vwap_condition="vwap_reclaim_long",
        vwap_side_bias="long",
        vwap_max_distance_bps=150.0,
        vwap_min_slope_bps=0.0,
        session_filter=None,
        cost_filter=None,
        max_execution_cost_r=None,
        benchmark_regime_filter=None,
        benchmark_symbols=None,
    )

    try:
        runner._apply_settings_env_overrides(args)
    finally:
        for key, value in previous_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    assert {key: os.environ.get(key) for key in protected_keys} == before


def test_wave_runner_blocks_execute_when_lock_active(monkeypatch, tmp_path: Path) -> None:
    runner = _load_runner_module()
    settings = _FakeSettings(artifacts_path=tmp_path / "artifacts")
    lock_path = runner._execute_lock_path(settings)
    lock_path.parent.mkdir(parents=True)
    lock_path.write_text("{}", encoding="utf-8")
    worker_calls: list[bool] = []
    monkeypatch.setattr(runner, "get_settings", lambda: settings)
    monkeypatch.setattr(runner, "IntradayResearchReadinessGate", _FakeReadinessGate)
    monkeypatch.setattr(
        runner.worker,
        "_run_intraday_research_process_pool",
        lambda *args, **kwargs: worker_calls.append(True),
    )

    code = _run_main(
        monkeypatch,
        runner,
        ["--execute", "--manifest-path", str(tmp_path / "blocked.json"), "--json-only"],
    )

    manifest = json.loads((tmp_path / "blocked.json").read_text(encoding="utf-8"))
    assert code == 4
    assert manifest["decision"] == "blocked_concurrent_wave"
    assert worker_calls == []


def test_wave_runner_does_not_block_dry_run_with_lock_active(monkeypatch, tmp_path: Path) -> None:
    runner = _load_runner_module()
    settings = _FakeSettings(artifacts_path=tmp_path / "artifacts")
    lock_path = runner._execute_lock_path(settings)
    lock_path.parent.mkdir(parents=True)
    lock_path.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(runner, "get_settings", lambda: settings)
    monkeypatch.setattr(runner, "IntradayResearchReadinessGate", _FakeReadinessGate)

    code = _run_main(monkeypatch, runner, ["--manifest-path", str(tmp_path / "dry.json"), "--json-only"])

    manifest = json.loads((tmp_path / "dry.json").read_text(encoding="utf-8"))
    assert code == 0
    assert manifest["decision"] == "ready_dry_run"
    assert lock_path.exists()


def test_wave_runner_releases_lock_after_worker_ok(monkeypatch, tmp_path: Path) -> None:
    runner = _load_runner_module()
    settings = _FakeSettings(artifacts_path=tmp_path / "artifacts")
    monkeypatch.setattr(runner, "get_settings", lambda: settings)
    monkeypatch.setattr(runner, "IntradayResearchReadinessGate", _FakeReadinessGate)
    monkeypatch.setattr(
        runner.worker,
        "_run_intraday_research_process_pool",
        lambda *args, **kwargs: {"status": "ok"},
    )

    code = _run_main(monkeypatch, runner, ["--execute", "--manifest-path", str(tmp_path / "ok.json"), "--json-only"])

    assert code == 0
    assert not runner._execute_lock_path(settings).exists()


def test_wave_runner_retains_lock_after_worker_exception(monkeypatch, tmp_path: Path) -> None:
    runner = _load_runner_module()
    settings = _FakeSettings(artifacts_path=tmp_path / "artifacts")

    def raise_worker(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(runner, "get_settings", lambda: settings)
    monkeypatch.setattr(runner, "IntradayResearchReadinessGate", _FakeReadinessGate)
    monkeypatch.setattr(runner.worker, "_run_intraday_research_process_pool", raise_worker)

    code = _run_main(
        monkeypatch,
        runner,
        ["--execute", "--manifest-path", str(tmp_path / "exception.json"), "--json-only"],
    )

    manifest = json.loads((tmp_path / "exception.json").read_text(encoding="utf-8"))
    assert code == 1
    assert manifest["research_result"]["lock_retained"] is True
    assert runner._execute_lock_path(settings).exists()


def test_stale_lock_requires_explicit_stale_lock_minutes(tmp_path: Path) -> None:
    runner = _load_runner_module()
    settings = _FakeSettings(artifacts_path=tmp_path / "artifacts")
    lock_path = runner._execute_lock_path(settings)
    lock_path.parent.mkdir(parents=True)
    lock_path.write_text("{}", encoding="utf-8")
    old = time.time() - 3600
    os.utime(lock_path, (old, old))
    spec = {"limit": 1}

    blocked = runner._acquire_execute_lock(
        settings=settings,
        execution_spec=spec,
        execution_spec_hash="hash",
        manifest_path=None,
        stale_lock_minutes=None,
    )
    acquired = runner._acquire_execute_lock(
        settings=settings,
        execution_spec=spec,
        execution_spec_hash="hash",
        manifest_path=None,
        stale_lock_minutes=1,
    )

    assert blocked is None
    assert acquired == lock_path
