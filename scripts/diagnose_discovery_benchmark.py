#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Any


DEFAULT_GROUPS = (
    "warmup_2042_2051:2042-2051",
    "round1_fast_2053_2062:2053-2062",
    "pre_current_2074_2083:2074-2083",
    "current_a_2084_2093:2084-2093",
    "current_b_2094_2103:2094-2103",
    "current_c_2104_2113:2104-2113",
    "round3_fixed_2216_2225:2216-2225",
    "current_best_2396_2405:2396-2405",
    "current_best_2478_2487:2478-2487",
)

DEFAULT_AUTO_RECENT_LOOKBACK = 250
DEFAULT_AUTO_GROUP_SIZE = 10
DEFAULT_AUTO_GROUP_COUNT = 4


@dataclass(frozen=True)
class GroupSpec:
    label: str
    first_id: int
    last_id: int

    def contains(self, run_id: int) -> bool:
        return self.first_id <= run_id <= self.last_id


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compare DiscoveryRun benchmark batches with report hashes."
    )
    parser.add_argument(
        "--group",
        action="append",
        default=[],
        metavar="LABEL:START-END",
        help="Group to compare. Defaults cover the 2026-06-28 benchmark loop.",
    )
    parser.add_argument("--container", default="tradeo-db", help="Postgres Docker container name.")
    parser.add_argument("--db-user", default="tradeo")
    parser.add_argument("--db-name", default="tradeo")
    parser.add_argument("--repo-root", default=".", help="Repository root for /app report path mapping.")
    parser.add_argument(
        "--baseline",
        default=None,
        help="Baseline group label for workload pivots. Defaults to the first round1 group.",
    )
    parser.add_argument(
        "--no-auto-recent",
        action="store_true",
        help="Do not append recent valid repeat groups discovered from discovery_runs.",
    )
    parser.add_argument(
        "--auto-recent-lookback",
        type=int,
        default=DEFAULT_AUTO_RECENT_LOOKBACK,
        help="Recent discovery_runs rows to scan for automatic repeat grouping.",
    )
    parser.add_argument(
        "--auto-group-size",
        type=int,
        default=DEFAULT_AUTO_GROUP_SIZE,
        help="Consecutive valid runs per automatic repeat group.",
    )
    parser.add_argument(
        "--auto-group-count",
        type=int,
        default=DEFAULT_AUTO_GROUP_COUNT,
        help="Maximum number of recent automatic repeat groups to append.",
    )
    args = parser.parse_args()

    groups = [_parse_group(raw) for raw in (args.group or list(DEFAULT_GROUPS))]
    recent_rows: list[dict[str, Any]] = []
    if not args.no_auto_recent:
        recent_rows = _load_recent_rows(
            args.container,
            args.db_user,
            args.db_name,
            max(int(args.auto_recent_lookback), int(args.auto_group_size)),
        )
        groups = _dedupe_groups(
            [
                *groups,
                *_auto_recent_groups(
                    recent_rows,
                    group_size=max(1, int(args.auto_group_size)),
                    max_groups=max(0, int(args.auto_group_count)),
                    existing=groups,
                ),
            ]
        )
    baseline = _select_baseline(groups, args.baseline)
    rows = _load_rows(args.container, args.db_user, args.db_name, groups)
    repo_root = Path(args.repo_root).resolve()
    enriched = [_with_report_details(row, repo_root) for row in rows]
    valid_enriched = [row for row in enriched if _is_valid_run(row)]

    print("group_summary")
    print(
        "group\truns\tinvalid_runs\twall_s\tavg_run_s\tmax_run_s\ttail_run_id\ttail_interval"
        "\ttail_symbols\ttail_run_s\ttail_pct_wall\twindows\tclusters\taccepted"
        "\trejected\twarnings\treport_missing\tphase_missing"
        "\tunique_manifest_hashes\tunique_pattern_hashes"
    )
    for group in groups:
        all_group_rows = [row for row in enriched if row["group"] == group.label]
        group_rows = [row for row in valid_enriched if row["group"] == group.label]
        invalid_count = len(all_group_rows) - len(group_rows)
        if not group_rows:
            print(
                f"{group.label}\t0\t{invalid_count}\tNA\tNA\tNA\tNA\tNA\tNA\tNA\tNA"
                "\t0\t0\t0\t0\t0\t0\t0\t0\t0"
            )
            continue
        wall_s = (
            max(row["finished_epoch"] for row in group_rows)
            - min(row["started_epoch"] for row in group_rows)
        )
        tail_row = max(group_rows, key=lambda row: row["duration_seconds"])
        tail_pct_wall = (
            None if wall_s <= 0 else (tail_row["duration_seconds"] / wall_s) * 100.0
        )
        manifest_hashes = {row.get("manifest_hash") for row in group_rows if row.get("manifest_hash")}
        pattern_hashes = {row.get("pattern_fingerprint") for row in group_rows if row.get("pattern_fingerprint")}
        print(
            "\t".join(
                [
                    group.label,
                    str(len(group_rows)),
                    str(invalid_count),
                    _fmt(wall_s),
                    _fmt(mean(row["duration_seconds"] for row in group_rows)),
                    _fmt(max(row["duration_seconds"] for row in group_rows)),
                    str(tail_row["id"]),
                    str(tail_row["interval"]),
                    json.dumps(tail_row["symbols"], separators=(",", ":")),
                    _fmt(tail_row["duration_seconds"]),
                    _fmt(tail_pct_wall),
                    str(sum(row["windows_sampled"] for row in group_rows)),
                    str(sum(row["clusters_evaluated"] for row in group_rows)),
                    str(sum(row["accepted_patterns"] for row in group_rows)),
                    str(sum(row["rejected_patterns"] for row in group_rows)),
                    str(sum(row.get("warning_count", 0) for row in group_rows)),
                    str(sum(1 for row in group_rows if row.get("report_missing"))),
                    str(sum(1 for row in group_rows if not row.get("phase_timings"))),
                    str(len(manifest_hashes)),
                    str(len(pattern_hashes)),
                ]
            )
        )

    _print_invalid_runs(groups, enriched, recent_rows)
    _print_phase_summary(groups, valid_enriched)
    _print_clustering_profile_summary(groups, valid_enriched)

    comparison_groups = [group.label for group in groups if group.label != baseline]
    print()
    print(f"workload_pivot baseline={baseline}")
    header = [
        "tf",
        "symbols",
        "windows",
        "clusters",
        baseline,
        *comparison_groups,
        "comparison_avg",
        "delta_s",
        "delta_pct",
        "same_manifest_vs_baseline",
        "same_patterns_vs_baseline",
    ]
    print("\t".join(header))

    by_workload: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in valid_enriched:
        key = (row["interval"], json.dumps(row["symbols"], separators=(",", ":")))
        by_workload.setdefault(key, []).append(row)

    for (interval, symbols_json), workload_rows in sorted(by_workload.items(), key=lambda item: item[0]):
        by_group = {row["group"]: row for row in workload_rows}
        baseline_row = by_group.get(baseline)
        if baseline_row is None:
            continue
        comparison_durations = [
            by_group[label]["duration_seconds"] for label in comparison_groups if label in by_group
        ]
        comparison_avg = mean(comparison_durations) if comparison_durations else None
        delta_s = (
            None
            if comparison_avg is None
            else comparison_avg - baseline_row["duration_seconds"]
        )
        delta_pct = None if delta_s is None else (delta_s / baseline_row["duration_seconds"]) * 100.0
        baseline_manifest_hash = baseline_row.get("manifest_hash")
        comparison_manifest_hashes = {
            by_group[label].get("manifest_hash")
            for label in comparison_groups
            if label in by_group and by_group[label].get("manifest_hash")
        }
        same_manifest = bool(
            baseline_manifest_hash
            and comparison_manifest_hashes
            and comparison_manifest_hashes == {baseline_manifest_hash}
        )
        baseline_pattern_hash = baseline_row.get("pattern_fingerprint")
        comparison_pattern_hashes = {
            by_group[label].get("pattern_fingerprint")
            for label in comparison_groups
            if label in by_group and by_group[label].get("pattern_fingerprint")
        }
        same_patterns = bool(
            baseline_pattern_hash
            and comparison_pattern_hashes
            and comparison_pattern_hashes == {baseline_pattern_hash}
        )
        values = [
            interval,
            symbols_json,
            str(baseline_row["windows_sampled"]),
            str(baseline_row["clusters_evaluated"]),
            _fmt(baseline_row["duration_seconds"]),
            *[
                _fmt(by_group[label]["duration_seconds"]) if label in by_group else "NA"
                for label in comparison_groups
            ],
            _fmt(comparison_avg),
            _fmt(delta_s),
            _fmt(delta_pct),
            str(same_manifest).lower(),
            str(same_patterns).lower(),
        ]
        print("\t".join(values))

    return 0


