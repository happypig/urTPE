"""twur sweep — recover twur links for twur-less projects (order 2 of §6.14).

Identity: the national portal asserts case↔unit membership via the 相關連結
anchors on each project's view page. This sweep:
  1. title-searches the portal via ?title=<section>&city_id=2,
  2. fetches ≤3 candidate view pages (DEFAULT_MAX_PROBE),
  3. attaches when the page's 相關連結 ∩ disc.city_case_ids ≠ ∅
     (portal-proven identity — no matcher loosening),
  4. merges twur_view_id / twur_url / national_milestones into result.json,
  5. clears the ledger entry (clear-on-match).

Pacing: 15–45 s between projects; no-match skips sleep 15–45 s.
Two passes; pass 2 runs only if pass 1 leaves any unresolved.
"""
from __future__ import annotations

import json
import random
import sys
import time
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

from urtpe.links import fetch_url, extract_case_ids_from_view  # noqa: E402

SEARCH_URL = "https://twur.nlma.gov.tw/zh/urban/rebuild/0"
VIEW_URL_BASE = "https://twur.nlma.gov.tw/zh/urban/rebuild/view/"
ROOT = Path("data/.link_cache")
DEFAULT_MAX_PROBE = 3
REPROBE_DAYS = 14
