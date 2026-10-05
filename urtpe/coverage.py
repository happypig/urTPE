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
    崇仁新村 merge legitimately removed a duplicate project.

    A total re-key is reported as its own outcome. Regressions alone cannot see one:
    when every identity changes, ``set(before) & set(after)`` is empty, so
    ``regressions`` is ``{}`` and a guard keyed on it passes while every cache is
    orphaned. That is the shape of the 2026-08-24 incident, and the orphaned set moved
    27 → 2 during the gazette change without the guard noticing either step.
    """
    regressions: dict[str, list[str]] = {}
    for pid in set(before) & set(after):
        dropped = [f for f in before[pid] if before[pid][f] and not after[pid].get(f)]
        if dropped:
            regressions[pid] = dropped
    lost = sorted(set(before) - set(after))
    gained = sorted(set(after) - set(before))
    # Only zero overlap counts. A large ordinary loss is churn, not a re-key, and
    # drawing a threshold would be a judgement about acceptable change rate.
    total_rekey = bool(before) and bool(after) and not (set(before) & set(after))
    return {
        "regressions": regressions,
        "lost": lost,
        "gained": gained,
        "total_rekey": total_rekey,
        "before_count": len(before),
        "after_count": len(after),
    }


class CoverageRegression(RuntimeError):
    """A destructive cache job decreased coverage."""


@contextmanager
def coverage_guard(root, project_ids, strict: bool = True, alert_path: Path | None = None):
    """Wrap a cache-writing job. Snapshots before/after, records the diff in
    the yielded dict, and (strict) raises CoverageRegression when any coverage
    flag regresses — so destructive jobs stop before emitting a regressed viewer.

    Also raises on a total re-key. Without that, every identity changing empties the
    intersection the regression scan works over, so a wholesale re-key reports success
    while every cache is orphaned.
    """
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
        if d["regressions"] or d["total_rekey"]:
            ap = Path(alert_path) if alert_path else Path(root) / "coverage_alerts.jsonl"
            ap.parent.mkdir(parents=True, exist_ok=True)
            with open(ap, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(
                    {"timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
                     "regressions": d["regressions"],
                     "total_rekey": d["total_rekey"],
                     "before_count": d["before_count"],
                     "after_count": d["after_count"]},
                    ensure_ascii=False,
                ) + "\n")
            if strict:
                if d["total_rekey"]:
                    raise CoverageRegression(
                        f"total re-key: no cached identity survives "
                        f"({d['before_count']} before, {d['after_count']} after, "
                        f"{len(d['lost'])} orphaned). Every cache directory is "
                        f"unreachable by name; this is the shape of the 2026-08-24 "
                        f"incident and is not a set of ordinary regressions.")
                raise CoverageRegression(
                    f"coverage regression detected: {d['regressions']}")
