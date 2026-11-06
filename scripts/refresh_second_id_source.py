#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""D9c-2a(b): the second id source, on the projects that need it.

The 168 list names case ids the city's parcel search does not index
(10708311, 11412011 — live probe 2026-11-05). The refresh's second-id-source
step reads the list, scopes it by the project's own section, and confirms each
candidate by that case's header before the id enters the project's case list.

This driver runs that step over the projects whose nodes carry the unplaced
flag 節點未能對應平台案件 — the projects that can benefit — and writes into
``data/.link_cache/`` only.

    python scripts/refresh_second_id_source.py [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from urtpe.links import refresh_project, resolve_cache_dir  # noqa: E402
from urtpe.lock import SingleWriterLock  # noqa: E402

CACHE_DIR = ROOT / "data" / ".link_cache"
UNPLACED = "節點未能對應平台案件"


def _search_key(project: dict) -> tuple[str, str, str]:
    """The (section, first parcel, anchor name) the refresh searches by."""
    anchor = next((n for n in project["nodes"]
                   if n["recno"] == project["anchor_recno"]), project["nodes"][0])
    return (anchor.get("section", ""), anchor.get("first_parcel", ""),
            (anchor.get("case_name") or anchor.get("name") or "")[:40])


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--delay", type=float, default=1.0)
    args = ap.parse_args(argv)

    doc = json.loads((ROOT / "data" / "projects.json").read_text(encoding="utf-8"))
    # the 168 list's rows, and the sections they name — the same substring
    # test the refresh's own scope check uses
    list_rows = json.loads((ROOT / "data" / "p168_all.json").read_text(encoding="utf-8"))
    list_names = [str(r.get("T_name") or "") for r in list_rows]

    targets = []
    for p in doc["projects"]:
        section, parcel, _name = _search_key(p)
        unplaced = any(UNPLACED in f for n in p["nodes"]
                       for f in (n.get("review_flags") or []))
        # the second id source can help a project in two ways: a node the
        # parcel search cannot reach (the unplaced flag), and a node that
        # should hold a SIBLING case the search missed (玉成166's node 75
        # holds the A區 twin 11412012 but not the B區 twin 11412011).
        #
        # the sibling shape: the project has a node bound to an 區 area case
        # (11412012 is the -A區 twin) and the list names another case of the
        # same unit.
        sibling_gap = False
        for n in p["nodes"]:
            for cid in (n.get("links") or {}).get("taipei", []) or []:
                if cid.endswith("11") or cid.endswith("12"):
                    sibling_gap = True
        # the scope is the section AND the parcel, ADJACENT — the city writes
        # 玉成段二小段166地號. A section alone names 504 projects (中山段一小段
        # appears in many), and the parcel alone names 246.
        in_list = any(
            section and parcel and re.search(
                re.escape(section) + r"\s*" + re.escape(parcel) + r"(?:地號|$)",
                name)
            for name in list_names)
        if unplaced or (sibling_gap and in_list):
            targets.append(p)

    print("projects the 168 list's sections name, or that carry an unplaced "
          "node:", len(targets))
    for p in targets:
        section, parcel, _name = _search_key(p)
        unplaced = any(UNPLACED in f for n in p["nodes"]
                       for f in (n.get("review_flags") or []))
        print("   %-46s section=%-14s parcel=%-10s unplaced=%s"
              % (p["project_id"], section, parcel, "yes" if unplaced else "no"))
    if args.dry_run:
        print("would refresh those projects with the second id source")
        return 0

    report = []
    with SingleWriterLock(ROOT / "data"):
        for p in targets:
            pid = p["project_id"]
            key = _search_key(p)
            try:
                r = refresh_project(CACHE_DIR, pid, search_key=key)
            except Exception as exc:
                print(f"  FAILED {pid}: {type(exc).__name__}: {exc}",
                      file=sys.stderr)
                continue
            added = [a for a in (r.get("added") or [])
                     if a.get("source", "").startswith("168 list")]
            unconfirmed = r.get("unconfirmed") or []
            report.append({"project_id": pid, "added": added,
                           "unconfirmed": unconfirmed, "error": r.get("error")})
            if added or unconfirmed:
                print("%-46s added=%s unconfirmed=%s"
                      % (pid, [a["case_id"] for a in added], unconfirmed))
    print()
    print("ids added:", sum(len(x["added"]) for x in report))
    print("ids unconfirmed:", sum(len(x["unconfirmed"]) for x in report))
    for x in report:
        if x["error"]:
            print("  ERROR", x["project_id"], x["error"])
    Path(ROOT / "data" / "second_id_source_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
