"""Coverage regression guard — facts §12 #1, §18 rule 3.

Snapshots per-project coverage flags (resolved / twur / national / 使用核發)
from the per-project caches, diffs before/after a destructive job, and raises
`CoverageRegression` when any flag drops on a shared project id — aborting the
job BEFORE a regressed viewer can be emitted. Alert trail: JSON Lines in
`data/.link_cache/coverage_alerts.jsonl` (one line per regression event).
"""
from __future__ import annotations

import json
import re
import time
from contextlib import contextmanager
from pathlib import Path

FLAGS = ("resolved", "twur", "national", "ulic")


def _flags_from_cache(result_file: Path) -> dict[str, bool] | None:
    try:
        d = json.loads(result_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    nm = d.get("national_milestones") or {}
    return {
        "resolved": d.get("status") == "resolved",
        "twur": bool(d.get("twur_url")),
        "national": bool(nm),
        "ulic": any(k == "使用核發日期" for k in nm),
    }


def snapshot(root: Path, project_ids: list[str]) -> dict[str, dict[str, bool]]:
    """Read each project's flags from its sanitized-id cache (links.py:974)."""
    root = Path(root)
    out: dict[str, dict[str, bool]] = {}
    for pid in project_ids:
        rf = root / re.sub(r"[^\w\-]", "_", pid) / "result.json"
        flags = _flags_from_cache(rf)
        if flags is not None:
            out[pid] = flags
    return out


def diff(before: dict, after: dict) -> dict:
    """Regressions = a flag True→False on a pid present in both snapshots.
    Lost/gained pids (family merges) are reported informationally — the
    崇仁新村 merge legitimately removed a duplicate project."""
    regressions: dict[str, list[str]] = {}
    for pid in set(before) & set(after):
        dropped = [f for f in before[pid] if before[pid][f] and not after[pid].get(f)]
        if dropped:
            regressions[pid] = dropped
    return {
        "regressions": regressions,
        "lost": sorted(set(before) - set(after)),
        "gained": sorted(set(after) - set(before)),
    }


class CoverageRegression(RuntimeError):
    """A destructive cache job decreased coverage."""


@contextmanager
def coverage_guard(root, project_ids, strict: bool = True, alert_path: Path | None = None):
    """Wrap a cache-writing job. Snapshots before/after, records the diff in
    the yielded dict, and (strict) raises CoverageRegression when any coverage
    flag regresses — so destructive jobs stop before emitting a regressed viewer."""
    result: dict = {}
    before = snapshot(root, project_ids)
    try:
        yield result
    finally:
        after = snapshot(root, project_ids)
        d = diff(before, after)
        result["diff"] = d
        result["before"] = before
        result["after"] = after
        if d["regressions"]:
            ap = Path(alert_path) if alert_path else Path(root) / "coverage_alerts.jsonl"
            ap.parent.mkdir(parents=True, exist_ok=True)
            with open(ap, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(
                    {"timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"), "regressions": d["regressions"]},
                    ensure_ascii=False,
                ) + "\n")
            if strict:
                raise CoverageRegression(f"coverage regression detected: {d['regressions']}")
