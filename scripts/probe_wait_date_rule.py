"""Which date does each funnel row's "median days waiting" use?

The 核定 row's median reproduces with the LATEST of its approval dates, and
not with the earliest. Appendix A says "the earliest date over the stage's
fields", so the rule may differ per row, and a dashboard built on the wrong
one would be wrong.

This measures every row under both readings and reports which reproduces the
document's figure.

    python scripts/probe_wait_date_rule.py [REVS]

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

STAGES = (
    ("核定", ("核定日期", "權變核定日期", "概要核准日期"), ("建照核發日期",)),
    ("建照", ("建照核發日期",), ("開工日期",)),
    ("開工", ("開工日期",), ("使照核發日期",)),
    ("使照", ("使照核發日期",), ("成果報備日期",)),
    ("成果報備", ("成果報備日期",), ()),
)

# the document's figures, at 4b67a8f
DOCUMENT = {
    "核定": (145, 874),
    "建照": (27, 337),
    "開工": (176, 1120),
    "使照": (279, 2014),
    "成果報備": (51, 5224),
}


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
    if not keys:
        return False
    for bucket in buckets(project).values():
        for k in keys:
            if bucket.get(k) and normalise(bucket[k]):
                return True
    return False


def dates_over(ms: dict[str, str], keys: tuple[str, ...]) -> list[date]:
    return [d for d in (normalise(ms[k]) for k in keys if ms.get(k)) if d is not None]


def main() -> int:
    revs = sys.argv[1:] or ["4b67a8f", "eafb9dd", "3e0c570"]
    for rev in revs:
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
        gazette = normalise(doc.get("published_date") or "")
        print()
        print("%s  (projects %d)" % (rev, len(doc["projects"])))
        print("   %-8s %-6s %-12s %-12s %s" % ("stage", "n", "earliest", "latest", "document"))
        for name, own, nxt in STAGES:
            stands = [p for p in doc["projects"]
                      if has(p, own) and (not nxt or not has(p, nxt))]
            row = {}
            for label, pick in (("earliest", min), ("latest", max)):
                waits = []
                for p in stands:
                    ds = dates_over(merged(p), own)
                    if ds and gazette:
                        waits.append((gazette - pick(ds)).days)
                row[label] = int(statistics.median(waits)) if waits else 0
            want = DOCUMENT.get(name)
            doc_txt = ("n=%d median=%d" % want) if want else "-"
            mark = ""
            if want:
                if row["earliest"] == want[1]:
                    mark = "  <- earliest"
                elif row["latest"] == want[1]:
                    mark = "  <- latest"
            print("   %-8s %-6d %-12s %-12s %s%s"
                  % (name, len(stands), format(row["earliest"], ","),
                     format(row["latest"], ","), doc_txt, mark))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
