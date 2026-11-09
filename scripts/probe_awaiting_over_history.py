"""How many projects awaited approval at each payload revision?

The dashboard document (§4.1) says 97, and §14 calls that figure stable
across four revisions. The current payload gives 99 under the pipeline's own
rule (`cached_cases_awaiting_approval`).

The payload carries what the rule reads — `case_milestones`, `case_schedules`,
`case_headers`, `superseded_by` — so each revision can be measured from its
own bytes, with no cache and no network. That makes the figure a property of
the payload rather than of the cache layer as it stands today.

    python scripts/probe_awaiting_over_history.py [--limit N] [--names REVS]

Reads committed blobs. Writes nothing, reaches no network.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import subprocess
import sys
from collections import Counter

ROOT = pathlib.Path(__file__).resolve().parents[1]
PATH_IN_REPO = "viewer/projects.data.js"

sys.path.insert(0, str(ROOT))
from urtpe.links import (  # noqa: E402
    _APPLICATION_FIELDS,
    _APPROVAL_FIELDS,
    TERMINAL_SCHEDULES,
)


def load_document(text: str) -> dict | None:
    body = re.sub(r"^window\.PROJECTS\s*=\s*", "", text.strip())
    body = re.sub(r";\s*$", "", body)
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        return None


def header_name(headers: dict, cid: str) -> str:
    hdr = (headers or {}).get(cid)
    if isinstance(hdr, dict):
        return str(hdr.get("NAME", "x") or "x")
    if isinstance(hdr, str) and hdr:
        return hdr
    return "x"


def awaiting_in_doc(doc: dict) -> tuple[int, Counter]:
    """The pipeline's rule, read from the payload's own bytes."""
    districts: Counter = Counter()
    total = 0
    for p in doc["projects"]:
        links = p.get("links") or {}
        per_case = links.get("case_milestones") or {}
        schedules = links.get("case_schedules") or {}
        headers = links.get("case_headers") or {}
        replaced = links.get("superseded_by") or {}
        found = False
        for cid, ms in per_case.items():
            if not isinstance(ms, dict):
                continue
            if schedules.get(cid) in TERMINAL_SCHEDULES:
                continue
            if cid in replaced:
                continue
            if header_name(headers, cid).strip() in ("", "無"):
                continue
            if any(ms.get(f) for f in _APPROVAL_FIELDS):
                continue
            if any(ms.get(f) for f in _APPLICATION_FIELDS):
                found = True
                break
        if found:
            total += 1
            districts[p.get("district", "")] += 1
    return total, districts


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--limit", type=int, default=30)
    ap.add_argument("--names", default="", help="revisions to name the districts for")
    args = ap.parse_args()

    revs = subprocess.run(
        ["git", "log", "--format=%h", "-n", str(args.limit), "--", PATH_IN_REPO],
        cwd=ROOT, capture_output=True, text=True, check=True,
    ).stdout.split()

    print("%-9s %-46s %s" % ("commit", "subject", "awaiting"))
    print("-" * 78)
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
        n, _ = awaiting_in_doc(doc)
        print("%-9s %-46s %d" % (rev, subject[:46], n))

    for rev in (args.names or "").split():
        out = subprocess.run(
            ["git", "show", f"{rev}:{PATH_IN_REPO}"],
            cwd=ROOT, capture_output=True,
        )
        doc = load_document(out.stdout.decode("utf-8", errors="replace"))
        if doc is None:
            continue
        n, d = awaiting_in_doc(doc)
        print()
        print("%s — %d awaiting, %d districts" % (rev, n, len(d)))
        print("   ", dict(d.most_common()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
