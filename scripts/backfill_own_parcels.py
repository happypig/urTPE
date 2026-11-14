"""Backfill `own_parcels` into the caches that hold view ids.

section8-gate-anchor-parcel-drift D2: the §8 gate keeps a view-named case of
the unit's own parcels although its 案名 starts at another parcel (華中247).
It reads the unit's parcels from the cache's `own_parcels`. Discovery writes the
field for a new cache; the 675 existing caches have none, so the gate would
decide on the land core alone for them.

This script writes the field from the emitted payload's anchor record, for the
caches the gate reads: those holding `view_verified_case_ids` or `view_rejected`.
It copies each `result.json` it will change into a dated backup directory first
(the cache is the durable middle layer — AGENTS.md), never deletes, and writes
nothing else. A cache whose project is not in the payload is named and skipped.

Single-writer rule: it takes the lock and refuses to run while another run owns
the output tree.

    python scripts/backfill_own_parcels.py --dry-run
    python scripts/backfill_own_parcels.py
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from urtpe.lock import LockHeld, SingleWriterLock  # noqa: E402


def anchor_parcels(project: dict) -> list[str]:
    """The anchor record's parcels, first parcel first."""
    anchor = next((n for n in project.get("nodes") or ()
                   if n.get("recno") == project.get("anchor_recno")),
                  (project.get("nodes") or [{}])[0])
    first = str(anchor.get("first_parcel") or "")
    parcels = [str(p) for p in (anchor.get("parcels") or []) if str(p)]
    return ([first] if first else []) + [p for p in parcels if p != first]


def select(cache_dir: Path) -> list[Path]:
    """Cache directories whose result.json holds view ids."""
    out = []
    for entry in sorted(cache_dir.iterdir()):
        rf = entry / "result.json"
        if not rf.is_file():
            continue
        try:
            data = json.loads(rf.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if data.get("view_verified_case_ids") or data.get("view_rejected"):
            out.append(entry)
    return out


def backfill(cache_dir: Path, projects: dict[str, dict], backup_dir: Path,
             dry_run: bool = False) -> dict:
    """Write own_parcels where it differs. Returns the run report."""
    report = {"candidates": 0, "written": [], "unchanged": [], "no_project": [],
              "no_parcels": []}
    for entry in select(cache_dir):
        report["candidates"] += 1
        rf = entry / "result.json"
        data = json.loads(rf.read_text(encoding="utf-8"))
        pid = str(data.get("project_id") or entry.name)
        project = projects.get(pid)
        if project is None:
            report["no_project"].append(pid)
            continue
        parcels = anchor_parcels(project)
        if not parcels:
            report["no_parcels"].append(pid)
            continue
        if data.get("own_parcels") == parcels:
            report["unchanged"].append(pid)
            continue
        if not dry_run:
            dest = backup_dir / entry.name
            dest.mkdir(parents=True, exist_ok=True)
            shutil.copy2(rf, dest / "result.json")
            data["own_parcels"] = parcels
            rf.write_text(json.dumps(data, ensure_ascii=False, indent=2),
                          encoding="utf-8")
        report["written"].append(pid)
    return report


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--cache", default=str(ROOT / "data" / ".link_cache"))
    ap.add_argument("--payload", default=str(ROOT / "data" / "projects.json"))
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    cache_dir = Path(args.cache)
    if not cache_dir.is_dir():
        print(f"no cache directory at {cache_dir}", file=sys.stderr)
        return 1
    doc = json.loads(Path(args.payload).read_text(encoding="utf-8"))
    projects = {p["project_id"]: p for p in doc["projects"]}

    stamp = time.strftime("%Y%m%d_%H%M%S")
    backup_dir = cache_dir.parent / f".link_cache_backup_{stamp}_ownparcels"

    if args.dry_run:
        report = backfill(cache_dir, projects, backup_dir, dry_run=True)
    else:
        lock = SingleWriterLock(cache_dir.parent)
        try:
            lock.acquire()
        except LockHeld as exc:
            print(f"LOCKED: {exc}", file=sys.stderr)
            return 5
        try:
            report = backfill(cache_dir, projects, backup_dir)
        finally:
            lock.release()

    print(f"candidates (caches holding view ids): {report['candidates']}")
    print(f"{'would write' if args.dry_run else 'wrote'}: {len(report['written'])}")
    print(f"unchanged: {len(report['unchanged'])}")
    for label in ("no_project", "no_parcels"):
        if report[label]:
            print(f"{label} (skipped, named): {report[label]}")
    if report["written"] and not args.dry_run:
        print(f"backup: {backup_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
