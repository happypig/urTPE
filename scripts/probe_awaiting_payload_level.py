"""How many payload projects await approval, computed from the payload alone?

The dashboard document (§4.1) counts 97 awaiting-approval projects and says
"The payload computes this exactly": a case carries an application date and
no approval date, and is neither terminal (自行撤回 / 已駁回 / 已失效) nor
superseded.

Two readings of that exist, and they do not agree:

  per PROJECT — the project's merged milestone projection carries an
                 application and no approval, and the project has no
                 superseded case.
  per CASE    — any of the project's cases carries an application and no
                 approval, and that case is neither terminal nor superseded.

`cached_cases_awaiting_approval` is the per-CASE rule, read from the cache.
This measures both readings from the payload and names the difference, so
the document's 97 can be checked against the rule it describes.

    python scripts/probe_awaiting_payload_level.py

Reads the payload and the caches. Writes nothing, reaches no network.
"""

from __future__ import annotations

import json
import pathlib
import re
import sys
from collections import Counter

ROOT = pathlib.Path(__file__).resolve().parents[1]
PAYLOAD = ROOT / "viewer" / "projects.data.js"
CACHE = ROOT / "data" / ".link_cache"

sys.path.insert(0, str(ROOT))
from urtpe.links import (  # noqa: E402
    _APPLICATION_FIELDS,
    _APPROVAL_FIELDS,
    TERMINAL_SCHEDULES,
    cached_cases_awaiting_approval,
)


def load_payload() -> dict:
    text = PAYLOAD.read_text(encoding="utf-8")
    body = re.sub(r"^window\.PROJECTS\s*=\s*", "", text.strip())
    body = re.sub(r";\s*$", "", body)
    return json.loads(body)


def per_case_from_payload(links: dict) -> bool:
    """Any case of the project: an application, no approval, not terminal.

    A MISSING header is not evidence of 無, so the default is "x" — the same
    default the pipeline's own predicate uses. Reading it as "" would exclude
    every case whose header the payload does not carry.
    """
    per_case = links.get("case_milestones") or {}
    schedules = links.get("case_schedules") or {}
    headers = links.get("case_headers") or {}
    replaced = links.get("superseded_by") or {}
    for cid, ms in per_case.items():
        if not isinstance(ms, dict):
            continue
        if schedules.get(cid) in TERMINAL_SCHEDULES:
            continue
        if cid in replaced:
            continue
        hdr = headers.get(cid)
        if isinstance(hdr, dict):
            name = hdr.get("NAME", "x")
        elif isinstance(hdr, str):
            name = hdr
        else:
            name = "x"
        if str(name or "x").strip() in ("", "無"):
            continue
        if any(ms.get(f) for f in _APPROVAL_FIELDS):
            continue
        if any(ms.get(f) for f in _APPLICATION_FIELDS):
            return True
    return False


def per_project_from_payload(links: dict) -> bool:
    """The project's merged projection: an application, no approval."""
    ms = links.get("milestones_taipei") or {}
    if any(ms.get(f) for f in _APPROVAL_FIELDS):
        return False
    return any(ms.get(f) for f in _APPLICATION_FIELDS)


def main() -> int:
    doc = load_payload()
    projects = doc["projects"]

    per_case = Counter()
    per_proj = Counter()
    per_case_ids: list[str] = []
    cache_rule_ids: list[str] = []

    for p in projects:
        links = p.get("links") or {}
        if per_case_from_payload(links):
            per_case[p.get("district", "")] += 1
            per_case_ids.append(p["project_id"])
        if per_project_from_payload(links):
            per_proj[p.get("district", "")] += 1

        rf = CACHE / p["project_id"] / "result.json"
        if rf.is_file():
            data = json.loads(rf.read_text(encoding="utf-8"))
            if cached_cases_awaiting_approval(
                data.get("case_milestones") or {},
                data.get("case_schedules") or {},
                data.get("case_headers") or {},
                data.get("superseded_by") or {},
            ):
                cache_rule_ids.append(p["project_id"])

    print("projects: %d" % len(projects))
    print()
    print("per CASE, from the payload  : %d" % len(per_case_ids))
    print("per CASE, from the cache    : %d" % len(cache_rule_ids))
    print("per PROJECT, from the payload: %d" % sum(per_proj.values()))
    print()
    only_payload = sorted(set(per_case_ids) - set(cache_rule_ids))
    only_cache = sorted(set(cache_rule_ids) - set(per_case_ids))
    print("in the payload rule but not the cache rule: %d" % len(only_payload))
    for pid in only_payload:
        print("   ", pid)
    print("in the cache rule but not the payload rule: %d" % len(only_cache))
    for pid in only_cache:
        print("   ", pid)

    print()
    print("per-CASE district split (payload):")
    for district, n in per_case.most_common():
        print("   %-8s %d" % (district, n))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
