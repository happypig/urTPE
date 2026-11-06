"""Find which session transcript WROTE a given change. Read-only.

Three sessions work in this tree and every commit carries the same configured
author and the same trailer, so the git history can never answer "who wrote
this". The session transcripts under ~/.claude/projects/ can: each transcript
is one session's own record, so the tool_use that wrote the line names the
session that wrote it.

    python scripts/probe_third_session_transcript.py <needle> [--all]

The needle is matched against what a session did, and each match is
classified by what the tool actually did:

    EDITED   the Edit or Write tool, or a shell command that rewrites a file
    COMMITTED a git commit
    STAGED   a git add
    READ     a git show, git log, grep, cat — a session that LOOKED

Only EDITED, COMMITTED and STAGED are reported by default. A session that
read a line is not the session that wrote it, and scoring the two alike
makes the tool contradict a settled reading. Pass ``--all`` to see the
readers too.

The default needle must exercise the tool, so it names a thing that is
still in the tree. The line it once named — kwargs.get("publisher_url",
"") — was replaced by the commit that carried it, and a default that finds
nothing reads as a broken tool.

Reads the transcripts and prints. Writes nothing, reaches no network.
"""

from __future__ import annotations

import json
import pathlib
import re
import sys

ROOT = pathlib.Path.home() / ".claude" / "projects" / "D--project-urTPE"

DEFAULT_NEEDLE = "publisher_url"

# A shell command that rewrites a file: a redirect into one, or a python
# that opens it for writing.
_WRITE_RE = re.compile(r"(>\s*[\w./\\-]+\s*$)|(>>\s*[\w./\\-]+\s*$)|"
                       r"open\([^)]*['\"][wa]['\"]|write_text|write_bytes")


def classify(name: str, cmd: str) -> str:
    """What the tool did, by its name and its command."""
    if name in ("Edit", "Write", "MultiEdit", "NotebookEdit"):
        return "EDITED"
    if not cmd:
        return "READ"
    if re.search(r"git\s+commit", cmd):
        return "COMMITTED"
    if re.search(r"git\s+add\b", cmd):
        return "STAGED"
    if _WRITE_RE.search(cmd):
        return "EDITED"
    return "READ"


def scan(needle: str):
    """Every session that touched the needle, classified."""
    for path in sorted(ROOT.glob("*.jsonl")):
        first_user = ""
        acts = []
        saw = []
        try:
            with path.open(encoding="utf-8", errors="replace") as fh:
                for lineno, line in enumerate(fh, 1):
                    try:
                        rec = json.loads(line)
                    except ValueError:
                        continue
                    msg = rec.get("message") or {}
                    content = msg.get("content")
                    if rec.get("type") == "user" and not first_user:
                        first_user = _text_of(content)
                    if not isinstance(content, list):
                        continue
                    for part in content:
                        if not isinstance(part, dict):
                            continue
                        if part.get("type") == "tool_use":
                            name = part.get("name") or ""
                            inp = part.get("input") or {}
                            blob = json.dumps(inp, ensure_ascii=False)
                            if needle not in blob:
                                continue
                            cmd = inp.get("command") or ""
                            kind = classify(name, cmd if isinstance(cmd, str) else "")
                            acts.append((lineno, kind, name, _describe(name, inp, cmd)))
                        elif part.get("type") == "tool_result":
                            body = json.dumps(part.get("content"), ensure_ascii=False)
                            if needle in body:
                                saw.append((lineno, body.replace("\\n", " ")[:200]))
        except OSError:
            continue
        if acts or saw:
            yield path, first_user, acts, saw


def _text_of(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        for part in content:
            if isinstance(part, dict) and part.get("type") == "text":
                return part.get("text", "")
    return ""


def _describe(name: str, inp: dict, cmd) -> str:
    """One line naming what the tool touched, and the text it wrote.

    An Edit carries both the old and the new text, so the needle usually
    appears in the old text — the line being replaced. The new text is what
    the session actually wrote, so it is quoted when there is one.
    """
    if isinstance(cmd, str) and cmd:
        return cmd.replace("\n", " ")[:300]
    path = inp.get("file_path") or inp.get("notebook_path") or ""
    new = inp.get("new_string") or inp.get("content") or ""
    if isinstance(new, str) and new.strip():
        head = new.strip().splitlines()[0][:150]
        return "%s %s  ->  %s" % (name, path, head)
    if path:
        return "%s %s" % (name, path)
    keys = ", ".join(sorted(inp)[:6])
    return "%s (%s)" % (name, keys) if keys else name


def main(argv: list[str]) -> int:
    args = [a for a in argv if a != "--all"]
    show_all = "--all" in argv
    needle = args[0] if args else DEFAULT_NEEDLE

    print("needle: %s" % needle)
    print("the verdict is the session that EDITED, COMMITTED or STAGED it;")
    print("a session that only READ it is shown with --all.\n")

    found = False
    for path, first_user, acts, saw in scan(needle):
        real = [a for a in acts if a[1] != "READ"]
        if not real and not show_all:
            continue
        found = True
        print("=" * 72)
        print(path.name)
        if first_user:
            print("  first user message: %s"
                  % first_user.replace("\n", " ").replace("<", "")[:150])
        for lineno, kind, name, text in real[:6]:
            print("  %-9s line %-6d %s" % (kind, lineno, text))
        if show_all:
            for lineno, kind, name, text in [a for a in acts if a[1] == "READ"][:3]:
                print("  READ     line %-6d %s" % (lineno, text))
            for lineno, text in saw[:2]:
                print("  saw      line %-6d %s" % (lineno, text))

    if not found:
        print("no session edited, committed or staged that needle.")
        print("(pass --all to see the sessions that only read it)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
