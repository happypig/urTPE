"""§6.8 re-merge pass: refresh per-project link caches after the search guard.

Deletes each project's cached result.json (keeps portal_index.json and cached
view.html), then re-runs Taipei-first discovery so the §6.7/§6.8 parcel guard
decides which cases enter city_case_ids. Per-project caching makes the run
resumable — rerun after an interruption to continue where it stopped.

Usage: python scripts/regen_links_2026_08_26.py [delay_seconds]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from urtpe.cli import _load_projects_from_js
from urtpe.links import LinksDiscovery

DELAY = float(sys.argv[1]) if len(sys.argv) > 1 else 0.25
CACHE = Path("data/.link_cache")
SOURCE_JS = "viewer/projects.data.js"


def main() -> None:
    projects, _meta = _load_projects_from_js(SOURCE_JS)
    cleared = 0
    for d in CACHE.iterdir():
        rf = d / "result.json"
        if rf.exists():
            rf.unlink()
            cleared += 1
    print(f"cleared {cleared} result.json caches; regenerating...", flush=True)

    discovery = LinksDiscovery(cache_dir=str(CACHE), delay=DELAY)
    results = discovery.run(projects)
    resolved = sum(1 for r in results.values() if r.status != "unresolved")
    unresolved = sum(1 for r in results.values() if r.status == "unresolved")
    errors = sum(1 for r in results.values() if r.status == "error")
    print(f"done: {len(results)} projects, {resolved} resolved, "
          f"{unresolved} unresolved, {errors} errors", flush=True)


if __name__ == "__main__":
    main()
