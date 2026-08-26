"""Official link discovery adapter: crawls national portal and Taipei platform,
joins by land-identity core, scrapes timelines, and attaches to projects."""

from __future__ import annotations

import asyncio
import html.parser
import json
import re
import shutil
import time
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional

from urtpe.models import CleanRecord, Project
from urtpe.taipei_playwright import TaipeiPlaywrightSearcher, TaipeiSearchResult


# ──────────────────────────────────────────────────────────────────────────────
# HTML Parsing (stdlib html.parser)
# ──────────────────────────────────────────────────────────────────────────────

class SearchResultParser(html.parser.HTMLParser):
    """Parse national portal search results to extract view IDs."""

    def __init__(self):
        super().__init__()
        self.in_result_row = False
        self.in_link = False
        self.link_href = ""
        self.view_ids = []

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        if tag == "tr":
            self.in_result_row = True
        elif tag == "a" and self.in_result_row:
            href = attrs_dict.get("href", "")
            if "/view/" in href:
                self.in_link = True
                self.link_href = href

    def handle_endtag(self, tag):
        if tag == "tr":
            self.in_result_row = False
        elif tag == "a" and self.in_link:
            self.in_link = False
            m = re.search(r"/view/(\d+)", self.link_href)
            if m:
                self.view_ids.append(m.group(1))
            self.link_href = ""


class ListPageParser(html.parser.HTMLParser):
    """Parse national portal list pages to extract all case entries."""

    def __init__(self):
        super().__init__()
        self.entries = []
        self.has_next_page = False
        self._in_table = False
        self._in_row = False
        self._in_cell = False
        self._current_cell = 0
        self._row_data = {}
        self._cell_buffer = ""

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        if tag == "table":
            self._in_table = True
        elif tag == "tr" and self._in_table:
            self._in_row = True
            self._current_cell = 0
            self._row_data = {}
        elif tag == "td" and self._in_row:
            self._in_cell = True
            self._cell_buffer = ""
        elif tag == "a" and self._in_row and self._in_cell:
            href = attrs_dict.get("href", "")
            if "/view/" in href:
                m = re.search(r"/view/(\d+)", href)
                if m:
                    self._row_data["view_id"] = m.group(1)
        elif tag == "a" and not self._in_table:
            href = attrs_dict.get("href", "")
            if "page=" in href:
                self.has_next_page = True

    def handle_endtag(self, tag):
        if tag == "table":
            self._in_table = False
        elif tag == "tr" and self._in_row:
            self._in_row = False
            if "view_id" in self._row_data:
                self.entries.append(self._row_data)
        elif tag == "td" and self._in_cell:
            self._in_cell = False
            text = self._cell_buffer.strip()
            if text:
                if self._current_cell == 0:
                    pass
                elif self._current_cell == 1:
                    self._row_data["approval_date"] = text
                elif self._current_cell == 2:
                    self._row_data["title"] = text
                elif self._current_cell == 3:
                    self._row_data["implementer"] = text
                elif self._current_cell == 4:
                    self._row_data["method"] = text
            self._current_cell += 1
            self._cell_buffer = ""

    def handle_data(self, data):
        if self._in_cell:
            self._cell_buffer += data


class ViewPageParser(html.parser.HTMLParser):
    """Parse national portal view page for 縣市政府案件連結 and 推動歷程.

    推動歷程 lives in a 項目/日期-headed table. Older portal builds rendered it
    inside display:none boxes (handled by the legacy text path); the current
    site serves it as visible static rows, so row-level parsing is the
    primary path.
    """

    ROC_DATE_RE = re.compile(r"^\d{2,3}(?:\.\d{2}){2}$")

    def __init__(self):
        super().__init__()
        self.case_ids = []
        self.tuidui_history = {}
        self._in_data_table = False
        self._in_hidden_table = False
        self._in_td = False
        self._tds = []
        self._current_table_text = ""
        self._in_milestone_table = False
        self._cell_active = False
        self._cell_buf = ""
        self._row_tds: list[str] = []

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        if tag == "div":
            cls = attrs_dict.get("class", "")
            style = attrs_dict.get("style", "")
            if "data_table_box" in cls:
                self._in_data_table = True
                self._tds = []
                self._current_table_text = ""
                self._in_hidden_table = "display:none" in style.replace(" ", "")
        elif tag == "table":
            self._in_milestone_table = False
        elif tag == "tr":
            self._row_tds = []
        elif tag == "a" and self._in_data_table:
            href = attrs_dict.get("href", "")
            if "case_id=" in href:
                m = re.search(r"case_id=(\d+)", href)
                if m:
                    self.case_ids.append(m.group(1))
        elif tag in ("td", "th"):
            self._cell_active = True
            self._cell_buf = ""
            if self._in_data_table:
                self._in_td = True

    def handle_endtag(self, tag):
        if tag == "div" and self._in_data_table:
            self._in_data_table = False
            if self._in_hidden_table:
                self._process_tuidui_table()
            self._tds = []
            self._in_hidden_table = False
            self._current_table_text = ""
        elif tag == "table":
            self._in_milestone_table = False
        elif tag == "tr":
            self._process_row()
        elif tag in ("td", "th"):
            if self._cell_active:
                text = self._cell_buf.strip()
                if text:
                    self._row_tds.append(text)
            self._cell_active = False
            self._in_td = False

    def handle_data(self, data):
        if self._cell_active:
            self._cell_buf += data
        if self._in_data_table:
            self._current_table_text += data
            if self._in_td:
                text = data.strip()
                if text:
                    self._tds.append(text)

    def _process_row(self):
        if not self._row_tds:
            return
        cells = self._row_tds
        self._row_tds = []
        if len(cells) == 2 and cells[0] == "項目" and cells[1] == "日期":
            self._in_milestone_table = True
            return
        if not self._in_milestone_table or len(cells) < 2:
            return
        label, value = cells[0], cells[1]
        if label == "備註" or not value:
            return
        if self.ROC_DATE_RE.match(value) and label not in self.tuidui_history:
            self.tuidui_history[label] = value

    def _process_tuidui_table(self):
        text = self._current_table_text
        pattern = r"(事業計畫申請日期|事業計畫核定日期|權利變換計畫申請日期|權利變換計畫核定日期|概要申請日期|概要核定日期)\s+([\d\.]+)"
        for match in re.finditer(pattern, text):
            label, value = match.groups()
            self.tuidui_history[label] = value


