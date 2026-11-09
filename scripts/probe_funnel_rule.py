"""Which funnel rule gives 674 / 529 / 505 / 330, and which gives 681 / 534 / 510 / 334?

The dashboard document (§3.1) gives "ever reached" counts of 674, 529, 505,
330. A probe written from Appendix A's recipe gives 681, 534, 510, 334 on the
current payload. The two rules differ, and the document's figures are what a
dashboard must show — so the rule that produces them is named here.

The candidates:

  A  the milestone exists in the project's own merged buckets
  B  the milestone exists, and the NEXT stage's milestone does not
  C  the project's CURRENT NODE carries the stage

"Ever reached" should count a project that passed a stage even if it has
since passed the next one, so a rule that requires the next milestone to be
absent would undercount by construction.

    python scripts/probe_funnel_rule.py

Reads the payload. Writes nothing, reaches no network.
"""

from __future__ import annotations

import json
import pathlib
import re
import statistics
import sys
from datetime import date

ROOT = pathlib.Path(__file__).resolve().parents[1]
PAYLOAD = ROOT / "viewer" / "projects.data.js"

STAGES = (
    ("核定", ("核定日期", "權變核定日期", "概要核准日期"), "建照核發日期"),
    ("建照", ("建照核發日期",), "開工日期"),
    ("開工", ("開工日期",), "使照核發日期"),
    ("使照", ("使照核發日期",), "成果報備日期"),
)


def load_payload() -> dict:
    text = PAYLOAD.read_text(encoding="utf-8")
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


def merged(project: dict) -> dict[str, str]:
    links = project.get("links") or {}
    out: dict[str, str] = {}
    for key in ("milestones_taipei", "milestones_national", "milestones_taipei_case"):
        for k, v in (links.get(key) or {}).items():
            if v and k not in out:
                out[k] = v
    return out


def main() -> int:
    doc = load_payload()
    projects = doc["projects"]
    gazette = normalise(doc.get("published_date") or "")

    print("%-6s %-10s %-10s %-10s %-10s" % ("stage", "A merged", "B merged", "C node", "stands"))
    print("-" * 56)
    for name, own, nxt in STAGES:
        a = b = c = 0
        stands: list[int] = []
        for p in projects:
            ms = merged(p)
            has_own = any(ms.get(k) for k in own)
            has_next = any(ms.get(k) for k in nxt)
            if has_own:
                a += 1
            if has_own and not has_next:
                b += 1
                own_date = next((normalise(ms[k]) for k in own if ms.get(k)), None)
                if own_date and gazette:
                    stands.append((gazette - own_date).days)
            nodes = p.get("nodes") or []
            cur = next((n for n in nodes if n.get("is_current")), nodes[0] if nodes else {})
            if any(cur.get(k) for k in own):
                c += 1
        med = int(statistics.median(stands)) if stands else 0
        print("%-6s %-10d %-10d %-10d %-10d  (median %s)"
              % (name, a, b, c, len(stands), format(med, ",")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
