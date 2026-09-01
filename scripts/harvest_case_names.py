"""Backfill candidate case_names into per-project caches (scheduled operation).

Makes one platform-search call per project (the same §6.7/§6.8-guarded search
discovery uses) and merges the returned {case_id: case_name} into the cached
result.json's `candidate_names`. Run this SEPARATELY from discovery/other
crawls: the search endpoint's rate-limit profile differs from the discovery
JSON APIs, so pacing lives here and defaults conservatively (1.0s).

Resumable: projects whose cache already carries non-empty candidate_names are
skipped unless --force. NEVER pass --fresh anywhere near this.

Usage:
  python scripts/harvest_case_names.py [--pid PROJECT_ID] [--delay 1.0] [--force]
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from urtpe.cli import _load_projects_from_js
from urtpe.links import search_taipei_cases_api

CACHE = Path("data/.link_cache")
SOURCE_JS = "viewer/projects.data.js"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--pid", default="", help="harvest a single project_id")
    parser.add_argument("--delay", type=float, default=1.0,
                        help="seconds between search calls (default 1.0)")
    parser.add_argument("--force", action="store_true",
                        help="re-harvest even when candidate_names already present")
    args = parser.parse_args()

    projects, _meta = _load_projects_from_js(SOURCE_JS)
    if args.pid:
        projects = [p for p in projects if p.project_id == args.pid]
        if not projects:
            sys.exit(f"project not found: {args.pid}")

    done = skipped = missing = failed = 0
    for i, project in enumerate(projects, 1):
        rf = CACHE / project.project_id / "result.json"
        if not rf.is_file():
            missing += 1
            continue
        data = json.loads(rf.read_text(encoding="utf-8"))
        if data.get("candidate_names") and not args.force:
            skipped += 1
            continue

        anchor = next(m for m in project.members if m.recno == project.anchor_recno)
        try:
            entries = search_taipei_cases_api(anchor.section, anchor.first_parcel)
        except Exception as e:
            print(f"  FAIL {project.project_id}: {e}", flush=True)
            failed += 1
            time.sleep(args.delay)
            continue

        names = {e["case_id"]: e.get("case_name", "")
                 for e in entries if e.get("case_id")}
        data["candidate_names"] = names
        rf.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        done += 1
        if i % 50 == 0 or args.pid:
            print(f"[{i}/{len(projects)}] {project.project_id}: {len(names)} names", flush=True)
        time.sleep(args.delay)

    print(f"harvested: {done} · skipped(resumed): {skipped} · "
          f"no-cache: {missing} · failed: {failed}")


if __name__ == "__main__":
    main()