class TaipeiCaseParser(html.parser.HTMLParser):
    """Parse Taipei platform case page for 階段辦理過程."""

    def __init__(self):
        super().__init__()
        self.in_data2 = False
        self.stages = {}
        self._buffer = ""

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        if tag == "div" and attrs_dict.get("id") == "data2":
            self.in_data2 = True

    def handle_endtag(self, tag):
        if tag == "div" and self.in_data2:
            self.in_data2 = False
            self._flush_buffer()

    def handle_data(self, data):
        if not self.in_data2:
            return
        self._buffer += data + "\n"

    def _flush_buffer(self):
        if not self._buffer:
            return
        text = self._buffer.strip()
        for line in text.split("\n"):
            line = line.strip()
            if not line:
                continue
            date_match = re.search(r"(\d{4}/\d{2}/\d{2}|\d{3}\.\d{2}\.\d{2})$", line)
            if date_match:
                date = date_match.group(1)
                label = line[:date_match.start()].strip()
                if label:
                    self.stages[label] = date
        self._buffer = ""


# ──────────────────────────────────────────────────────────────────────────────
# Core Discovery Logic
# ──────────────────────────────────────────────────────────────────────────────

SEARCH_URL = "https://twur.nlma.gov.tw/zh/urban/rebuild/0"
VIEW_URL_BASE = "https://twur.nlma.gov.tw/zh/urban/rebuild/view/"
TAIPEI_CASE_URL_BASE = "https://gis.uro.taipei/r_progress_detail.aspx?case_id="

# Browser-like headers to avoid WAF blocking
BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
}


@dataclass
class DiscoveryResult:
    """Result of discovering links for one project."""
    project_id: str
    land_core: str
    twur_view_id: Optional[str] = None
    twur_url: str = ""
    city_case_ids: list[str] = field(default_factory=list)
    national_milestones: dict[str, str] = field(default_factory=dict)
    taipei_milestones: dict[str, str] = field(default_factory=dict)
    # Per-case milestone timelines: {case_id: {label: date}} — retained so node
    # links can be anchored by 核定日期 instead of list position.
    case_milestones: dict[str, dict[str, str]] = field(default_factory=dict)
    # Label → winning case_id from the last-write-wins stage merge, so slot
    # provenance (建照核發日期 included) is provable at the viewer.
    milestones_source: dict[str, str] = field(default_factory=dict)
    # Per-case 執行階段 (third.ashx) / 獎勵資料 (fourth.ashx) payloads.
    implementation: dict[str, dict[str, str]] = field(default_factory=dict)
    rewards: dict[str, dict[str, str]] = field(default_factory=dict)
    # §6.8 fragment evidence: {case_id: case_name} — cases the platform
    # returned for this family's parcel search but the name guard rejected.
    search_rejected: dict[str, str] = field(default_factory=dict)
    status: str = "unresolved"  # resolved, unresolved, multi-case, error
    error: str = ""


def build_land_core_key(record: CleanRecord) -> str:
    """Build land-identity core key from a CleanRecord.
    Uses district + section + first_parcel + land_count (or orig_count).
    Format: {district}{section}{first_parcel}地號等{count}筆"""
    parts = []
    if record.district_land:
        parts.append(record.district_land)
    if record.section:
        parts.append(record.section)
    core = "".join(parts)
    if record.first_parcel:
        core += record.first_parcel
    count = record.land_count or record.orig_count
    if count:
        core += f"地號等{count}筆"
    return core


def fetch_url(url: str, cache_dir: Optional[Path] = None, fresh: bool = False, max_retries: int = 3) -> str:
    """Fetch URL with optional caching and retry with exponential backoff."""
    if cache_dir:
        cache_dir.mkdir(parents=True, exist_ok=True)
        safe_name = re.sub(r"[^a-zA-Z0-9]", "_", url)
        cache_file = cache_dir / f"{safe_name}.html"
        if not fresh and cache_file.exists():
            return cache_file.read_text(encoding="utf-8")

    last_exception = None
    for attempt in range(max_retries + 1):
        try:
            req = urllib.request.Request(url, headers=BROWSER_HEADERS)
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read()
                # Handle gzip/deflate compression (servers honour our
                # Accept-Encoding header and may reply compressed).
                if raw[:2] == b"\x1f\x8b":  # gzip magic bytes
                    import gzip
                    import io
                    raw = gzip.GzipFile(fileobj=io.BytesIO(raw)).read()
                elif raw[:1] == b"\x1f" or resp.headers.get("Content-Encoding") == "deflate":
                    import zlib
                    raw = zlib.decompress(raw)
                html = raw.decode("utf-8", errors="replace")

            if cache_dir:
                cache_file.write_text(html, encoding="utf-8")
            return html

        except (ConnectionResetError, TimeoutError, urllib.error.URLError, OSError) as e:
            last_exception = e
            if attempt < max_retries:
                wait_time = 2 ** attempt  # 1s, 2s, 4s
                time.sleep(wait_time)
            else:
                raise

    raise last_exception


