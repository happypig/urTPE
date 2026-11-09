"""The dashboard's §3.5, §3.6 and §3.7 figures, measured on the current payload.

  S3.5  the 成果報備 year histogram, and the 631 that would read as stalled
  S3.6  how 使用核發日期 relates to 使照核發日期
  S3.7  the ROC year 291 record, and what the current node carries

    python scripts/probe_dashboard_national_dates.py

Reads the payload. Writes nothing, reaches no network.
"""

from __future__ import annotations

import json
import pathlib
import re
import sys
from collections import Counter

ROOT = pathlib.Path(__file__).resolve().parents[1]
PAYLOAD = ROOT / "viewer" / "projects.data.js"


def load_payload() -> dict:
    text = PAYLOAD.read_text(encoding="utf-8")
    body = re.sub(r"^window\.PROJECTS\s*=\s*", "", text.strip())
    body = re.sub(r";\s*$", "", body)
    return json.loads(body)


def merged(project: dict) -> dict[str, str]:
    links = project.get("links") or {}
    out: dict[str, str] = {}
    for key in ("milestones_taipei", "milestones_national", "milestones_taipei_case"):
        for k, v in (links.get(key) or {}).items():
            if v and k not in out:
                out[k] = v
    return out


def normalise(value: str) -> str:
    """A date to ISO, so the ROC and Gregorian forms can be compared.

    The national portal writes ROC (`112.12.20`); the city writes Gregorian
    (`2023/12/20`). Comparing the raw strings says they differ when they
    agree, so the comparison must normalise first.
    """
    text = str(value or "").strip()
    if not text:
        return ""
    if "T" in text:
        text = text.split("T")[0]
    text = text.replace("/", "-").replace(".", "-")
    parts = text.split("-")
    if len(parts) != 3:
        return text
    try:
        year, month, day = (int(p) for p in parts)
    except ValueError:
        return text
    if year < 1911:
        year += 1911
    return "%04d-%02d-%02d" % (year, month, day)


def main() -> int:
    doc = load_payload()
    projects = doc["projects"]

    # S3.5 成果報備
    years: Counter = Counter()
    done = []
    for p in projects:
        v = merged(p).get("成果報備日期")
        if not v:
            continue
        done.append(p)
        m = re.match(r"(\d{4})", str(v))
        if m:
            years[int(m.group(1))] += 1
    print("projects with 成果報備日期: %d" % len(done))
    print("  by year:", dict(sorted(years.items())))
    dates = sorted(str(merged(p).get("成果報備日期")) for p in done)
    print("  earliest %s   latest %s" % (dates[0], dates[-1]))
    # a funnel ending at 成果報備 would show these as waiting
    waiting = sum(1 for p in projects
                  if merged(p).get("使照核發日期") and not merged(p).get("成果報備日期"))
    print("  projects with 使照 but no 成果報備 (the false 'stalled' count): %d" % waiting)

    # S3.6 使用核發日期 vs 使照核發日期
    both_same = both_diff = only_use = only_use_city = 0
    use_dates = []
    for p in projects:
        links = p.get("links") or {}
        nat = (links.get("milestones_national") or {}).get("使用核發日期") or ""
        city = (links.get("milestones_taipei") or {}).get("使照核發日期") or ""
        if nat:
            use_dates.append((p["project_id"], nat))
        if nat and city:
            if normalise(nat) == normalise(city):
                both_same += 1
            else:
                both_diff += 1
        elif nat:
            only_use += 1
        elif city:
            only_use_city += 1
    print()
    print("使用核發日期: %d projects" % len(use_dates))
    print("  both present, same date    : %d" % both_same)
    print("  both present, different date: %d" % both_diff)
    print("  使用核發日期 only           : %d" % only_use)
    print("  使照核發日期 only           : %d" % only_use_city)

    # S3.7 the ROC 291 record
    print()
    roc = [(pid, v) for pid, v in use_dates if str(v).startswith("291")]
    print("ROC 291 records: %d" % len(roc))
    for pid, v in roc:
        p = next(x for x in projects if x["project_id"] == pid)
        print("   %s" % pid)
        print("      使用核發日期 = %s" % v)
        print("      使照核發日期 = %s" % merged(p).get("使照核發日期"))

    # what the current node carries. The node's milestones ride under its
    # `links`, not as top-level fields, so both places are read.
    node_counts: Counter = Counter()
    for p in projects:
        nodes = p.get("nodes") or []
        cur = next((n for n in nodes if n.get("is_current")), nodes[0] if nodes else {})
        links = cur.get("links") or {}
        for label in ("核定日期", "申請計畫日期", "審議通過日期", "建照核發日期",
                      "開工日期", "使照核發日期", "成果報備日期"):
            if cur.get(label):
                node_counts[label] += 1
                continue
            for bucket in ("milestones_taipei", "milestones_national",
                           "milestones_taipei_case", "case_milestones"):
                ms = links.get(bucket) or {}
                if isinstance(ms, dict) and any(
                        isinstance(v, dict) and v.get(label) for v in ms.values()):
                    node_counts[label] += 1
                    break
                if ms.get(label):
                    node_counts[label] += 1
                    break
    print()
    print("the current node carries:")
    for label in ("核定日期", "申請計畫日期", "審議通過日期", "建照核發日期",
                  "開工日期", "使照核發日期", "成果報備日期"):
        print("   %-16s %d" % (label, node_counts.get(label, 0)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
