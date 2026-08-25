"""Tests for fetch_remaining_national_portal script.

Tests cover:
- Portal search and view page parsing
- Cache update logic
- Candidate prioritization
- Deadline logic
- Failure logging
- End-to-end integration
"""

from __future__ import annotations

import json
import tempfile
import time
from datetime import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Import the script functions (will be implemented)
# from scripts.fetch_remaining_national_portal import (
#     search_portal,
#     fetch_and_parse_view,
#     update_project_cache,
#     select_candidates,
#     is_past_deadline,
#     log_failure,
#     main,
# )

# ──────────────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────────────

# Sample portal search result HTML with single view_id
SEARCH_SINGLE_MATCH_HTML = """
<!DOCTYPE html>
<html>
<body>
<div class="data_table_box">
<table>
<tr><td><a href="/zh/urban/rebuild/view/123">Case 1</a></td></tr>
</table>
</div>
</body>
</html>
"""

# Sample portal search result HTML with multiple view_ids
SEARCH_MULTI_MATCH_HTML = """
<!DOCTYPE html>
<html>
<body>
<div class="data_table_box">
<table>
<tr><td><a href="/zh/urban/rebuild/view/123">Case 1</a></td></tr>
<tr><td><a href="/zh/urban/rebuild/view/456">Case 2</a></td></tr>
</table>
</div>
</body>
</html>
"""

# Sample portal search result HTML with no matches
SEARCH_NO_MATCH_HTML = """
<!DOCTYPE html>
<html>
<body>
<div class="data_table_box">
<table>
<tr><td>No results</td></tr>
</table>
</div>
</body>
</html>
"""

# Sample view page HTML with visible type4_table (current portal format)
VIEW_VISIBLE_TUIDUI_HTML = """
<!DOCTYPE html>
<html>
<body>
<div class="data_table_box">
<table class='type4_table'>
<tr><th scope="col" id="j01">項目</th><th scope="col" id="j02">日期</th></tr>
<tr><td headers="j01">事業計畫申請日期</td><td headers="j02">99.01.27</td></tr>
<tr><td headers="j01">事業計畫核定日期</td><td headers="j02">101.08.28</td></tr>
<tr><td headers="j01">權利變換計畫申請日期</td><td headers="j02">99.01.27</td></tr>
<tr><td headers="j01">第一次變更事業計畫核定日期</td><td headers="j02">105.08.24</td></tr>
<tr><td headers="j01">使用核發日期</td><td headers="j02">105.08.29</td></tr>
<tr><td headers="j01">備註</td><td headers="j02"></td></tr>
</table>
</div>
<div class="data_table_box">
<table class='type4_table'>
<tr><th scope="col" id="j11">項目</th><th scope="col" id="j12">內容</th></tr>
<tr><td headers="j11">資料更新日期</td><td headers="j12">本專案資料最後更新於112.03.17 17:40</td></tr>
</table>
</div>
<div class="data_table_box">
相關連結
縣市政府案件連結
<a href="https://gis.uro.taipei/r_progress_detail.aspx?case_id=11407009">案</a>
</div>
</body>
</html>
"""

# Sample view page HTML with legacy hidden table (old portal format)
VIEW_LEGACY_HIDDEN_HTML = """
<!DOCTYPE html>
<html>
<body>
<div class="data_table_box" style="display:none">
推動歷程
項目 日期
事業計畫申請日期 105.01.01
事業計畫核定日期 105.06.01
備註
</div>
<div class="data_table_box">
基本資料
實施者 單一實施者
相關連結
縣市政府案件連結
<a href="https://gis.uro.taipei/r_progress_detail.aspx?case_id=10110181">案</a>
</div>
</body>
</html>
"""

# Sample view page with no milestone table
VIEW_NO_MILESTONE_HTML = """
<!DOCTYPE html>
<html>
<body>
<div class="data_table_box">
基本資料
實施者 單一實施者
</div>
</body>
</html>
"""

