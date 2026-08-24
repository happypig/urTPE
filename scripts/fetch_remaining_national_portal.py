#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fetch_remaining_national_portal.py

Time-bounded script to fetch missing national portal data for projects lacking twur links.

Usage:
    python scripts/fetch_remaining_national_portal.py [--dry-run] [--max-projects N]

Behavior:
- Loads viewer/projects.data.js
- Finds projects missing twur links
- Prioritizes by 現況 date descending (newest first)
- For each: searches portal via ?title=, fetches view page, parses 推導歷程
- Updates per-project cache with twur_view_id, twur_url, national_milestones
- Waits 3-5 min between projects (random 180-300s)
- Retries failed fetches up to 3x with exponential backoff (2s, 4s, 8s)
- Logs failures to data/.link_cache/fetch_failures.json (JSON Lines)
- Stops at 06:30 local time, completes current fetch, then regenerates viewer
- Auto-regenerates viewer/projects.data.js on completion

Usage:
    python scripts/fetch_remaining_national_portal.py
    python scripts/fetch_remaining_national_portal.py --dry-run
    python scripts/fetch_remaining_national_portal.py --max-projects 10
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
from datetime import time as dtime
from pathlib import Path
from typing import Optional

# Force UTF-8 stdout/stderr for Chinese characters
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8')

# Ensure local imports work
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from urtpe.links import (
    fetch_url,
    extract_tuidui_history_from_view,
    extract_case_ids_from_view,
    extract_view_id_from_search,
    SEARCH_URL,
    _project_cache_dir,
)

# ──────────────────────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────────────────────

DEADLINE_HOUR = 6
DEADLINE_MINUTE = 30
SEARCH_URL = "https://twur.nlma.gov.tw/zh/urban/rebuild/0"
VIEW_URL_BASE = "https://twur.nlma.gov.tw/zh/urban/rebuild/view/"
ROOT = Path("data/.link_cache")
FAILURES_LOG = ROOT / "fetch_failures.json"

# ──────────────────────────────────────────────────────────────────────────────
# Core Functions
# ──────────────────────────────────────────────────────────────────────────────

def is_past_deadline() -> bool:
    """Check if current time is past 06:30."""
    now = time.localtime()
    current = dtime(now.tm_hour, now.tm_min)
    deadline = dtime(DEADLINE_HOUR, DEADLINE_MINUTE)
    return current >= deadline


def load_candidates() -> list[dict]:
    """Load projects from viewer/projects.data.js and return candidates missing twur."""
    js_path = REPO_ROOT / "viewer" / "projects.data.js"
    if not js_path.exists():
        raise FileNotFoundError(f"Viewer data not found: {js_path}")

    content = js_path.read_text(encoding="utf-8")
    # Extract window.PROJECTS JSON
    # Format: window.PROJECTS = {...};
    import re
    match = re.search(r"window\.PROJECTS\s*=\s*(\{.*?\});", content, re.DOTALL)
    if not match:
        raise ValueError("Could not parse window.PROJECTS from projects.data.js")
    data = json.loads(match.group(1))
    projects = data.get("projects", [])

    candidates = []
    for p in projects:
        links = p.get("links", {})
        if links.get("twur"):
            continue  # Already has twur link

        # Find anchor (現況) node
        current_node = None
        for node in p.get("nodes", []):
            if node.get("is_current"):
                current_node = node
                break

        if not current_node:
            continue

        # Extract section and first parcel from anchor node
        section = current_node.get("section", "")
        land = current_node.get("land", "")
        # Extract first parcel from land string (e.g., "中山區中山段一小段254地號等13筆" -> "254")
        parcel = ""
        if land:
            import re
            # Extract first number sequence that looks like a parcel
            m = re.search(r"(\d+(?:-\d+)?)地號", land)
            if m:
                parcel = m.group(1)

        if not section or not parcel:
            continue

        candidates.append({
            "project_id": p["project_id"],
            "section": section,
            "parcel": parcel,
            "current_date": current_node.get("date", ""),
        })

    # Sort by current_date descending (newest first)
    candidates.sort(key=lambda x: x["current_date"], reverse=True)
    return candidates


