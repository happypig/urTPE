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
# Entry point for running tests
# ──────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    pytest.main([__file__, "-v"])