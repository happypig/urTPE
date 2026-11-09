"""Did the archive drop any live scenario?

`openspec archive` replaces a MODIFIED requirement wholesale rather than
merging it. The archive's own guard (`findMissingCurrentScenarios` in
`dist/core/specs-apply.js`) compares the LIVE requirement's scenario
headings with the delta's, by NAME, with multiplicity: a name present N times
in the live block and M times in the delta means max(0, N-M) instances are
missing. Set membership would let a duplicate be dropped silently.

This probe mirrors that rule, so it names what the archive would have
dropped — including the duplicate case the guard protects and a naive
set-membership check misses.

**The guard compares names, not text.** A scenario whose body was replaced
still counts as kept, because the guard never reads a scenario's body. The
body is a separate question; `probe_archive_bodies.py` asks it.

**A scenario inside a fenced code block is not a scenario.** The archive
masks fenced lines before it counts, so a fenced `#### Scenario:` sample is
neither protected nor counted. This probe masks the same lines.

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
SCEN_RE = re.compile(r"^####\s*Scenario:\s*(.+?)\s*$", re.M)
FENCE_RE = re.compile(r"^\s*(```|~~~)")


def read(rev: str, path: str) -> str:
    out = subprocess.run(
        ["git", "show", f"{rev}:{path}"],
        cwd=ROOT, capture_output=True,
    )
    if out.returncode != 0:
        raise SystemExit(f"cannot read {rev}:{path}")
    return out.stdout.decode("utf-8", errors="replace")


def _mask_fences(lines: list[str]) -> list[bool]:
    """True for each line that sits inside a fenced code block.

    The archive masks the same lines before it counts scenarios, so a fenced
    `#### Scenario:` sample is neither protected nor counted."""
    masked: list[bool] = []
    in_fence = False
    fence = ""
    for line in lines:
        m = FENCE_RE.match(line)
        if m:
            marker = m.group(1)
            if not in_fence:
                in_fence, fence = True, marker
            elif marker == fence:
                in_fence, fence = False, ""
            masked.append(True)
            continue
        masked.append(in_fence)
    return masked


def scenarios_by_requirement(text: str) -> dict[str, list[str]]:
    """requirement heading -> the scenario headings under it, in order.

    A scenario is identified by its heading, and a fenced block's headings are
    ignored. The list keeps duplicates: the archive's guard is
    multiplicity-aware, so a name present twice in the live block and once in
    the delta is one dropped instance.
    """
    out: dict[str, list[str]] = {}
    blocks = re.split(r"^### Requirement: ", text, flags=re.M)[1:]
    for block in blocks:
        title = block.splitlines()[0].strip()
        lines = block.splitlines()
        masked = _mask_fences(lines)
        names: list[str] = []
        for i, line in enumerate(lines):
            if masked[i]:
                continue
            m = SCEN_RE.match(line)
            if m:
                names.append(m.group(1).strip())
        out[title] = names
    return out


def missing_scenarios(live: list[str], incoming: list[str]) -> list[str]:
    """The live scenario instances the incoming block does not carry.

    Multiplicity-aware, mirroring `findMissingCurrentScenarios`: a name
    present N times in live and M times in incoming means max(0, N-M)
    instances are missing."""
    remaining: dict[str, int] = {}
    for name in incoming:
        remaining[name] = remaining.get(name, 0) + 1
    missing: list[str] = []
    for name in live:
        left = remaining.get(name, 0)
        if left > 0:
            remaining[name] = left - 1
        else:
            missing.append(name)
    return missing


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
    for req, live in before.items():
        if req not in after:
            continue
        for name in missing_scenarios(live, after[req]):
            dropped_scenarios.append("%s / Scenario: %s" % (req, name))

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
