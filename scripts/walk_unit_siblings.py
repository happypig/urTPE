"""Walk the id stems of each unit's held cases and add the sibling cases found.

unit-sibling-id-walk (docs/inspection-batchF.md F4, D3 = A, D4 = A). A city case
id is a filing day's 7-digit stem plus one digit, so a unit's cases sit in the
stems it already holds. For every payload project this probes each id strictly
between the lowest and highest held digit of a stem (not held, not held by
another project, not probed before) by its case header, and joins a case to the
project only when its own case name passes `unit_accepts_case_name`.

The dry run (default) lists the ids it would probe and issues NO request. With
`--apply` the script takes the single-writer lock, copies every `result.json` it
changes into a dated backup directory first, paces one request per second, and
stops at `--max-requests` (default 80; the F4 pass measured 63). The emission
path never runs this: re-emit afterwards with the normal CLI.

    python scripts/walk_unit_siblings.py
    python scripts/walk_unit_siblings.py --apply
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


def _read(rf: Path) -> dict | None:
    try:
        return json.loads(rf.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def run(cache_dir: Path, projects: dict[str, dict], backup_dir: Path, *,
        apply: bool = False, max_requests: int | None = 80,
        fetch_header=None, fetch_milestones=None, sleep=None,
        delay: float = 1.0) -> dict:
    """Walk every payload project's cache. Returns the run report."""
    report: dict = {"plan": {}, "written": [], "added": {}, "refused": {},
                    "errors": {}, "no_project": [], "requests": 0, "capped": False}
    entries = []
    held_by: dict[str, set[str]] = {}          # case id -> payload projects holding it
    for entry in sorted(cache_dir.iterdir()):
        data = _read(entry / "result.json")
        if data is None:
            continue
        pid = str(data.get("project_id") or entry.name)
        if pid not in projects:
            report["no_project"].append(pid)
            continue
        entries.append((entry, pid, data))
        for cid in data.get("city_case_ids") or []:
            held_by.setdefault(str(cid), set()).add(pid)

    for entry, pid, data in entries:
        elsewhere = {c for c, owners in held_by.items() if owners - {pid}}
        disc = DiscoveryResult(**data)
        if not apply:
            ids = links.sibling_candidates(disc, held_elsewhere=elsewhere)
            if ids:
                report["plan"][pid] = ids
            continue
        remaining = None if max_requests is None else max_requests - report["requests"]
        if remaining is not None and remaining <= 0:
            report["capped"] = True
            break
        before = asdict(disc)
        rep = links.walk_unit_siblings(
            disc, disc.land_core, disc.own_parcels, held_elsewhere=elsewhere,
            fetch_header=fetch_header, fetch_milestones=fetch_milestones,
            sleep=sleep, delay=delay, max_requests=remaining)
        report["requests"] += rep["requests"]
        if rep["added"]:
            report["added"][pid] = rep["added"]
        if rep["other_unit"]:
            report["refused"][pid] = {c: rep["names"].get(c, "") for c in rep["other_unit"]}
        if rep["errors"]:
            report["errors"][pid] = rep["errors"]
        if asdict(disc) != before:
            dest = backup_dir / entry.name
            dest.mkdir(parents=True, exist_ok=True)
            shutil.copy2(entry / "result.json", dest / "result.json")
            (entry / "result.json").write_text(
                json.dumps(asdict(disc), ensure_ascii=False, indent=2), encoding="utf-8")
            report["written"].append(pid)
        if rep["capped"]:
            report["capped"] = True
            break
    return report


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--cache", default=str(ROOT / "data" / ".link_cache"))
    ap.add_argument("--payload", default=str(ROOT / "data" / "projects.json"))
    ap.add_argument("--apply", action="store_true",
                    help="probe live, write the caches (default: dry run, no request)")
    ap.add_argument("--max-requests", type=int, default=80)
    args = ap.parse_args(argv)

    cache_dir = Path(args.cache)
    if not cache_dir.is_dir():
        print(f"no cache directory at {cache_dir}", file=sys.stderr)
        return 1
    doc = json.loads(Path(args.payload).read_text(encoding="utf-8"))
    projects = {p["project_id"]: p for p in doc["projects"]}
    backup_dir = cache_dir.parent / f".link_cache_backup_{time.strftime('%Y%m%d_%H%M%S')}_siblingwalk"

    if not args.apply:
        report = run(cache_dir, projects, backup_dir, apply=False)
    else:
        lock = SingleWriterLock(cache_dir.parent)
        try:
            lock.acquire()
        except LockHeld as exc:
            print(f"LOCKED: {exc}", file=sys.stderr)
            return 5
        try:
            report = run(cache_dir, projects, backup_dir, apply=True,
                         max_requests=args.max_requests)
        finally:
            lock.release()

    if not args.apply:
        n = sum(len(v) for v in report["plan"].values())
        print(f"dry run: {n} ids to probe in {len(report['plan'])} projects (no request issued)")
        for pid, ids in report["plan"].items():
            print(f"  {pid}: {' '.join(ids)}")
    else:
        print(f"requests: {report['requests']}  capped: {report['capped']}")
        print(f"added: {sum(len(v) for v in report['added'].values())} "
              f"in {len(report['added'])} projects; written: {len(report['written'])}")
        for pid, ids in report["added"].items():
            print(f"  + {pid}: {' '.join(ids)}")
        for pid, names in report["refused"].items():
            for cid, name in names.items():
                print(f"  - {pid} {cid} other unit: {name}")
        for pid, ids in report["errors"].items():
            print(f"  ! {pid} not recorded (retry): {' '.join(ids)}")
        if report["written"]:
            print(f"backup: {backup_dir}")
    if report["no_project"]:
        print(f"no payload project (skipped, named): {len(report['no_project'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
