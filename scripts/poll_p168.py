#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Poll the city's 168 fast-track case list, and detect a change by hash.

Acquisition only. This NEVER ingests and NEVER writes `data/.link_cache/` —
the same rule the gazette poller follows (AGENTS.md: "Acquisition is separate
from ingestion").

What it does:
  - fetches the 168 list (`Get_project168.ashx`) — one request, sized by the
    `TotalCount` the endpoint reports (its paging is broken: with
    `pageSize=50` each page advances by exactly ONE row, so a paged walk
    gathers 90 of the 466 rows in 40 requests);
  - writes a snapshot under `urtpe-gazettes/p168_snapshots/`, named by the
    content hash;
  - compares the hash with the previous snapshot's, and reports whether the
    list CHANGED.

Change detection is by content hash, never by the platform's timestamp — the
same rule the gazette poller follows.

    python scripts/poll_p168.py [--archive-root PATH] [--dry-run] [--json]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from urtpe.links import fetch_taipei_168_list_api  # noqa: E402

SNAPSHOT_DIRNAME = "p168_snapshots"
STATE_NAME = "p168_state.json"
LOG_NAME = "p168_log.jsonl"


def _archive_root(arg: str | None) -> Path:
    if arg:
        return Path(arg)
    from urtpe.archive import DEFAULT_ARCHIVE_ROOT
    return Path(DEFAULT_ARCHIVE_ROOT)


def _canonical(rows: list[dict]) -> str:
    """The list's canonical form: the rows as they are, sorted by case id.

    The sort makes the hash a property of the CONTENT, not of the order the
    endpoint happened to return.
    """
    return json.dumps(sorted(rows, key=lambda r: str(r.get("case_id") or "")),
                      ensure_ascii=False, sort_keys=True)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--archive-root", default=None,
                    help="archive directory (default: the configured archive root)")
    ap.add_argument("--dry-run", action="store_true",
                    help="report whether the list changed without writing a snapshot")
    ap.add_argument("--json", action="store_true", help="print the outcome as JSON")
    args = ap.parse_args(argv)

    root = _archive_root(args.archive_root)
    snap_dir = root / SNAPSHOT_DIRNAME
    state_path = root / STATE_NAME
    log_path = root / LOG_NAME

    rows = fetch_taipei_168_list_api()
    if not rows:
        print("[WARN] the 168 list came back empty — the fetch failed or the "
              "endpoint changed", file=sys.stderr)
        return 1
    body = _canonical(rows)
    digest = hashlib.sha256(body.encode("utf-8")).hexdigest()

    previous = ""
    if state_path.is_file():
        try:
            previous = json.loads(state_path.read_text(encoding="utf-8")).get("sha256", "")
        except (json.JSONDecodeError, OSError):
            previous = ""
    changed = bool(previous) and previous != digest

    out = {
        "rows": len(rows),
        "sha256": digest,
        "previous_sha256": previous,
        "changed": changed,
        "first_seen": not previous,
        "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "dry_run": bool(args.dry_run),
    }

    if not args.dry_run:
        snap_dir.mkdir(parents=True, exist_ok=True)
        snap = snap_dir / f"p168-{digest[:16]}.json"
        if not snap.is_file():
            snap.write_text(json.dumps(rows, ensure_ascii=False, indent=1),
                            encoding="utf-8")
        state_path.write_text(json.dumps(out, ensure_ascii=False, indent=2),
                              encoding="utf-8")
        with log_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(out, ensure_ascii=False) + "\n")
        out["snapshot"] = str(snap)

    if args.json:
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        print("168 list check: %d rows" % out["rows"])
        print("  sha256 : %s" % digest[:16])
        if out["first_seen"]:
            print("  status : first snapshot (no previous hash to compare)")
        elif changed:
            print("  status : CHANGED — the list moved since the last check")
        else:
            print("  status : unchanged")
        if out.get("snapshot"):
            print("  snapshot: %s" % out["snapshot"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
