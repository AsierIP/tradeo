from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date, datetime, time
import json
import os
from pathlib import Path
from typing import Protocol
from zoneinfo import ZoneInfo

from tradeo.core.config import Settings, get_settings

MARKET_SESSION_POLICY_VERSION = "tradeo.resource_policy.market_session.v1"
NEW_YORK_TZ = ZoneInfo("America/New_York")


class SessionState:
    PRE_MARKET = "PRE_MARKET"
    REGULAR_MARKET = "REGULAR_MARKET"
    POST_MARKET = "POST_MARKET"
    MARKET_CLOSED = "MARKET_CLOSED"
    WEEKEND_OR_HOLIDAY = "WEEKEND_OR_HOLIDAY"
    UNKNOWN = "UNKNOWN"


class PriorityLevel:
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    BLOCKED = "BLOCKED"
    ALLOWED = "ALLOWED"


class JobType:
    LAB_EXECUTION = "lab_execution"
    LAB_READINESS = "lab_readiness"
    LAB_PAPER_PROBE = "lab_paper_probe"
    PAPER_SUBMIT = "paper_submit"
    RESEARCH_HEAVY = "research_heavy"
    RESEARCH_LIGHT = "research_light"
    DAILY_WATCHLIST_REEVAL = "daily_watchlist_reeval"
    DAILY_WATCHLIST_PREP = "daily_watchlist_prep"
    NIGHTLY_REPORT = "nightly_report"
    FAST_ENGINE = "fast_engine"
    LARGE_SCANNER = "large_scanner"
    HEAVY_BACKTEST = "heavy_backtest"
    LIVE = "live"


class HolidayProvider(Protocol):
    def is_holiday(self, day: date) -> bool:
        ...


class EmptyHolidayProvider:
    def is_holiday(self, day: date) -> bool:
        return False


@dataclass(frozen=True, slots=True)
class ResourceBudget:
    session_state: str
    generated_at: str
    timezone: str
    lab_priority: str
    research_priority: str
    daily_watchlist_priority: str
    lab_paper_probe_priority: str
    cpu_slots_lab: int
    cpu_slots_research: int
    max_symbols_lab_cycle: int
    max_symbols_research_cycle: int
    max_process_pool_workers_lab: int
    max_process_pool_workers_research: int
    ibkr_read_budget: str
    ibkr_write_allowed: bool
    market_data_budget: str
    scanner_budget: str
    cache_read_budget: str
    cache_write_budget: str
    heavy_research_allowed: bool
    lab_paper_probe_allowed: bool
    daily_watchlist_reeval_allowed: bool
    blocked_job_types: list[str]
    deny_reasons: dict[str, str]
    reason: str
    policy_version: str = MARKET_SESSION_POLICY_VERSION

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    def public_status(self) -> dict[str, object]:
        return {
            "session_state": self.session_state,
            "priorities": {
                "lab": self.lab_priority,
                "research": self.research_priority,
                "daily_watchlist": self.daily_watchlist_priority,
                "lab_paper_probe": self.lab_paper_probe_priority,
            },
            "budgets": {
                "cpu_slots_lab": self.cpu_slots_lab,
                "cpu_slots_research": self.cpu_slots_research,
                "max_symbols_lab_cycle": self.max_symbols_lab_cycle,
                "max_symbols_research_cycle": self.max_symbols_research_cycle,
                "max_process_pool_workers_lab": self.max_process_pool_workers_lab,
                "max_process_pool_workers_research": self.max_process_pool_workers_research,
                "ibkr_read_budget": self.ibkr_read_budget,
                "ibkr_write_allowed": self.ibkr_write_allowed,
                "market_data_budget": self.market_data_budget,
                "scanner_budget": self.scanner_budget,
                "cache_read_budget": self.cache_read_budget,
                "cache_write_budget": self.cache_write_budget,
                "heavy_research_allowed": self.heavy_research_allowed,
                "lab_paper_probe_allowed": self.lab_paper_probe_allowed,
                "daily_watchlist_reeval_allowed": self.daily_watchlist_reeval_allowed,
            },
            "blocked_job_types": list(self.blocked_job_types),
            "generated_at": self.generated_at,
            "timezone": self.timezone,
            "reason": self.reason,
        }


