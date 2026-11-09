"""Did the archive drop any live scenario?

`openspec archive` replaces a MODIFIED requirement wholesale rather than
merging it. A delta that does not name every scenario of the requirement it
replaces loses the ones it leaves out — silently, because the archive reports
a count and not a diff.

This compares the spec before the archive with the spec after it, scenario by
scenario, and names any scenario the archive dropped. A scenario is identified
by its heading, so a scenario whose text was extended still counts as kept.

    python scripts/probe_archive_scenarios.py <commit-before> <commit-after> <spec-path>

Reads two committed blobs. Writes nothing, reaches no network.
"""

from __future__ import annotations

import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]

REQ_RE = re.compile(r"^### Requirement: (.+)$", re.M)
SCEN_RE = re.compile(r"^#### (.+)$", re.M)


def read(rev: str, path: str) -> str:
    out = subprocess.run(
        ["git", "show", f"{rev}:{path}"],
        cwd=ROOT, capture_output=True,
    )
    if out.returncode != 0:
        raise SystemExit(f"cannot read {rev}:{path}")
    return out.stdout.decode("utf-8", errors="replace")


def scenarios_by_requirement(text: str) -> dict[str, list[str]]:
    """requirement heading -> the scenario headings under it."""
    out: dict[str, list[str]] = {}
    blocks = re.split(r"^### Requirement: ", text, flags=re.M)[1:]
    for block in blocks:
        title = block.splitlines()[0].strip()
        out[title] = [m.strip() for m in SCEN_RE.findall(block)]
    return out


def main() -> int:
    if len(sys.argv) < 4:
        print(__doc__.strip())
        print("usage: probe_archive_scenarios.py <before> <after> <spec-path>")
        return 2
    before_rev, after_rev, path = sys.argv[1], sys.argv[2], sys.argv[3]

    before = scenarios_by_requirement(read(before_rev, path))
    after = scenarios_by_requirement(read(after_rev, path))

    print("spec: %s" % path)
    print("  before (%s): %d requirements, %d scenarios"
          % (before_rev, len(before), sum(len(v) for v in before.values())))
    print("  after  (%s): %d requirements, %d scenarios"
          % (after_rev, len(after), sum(len(v) for v in after.values())))

    dropped_requirements = [r for r in before if r not in after]
    dropped_scenarios: list[str] = []
    for req, scens in before.items():
        if req not in after:
            continue
        kept = set(after[req])
        for s in scens:
            if s not in kept:
                dropped_scenarios.append("%s / %s" % (req, s))

    print()
    if dropped_requirements:
        print("requirements the archive DROPPED: %d" % len(dropped_requirements))
        for r in dropped_requirements:
            print("   ", r)
    else:
        print("no requirement was dropped.")
    if dropped_scenarios:
        print("scenarios the archive DROPPED: %d" % len(dropped_scenarios))
        for s in dropped_scenarios:
            print("   ", s)
    else:
        print("no scenario was dropped.")
    return 1 if (dropped_requirements or dropped_scenarios) else 0


if __name__ == "__main__":
    raise SystemExit(main())
