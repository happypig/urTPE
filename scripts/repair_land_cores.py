"""Repair a cache's `land_core` that disagrees with its project id.

docs/inspection-batchF.md F5 (D5 = C, part A). A unit's project id is the slug of
its land core: `{district}-{section}-{first parcel}地號等{count}筆`, so the core is
the id's three parts joined. Three payload caches held another core: 市府220-2
reads 中正區 (the project is 大同區), and 寶清51-13 and 崇仁新村711-3 lack
`地號等N筆`. The §8 gate decides a case by that field, so a district typo refused
`09609301`, a correct case.

The script rewrites the field from the id, for payload projects whose id has the
unit-id shape. It copies each `result.json` it changes into a dated backup first,
never deletes, touches no other field, and names every cache it skips (no payload
project, or an id that is not a unit id: a `-2` twin, `未解析-N`, `地號等?筆`).

Single-writer rule: it takes the lock and refuses to run while another run owns
the output tree.

    python scripts/repair_land_cores.py --dry-run
    python scripts/repair_land_cores.py
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from urtpe.lock import LockHeld, SingleWriterLock  # noqa: E402

_UNIT_ID = re.compile(r"^(.+?區)-([^-]+)-(\d[\d-]*地號等\d+筆)$")


def expected_core(project_id: str) -> str:
    """The land core a unit id spells, or "" when the id is not a unit id."""
    m = _UNIT_ID.match(project_id or "")
    return "".join(m.groups()) if m else ""


def repair(cache_dir: Path, projects: dict, backup_dir: Path,
           dry_run: bool = False) -> dict:
    """Rewrite land_core where it differs. Returns the run report."""
    report = {"written": {}, "unchanged": [], "no_project": [], "no_unit_id": []}
    for entry in sorted(cache_dir.iterdir()):
        rf = entry / "result.json"
        if not rf.is_file():
            continue
        try:
            data = json.loads(rf.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        pid = str(data.get("project_id") or entry.name)
        if pid not in projects:
            report["no_project"].append(pid)
            continue
        want = expected_core(pid)
        if not want:
            report["no_unit_id"].append(pid)
            continue
        have = data.get("land_core")
        if have == want:
            report["unchanged"].append(pid)
            continue
        report["written"][pid] = [have, want]
        if not dry_run:
            dest = backup_dir / entry.name
            dest.mkdir(parents=True, exist_ok=True)
            shutil.copy2(rf, dest / "result.json")
            data["land_core"] = want
            rf.write_text(json.dumps(data, ensure_ascii=False, indent=2),
                          encoding="utf-8")
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
    backup_dir = cache_dir.parent / f".link_cache_backup_{time.strftime('%Y%m%d_%H%M%S')}_landcore"

    if args.dry_run:
        report = repair(cache_dir, projects, backup_dir, dry_run=True)
    else:
        lock = SingleWriterLock(cache_dir.parent)
        try:
            lock.acquire()
        except LockHeld as exc:
            print(f"LOCKED: {exc}", file=sys.stderr)
            return 5
        try:
            report = repair(cache_dir, projects, backup_dir)
        finally:
            lock.release()

    print(f"{'would write' if args.dry_run else 'wrote'}: {len(report['written'])}")
    for pid, (old, new) in report["written"].items():
        print(f"  {pid}: {old!r} -> {new!r}")
    print(f"unchanged: {len(report['unchanged'])}")
    for label in ("no_project", "no_unit_id"):
        if report[label]:
            print(f"{label} (skipped, named): {len(report[label])}")
    if report["written"] and not args.dry_run:
        print(f"backup: {backup_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