@dataclass(frozen=True, slots=True)
class JobDecision:
    allowed: bool
    priority: str
    reason: str
    budget: ResourceBudget

    def to_dict(self) -> dict[str, object]:
        return {
            "allowed": self.allowed,
            "priority": self.priority,
            "reason": self.reason,
            "session_state": self.budget.session_state,
        }


@dataclass(slots=True)
class MarketSessionResourcePolicy:
    settings: Settings | None = None
    holiday_provider: HolidayProvider | None = None
    forced_session_state: str | None = None
    timezone: ZoneInfo = field(default=NEW_YORK_TZ)

    def current_budget(self, now: datetime | None = None) -> ResourceBudget:
        current = self._coerce_now(now)
        state = self.forced_session_state or self.classify_session(current)
        budget = self._budget_for_state(state, current)
        self.write_latest_artifact(budget)
        return budget

    def classify_session(self, now: datetime | None = None) -> str:
        current = self._coerce_now(now)
        try:
            if current.weekday() >= 5 or self._holiday_provider().is_holiday(current.date()):
                return SessionState.WEEKEND_OR_HOLIDAY
            t = current.time()
            if time(4, 0) <= t < time(9, 30):
                return SessionState.PRE_MARKET
            if time(9, 30) <= t < time(16, 0):
                return SessionState.REGULAR_MARKET
            if time(16, 0) <= t < time(20, 0):
                return SessionState.POST_MARKET
            return SessionState.MARKET_CLOSED
        except Exception:  # noqa: BLE001 - calendar uncertainty must fail closed.
            return SessionState.UNKNOWN

    def decide_job(self, job_type: str, now: datetime | None = None) -> JobDecision:
        budget = self.current_budget(now)
        normalized = str(job_type).strip().lower()
        if normalized in budget.blocked_job_types:
            return JobDecision(
                allowed=False,
                priority=PriorityLevel.BLOCKED,
                reason=budget.deny_reasons.get(normalized, budget.reason),
                budget=budget,
            )
        if normalized in {JobType.LAB_EXECUTION, JobType.LAB_READINESS}:
            return JobDecision(True, budget.lab_priority, budget.reason, budget)
        if normalized == JobType.LAB_PAPER_PROBE:
            return JobDecision(
                budget.lab_paper_probe_allowed,
                budget.lab_paper_probe_priority if budget.lab_paper_probe_allowed else PriorityLevel.BLOCKED,
                budget.reason if budget.lab_paper_probe_allowed else budget.deny_reasons.get(normalized, budget.reason),
                budget,
            )
        if normalized == JobType.PAPER_SUBMIT:
            return JobDecision(
                False,
                PriorityLevel.BLOCKED,
                budget.deny_reasons.get(
                    normalized,
                    "paper submit is blocked unless an explicit Lab Paper Probe gate allows it",
                ),
                budget,
            )
        if normalized == JobType.RESEARCH_HEAVY:
            return JobDecision(
                budget.heavy_research_allowed,
                budget.research_priority if budget.heavy_research_allowed else PriorityLevel.BLOCKED,
                budget.reason if budget.heavy_research_allowed else budget.deny_reasons.get(normalized, budget.reason),
                budget,
            )
        if normalized in {JobType.DAILY_WATCHLIST_REEVAL, JobType.DAILY_WATCHLIST_PREP}:
            return JobDecision(
                budget.daily_watchlist_reeval_allowed,
                budget.daily_watchlist_priority,
                budget.reason,
                budget,
            )
        if normalized == JobType.LIVE:
            return JobDecision(False, PriorityLevel.BLOCKED, "live orders are outside this policy and remain blocked", budget)
        return JobDecision(True, PriorityLevel.LOW, "unclassified job receives LOW priority metadata only", budget)

    def write_latest_artifact(self, budget: ResourceBudget) -> Path:
        path = self._settings().artifacts_path / "runtime" / "resource_policy" / "latest.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = budget.to_dict()
        tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
        tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(tmp, path)
        return path

    def _budget_for_state(self, state: str, current: datetime) -> ResourceBudget:
        generated = current.astimezone(self.timezone).isoformat()
        if state == SessionState.PRE_MARKET:
            return self._budget(
                state,
                generated,
                lab=PriorityLevel.HIGH,
                research=PriorityLevel.LOW,
                daily=PriorityLevel.MEDIUM,
                lab_probe=PriorityLevel.HIGH,
                cpu_lab=3,
                cpu_research=1,
                max_lab=120,
                max_research=20,
                workers_lab=2,
                workers_research=1,
                ibkr_write=False,
                heavy=False,
                lab_probe_allowed=True,
                daily_allowed=True,
                blocked=[JobType.RESEARCH_HEAVY, JobType.PAPER_SUBMIT, JobType.HEAVY_BACKTEST, JobType.LARGE_SCANNER, JobType.LIVE],
                reason="pre-market prioritizes Lab readiness and paper-probe preparation; heavy Research is blocked",
            )
        if state == SessionState.REGULAR_MARKET:
            return self._budget(
                state,
                generated,
                lab=PriorityLevel.HIGH,
                research=PriorityLevel.LOW,
                daily=PriorityLevel.MEDIUM,
                lab_probe=PriorityLevel.HIGH,
                cpu_lab=4,
                cpu_research=1,
                max_lab=160,
                max_research=10,
                workers_lab=3,
                workers_research=1,
                ibkr_write=True,
                heavy=False,
                lab_probe_allowed=True,
                daily_allowed=True,
                blocked=[
                    JobType.RESEARCH_HEAVY,
                    JobType.PAPER_SUBMIT,
                    JobType.HEAVY_BACKTEST,
                    JobType.LARGE_SCANNER,
                    JobType.LIVE,
                ],
                reason="regular market gives Lab and Lab Paper Probe priority; Research heavy jobs are blocked",
            )
        if state == SessionState.POST_MARKET:
            return self._budget(
                state,
                generated,
                lab=PriorityLevel.BLOCKED,
                research=PriorityLevel.MEDIUM,
                daily=PriorityLevel.HIGH,
                lab_probe=PriorityLevel.BLOCKED,
                cpu_lab=1,
                cpu_research=3,
                max_lab=20,
                max_research=120,
                workers_lab=1,
                workers_research=2,
                ibkr_write=False,
                heavy=True,
                lab_probe_allowed=False,
                daily_allowed=True,
                blocked=[JobType.LAB_EXECUTION, JobType.PAPER_SUBMIT, JobType.LIVE],
                reason="post-market prioritizes Daily reevaluation, nightly reports and medium Research batch work",
            )
        if state == SessionState.MARKET_CLOSED:
            return self._budget(
                state,
                generated,
                lab=PriorityLevel.LOW,
                research=PriorityLevel.HIGH,
                daily=PriorityLevel.HIGH,
                lab_probe=PriorityLevel.BLOCKED,
                cpu_lab=1,
                cpu_research=4,
                max_lab=20,
                max_research=200,
                workers_lab=1,
                workers_research=4,
                ibkr_write=False,
                heavy=True,
                lab_probe_allowed=False,
                daily_allowed=True,
                blocked=[JobType.PAPER_SUBMIT, JobType.LIVE],
                reason="market closed allows heavy Research and Daily after-close reevaluation; paper/live submit blocked",
            )
        if state == SessionState.WEEKEND_OR_HOLIDAY:
            return self._budget(
                state,
                generated,
                lab=PriorityLevel.BLOCKED,
                research=PriorityLevel.HIGH,
                daily=PriorityLevel.ALLOWED,
                lab_probe=PriorityLevel.BLOCKED,
                cpu_lab=0,
                cpu_research=4,
                max_lab=0,
                max_research=200,
                workers_lab=0,
                workers_research=4,
                ibkr_write=False,
                heavy=True,
                lab_probe_allowed=False,
                daily_allowed=True,
                blocked=[JobType.LAB_EXECUTION, JobType.LAB_PAPER_PROBE, JobType.PAPER_SUBMIT, JobType.LIVE],
                reason="weekend or holiday allows Research batch and Daily maintenance; Lab execution and paper/live submit blocked",
            )
        return self._budget(
            SessionState.UNKNOWN,
            generated,
            lab=PriorityLevel.BLOCKED,
            research=PriorityLevel.BLOCKED,
            daily=PriorityLevel.BLOCKED,
            lab_probe=PriorityLevel.BLOCKED,
            cpu_lab=0,
            cpu_research=0,
            max_lab=0,
            max_research=0,
            workers_lab=0,
            workers_research=0,
            ibkr_write=False,
            heavy=False,
            lab_probe_allowed=False,
            daily_allowed=False,
            blocked=[
                JobType.LAB_EXECUTION,
                JobType.LAB_PAPER_PROBE,
                JobType.PAPER_SUBMIT,
                JobType.RESEARCH_HEAVY,
                JobType.RESEARCH_LIGHT,
                JobType.DAILY_WATCHLIST_REEVAL,
                JobType.HEAVY_BACKTEST,
                JobType.LARGE_SCANNER,
                JobType.LIVE,
            ],
            reason="session state unknown; policy fails closed",
        )

    def _budget(
        self,
        state: str,
        generated: str,
        *,
        lab: str,
        research: str,
        daily: str,
        lab_probe: str,
        cpu_lab: int,
        cpu_research: int,
        max_lab: int,
        max_research: int,
        workers_lab: int,
        workers_research: int,
        ibkr_write: bool,
        heavy: bool,
        lab_probe_allowed: bool,
        daily_allowed: bool,
        blocked: list[str],
        reason: str,
    ) -> ResourceBudget:
        deny = {job: reason for job in blocked}
        if JobType.PAPER_SUBMIT in blocked:
            deny[JobType.PAPER_SUBMIT] = "paper submit is blocked unless an explicit Lab Paper Probe gate allows it"
        deny[JobType.LIVE] = "live orders are never allowed by this policy"
        return ResourceBudget(
            session_state=state,
            generated_at=generated,
            timezone="America/New_York",
            lab_priority=lab,
            research_priority=research,
            daily_watchlist_priority=daily,
            lab_paper_probe_priority=lab_probe,
            cpu_slots_lab=cpu_lab,
            cpu_slots_research=cpu_research,
            max_symbols_lab_cycle=max_lab,
            max_symbols_research_cycle=max_research,
            max_process_pool_workers_lab=workers_lab,
            max_process_pool_workers_research=workers_research,
            ibkr_read_budget="limited" if state == SessionState.UNKNOWN else "normal",
            ibkr_write_allowed=ibkr_write,
            market_data_budget="blocked" if state == SessionState.UNKNOWN else "session_scoped",
            scanner_budget="blocked" if state == SessionState.UNKNOWN else "session_scoped",
            cache_read_budget="blocked" if state == SessionState.UNKNOWN else "normal",
            cache_write_budget="blocked" if state == SessionState.UNKNOWN else "normal",
            heavy_research_allowed=heavy,
            lab_paper_probe_allowed=lab_probe_allowed,
            daily_watchlist_reeval_allowed=daily_allowed,
            blocked_job_types=blocked,
            deny_reasons=deny,
            reason=reason,
        )

    def _coerce_now(self, now: datetime | None) -> datetime:
        current = now or datetime.now(tz=self.timezone)
        if current.tzinfo is None:
            current = current.replace(tzinfo=self.timezone)
        return current.astimezone(self.timezone)

    def _holiday_provider(self) -> HolidayProvider:
        return self.holiday_provider or EmptyHolidayProvider()

    def _settings(self) -> Settings:
        return self.settings or get_settings()
