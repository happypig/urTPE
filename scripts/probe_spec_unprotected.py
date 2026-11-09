"""Audit a spec for content the archive's guard does not protect.

`openspec archive` replaces a MODIFIED requirement wholesale, and its guard
(`findMissingCurrentScenarios` in the installed package's
`dist/core/specs-apply.js`) compares only `#### Scenario:` headings that sit
OUTSIDE a fenced code block, by name, with multiplicity.

So three kinds of live content are replaced without any protection:

  - a `#### Scenario:` heading inside a fenced example — masked, so the guard
    neither counts it nor notices its loss;
  - any other `####` heading (a note, an example block) — not counted at all;
  - the requirement's prose — never compared.

A delta that drops any of these archives cleanly and the archive reports
nothing. This probe finds that shape in a spec so the delta can be written to
carry it.

    python scripts/probe_spec_unprotected.py <commit> <spec-path>

Reads one committed blob. Writes nothing, reaches no network.
"""

from __future__ import annotations

import re
import subprocess
import sys

# The guard's own patterns: a scenario heading is `#### Scenario:` with a
# name, and any other `####` heading is content it never counts.
SCENARIO_RE = re.compile(r"^####\s*Scenario:\s*(.+?)\s*$")
HEADING_RE = re.compile(r"^####\s+\S")

# The archive's fence detection (dist/core/parsers/code-fence.js): a fence
# opens with 3 or more backticks OR 3 or more tildes, and closes on the same
# marker at the same length or longer. A `~~~` fence is a fence — the guard
# masks it, so a `#### Scenario:` inside one is unprotected, and a probe that
# only looks for ``` misses it.
FENCE_MARKER_RE = re.compile(r"^\s*(`{3,}|~{3,})")
FENCE_CLOSE_RE = re.compile(r"^\s*(`{3,}|~{3,})\s*$")


def requirement_blocks(text: str) -> list[tuple[str, str]]:
    """-> [(title, body)] for each '### Requirement:' block."""
    out = []
    for part in re.split(r"^### Requirement: ", text, flags=re.M)[1:]:
        title, _, body = part.partition("\n")
        out.append((title.strip(), body))
    return out


def fence_mask(lines: list[str]) -> list[bool]:
    """Which lines sit inside a fenced code block, the way the guard sees them.

    Mirrors `buildCodeFenceMask` in the archive's
    `dist/core/parsers/code-fence.js`: the fence marker is a run of 3 or more
    backticks or 3 or more tildes, and it closes on the same character at the
    same length or longer. The opening and closing fence lines are part of the
    block."""
    mask = [False] * len(lines)
    active: tuple[str, int] | None = None
    for i, line in enumerate(lines):
        if active is None:
            m = FENCE_MARKER_RE.match(line)
            if m:
                active = (m.group(1)[0], len(m.group(1)))
                mask[i] = True
            continue
        mask[i] = True
        m = FENCE_CLOSE_RE.match(line)
        if m and m.group(1)[0] == active[0] and len(m.group(1)) >= active[1]:
            active = None
    return mask


def audit(text: str) -> list[tuple[str, list[str], list[str]]]:
    """-> [(requirement title, fenced scenarios, other '####' headings)]"""
    out = []
    for title, body in requirement_blocks(text):
        lines = body.split("\n")
        mask = fence_mask(lines)
        fenced = [ln for i, ln in enumerate(lines)
                  if mask[i] and SCENARIO_RE.match(ln)]
        other = [ln for ln in lines
                 if HEADING_RE.match(ln) and not SCENARIO_RE.match(ln)]
        if fenced or other:
            out.append((title, fenced, other))
    return out


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(__doc__)
        print("usage: probe_spec_unprotected.py <commit> <spec-path>")
        return 2
    rev, path = argv[1], argv[2]
    proc = subprocess.run(
        ["git", "show", "%s:%s" % (rev, path)],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        print("[ERROR] cannot read %s:%s\n%s" % (rev, path, proc.stderr.strip()))
        return 1
    text = proc.stdout

    findings = audit(text)
    print("spec: %s @ %s" % (path, rev))
    if not findings:
        print("  no fenced scenarios and no other '####' headings.")
        print("  Every requirement's content is a scenario heading or prose;")
        print("  the guard protects the headings and nothing else.")
        return 0

    for title, fenced, other in findings:
        print("  requirement: %s" % title)
        for line in fenced:
            print("    UNPROTECTED (fenced scenario): %s" % line.strip())
        for line in other:
            print("    UNPROTECTED (other heading)  : %s" % line.strip())
    print()
    print("  %d requirement(s) carry content the guard does not protect." % len(findings))
    print("  The delta must carry them; the archive will not notice their loss.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
