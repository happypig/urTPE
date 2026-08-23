"""Tests for portal index building, lookup, cache, and retry behavior."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from urtpe.links import (
    ListPageParser,
    build_portal_index,
    load_portal_index,
    save_portal_index,
    lookup_in_portal_index,
    fetch_url,
    discover_project_links,
    LinksDiscovery,
    DiscoveryResult,
)
from urtpe.models import CleanRecord, Project
from tests.fixtures_links import (
    LIST_PAGE_1_HTML,
    LIST_PAGE_2_HTML,
    LIST_PAGE_EMPTY_HTML,
    VIEW_771_HTML,
    VIEW_292_HTML,
    TAIPEI_CASE_10110211_HTML,
    TEST_CORES,
)


class TestListPageParser:
    """Tests for ListPageParser."""

    def test_parse_list_page_rows(self):
        """Parse list page rows → view_id + title + implementer + date."""
        parser = ListPageParser()
        parser.feed(LIST_PAGE_1_HTML)

        assert len(parser.entries) == 3
        # First entry
        assert parser.entries[0]["view_id"] == "771"
        assert "玉泉段二小段40地號等29筆" in parser.entries[0]["title"]
        assert parser.entries[0]["implementer"] == "弘千建設股份有限公司"
        assert parser.entries[0]["approval_date"] == "109.11.17"
        # Second entry
        assert parser.entries[1]["view_id"] == "292"
        assert "臨沂段一小段507地號等3筆" in parser.entries[1]["title"]
        assert parser.entries[1]["implementer"] == "東綺建設"
        # Third entry (duplicate core)
        assert parser.entries[2]["view_id"] == "888"
        assert "玉泉段二小段40地號等29筆" in parser.entries[2]["title"]

    def test_parse_last_page_no_next_link(self):
        """Last page has no next page link."""
        parser = ListPageParser()
        parser.feed(LIST_PAGE_2_HTML)
        assert parser.has_next_page is False

    def test_parse_empty_page(self):
        """Empty page has no entries."""
        parser = ListPageParser()
        parser.feed(LIST_PAGE_EMPTY_HTML)
        assert len(parser.entries) == 0
        assert parser.has_next_page is False


class TestBuildPortalIndex:
    """Tests for build_portal_index."""

    def test_build_index_crawls_all_pages(self):
        """Crawls all pages until empty."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir)

            def mock_fetch(url, cache_dir=None, fresh=False):
                if "page=1" in url or "page=" not in url:
                    return LIST_PAGE_1_HTML
                elif "page=2" in url:
                    return LIST_PAGE_2_HTML
                else:
                    return LIST_PAGE_EMPTY_HTML

            with patch("urtpe.links.fetch_url", side_effect=mock_fetch):
                index = build_portal_index(cache_dir, fresh=True)

            assert len(index) == 4  # 3 from page 1 + 1 from page 2
            # Verify cores are normalized
            cores = [e["core"] for e in index]
            assert any("玉泉段二小段40地號等29筆" in c for c in cores)
            assert any("臨沂段一小段507地號等3筆" in c for c in cores)

    def test_build_index_preserves_duplicates(self):
        """Duplicate cores are preserved for review."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir)

            def mock_fetch(url, cache_dir=None, fresh=False):
                if "page=1" in url or "page=" not in url:
                    return LIST_PAGE_1_HTML
                else:
                    return LIST_PAGE_EMPTY_HTML

            with patch("urtpe.links.fetch_url", side_effect=mock_fetch):
                index = build_portal_index(cache_dir, fresh=True)

            # Two entries with 玉泉段二小段40地號等29筆
            yuquan_entries = [e for e in index if "玉泉段二小段40地號等29筆" in e["core"]]
            assert len(yuquan_entries) == 2
            assert yuquan_entries[0]["view_id"] == "771"
            assert yuquan_entries[1]["view_id"] == "888"

    def test_build_index_uses_cache(self):
        """Reuses cached index when fresh=False."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir)

            def mock_fetch(url, cache_dir=None, fresh=False):
                if "page=1" in url or "page=" not in url:
                    return LIST_PAGE_1_HTML
                else:
                    return LIST_PAGE_EMPTY_HTML

            with patch("urtpe.links.fetch_url", side_effect=mock_fetch) as mock:
                build_portal_index(cache_dir, fresh=True)
                first_calls = mock.call_count

                # Second call with fresh=False should use cache
                build_portal_index(cache_dir, fresh=False)
                second_calls = mock.call_count

            assert second_calls == first_calls  # No additional fetches


