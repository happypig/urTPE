#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fetch_remaining_national_portal.py

Time-bounded script to fetch missing national portal data for projects lacking twur links.

Usage:
    python scripts/fetch_remaining_national_portal.py [--dry-run] [--max-projects N] [--max-probe N]

Behavior:
- Loads viewer/projects.data.js
- Finds projects missing twur links
- Prioritizes by 現況 date descending (newest first)
- For each: searches portal via ?title=, fetches view page, parses 推導歷程
- Updates per-project cache with twur_view_id, twur_url, national_milestones
- Waits 1-3 min between projects (random 60-180s; calibrated from 3-5 min —
  watch fetch_failures.json for WAF resets and revert to 180-300 if seen)
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
import os
import random
import re
import sys
import time
from datetime import datetime, time as dtime, timedelta
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

# The requirement says 06:30; the implementation said 07:00. The requirement wins, and the
# window is now a launch-time option so the two can never disagree again.
DEFAULT_DEADLINE = "06:30"
SEARCH_URL = "https://twur.nlma.gov.tw/zh/urban/rebuild/0"
VIEW_URL_BASE = "https://twur.nlma.gov.tw/zh/urban/rebuild/view/"
ROOT = Path("data/.link_cache")
FAILURES_LOG = ROOT / "fetch_failures.json"
LEDGER_PATH = ROOT / "no_match_ledger.json"
DEFAULT_REPROBE_DAYS = 14
DEFAULT_MAX_PROBE = 8

# ──────────────────────────────────────────────────────────────────────────────
# No-Match Ledger (design D1/D3/D5)
# ──────────────────────────────────────────────────────────────────────────────

def load_ledger(path: Path = LEDGER_PATH) -> dict:
    """Load the no-match ledger; a corrupt file is quarantined and run starts fresh."""
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError) as e:
        corrupt = path.with_suffix(path.suffix + ".corrupt")
        print(f"WARNING: unreadable no-match ledger {path} ({e}); quarantining to {corrupt}",
              file=sys.stderr)
        try:
            os.replace(path, corrupt)
        except OSError:
            pass
        return {}


def save_ledger(ledger: dict, path: Path = LEDGER_PATH) -> None:
    """Persist ledger atomically (write temp, then os.replace)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(ledger, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)


# Outcome of a targeted search. miss is a negative: the portal answered and had nothing.
# rror means every fetch raised, so the search never completed and the project was never
# shown to be absent -- recording it as a miss would bury it for the re-probe TTL on the
# strength of a network blip.
OUTCOME_MATCH = "match"
OUTCOME_MISS = "miss"
OUTCOME_ERROR = "error"


def annotate_class(ledger: dict, project_id: str, cls: str) -> None:
    """Annotate a ledger entry with the project's twur class
    (never-approved / recoverable) from the top.ashx outcome classification —
    never-approved entries are excluded from re-probes regardless of TTL.

    Classification reads case outcomes, so it applies to negatives only. An rror entry
    retrieved nothing and therefore has no case outcome; forcing 
ecoverable onto it
    would assert the portal should hold a page we never reached.
    """
    entry = ledger.get(project_id)
    if entry is None:
        return
    if entry.get("twur_class") == OUTCOME_ERROR:
        return
    entry["twur_class"] = cls


def record_no_match(ledger: dict, project_id: str, view_ids_checked: list[str],
                    now: Optional[datetime] = None) -> None:
    """Record/update a project's no-match probe result (mutates ledger in place)."""
    record_outcome(ledger, project_id, view_ids_checked,
                   outcome=OUTCOME_MISS, now=now)


def record_outcome(ledger: dict, project_id: str, view_ids_checked: list[str],
                   *, outcome: str, now: Optional[datetime] = None) -> None:
    """Record a targeted search's outcome. Only a miss carries the re-probe exclusion.

    The entry shape is identical for all three so the ledger stays one table; 	wur_class
    is what distinguishes them, and ilter_candidates keys eligibility off it rather than
    off the timestamp. An rror keeps its last_probed -- when the failure happened is
    evidence -- without that timestamp buying an exclusion, because it was never a negative.
    """
    entry = {
        "last_probed": (now or datetime.now()).isoformat(timespec="seconds"),
        "view_ids_checked": list(view_ids_checked),
    }
    if outcome == OUTCOME_ERROR:
        entry["twur_class"] = OUTCOME_ERROR
    elif outcome == OUTCOME_MISS:
        entry["twur_class"] = ledger.get(project_id, {}).get("twur_class")
        if entry["twur_class"] in (None, OUTCOME_ERROR):
            entry["twur_class"] = OUTCOME_MISS
    ledger[project_id] = entry