# Sample projects.data.js content
SAMPLE_PROJECTS_JS = """
window.PROJECTS = {
  "schema_version": 1,
  "generated_at": "2026-08-23T10:00:00",
  "source": "test",
  "published_date": "2026-08-23",
  "counts": {"projects": 3, "records": 5},
  "projects": [
    {
      "project_id": "中山區-中山段一小段-254地號等13筆",
      "anchor_recno": 1,
      "district": "中山區",
      "section": "中山段一小段",
      "implementer": "聖得福建設",
      "name": "擬訂...",
      "member_recnos": [1, 2],
      "nodes": [
        {"recno": 1, "date": "2012-08-27", "stage": "擬訂", "track": "事業計畫、權利變換", "is_current": true, "section": "中山段一小段", "land": "中山區中山段一小段254地號等13筆"},
        {"recno": 2, "date": "2016-08-23", "stage": "變更", "track": "事業計畫、權利變換", "is_current": false, "section": "中山段一小段", "land": "中山區中山段一小段254地號等13筆"}
      ],
      "edges": [],
      "links": {"twur": "", "taipei": ["09811141", "09811142"], "milestones_national": {}, "milestones_taipei": {}},
      "borderline": []
    },
    {
      "project_id": "大安區-仁愛段四小段-54地號等3筆",
      "anchor_recno": 1,
      "district": "大安區",
      "section": "仁愛段四小段",
      "implementer": "昇陽建設",
      "name": "擬訂...",
      "member_recnos": [1],
      "nodes": [
        {"recno": 1, "date": "2026-08-06", "stage": "擬訂", "track": "事業計畫", "is_current": true, "section": "仁愛段四小段", "land": "大安區仁愛段四小段54地號等3筆"}
      ],
      "edges": [],
      "links": {"twur": "", "taipei": [], "milestones_national": {}, "milestones_taipei": {}},
      "borderline": []
    },
    {
      "project_id": "中正區-臨沂段一小段-507地號等3筆",
      "anchor_recno": 1,
      "district": "中正區",
      "section": "臨沂段一小段",
      "implementer": "東綺建設",
      "name": "擬訂...",
      "member_recnos": [1],
      "nodes": [
        {"recno": 1, "date": "2026-08-11", "stage": "擬訂", "track": "事業計畫", "is_current": true, "section": "臨沂段一小段", "land": "中正區臨沂段一小段507地號等3筆"}
      ],
      "edges": [],
      "links": {"twur": "https://twur.nlma.gov.tw/zh/urban/rebuild/view/123", "taipei": ["11508011"], "milestones_national": {}, "milestones_taipei": {}},
      "borderline": []
    }
  ]
};
"""


@pytest.fixture
def sample_projects_js():
    """Return sample projects.js content as string."""
    return SAMPLE_PROJECTS_JS