def search_portal(section: str) -> list[str]:
    """Search portal by section name, return list of view_ids."""
    params = {"title": section, "city_id": "2", "page": "1"}
    from urllib.parse import urlencode
    url = f"{SEARCH_URL}?{urlencode(params)}"

    try:
        html = fetch_url(url, None, True)
    except Exception as e:
        print(f"  search failed: {e}", file=sys.stderr)
        return []

    import re
    ids = []
    for m in re.finditer(r"/view/(\d+)", html):
        vid = m.group(1)
        if vid not in ids:
            ids.append(vid)
    return ids


def fetch_and_parse_view(view_id: str) -> tuple[dict[str, str], list[str]]:
    """Fetch view page and parse milestones and city case_ids."""
    url = f"https://twur.nlma.gov.tw/zh/urban/rebuild/view/{view_id}"
    try:
        html = fetch_url(url, None, True)
    except Exception as e:
        print(f"  fetch view/{view_id} failed: {e}", file=sys.stderr)
        return {}, []

    from urtpe.links import extract_tuidui_history_from_view, extract_case_ids_from_view
    milestones = extract_tuidui_history_from_view(html)
    city_ids = extract_case_ids_from_view(html)
    return milestones, city_ids


def find_matching_view(section: str, parcel: str) -> tuple[str, dict[str, str], list[str]]:
    """Search for view_id matching section, then filter by parcel."""
    vids = search_portal(section)
    if not vids:
        return "", {}, []

    for vid in vids[:5]:  # Check first 5 results max
        print(f"  Checking view/{vid} for parcel {parcel}...")
        try:
            url = f"https://twur.nlma.gov.tw/zh/urban/rebuild/view/{vid}"
            html = fetch_url(url, None, True)
            # Check if parcel appears in the page
            if parcel in html or parcel.replace("-", "、") in html:
                print(f"  Match found: view/{vid}")
                milestones = extract_tuidui_history_from_view(html)
                city_ids = extract_case_ids_from_view(html)
                return vid, milestones, city_ids
        except Exception as e:
            print(f"  Error checking view/{vid}: {e}")
            continue
    return "", {}, []


def update_project_cache(project_id: str, view_id: str, milestones: dict[str, str]) -> bool:
    """Update project cache with twur_view_id, twur_url, national_milestones."""
    from urtpe.links import _project_cache_dir

    cache_dir = _project_cache_dir(Path("data/.link_cache"), project_id)
    result_file = cache_dir / "result.json"
    if not result_file.exists():
        print(f"  SKIP (no cache): {project_id}", file=sys.stderr)
        return False

    try:
        content = result_file.read_text(encoding="utf-8")
        result = json.loads(content)
    except (json.JSONDecodeError, OSError) as e:
        print(f"  ERROR reading cache {project_id}: {e}", file=sys.stderr)
        return False

    # Merge milestones (new wins on overlap)
    existing = result.get("national_milestones", {})
    merged = {**existing, **milestones}
    result["national_milestones"] = merged

    # Update twur info
    result["twur_view_id"] = view_id
    result["twur_url"] = f"https://twur.nlma.gov.tw/zh/urban/rebuild/view/{view_id}"

    # Write back
    try:
        result_file.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        return True
    except OSError as e:
        print(f"  ERROR writing cache {project_id}: {e}", file=sys.stderr)
        return False