def _select_baseline(groups: list[GroupSpec], requested: str | None) -> str:
    labels = {group.label for group in groups}
    if requested:
        if requested not in labels:
            raise SystemExit(f"Unknown baseline {requested!r}; expected one of {sorted(labels)}")
        return requested
    for group in groups:
        if group.label.startswith("round1"):
            return group.label
    return groups[0].label


def _parse_group(raw: str) -> GroupSpec:
    label, _, span = raw.partition(":")
    if not label or not span or "-" not in span:
        raise SystemExit(f"Invalid group {raw!r}; expected LABEL:START-END")
    first, _, last = span.partition("-")
    return GroupSpec(label=label, first_id=int(first), last_id=int(last))


def _dedupe_groups(groups: list[GroupSpec]) -> list[GroupSpec]:
    seen: set[tuple[str, int, int]] = set()
    output: list[GroupSpec] = []
    for group in groups:
        key = (group.label, group.first_id, group.last_id)
        span = (group.first_id, group.last_id)
        if key in seen or any((existing.first_id, existing.last_id) == span for existing in output):
            continue
        seen.add(key)
        output.append(group)
    return output


def _load_recent_rows(
    container: str,
    db_user: str,
    db_name: str,
    limit: int,
) -> list[dict[str, Any]]:
    sql = f"""
        select jsonb_build_object(
            'id', id,
            'started_at', started_at,
            'status', status,
            'windows_sampled', windows_sampled,
            'clusters_evaluated', clusters_evaluated,
            'accepted_patterns', accepted_patterns,
            'rejected_patterns', rejected_patterns,
            'interval', params_json->>'interval',
            'symbols', params_json->'symbols'
        )::text
        from discovery_runs
        order by id desc
        limit {max(1, int(limit))}
    """
    cmd = [
        "docker",
        "exec",
        container,
        "psql",
        "-U",
        db_user,
        "-d",
        db_name,
        "-At",
        "-c",
        sql,
    ]
    output = subprocess.check_output(cmd, text=True)
    return [json.loads(line) for line in output.splitlines() if line.strip()]