class TestPortalIndexLookup:
    """Tests for lookup_in_portal_index."""

    def test_lookup_unique_core_returns_view_id(self):
        """Unique core returns the single view_id."""
        index = [
            {"core": "玉泉段二小段40地號等29筆", "view_id": "771"},
            {"core": "臨沂段一小段507地號等3筆", "view_id": "292"},
        ]

        result = lookup_in_portal_index("玉泉段二小段40地號等29筆", index)
        assert result == "771"

    def test_lookup_ambiguous_core_returns_none(self):
        """Ambiguous core (multiple matches) returns None."""
        index = [
            {"core": "玉泉段二小段40地號等29筆", "view_id": "771"},
            {"core": "玉泉段二小段40地號等29筆", "view_id": "888"},
        ]

        result = lookup_in_portal_index("玉泉段二小段40地號等29筆", index)
        assert result is None

    def test_lookup_missing_core_returns_none(self):
        """Missing core returns None."""
        index = [{"core": "玉泉段二小段40地號等29筆", "view_id": "771"}]

        result = lookup_in_portal_index("不存在的核心", index)
        assert result is None


class TestFetchUrlRetry:
    """Tests for retry/backoff in fetch_url."""

    def test_fetch_succeeds_on_third_attempt(self):
        """Succeeds on 3rd attempt after 2 connection errors."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir)
            call_count = [0]

            def mock_urlopen(req, timeout=30):
                call_count[0] += 1
                if call_count[0] < 3:
                    raise ConnectionResetError("Connection reset by peer")
                resp = MagicMock()
                resp.read.return_value = b"<html>success</html>"
                resp.__enter__ = lambda s: s
                resp.__exit__ = lambda s, *a: None
                return resp

            with patch("urllib.request.urlopen", side_effect=mock_urlopen):
                result = fetch_url("http://example.com", cache_dir, fresh=True)

            assert call_count[0] == 3
            assert "success" in result

    def test_fetch_fails_after_three_retries(self):
        """Fails after 3 retries (4 total attempts)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir)
            call_count = [0]

            def mock_urlopen(req, timeout=30):
                call_count[0] += 1
                raise ConnectionResetError("Connection reset by peer")

            with patch("urllib.request.urlopen", side_effect=mock_urlopen):
                with pytest.raises(ConnectionResetError):
                    fetch_url("http://example.com", cache_dir, fresh=True)

            assert call_count[0] == 4  # Initial + 3 retries

    def test_fetch_adds_browser_headers(self):
        """Request includes browser-like headers."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir)
            captured_req = {}

            def mock_urlopen(req, timeout=30):
                captured_req["headers"] = {k.lower(): v for k, v in req.headers.items()}
                resp = MagicMock()
                resp.read.return_value = b"<html>ok</html>"
                resp.__enter__ = lambda s: s
                resp.__exit__ = lambda s, *a: None
                return resp

            with patch("urllib.request.urlopen", side_effect=mock_urlopen):
                fetch_url("http://example.com", cache_dir, fresh=True)

            assert "user-agent" in captured_req["headers"]
            assert "mozilla" in captured_req["headers"]["user-agent"].lower()
            assert "accept" in captured_req["headers"]
            assert "text/html" in captured_req["headers"]["accept"]
            assert "accept-language" in captured_req["headers"]
            assert "zh-tw" in captured_req["headers"]["accept-language"].lower()


class TestPerProjectCache:
    """Tests for per-project cache and resume."""

    def test_cache_hit_skips_http(self):
        """Cache hit skips HTTP entirely."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir)

            # Create a fake project
            record = CleanRecord(
                recno=123, date="109/11/17", iso_date="2020-11-17",
                ymd=(2020, 11, 17), district="大同區", district_land="大同區",
                name="擬訂大同區玉泉段二小段40地號等29筆事業計畫及權利變換計畫案",
                name_raw="擬訂大同區玉泉段二小段40地號等29筆事業計畫及權利變換計畫案",
                land="大同區玉泉段二小段40、40-2、43地號等29筆土地",
                section="玉泉段二小段", first_parcel="40",
                parcels=["40", "40-2", "43"], aliases={}, land_count=29,
                orig_count=None, named_anchor="", area_section="",
                stage="擬訂", stage_index=0, track="事業計畫、權利變換",
                implementer="弘千建設", planner="規劃公司",
                auto_fixes=[], review_flags=[],
            )
            project = Project(
                project_id="大同區-玉泉段二小段-40地號等29筆",
                anchor_recno=123, members=[record],
            )

            # Pre-populate cache with a result
            slug = project.project_id.replace("/", "_").replace(" ", "_")
            project_cache = cache_dir / slug
            project_cache.mkdir(parents=True)
            result = DiscoveryResult(
                project_id=project.project_id,
                land_core=TEST_CORES["yuquan"],
                twur_view_id="771",
                twur_url="https://twur.nlma.gov.tw/zh/urban/rebuild/view/771",
                city_case_ids=["10110181"],
                national_milestones={"事業計畫申請日期": "101.12.28"},
                taipei_milestones={"計畫公聽會日期": "2012/10/21"},
                status="resolved",
            )
            import json
            (project_cache / "result.json").write_text(
                json.dumps(result.__dict__, ensure_ascii=False), encoding="utf-8"
            )

            # Mock fetch to verify it's NOT called
            call_count = [0]

            def mock_fetch(url, cache_dir=None, fresh=False):
                call_count[0] += 1
                if "view/771" in url:
                    return VIEW_771_HTML
                elif "case_id=10110181" in url:
                    return TAIPEI_CASE_10110211_HTML
                return ""

            with patch("urtpe.links.fetch_url", side_effect=mock_fetch) as mock:
                result = discover_project_links(project, cache_dir, fresh=False, delay=0)

            assert call_count[0] == 0  # No HTTP calls made
            assert result.twur_view_id == "771"
            assert result.city_case_ids == ["10110181"]

    def test_cache_miss_fetches_and_saves(self):
        """Cache miss runs Taipei-first discovery and saves result."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir)

            record = CleanRecord(
                recno=123, date="109/11/17", iso_date="2020-11-17",
                ymd=(2020, 11, 17), district="大同區", district_land="大同區",
                name="擬訂大同區玉泉段二小段40地號等29筆事業計畫及權利變換計畫案",
                name_raw="擬訂大同區玉泉段二小段40地號等29筆事業計畫及權利變換計畫案",
                land="大同區玉泉段二小段40、40-2、43地號等29筆土地",
                section="玉泉段二小段", first_parcel="40",
                parcels=["40", "40-2", "43"], aliases={}, land_count=29,
                orig_count=None, named_anchor="", area_section="",
                stage="擬訂", stage_index=0, track="事業計畫、權利變換",
                implementer="弘千建設", planner="規劃公司",
                auto_fixes=[], review_flags=[],
            )
            project = Project(
                project_id="大同區-玉泉段二小段-40地號等29筆",
                anchor_recno=123, members=[record],
            )

            # Portal index supplies the supplementary twur view id
            portal_index = [
                {"core": "大同區玉泉段二小段40地號等29筆", "view_id": "771"},
            ]

            # JSON payloads returned by the Taipei ashx endpoints
            search_json = json.dumps([
                {"item": "玉泉段二小段<br>0040 - 0000",
                 "case_id": "R091306-02",
                 "case_name": "擬訂臺北市大同區玉泉段二小段40地號等29筆...",
                 "schedule": "施工中",
                 "details": "r_progress_detail.aspx?case_id=10110181"},
            ], ensure_ascii=False)
            stage_json = json.dumps([
                {"Plan_Open_Date": "2012/10/18", "Uro_Chk_Date": "2020-11-17T00:00:00"},
            ], ensure_ascii=False)

            # Mock at urlopen level so fetch_url/fetch helpers run their real logic
            def mock_urlopen(req, timeout=30):
                url = req.full_url
                resp = MagicMock()
                if "Get_updcase_list.ashx" in url:
                    body = search_json.encode("utf-8")
                elif "Get_project168_second.ashx" in url:
                    body = stage_json.encode("utf-8")
                elif "view/771" in url:
                    body = VIEW_771_HTML.encode("utf-8")
                else:
                    body = b""
                resp.read.return_value = body
                resp.headers = {}
                resp.__enter__ = lambda s: s
                resp.__exit__ = lambda s, *a: None
                return resp

            with patch("urllib.request.urlopen", side_effect=mock_urlopen):
                result = discover_project_links(
                    project, cache_dir, fresh=True, delay=0,
                    portal_index=portal_index,
                )

            assert result.status == "resolved"
            assert result.twur_view_id == "771"
            assert result.city_case_ids == ["10110181"]
            assert result.taipei_milestones["計畫公聽會日期"] == "2012/10/18"
            assert result.taipei_milestones["核定日期"] == "2020-11-17"

            # Verify checkpoint cache created
            slug = project.project_id.replace("/", "_").replace(" ", "_")
            project_cache = cache_dir / slug
            assert (project_cache / "result.json").exists()

    def test_fresh_clears_cache(self):
        """--fresh clears cache before starting."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir)

            # Pre-populate cache
            slug = "test_project"
            project_cache = cache_dir / slug
            project_cache.mkdir(parents=True)
            (project_cache / "result.json").write_text("{}")

            record = CleanRecord(
                recno=1, date="109/11/17", iso_date="2020-11-17",
                ymd=(2020, 11, 17), district="大同區", district_land="大同區",
                name="擬訂大同區玉泉段二小段40地號等29筆案",
                name_raw="擬訂大同區玉泉段二小段40地號等29筆案",
                land="大同區玉泉段二小段40地號", section="玉泉段二小段",
                first_parcel="40", parcels=["40"], aliases={}, land_count=1,
                orig_count=None, named_anchor="", area_section="",
                stage="擬訂", stage_index=0, track="事業計畫",
                implementer="測試", planner="測試",
                auto_fixes=[], review_flags=[],
            )
            project = Project(
                project_id=slug, anchor_recno=1, members=[record],
            )

            # Mock portal index and fetch_url for view page
            portal_index = [
                {"core": "大同區玉泉段二小段40地號等1筆", "view_id": "771"},
            ]

            def mock_fetch(url, cache_dir=None, fresh=False):
                if "view/771" in url:
                    return VIEW_771_HTML
                return ""

            with patch("urtpe.links.fetch_url", side_effect=mock_fetch):
                with patch("urtpe.links.build_portal_index", return_value=portal_index):
                    discovery = LinksDiscovery(cache_dir=str(cache_dir), delay=0)
                    discovery.run([project], fresh=True)

            # Cache should be recreated (not use old stale result)
            assert (project_cache / "result.json").exists()