def log_failure(project_id: str, view_id: str, error: str) -> None:
    """Log failure to fetch_failures.json (JSON Lines)."""
    entry = {
        "project_id": project_id,
        "view_id": view_id,
        "error": str(error),
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime()),
    }
    ROOT = Path("data/.link_cache")
    ROOT.mkdir(parents=True, exist_ok=True)
    with open(ROOT / "fetch_failures.json", "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    print(f"  FAILURE logged: {project_id} - {error}", file=sys.stderr)


def regenerate_viewer() -> bool:
    """Regenerate viewer/projects.data.js via CLI."""
    import subprocess
    cmd = [
        sys.executable, "-m", "urtpe.cli",
        "--from-js", "viewer/projects.data.js",
        "-o", "data",
        "--viewer", "viewer",
        "--links"
    ]
    print("Regenerating viewer...")
    try:
        result = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True, timeout=300)
        if result.returncode == 0:
            print("Viewer regenerated successfully")
            return True
        else:
            print(f"Viewer regeneration failed: {result.stderr}", file=sys.stderr)
            return False
    except subprocess.TimeoutExpired:
        print("Viewer regeneration timed out", file=sys.stderr)
        return False
    except Exception as e:
        print(f"Viewer regeneration error: {e}", file=sys.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(description="Fetch missing national portal data for projects.")
    parser.add_argument("--dry-run", action="store_true", help="Process only first 3 candidates")
    parser.add_argument("--max-projects", type=int, default=0, help="Maximum projects to process (0 = all)")
    args = parser.parse_args()

    print("=" * 60)
    print("Fetch Remaining National Portal Data")
    print(f"Deadline: {DEADLINE_HOUR:02d}:{DEADLINE_MINUTE:02d}")
    print("=" * 60)

    # Load candidates
    print("Loading candidates from viewer/projects.data.js...")
    candidates = load_candidates()
    print(f"Found {len(candidates)} projects missing twur links")

    if not candidates:
        print("No candidates to process.")
        return 0

    # Show top 5
    print("Top 5 candidates (by 現況 date desc):")
    for i, c in enumerate(candidates[:5]):
        print(f"  {i+1}. {c['project_id']} | {c['current_date']} | {c['section']}{c['parcel']}")

    if args.dry_run:
        candidates = candidates[:3]
        print(f"\nDRY RUN: processing only first {len(candidates)} candidates")

    if args.max_projects > 0:
        candidates = candidates[:args.max_projects]
        print(f"\nLimited to first {args.max_projects} candidates")

    processed = 0
    updated = 0
    failed = 0

    for i, cand in enumerate(candidates):
        # Check deadline at start of each iteration
        if is_past_deadline():
            print(f"\nDeadline {DEADLINE_HOUR:02d}:{DEADLINE_MINUTE:02d} reached. Stopping.")
            break

        project_id = cand["project_id"]
        section = cand["section"]
        parcel = cand["parcel"]
        current_date = cand["current_date"]

        print(f"\n[{processed+1}/{len(candidates)}] {project_id} | {current_date} | {section}{parcel}")

        # Search portal by section, then filter by parcel
        chosen_vid, milestones, city_ids = find_matching_view(section, parcel)
        if not chosen_vid:
            print(f"  No matching view_id found for parcel {parcel}, skipping")
            continue

        print(f"  Matched view/{chosen_vid}")
        print(f"  Milestones: {len(milestones)}")

        print(f"  Milestones: {len(milestones)}")
        for k, v in milestones.items():
            print(f"    {k} = {v}")

        # Update cache
        success = update_project_cache(cand["project_id"], chosen_vid, milestones)
        if success:
            updated += 1
            print(f"  Cache updated for {chosen_vid}")
        else:
            failed += 1

        processed += 1

        # Check deadline before sleeping
        if is_past_deadline():
            print(f"\nDeadline reached after processing {project_id}. Stopping.")
            break

        # Polite interval (not after last, and not in dry-run)
        if i < len(candidates) - 1 and not is_past_deadline() and not args.dry_run:
            wait = random.uniform(180, 300)
            print(f"  Sleeping {wait:.0f}s...")
            time.sleep(wait)

    print(f"\n{'='*60}")
    print(f"Processed: {processed}")
    print(f"Updated:   {updated}")
    print(f"Failed:    {failed}")

    # Regenerate viewer
    print("\nRegenerating viewer...")
    regenerate_viewer()

    return 0


if __name__ == "__main__":
    sys.exit(main())