def _auto_recent_groups(
    recent_rows: list[dict[str, Any]],
    *,
    group_size: int,
    max_groups: int,
    existing: list[GroupSpec],
) -> list[GroupSpec]:
    if group_size <= 0 or max_groups <= 0:
        return []

    existing_spans = {(group.first_id, group.last_id) for group in existing}
    rows = sorted(recent_rows, key=lambda row: _int(row.get("id")))
    valid_ids = [_int(row.get("id")) for row in rows if _is_valid_run(row)]
    segments: list[list[int]] = []
    current: list[int] = []
    previous: int | None = None
    for run_id in valid_ids:
        if previous is None or run_id == previous + 1:
            current.append(run_id)
        else:
            if current:
                segments.append(current)
            current = [run_id]
        previous = run_id
    if current:
        segments.append(current)

    candidates: list[tuple[int, int]] = []
    for segment in segments:
        usable = len(segment) - (len(segment) % group_size)
        for index in range(0, usable, group_size):
            chunk = segment[index : index + group_size]
            candidates.append((chunk[0], chunk[-1]))

    selected = [
        span
        for span in candidates[-max_groups:]
        if span not in existing_spans
    ]
    return [
        GroupSpec(label=f"repeat{index}_{first}_{last}", first_id=first, last_id=last)
        for index, (first, last) in enumerate(selected, start=1)
    ]


