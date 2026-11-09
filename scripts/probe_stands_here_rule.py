"""Which rule gives "stands here" = 145 / 27 / 176 / 279?

The dashboard document (§3.1) says "Stands here" counts projects that
reached the stage and have not reached the next one, and gives 145, 27,
176, 279. A probe written that way gives 681, 534, 510, 334 — the same as
"ever reached", because on this payload almost every project that reached a
stage also reached the next.

The document's numbers are what a dashboard must show, so the rule that
produces them is named here rather than guessed at.

The candidates:

  A  reached the stage, and the NEXT stage's milestone is absent
  B  reached the stage, and the next stage's milestone is absent, where the
     next stage is read from the project's CURRENT NODE's stage order
  C  reached the stage, and the project has no construction milestone at all
     (the "ever reached" set minus everything that moved on)
  D  reached the stage, and the project's current node's stage IS this stage

    python scripts/probe_stands_here_rule.py [REVS]

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
    ("核定", ("核定日期", "權變核定日期", "概要核准日期"), "建照核發日期"),
    ("建照", ("建照核發日期",), "開工日期"),
    ("開工", ("開工日期",), "使照核發日期"),
    ("使照", ("使照核發日期",), "成果報備日期"),
)

# the stage order the current node's `stage` word implies
STAGE_RANK = {"事業概要": 0, "擬訂": 1, "變更": 1}


def load_document(text: str) -> dict:
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


def earliest(ms: dict[str, str], keys: tuple[str, ...]) -> date | None:
    dates = [normalise(ms[k]) for k in keys if ms.get(k)]
    dates = [d for d in dates if d is not None]
    return min(dates) if dates else None


def measure(doc: dict, gazette: date | None) -> dict[str, dict[str, int]]:
    out: dict[str, dict[str, int]] = {}
    for name, own, nxt in STAGES:
        ever = a = b = c = d = 0
        waits_a: list[int] = []
        for p in doc["projects"]:
            ms = merged(p)
            own_date = earliest(ms, own)
            if own_date is None:
                continue
            ever += 1
            has_next = earliest(ms, nxt) is not None
            if not has_next:
                a += 1
                if gazette:
                    waits_a.append((gazette - own_date).days)
            nodes = p.get("nodes") or []
            cur = next((n for n in nodes if n.get("is_current")), nodes[0] if nodes else {})
            cur_stage = cur.get("stage") or ""
            # B: the current node's own stage is not a construction stage, and
            # the project has no construction milestone
            construction = any(ms.get(k) for k in
                                ("建照核發日期", "開工日期", "使照核發日期", "成果報備日期"))
            if not construction:
                b += 1
            if STAGE_RANK.get(cur_stage, 2) >= 2:
                c += 1
            # D: the current node's stage word names this stage
            stage_of = {"核定": ("核定", "擬訂", "變更"), "建照": ("建照",),
                        "開工": ("開工",), "使照": ("使照",)}
            if cur_stage in stage_of.get(name, ()):
                d += 1
        out[name] = {"ever": ever, "A": a, "B": b, "C": c, "D": d,
                     "medA": int(statistics.median(waits_a)) if waits_a else 0}
    return out


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
        gazette = normalise(doc.get("published_date") or "")
        res = measure(doc, gazette)
        print()
        print("%s  (projects %d, gazette %s)" % (rev, doc["counts"]["projects"], doc.get("published_date")))
        print("   %-6s %-8s %-8s %-8s %-8s %-8s %-8s" % ("stage", "ever", "A", "medA", "B", "C", "D"))
        for name in ("核定", "建照", "開工", "使照"):
            r = res[name]
            print("   %-6s %-8d %-8d %-8d %-8d %-8d %-8d"
                  % (name, r["ever"], r["A"], r["medA"], r["B"], r["C"], r["D"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
