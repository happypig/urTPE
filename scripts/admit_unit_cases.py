"""Admit a case the city search refused, when the single count rule accepts it.

unit-count-rule (docs/inspection-batchF.md F7 addendum, D2). Discovery's search
guard dropped these cases into a cache's `search_rejected` before the cache knew
the unit's own parcels. A name that declares the unit's own district+section, one
of its own parcels, and a count the unit had at some approval (`own_counts`) passes
`unit_accepts_case_name`; if no payload project holds the id and the project did
not record it in `view_rejected`, the case joins the project's cache in place
(header and milestones read live: two read-only requests per admitted case).

The dry run (default) lists the ids it would admit and issues NO request. With
`--apply` the script takes the single-writer lock, copies every `result.json` it
changes into a dated backup directory first, and paces one request per second.
`search_rejected` is left as recorded. Re-emit afterwards with the normal CLI.

    python scripts/admit_unit_cases.py
    python scripts/admit_unit_cases.py --apply
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from urtpe import links  # noqa: E402
from urtpe.links import DiscoveryResult  # noqa: E402
from urtpe.lock import LockHeld, SingleWriterLock  # noqa: E402


def _read(rf: Path):
    try:
        return json.loads(rf.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def run(cache_dir: Path, projects: dict, backup_dir: Path, *, apply: bool = False,
        fetch_header=None, fetch_milestones=None, sleep=None,
        delay: float = 1.0) -> dict:
    """Admit the passing `search_rejected` cases. Returns the run report."""
    if fetch_header is None:
        fetch_header = links.fetch_taipei_case_header_api
    if fetch_milestones is None:
        fetch_milestones = links.fetch_taipei_milestones_api
    if sleep is None:
        sleep = time.sleep
    report: dict = {"plan": {}, "admitted": {}, "written": [], "errors": {},
                    "no_project": [], "requests": 0}
    entries = []
    held: set[str] = set()                      # ids any payload project holds
    for entry in sorted(cache_dir.iterdir()):
        data = _read(entry / "result.json")
        if data is None:
            continue
        pid = str(data.get("project_id") or entry.name)
        if pid not in projects:
            report["no_project"].append(pid)
            continue
        entries.append((entry, pid, data))
        held |= {str(c) for c in data.get("city_case_ids") or []}

    for entry, pid, data in entries:
        disc = DiscoveryResult(**data)
        ids = [cid for cid, name in (disc.search_rejected or {}).items()
               if isinstance(name, str) and cid not in held
               and cid not in (disc.view_rejected or {})
               and links.unit_accepts_case_name(disc.land_core, name, disc.own_parcels,
                                                disc.own_counts)]
        ids.sort()
        if not ids:
            continue
        if not apply:
            report["plan"][pid] = ids
            continue
        before = asdict(disc)
        for cid in ids:
            sleep(delay)
            report["requests"] += 1
            try:
                row = fetch_header(cid) or {}
            except Exception:
                report["errors"].setdefault(pid, []).append(cid)
                continue
            name = str(row.get("CASE_NAME", "") or "").strip()
            if not name or not links.unit_accepts_case_name(
                    disc.land_core, name, disc.own_parcels, disc.own_counts):
                continue                        # the header does not confirm it
            sleep(delay)
            report["requests"] += 1
            try:
                ms = fetch_milestones(cid) or {}
            except Exception:
                report["errors"].setdefault(pid, []).append(cid)
                continue
            links._join_unit_case(disc, cid, name, row, ms)
            held.add(cid)
            report["admitted"].setdefault(pid, []).append(cid)
        if asdict(disc) != before:
            dest = backup_dir / entry.name
            dest.mkdir(parents=True, exist_ok=True)
            shutil.copy2(entry / "result.json", dest / "result.json")
            (entry / "result.json").write_text(
                json.dumps(asdict(disc), ensure_ascii=False, indent=2), encoding="utf-8")
            report["written"].append(pid)
    return report


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--cache", default=str(ROOT / "data" / ".link_cache"))
    ap.add_argument("--payload", default=str(ROOT / "data" / "projects.json"))
    ap.add_argument("--apply", action="store_true",
                    help="read header and milestones live, write the caches "
                         "(default: dry run, no request)")
    args = ap.parse_args(argv)

    cache_dir = Path(args.cache)
    if not cache_dir.is_dir():
        print(f"no cache directory at {cache_dir}", file=sys.stderr)
        return 1
    doc = json.loads(Path(args.payload).read_text(encoding="utf-8"))
    projects = {p["project_id"]: p for p in doc["projects"]}
    backup_dir = cache_dir.parent / f".link_cache_backup_{time.strftime('%Y%m%d_%H%M%S')}_admitcases"

    if not args.apply:
        report = run(cache_dir, projects, backup_dir, apply=False)
        n = sum(len(v) for v in report["plan"].values())
        print(f"dry run: {n} cases to admit in {len(report['plan'])} projects "
              "(no request issued)")
        for pid, ids in report["plan"].items():
            print(f"  {pid}: {' '.join(ids)}")
        return 0

    lock = SingleWriterLock(cache_dir.parent)
    try:
        lock.acquire()
    except LockHeld as exc:
        print(f"LOCKED: {exc}", file=sys.stderr)
        return 5
    try:
        report = run(cache_dir, projects, backup_dir, apply=True)
    finally:
        lock.release()
    print(f"requests: {report['requests']}")
    print(f"admitted: {sum(len(v) for v in report['admitted'].values())} "
          f"in {len(report['admitted'])} projects; written: {len(report['written'])}")
    for pid, ids in report["admitted"].items():
        print(f"  + {pid}: {' '.join(ids)}")
    for pid, ids in report["errors"].items():
        print(f"  ! {pid} not admitted (retry): {' '.join(ids)}")
    if report["written"]:
        print(f"backup: {backup_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