def _load_rows(container: str, db_user: str, db_name: str, groups: list[GroupSpec]) -> list[dict[str, Any]]:
    first_id = min(group.first_id for group in groups)
    last_id = max(group.last_id for group in groups)
    case_sql = " ".join(
        f"when id between {group.first_id} and {group.last_id} then '{group.label}'"
        for group in groups
    )
    sql = f"""
        select jsonb_build_object(
            'group', case {case_sql} end,
            'id', id,
            'started_at', started_at,
            'finished_at', finished_at,
            'started_epoch', extract(epoch from started_at),
            'finished_epoch', extract(epoch from finished_at),
            'status', status,
            'duration_seconds', duration_seconds,
            'symbols_scanned', symbols_scanned,
            'windows_sampled', windows_sampled,
            'clusters_evaluated', clusters_evaluated,
            'accepted_patterns', accepted_patterns,
            'rejected_patterns', rejected_patterns,
            'interval', params_json->>'interval',
            'symbols', params_json->'symbols',
            'params_json', params_json,
            'summary_json', summary_json,
            'report_path', report_path
        )::text
        from discovery_runs
        where id between {first_id} and {last_id}
        order by id
    """
    cmd = [
        "docker",
        "exec",
        container,
        "psql",
        "-U",
        db_user,
        "-d",
        db_name,
        "-At",
        "-c",
        sql,
    ]
    output = subprocess.check_output(cmd, text=True)
    rows = [json.loads(line) for line in output.splitlines() if line.strip()]
    return [row for row in rows if row.get("group")]


def _with_report_details(row: dict[str, Any], repo_root: Path) -> dict[str, Any]:
    db_summary = row.get("summary_json") if isinstance(row.get("summary_json"), dict) else {}
    report_path = row.get("report_path")
    if not report_path:
        return {
            **row,
            "report_missing": True,
            "phase_timings": _phase_timings_from_summary(db_summary),
            "phase_diagnostics": _phase_diagnostics_from_summary(db_summary),
        }
    path = Path(str(report_path))
    if path.is_absolute() and str(path).startswith("/app/"):
        path = repo_root / str(path)[5:]
    if not path.exists():
        return {
            **row,
            "report_missing": True,
            "phase_timings": _phase_timings_from_summary(db_summary),
            "phase_diagnostics": _phase_diagnostics_from_summary(db_summary),
        }
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {
            **row,
            "report_missing": True,
            "phase_timings": _phase_timings_from_summary(db_summary),
            "phase_diagnostics": _phase_diagnostics_from_summary(db_summary),
        }
    summary = report.get("summary") if isinstance(report, dict) else {}
    if not isinstance(summary, dict):
        summary = {}
    phase_timings = _phase_timings_from_summary(db_summary) or _phase_timings_from_summary(summary)
    phase_diagnostics = _phase_diagnostics_from_summary(db_summary) or _phase_diagnostics_from_summary(
        summary
    )
    determinism = report.get("determinism") if isinstance(report, dict) else {}
    patterns = report.get("patterns") if isinstance(report, dict) else []
    data_manifest = summary.get("data_manifest") if isinstance(summary, dict) else {}
    warnings = summary.get("warnings") if isinstance(summary, dict) else []
    return {
        **row,
        "report_missing": False,
        "warning_count": len(warnings) if isinstance(warnings, list) else 0,
        "content_hash": determinism.get("content_hash") if isinstance(determinism, dict) else None,
        "manifest_hash": data_manifest.get("manifest_hash") if isinstance(data_manifest, dict) else None,
        "pattern_fingerprint": _pattern_fingerprint(patterns),
        "status_counts": summary.get("status_counts") if isinstance(summary, dict) else None,
        "phase_timings": phase_timings,
        "phase_diagnostics": phase_diagnostics,
    }


