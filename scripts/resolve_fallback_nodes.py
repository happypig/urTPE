#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Resolve the positional-fallback nodes: run the 4-step resolver live.

resolve-recno-case task 3.3. The resolver binds offline at emit time; the
live steps (same-day id probe, all-parcel search) belong to this sweep: it
re-runs the resolver for every node the date matcher cannot place, with the
real adapters, and writes every accepted find into the project's cache
(append-only city_case_ids + milestones + names + headers). The next
emission binds from the caches without a request.

Read-only towards the city: get_project168_top (the probe's header) and
Get_updcase_list (the parcel search). Rate-limited at --delay seconds.

Single-writer rule (AGENTS.md): do not run this while an ingestion or a
refresh owns the cache.

    python scripts/resolve_fallback_nodes.py [--dry-run] [--delay 1.0]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from urtpe.links import (  # noqa: E402
    _match_case_by_date,
    fetch_taipei_case_header_api,
    fetch_taipei_milestones_api,
    load_project_cache,
    resolve_node_cases,
    resolve_cache_dir,
    save_project_cache,
    search_taipei_cases_api,
)


def fallback_nodes(doc: dict) -> list[tuple[str, dict]]:
    """[(project_id, node)] for every node whose bound case the date matcher
    refutes (the payload's positional-fallback nodes) or that carries none."""
    out = []
    for p in doc.get("projects", []):
        L = p.get("links") or {}
        city = L.get("taipei") or []
        milestones = L.get("case_milestones") or {}
        for n in p.get("nodes", []):
            bound = (n.get("links") or {}).get("taipei") or []
            if not bound and not city:
                continue
            disc = type("D", (object,), {})()
            disc.project_id = p["project_id"]
            disc.city_case_ids = list(city)
            disc.case_milestones = milestones
            date = n.get("date") or ""
            if bound and _match_case_by_date(date, disc):
                continue
            out.append((p["project_id"], n))
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--cache", default=str(ROOT / "data" / ".link_cache"))
    ap.add_argument("--payload", default=str(ROOT / "viewer" / "projects.data.js"))
    ap.add_argument("--delay", type=float, default=1.0,
                    help="seconds between requests (rate limit)")
    ap.add_argument("--dry-run", action="store_true",
                    help="list the fallback nodes and stop")
    args = ap.parse_args(argv)

    text = Path(args.payload).read_text(encoding="utf-8").strip()
    doc = json.loads(text[text.index("{"):].rstrip().rstrip(";"))
    nodes = fallback_nodes(doc)
    print(f"fallback nodes: {len(nodes)} on "
          f"{len({pid for pid, _ in nodes})} project(s)")
    if args.dry_run:
        for pid, n in nodes:
            print(f"  {pid} recno {n.get('recno')} {n.get('date')} "
                  f"{(n.get('case_name') or '')[:36]}")
        return 0

    cache_dir = Path(args.cache)
    delay = args.delay
    resolved = 0
    unresolved: list[str] = []
    requests = 0

    def pace() -> None:
        nonlocal requests
        requests += 1
        time.sleep(delay)

    # the probe/search adapters pace through the shared counter
    def fetch_header(cid: str) -> dict:
        pace()
        return fetch_taipei_case_header_api(cid)

    def fetch_milestones(cid: str) -> dict:
        pace()
        return fetch_taipei_milestones_api(cid)

    def search(section: str, parcel: str, dropped_out=None, anchor_name: str = "") -> list:
        pace()
        return search_taipei_cases_api(section, parcel, dropped_out=dropped_out,
                                       anchor_name=anchor_name)

    current_pid = None
    cache = None
    changed = False
    for pid, n in nodes:
        if pid != current_pid:
            # write the previous project's cache before moving on
            if cache is not None and changed:
                save_project_cache(cache_dir, current_pid, cache)
            current_pid = pid
            cache = load_project_cache(cache_dir, pid)
            changed = False
            if cache is None:
                print(f"  {pid}: no cache, skipped", file=sys.stderr)
                continue
        member = type("M", (object,), {})()
        member.date = n.get("date") or ""
        member.name = n.get("case_name") or ""
        member.stage = n.get("stage") or ""
        member.track = n.get("track") or ""
        member.recno = n.get("recno")
        member.parcels = list(n.get("parcels") or [])
        member.section = n.get("section") or ""
        member.review_flags = []
        # the resolver mutates the cache in place on acceptance
        before = list(cache.city_case_ids)
        got = resolve_node_cases(member, cache, fetch_header=fetch_header,
                                 fetch_milestones=fetch_milestones,
                                 search=search)
        if cache.city_case_ids != before:
            changed = True
        if got:
            resolved += 1
            print(f"  {pid} recno {member.recno} {member.date}: -> {','.join(got)}")
        else:
            unresolved.append(f"{pid} recno {member.recno} {member.date}")
    if cache is not None and changed:
        save_project_cache(cache_dir, current_pid, cache)

    print(f"\n{len(nodes)} node(s): {resolved} resolved, {len(unresolved)} unresolved; "
          f"{requests} request(s)")
    for u in unresolved:
        print(f"  UNRESOLVED {u}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
