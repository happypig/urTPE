"""How many projects have 核定 but not 建照, and so on?

A direct count, with no abstraction between the payload and the answer. The
dashboard document (§3.1) gives "stands here" as 145 / 27 / 176 / 279, and
its rule reads "the stage milestone exists and the next stage's milestone
does not". If the sets nest, that difference is the answer, so it is counted
directly.

    python scripts/probe_stands_here_direct.py [REVS]

Reads committed payloads. Writes nothing, reaches no network.
"""

from __future__ import annotations

import json
import pathlib
import re
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
)


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
    b = buckets(project)
    for name, bucket in b.items():
        for k in keys:
            if bucket.get(k) and normalise(bucket[k]):
                return True
    return False


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
                print("%s: cannot read" % rev)
                continue
            text = out.stdout.decode("utf-8")
        doc = load_document(text)
        projects = doc["projects"]
        print()
        print("%s  (projects %d)" % (rev, len(projects)))
        print("   %-6s %-8s %-8s %-10s" % ("stage", "ever", "next", "ever-not-next"))
        for name, own, nxt in STAGES:
            ever = [p for p in projects if has(p, own)]
            with_next = [p for p in ever if has(p, nxt)]
            without = [p for p in ever if not has(p, nxt)]
            print("   %-6s %-8d %-8d %-10d" % (name, len(ever), len(with_next), len(without)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