@pytest.fixture
def temp_cache_dir():
    """Create a temporary cache directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_project_cache(temp_cache_dir):
    """Create a sample project cache with existing data."""
    from urtpe.links import _project_cache_dir, DiscoveryResult, save_project_cache

    project_id = "中山區-中山段一小段-254地號等13筆"
    cache_dir = _project_cache_dir(temp_cache_dir, project_id)
    cache_dir.mkdir(parents=True, exist_ok=True)

    result = DiscoveryResult(
        project_id=project_id,
        land_core="中山區中山段一小段254地號等13筆",
        twur_view_id=None,
        twur_url="",
        city_case_ids=["09811141", "09811142"],
        national_milestones={},
        taipei_milestones={"核定日期": "2016/08/23"},
        status="resolved",
        error="",
    )
    save_project_cache(temp_cache_dir, project_id, result)
    return temp_cache_dir, project_id


# ──────────────────────────────────────────────────────────────────────────────
# Test Group 1: Unit Tests
# ──────────────────────────────────────────────────────────────────────────────

class TestSearchPortal:
    """Tests for search_portal function."""

    def test_single_match_returns_view_id(self):
        """Single unique view_id found."""
        # TODO: Implement when search_portal is created
        pass

    def test_multi_match_picks_first_logs_warning(self):
        """Multiple view_ids found - picks first, logs warning."""
        pass

    def test_no_match_returns_empty(self):
        """No view_ids found - returns empty list."""
        pass


class TestFetchAndParseView:
    """Tests for fetch_and_parse_view function."""

    def test_visible_type4_table_parses_milestones(self):
        """Visible type4_table with 項目/日期 headers parses correctly."""
        from urtpe.links import extract_tuidui_history_from_view

        history = extract_tuidui_history_from_view(VIEW_VISIBLE_TUIDUI_HTML)
        assert history["事業計畫申請日期"] == "99.01.27"
        assert history["事業計畫核定日期"] == "101.08.28"
        assert history["權利變換計畫申請日期"] == "99.01.27"
        assert history["第一次變更事業計畫核定日期"] == "105.08.24"
        assert history["使用核發日期"] == "105.08.29"
        assert "備註" not in history
        assert "資料更新日期" not in history

    def test_legacy_hidden_table_parses_milestones(self):
        """Legacy hidden table with display:none parses correctly."""
        from urtpe.links import extract_tuidui_history_from_view

        history = extract_tuidui_history_from_view(VIEW_LEGACY_HIDDEN_HTML)
        assert history["事業計畫申請日期"] == "105.01.01"
        assert history["事業計畫核定日期"] == "105.06.01"

    def test_no_milestone_table_returns_empty(self):
        """Page without milestone table returns empty dict."""
        from urtpe.links import extract_tuidui_history_from_view

        history = extract_tuidui_history_from_view(VIEW_NO_MILESTONE_HTML)
        assert history == {}

    def test_case_ids_extracted_alongside_milestones(self):
        """Case IDs still extracted from visible table page."""
        from urtpe.links import extract_case_ids_from_view

        ids = extract_case_ids_from_view(VIEW_VISIBLE_TUIDUI_HTML)
        assert ids == ["11407009"]


class TestUpdateProjectCache:
    """Tests for update_project_cache function."""

    def test_merges_twur_and_milestones(self, temp_cache_dir, sample_project_cache):
        """Merges twur_view_id, twur_url, national_milestones correctly."""
        # TODO: Implement when update_project_cache is created
        pass

    def test_preserves_existing_fields(self, temp_cache_dir, sample_project_cache):
        """Preserves existing fields like city_case_ids, taipei_milestones, status, error."""
        pass

    def test_new_wins_on_overlap(self, temp_cache_dir, sample_project_cache):
        """New milestones win on label overlap."""
        pass

    def test_missing_cache_dir_skipped(self, temp_cache_dir):
        """Missing cache dir is skipped with log."""
        pass


class TestCandidatePrioritization:
    """Tests for candidate selection and prioritization."""

    def test_loads_projects_data_js(self):
        """Loads and parses viewer/projects.data.js correctly."""
        pass

    def test_filters_projects_without_twur(self):
        """Filters projects where links.twur is empty/falsy."""
        pass

    def test_extracts_anchor_current_node(self):
        """Extracts anchor 現況 node (is_current=True) and its ISO date."""
        pass

    def test_extracts_section_and_parcel(self):
        """Extracts section and first parcel from anchor node."""
        pass

    def test_sorts_by_current_date_descending(self):
        """Sorts candidates by 現況 date descending (newest first)."""
        pass


class TestDeadlineLogic:
    """Tests for deadline logic."""

    def test_is_past_deadline_before_630(self):
        """Returns False before 06:30."""
        from datetime import time
        # TODO: Implement is_past_deadline function
        pass

    def test_is_past_deadline_at_630(self):
        """Returns True at 06:30."""
        pass

    def test_is_past_deadline_after_630(self):
        """Returns True after 06:30."""
        pass

    def test_next_deadline_same_day(self):
        """Deadline later today resolves to today."""
        from datetime import datetime
        from scripts.fetch_remaining_national_portal import _next_deadline
        start = datetime(2026, 8, 25, 12, 59)
        now = datetime(2026, 8, 25, 13, 0)
        assert _next_deadline(now, start, 22, 30) == datetime(2026, 8, 25, 22, 30)

    def test_next_deadline_crosses_midnight(self):
        """Deadline already passed at launch rolls to tomorrow (run_sweep_until 6 0 at 22:32)."""
        from datetime import datetime
        from scripts.fetch_remaining_national_portal import _next_deadline
        start = datetime(2026, 8, 25, 22, 32)
        now = datetime(2026, 8, 25, 23, 0)
        assert _next_deadline(now, start, 6, 0) == datetime(2026, 8, 26, 6, 0)

    def test_next_deadline_at_launch_rolls_forward(self):
        """Deadline equal to the launch moment also rolls to tomorrow."""
        from datetime import datetime
        from scripts.fetch_remaining_national_portal import _next_deadline
        start = datetime(2026, 8, 25, 7, 0)
        now = datetime(2026, 8, 25, 7, 0)
        assert _next_deadline(now, start, 7, 0) == datetime(2026, 8, 26, 7, 0)

    def test_loop_stops_at_deadline(self):
        """Loop stops at 06:30 and triggers regeneration."""
        pass


class TestFailureLogging:
    """Tests for failure logging."""

    def test_writes_json_lines(self, temp_cache_dir):
        """Writes JSON Lines with correct schema."""
        pass

    def test_includes_required_fields(self, temp_cache_dir):
        """Includes project_id, view_id, error, timestamp."""
        pass


class TestEndToEnd:
    """End-to-end integration tests."""

    def test_dry_run_on_3_samples(self, temp_cache_dir):
        """Dry-run on 3 sample projects produces expected cache updates."""
        pass


# ──────────────────────────────────────────────────────────────────────────────
# Test Group 2: Acceptance Tests (User-Visible Requirements)
# ──────────────────────────────────────────────────────────────────────────────

class TestAcceptance:
    """Acceptance tests for user-visible requirements."""

    def test_script_produces_twur_links_and_milestones(self):
        """Script run on 3 known projects produces twur links + national milestones visible in viewer."""
        pass

    def test_occupancy_permit_appears_in_viewer(self):
        """使用核發日期 from portal appears in 國 card in viewer."""
        pass

    def test_no_match_skips_gracefully(self):
        """Projects without portal match skip gracefully (no crash, logged)."""
        pass

    def test_viewer_regeneration_valid(self):
        """Viewer regeneration produces valid projects.data.js with new twur/milestones_national."""
        pass


# ──────────────────────────────────────────────────────────────────────────────
# Test Group 3: Adapter / Infrastructure Tests
# ──────────────────────────────────────────────────────────────────────────────

class TestAdapter:
    """Adapter/Infrastructure tests."""

    def test_search_portal_parses_view_ids(self):
        """search_portal parses /view/(\\d+) from real portal HTML (fixture)."""
        pass

    def test_fetch_and_parse_view_handles_both_markup(self):
        """fetch_and_parse_view handles both legacy (hidden) and current (visible type4_table) markup."""
        pass

    def test_cache_update_preserves_existing_fields(self):
        """Cache update preserves existing fields (city_case_ids, taipei_milestones, status, error)."""
        pass

    def test_deadline_check_stops_loop(self):
        """Deadline check at 06:30 stops loop and triggers regeneration."""
        pass

    def test_failure_logging_writes_valid_json_lines(self, temp_cache_dir):
        """Failure logging writes valid JSON Lines to fetch_failures.json."""
        pass


# ──────────────────────────────────────────────────────────────────────────────
# Test Group: No-Match Ledger (add-no-match-ledger change)
# ──────────────────────────────────────────────────────────────────────────────

from datetime import datetime, timedelta

from scripts.fetch_remaining_national_portal import (
    clear_entry,
    filter_candidates,
    load_ledger,
    record_no_match,
    save_ledger,
    sweep_matched_entries,
    update_project_cache,
)


def _cand(pid: str, date: str = "2026-01-01") -> dict:
    return {"project_id": pid, "section": "測試段", "parcel": "1", "count": "", "current_date": date}


class TestLedgerLoadSave:
    """1.1 — ledger load/save round-trip and corruption handling."""

    def test_round_trip_new_entry(self, tmp_path):
        ledger_path = tmp_path / "no_match_ledger.json"
        ledger = load_ledger(ledger_path)
        assert ledger == {}
        record_no_match(ledger, "pid-A", ["123", "456"], now=datetime(2026, 8, 25, 3, 0, 0))
        save_ledger(ledger, ledger_path)
        assert load_ledger(ledger_path) == {
            "pid-A": {"last_probed": "2026-08-25T03:00:00", "view_ids_checked": ["123", "456"]}
        }

    def test_update_existing_entry_last_wins(self):
        ledger = {}
        record_no_match(ledger, "pid-A", ["123"], now=datetime(2026, 8, 1))
        record_no_match(ledger, "pid-A", ["999"], now=datetime(2026, 8, 20))
        assert len(ledger) == 1
        assert ledger["pid-A"]["last_probed"] == "2026-08-20T00:00:00"
        assert ledger["pid-A"]["view_ids_checked"] == ["999"]

    def test_atomic_replace_leaves_no_temp_files(self, tmp_path):
        ledger_path = tmp_path / "no_match_ledger.json"
        ledger = {}
        record_no_match(ledger, "pid-A", ["123"])
        save_ledger(ledger, ledger_path)
        save_ledger(ledger, ledger_path)
        assert ledger_path.exists()
        assert list(tmp_path.iterdir()) == [ledger_path]

    def test_corrupt_json_quarantined_and_empty(self, tmp_path):
        ledger_path = tmp_path / "no_match_ledger.json"
        ledger_path.write_text("{not json", encoding="utf-8")
        ledger = load_ledger(ledger_path)
        assert ledger == {}
        assert not ledger_path.exists()
        corrupt = ledger_path.with_suffix(ledger_path.suffix + ".corrupt")
        assert corrupt.exists()


class TestCandidateFiltering:
    """1.2 — TTL-based candidate exclusion (pure logic)."""

    NOW = datetime(2026, 8, 25, 3, 0, 0)

    def _three_candidates(self):
        return [_cand("fresh"), _cand("stale"), _cand("never-probed")]

    def _ledger_fresh_and_stale(self):
        ledger = {}
        record_no_match(ledger, "fresh", ["1"], now=self.NOW - timedelta(days=1))
        record_no_match(ledger, "stale", ["2"], now=self.NOW - timedelta(days=15))
        return ledger

    def test_recent_entry_excluded(self):
        kept, skipped = filter_candidates(self._three_candidates(), self._ledger_fresh_and_stale(),
                                          reprobe_days=14, now=self.NOW)
        pids = [c["project_id"] for c in kept]
        assert "fresh" not in pids
        assert len(skipped) == 1 and skipped[0]["project_id"] == "fresh"

    def test_stale_entry_included(self):
        kept, _ = filter_candidates(self._three_candidates(), self._ledger_fresh_and_stale(),
                                    reprobe_days=14, now=self.NOW)
        assert "stale" in [c["project_id"] for c in kept]

    def test_missing_entry_included(self):
        kept, _ = filter_candidates(self._three_candidates(), self._ledger_fresh_and_stale(),
                                    reprobe_days=14, now=self.NOW)
        assert "never-probed" in [c["project_id"] for c in kept]

    def test_zero_reprobe_days_includes_everything(self):
        kept, skipped = filter_candidates(self._three_candidates(), self._ledger_fresh_and_stale(),
                                          reprobe_days=0, now=self.NOW)
        assert len(kept) == 3
        assert skipped == []

    def test_skipped_count_equals_difference(self):
        all_c = self._three_candidates()
        kept, skipped = filter_candidates(all_c, self._ledger_fresh_and_stale(),
                                          reprobe_days=14, now=self.NOW)
        assert len(all_c) - len(kept) == len(skipped)

    def test_malformed_timestamp_treated_as_unprobed(self):
        ledger = {"broken": {"last_probed": "not-a-date", "view_ids_checked": []}}
        kept, skipped = filter_candidates([_cand("broken")], ledger, reprobe_days=14, now=self.NOW)
        assert len(kept) == 1 and skipped == []


class TestClearOnMatchAndSweep:
    """1.3 — ledger cleared when project gains twur (direct + run-start sweep)."""

    PID = "中山區-中山段一小段-254地號等13筆"

    def _seed_cache(self, cache_root: Path, pid: str, twur_url: str) -> Path:
        from urtpe.links import _project_cache_dir

        d = _project_cache_dir(cache_root, pid)
        d.mkdir(parents=True, exist_ok=True)
        (d / "result.json").write_text(
            json.dumps({"project_id": pid, "twur_url": twur_url}), encoding="utf-8"
        )
        return d

    def test_update_success_clears_entry(self, tmp_path):
        self._seed_cache(tmp_path, self.PID, "")
        ledger_path = tmp_path / "ledger.json"
        ledger = {}
        record_no_match(ledger, self.PID, ["123"])
        save_ledger(ledger, ledger_path)

        ok = update_project_cache(self.PID, "789", {"使用核發日期": "112.05.31"},
                                  view_html="", ledger=ledger, ledger_path=ledger_path,
                                  cache_root=tmp_path)
        assert ok is True
        assert self.PID not in ledger
        assert load_ledger(ledger_path) == {}

    def test_sweep_drops_only_twured_entries(self, tmp_path):
        self._seed_cache(tmp_path, "has-twur", "https://twur.nlma.gov.tw/zh/urban/rebuild/view/1")
        self._seed_cache(tmp_path, "still-missing", "")
        ledger = {}
        record_no_match(ledger, "has-twur", ["1"])
        record_no_match(ledger, "still-missing", ["2"])

        removed = sweep_matched_entries(ledger, cache_root=tmp_path)

        assert removed == ["has-twur"]
        assert "has-twur" not in ledger
        assert "still-missing" in ledger


# ──────────────────────────────────────────────────────────────────────────────
# Test Group: Matcher fixes (fix-targeted-portal-matcher)
# ──────────────────────────────────────────────────────────────────────────────

import re as _re

from scripts.fetch_remaining_national_portal import (
    DEFAULT_MAX_PROBE,
    find_matching_view,
    load_candidates,
    normalize_land_token,
    view_page_matches,
)


def _title_html(title: str, body_parcel: str = "") -> str:
    """Build a minimal view page whose <title> carries the given case title."""
    body = ""
    if body_parcel:
        body = f"<div>臺北市松山區寶清段四小段{body_parcel}地號等27筆土地</div>"
    return f"<html><head><title>{title}-都更查詢-內政部國土管理署都市更新入口網</title></head><body>{body}</body></html>"


VIEW30_TITLE = "擬訂臺北市松山區寶清段四小段599地號等27筆土地都市更新事業計畫案"
VIEW30_LAND = "臺北市松山區寶清段四小段599、599-1、601、601-1、603、603-1、605、605-1、607、607-1、609、609-1、611、611-1、613、613-1、615、615-1、616、616-1、617、618、619、620、621、622、623地號等27筆土地"


class TestNormalizeLandToken:
    """Notation normalization helper (design D2)."""

    def test_hyphen_subparcel_unchanged(self):
        assert normalize_land_token("263-19") == "263-19"

    def test_zhi_becomes_hyphen(self):
        assert normalize_land_token("263之19") == "263-19"

    def test_fullwidth_digits_to_ascii(self):
        assert normalize_land_token("５９９") == "599"

    def test_combined(self):
        assert normalize_land_token("２６３之１９") == "263-19"


class TestStrictIdentityMatch:
    """1.2 + 1.3 — type-safe counts and notation-drift tolerance."""

    def test_counted_candidate_matches_own_page(self):
        """Text count '27' vs parsed numeric count 27 must accept (the §view/30 bug)."""
        html = _title_html(VIEW30_TITLE, body_parcel="623")
        assert view_page_matches(html, "寶清段四小段", "599", "27") is True

    def test_differing_counts_rejected(self):
        html = _title_html(VIEW30_TITLE, body_parcel="623")
        assert view_page_matches(html, "寶清段四小段", "599", "17") is False

    def test_absent_candidate_count_skips_count_check(self):
        html = _title_html(VIEW30_TITLE, body_parcel="623")
        assert view_page_matches(html, "寶清段四小段", "599", "") is True

    def test_absent_title_count_skips_count_check(self):
        title = "擬訂臺北市松山區寶清段四小段599地號1筆土地都市更新事業計畫案"  # no 等N筆 → count None
        m = _re.search(r"(臺北市.{1,4}?區.{1,10}?地號(?:等)?\d*筆)", title)
        assert m, "fixture title must be regex-shaped for this test"
        html = f"<html><head><title>{title}</title></head><body>x</body></html>"
        assert view_page_matches(html, "寶清段四小段", "599", "27") is False  # 1 vs 27 differ
        assert view_page_matches(html, "寶清段四小段", "599", "") is True

    def test_zhi_notation_title_accepted_for_hyphen_parcel(self):
        title = "變更臺北市松山區寶清段四小段２６３之１９地號等2筆土地都市更新事業計畫案"
        html = f"<html><head><title>{title}</title></head><body><div>263之19地號</div></body></html>"
        assert view_page_matches(html, "寶清段四小段", "263-19", "2") is True

    def test_wrong_parcel_rejected_even_if_in_body(self):
        """The 623-extraction bug signature: candidate says 623, title says 599."""
        html = _title_html(VIEW30_TITLE, body_parcel="623")
        assert view_page_matches(html, "寶清段四小段", "623", "27") is False

    def test_wrong_section_rejected(self):
        html = _title_html(VIEW30_TITLE, body_parcel="623")
        assert view_page_matches(html, "寶清段三小段", "599", "27") is False

    def test_unparseable_title_rejected(self):
        html = "<html><head><title>都更查詢</title></head><body>599地號</body></html>"
        assert view_page_matches(html, "寶清段四小段", "599", "") is False

    def test_offline_acceptance_replay_view30_cached(self):
        """1.5 replay hook — cached view/30 page must match its own project tuple."""
        cache_file = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "view30.html"
        if not cache_file.exists():
            pytest.skip("tests/fixtures/view30.html not present")
        html = cache_file.read_text(encoding="utf-8")
        assert view_page_matches(html, "寶清段四小段", "599", "27") is True


def _write_projects_js(tmp_path: Path, projects: list[dict]) -> Path:
    data = {
        "schema_version": 2, "generated_at": "2026-08-25T00:00:00", "source": "test",
        "published_date": "2026-08-25", "counts": {}, "projects": projects,
    }
    p = tmp_path / "projects.data.js"
    p.write_text(f"window.PROJECTS = {json.dumps(data, ensure_ascii=False)};\n", encoding="utf-8")
    return p


def _project(pid: str, section: str, land: str, first_parcel: str = "", twur: str = "",
             date: str = "2007-10-30") -> dict:
    node = {"recno": 1, "date": date, "stage": "變更", "is_current": True,
            "section": section, "land": land}
    if first_parcel:
        node["first_parcel"] = first_parcel
    return {"project_id": pid, "section": section, "nodes": [node],
            "links": {"twur": twur, "taipei": []}}


class TestCandidateParcelDerivation:
    """1.1 — anchor named first parcel wins over positional extraction (design D1)."""

    def test_enumerated_land_uses_named_first_parcel(self, tmp_path):
        pid = "松山區-寶清段四小段-599地號等27筆"
        p = _project(pid, "寶清段四小段", VIEW30_LAND, first_parcel="599")
        cands = load_candidates(_write_projects_js(tmp_path, [p]))
        assert len(cands) == 1
        assert cands[0]["parcel"] == "599"
        assert cands[0]["count"] == "27"

    def test_fallback_first_enumeration_token_when_first_parcel_missing(self, tmp_path):
        pid = "松山區-寶清段四小段-599地號等27筆"
        p = _project(pid, "寶清段四小段", VIEW30_LAND, first_parcel="")
        cands = load_candidates(_write_projects_js(tmp_path, [p]))
        assert cands[0]["parcel"] == "599"  # never the last token 623

    def test_compact_land_without_first_parcel(self, tmp_path):
        pid = "中山區-中山段一小段-254地號等13筆"
        p = _project(pid, "中山段一小段", "中山區中山段一小段254地號等13筆", first_parcel="")
        cands = load_candidates(_write_projects_js(tmp_path, [p]))
        assert cands[0]["parcel"] == "254"


class TestProbeBreadth:
    """1.4 — configurable probe limit replacing hardcoded first-5 (design D3)."""

    def test_default_limit_is_eight(self):
        assert DEFAULT_MAX_PROBE == 8

    def _run_find(self, monkeypatch, capsys, n_vids: int, max_probe, match_at=None):
        import scripts.fetch_remaining_national_portal as mod

        vids = [str(100 + i) for i in range(n_vids)]
        monkeypatch.setattr(mod, "search_portal", lambda section: vids)
        calls = {"n": 0}

        def fake_fetch(url, *a, **k):
            calls["n"] += 1
            vid = url.rsplit("/", 1)[-1]
            if match_at is not None and vid == str(100 + match_at):
                return _title_html(VIEW30_TITLE, body_parcel="623")
            return "<html><head><title>無關案件</title></head><body></body></html>"
        monkeypatch.setattr(mod, "fetch_url", fake_fetch)

        kwargs = {} if max_probe is None else {"max_probe": max_probe}
        result = find_matching_view("寶清段四小段", "599", "27", **kwargs)
        out = capsys.readouterr().out
        return result, calls["n"], out, vids

    def test_no_match_probes_at_most_default_limit(self, monkeypatch, capsys):
        result, calls, out, vids = self._run_find(monkeypatch, capsys, 12, None)
        assert calls == DEFAULT_MAX_PROBE
        assert result[0] == ""  # no match
        assert len(result[4]) == DEFAULT_MAX_PROBE  # checked list feeds the ledger
        assert "4 unprobed" in out  # truncation note: 12 - 8

    def test_override_limits_probes(self, monkeypatch, capsys):
        _, calls, _, _ = self._run_find(monkeypatch, capsys, 12, 3)
        assert calls == 3

    def test_match_stops_probing_before_limit(self, monkeypatch, capsys):
        result, calls, out, _ = self._run_find(monkeypatch, capsys, 12, None, match_at=2)
        assert calls == 3
        assert result[0] == "102"
        assert "unprobed" not in out  # matched → no truncation note

    def test_truncation_note_counts_unprobed(self, monkeypatch, capsys):
        _, _, out, vids = self._run_find(monkeypatch, capsys, 9, None)
        assert "1 unprobed" in out


# ──────────────────────────────────────────────────────────────────────────────
# Entry point for running tests
# ──────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    pytest.main([__file__, "-v"])