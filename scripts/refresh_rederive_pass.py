#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The D9g step 2 cache pass: re-derive, re-fetch, label (D7 + D8 + D13).

Refreshes every project cache through the standing ``refresh_project``, which
now (a) re-derives the merged milestone projection, (b) re-fetches the
implementation layer for the cases that lack it, and (c) labels a case the
city emptied as 無.

The pass writes into ``data/.link_cache/`` only. The tracked datasets are
emitted once, afterwards, through the standing ``--from-js`` path.

Single-writer rule (AGENTS.md): the pass takes the lock, and it must not run
while another session writes the same tree.

    python scripts/refresh_rederive_pass.py [--dry-run] [--limit N]
        [--delay 1.0] [--report PATH]

The report names, for every project it touched: the cases labelled 無, the
implementation cases it re-fetched, and the projection change. The before/after
payload sizes of the named projects are printed, so a shrink is visible.
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
    load_project_cache,
    refresh_project,
)
from urtpe.lock import SingleWriterLock  # noqa: E402

# The projects the board names for the before/after payload sizes.
NAMED = [
    "萬華區-青年段一小段-130地號等3筆",
    "信義區-虎林段四小段-38地號等138筆",
    "信義區-雅祥段一小段-227-4地號等10筆",
    "北投區-立農段五小段-163-2地號等4筆",
    "萬華區-萬華段二小段-894地號等22筆",
    "中山區-吉林段四小段-705-3地號等14筆",
]


def payload_sizes(cache_dir: Path, pid: str) -> dict:
    """The project's payload sizes, before or after the refresh."""
    cached = load_project_cache(cache_dir, pid)
    if cached is None:
        return {}
    impl = cached.implementation or {}
    rew = cached.rewards or {}
    return {
        "implementation_cases": len(impl),
        "implementation_keys": sum(len(v or {}) for v in impl.values()),
        "reward_cases": len(rew),
        "reward_keys": sum(len(v or {}) for v in rew.values()),
        "per_case": {cid: {"impl": len(p or {}), "rew": len((cached.rewards or {}).get(cid) or {})}
                     for cid, p in impl.items()},
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--cache", default=str(ROOT / "data" / ".link_cache"))
    ap.add_argument("--out", default=str(ROOT / "data" / ".link_cache"))
    ap.add_argument("--dry-run", action="store_true",
                    help="read only: report the scope, touch nothing")
    ap.add_argument("--limit", type=int, default=0,
                    help="refresh at most N projects (0 = all)")
    ap.add_argument("--delay", type=float, default=1.0,
                    help="seconds between requests (the WAF cap)")
    ap.add_argument("--report", default=str(ROOT / "data" / "refresh_rederive_report.json"))
    args = ap.parse_args(argv)

    cache_dir = Path(args.cache)
    out_dir = Path(args.out)
    pids = sorted(d.name for d in cache_dir.iterdir()
                  if d.is_dir() and (d / "result.json").is_file())
    if args.limit:
        pids = pids[: args.limit]

    before_named = {pid: payload_sizes(cache_dir, pid) for pid in NAMED}

    if args.dry_run:
        print(f"would refresh {len(pids)} project caches in {out_dir}")
        for pid in NAMED:
            print(f"  {pid}: {json.dumps(before_named[pid], ensure_ascii=False)}")
        return 0

    out_dir.mkdir(parents=True, exist_ok=True)
    report = {"projects": [], "labelled_wu": [], "implementation_refetched": [],
              "projection_changed": [], "errors": []}
    with SingleWriterLock(out_dir):
        for i, pid in enumerate(pids, 1):
            try:
                r = refresh_project(out_dir, pid)
            except Exception as exc:
                report["errors"].append({"project_id": pid,
                                         "error": f"{type(exc).__name__}: {exc}"})
                print(f"  FAILED {pid}: {type(exc).__name__}: {exc}", file=sys.stderr)
                continue
            err = r.get("error") or ""
            if err:
                report["errors"].append({"project_id": pid, "error": err})
                print(f"  ERROR {pid}: {err}", file=sys.stderr)
            wu = r.get("labelled_wu") or []
            impl = r.get("implementation_refetched") or []
            if wu:
                report["labelled_wu"].append({"project_id": pid, "cases": wu})
            if impl:
                report["implementation_refetched"].append(
                    {"project_id": pid, "cases": impl})
            report["projects"].append({
                "project_id": pid,
                "labelled_wu": wu,
                "implementation_refetched": impl,
                "status_changes": r.get("status_changes") or [],
            })
            if wu or impl:
                print(f"[{i}/{len(pids)}] {pid}")
                for cid in wu:
                    print(f"    無: {cid}")
                for row in impl:
                    print(f"    impl refetched: {row['case_id']} "
                          f"({row.get('implementation_keys', 0)} keys)")
            if i % 25 == 0:
                print(f"  ... {i}/{len(pids)}", file=sys.stderr)

    after_named = {pid: payload_sizes(out_dir, pid) for pid in NAMED}
    print()
    print("=== the named projects: before and after ===")
    for pid in NAMED:
        b, a = before_named.get(pid, {}), after_named.get(pid, {})
        print(f"{pid}")
        print(f"   before: impl cases={b.get('implementation_cases')} "
              f"keys={b.get('implementation_keys')} "
              f"rew cases={b.get('reward_cases')} keys={b.get('reward_keys')}")
        print(f"   after:  impl cases={a.get('implementation_cases')} "
              f"keys={a.get('implementation_keys')} "
              f"rew cases={a.get('reward_cases')} keys={a.get('reward_keys')}")
    print()
    print("cases labelled 無:", sum(len(x["cases"]) for x in report["labelled_wu"]))
    for x in report["labelled_wu"]:
        print("   %s: %s" % (x["project_id"], ", ".join(x["cases"])))
    print("implementation cases re-fetched:",
          sum(len(x["cases"]) for x in report["implementation_refetched"]))
    print("errors:", len(report["errors"]))
    for e in report["errors"][:20]:
        print("   ", e)

    Path(args.report).write_text(json.dumps(report, ensure_ascii=False, indent=2),
                                 encoding="utf-8")
    print()
    print("report written to", args.report)
    return 1 if report["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