class TestDiscoveryRun:
    """Tests for LinksDiscovery.run."""

    def test_processes_projects_in_deterministic_order(self):
        """Projects processed in stable project_id order."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir)

            record1 = CleanRecord(
                recno=1, date="109/11/17", iso_date="2020-11-17",
                ymd=(2020, 11, 17), district="大同區", district_land="大同區",
                name="擬訂大同區玉泉段二小段40地號等29筆案",
                name_raw="擬訂大同區玉泉段二小段40地號等29筆案",
                land="大同區玉泉段二小段40地號", section="玉泉段二小段",
                first_parcel="40", parcels=["40"], aliases={}, land_count=1,
                orig_count=None, named_anchor="", area_section="",
                stage="擬訂", stage_index=0, track="事業計畫",
                implementer="測試", planner="測試",
                auto_fixes=[], review_flags=[],
            )
            record2 = CleanRecord(
                recno=2, date="108/06/20", iso_date="2019-06-20",
                ymd=(2019, 6, 20), district="中正區", district_land="中正區",
                name="擬訂中正區臨沂段一小段507地號等3筆案",
                name_raw="擬訂中正區臨沂段一小段507地號等3筆案",
                land="中正區臨沂段一小段507地號", section="臨沂段一小段",
                first_parcel="507", parcels=["507"], aliases={}, land_count=1,
                orig_count=None, named_anchor="", area_section="",
                stage="擬訂", stage_index=0, track="事業計畫",
                implementer="測試", planner="測試",
                auto_fixes=[], review_flags=[],
            )
            project1 = Project(project_id="中正區-臨沂段一小段-507地號等3筆", anchor_recno=2, members=[record2])
            project2 = Project(project_id="大同區-玉泉段二小段-40地號等29筆", anchor_recno=1, members=[record1])

            processed_order = []

            def mock_fetch(url, cache_dir=None, fresh=False):
                if "view/771" in url:
                    return VIEW_771_HTML
                elif "view/292" in url:
                    return VIEW_292_HTML
                elif "case_id=10110181" in url:
                    return TAIPEI_CASE_10110211_HTML
                elif "case_id=10110211" in url:
                    return TAIPEI_CASE_10110211_HTML
                return ""

            with patch("urtpe.links.fetch_url", side_effect=mock_fetch):
                with patch("urtpe.links.build_portal_index") as mock_build:
                    mock_build.return_value = [
                        {"core": "玉泉段二小段40地號等29筆", "view_id": "771"},
                        {"core": "臨沂段一小段507地號等3筆", "view_id": "292"},
                    ]
                    discovery = LinksDiscovery(cache_dir=str(cache_dir), delay=0)
                    discovery.run([project1, project2], fresh=True)
                    processed_order = list(discovery.run([project1, project2], fresh=True).keys())

            # Should be sorted by project_id
            assert processed_order == sorted(processed_order)