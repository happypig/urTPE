"""How many projects does the dashboard's Option B predicate select now?

The predicate is the one measured for the dashboard's unverified column:
a project is UNVERIFIED when it carries no national portal link
(``links.twur`` empty) AND no city case id (``links.taipei`` empty).

It selected 6 projects when the predicate was measured. The
bind-the-unplaced-by-searching-the-cell-section change (2026-11-09) gave 7
projects their city case ids, so the predicate may now select a different
number. The dashboard's design depends on the answer, so the predicate is
re-measured over the current payload and over the payload as it stood
before that change.

    python scripts/probe_option_b_after_unplaced.py

Reads the payload and a committed blob. Writes nothing, reaches no network.
"""

from __future__ import annotations

import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]

# the commit whose payload the predicate was measured against
BEFORE = "846f4e2"


def load_document(text: str) -> dict:
    body = re.sub(r"^window\.PROJECTS\s*=\s*", "", text.strip())
    body = re.sub(r";\s*$", "", body)
    return json.loads(body)


def load_worktree() -> dict:
    return load_document((ROOT / "viewer" / "projects.data.js").read_text(encoding="utf-8"))


def load_commit(rev: str) -> dict:
    out = subprocess.run(
        ["git", "show", f"{rev}:viewer/projects.data.js"],
        cwd=ROOT, capture_output=True,
    )
    if out.returncode != 0:
        raise SystemExit(f"cannot read {rev}:viewer/projects.data.js")
    return load_document(out.stdout.decode("utf-8"))


def classify(doc: dict) -> tuple[list[str], list[str]]:
    """(unverified, national-link-only).

    unverified   — no twur link AND no city case id
    national-only — no twur link, but it carries city case ids
    """
    unverified: list[str] = []
    national_only: list[str] = []
    for p in doc["projects"]:
        links = p.get("links") or {}
        has_twur = bool((links.get("twur") or "").strip())
        has_city = bool(links.get("taipei") or [])
        if has_twur:
            continue
        if has_city:
            national_only.append(p["project_id"])
        else:
            unverified.append(p["project_id"])
    return unverified, national_only


def main() -> int:
    for label, doc in (("before %s" % BEFORE, load_commit(BEFORE)),
                       ("now (HEAD)", load_worktree())):
        unverified, national_only = classify(doc)
        print("%-16s projects=%d  unverified=%d  national-link-only=%d"
              % (label, doc["counts"]["projects"], len(unverified), len(national_only)))
        for pid in unverified:
            print("      unverified:", pid)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