def _phase_timings_from_summary(summary: Any) -> dict[str, float]:
    if not isinstance(summary, dict):
        return {}
    timings = summary.get("phase_timings")
    if not isinstance(timings, dict):
        return {}
    normalized: dict[str, float] = {}
    for key, value in timings.items():
        try:
            normalized[str(key)] = float(value)
        except (TypeError, ValueError):
            continue
    return normalized


def _phase_diagnostics_from_summary(summary: Any) -> dict[str, Any]:
    if not isinstance(summary, dict):
        return {}
    diagnostics = summary.get("phase_diagnostics")
    return diagnostics if isinstance(diagnostics, dict) else {}


def _is_valid_run(row: dict[str, Any]) -> bool:
    return _int(row.get("windows_sampled")) > 0 and _int(row.get("clusters_evaluated")) > 0


def _invalid_reason(row: dict[str, Any]) -> str:
    if _int(row.get("windows_sampled")) <= 0:
        return "zero_windows"
    if _int(row.get("clusters_evaluated")) <= 0:
        return "zero_clusters"
    return "invalid"


def _print_invalid_runs(
    groups: list[GroupSpec],
    rows: list[dict[str, Any]],
    recent_rows: list[dict[str, Any]],
) -> None:
    grouped_invalid = [row for row in rows if not _is_valid_run(row)]
    grouped_ids = {_int(row.get("id")) for row in rows}
    recent_invalid = [
        row
        for row in recent_rows
        if not _is_valid_run(row) and _int(row.get("id")) not in grouped_ids
    ]
    invalid_rows = sorted(
        [*grouped_invalid, *recent_invalid],
        key=lambda row: _int(row.get("id")),
    )
    if not invalid_rows:
        return

    print()
    print("invalid_runs")
    print("group\tid\tstatus\twindows\tclusters\treason\tinterval\tsymbols")
    for row in invalid_rows:
        run_id = _int(row.get("id"))
        group_label = next((group.label for group in groups if group.contains(run_id)), "recent")
        print(
            "\t".join(
                [
                    group_label,
                    str(run_id),
                    str(row.get("status") or ""),
                    str(_int(row.get("windows_sampled"))),
                    str(_int(row.get("clusters_evaluated"))),
                    _invalid_reason(row),
                    str(row.get("interval") or ""),
                    json.dumps(row.get("symbols"), separators=(",", ":")),
                ]
            )
        )


def _print_phase_summary(groups: list[GroupSpec], rows: list[dict[str, Any]]) -> None:
    phase_names = sorted(
        {
            phase
            for row in rows
            for phase in (row.get("phase_timings") or {})
            if phase != "total_run_s"
        }
    )
    if not phase_names:
        return
    print()
    print("phase_summary")
    print("group\tphase\truns\tavg_s\tmax_s\ttotal_s")
    for group in groups:
        group_rows = [row for row in rows if row["group"] == group.label]
        for phase in phase_names:
            values = [
                (row.get("phase_timings") or {}).get(phase)
                for row in group_rows
                if (row.get("phase_timings") or {}).get(phase) is not None
            ]
            if not values:
                continue
            print(
                "\t".join(
                    [
                        group.label,
                        phase,
                        str(len(values)),
                        _fmt(mean(values)),
                        _fmt(max(values)),
                        _fmt(sum(values)),
                    ]
                )
            )


