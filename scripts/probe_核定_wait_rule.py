"""Which date does the 核定 row's "median days waiting" come from?

The dashboard document (§3.1) gives 核定 a median wait of 874 days over the
145 projects that reached 核定 and have not reached 建照. Every other row of
that table reproduces from the merged milestone dictionary — the 使照 row's
2,014, the 開工 row's 1,120, the 建照 row's 337 — so the rule is right and
this one row uses a different date.

The candidates:

  earliest  the earliest over 核定日期 / 權變核定日期 / 概要核准日期
  latest    the latest over the same three
  核定 only earliest over 核定日期 / 權變核定日期, dropping 概要核准日期
  核定 only latest

    python scripts/probe_核定_wait_rule.py [REVS]

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

OWN = ("核定日期", "權變核定日期", "概要核准日期")
OWN_NO_WU = ("核定日期", "權變核定日期")
NEXT = ("建照核發日期",)


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
        stands = [p for p in doc["projects"]
                  if has(p, OWN) and not has(p, NEXT)]

        variants = {
            "earliest over all three": (OWN, min),
            "latest over all three": (OWN, max),
            "earliest, 核定 only": (OWN_NO_WU, min),
            "latest, 核定 only": (OWN_NO_WU, max),
        }
        print()
        print("%s  (projects %d, stands %d)" % (rev, len(doc["projects"]), len(stands)))
        for label, (keys, pick) in variants.items():
            waits = []
            for p in stands:
                ds = dates_over(merged(p), keys)
                if not ds or not gazette:
                    continue
                waits.append((gazette - pick(ds)).days)
            if waits:
                print("   %-26s n=%-4d median %-8s max %s"
                      % (label, len(waits), format(int(statistics.median(waits)), ","),
                         format(max(waits), ",")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
