"""Which two projects joined the awaiting-approval set, and why?

The dashboard document (§4.1) counts 97 awaiting-approval projects. It is
now 99. The move happened at the
bind-the-unplaced-by-searching-the-cell-section re-emit, which gave 7
projects their city case ids.

This names the two projects that joined and the case that made them count:
a project awaits when one of its cases carries an application and no
approval. A project that had no case id at all had no case to carry one, so
it could not await.

    python scripts/probe_awaiting_joiners.py

Reads two committed payloads. Writes nothing, reaches no network.
"""

from __future__ import annotations

import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
PATH_IN_REPO = "viewer/projects.data.js"
BEFORE = "eafb9dd"

sys.path.insert(0, str(ROOT))
from urtpe.links import (  # noqa: E402
    _APPLICATION_FIELDS,
    _APPROVAL_FIELDS,
    TERMINAL_SCHEDULES,
)


def load_document(text: str) -> dict:
    body = re.sub(r"^window\.PROJECTS\s*=\s*", "", text.strip())
    body = re.sub(r";\s*$", "", body)
    return json.loads(body)


def load_payload(rev: str | None) -> dict:
    if rev is None:
        text = (ROOT / PATH_IN_REPO).read_text(encoding="utf-8")
    else:
        out = subprocess.run(
            ["git", "show", f"{rev}:{PATH_IN_REPO}"],
            cwd=ROOT, capture_output=True,
        )
        if out.returncode != 0:
            raise SystemExit(f"cannot read {rev}:{PATH_IN_REPO}")
        text = out.stdout.decode("utf-8")
    return load_document(text)


def header_name(headers: dict, cid: str) -> str:
    hdr = (headers or {}).get(cid)
    if isinstance(hdr, dict):
        return str(hdr.get("NAME", "x") or "x")
    if isinstance(hdr, str) and hdr:
        return hdr
    return "x"


def awaiting_cases(doc: dict) -> dict[str, list[str]]:
    """project_id -> the case ids that make it await."""
    out: dict[str, list[str]] = {}
    for p in doc["projects"]:
        links = p.get("links") or {}
        per_case = links.get("case_milestones") or {}
        schedules = links.get("case_schedules") or {}
        headers = links.get("case_headers") or {}
        replaced = links.get("superseded_by") or {}
        hits = []
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
                hits.append(cid)
        if hits:
            out[p["project_id"]] = hits
    return out


def main() -> int:
    before = awaiting_cases(load_payload(BEFORE))
    now = awaiting_cases(load_payload(None))
    joined = sorted(set(now) - set(before))
    left = sorted(set(before) - set(now))
    print("before %s: %d awaiting" % (BEFORE, len(before)))
    print("now (HEAD) : %d awaiting" % len(now))
    print()
    print("joined (%d):" % len(joined))
    for pid in joined:
        links = (load_payload(None)["projects"])
        print("   %-46s cases %s" % (pid, now[pid]))
    print("left (%d):" % len(left))
    for pid in left:
        print("   ", pid)

    # what the case carries
    doc = load_payload(None)
    for p in doc["projects"]:
        if p["project_id"] not in joined:
            continue
        links = p.get("links") or {}
        for cid in now[p["project_id"]]:
            ms = (links.get("case_milestones") or {}).get(cid) or {}
            apps = {k: v for k, v in ms.items() if k in _APPLICATION_FIELDS}
            appr = {k: v for k, v in ms.items() if k in _APPROVAL_FIELDS}
            print()
            print("%s" % p["project_id"])
            print("   case %s  application %s  approval %s" % (cid, apps, appr or "none"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