def _print_clustering_profile_summary(groups: list[GroupSpec], rows: list[dict[str, Any]]) -> None:
    if not any(_clustering_profile(row) for row in rows):
        return

    print()
    print("clustering_profile_buckets")
    print("group\tprofiled_runs\tsamples\tbucket\tsample_pct")
    for group in groups:
        profiles = [_clustering_profile(row) for row in rows if row["group"] == group.label]
        profiles = [profile for profile in profiles if profile]
        if not profiles:
            continue
        bucket_counts: dict[str, int] = {}
        for profile in profiles:
            for bucket in profile.get("buckets") or []:
                if not isinstance(bucket, dict):
                    continue
                name = str(bucket.get("bucket") or "unknown")
                bucket_counts[name] = bucket_counts.get(name, 0) + _int(bucket.get("samples"))
        total = sum(bucket_counts.values())
        for bucket, samples in sorted(bucket_counts.items(), key=lambda item: (-item[1], item[0])):
            print(
                "\t".join(
                    [
                        group.label,
                        str(len(profiles)),
                        str(total),
                        bucket,
                        _fmt((samples / total) * 100.0 if total else 0.0),
                    ]
                )
            )

    print()
    print("clustering_profile_top_frames")
    print("group\tfilename\tfunction\tline\tbucket\tsamples\tsample_pct")
    for group in groups:
        profiles = [_clustering_profile(row) for row in rows if row["group"] == group.label]
        profiles = [profile for profile in profiles if profile]
        if not profiles:
            continue
        total_profile_samples = _profile_sample_total(profiles)
        frame_counts: dict[tuple[str, str, int, str], int] = {}
        for profile in profiles:
            for frame in profile.get("top_frames") or []:
                if not isinstance(frame, dict):
                    continue
                key = (
                    str(frame.get("filename") or ""),
                    str(frame.get("function") or ""),
                    _int(frame.get("line")),
                    str(frame.get("bucket") or "unknown"),
                )
                frame_counts[key] = frame_counts.get(key, 0) + _int(frame.get("samples"))
        total = sum(frame_counts.values())
        for (filename, function, line, bucket), samples in sorted(
            frame_counts.items(), key=lambda item: (-item[1], item[0])
        )[:12]:
            print(
                "\t".join(
                    [
                        group.label,
                        filename,
                        function,
                        str(line),
                        bucket,
                        str(samples),
                        _fmt(
                            (samples / total_profile_samples) * 100.0
                            if total_profile_samples
                            else 0.0
                        ),
                    ]
                )
            )


def _clustering_profile(row: dict[str, Any]) -> dict[str, Any]:
    diagnostics = row.get("phase_diagnostics")
    if not isinstance(diagnostics, dict):
        return {}
    profile = diagnostics.get("clustering_profile")
    return profile if isinstance(profile, dict) else {}


def _profile_sample_total(profiles: list[dict[str, Any]]) -> int:
    total = 0
    for profile in profiles:
        for bucket in profile.get("buckets") or []:
            if isinstance(bucket, dict):
                total += _int(bucket.get("samples"))
    return total


def _pattern_fingerprint(patterns: Any) -> str | None:
    if not isinstance(patterns, list):
        return None
    stable = []
    for pattern in patterns:
        if not isinstance(pattern, dict):
            continue
        stable.append(
            {
                "pattern_key": pattern.get("pattern_key"),
                "side": pattern.get("side"),
                "window_size": pattern.get("window_size"),
                "sample_count": pattern.get("sample_count"),
                "symbol_count": pattern.get("symbol_count"),
                "year_count": pattern.get("year_count"),
                "best_rr": pattern.get("best_rr"),
                "best_expectancy_r": pattern.get("best_expectancy_r"),
                "status": pattern.get("status"),
            }
        )
    payload = json.dumps(stable, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _fmt(value: float | None) -> str:
    if value is None:
        return "NA"
    return f"{value:.3f}"


def _int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
