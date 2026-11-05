#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""D6's restore: re-fetch the ONE project whose twur override now applies.

`discover_project_links(project, cache_dir, fresh=True)` on a single project.
It is NOT the CLI's `--fresh`: that renames the whole `data/.link_cache/` to a
timestamped backup and starts an empty one — the 2026-08-24 incident shape,
where one project's restore would wipe all 719 caches and orphan every mapping
the index alone cannot rebuild.

This script touches exactly one cache directory.

    python scripts/restore_twur_override_project.py [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from urtpe.links import discover_project_links, load_project_cache  # noqa: E402
from urtpe.lock import SingleWriterLock  # noqa: E402
from urtpe.models import CleanRecord, Project  # noqa: E402

PROJECT_ID = "萬華區-崇仁新村青年段一小段-711-3地號等2筆"
CACHE_DIR = ROOT / "data" / ".link_cache"


def _project_from_payload(payload: dict) -> Project:
    """The project, rebuilt from the emitted payload's own nodes."""
    members = []
    for node in payload["nodes"]:
        members.append(CleanRecord(
            recno=node["recno"], date=node.get("date", ""),
            iso_date=node.get("iso_date", ""),
            ymd=tuple(node.get("ymd", (0, 0, 0))),
            district=node.get("district", ""),
            district_land=node.get("district_land", node.get("district", "")),
            name=node.get("case_name", node.get("name", "")),
            name_raw=node.get("name_raw", ""),
            land=node.get("land", ""),
            section=node.get("section", ""),
            first_parcel=node.get("first_parcel", ""),
            parcels=node.get("parcels", []),
            aliases=node.get("aliases", {}),
            land_count=node.get("land_count"),
            orig_count=node.get("orig_count"),
            named_anchor=node.get("named_anchor", ""),
            area_section=node.get("area_section", ""),
            stage=node.get("stage", ""),
            stage_index=node.get("stage_index", -1),
            track=node.get("track", ""),
            implementer=node.get("implementer", ""),
            planner=node.get("planner", ""),
            auto_fixes=node.get("auto_fixes", []),
            review_flags=node.get("review_flags", []),
        ))
    return Project(project_id=payload["project_id"],
                   anchor_recno=payload["anchor_recno"], members=members)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--delay", type=float, default=1.0)
    args = ap.parse_args(argv)

    doc = json.loads((ROOT / "data" / "projects.json").read_text(encoding="utf-8"))
    payload = next((p for p in doc["projects"]
                    if p["project_id"] == PROJECT_ID), None)
    if payload is None:
        print(f"[ERROR] the dataset holds no project {PROJECT_ID}")
        return 1

    before = load_project_cache(CACHE_DIR, PROJECT_ID)
    print("project:", PROJECT_ID)
    print("before: twur_view_id=%r national_milestones=%d twur_name=%r"
          % (before.twur_view_id if before else None,
             len(before.national_milestones or {}) if before else 0,
             (before.twur_name if before else "")[:40]))
    if args.dry_run:
        print("would re-fetch this one project's national page")
        return 0

    project = _project_from_payload(payload)
    with SingleWriterLock(ROOT / "data"):
        time.sleep(args.delay)
        result = discover_project_links(project, CACHE_DIR, fresh=True,
                                        delay=args.delay)
    after = load_project_cache(CACHE_DIR, PROJECT_ID)
    print("after:  twur_view_id=%r national_milestones=%d twur_name=%r"
          % (after.twur_view_id if after else None,
             len(after.national_milestones or {}) if after else 0,
             (after.twur_name if after else "")[:40]))
    print("status:", result.status, "error:", result.error or "(none)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
