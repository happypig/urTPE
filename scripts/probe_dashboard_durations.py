"""The dashboard's §3 figures, measured on the current payload.

Reads the payload, computes the funnel and the stage-to-stage durations, and
reports them at the current revision and at the revisions the document
cites. The rule is the one Appendix A states.

**The funnel's "stands here" counts per bucket.** "Ever reached" means the
milestone exists in ANY of the three buckets; "reached the next" means it
exists in ANY of them. A project that reached a stage in one bucket and the
next stage in a DIFFERENT bucket counts as having moved on. Merging the
buckets first and then comparing loses that distinction, and the counts come
out equal to "ever reached" — which is how an earlier version of this probe
reported 681 / 534 / 510 / 334 instead of 147 / 27 / 177 / 283.

    python scripts/probe_dashboard_durations.py

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

STAGES = (
    ("核定", APPROVE, ("建照核發日期",)),
    ("建照", ("建照核發日期",), ("開工日期",)),
    ("開工", ("開工日期",), ("使照核發日期",)),
    ("使照", ("使照核發日期",), ("成果報備日期",)),
)

TRANSITIONS = (
    ("申請 → 核定", APPLY, APPROVE),
    ("核定 → 建照", APPROVE, ("建照核發日期",)),
    ("建照 → 開工", ("建照核發日期",), ("開工日期",)),
    ("開工 → 使照", ("開工日期",), ("使照核發日期",)),
    ("核定 → 使照", APPROVE, ("使照核發日期",)),
    ("使照 → 成果報備", ("使照核發日期",), ("成果報備日期",)),
    ("申請 → 成果報備", APPLY, ("成果報備日期",)),
)

REVS = ("4b67a8f", "eafb9dd", "3e0c570")


def load_document(text: str) -> dict:
    body = re.sub(r"^window\.PROJECTS\s*=\s*", "", text.strip())
    body = re.sub(r";\s*$", "", body)
    return json.loads(body)


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


def has(project: dict, keys: tuple[str, ...]) -> bool:
    """The milestone exists, with a parsable date, in ANY bucket."""
    for bucket in buckets(project).values():
        for k in keys:
            if bucket.get(k) and normalise(bucket[k]):
                return True
    return False


def earliest(ms: dict[str, str], keys: tuple[str, ...]) -> date | None:
    """The EARLIEST date over the keys that carry one.

    Taking the first key that happens to be present is not the same thing: the
    key order is not the date order. 申請計畫日期 precedes 申請核定日期, so a
    first-present rule picks the later date and shortens every span.
    """
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


def measure(doc: dict) -> tuple[list[tuple], list[tuple]]:
    projects = doc["projects"]
    gazette = normalise(doc.get("published_date") or "")

    funnel: list[tuple] = []
    for name, own, nxt in STAGES:
        ever = [p for p in projects if has(p, own)]
        stands = [p for p in ever if not has(p, nxt)]
        waits = []
        for p in stands:
            own_date = earliest(merged(p), own)
            if own_date and gazette:
                waits.append((gazette - own_date).days)
        med = int(statistics.median(waits)) if waits else 0
        funnel.append((name, len(ever), len(stands), med))

    # 成果報備 is a historical cohort, not a funnel step: it has no next stage
    ever_wu = [p for p in projects if has(p, ("成果報備日期",))]
    waits_wu = []
    for p in ever_wu:
        d = earliest(merged(p), ("成果報備日期",))
        if d and gazette:
            waits_wu.append((gazette - d).days)
    funnel.append(("成果報備", len(ever_wu), len(ever_wu),
                   int(statistics.median(waits_wu)) if waits_wu else 0))

    durations: list[tuple] = []
    for label, frm, to in TRANSITIONS:
        spans: list[int] = []
        for p in projects:
            ms = merged(p)
            a = earliest(ms, frm)
            b = earliest(ms, to)
            if a is None or b is None:
                continue
            spans.append((b - a).days)
        durations.append((label, len(spans),
                          int(statistics.median(spans)) if spans else 0,
                          p75(spans), max(spans) if spans else 0))
    return funnel, durations


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
                print("%s: cannot read" % rev)
                continue
            text = out.stdout.decode("utf-8")
        doc = load_document(text)
        funnel, durations = measure(doc)
        print()
        print("=" * 74)
        print("%s  (projects %d, gazette %s)"
              % (rev, doc["counts"]["projects"], doc.get("published_date")))
        print("  %-8s %-8s %-8s %-10s" % ("stage", "ever", "stands", "median"))
        for name, ever, stands, med in funnel:
            print("  %-8s %-8d %-8d %-10s" % (name, ever, stands, format(med, ",")))
        print("  %-16s %-6s %-8s %-8s %-8s" % ("transition", "n", "median", "p75", "max"))
        for label, n, med, q, mx in durations:
            print("  %-16s %-6d %-8s %-8s %-8s"
                  % (label, n, format(med, ","), format(q, ","), format(mx, ",")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
