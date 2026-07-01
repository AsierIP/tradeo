from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Literal

from tradeo.core.config import Settings, get_settings
from tradeo.services.data_provider import normalize_universe_policy, pick_symbols

ReadinessStatus = Literal["DATA_READY", "DATA_MISSING"]


@dataclass(frozen=True, slots=True)
class IntradayResearchWaveSpec:
    universe_file: str
    period: str
    timeframes: tuple[str, ...]
    limit: int
    window_sizes: tuple[int, ...]
    forward_bars: tuple[int, ...]
    max_total_windows: int
    max_windows_per_symbol: int
    min_cache_coverage: float = 0.90
    min_rows_per_symbol: int = 1
    universe_policy: str = "stock_only"

    @classmethod
    def from_settings(
        cls,
        settings: Settings | None = None,
        *,
        universe_file: str | None = None,
        universe_policy: str | None = None,
        period: str | None = None,
        timeframes: tuple[str, ...] | None = None,
        limit: int | None = None,
        window_sizes: tuple[int, ...] | None = None,
        forward_bars: tuple[int, ...] | None = None,
        max_total_windows: int | None = None,
        max_windows_per_symbol: int | None = None,
        min_cache_coverage: float = 0.90,
        min_rows_per_symbol: int = 1,
    ) -> "IntradayResearchWaveSpec":
        s = settings or get_settings()
        return cls(
            universe_file=str(universe_file or s.intraday_universe_file),
            universe_policy=normalize_universe_policy(
                universe_policy or getattr(s, "intraday_universe_policy", "stock_only")
            ),
            period=str(period or s.intraday_research_period),
            timeframes=tuple(timeframes or tuple(s.intraday_timeframe_list)),
            limit=int(limit or s.intraday_research_limit_default),
            window_sizes=tuple(window_sizes or tuple(s.intraday_research_window_size_list)),
            forward_bars=tuple(forward_bars or tuple(s.intraday_research_forward_bar_list)),
            max_total_windows=int(max_total_windows or s.intraday_research_max_total_windows),
            max_windows_per_symbol=int(
                max_windows_per_symbol or s.intraday_research_max_windows_per_symbol
            ),
            min_cache_coverage=float(min_cache_coverage),
            min_rows_per_symbol=int(min_rows_per_symbol),
        )


@dataclass(frozen=True, slots=True)
class CacheArtifactCheck:
    symbol: str
    timeframe: str
    period: str
    path: str
    ok: bool
    reason: str
    rows: int = 0
    last_timestamp: str = ""
    artifact_sha256: str = ""


@dataclass(frozen=True, slots=True)
class IntradayResearchReadinessResult:
    status: ReadinessStatus
    ready: bool
    coverage: float
    ok: int
    total: int
    missing_or_bad: int
    manifest_hash: str
    manifest: dict[str, Any]
    checks: tuple[CacheArtifactCheck, ...]


@dataclass(slots=True)
class IntradayResearchReadinessGate:
    settings: Settings | None = None

    def __post_init__(self) -> None:
        self.settings = self.settings or get_settings()

    def evaluate(self, spec: IntradayResearchWaveSpec) -> IntradayResearchReadinessResult:
        assert self.settings is not None
        checks: list[CacheArtifactCheck] = []
        symbols_by_timeframe: dict[str, list[str]] = {}
        for timeframe in spec.timeframes:
            symbols = pick_symbols(
                limit=spec.limit,
                interval=timeframe,
                universe_file=spec.universe_file,
                universe_policy=spec.universe_policy,
            )
            symbols_by_timeframe[timeframe] = symbols
            for symbol in symbols:
                checks.append(
                    self._check_cache_artifact(
                        symbol=symbol,
                        timeframe=timeframe,
                        period=spec.period,
                        min_rows=spec.min_rows_per_symbol,
                    )
                )

        ok = sum(1 for check in checks if check.ok)
        total = len(checks)
        coverage = ok / max(total, 1)
        ready = total > 0 and coverage >= spec.min_cache_coverage
        status: ReadinessStatus = "DATA_READY" if ready else "DATA_MISSING"
        manifest = {
            "schema_version": 1,
            "generated_at": datetime.now(UTC).isoformat(),
            "status": status,
            "ready": ready,
            "coverage": round(coverage, 6),
            "ok": ok,
            "total": total,
            "missing_or_bad": total - ok,
            "cache_dir": str(self.settings.market_data_cache_path),
            "spec": asdict(spec),
            "symbols_by_timeframe": symbols_by_timeframe,
            "missing_preview": [asdict(check) for check in checks if not check.ok][:50],
            "checks": [asdict(check) for check in checks],
        }
        manifest_hash = self._manifest_hash(manifest)
        manifest["manifest_hash"] = manifest_hash
        return IntradayResearchReadinessResult(
            status=status,
            ready=ready,
            coverage=round(coverage, 6),
            ok=ok,
            total=total,
            missing_or_bad=total - ok,
            manifest_hash=manifest_hash,
            manifest=manifest,
            checks=tuple(checks),
        )

    def write_manifest(self, result: IntradayResearchReadinessResult, path: str | Path) -> Path:
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result.manifest, indent=2, sort_keys=True), encoding="utf-8")
        return output

    def _check_cache_artifact(
        self,
        *,
        symbol: str,
        timeframe: str,
        period: str,
        min_rows: int,
    ) -> CacheArtifactCheck:
        csv_path = self._cache_path(symbol, timeframe, period)
        meta_path = csv_path.with_suffix(".metadata.json")
        base = {
            "symbol": symbol.upper(),
            "timeframe": timeframe,
            "period": period,
            "path": str(csv_path),
        }
        if not csv_path.exists():
            return CacheArtifactCheck(**base, ok=False, reason="csv_missing")
        if not meta_path.exists():
            return CacheArtifactCheck(**base, ok=False, reason="metadata_missing")
        try:
            metadata = json.loads(meta_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return CacheArtifactCheck(**base, ok=False, reason="metadata_invalid_json")
        if str(metadata.get("symbol") or "").upper() != symbol.upper():
            return CacheArtifactCheck(**base, ok=False, reason="metadata_symbol_mismatch")
        if str(metadata.get("period") or "") != str(period):
            return CacheArtifactCheck(**base, ok=False, reason="metadata_period_mismatch")
        if str(metadata.get("interval") or "") != str(timeframe):
            return CacheArtifactCheck(**base, ok=False, reason="metadata_interval_mismatch")
        rows = int(metadata.get("rows") or 0)
        if rows < int(min_rows):
            return CacheArtifactCheck(**base, ok=False, reason="rows_below_min", rows=rows)
        return CacheArtifactCheck(
            **base,
            ok=True,
            reason="ok",
            rows=rows,
            last_timestamp=str(metadata.get("last_timestamp") or ""),
            artifact_sha256=str(metadata.get("sha256") or ""),
        )

    def _cache_path(self, symbol: str, timeframe: str, period: str) -> Path:
        assert self.settings is not None
        safe = "_".join(_safe_part(part) for part in (symbol.upper(), timeframe, period))
        return self.settings.market_data_cache_path / f"{safe}.csv"

    @staticmethod
    def _manifest_hash(manifest: dict[str, Any]) -> str:
        stable = {key: value for key, value in manifest.items() if key != "manifest_hash"}
        return sha256(json.dumps(stable, sort_keys=True, default=str).encode()).hexdigest()


def _safe_part(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in {"-", "."} else "_" for ch in value).strip("._")
