"""Which rule gives the dashboard's 97, and which gives 99?

The payload and the cache agree: 99 projects await approval, read with the
pipeline's own `cached_cases_awaiting_approval`. The dashboard document (§4.1)
says 97, and says the payload computes it exactly.

This tries the plausible variants of "a case carries an application date and
no approval date, and is neither terminal nor superseded" and reports each
one's count, so the 97 can be traced to the rule that produced it. A rule
that is not stated cannot be checked; this names it.

    python scripts/probe_awaiting_rules.py

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

# the fields a rule may treat as "an application"
APPLICATION_SETS = {
    "all 5 (the pipeline's)": _APPLICATION_FIELDS,
    "申請核定日期 only": ("申請核定日期",),
    "申請核定日期 + 權變申請核定日期": ("申請核定日期", "權變申請核定日期"),
    "申請計畫日期 only": ("申請計畫日期",),
    "申請概要核准日期 only": ("申請概要核准日期",),
    "3 申請* (no 概要)": ("申請核定日期", "權變申請核定日期", "申請計畫日期"),
}


def load_payload() -> dict:
    text = PAYLOAD.read_text(encoding="utf-8")
    body = re.sub(r"^window\.PROJECTS\s*=\s*", "", text.strip())
    body = re.sub(r";\s*$", "", body)
    return json.loads(body)


def header_name(headers: dict, cid: str) -> str:
    hdr = (headers or {}).get(cid)
    if isinstance(hdr, dict):
        return str(hdr.get("NAME", "x") or "x")
    if isinstance(hdr, str) and hdr:
        return hdr
    return "x"


def count(payload: dict, cache: dict, app_fields: tuple[str, ...],
          *, use_cache: bool, terminal: bool, no_state: bool,
          superseded: bool) -> tuple[int, Counter]:
    hits: list[str] = []
    districts: Counter = Counter()
    for p in payload["projects"]:
        pid = p["project_id"]
        if use_cache:
            src = cache.get(pid) or {}
            per_case = src.get("case_milestones") or {}
            schedules = src.get("case_schedules") or {}
            headers = src.get("case_headers") or {}
            replaced = src.get("superseded_by") or {}
        else:
            links = p.get("links") or {}
            per_case = links.get("case_milestones") or {}
            schedules = links.get("case_schedules") or {}
            headers = links.get("case_headers") or {}
            replaced = links.get("superseded_by") or {}
        found = False
        for cid, ms in per_case.items():
            if not isinstance(ms, dict):
                continue
            if terminal and schedules.get(cid) in TERMINAL_SCHEDULES:
                continue
            if superseded and cid in replaced:
                continue
            if no_state and header_name(headers, cid).strip() in ("", "無"):
                continue
            if any(ms.get(f) for f in _APPROVAL_FIELDS):
                continue
            if any(ms.get(f) for f in app_fields):
                found = True
                break
        if found:
            hits.append(pid)
            districts[p.get("district", "")] += 1
    return len(hits), districts


def main() -> int:
    payload = load_payload()
    cache: dict = {}
    for p in payload["projects"]:
        rf = CACHE / p["project_id"] / "result.json"
        if rf.is_file():
            cache[p["project_id"]] = json.loads(rf.read_text(encoding="utf-8"))

    print("%-34s %-8s %-8s %s" % ("rule", "payload", "cache", "districts"))
    print("-" * 78)
    for label, fields in APPLICATION_SETS.items():
        for terminal in (True, False):
            for no_state in (True, False):
                for use_cache in (False, True):
                    n, d = count(payload, cache, fields,
                                 use_cache=use_cache, terminal=terminal,
                                 no_state=no_state, superseded=True)
                    tag = "%s | terminal=%s no-state=%s" % (
                        label, "y" if terminal else "n", "y" if no_state else "n")
                    print("%-46s %-8s %-8s %d"
                          % (tag[:46], n if not use_cache else "-",
                             n if use_cache else "-", len(d)))
    print()
    n, d = count(payload, cache, _APPLICATION_FIELDS, use_cache=True,
                 terminal=True, no_state=True, superseded=True)
    print("the pipeline's own rule, from the cache: %d" % n)
    print("districts:", dict(d.most_common()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
