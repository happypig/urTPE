"""Inspect the link-discovery cache (data/.link_cache).

Prints each fallback-mapped land_core -> view_id (data/taipei_case_ids.json),
then parses the cached national portal view pages for case ids and推演歷史
milestones. Cache filenames follow urtpe.links.fetch_url: the URL with every
non-alphanumeric character replaced by "_", plus ".html".
"""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from urtpe.links import (
    VIEW_URL_BASE,
    extract_case_ids_from_view,
    extract_taipei_stage_process,
    extract_tuidui_history_from_view,
)

CACHE_DIR = Path("data/.link_cache")
MAPPING_FILE = Path("data/taipei_case_ids.json")


def cache_file_for(url: str) -> Path:
    safe_name = re.sub(r"[^a-zA-Z0-9]", "_", url)
    return CACHE_DIR / f"{safe_name}.html"


def main() -> None:
    mapping = {}
    if MAPPING_FILE.exists():
        mapping = json.loads(MAPPING_FILE.read_text(encoding="utf-8"))

    print("=== FALLBACK MAPPINGS ===")
    entries = []
    for land_core, info in sorted(mapping.items()):
        view_id = info.get("view_id", "")
        cached = cache_file_for(f"{VIEW_URL_BASE}{view_id}") if view_id else None
        in_cache = cached.exists() if cached else False
        print(f"  {land_core} -> view_id: {view_id}{'  [cached]' if in_cache else ''}")
        if in_cache:
            entries.append((cached, view_id))

    print("\n=== NATIONAL PORTAL VIEW PAGES ===")
    for f, view_id in entries:
        html = f.read_text(encoding="utf-8")
        case_ids = extract_case_ids_from_view(html)
        milestones = extract_tuidui_history_from_view(html)
        print(f"  View {view_id}: case_ids={case_ids}")
        print(f"    Milestones: {milestones}")
        stages = extract_taipei_stage_process(html)
        for case_id in case_ids:
            if case_id in stages:
                print(f"  Case {case_id}: {stages[case_id]}")
            else:
                print(f"  Case {case_id}: (no stages found)")


if __name__ == "__main__":
    main()
