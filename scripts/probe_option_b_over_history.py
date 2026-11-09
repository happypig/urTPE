"""When did the dashboard's Option B predicate stop selecting 6 projects?

The predicate is a project carrying no national portal link (``links.twur``
empty) AND no city case id (``links.taipei`` empty). The dashboard document
says it selects exactly 6 and that it "survived three payload revisions
without moving". The current payload says 0.

This walks the payload's history and reports the predicate's count at each
revision, so the claim in the document can be checked against the payloads
that actually existed.

    python scripts/probe_option_b_over_history.py [--limit N]

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


def load_document(text: str) -> dict | None:
    body = re.sub(r"^window\.PROJECTS\s*=\s*", "", text.strip())
    body = re.sub(r";\s*$", "", body)
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        return None


def count_unverified(doc: dict) -> int:
    n = 0
    for p in doc["projects"]:
        links = p.get("links") or {}
        if (links.get("twur") or "").strip():
            continue
        if links.get("taipei") or []:
            continue
        n += 1
    return n


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--limit", type=int, default=25)
    ap.add_argument("--names", help="also name the unverified projects at these revisions")
    args = ap.parse_args()

    revs = subprocess.run(
        ["git", "log", "--format=%h", "-n", str(args.limit), "--", PATH_IN_REPO],
        cwd=ROOT, capture_output=True, text=True, check=True,
    ).stdout.split()

    print("%-9s %-52s %s" % ("commit", "subject", "unverified"))
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
            print("%-9s %-52s %s" % (rev, "(not a payload)", "-"))
            continue
        subject = subprocess.run(
            ["git", "log", "-1", "--format=%s", rev],
            cwd=ROOT, capture_output=True, text=True, check=True,
        ).stdout.strip()
        print("%-9s %-52s %d" % (rev, subject[:52], count_unverified(doc)))

    for rev in (args.names or "").split():
        out = subprocess.run(
            ["git", "show", f"{rev}:{PATH_IN_REPO}"],
            cwd=ROOT, capture_output=True,
        )
        doc = load_document(out.stdout.decode("utf-8", errors="replace"))
        if doc is None:
            continue
        print()
        print("%s — the unverified projects:" % rev)
        for p in doc["projects"]:
            links = p.get("links") or {}
            if (links.get("twur") or "").strip() or (links.get("taipei") or []):
                continue
            print("   ", p["project_id"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
