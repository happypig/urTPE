"""Which projects joined the awaiting-approval set, and which left it?

The dashboard document (§5) counts 97 awaiting approval. It is now 99. This
compares the set at the payload as it stood before the
bind-the-unplaced-by-searching-the-cell-section change with the set now, so
the difference is named rather than asserted.

The rule is the pipeline's own — `urtpe.links.cached_cases_awaiting_approval`.

    python scripts/probe_awaiting_delta.py

Reads two committed payloads and the caches. Writes nothing, reaches no
network.
"""

from __future__ import annotations

import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
CACHE = ROOT / "data" / ".link_cache"
PAYLOAD_IN_REPO = "viewer/projects.data.js"

# the payload before the unplaced change
BEFORE = "eafb9dd"

sys.path.insert(0, str(ROOT))
from urtpe.links import cached_cases_awaiting_approval  # noqa: E402


def load_document(text: str) -> dict:
    body = re.sub(r"^window\.PROJECTS\s*=\s*", "", text.strip())
    body = re.sub(r";\s*$", "", body)
    return json.loads(body)


def load_payload(rev: str | None) -> dict:
    if rev is None:
        text = (ROOT / PAYLOAD_IN_REPO).read_text(encoding="utf-8")
    else:
        out = subprocess.run(
            ["git", "show", f"{rev}:{PAYLOAD_IN_REPO}"],
            cwd=ROOT, capture_output=True,
        )
        if out.returncode != 0:
            raise SystemExit(f"cannot read {rev}:{PAYLOAD_IN_REPO}")
        text = out.stdout.decode("utf-8")
    return load_document(text)


def awaiting_set(doc: dict) -> set[str]:
    out = set()
    for p in doc["projects"]:
        rf = CACHE / p["project_id"] / "result.json"
        if not rf.is_file():
            continue
        data = json.loads(rf.read_text(encoding="utf-8"))
        if cached_cases_awaiting_approval(
            data.get("case_milestones") or {},
            data.get("case_schedules") or {},
            data.get("case_headers") or {},
            data.get("superseded_by") or {},
        ):
            out.add(p["project_id"])
    return out


def main() -> int:
    before = awaiting_set(load_payload(BEFORE))
    now = awaiting_set(load_payload(None))
    print("before %s: %d awaiting" % (BEFORE, len(before)))
    print("now (HEAD) : %d awaiting" % len(now))
    joined = sorted(now - before)
    left = sorted(before - now)
    print()
    print("joined (%d):" % len(joined))
    for pid in joined:
        print("   ", pid)
    print("left (%d):" % len(left))
    for pid in left:
        print("   ", pid)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
