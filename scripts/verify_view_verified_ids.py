#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verify view-verified case ids by the city's own case name (§8 viewer-UX wave 3b).

The national view page's 相關連結 assertion was treated as unconditional, so
case ids of OTHER projects entered caches as view-verified and rendered as
nameless 孤 anchors carrying the other project's 建照 / 開工 dates — measured:
10202065 (中山254), 09511211 (大安557, shape B), 09807161 (大安龍泉169),
09608220 (信義犁和102); docs/viewer-UX.md §8, inspection board B7+B8.

This pass runs on every cache holding ``view_verified_case_ids`` — the defect
does not depend on the awaiting state — under the single-writer lock, in two
stages:

1. ``refresh_project`` per cache: re-fetches each case's header (harvesting
   CASE_NAME into ``case_case_names``), then the in-refresh gate decides every
   view-verified id by the §8 decision-1 table.
2. ``offer_rejected_ids`` over the run's rejections: a rejected id whose
   city-name land core matches exactly one other cache joins that cache
   (append-only), ``adopted_from_view`` recorded on the target, the rejection
   backfilled on the source. Zero or multiple matches: no move (never guess).

The run report names every rejected id, every offer, and every label error —
a rejection that vanished silently would read as a complete dataset.

Single-writer rule (AGENTS.md): do not run this while an ingestion or another
sweep owns the cache. Back up the cache dir first:
``cp -r data/.link_cache data/.link_cache_backup_<stamp>_viewgate``.

    python scripts/verify_view_verified_ids.py [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from urtpe.lock import SingleWriterLock, LockHeld  # noqa: E402
from urtpe.links import offer_rejected_ids, refresh_project  # noqa: E402


def select_candidates(cache_dir: Path) -> list[str]:
    """Caches holding view-verified ids — the §8 gate's input set."""
    out: list[str] = []
    for entry in sorted(cache_dir.iterdir()):
        rf = entry / "result.json"
        if not rf.is_file():
            continue
        try:
            data = json.loads(rf.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if data.get("view_verified_case_ids"):
            out.append(str(data.get("project_id") or entry.name))
    return out


def collect_rejections(cache_dir: Path, pids: list[str]) -> dict[str, dict[str, str]]:
    """{source_pid: {case_id: city_case_name}} from the refreshed caches."""
    out: dict[str, dict[str, str]] = {}
    for pid in pids:
        rf = cache_dir / pid / "result.json"
        try:
            data = json.loads(rf.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        rejected = data.get("view_rejected") or {}
        names = data.get("case_case_names") or {}
        for cid, rec in rejected.items():
            # the offer matches on the CITY name, which the refresh persisted;
            # a rejection recorded before the name was harvested has none.
            if rec.get("shape") in ("A", "B") and names.get(cid):
                out.setdefault(pid, {})[cid] = names[cid]
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--cache", default=str(ROOT / "data" / ".link_cache"))
    ap.add_argument("--delay", type=float, default=1.0,
                    help="seconds between projects (the WAF cap)")
    ap.add_argument("--dry-run", action="store_true",
                    help="list the candidates and stop")
    args = ap.parse_args(argv)

    cache_dir = Path(args.cache)
    if not cache_dir.is_dir():
        print(f"no cache directory at {cache_dir}", file=sys.stderr)
        return 1

    candidates = select_candidates(cache_dir)
    print(f"candidates (caches holding view-verified ids): {len(candidates)}")
    if args.dry_run:
        for pid in candidates:
            print(f"  {pid}")
        return 0

    lock = SingleWriterLock(cache_dir.parent)
    try:
        lock.acquire()
    except LockHeld as exc:
        print(f"LOCKED: {exc}", file=sys.stderr)
        return 5
    try:
        failures = 0
        rejected_ids: list[str] = []
        label_errors: list[str] = []
        not_confirmed: list[str] = []
        for i, pid in enumerate(candidates):
            if i:
                time.sleep(args.delay)
            report = refresh_project(cache_dir, pid)
            if report.get("error"):
                failures += 1
                print(f"  FAILED {pid}: {report['error']}", file=sys.stderr)
                continue
            for cid in report.get("view_rejected_ids") or []:
                rec = "?"
                try:
                    rec = (json.loads(
                        (cache_dir / pid / "result.json").read_text(encoding="utf-8")
                    )["view_rejected"][cid]["reason"])
                except (OSError, ValueError, KeyError):
                    pass
                rejected_ids.append((pid, cid, rec))
                print(f"  {pid}: REJECTED {cid} — {rec}")
            for cid in report.get("view_label_errors") or []:
                label_errors.append((pid, cid))
                print(f"  {pid}: LABEL ERROR (accepted) {cid} — the 相關連結 label "
                      f"names another project; the city's own case name matches")
            for cid in report.get("view_not_confirmed") or []:
                not_confirmed.append((pid, cid))
                print(f"  {pid}: NOT CONFIRMED {cid} — no city case name; the id stays")

        # ── the offer step: move each rejection to its owning project ──────
        moves = offer_rejected_ids(cache_dir, collect_rejections(cache_dir, candidates))
        for src, target, cid in moves:
            print(f"  OFFERED {cid}: {src} -> {target} (adopted_from_view recorded)")

        print(f"\n{len(candidates)} project(s) verified; {len(rejected_ids)} rejection(s); "
              f"{len(moves)} offer(s); {len(label_errors)} label error(s) accepted; "
              f"{len(not_confirmed)} not confirmed; {failures} failure(s)")
        return 1 if failures else 0
    finally:
        lock.release()


if __name__ == "__main__":
    sys.exit(main())
