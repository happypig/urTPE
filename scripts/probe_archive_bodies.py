"""Did the archive keep each requirement's live prose?

`openspec archive` replaces a MODIFIED requirement wholesale. The scenarios
are guarded — the archive aborts if a delta leaves one out — but the BODY is
not. A delta that carries every scenario but replaces the prose archives
cleanly, and the live paragraphs are lost.

This compares each requirement's body before and after the archive, and names
any live paragraph that the archive dropped. A paragraph is a non-empty line
that is not a heading, so a requirement's prose is compared line by line.

    python scripts/probe_archive_bodies.py <commit-before> <commit-after> <spec-path>

Reads two committed blobs. Writes nothing, reaches no network.
"""

from __future__ import annotations

import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]

REQ_RE = re.compile(r"^### Requirement: (.+)$", re.M)


def read(rev: str, path: str) -> str:
    out = subprocess.run(
        ["git", "show", f"{rev}:{path}"],
        cwd=ROOT, capture_output=True,
    )
    if out.returncode != 0:
        raise SystemExit(f"cannot read {rev}:{path}")
    return out.stdout.decode("utf-8", errors="replace")


def bodies_by_requirement(text: str) -> dict[str, list[str]]:
    """requirement heading -> its prose lines, with the scenarios removed.

    A scenario's own lines are excluded: the scenarios are guarded elsewhere,
    and this check is about the prose that sits around them.
    """
    out: dict[str, list[str]] = {}
    blocks = re.split(r"^### Requirement: ", text, flags=re.M)[1:]
    for block in blocks:
        lines = block.splitlines()
        title = lines[0].strip()
        prose: list[str] = []
        in_scenario = False
        for line in lines[1:]:
            if line.startswith("#### "):
                in_scenario = True
                continue
            if line.startswith("### "):
                in_scenario = False
                continue
            if in_scenario:
                # a scenario's WHEN/THEN lines
                if line.strip().startswith(("**WHEN**", "**THEN**", "AND", "GIVEN")):
                    continue
                continue
            text_line = line.strip()
            if text_line:
                prose.append(text_line)
        out[title] = prose
    return out


def main() -> int:
    if len(sys.argv) < 4:
        print(__doc__.strip())
        print("usage: probe_archive_bodies.py <before> <after> <spec-path>")
        return 2
    before_rev, after_rev, path = sys.argv[1], sys.argv[2], sys.argv[3]

    before = bodies_by_requirement(read(before_rev, path))
    after = bodies_by_requirement(read(after_rev, path))

    print("spec: %s" % path)
    lost = 0
    for req, prose in before.items():
        if req not in after:
            print("  requirement DROPPED: %s" % req)
            lost += 1
            continue
        kept = after[req]
        missing = [p for p in prose if p not in kept]
        if missing:
            print("  %s — %d live prose line(s) the archive dropped:" % (req, len(missing)))
            for m in missing:
                print("      %s" % m[:110])
            lost += len(missing)
    if not lost:
        print("no live prose was dropped.")
    return 1 if lost else 0


if __name__ == "__main__":
    raise SystemExit(main())
