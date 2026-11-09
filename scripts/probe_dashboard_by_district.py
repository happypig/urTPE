"""The dashboard's §3.3 and §3.4 tables, measured on the current payload.

§3.3 splits 申請 → 核定 by the project's track; §3.4 splits it by district
and counts three more conditions. Both are measured here and printed at the
current payload and at the revision the document cites, so a figure that
moved can be told from a rule that was always this.

    python scripts/probe_dashboard_by_district.py

Reads committed payloads. Writes nothing, reaches no network.
"""

from __future__ import annotations

import json
import pathlib
import re
import statistics
import subprocess
import sys
from datetime import date

ROOT = pathlib.Path(__file__).resolve().parents[1]
PATH_IN_REPO = "viewer/projects.data.js"

APPLY = ("申請核定日期", "權變申請核定日期", "申請計畫日期", "申請權變日期", "申請概要日期")
APPROVE = ("核定日期", "權變核定日期", "概要核准日期")
PERMIT = ("建照核發日期",)
USE = ("使照核發日期",)
DONE = ("成果報備日期",)

REVS = ("4b67a8f", "eafb9dd", "3e0c570")


def load_document(text: str) -> dict:
    body = re.sub(r"^window\.PROJECTS\s*=\s*", "", text.strip())
    body = re.sub(r";\s*$", "", body)
    return json.loads(body)


def buckets(project: dict) -> dict[str, dict[str, str]]:
    links = project.get("links") or {}
    return {
        "taipei": links.get("milestones_taipei") or {},
        "national": links.get("milestones_national") or {},
        "case": links.get("milestones_taipei_case") or {},
    }


def merged(project: dict) -> dict[str, str]:
    out: dict[str, str] = {}
    for bucket in buckets(project).values():
        for k, v in bucket.items():
            if v and k not in out:
                out[k] = v
    return out


def normalise(value: str) -> date | None:
    text = (value or "").strip()
    if not text:
        return None
    if "T" in text:
        text = text.split("T")[0]
    text = text.replace("/", "-")
    m = re.fullmatch(r"(\d{2,3})-(\d{1,2})-(\d{1,2})", text)
    if m:
        year = int(m.group(1))
        if year < 1911:
            year += 1911
        try:
            return date(year, int(m.group(2)), int(m.group(3)))
        except ValueError:
            return None
    m = re.fullmatch(r"(\d{4})-(\d{1,2})-(\d{1,2})", text)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            return None
    return None


def has(project: dict, keys: tuple[str, ...]) -> bool:
    for bucket in buckets(project).values():
        for k in keys:
            if bucket.get(k) and normalise(bucket[k]):
                return True
    return False


def earliest(ms: dict[str, str], keys: tuple[str, ...]) -> date | None:
    dates = [normalise(ms[k]) for k in keys if ms.get(k)]
    dates = [d for d in dates if d is not None]
    return min(dates) if dates else None


def p75(values: list[int]) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    pos = 0.75 * (len(ordered) - 1)
    low = int(pos)
    high = min(low + 1, len(ordered) - 1)
    frac = pos - low
    return int(round(ordered[low] + (ordered[high] - ordered[low]) * frac))


def track_of(project: dict) -> str:
    nodes = project.get("nodes") or []
    cur = next((n for n in nodes if n.get("is_current")), nodes[0] if nodes else {})
    return cur.get("track") or ""


def apply_to_approve(project: dict) -> int | None:
    ms = merged(project)
    a = earliest(ms, APPLY)
    b = earliest(ms, APPROVE)
    if a is None or b is None:
        return None
    return (b - a).days


def main() -> int:
    for rev in ("HEAD",) + REVS:
        if rev == "HEAD":
            text = (ROOT / PATH_IN_REPO).read_text(encoding="utf-8")
        else:
            out = subprocess.run(
                ["git", "show", f"{rev}:{PATH_IN_REPO}"],
                cwd=ROOT, capture_output=True,
            )
            if out.returncode != 0:
                continue
            text = out.stdout.decode("utf-8")
        doc = load_document(text)
        projects = doc["projects"]

        print()
        print("=" * 92)
        print("%s  (projects %d)" % (rev, len(projects)))

        print()
        print("by track:")
        print("   %-22s %-6s %-10s %-10s %-10s" % ("track", "n", "median", "p75", "max"))
        tracks: dict[str, list[int]] = {}
        for p in projects:
            span = apply_to_approve(p)
            if span is None:
                continue
            tracks.setdefault(track_of(p), []).append(span)
        for name, spans in sorted(tracks.items(), key=lambda kv: -len(kv[1])):
            print("   %-22s %-6d %-10s %-10s %-10s"
                  % (name, len(spans), format(int(statistics.median(spans)), ","),
                     format(p75(spans), ","), format(max(spans), ",")))

        print()
        print("by district:")
        print("   %-8s %-8s %-12s %-8s %-8s %-16s %-9s %-9s"
              % ("district", "projects", "n apply->ap", "median", "p75",
                 "use-no-done", "no permit", "not appr"))
        rows = []
        for district in sorted({p.get("district", "") for p in projects}):
            sub = [p for p in projects if p.get("district", "") == district]
            spans = [s for s in (apply_to_approve(p) for p in sub) if s is not None]
            use_no_done = sum(1 for p in sub if has(p, USE) and not has(p, DONE))
            no_permit = sum(1 for p in sub if not has(p, PERMIT))
            not_appr = sum(1 for p in sub if not has(p, APPROVE))
            rows.append((district, len(sub), len(spans),
                         int(statistics.median(spans)) if spans else 0,
                         p75(spans), use_no_done, no_permit, not_appr))
        for r in rows:
            print("   %-8s %-8d %-12d %-8s %-8s %-16d %-9d %-9d"
                  % (r[0], r[1], r[2], format(r[3], ","), format(r[4], ","),
                     r[5], r[6], r[7]))
        total = (len(projects),
                 sum(r[2] for r in rows), sum(r[5] for r in rows),
                 sum(r[6] for r in rows), sum(r[7] for r in rows))
        print("   %-8s %-8d %-12d %-8s %-8s %-16d %-9d %-9d"
              % ("Total", total[0], total[1], "", "", total[2], total[3], total[4]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
