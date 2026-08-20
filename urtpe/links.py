"""Official link discovery adapter: crawls national portal and Taipei platform,
joins by land-identity core, scrapes timelines, and attaches to projects."""

from __future__ import annotations

import html.parser
import re
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from urtpe.models import CleanRecord, Project


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
            # Check if this is a data row (has td children with links)
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
            # Extract view ID from /zh/urban/rebuild/view/771
            m = re.search(r"/view/(\d+)", self.link_href)
            if m:
                self.view_ids.append(m.group(1))
            self.link_href = ""


class ViewPageParser(html.parser.HTMLParser):
    """Parse national portal view page for 縣市政府案件連結 and 推動歷程."""

    def __init__(self):
        super().__init__()
        self.case_ids = []
        self.tuidui_history = {}
        self._in_data_table = False
        self._in_hidden_table = False
        self._in_td = False
        self._tds = []
        self._current_table_text = ""

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
        elif tag == "a" and self._in_data_table:
            href = attrs_dict.get("href", "")
            if "case_id=" in href:
                m = re.search(r"case_id=(\d+)", href)
                if m:
                    self.case_ids.append(m.group(1))
        elif tag in ("td", "th") and self._in_data_table:
            self._in_td = True

    def handle_endtag(self, tag):
        if tag == "div" and self._in_data_table:
            self._in_data_table = False
            if self._in_hidden_table:
                self._process_tuidui_table()
            self._tds = []
            self._in_hidden_table = False
            self._current_table_text = ""
        elif tag in ("td", "th") and self._in_td:
            self._in_td = False

    def handle_data(self, data):
        if self._in_data_table:
            self._current_table_text += data
            if self._in_td:
                text = data.strip()
                if text:
                    self._tds.append(text)

    def _process_tuidui_table(self):
        """Process the hidden table for 推動歷程."""
        # Use the full table text for more robust parsing
        text = self._current_table_text
        # Look for patterns like "事業計畫申請日期 101.12.28"
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
        """Process accumulated text for stage milestones."""
        if not self._buffer:
            return
        text = self._buffer.strip()
        # Process line by line - each line has label then date
        for line in text.split("\n"):
            line = line.strip()
            if not line:
                continue
            # Match patterns like "計畫公聽會日期 2012/10/21" or "申請計畫日期 2012/11/08"
            # Date patterns: YYYY/MM/DD or YYY.MM.DD
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


def fetch_url(url: str, cache_dir: Optional[Path] = None, fresh: bool = False) -> str:
    """Fetch URL with optional caching."""
    if cache_dir:
        cache_dir.mkdir(parents=True, exist_ok=True)
        # Safe filename from URL
        safe_name = re.sub(r"[^a-zA-Z0-9]", "_", url)
        cache_file = cache_dir / f"{safe_name}.html"
        if not fresh and cache_file.exists():
            return cache_file.read_text(encoding="utf-8")

    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; urTPE/1.0)"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        html = resp.read().decode("utf-8", errors="replace")

    if cache_dir:
        cache_file.write_text(html, encoding="utf-8")

    return html


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


def search_national_portal(land_core: str, cache_dir: Optional[Path] = None, fresh: bool = False) -> Optional[str]:
    """Search national portal for a land core, return view_id if unique."""
    params = {"city_id": "2", "title": land_core}
    url = f"{SEARCH_URL}?{urllib.parse.urlencode(params)}"
    html = fetch_url(url, cache_dir, fresh)
    return extract_view_id_from_search(html)


def fetch_view_page(view_id: str, cache_dir: Optional[Path] = None, fresh: bool = False) -> str:
    """Fetch national portal view page by ID."""
    url = f"{VIEW_URL_BASE}{view_id}"
    return fetch_url(url, cache_dir, fresh)


def fetch_taipei_case(case_id: str, cache_dir: Optional[Path] = None, fresh: bool = False) -> str:
    """Fetch Taipei platform case page by case_id."""
    url = f"{TAIPEI_CASE_URL_BASE}{case_id}"
    return fetch_url(url, cache_dir, fresh)