def clear_entry(ledger: dict, project_id: str) -> None:
    """Remove a project's ledger entry (no-op when absent)."""
    ledger.pop(project_id, None)


def filter_candidates(candidates: list[dict], ledger: dict, reprobe_days: float = DEFAULT_REPROBE_DAYS,
                      now: Optional[datetime] = None) -> tuple[list[dict], list[dict]]:
    """Split candidates into (kept, skipped-as-recently-probed).

    Pure logic over in-memory entries — no filesystem access. A project is
    skipped when its ledger entry is annotated never-approved (the portal will
    never list the unit — liveness policy, §6.14 E3) or when its entry has a
    parseable last_probed newer than now - reprobe_days. Malformed or missing
    entries never exclude.
    """
    now = now or datetime.now()
    cutoff = now - timedelta(days=reprobe_days)
    kept: list[dict] = []
    skipped: list[dict] = []
    for cand in candidates:
        entry = ledger.get(cand["project_id"]) or {}
        if entry.get("twur_class") == "never-approved":
            skipped.append(cand)
            continue
        if entry.get("twur_class") == OUTCOME_ERROR:
            # Never a negative: the search did not complete, so the project must not be
            # suppressed for the TTL. Re-probe pacing for a portal that is down is the
            # politeness interval's job, not this entry's.
            kept.append(cand)
            continue
        probed = None
        raw = entry.get("last_probed")
        if isinstance(raw, str):
            try:
                probed = datetime.fromisoformat(raw)
            except ValueError:
                probed = None
        if probed is not None and probed > cutoff:
            skipped.append(cand)
        else:
            kept.append(cand)
    return kept, skipped


