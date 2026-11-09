"""Did the funnel's "ever reached" counts move with the payload?

The dashboard document (§3.1) gives 674, 529, 505, 330 for 核定, 建照, 開工
and 使照. The current payload gives 681, 534, 510, 334 under every rule this
probe tries.

Either the figures moved when the corpus did, or the document's rule is not
the one being measured here. This walks the payload history and reports both
counts at each revision, so the question is answered by the payloads
themselves.

    python scripts/probe_funnel_over_history.py [--names REVS]

Reads committed blobs. Writes nothing, reaches no network.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
PATH_IN_REPO = "viewer/projects.data.js"

STAGES = (
    ("核定", ("核定日期", "權變核定日期", "概要核准日期"), "建照核發日期"),
    ("建照", ("建照核發日期",), "開工日期"),
    ("開工", ("開工日期",), "使照核發日期"),
    ("使照", ("使照核發日期",), "成果報備日期"),
)


def load_document(text: str) -> dict | None:
    body = re.sub(r"^window\.PROJECTS\s*=\s*", "", text.strip())
    body = re.sub(r";\s*$", "", body)
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        return None


def merged(project: dict) -> dict[str, str]:
    links = project.get("links") or {}
    out: dict[str, str] = {}
    for key in ("milestones_taipei", "milestones_national", "milestones_taipei_case"):
        for k, v in (links.get(key) or {}).items():
            if v and k not in out:
                out[k] = v
    return out


def counts(doc: dict) -> dict[str, int]:
    out: dict[str, int] = {}
    for name, own, _nxt in STAGES:
        n = 0
        for p in doc["projects"]:
            ms = merged(p)
            if any(ms.get(k) for k in own):
                n += 1
        out[name] = n
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--limit", type=int, default=20)
    ap.add_argument("--names", default="")
    args = ap.parse_args()

    revs = subprocess.run(
        ["git", "log", "--format=%h", "-n", str(args.limit), "--", PATH_IN_REPO],
        cwd=ROOT, capture_output=True, text=True, check=True,
    ).stdout.split()

    print("%-9s %-40s %s" % ("commit", "subject", "核定 建照 開工 使照"))
    print("-" * 76)
    for rev in revs:
        out = subprocess.run(
            ["git", "show", f"{rev}:{PATH_IN_REPO}"],
            cwd=ROOT, capture_output=True,
        )
        if out.returncode != 0:
            continue
        doc = load_document(out.stdout.decode("utf-8", errors="replace"))
        if doc is None:
            continue
        subject = subprocess.run(
            ["git", "log", "-1", "--format=%s", rev],
            cwd=ROOT, capture_output=True, text=True, check=True,
        ).stdout.strip()
        c = counts(doc)
        print("%-9s %-40s %4d %4d %4d %4d"
              % (rev, subject[:40], c["核定"], c["建照"], c["開工"], c["使照"]))

    for rev in (args.names or "").split():
        out = subprocess.run(
            ["git", "show", f"{rev}:{PATH_IN_REPO}"],
            cwd=ROOT, capture_output=True,
        )
        doc = load_document(out.stdout.decode("utf-8", errors="replace"))
        if doc is None:
            continue
        print()
        print("%s — projects %d" % (rev, doc["counts"]["projects"]))
        print("   ", counts(doc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