def extract_view_id_from_search(html: str) -> Optional[str]:
    """Parse search results HTML, return view_id if unique hit, else None."""
    parser = SearchResultParser()
    parser.feed(html)
    if len(parser.view_ids) == 1:
        return parser.view_ids[0]
    return None


def extract_case_ids_from_view(html: str) -> list[str]:
    """Parse view page HTML for 縣市政府案件連結 case_ids."""
    parser = ViewPageParser()
    parser.feed(html)
    return parser.case_ids


def extract_tuidui_history_from_view(html: str) -> dict[str, str]:
    """Parse view page for 推動歷程 timeline."""
    parser = ViewPageParser()
    parser.feed(html)
    return parser.tuidui_history


def extract_taipei_stage_process(html: str) -> dict[str, str]:
    """Parse Taipei case page for 階段辦理過程."""
    parser = TaipeiCaseParser()
    parser.feed(html)
    return parser.stages


# Fallback mapping file path
FALLBACK_MAPPING_FILE = Path("data/taipei_case_ids.json")


def load_fallback_mapping() -> dict:
    """Load fallback case_id mappings from JSON file."""
    try:
        return json.loads(FALLBACK_MAPPING_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def build_portal_index(cache_dir: Path, fresh: bool = False) -> list[dict]:
    """Crawl all list pages and build the portal index.
    Returns list of index entries: {core, view_id, title, implementer, approval_date}."""
    index_file = cache_dir / "portal_index.json"
    if not fresh and index_file.exists():
        return load_portal_index(cache_dir)

    index_entries = []
    page = 1
    base_url = "https://twur.nlma.gov.tw/zh/urban/rebuild/0"

    while True:
        params = {"city_id": "2", "page": str(page)}
        url = f"{base_url}?{urllib.parse.urlencode(params)}"
        try:
            html = fetch_url(url, cache_dir, fresh)
        except Exception as e:
            break

        parser = ListPageParser()
        parser.feed(html)

        if not parser.entries:
            break

        for entry in parser.entries:
            title = entry.get("title", "")
            from urtpe.cleanse import parse_name_id
            district, section, parcel, count = parse_name_id(title)
            if district and section and parcel:
                core_parts = [district, section]
                core = "".join(core_parts)
                core += parcel
                if count:
                    core += f"地號等{count}筆"
            else:
                core = title.replace("擬訂", "").replace("臺北市", "").replace("土地都市更新事業計畫及權利變換計畫案", "").replace("土地都市更新事業計畫案", "").replace("土地都市更新權利變換計畫案", "").strip()

            index_entries.append({
                "core": core,
                "view_id": entry["view_id"],
                "title": entry["title"],
                "implementer": entry.get("implementer", ""),
                "approval_date": entry.get("approval_date", ""),
            })

        if not parser.has_next_page:
            break

        page += 1
        time.sleep(0.5)

    save_portal_index(cache_dir, index_entries)
    return index_entries


def load_portal_index(cache_dir: Path) -> list[dict]:
    """Load portal index from JSON file."""
    index_file = cache_dir / "portal_index.json"
    try:
        return json.loads(index_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def save_portal_index(cache_dir: Path, index: list[dict]) -> None:
    """Save portal index to JSON file."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    index_file = cache_dir / "portal_index.json"
    index_file.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")


def lookup_in_portal_index(core: str, index: list[dict]) -> Optional[str]:
    """Look up a land core in the portal index.
    Returns view_id if unique match, None if 0 or >1 matches."""
    matches = [e for e in index if e["core"] == core]
    if len(matches) == 1:
        return matches[0]["view_id"]
    return None


def build_index_multimap(index: list[dict]) -> dict[str, list[dict]]:
    multimap: dict[str, list[dict]] = {}
    for entry in index:
        multimap.setdefault(entry["core"], []).append(entry)
    return multimap


def discover_project_links(
    project: Project,
    cache_dir: Optional[Path] = None,
    fresh: bool = False,
    delay: float = 1.0,
    portal_index: Optional[list[dict]] = None,
    use_playwright: bool = False,
) -> DiscoveryResult:
    """Discover official links for a single project.

    Taipei-first flow: search the Taipei platform's JSON API by
    section + parcel (works for every project, no national portal needed),
    then fetch milestone timelines per case_id via the same API.
    National portal is only used as a supplementary source for 推動歷程.
    """
    # Build land core from anchor record
    anchor = next(r for r in project.members if r.recno == project.anchor_recno)
    land_core = build_land_core_key(anchor)

    # Check per-project cache first
    if cache_dir and not fresh:
        cached = load_project_cache(cache_dir, project.project_id)
        if cached:
            return cached

    result = DiscoveryResult(project_id=project.project_id, land_core=land_core)

    # ── Step 1: Taipei platform search by section + parcel ──────────────────
    city_entries: list[dict] = []
    dropped_by_guard: dict[str, str] = {}
    if anchor.section and anchor.first_parcel:
        try:
            time.sleep(delay)
            city_entries = search_taipei_cases_api(
                anchor.section, anchor.first_parcel, dropped_out=dropped_by_guard
            )
        except Exception as e:
            result.error = f"Taipei search failed: {e}"
    result.search_rejected = dropped_by_guard

    city_ids = [e["case_id"] for e in city_entries]
    result.city_case_ids = city_ids

    # ── Step 2: milestones per case_id via JSON API ─────────────────────────
    all_taipei_milestones: dict[str, str] = {}
    milestones_source: dict[str, str] = {}
    case_names: list[str] = []
    for cid in city_ids:
        time.sleep(delay)
        try:
            ms = fetch_taipei_milestones_api(cid)
            merge_stage_milestones(all_taipei_milestones, milestones_source, cid, ms)
            result.case_milestones[cid] = ms
            for e in city_entries:
                if e["case_id"] == cid and e.get("case_name"):
                    case_names.append(e["case_name"])
                    break
        except Exception as e:
            result.error = f"Taipei milestones {cid} failed: {e}"
        # 執行階段 (third.ashx) — only the completed case carries values
        time.sleep(delay)
        try:
            result.implementation[cid] = fetch_taipei_implementation_api(cid)
        except Exception as e:
            result.error = f"{result.error}; " if result.error else ""
            result.error += f"Taipei implementation {cid} failed: {e}"
        # 獎勵資料 (fourth.ashx)
        time.sleep(delay)
        try:
            result.rewards[cid] = fetch_taipei_rewards_api(cid)
        except Exception as e:
            result.error = f"{result.error}; " if result.error else ""
            result.error += f"Taipei rewards {cid} failed: {e}"
    result.taipei_milestones = all_taipei_milestones
    result.milestones_source = milestones_source

    # ── Step 3 (supplementary): national portal for view URL + 推動歷程 ──────
    national_milestones = {}
    view_html = ""
    if portal_index:
        view_id = lookup_in_portal_index(land_core, portal_index)
        if not view_id:
            fb_entry = load_fallback_mapping().get(land_core, {})
            view_id = fb_entry.get("view_id")
        if view_id:
            result.twur_view_id = view_id
            result.twur_url = f"{VIEW_URL_BASE}{view_id}"
            try:
                time.sleep(delay)
                view_html = fetch_view_page(view_id, cache_dir, fresh)
                national_milestones = extract_tuidui_history_from_view(view_html)
            except Exception as e:
                if result.error:
                    result.error += "; "
                result.error += f"View page fetch failed: {e}"
                view_html = ""
    result.national_milestones = national_milestones

    # Determine final status based on what we actually obtained
    if city_ids and all_taipei_milestones:
        result.status = "resolved"
    elif city_ids:
        result.status = "resolved_no_city"
    else:
        result.status = "unresolved"

    # Save to cache
    if cache_dir:
        save_project_cache(cache_dir, project.project_id, result, view_html=view_html)

    return result


def fetch_view_page(view_id: str, cache_dir: Optional[Path] = None, fresh: bool = False) -> str:
    url = f"{VIEW_URL_BASE}{view_id}"
    return fetch_url(url, cache_dir, fresh)


def fetch_taipei_case(case_id: str, cache_dir: Optional[Path] = None, fresh: bool = False) -> str:
    url = f"{TAIPEI_CASE_URL_BASE}{case_id}"
    return fetch_url(url, cache_dir, fresh)


# ──────────────────────────────────────────────────────────────────────────────
# Taipei platform JSON API (ashx endpoints — fast, no HTML parsing)
# ──────────────────────────────────────────────────────────────────────────────

TAIPEI_SEARCH_API = "https://gis.uro.taipei/ashx/Get_updcase_list.ashx"
TAIPEI_TOP_API = "https://gis.uro.taipei/ashx/get_project168_top.ashx"
TAIPEI_STAGE_API = "https://gis.uro.taipei/ashx/Get_project168_second.ashx"
TAIPEI_THIRD_API = "https://gis.uro.taipei/ashx/Get_project168_third.ashx"
TAIPEI_FOURTH_API = "https://gis.uro.taipei/ashx/Get_project168_fourth.ashx"

# Milestone field mapping from Get_project168_second.ashx JSON keys
STAGE_FIELD_MAP = [
    ("Plan_Open_Date", "計畫公聽會日期"),
    ("Plan_Open_Date2", "權變公聽會日期"),
    ("outline_open_date", "概要公聽會日期"),
    ("Plan_App_Date", "申請計畫日期"),
    ("Plan_App_Date2", "申請權變日期"),
    ("outline_app_date", "申請概要日期"),
    ("outline_ok_date", "概要核准日期"),
    ("Show_Bull_Date", "公告公展日期"),
    ("Show_Bull_Date2", "權變公告公展日期"),
    ("Show_Open_Date", "公展公聽會日期"),
    ("Show_Open_Date2", "權變公展公聽會日期"),
    ("jud_ok_date", "審議通過日期"),
    ("jud_ok_date0", "概要審議會通過日期"),
    ("jud_ok_date2", "權變審議通過日期"),
    ("Stew_App_Date", "申請幹事會日期"),
    ("Stew_App_Date2", "權變申請幹事會日期"),
    ("Stew_Hold_Date", "召開幹事會日期"),
    ("Stew_Hold_Date2", "權變召開幹事會日期"),
    ("Review_app_date", "申請幹事複審日期"),
    ("Review_app_date2", "權變申請幹事複審日期"),
    ("Review_hold_date", "召開幹事複審日期"),
    ("Review_hold_date2", "權變召開幹事複審日期"),
    ("App_Hear_Date", "申請聽證日期"),
    ("App_Hear_Date2", "權變申請聽證日期"),
    ("Hold_Hear_Date", "召開聽證日期"),
    ("Hold_Hear_Date2", "權變召開聽證日期"),
    ("comm_hold_date0", "概要召開審議會日期"),
    ("comm_hold_date", "召開審議會日期"),
    ("comm_hold_date2", "權變召開審議會日期"),
    ("App_Chk_Date", "申請核定日期"),
    ("App_Chk_Date2", "權變申請核定日期"),
    ("Uro_Chk_Date", "核定日期"),
    ("Uro_Chk_Date2", "權變核定日期"),
    ("Blic_Date", "建照核發日期"),
]


def _post_taipei_api(url: str, params: dict, max_retries: int = 3) -> str:
    """POST to a Taipei ashx endpoint and return the decoded body."""
    last_exc = None
    for attempt in range(max_retries + 1):
        try:
            data = urllib.parse.urlencode(params).encode("utf-8")
            req = urllib.request.Request(url, data=data, headers=BROWSER_HEADERS)
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read()
                if raw[:2] == b"\x1f\x8b":  # gzip
                    import gzip
                    import io
                    raw = gzip.GzipFile(fileobj=io.BytesIO(raw)).read()
                return raw.decode("utf-8", errors="replace")
        except (ConnectionResetError, TimeoutError, urllib.error.URLError, OSError) as e:
            last_exc = e
            if attempt < max_retries:
                time.sleep(2 ** attempt)
            else:
                raise
    raise last_exception


def search_taipei_cases_api(section: str, parcel: str, dropped_out: Optional[dict] = None) -> list[dict]:
    """Search Taipei platform cases by land section + parcel.

    Args:
        section: 地段小段 name (e.g. 玉泉段二小段).
        parcel: first parcel number, may contain '-' (e.g. '263-19' or '40').
        dropped_out: optional dict filled with the guard-rejected entries
            ({case_id: case_name}) — cross-family pollution kept out of the
            result but retained as fragment-detection evidence (§6.8).

    Returns list of {case_id, case_name, schedule} dicts whose case_name
    carries the searched parcel (§6.7 guard shape).
    """
    if "-" in parcel:
        mono, _, suno = parcel.partition("-")
    else:
        mono, suno = parcel, "0"

    body = _post_taipei_api(TAIPEI_SEARCH_API, {
        "qitem": "qland",
        "sectstr": section,
        "monobuf": mono,
        "sunobuf": suno or "0",
    })
    try:
        entries = json.loads(body)
    except json.JSONDecodeError:
        return []

    # Keep only r_progress_detail cases (those carry milestone timelines).
    # The numeric detail case_id lives in the details URL, not the case_id
    # field (which may hold internal codes like 'R091306-02').
    # §6.7/§6.8 parcel guard: the platform matches at renewal-unit/R13 street-
    # block level, so sibling and foreign same-section cases ride along; keep
    # only cases whose own case_name carries the searched parcel.
    results = []
    dropped: dict[str, str] = {}
    seen: set[str] = set()
    for e in entries:
        details = e.get("details", "")
        m = re.search(r"case_id=(\d+)", details)
        if not m or "r_progress_detail.aspx" not in details:
            continue
        cid = m.group(1)
        if cid in seen:
            continue
        seen.add(cid)
        case_name = e.get("case_name", "")
        if not _case_name_carries_parcel(case_name, parcel):
            dropped[cid] = case_name
            continue
        results.append({
            "case_id": cid,
            "case_name": case_name,
            "schedule": e.get("schedule", ""),
        })
    if dropped_out is not None:
        dropped_out.update(dropped)
    return results


# Full-width → ASCII digit folding for parcel notation drift (§16.1 rule)
_FULLWIDTH_DIGITS = str.maketrans("０１２３４５６７８９", "0123456789")


def normalize_parcel_token(token: str) -> str:
    """Normalize parcel notation only: full-width→ASCII digits, 之→-."""
    return (token or "").translate(_FULLWIDTH_DIGITS).replace("之", "-")


def _case_name_carries_parcel(case_name: str, parcel: str) -> bool:
    """True when the case's own name declares the searched parcel.

    The name is the platform's per-case unit declaration (§6.7 evidence), so a
    name lacking the parcel marks a foreign/sibling case. Comparisons are
    notation-normalized (之 ↔ -, full-width ↔ ASCII):
    - exact form: the full parcel as a standalone token (115 keeps 115地號 /
      115等18筆 / 115、… lists; rejects 115-3, 2115, 1151);
    - legacy mono form: when searching <mono>-<suno>, an older approval naming
      the pre-subdivision stem (<mono>地號/<mono>等…) still counts.
    """
    name = normalize_parcel_token(case_name)
    parcel_n = normalize_parcel_token(str(parcel or ""))
    if not name or not parcel_n:
        return False

    def _token_hit(token: str, declared_only: bool) -> bool:
        pattern = rf"(?<![0-9.\-]){re.escape(token)}"
        pattern += r"[地等]" if declared_only else r"(?![0-9\-])"
        return re.search(pattern, name) is not None

    if _token_hit(parcel_n, declared_only=False):
        return True
    mono = parcel_n.partition("-")[0]
    return mono != parcel_n and bool(mono) and _token_hit(mono, declared_only=True)


def fetch_taipei_milestones_api(case_id: str) -> dict[str, str]:
    """Fetch 階段辦理過程 milestones via Get_project168_second.ashx."""
    body = _post_taipei_api(TAIPEI_STAGE_API, {"case_id": case_id})
    try:
        rows = json.loads(body)
    except json.JSONDecodeError:
        return {}
    if not isinstance(rows, list) or not rows:
        return {}

    milestones: dict[str, str] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        for field, label in STAGE_FIELD_MAP:
            val = row.get(field, "")
            if val and label not in milestones:
                # Normalise ISO datetimes (2020-11-17T00:00:00) to dates
                if "T" in str(val):
                    val = str(val).split("T")[0]
                milestones[label] = str(val)
    return milestones


def fetch_taipei_payload_api(url: str, case_id: str) -> dict[str, str]:
    """POST case_id to a payload endpoint (third/fourth.ashx) and return the row's
    non-empty fields as a plain dict. Empty/malformed bodies yield {}."""
    body = _post_taipei_api(url, {"case_id": case_id})
    try:
        rows = json.loads(body)
    except json.JSONDecodeError:
        return {}
    row = rows[0] if isinstance(rows, list) and rows else (rows if isinstance(rows, dict) else {})
    if not isinstance(row, dict):
        return {}
    return {k: str(v) for k, v in row.items() if v not in ("", None) and str(v).strip() != ""}


def fetch_taipei_implementation_api(case_id: str) -> dict[str, str]:
    """Fetch 執行階段 payload via Get_project168_third.ashx (non-empty fields only)."""
    return fetch_taipei_payload_api(TAIPEI_THIRD_API, case_id)


def fetch_taipei_rewards_api(case_id: str) -> dict[str, str]:
    """Fetch 獎勵資料 payload via Get_project168_fourth.ashx (non-empty fields only)."""
    return fetch_taipei_payload_api(TAIPEI_FOURTH_API, case_id)


def _project_cache_dir(cache_dir: Path, project_id: str) -> Path:
    safe_id = re.sub(r"[^\w\-]", "_", project_id)
    return cache_dir / safe_id


def load_project_cache(cache_dir: Path, project_id: str) -> Optional[DiscoveryResult]:
    project_cache = _project_cache_dir(cache_dir, project_id)
    result_file = project_cache / "result.json"
    if result_file.exists():
        try:
            data = json.loads(result_file.read_text(encoding="utf-8"))
            return DiscoveryResult(**data)
        except (json.JSONDecodeError, TypeError):
            pass
    return None


def save_project_cache(cache_dir: Path, project_id: str, result: DiscoveryResult, view_html: str = "") -> None:
    project_cache = _project_cache_dir(cache_dir, project_id)
    project_cache.mkdir(parents=True, exist_ok=True)

    result_file = project_cache / "result.json"
    result_file.write_text(json.dumps(asdict(result), ensure_ascii=False, indent=2), encoding="utf-8")

    if view_html:
        view_file = project_cache / "view.html"
        view_file.write_text(view_html, encoding="utf-8")

    # Taipei case pages are cached by fetch_url automatically


def _iso_date(s: str) -> str:
    """Normalize '2016/07/05' or '2016-07-05' to '2016-07-05' ('' if empty)."""
    return s.strip().replace("/", "-") if s else ""


def _shift_iso_date(iso: str, days: int) -> str:
    """Return iso shifted by N days ('' if unparseable)."""
    try:
        from datetime import date, timedelta
        y, m, d = (int(x) for x in iso.split("-"))
        return (date(y, m, d) + timedelta(days=days)).isoformat()
    except (ValueError, AttributeError):
        return ""


# third.ashx date fields surfaced as project milestones (design D3)
IMPLEMENTATION_MILESTONE_FIELDS = [
    ("Eng_Start_Date", "開工日期"),
    ("Ulic_Date", "使照核發日期"),
    ("Report_Date", "成果報備日期"),
]


def select_best_payload(payloads: dict[str, dict]) -> tuple[str, dict, list[str]]:
    """Pick the best-populated payload whole (never field-merged) per design D5.

    Returns (case_id, payload, review_flags). Empty/absent payloads are ignored;
    conflicting values across multiple carriers surface review flags.
    """
    candidates = {cid: p for cid, p in (payloads or {}).items() if p}
    if not candidates:
        return "", {}, []
    best_cid = max(candidates, key=lambda cid: len(candidates[cid]))
    flags: list[str] = []
    if len(candidates) > 1:
        others = [cid for cid in candidates if cid != best_cid]
        for key, val in candidates[best_cid].items():
            for other in others:
                if key in candidates[other] and candidates[other][key] != val:
                    flags.append(
                        f"payload {key} conflicts across cases: {best_cid}={val} vs {other}={candidates[other][key]}"
                    )
    return best_cid, candidates[best_cid], flags


def implementation_milestones(payload: dict) -> dict[str, str]:
    """Extract the third.ashx date fields as labelled milestones (non-empty only)."""
    return {
        label: payload[field]
        for field, label in IMPLEMENTATION_MILESTONE_FIELDS
        if payload.get(field)
    }


def merge_stage_milestones(
    all_ms: dict[str, str], source: dict[str, str], cid: str, ms: dict[str, str]
) -> None:
    """Last-write-wins merge of one case's stage milestones, recording which
    case won each label so slot provenance stays provable at the viewer."""
    for label, v in ms.items():
        all_ms[label] = v
        source[label] = cid


def _match_case_by_date(member_date: str, disc) -> str:
    """Find the city case whose 核定日期/權變核定日期 equals the node's date
    (exact first, then ±1 day). Returns case_id or ''."""
    if not member_date or not getattr(disc, "case_milestones", None):
        return ""
    target = _iso_date(member_date)
    candidates: dict[str, set[str]] = {}
    for cid, ms in disc.case_milestones.items():
        dates: set[str] = set()
        for label in ("核定日期", "權變核定日期"):
            iso = _iso_date(ms.get(label, ""))
            if iso:
                dates.add(iso)
        if dates:
            candidates[cid] = dates
    # exact match
    hits = [cid for cid, dates in candidates.items() if target in dates]
    if len(hits) == 1:
        return hits[0]
    # ±1 day tolerance (gazette vs committee date drift)
    near = {target, _shift_iso_date(target, 1), _shift_iso_date(target, -1)}
    hits = [cid for cid, dates in candidates.items() if dates & near]
    if len(hits) == 1:
        return hits[0]
    return ""


def detect_fragment_families(
    projects: list[Project], discovered: dict
) -> dict[str, tuple[str, int]]:
    """Detect §6.8 fragment families after node anchoring.

    A family is a merge candidate iff EVERY discovered case it keeps surfaces
    in exactly ONE other family's platform search — either kept there (shared
    first-parcel shapes: count drift 懷生段249 中正區↔大安區) or guard-rejected
    there (anchor-parcel changed: 南港段一小段101地號等41筆 → 19-1). The search
    scope is the corpus-wide evidence the per-node case linkage draws from;
    families whose cases surface across multiple other families (R13 street-
    block noise) or nowhere stay unflagged, per spec.

    Returns {fragment_project_id: (target_project_id, case_count)}.
    """
    surfaced_by_case: dict[str, set[str]] = {}
    kept_by_pid: dict[str, set[str]] = {}

    def _kept_and_rejected(disc) -> tuple[set, set]:
        if isinstance(disc, dict):
            # Same shape the attach shim accepts: {"taipei": [...], ...}
            return set(disc.get("taipei") or []), set((disc.get("search_rejected") or {}).keys())
        return (
            set(getattr(disc, "city_case_ids", None) or []),
            set((getattr(disc, "search_rejected", None) or {}).keys()),
        )

    for project in projects:
        disc = discovered.get(project.project_id)
        if disc is None:
            continue
        kept, rejected = _kept_and_rejected(disc)
        kept_by_pid[project.project_id] = kept
        for cid in kept | rejected:
            surfaced_by_case.setdefault(cid, set()).add(project.project_id)

    candidates: dict[str, tuple[str, int]] = {}
    for project in projects:
        kept = kept_by_pid.get(project.project_id) or set()
        if not kept:
            continue
        assocs = [
            surfaced_by_case.get(cid, set()) - {project.project_id}
            for cid in kept
        ]
        if not all(len(a) == 1 for a in assocs):
            continue
        targets = {next(iter(a)) for a in assocs}
        if len(targets) != 1:
            continue
        candidates[project.project_id] = (targets.pop(), len(kept))
    return candidates


_FRAGMENT_FLAG_PREFIX = "片段家族合併候選"


def _flag_fragment_families(projects: list[Project], candidates: dict[str, tuple[str, int]]) -> None:
    """Append 臨界對-style review flags on each fragment's anchor record.
    Review output only — no family membership or record structure changes."""
    by_pid = {p.project_id: p for p in projects}
    for frag_pid, (target_pid, n_cases) in candidates.items():
        project = by_pid.get(frag_pid)
        if project is None:
            continue
        anchor_record = next(
            (m for m in project.members if m.recno == project.anchor_recno),
            project.members[0] if project.members else None,
        )
        if anchor_record is None:
            continue
        flag = (
            f"{_FRAGMENT_FLAG_PREFIX}: 全部 {n_cases} 筆案例錨定於 "
            f"{target_pid}（合併候選，需人工確認）"
        )
        existing = anchor_record.review_flags
        if any(f.startswith(_FRAGMENT_FLAG_PREFIX) and target_pid in f for f in existing):
            continue
        existing.append(flag)


def attach_links_to_projects(projects: list[Project], discovered: dict) -> None:
    disc_by_pid = {}
    for k, v in discovered.items():
        if hasattr(v, 'project_id'):
            disc_by_pid[k] = v
        elif isinstance(v, dict):
            obj = type('DiscoveryDict', (object,), {})()
            obj.project_id = k
            obj.twur_url = v.get("twur", "")
            obj.city_case_ids = v.get("taipei", [])
            obj.national_milestones = v.get("milestones_national", {})
            obj.taipei_milestones = v.get("milestones_taipei", {})
            obj.case_milestones = v.get("case_milestones", {})
            obj.milestones_source = v.get("milestones_source", {})
            obj.implementation = v.get("implementation", {})
            obj.rewards = v.get("rewards", {})
            obj.search_rejected = v.get("search_rejected", {})
            disc_by_pid[k] = obj

    for project in projects:
        disc = disc_by_pid.get(project.project_id)
        if not disc:
            project.links = {
                "twur": "",
                "taipei": [],
                "milestones_national": {},
                "milestones_taipei": {},
            }
            continue

        project.links = {
            "twur": disc.twur_url,
            "taipei": disc.city_case_ids[:],
            "milestones_national": disc.national_milestones.copy(),
            "milestones_taipei": disc.taipei_milestones.copy(),
        }
        source_map = getattr(disc, "milestones_source", None) or {}
        if source_map:
            project.links["milestones_source"] = dict(source_map)

        # Implementation (third.ashx) / rewards (fourth.ashx): project-level
        # attachment with case provenance (design D2/D5). Date fields surface as
        # milestones; the rest goes into the emitted objects.
        impl_cid, impl_payload, impl_flags = select_best_payload(getattr(disc, "implementation", None) or {})
        if impl_payload:
            impl_out = dict(impl_payload)
            impl_out["case_id"] = impl_cid
            if impl_flags:
                impl_out["review_flags"] = impl_flags
            project.implementation = impl_out
            for label, date in implementation_milestones(impl_payload).items():
                project.links["milestones_taipei"][label] = date
                project.links.setdefault("milestones_source", {})[label] = impl_cid
        rew_cid, rew_payload, rew_flags = select_best_payload(getattr(disc, "rewards", None) or {})
        if rew_payload:
            rew_out = dict(rew_payload)
            rew_out["case_id"] = rew_cid
            if rew_flags:
                rew_out["review_flags"] = rew_flags
            project.rewards = rew_out

        for member in project.members:
            node_links = {"taipei": [], "milestones_national": {}, "milestones_taipei": {}}
            track = member.track

            # Spec (official-link-discovery): per-stage city links land on the
            # node whose 核定日期 matches the case's approval date. Fall back to
            # the legacy positional heuristic only when dates cannot disambiguate.
            matched = _match_case_by_date(member.date, disc)
            if matched:
                node_links["taipei"].append(matched)
            elif "事業計畫" in track and disc.city_case_ids:
                node_links["taipei"].append(disc.city_case_ids[0])
            elif "權利變換" in track and len(disc.city_case_ids) > 1:
                node_links["taipei"].append(disc.city_case_ids[1])
            elif "權利變換" in track and disc.city_case_ids:
                node_links["taipei"].append(disc.city_case_ids[0])

            member.links = node_links

            # Per-record implementation snapshot (additive, optional): the case
            # this record anchors to may carry its own third.ashx payload, so
            # per-record callouts can show plan-revision drift. Records whose
            # case has an empty/absent payload carry nothing.
            for cid in node_links["taipei"]:
                payload = (getattr(disc, "implementation", None) or {}).get(cid)
                if payload:
                    snapshot = dict(payload)
                    snapshot["case_id"] = cid
                    member.implementation = snapshot
                    break

    # §6.8: after node anchoring, surface fragment families as merge
    # candidates (review flags on anchor records; no family mutation).
    _flag_fragment_families(projects, detect_fragment_families(projects, discovered))


class LinksDiscovery:
    """High-level discovery orchestrator with CLI-friendly interface."""

    def __init__(self, cache_dir: str = "data/.link_cache", delay: float = 1.0):
        self.cache_dir = Path(cache_dir)
        self.delay = delay

    def run(self, projects: list[Project], fresh: bool = False, use_playwright: bool = False) -> dict[str, DiscoveryResult]:
        """Run discovery for all projects."""
        if fresh:
            if self.cache_dir.exists():
                shutil.rmtree(self.cache_dir)
            self.cache_dir.mkdir(parents=True, exist_ok=True)

        portal_index = build_portal_index(self.cache_dir, fresh)
        multimap = build_index_multimap(portal_index)

        sorted_projects = sorted(projects, key=lambda p: p.project_id)

        results = {}
        for project in sorted_projects:
            result = discover_project_links(
                project,
                self.cache_dir,
                fresh,
                self.delay,
                portal_index,
                use_playwright=use_playwright
            )
            results[project.project_id] = result

        return results

    def write_crawl_log(self, results: dict[str, DiscoveryResult], out_path: str) -> None:
        lines = ["project_id\tland_core\tstatus\ttwur_url\tcity_case_ids\tnational_milestones\ttaipei_milestones\terror"]
        for r in results.values():
            lines.append("\t".join([
                r.project_id,
                r.land_core,
                r.status,
                r.twur_url,
                "|".join(r.city_case_ids),
                "|".join(f"{k}:{v}" for k, v in r.national_milestones.items()),
                "|".join(f"{k}:{v}" for k, v in r.taipei_milestones.items()),
                r.error,
            ]))
        Path(out_path).write_text("\n".join(lines) + "\n", encoding="utf-8")


async def _search_taipei_case_ids(land_core: str) -> TaipeiSearchResult:
    try:
        async with TaipeiPlaywrightSearcher(headless=True) as searcher:
            return await searcher.search_by_land_core(land_core)
    except Exception as e:
        return TaipeiSearchResult(
            case_ids=[],
            status="error",
            error=str(e)
        )


if __name__ == "__main__":
    pass