def sweep_matched_entries(ledger: dict, cache_root: Path = ROOT) -> list[str]:
    """Drop ledger entries for projects whose cache already carries a twur link.

    Self-heals entries left behind when a match came from another writer.
    Returns the removed project_ids; caller persists the mutated ledger.
    """
    removed: list[str] = []
    for pid in list(ledger):
        result_file = _project_cache_dir(cache_root, pid) / "result.json"
        try:
            result = json.loads(result_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if result.get("twur_url"):
            clear_entry(ledger, pid)
            removed.append(pid)
    return removed

# ──────────────────────────────────────────────────────────────────────────────
# Core Functions
# ──────────────────────────────────────────────────────────────────────────────

# Captured at import so is_past_deadline can resolve an HH:MM deadline that
# has already passed today into tomorrow instead of stopping instantly.
_PROCESS_START = datetime.now()


def parse_deadline(text: str) -> tuple[int, int]:
    """Parse an `HH:MM` stop time.

    Raises ValueError on anything unparseable. Falling back to the default instead would be
    worse than refusing: a typo in `--deadline` would silently become 06:30 and a sweep
    meant to stop this afternoon would run overnight against the portal.
    """
    raw = (text or "").strip()
    m = re.fullmatch(r"(\d{1,2}):(\d{2})", raw)
    if not m:
        raise ValueError(
            "stop time must be HH:MM in 24-hour form, got %r" % text)
    hour, minute = int(m.group(1)), int(m.group(2))
    if not (0 <= hour <= 23) or not (0 <= minute <= 59):
        raise ValueError("stop time out of range: %r" % text)
    return hour, minute


def resolve_deadline(start: datetime, hour: int, minute: int) -> datetime:
    """The first occurrence of the stop time strictly after `start`.

    A stop time at-or-before the launch moment means tomorrow: launching at 10:30 with a
    06:30 stop targets tomorrow 06:30, not an already-past 06:30 that would exit instantly.
    """
    target = start.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if target <= start:
        target += timedelta(days=1)
    return target


# Resolved once at startup so is_past_deadline stays a cheap comparison in the hot loop.
# Rebound by main() when --deadline supplies a different window.
_DEADLINE: list[datetime] = [resolve_deadline(_PROCESS_START, *parse_deadline(DEFAULT_DEADLINE))]


def is_past_deadline() -> bool:
    """True once now passes the resolved stop time."""
    now = datetime.now()
    return now >= _DEADLINE[0]


def load_candidates(js_path: Optional[Path] = None) -> list[dict]:
    """Load projects from viewer/projects.data.js and return candidates missing twur."""
    js_path = js_path or (REPO_ROOT / "viewer" / "projects.data.js")
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

        section = current_node.get("section", "")
        land = current_node.get("land", "")
        # Parcel keyword = the anchor record's NAMED first parcel — the parcel the
        # case name is titled after. Never derive it positionally from an
        # enumerated land string ("599、599-1、…、623地號" must yield 599, not 623).
        parcel = current_node.get("first_parcel") or ""
        count = ""
        if land:
            m2 = re.search(r"等(\d+)筆", land)
            if m2:
                count = m2.group(1)
            if not parcel:
                # Fallback: first parcel token appearing in the land string.
                m = re.search(r"(\d+(?:-\d+)?)", land)
                if m:
                    parcel = m.group(1)

        if not section or not parcel:
            continue

        candidates.append({
            "project_id": p["project_id"],
            "section": section,
            "parcel": parcel,
            "count": count,
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


_FULLWIDTH_DIGITS = str.maketrans("０１２３４５６７８９", "0123456789")


def normalize_land_token(token: str) -> str:
    """Normalize a parcel/count token: full-width→ASCII digits, 之→- (design D2).

    Notation equivalence only — never changes numeric values.
    """
    return (token or "").translate(_FULLWIDTH_DIGITS).replace("之", "-")


def view_page_matches(html: str, section: str, parcel: str, count: str = "") -> bool:
    """Strict match: the page title must carry the same section + named first
    parcel (+ equal land count when both sides carry one).

    Comparisons are type-safe and notation-normalized so text '27' equals
    parsed count 27 and 263之19 equals 263-19. Prevents substring collisions
    (263-19 vs 209-19) and same-parcel different-project collisions
    (444等7筆 vs 444等17筆).
    """
    parcel_n = normalize_land_token(parcel)
    count_n = normalize_land_token(count)
    if not section or not parcel_n:
        return False

    # Body check accepts both hyphen and 之 spellings of the sub-parcel.
    body_variants = (f"{parcel_n}地號", f"{parcel_n.replace('-', '之')}地號")
    if not any(v in html for v in body_variants):
        return False

    import re
    m = re.search(r"<title>([^<]+)</title>", html)
    title = m.group(1) if m else ""
    if not title:
        return False

    # parse_name_id only reads ASCII digits and hyphen sub-parcels — normalize
    # the title's 地號 notation before parsing.
    title_norm = title.translate(_FULLWIDTH_DIGITS)
    title_norm = re.sub(r"(\d+)之(\d+)", r"\1-\2", title_norm)

    from urtpe.cleanse import parse_name_id
    t_district, t_section, t_parcel, t_count = parse_name_id(title_norm)
    if t_section != section:
        return False
    if normalize_land_token(t_parcel) != parcel_n:
        return False
    if count_n and t_count is not None and str(t_count) != count_n:
        return False
    return True


def find_matching_view_with_outcome(section: str, parcel: str, count: str = "",
                       max_probe: int = DEFAULT_MAX_PROBE) -> tuple[str, dict[str, str], list[str], str, list[str]]:
    """Search for view_id matching section, then filter by strict identity match.

    Probes at most max_probe results (default 8) in returned order; stops at
    the first match. When the limit truncates unprobed results without a
    match, a note with the unprobed count is printed.

    Returns (view_id, milestones, city_ids, html, view_ids_checked); html is
    empty when no match. view_ids_checked lists every probed view_id (match,
    reject, or error) so no-match probes can be recorded in the ledger.
    """
    vids = search_portal(section)
    if not vids:
        return "", {}, [], "", []

    limit = max(1, int(max_probe))
    checked: list[str] = []
    raised = 0
    for vid in vids[:limit]:
        print(f"  Checking view/{vid} for parcel {parcel}...")
        checked.append(vid)
        try:
            url = f"https://twur.nlma.gov.tw/zh/urban/rebuild/view/{vid}"
            html = fetch_url(url, None, True)
            if view_page_matches(html, section, parcel, count):
                print(f"  Match found: view/{vid}")
                milestones = extract_tuidui_history_from_view(html)
                city_ids = extract_case_ids_from_view(html)
                # Some probes may have raised; a page that satisfies the strict matcher is
                # still a match, so no error is recorded for the ones that did not.
                return vid, milestones, city_ids, html, checked, OUTCOME_MATCH
            print(f"  view/{vid} rejected (section/parcel/count mismatch)")
        except Exception as e:
            raised += 1
            print(f"  Error checking view/{vid}: {e}")
            continue

    remaining = len(vids) - len(checked)
    if remaining > 0:
        print(f"  No match within {limit} probes ({remaining} unprobed results remain)")
    # Every probe raised, or at least one did and none answered. A miss is a negative only
    # when the portal actually answered.
    if checked and raised == len(checked):
        return "", {}, [], "", checked, OUTCOME_ERROR
    return "", {}, [], "", checked, OUTCOME_MISS


def update_project_cache(project_id: str, view_id: str, milestones: dict[str, str], view_html: str = "",
                         ledger: Optional[dict] = None, ledger_path: Path = LEDGER_PATH,
                         cache_root: Path = Path("data/.link_cache")) -> bool:
    """Update project cache with twur_view_id, twur_url, national_milestones (and view.html when provided).

    When a ledger dict is supplied, a successful update also clears the
    project's no-match entry and persists the ledger (design D4).
    """
    from urtpe.links import _project_cache_dir

    cache_dir = _project_cache_dir(cache_root, project_id)
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
        if view_html:
            (cache_dir / "view.html").write_text(view_html, encoding="utf-8")
    except OSError as e:
        print(f"  ERROR writing cache {project_id}: {e}", file=sys.stderr)
        return False

    if ledger is not None and project_id in ledger:
        clear_entry(ledger, project_id)
        save_ledger(ledger, ledger_path)

    return True


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
    """Regenerate viewer/projects.data.js via CLI.

    Child output goes to a log file instead of capture pipes: an orphaned
    child can always finish writing and stays observable, and slow
    regenerations don't hit the timeout into silent 'viewer not refreshed'
    states (facts_2_portals.md §17 #1 correction, §12.9).
    """
    import subprocess
    cmd = [
        sys.executable, "-m", "urtpe.cli",
        "--from-js", "viewer/projects.data.js",
        "-o", "data",
        "--viewer", "viewer",
        "--links"
    ]
    log_path = ROOT / "regen_log.txt"
    print("Regenerating viewer...")
    try:
        with open(log_path, "ab") as log:
            log.write(f"\n=== regen start {time.strftime('%Y-%m-%dT%H:%M:%S')} ===\n".encode("utf-8"))
            log.flush()
            result = subprocess.run(cmd, cwd=REPO_ROOT, stdout=log, stderr=log, timeout=1800)
        if result.returncode == 0:
            print("Viewer regenerated successfully")
            return True
        else:
            print(f"Viewer regeneration failed (see {log_path})", file=sys.stderr)
            return False
    except subprocess.TimeoutExpired:
        print(f"Viewer regeneration timed out after 1800s (see {log_path})", file=sys.stderr)
        return False
    except Exception as e:
        print(f"Viewer regeneration error: {e}", file=sys.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(description="Fetch missing national portal data for projects.")
    parser.add_argument("--dry-run", action="store_true", help="Process only first 3 candidates")
    parser.add_argument("--max-projects", type=int, default=0, help="Maximum projects to process (0 = all)")
    parser.add_argument("--reprobe-days", type=int, default=DEFAULT_REPROBE_DAYS,
                        help=f"Re-probe no-match candidates after N days (default {DEFAULT_REPROBE_DAYS}; 0 disables skipping)")
    parser.add_argument("--max-probe", type=int, default=DEFAULT_MAX_PROBE,
                        help=f"Max view pages to probe per project (default {DEFAULT_MAX_PROBE})")
    parser.add_argument("--deadline", default=DEFAULT_DEADLINE, metavar="HH:MM",
                        help="Stop initiating fetches at this local time; resolves to the next "
                             "occurrence after launch (default: %(default)s). Malformed input is "
                             "refused rather than defaulted.")
    args = parser.parse_args()

    print("=" * 60)
    print("Fetch Remaining National Portal Data")

    # Refuse a malformed stop time before touching the ledger or the portal: silently
    # defaulting would turn a typo into an overnight crawl.
    try:
        hour, minute = parse_deadline(args.deadline)
    except ValueError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 2
    global _DEADLINE
    _DEADLINE = [resolve_deadline(_PROCESS_START, hour, minute)]
    resolved_deadline = _DEADLINE[0]
    print(f"Stop time: {resolved_deadline:%Y-%m-%d %H:%M} local "
          f"({(resolved_deadline - _PROCESS_START).total_seconds() / 3600:.1f}h window)")
    print("=" * 60)

    # Load ledger + self-heal entries for projects that gained twur elsewhere
    ledger = load_ledger()
    removed = sweep_matched_entries(ledger)
    if removed:
        save_ledger(ledger)
        print(f"Ledger sweep: cleared {len(removed)} entries (projects now have twur)")

    # Load candidates, then exclude recently-probed no-matches (design D2)
    print("Loading candidates from viewer/projects.data.js...")
    all_candidates = load_candidates()
    candidates, skipped_list = filter_candidates(all_candidates, ledger, reprobe_days=args.reprobe_days)
    skipped_count = len(skipped_list)
    print(f"Found {len(all_candidates)} projects missing twur links")
    if skipped_count:
        print(f"Ledger: skipping {skipped_count} probed within {args.reprobe_days} days "
              f"— {len(candidates)} to process this run")

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
            print(f"\nStop time {resolved_deadline:%H:%M} reached. Stopping.")
            break

        project_id = cand["project_id"]
        section = cand["section"]
        parcel = cand["parcel"]
        count = cand.get("count", "")
        current_date = cand["current_date"]

        print(f"\n[{processed+1}/{len(candidates)}] {project_id} | {current_date} | {section}{parcel}")

        # Search portal by section, then filter by strict identity match
        chosen_vid, milestones, city_ids, view_html, checked_vids, outcome = \
            find_matching_view_with_outcome(section, parcel, count, max_probe=args.max_probe)
        matched = outcome == OUTCOME_MATCH
        if outcome == OUTCOME_ERROR:
            # Every fetch raised. The search did not complete, so this is not evidence the
            # portal lacks the case -- recording it as a miss would suppress the project for
            # the re-probe TTL on the strength of a network blip.
            print(f"  All {len(checked_vids)} portal fetches failed for {parcel}; "
                  f"recording an error, not a no-match")
            record_outcome(ledger, project_id, checked_vids, outcome=OUTCOME_ERROR)
            save_ledger(ledger)
        elif not matched:
            print(f"  No matching view_id found for parcel {parcel}, skipping")
            # Record immediately (design D3): a deadline kill must not lose tonight's negatives
            record_outcome(ledger, project_id, checked_vids, outcome=OUTCOME_MISS)
            save_ledger(ledger)
        else:
            print(f"  Matched view/{chosen_vid}")
            print(f"  Milestones: {len(milestones)}")

            for k, v in milestones.items():
                print(f"    {k} = {v}")

            # Update cache (also persists matched view.html for future re-parsing);
            # success clears the project's ledger entry (design D4)
            success = update_project_cache(cand["project_id"], chosen_vid, milestones, view_html,
                                           ledger=ledger)
            if success:
                updated += 1
                print(f"  Cache updated for {chosen_vid}")
            else:
                # The portal matched but the cache could not be written. That is our
                # failure, not the portal's absence, so it must not become a 14-day miss.
                failed += 1
                record_outcome(ledger, project_id, checked_vids, outcome=OUTCOME_ERROR)
                save_ledger(ledger)

        processed += 1

        # Check deadline before sleeping
        if is_past_deadline():
            print(f"\nDeadline reached after processing {project_id}. Stopping.")
            break

        # Polite interval (not after last, not in dry-run) — applies to matches
        # AND skips: a long no-match stretch must not run at bulk-crawl tempo.
        if i < len(candidates) - 1 and not is_past_deadline() and not args.dry_run:
            wait = random.uniform(60, 180) if matched else random.uniform(15, 45)
            print(f"  Sleeping {wait:.0f}s...")
            time.sleep(wait)

    print(f"\n{'='*60}")
    print(f"Candidates: {len(all_candidates)} total · {skipped_count} skipped as recently probed")
    print(f"Processed: {processed}")
    print(f"Updated:   {updated}")
    print(f"Failed:    {failed}")

    # Regenerate viewer
    print("\nRegenerating viewer...")
    regenerate_viewer()

    return 0


if __name__ == "__main__":
    sys.exit(main())