def discover_project_links(
    project: Project,
    cache_dir: Optional[Path] = None,
    fresh: bool = False,
    delay: float = 1.0,
) -> DiscoveryResult:
    """Discover official links for a single project."""
    # Build land core from anchor record
    anchor = next(r for r in project.members if r.recno == project.anchor_recno)
    land_core = build_land_core_key(anchor)

    result = DiscoveryResult(project_id=project.project_id, land_core=land_core)

    # Search national portal
    view_id = search_national_portal(land_core, cache_dir, fresh)
    if not view_id:
        result.status = "unresolved"
        return result

    result.twur_view_id = view_id
    result.twur_url = f"{VIEW_URL_BASE}{view_id}"

    # Fetch view page
    time.sleep(delay)
    view_html = fetch_view_page(view_id, cache_dir, fresh)

    # Extract city case IDs
    city_ids = extract_case_ids_from_view(view_html)
    result.city_case_ids = city_ids

    # Extract national milestones (推動歷程)
    result.national_milestones = extract_tuidui_history_from_view(view_html)

    # For each city case_id, fetch Taipei page and extract milestones
    all_taipei_milestones = {}
    for cid in city_ids:
        time.sleep(delay)
        taipei_html = fetch_taipei_case(cid, cache_dir, fresh)
        milestones = extract_taipei_stage_process(taipei_html)
        all_taipei_milestones.update(milestones)

    result.taipei_milestones = all_taipei_milestones
    result.status = "resolved" if city_ids else "resolved_no_city"
    return result


def attach_links_to_projects(projects: list[Project], discovered: dict) -> None:
    """Attach discovered links and milestones to projects and their member nodes.
    `discovered` can be a dict of DiscoveryResult objects or plain dicts (for tests)."""
    # Build lookup by project_id, handling both DiscoveryResult and dict
    disc_by_pid = {}
    for k, v in discovered.items():
        if hasattr(v, 'project_id'):  # DiscoveryResult object
            disc_by_pid[k] = v
        elif isinstance(v, dict):  # plain dict from tests
            # Convert dict to object with attribute access
            obj = type('DiscoveryDict', (object,), {})()
            obj.project_id = k
            obj.twur_url = v.get("twur", "")
            obj.city_case_ids = v.get("taipei", [])
            obj.national_milestones = v.get("milestones_national", {})
            obj.taipei_milestones = v.get("milestones_taipei", {})
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

        # Project-level links
        project.links = {
            "twur": disc.twur_url,
            "taipei": disc.city_case_ids[:],
            "milestones_national": disc.national_milestones.copy(),
            "milestones_taipei": disc.taipei_milestones.copy(),
        }

        # Per-node links: attribute city case_ids by stage/track
        for member in project.members:
            node_links = {"taipei": [], "milestones_national": {}, "milestones_taipei": {}}
            track = member.track

            # Simple attribution: 事業計畫 -> first case_id, 權利變換 -> second case_id
            if "事業計畫" in track and disc.city_case_ids:
                node_links["taipei"].append(disc.city_case_ids[0])
            elif "權利變換" in track and len(disc.city_case_ids) > 1:
                node_links["taipei"].append(disc.city_case_ids[1])
            elif "權利變換" in track and disc.city_case_ids:
                node_links["taipei"].append(disc.city_case_ids[0])

            member.links = node_links


class LinksDiscovery:
    """High-level discovery orchestrator with CLI-friendly interface."""

    def __init__(self, cache_dir: str = "data/.link_cache", delay: float = 1.0):
        self.cache_dir = Path(cache_dir)
        self.delay = delay

    def run(self, projects: list[Project], fresh: bool = False) -> dict[str, DiscoveryResult]:
        """Run discovery for all projects."""
        results = {}
        for project in projects:
            result = discover_project_links(project, self.cache_dir, fresh, self.delay)
            results[project.project_id] = result
        return results

    def write_crawl_log(self, results: dict[str, DiscoveryResult], out_path: str) -> None:
        """Write per-project crawl status to TSV log."""
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