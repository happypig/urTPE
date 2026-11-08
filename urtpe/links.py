"""Official link discovery adapter: crawls national portal and Taipei platform,
joins by land-identity core, scrapes timelines, and attaches to projects."""

from __future__ import annotations

import asyncio
import html.parser
import json
import re
import shutil
import sys
import time
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional

from urtpe.models import CleanRecord, Project
from urtpe.permit_sources import (
    build_permit_index,
    match_project_permits,
    parse_permit_xml,
    permit_review_flags,
    select_permit_witness,
)
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
    # Harvested candidate names {case_id: case_name} — kept candidates from the
    # platform search response; enables landcore similarity and virtual-node
    # stage/track derivation for orphans without a PDF record.
    candidate_names: dict[str, str] = field(default_factory=dict)
    # Per-case schedule from the search response (已核准/已駁回/自行撤回/已失效/
    # 審查中/施工中) — explains each case's state and why a project whose cases
    # were all rejected/withdrawn/lapsed has no national-portal page (§6.14).
    case_schedules: dict[str, str] = field(default_factory=dict)
    # Case_ids extracted from this project's own national view page 相關連結 —
    # identity-verified by the portal itself, exempt from the landcore
    # similarity gate in ghost creation (parcel-less case names score 0.0).
    view_verified_case_ids: list[str] = field(default_factory=list)
    # supersede-headerless-cases-and-discover-new-ids D3: the case header
    # (基本資料 目前辦理情形, get_project168_top NAME) the last refresh read per
    # case, so the offline selector can see a 無 case; and {old: new} for a case
    # the city re-filed under a new id (11211211 → 11409026).
    case_headers: dict[str, str] = field(default_factory=dict)
    superseded_by: dict[str, str] = field(default_factory=dict)
    # §8 viewer-UX (reject-foreign-view-cases): the header row's CASE_NAME —
    # the city's own case name, distinct from the NAME state field — persisted
    # per case, so the view-verified verification and the offer step can decide
    # offline after the run.
    case_case_names: dict[str, str] = field(default_factory=dict)
    # §8: view-verified ids the city's own case name rejected
    # {case_id: {reason, shape, label_ok, city_ok}} — named, never dropped
    # silently (the truncated-records rule).
    view_rejected: dict[str, dict] = field(default_factory=dict)
    # §8: rejected ids this project ADOPTED from their wrong holder
    # {case_id: source_project_id} — the offer step's provenance record.
    adopted_from_view: dict[str, str] = field(default_factory=dict)
    # label-by-own-name (C10): the national page's own 案名 — the <title>'s
    # project name. The portal names the project by its first 擬訂 case; the
    # viewer labels 國 with it (452 of 632 projects showed the wrong name under
    # the current-node rule). Parsed from the cached view.html, no request.
    twur_name: str = ""
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


# Fallback mapping file path — the single definition (P2.3): urtpe/cli.py imports
# this constant rather than hardcoding a second copy. Resolved from the repository
# root, not the CWD, so a clone in any working directory finds the tracked file.
FALLBACK_MAPPING_FILE = Path(__file__).resolve().parents[1] / "data" / "taipei_case_ids.json"


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
        previous = load_portal_index(cache_dir)
        if previous:
            print(f"[INFO] portal index cached: {len(previous)} entries",
                  file=sys.stderr)
        return previous

    index_entries = []
    previous_size = 0
    if index_file.exists():
        try:
            previous_size = len(json.loads(index_file.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, OSError):
            previous_size = 0
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
    # Completeness signal (P3.3): a WAF-shortened crawl silently saves a smaller
    # index — the only reachability path for the older identities. A big drop is
    # reported loudly; the caller decides whether to proceed.
    if previous_size and len(index_entries) < previous_size * 0.8:
        print(f"[WARN] portal index shrank: {len(index_entries)} entries vs "
              f"{previous_size} before — the crawl was likely cut short (WAF). "
              f"Re-run --fresh or investigate before trusting portal joins.",
              file=sys.stderr)
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


def _sorted_orphan_nodes(nodes: list[dict]) -> list[dict]:
    """Publish orphan nodes in a total order rather than the order they arrived in.

    The list is built by iterating an unordered collection of case ids, so its order
    tracked the concurrent Taipei fetches: two consecutive `--from-js --links` runs emitted
    the same cases swapped, in 97 projects. Pinning PYTHONHASHSEED did not fix it, so the
    driver is fetch completion order rather than string hashing.

    Sorting by `case_id` makes the order total without changing what is emitted. Python's
    sort is stable, so equal keys keep their arrival order rather than shuffling.
    """
    return sorted(nodes or [], key=lambda n: str(n.get("case_id") or ""))


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
            # label-by-own-name: caches written before twur_name existed carry
            # the page on disk — parse it (no request) so the 國 label has the
            # portal's own name on the next emit.
            if not cached.twur_name and cached.twur_view_id:
                _vh = resolve_cache_dir(cache_dir, project.project_id) / "view.html"
                if _vh.is_file():
                    try:
                        cached.twur_name = parse_view_title(_vh.read_text(encoding="utf-8"))
                        if cached.twur_name:
                            save_project_cache(cache_dir, project.project_id, cached)
                    except OSError:
                        pass
            return cached

    # B3 (Batch B): a fresh re-discovery starts from a bare DiscoveryResult, so
    # saving it would silently wipe the fields only refresh_project writes
    # (case_headers, superseded_by, case_case_names, view_rejected,
    # adopted_from_view). Carry them forward from the prior cache: they are the
    # refresh's evidence, and dropping them would make one --fresh run erase
    # what the last refresh read (628 of 726 caches lack case_headers; a fresh
    # run would also have emptied the 99 that hold them). The refresh's own
    # re-derivation is what may clear these, not discovery.
    prior = None
    if cache_dir and fresh:
        prior = load_project_cache(cache_dir, project.project_id)

    result = DiscoveryResult(project_id=project.project_id, land_core=land_core)
    if prior is not None:
        result.case_headers = dict(prior.case_headers)
        result.superseded_by = dict(prior.superseded_by)
        result.case_case_names = dict(prior.case_case_names)
        result.view_rejected = {k: dict(v) for k, v in prior.view_rejected.items()}
        result.adopted_from_view = dict(prior.adopted_from_view)

    # ── Step 1: Taipei platform search by section + parcel ──────────────────
    city_entries: list[dict] = []
    dropped_by_guard: dict[str, str] = {}
    if anchor.section and anchor.first_parcel:
        try:
            time.sleep(delay)
            # bind-the-unplaced-by-searching-the-cell-section: the 地號 cell's
            # section is a further form to ask for — the gazette's 案名 and 地號
            # columns can disagree about which 段小段 a unit is in, and the
            # city indexes the 地號 column's form (河堤五小段 vs 河堤段五小段).
            extra_sections = []
            cell_section = getattr(anchor, "section_land", "") or ""
            if cell_section and cell_section != anchor.section:
                extra_sections.append(cell_section)
            try:
                city_entries = search_taipei_cases_api(
                    anchor.section, anchor.first_parcel, dropped_out=dropped_by_guard,
                    # The anchor's own 案名 is what corroborates a parcel-less case name; without
                    # it a named-area unit like 崇仁新村 can never be corroborated and both of
                    # its Taipei cases stay rejected.
                    anchor_name=anchor.name,
                    extra_sections=extra_sections,
                )
            except TypeError:
                # an adapter that does not take the extra forms (a test double)
                city_entries = search_taipei_cases_api(
                    anchor.section, anchor.first_parcel, dropped_out=dropped_by_guard,
                    anchor_name=anchor.name,
                )
        except Exception as e:
            result.error = f"Taipei search failed: {e}"
    result.search_rejected = dropped_by_guard
    result.candidate_names = {
        e["case_id"]: e.get("case_name", "")
        for e in city_entries
        if e.get("case_id")
    }
    result.case_schedules = {
        e["case_id"]: e.get("schedule", "")
        for e in city_entries
        if e.get("case_id") and e.get("schedule")
    }

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
    view_id = None
    if portal_index:
        view_id = lookup_in_portal_index(land_core, portal_index)
        if not view_id:
            fb_entry = load_fallback_mapping().get(land_core, {})
            view_id = fb_entry.get("view_id")
    if not view_id and cache_dir:
        # Last link in the chain: a human-verified record. Read here, during discovery,
        # rather than from `load_project_cache` -- that function can only see a record
        # from inside its `result.json` branch, so on an empty cache (every fresh clone,
        # since `.link_cache/` is not version-controlled) the table was never consulted and
        # the committed dataset could not be rebuilt. Returning a synthetic result from the
        # cache read instead would satisfy the link and leave every other field empty.
        entry = load_twur_overrides(cache_dir).get(project.project_id)
        view_id = entry.get("twur_view_id") if entry else None
    if view_id:
        result.twur_view_id = view_id
        result.twur_url = f"{VIEW_URL_BASE}{view_id}"
        try:
            time.sleep(delay)
            view_html = fetch_view_page(view_id, cache_dir, fresh)
            national_milestones = extract_tuidui_history_from_view(view_html)
            result.twur_name = parse_view_title(view_html)
            _absorb_view_case_ids(project, result, view_html, delay,
                                  all_taipei_milestones, milestones_source)
        except Exception as e:
            if result.error:
                result.error += "; "
            result.error += f"View page fetch failed: {e}"
            view_html = ""
    result.national_milestones = national_milestones

    # Determine final status based on what we actually obtained. Read the result's own
    # case ids, not the Step 1 local: ids absorbed from the view page count, or an
    # overridden project reads "unresolved" while carrying both its links and milestones.
    found_ids = result.city_case_ids
    if found_ids and all_taipei_milestones:
        result.status = "resolved"
    elif found_ids:
        result.status = "resolved_no_city"
    else:
        result.status = "unresolved"

    # Save to cache
    if cache_dir:
        save_project_cache(cache_dir, project.project_id, result, view_html=view_html)

    return result


def parse_view_title(view_html: str) -> str:
    """The national page's own 案名 — the <title>'s project name before the
    "-都更查詢" suffix (label-by-own-name; the portal names the project by its
    first 擬訂 case). Empty when the page has no parseable title."""
    m = re.search(r"<title>(.*?)-都更查詢", view_html or "")
    return m.group(1).strip() if m else ""


def _absorb_view_case_ids(project, result: "DiscoveryResult", view_html: str, delay: float,
                          all_taipei_milestones: dict, milestones_source: dict) -> None:
    """Take the city case ids off the national view page and resolve their milestones.

    The view page lists the project's own cases under 縣市政府案件連結. For a project whose
    parcel the city API cannot match -- the parcel the city prints differs from the one in the
    gazette -- that block is the only place the case id is written down at all.

    `extract_case_ids_from_view` and the `view_verified_case_ids` field both existed, and
    `attach_links_to_projects` already skips its similarity gate for view-verified ids, but
    nothing ever populated the field: the extractor was called from tests and nowhere else.
    So a project reached this way kept an empty `city_case_ids` while the page named its case,
    and rendered a national-portal link with no city link beside it.

    The ids are marked view-verified rather than merely added, because a parcel-less case name
    scores 0.0 against the project's land core and would otherwise be rejected as unrelated.
    """
    ids = [c for c in extract_case_ids_from_view(view_html) if c]
    if not ids:
        return
    result.view_verified_case_ids = list(ids)
    # S3a (Batch C residual): an id a previous refresh rejected (§8) must not be
    # re-fetched on every later absorb — its milestones sit in case_milestones
    # where no node, orphan, edge or badge reads them (measured: 10202065,
    # 09608220, 09511211, 09807161). Skip them here; the §8 gate below drops
    # any stale entry.
    rejected = set(getattr(result, "view_rejected", {}) or {})
    ids = [c for c in ids if c not in rejected]
    known = list(result.city_case_ids)
    fresh_ids = [c for c in ids if c not in known]
    if fresh_ids:
        result.city_case_ids = known + fresh_ids
    for cid in fresh_ids:
        time.sleep(delay)
        try:
            ms = fetch_taipei_milestones_api(cid)
            merge_stage_milestones(all_taipei_milestones, milestones_source, cid, ms)
            result.case_milestones[cid] = ms
        except Exception as e:
            if result.error:
                result.error += "; "
            result.error += f"View-page milestone {cid} failed: {e}"


def fetch_view_page(view_id: str, cache_dir: Optional[Path] = None, fresh: bool = False) -> str:
    url = f"{VIEW_URL_BASE}{view_id}"
    return fetch_url(url, cache_dir, fresh)


def fetch_portal_title_search(title: str, city_id: str = "2",
                              cache_dir: Optional[Path] = None,
                              fresh: bool = False) -> list[dict]:
    """The national portal's own title search — the THIRD id source.

    The city's parcel search does not index every approved case. The 懷生段
    一小段928 case (10002141) is indexed by no parcel search under any
    section form the gazette prints, yet the portal's
    `?title=<段小段>&city_id=2` search finds it.

    Each result carries the unit's view id and the case ids the page's
    相關連結 block names. An empty result is not a failure — the portal's
    WAF resets connections, and the caller treats every id it returns as a
    CANDIDATE that the case's own header must confirm.

    The title is the 段小段, URL-encoded: a Chinese section in a raw URL
    raises UnicodeEncodeError under ASCII.
    """
    import urllib.parse
    params = {"title": title, "city_id": str(city_id)}
    url = f"{SEARCH_URL}?{urllib.parse.urlencode(params)}"
    try:
        html = fetch_url(url, cache_dir, fresh)
    except Exception:
        return []
    parser = ListPageParser()
    parser.feed(html)
    out: list[dict] = []
    for entry in parser.entries:
        view_id = entry.get("view_id")
        if not view_id:
            continue
        title_text = entry.get("title", "")
        try:
            view_html = fetch_view_page(view_id, cache_dir, fresh)
        except Exception:
            view_html = ""
        case_ids = extract_case_ids_from_view(view_html) if view_html else []
        milestones = extract_tuidui_history_from_view(view_html) if view_html else {}
        out.append({"view_id": view_id, "title": title_text,
                    "case_ids": case_ids, "milestones": milestones})
    return out


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
# D9c-2a: the 168 fast-track programme's own case list. It names case ids the
# parcel search does not index (10708311, 11412011 — live probe 2026-11-05),
# so it is the pipeline's second id source.
TAIPEI_168_LIST_API = "https://gis.uro.taipei/ashx/Get_project168.ashx"

# Twin-bridge ghost gate: an orphan with no name and no attribution still
# anchors when its per-case milestone record shares at least this many exact
# (label, date) pairs with cases already anchored to the same unit — shared
# process history as the stand-in for landcore similarity until case_name
# harvesting lands.
TWIN_BRIDGE_MIN_SHARED_DATES = 3

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


def search_taipei_cases_api(section: str, parcel: str, dropped_out: Optional[dict] = None,
                            anchor_name: str = "",
                            extra_sections: Optional[list] = None) -> list[dict]:
    """Search Taipei platform cases by land section + parcel.

    Args:
        section: 地段小段 name (e.g. 玉泉段二小段).
        parcel: first parcel number, may contain '-' (e.g. '263-19' or '40').
        dropped_out: optional dict filled with the guard-rejected entries
            ({case_id: case_name}) — cross-family pollution kept out of the
            result but retained as fragment-detection evidence (§6.8).
        anchor_name: the gazette record's own 案名, used only to corroborate a
            case whose name declares no 地號 at all (see `_corroborated_area`).
        extra_sections: further section forms to try after the first form
            returns nothing — the 地號 cell's section, which is the form the
            city indexes when the gazette's 案名 and 地號 columns disagree
            (河堤五小段 vs 河堤段五小段, design D4).

    Returns list of {case_id, case_name, schedule} dicts whose case_name
    carries the searched parcel (§6.7 guard shape) or is a corroborated named-area case.
    """
    return _search_taipei_raw(section, parcel, guard=True, dropped_out=dropped_out,
                              anchor_name=anchor_name,
                              extra_sections=extra_sections)


def search_taipei_cases_for_node(section: str, parcel: str,
                                 extra_sections: Optional[list] = None) -> list[dict]:
    """The all-parcel search's raw form (resolve-recno-case step 4, design D5).

    The §6.7 name guard keys on the SEARCHED parcel, but a case found under a
    non-first parcel is declared under the node's own first parcel (南港566's
    plan case 10006032 hides under parcel 567 while its name says 566) — the
    guard would drop exactly the cases this step exists to find. The node's
    own 案名 comparison in `resolve_node_cases` is the acceptance test instead.
    """
    return _search_taipei_raw(section, parcel, guard=False,
                              extra_sections=extra_sections)


def _search_taipei_raw(section: str, parcel: str, guard: bool = True,
                       dropped_out: Optional[dict] = None,
                       anchor_name: str = "",
                       extra_sections: Optional[list] = None) -> list[dict]:
    def _query(sec: str, p: str) -> list:
        if "-" in p:
            mono, _, suno = p.partition("-")
        else:
            mono, suno = p, "0"
        body = _post_taipei_api(TAIPEI_SEARCH_API, {
            "qitem": "qland",
            "sectstr": sec,
            "monobuf": mono,
            "sunobuf": suno or "0",
        })
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            return []

    # Both halves of the key drift from what the city prints, so an empty answer is retried
    # across the small cross-product of the two known variants: printed parcel vs its
    # pre-subdivision stem, printed section vs the same section without its place name.
    # Bounded to three retries and only on an empty body -- an unmatchable project must not
    # fan out into a sweep against a WAF-fronted endpoint.
    #
    # The 地號 cell's section is a further form (design D4): the gazette's 案名
    # and 地號 columns can disagree about which 段小段 the unit is in, and the
    # city indexes the 地號 column's form. The extra forms are tried only after
    # the 案名's form returns nothing, so the request count does not grow for
    # the projects whose 案名 is already right.
    stem = parcel.partition("-")[0]
    sections = _section_variants(section, anchor_name)
    for extra in (extra_sections or ()):
        extra = str(extra or "").strip()
        if extra and extra not in sections:
            sections.append(extra)
    parcels = [parcel] if stem == parcel else [parcel, stem]

    entries: list = []
    for sec in sections:
        for p in parcels:
            entries = _query(sec, p)
            if entries:
                break
        if entries:
            break

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
        if guard and not (_case_name_carries_parcel(case_name, parcel)
                          or _corroborated_area(anchor_name, case_name)):
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


def derive_stage_from_case_name(name: str) -> str:
    """Derive the approval stage (擬訂 / 變更 / 變更(第N次)) from a case name."""
    n = (name or "").strip()
    if not n:
        return ""
    if n.startswith("擬訂"):
        return "擬訂"
    m = re.match(r"^變更(?:\s*[（(]?第([一二三四五六七八九十百\d]+)次[）)]?)?", n)
    if m:
        return f"變更(第{m.group(1)}次)" if m.group(1) else "變更"
    return ""


def derive_track_from_case_name(name: str) -> str:
    """Derive 事業種類 from a case name using the TRACK vocabulary."""
    n = name or ""
    if "事業概要" in n:
        return "事業概要"
    # The city shortens 事業概要 to 概要 in some case names
    # (南港531-4's 09406102: …土地都市更新概要案). 概要 alone is still the
    # 事業概要 track — a ghost with an empty track renders no row (the
    # viewer's virtual-node filter), so the short form must map too.
    if "概要" in n:
        return "事業概要"
    has_plan = "事業計畫" in n
    has_rw = "權利變換" in n
    if has_plan and has_rw:
        return "事業計畫、權利變換"
    if has_rw:
        return "權利變換"
    if has_plan:
        return "事業計畫"
    if "都市更新計畫" in n:
        return "都市更新計畫"
    return ""


def extract_landcore_from_case_name(name: str) -> str:
    """Extract landcore from a case name, skipping prefixes like '擬訂臺北市'.

    The landcore format is: {district}{section}{first_parcel}地號等{count}筆
    e.g., "文山區木柵段三小段623地號等39筆" (段小段) or
    "松山區民生段140-9地號等3筆" (single-段 sections — village/older units;
    rejecting them silently dropped every orphan of the family, §6.14).

    parse-listed-parcel-names (Batch C, C4): three measured city shapes the
    single regex missed dropped 8 real cases at the orphan gate silently:
    a 、-list before 地號 (華中247 `201-2、352地號等26筆` — the land core keys
    on the first parcel), an `(原NNN)` suffix inside the parcel or the count
    (`105(原90)地號等13筆(原24筆)`), and spaces before 地號/筆 (`1-1 地號等11
    筆`). Compatibility characters are NFKC-normalised first (U+F963 北 after
    臺 breaks the 臺北市 split — Appendix A). Names that still yield no land
    core are reported at the orphan gate, never repaired by inference.
    """
    import unicodedata
    name = unicodedata.normalize("NFKC", name or "")
    # Spaces between the parcel/count and 地號/筆 (奇岩1-1: `1-1 地號等11 筆`);
    # removed only where a digit meets the keyword, not from the whole name.
    name = re.sub(r"(?<=\d) +(?=(?:地號|筆))", "", name)
    # `(原NNN)` inside the parcel or the count — the gazette cleanser strips
    # the same shape chunk-wise (check-declared-parcel-counts).
    name = re.sub(r"\(原\d+\)", "", name)
    patterns = [
        # The 、-list keeps its first parcel: `201-2、352地號等26筆` matches,
        # then the list tail is cut below (identity keys on the first parcel).
        re.compile(r"([一-鿿]+區[一-鿿]+?段(?:[一-鿿]+?段)?\d+(?:-\d+)?(?:、\d+(?:-\d+)?)*地號等?\d*筆?)"),
        re.compile(r"([一-鿿]+區[一-鿿]+段[一-鿿]+段\d+地號等\d+筆)"),
    ]
    for pattern in patterns:
        for candidate in ((name.split("臺北市", 1)[1] if "臺北市" in name else ""), name):
            if not candidate:
                continue
            m = pattern.search(candidate)
            if m:
                lc = m.group(1)
                # first parcel only — the land core keys on it
                lc = re.sub(r"(?<=\d)(?:、\d+(?:-\d+)?)+(?=地號)", "", lc)
                return lc
    return ""


def _parse_landcore(lc: str) -> tuple[str, str, str, str]:
    """Parse landcore string into (district, section, first_parcel, land_count)."""
    district = section = first_parcel = land_count = ""

    m = re.match(r"(.+?區)", lc)
    if m:
        district = m.group(1)
        rest = lc[len(m.group(1)):]
    else:
        rest = lc

    m = re.match(r"(.+?段)", rest)
    if m:
        section = m.group(1)
        rest = rest[len(m.group(1)):]

    m = re.match(r"(.+?)地號", rest)
    if m:
        first_parcel = m.group(1)
        rest = rest[len(m.group(1)) + 2:]

    m = re.search(r"等(\d+)筆", lc)
    if m:
        land_count = m.group(1)

    return district, section, first_parcel, land_count


def _parse_landcore_at_last_segment(lc: str) -> tuple[str, str, str, str]:
    """The same core, read with the section cut at its LAST 段.

    河堤段五小段399地號等3筆 reads as the section 河堤段五小段 with parcel 399
    under this rule, and as the section 河堤段 with parcel 五小段399 under
    `_parse_landcore`'s. The two sides of a comparison may print the same 段
    小段 differently (the gazette says 河堤五小段, the city says 河堤段五小段),
    so the comparison reads both and pairs every reading of one side with
    every reading of the other (design D1)."""
    district = section = first_parcel = land_count = ""

    m = re.match(r"(.+?區)", lc)
    if m:
        district = m.group(1)
        rest = lc[len(district):]
    else:
        rest = lc

    m = re.match(r"(.+?)地號", rest)
    if m:
        head = m.group(1)
        i = head.rfind("段")
        if i >= 0:
            section = head[:i + 1]
            first_parcel = head[i + 1:]
        else:
            first_parcel = head

    m = re.search(r"等(\d+)筆", lc)
    if m:
        land_count = m.group(1)

    return district, section, first_parcel, land_count


def parse_landcore_variants(lc: str) -> list[tuple[str, str, str, str]]:
    """A core's readings: the section cut at its first 段 and at its last.

    The first reading is the pipeline's own (`_parse_landcore`). The second
    reads a 段小段 as one section name. A pair matches if any pairing of the
    two sides' readings matches, so the comparison stays a superset of the
    present one (design D1)."""
    readings = [_parse_landcore(lc)]
    last = _parse_landcore_at_last_segment(lc)
    if last != readings[0]:
        readings.append(last)
    return readings


# a section's 小段 suffix: 一小段, 二小段, ... 六小段, 小段
_SECTION_SUFFIX_RE = re.compile(r"^(.*?)([一二三四五六七八九十]?小段)$")


def landcore_sections_match(a: str, b: str) -> bool:
    """Two sections name the same unit.

    They match when they carry the same 小段 suffix and the same 段 name,
    with a trailing 段 optional on either side. The gazette prints 吳興一小段
    where the city prints 吳興段一小段, and 河堤五小段 where the city prints
    河堤段五小段 (design D2)."""
    if not a or not b:
        return False
    if a == b:
        return True
    ma = _SECTION_SUFFIX_RE.match(a)
    mb = _SECTION_SUFFIX_RE.match(b)
    if not ma or not mb:
        return False
    if ma.group(2) != mb.group(2):
        return False
    name_a, name_b = ma.group(1), mb.group(1)
    if name_a == name_b:
        return True
    return name_a == name_b + "段" or name_b == name_a + "段"


def compute_landcore_similarity(a: str, b: str,
                                 node_parcels: tuple | list | None = None) -> float:
    """Compute similarity between two landcore strings.

    Uses the same weighted logic as merge.py's score function:
    - section match: 0.35
    - first parcel match: 0.20
    - parcel Jaccard: 0.30
    - land count match: 0.10

    The score and its four weights are unchanged. Two of the parts are wider
    than before, and each widening is measured to add bindings and lose none
    (design D2):

    - the **section** part scores 1.0 when the two sections name the same
      小段 and the same 段, with a trailing 段 optional on either side;
    - the **parcel** part scores 1.0 when the city's parcel equals the node's
      first parcel **or is one of the node's own parcels** (the 吳興街二期
      unit's first parcel is 163-2; the city declares 247).

    Each core is read twice — the section cut at its first 段 and at its last
    — and every pairing of the two sides' readings is scored. The best
    pairing wins, so the comparison stays a superset of the present one.

    Returns similarity in [0.0, 1.0]. Returns 0.0 if the districts differ.
    """
    node_parcels = tuple(node_parcels or ())
    best = 0.0
    for a_district, a_section, a_parcel, a_count in parse_landcore_variants(a):
        for b_district, b_section, b_parcel, b_count in parse_landcore_variants(b):
            if not (a_district and b_district and a_district == b_district):
                continue
            if not landcore_sections_match(a_section, b_section):
                continue

            # First parcel score (weight 0.20)
            fp = 0.0
            if a_parcel and b_parcel:
                if a_parcel == b_parcel:
                    fp = 1.0
                elif node_parcels and b_parcel in node_parcels:
                    # the city's parcel is one of the node's OWN parcels
                    fp = 1.0
                elif (b_parcel in a_parcel) or (a_parcel in b_parcel):
                    fp = 0.95  # renumbering alias
                elif a_parcel in b_parcel or b_parcel in a_parcel:
                    fp = 0.7

            # Land count score (weight 0.10)
            cnt = 0.0
            if a_count and b_count and a_count == b_count:
                cnt = 1.0

            # Parcel Jaccard (weight 0.30) - simplified since we only have first parcel
            jac = 1.0 if fp == 1.0 else 0.0

            score = 0.35 + 0.2 * fp + 0.3 * jac + 0.1 * cnt
            if score > best:
                best = score
    return best


# ── §8 viewer-UX (reject-foreign-view-cases): view-verified ownership gate ───


def _link_threshold() -> float:
    """The merge similarity threshold, imported lazily: merge.py and links.py
    stay import-order independent."""
    from urtpe.merge import LINK_THRESHOLD
    return LINK_THRESHOLD


class ViewVerifiedDecision:
    """Outcome of the §8 decision pass over one cache's view-verified ids.

    kept / rejected / not_confirmed / label_errors are parallel views of the
    same id list: kept ids stay view-verified, rejected ids carry their reason
    ({reason, shape, label_ok, city_ok}), not_confirmed ids had no city name
    available (missing header = no evidence — the header_has_no_state rule),
    and label_errors are row-4 accepts whose 相關連結 label named another
    project.
    """

    def __init__(self):
        self.kept: list[str] = []
        self.rejected: dict[str, dict] = {}
        self.not_confirmed: list[str] = []
        self.label_errors: list[str] = []


def verify_view_verified_ids(own_land_core: str, ids: list[str],
                             city_names: dict, labels: dict) -> ViewVerifiedDecision:
    """§8 decision 1 (docs/viewer-UX.md §8): the city's own case name decides.

    | label (check 1) | city name (check 2) | result | reason |
    | --- | --- | --- | --- |
    | match | match | accept | — |
    | no match | no match | reject | label and city name name another project (shape A) |
    | match | no match | reject | label is right, id is wrong (shape B) |
    | no match | match | accept | — (the label error is logged) |

    The label and the city name are compared by land core at
    merge.LINK_THRESHOLD (extract_landcore_from_case_name +
    compute_landcore_similarity). A
    parcel-less name (崇仁新村 — no 地號) is not decidable by land core and
    does NOT reject. A missing city name is no evidence and does NOT reject;
    with a mismatching label the id is reported as "label not confirmed" — the
    label alone never rejects.
    """
    out = ViewVerifiedDecision()
    for cid in ids:
        city_name = (city_names.get(cid) or "").strip()
        label = (labels.get(cid) or "").strip()
        city_lc = extract_landcore_from_case_name(city_name) if city_name else ""
        label_lc = extract_landcore_from_case_name(label) if label else ""
        # land cores equal by string identity also count as a match: both sides
        # are built the same way (build_land_core_key format), so equality is
        # the 1.0 case of compute_landcore_similarity.
        threshold = _link_threshold()
        label_ok = (label_lc == own_land_core
                    or compute_landcore_similarity(own_land_core, label_lc) >= threshold)
        if not city_lc:
            # No city name at all (missing header), or a parcel-less city name
            # (崇仁新村 — no 地號): neither is evidence of a foreign unit.
            # §8 open question 3 default + the parcel-less rule. The label
            # alone never rejects.
            out.kept.append(cid)
            if not label_ok:
                out.not_confirmed.append(cid)
            continue
        city_ok = (city_lc == own_land_core
                   or compute_landcore_similarity(own_land_core, city_lc) >= threshold)
        if city_ok:
            out.kept.append(cid)
            if not label_ok:
                out.label_errors.append(cid)
        else:
            out.rejected[cid] = {
                "reason": ("label and city name name another project (shape A)"
                           if not label_ok else
                           "label is right, id is wrong (shape B)"),
                "shape": "A" if not label_ok else "B",
                "label_ok": label_ok,
                "city_ok": city_ok,
            }
    return out


def offer_rejected_ids(cache_dir: Path, rejected: dict[str, dict[str, str]]) -> list[tuple[str, str, str]]:
    """§8 decision 2 (docs/viewer-UX.md §8): offer a rejected id to its own project.

    ``rejected`` maps {source_project_id: {case_id: city_case_name}}. For each
    rejected id, the land core of its city case name is matched against every
    cache's stored ``land_core`` at LINK_THRESHOLD:
    - exactly one other cache matches → append the id to that cache's
      ``city_case_ids`` (append-only: the positional fallback binds by index),
      record ``adopted_from_view[cid] = source_project_id`` on the target,
      fetch its milestones when absent, and report the move;
    - zero matches → no move (the id stays only in ``view_rejected``);
    - more than one → no guess, the same rule data/project_aliases.json
      applies to ambiguous pairs.

    Matching uses the land core, never 編號 or project_id (both churn).
    Returns the moves as (source, target, case_id).
    """
    cache_dir = Path(cache_dir)
    cores: dict[str, str] = {}
    for entry in sorted(cache_dir.iterdir()):
        rf = entry / "result.json"
        if not rf.is_file():
            continue
        try:
            data = json.loads(rf.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if data.get("land_core"):
            cores[str(data.get("project_id") or entry.name)] = data["land_core"]

    moves: list[tuple[str, str, str]] = []
    for src_pid, cases in rejected.items():
        for cid, city_name in cases.items():
            lc = extract_landcore_from_case_name(city_name or "")
            if not lc:
                continue  # parcel-less name: not decidable, no offer
            hits = [pid for pid, core in cores.items()
                    if pid != src_pid
                    and (core == lc
                         or compute_landcore_similarity(core, lc) >= _link_threshold())]
            if len(hits) != 1:
                continue  # zero or ambiguous: never guess
            target_pid = hits[0]
            target = load_project_cache(cache_dir, target_pid)
            if target is None:
                continue
            changed = False
            if cid not in target.city_case_ids:
                target.city_case_ids.append(cid)
                changed = True
                if cid not in target.case_milestones:
                    try:
                        ms = fetch_taipei_milestones_api(cid)
                        if ms:
                            target.case_milestones[cid] = ms
                            changed = True
                    except Exception:
                        pass  # a failed fetch leaves the id appended; the
                        # next refresh re-reads it like any other case
            if target.adopted_from_view.get(cid) != src_pid:
                target.adopted_from_view[cid] = src_pid
                changed = True
            # the source keeps the rejection recorded: the audit trail lives on
            # both caches (§8 design 3 — view_rejected on the source,
            # adopted_from_view on the target). The refresh pass writes it in
            # the normal flow; this backfill covers a direct offer call.
            source = load_project_cache(cache_dir, src_pid)
            if source is not None and cid not in source.view_rejected:
                source.view_rejected[cid] = {
                    "reason": "moved to its own project (adopted_from_view)",
                    "shape": "offer",
                    "adopted_by": target_pid,
                }
                save_project_cache(cache_dir, src_pid, source)
            if changed:
                save_project_cache(cache_dir, target_pid, target)
            moves.append((src_pid, target_pid, cid))
    return moves


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


# A 地號 / 等N筆 declaration anywhere in a case name. Its absence is what makes a
# name "parcel-less" — the 崇仁新村 case names say nothing about parcels at all.
_PARCEL_DECLARED = re.compile(r"[0-9０-９]+\s*[地等]")

# Tokens that identify a place rather than a parcel. 段 marks a section name, 市/區 a
# district; matching only on those would corroborate every case in the same 段, which is
# the pollution §6.7 exists to keep out.
_NOT_AREA = ("段", "市", "區")

# Case-name boilerplate. Every 都市更新 case name ends in some of these, so a longest-common-
# run over two case names finds 更新事業計畫 before it finds anything about the place -- and
# '更新事業計畫' corroborates every project in Taipei. A run lying inside any of these is
# not evidence of a shared place.
_GENERIC_CASE_WORDS = (
    "都市更新", "更新事業", "事業計畫", "權利變換", "土地", "重建", "區段", "概要",
    "計畫", "變更", "擬訂", "臺北市", "臺北縣", "新北市", "都計畫", "都更", "公展",
    "都審", "開工", "使照", "竣工", "實施", "權利", "面積", "容積", "建築物", "住宅",
)


def _declares_parcel(case_name: str) -> bool:
    return bool(_PARCEL_DECLARED.search(normalize_parcel_token(case_name)))


def _is_generic(run: str) -> bool:
    return any(g in run or run in g for g in _GENERIC_CASE_WORDS)


def _place_candidates(name: str, min_len: int = 2) -> list[str]:
    """Strip plan boilerplate and section/district text, leaving place-name runs.

    Comparing two case names directly is hopeless: every 都市更新 case name ends in the same
    words, so a longest-common-run finds '更新事業計畫' — or a 4-char slice across a word
    boundary like '新事業計' — before anything about the place, and that corroborates every
    project in Taipei. Masking the boilerplate first is what makes the comparison mean
    something; filtering matches afterwards cannot, because the leak is a fragment.
    """
    s = normalize_parcel_token(name)
    for word in sorted(_GENERIC_CASE_WORDS, key=len, reverse=True):
        s = s.replace(word, "\x00")
    s = s.replace("段", "\x00").replace("市", "\x00").replace("區", "\x00")
    return [p for p in s.split("\x00") if len(p) >= min_len]


def _shared_place_run(a: str, c: str, min_len: int = 3) -> str:
    """The longest run of place-name text two names share, after boilerplate is masked out."""
    best = ""
    for pa in _place_candidates(a):
        if len(pa) <= len(best) or len(pa) < min_len:
            continue
        for pc in _place_candidates(c):
            run = pa if pa in pc else ""
            if len(run) > len(best):
                best = run
    return best


def _corroborated_area(anchor_name: str, case_name: str, min_len: int = 3) -> bool:
    """True when two names share a run of text that names a place.

    The §6.7 guard reads a name with no 地號 as a foreign case. That is wrong for a unit
    named for a place — 崇仁新村's cases declare no parcel precisely because the unit has
    no parcel-numbered name. So a parcel-less name is admitted only when it shares a
    place-name run with the gazette record, which is what makes it the *same* unit rather
    than a neighbour.

    Deliberately biased toward rejection: the run must be at least `min_len` characters and
    must not consist of section or district text, so two 更新單元 in one 段 that share only
    a district stay apart. A genuine unit whose area name is shorter stays rejected and is
    named in `search_rejected`, to be recorded by hand.
    """
    if not anchor_name or not case_name or _declares_parcel(case_name):
        # A name that declares a parcel of its own is never rescued: a conflicting 地號 is
        # positive evidence of a specific different unit, whatever area text it shares.
        return False
    return bool(_shared_place_run(anchor_name, case_name))


def _section_variants(section: str, anchor_name: str) -> list[str]:
    """The section as printed, then the same section without a leading place name.

    The gazette prints 崇仁新村青年段一小段 while the city's index holds 青年段一小段. Both
    halves of the key drift, and the section half is the one that actually blocks the
    search: with the prefix left on, every parcel variant returns an empty body, so the
    stem retry recovers nothing.

    The prefix is identified from the same shared place run used for corroboration rather
    than by guessing at 段 boundaries, which are not recoverable from the text (青年段一小段
    and 仁新村青年段一小段 are both suffix-段 strings). A section that is already a whole
    段-name yields no place run and therefore no extra request.
    """
    out = [section]
    run = _shared_place_run(anchor_name, section)
    if run and section.startswith(run):
        trimmed = section[len(run):]
        # A trimmed name that still opens on 段 is not a section name, it is the tail of one
        # (玉泉段二小段 → 段二小段), so it would only spend a request.
        if trimmed and not trimmed.startswith("段"):
            out.append(trimmed)
    return out


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


def fetch_taipei_168_list_api(page_size: int = 0) -> list[dict]:
    """The 168 fast-track programme's case list (D9c-2a's second id source).

    The list is the city's own register of the programme's cases, and it names
    ids the parcel search does not index (10708311, 11412011 — live probe
    2026-11-05). Each row carries the case id and the city's own case name
    (``T_name``), so a caller can SCOPE the list to a project's unit before
    spending a header request on it.

    **One request.** The endpoint's paging is broken: with ``pageSize=50`` each
    page advances by exactly ONE row (measured 2026-11-06 — page 0 starts at
    `09503232`, page 1 at `09503233`, page 2 at `09504081`), so a paged walk
    gathers 90 of the 466 rows in 40 requests. Asking for the whole list in one
    request (``pageSize=466``, the row count the endpoint itself reports in
    ``TotalCount``) returns all 466. The list grew since — ``TotalCount`` is
    read from the first row, and the request uses it.

    A failed request yields an empty list: the caller treats every id as a
    candidate, so an empty list costs recall, never correctness.
    """
    rows_out: list[dict] = []
    seen: set[str] = set()
    page = 0
    size = page_size
    while True:
        try:
            body = _post_taipei_api(TAIPEI_168_LIST_API, {
                "type": "project168",
                "pageIndex": str(page),
                "pageSize": str(size or 50),
            })
            rows = json.loads(body)
        except Exception:
            break
        if not isinstance(rows, list) or not rows:
            break
        before = len(rows_out)
        for row in rows:
            if not isinstance(row, dict):
                continue
            cid = str(row.get("case_id") or "").strip()
            if cid and cid not in seen:
                seen.add(cid)
                rows_out.append(row)
        if not size:
            # ask for the whole list in one request, using the count the
            # endpoint reports
            total = rows[0].get("TotalCount")
            if isinstance(total, int) and total > len(rows):
                size = total
                rows_out = []
                seen = set()
                continue
        if len(rows) < (size or 50):
            break
        if len(rows_out) == before:
            break          # the pages stopped advancing
        page += 1
        if page > 40:
            break
    return rows_out


_MEMO_DATE_RE = re.compile(r"(\d{4})/(\d{1,2})/(\d{1,2})")


def _memo_date(memo: str) -> str:
    """The 核定公告 date in a 168 list row's MEMO, as ISO ("" when absent)."""
    m = _MEMO_DATE_RE.search(memo or "")
    if not m:
        return ""
    return "%s-%02d-%02d" % (m.group(1), int(m.group(2)), int(m.group(3)))


def memo_date_source(rows: list[dict] | None = None):
    """``case_id -> 核定公告 date`` from the 168 list (D9f-2).

    The 核定公告 date is the day the city **announced** an approval, which is a
    **different date** from the 核定日期 (measured 2026-11-06: the two agree in
    99 of the 109 joinable rows and differ in 10, by weeks or months). It is
    therefore a **second confirmation**, never the source of a recovered date —
    and it is empty for every case where the publication's date and the
    platform's date disagree, so it cannot settle those either.

    The rows are read once and cached for the run: the list is one request
    (see :func:`fetch_taipei_168_list_api`).
    """
    cache: dict[str, str] = {}

    def source(case_id: str) -> str:
        if not cache:
            for r in (rows if rows is not None else fetch_taipei_168_list_api()):
                cid = str((r or {}).get("case_id") or "")
                d = _memo_date(str((r or {}).get("MEMO") or ""))
                if cid and d:
                    cache[cid] = d
        return cache.get(case_id, "")

    return source


def _project_cache_dir(cache_dir: Path, project_id: str) -> Path:
    safe_id = re.sub(r"[^\w\-]", "_", project_id)
    return cache_dir / safe_id


_ALIAS_CACHE: dict[str, dict[str, str]] = {}


def load_alias_table(cache_dir: Path) -> dict[str, str]:
    """Return current -> former project_id, for cache migration.

    A project's identity is the land-core slug of its newest approval, so it changes
    whenever that approval's parcel description or district is corrected. The cache
    directories are named on the former identity; resolving through this table keeps
    the ~28 hours of portal work already done instead of orphaning it. Built by
    ``scripts/build_project_aliases.py``, which pairs identities on member content
    and refuses ambiguous pairs.
    """
    root = Path(cache_dir)
    if root in _ALIAS_CACHE:
        return _ALIAS_CACHE[root]
    table: dict[str, str] = {}
    for candidate in (root.parent / "project_aliases.json", root / "project_aliases.json"):
        if candidate.exists():
            try:
                data = json.loads(candidate.read_text(encoding="utf-8"))
                table = {new: old for old, new in (data.get("aliases") or {}).items()}
            except (json.JSONDecodeError, OSError, AttributeError):
                table = {}
            break
    _ALIAS_CACHE[root] = table
    return table


_OVERRIDE_CACHE: dict = {}

# Evidence every recorded link must carry. A view id alone is an assertion nobody can
# audit, and the failure it produces -- another project's milestones attached to this one
# -- is invisible downstream. The "reason" field specifically exists so that a future
# reader does not "fix" the underlying miss by loosening the parcel matcher.
_OVERRIDE_EVIDENCE = ("twur_url", "portal_title", "verified_on", "reason")


def load_twur_overrides(cache_dir: Path) -> dict[str, dict]:
    """Return project_id -> recorded portal link, for projects discovery could not match.

    Tracked configuration rather than derived data, exactly as
    `data/project_aliases.json` is: a per-project cache write would satisfy today's
    dataset and nothing else, and the next `--fresh` run would drop it with no record
    that it had ever been found. Records lacking evidence are dropped and reported.
    """
    root = Path(cache_dir)
    if root in _OVERRIDE_CACHE:
        return _OVERRIDE_CACHE[root]
    table: dict[str, dict] = {}
    for candidate in (root.parent / "twur_overrides.json", root / "twur_overrides.json"):
        if candidate.exists():
            try:
                data = json.loads(candidate.read_text(encoding="utf-8"))
                for pid, entry in (data.get("overrides") or {}).items():
                    if not entry.get("twur_view_id"):
                        print(f"[WARN] twur override for {pid} names no view id; ignored",
                              file=sys.stderr)
                        continue
                    missing = [f for f in _OVERRIDE_EVIDENCE if not entry.get(f)]
                    if missing:
                        print(f"[WARN] twur override for {pid} lacks {', '.join(missing)}; "
                              f"ignored -- an unattributed link cannot be audited",
                              file=sys.stderr)
                        continue
                    table[pid] = entry
            except (json.JSONDecodeError, OSError, AttributeError):
                table = {}
            break
    _OVERRIDE_CACHE[root] = table
    return table


def unattached_overrides(cache_dir: Path, known_project_ids) -> list[str]:
    """Recorded links whose project is not in the dataset.

    An identity churn would silently stop the record applying; surfacing it keeps the
    table honest instead of leaving a stale entry nobody notices.
    """
    known = set(known_project_ids)
    orphans = [pid for pid in load_twur_overrides(cache_dir) if pid not in known]
    for pid in orphans:
        print(f"[WARN] twur override names a project not in the dataset: {pid}")
    return orphans


def resolve_cache_dir(cache_dir: Path, project_id: str) -> Path:
    """The cache directory for ``project_id``, following an alias if one applies."""
    direct = _project_cache_dir(cache_dir, project_id)
    if direct.exists():
        return direct
    former = load_alias_table(cache_dir).get(project_id)
    if former:
        aliased = _project_cache_dir(cache_dir, former)
        if aliased.exists():
            return aliased
    return direct


def load_project_cache(cache_dir: Path, project_id: str) -> Optional[DiscoveryResult]:
    project_cache = resolve_cache_dir(cache_dir, project_id)
    result_file = project_cache / "result.json"
    if result_file.exists():
        try:
            data = json.loads(result_file.read_text(encoding="utf-8"))
            result = DiscoveryResult(**data)
        except (json.JSONDecodeError, TypeError):
            result = None
        if result is not None:
            # D9c-2a: a stub and a richer ALIASED directory are MERGED, not
            # shadowed. `resolve_cache_dir` returns the current directory
            # whenever it exists, so a stub at the current id left the richer
            # directory unreadable — and the loss was silent: two nodes kept
            # the flag 節點未能對應平台案件 although the case and its
            # milestones were in the cache all along (南港566's 10708311,
            # 核定 2019-11-20, and 10006032, 核定 2016-02-25).
            #
            # The current directory's content wins a conflict (it is the newer
            # reading, written under the current identity), and its identity
            # fields are never overwritten.
            _merge_aliased_cache(cache_dir, project_id, project_cache, result)
            # Gap-fill only. A recorded link is a human assertion about a project discovery
            # could not resolve; letting it displace a real discovery result would mean one
            # careless record silently rewrites what the portal actually returned.
            if not result.twur_view_id:
                entry = load_twur_overrides(cache_dir).get(project_id)
                if entry:
                    result.twur_view_id = entry["twur_view_id"]
                    result.twur_url = entry.get("twur_url", "")
            return result
    return None


def _merge_aliased_cache(cache_dir: Path, project_id: str, project_cache: Path,
                         result: "DiscoveryResult") -> list[str]:
    """Union the aliased directory's case ids and milestones into the current
    one. Returns what was added (empty when nothing was).

    The aliased directory is the project's FORMER identity (the alias table
    pairs the two on member content), so the ids it holds are this project's
    cases. The current directory's own content wins a conflict: it was
    written under the current identity and is the newer reading. The
    identity fields (`project_id`, `land_core`) are never overwritten — the
    current id is the one the dataset holds.
    """
    former = load_alias_table(cache_dir).get(project_id)
    if not former:
        return []
    aliased = _project_cache_dir(cache_dir, former)
    if not aliased.exists() or aliased == project_cache:
        return []
    result_file = aliased / "result.json"
    if not result_file.is_file():
        return []
    try:
        data = json.loads(result_file.read_text(encoding="utf-8"))
        other = DiscoveryResult(**data)
    except (json.JSONDecodeError, TypeError, OSError):
        return []

    added: list[str] = []
    known = set(result.city_case_ids)
    for cid in other.city_case_ids:
        if cid not in known:
            result.city_case_ids.append(cid)
            known.add(cid)
            added.append(cid)
    for cid, ms in (other.case_milestones or {}).items():
        if cid not in result.case_milestones:
            result.case_milestones[cid] = dict(ms or {})
            if cid not in added:
                added.append(cid)
    # the schedules and headers the merged ids need, so the resolver can
    # read them offline
    for cid in added:
        if cid in (other.case_schedules or {}) and cid not in result.case_schedules:
            result.case_schedules[cid] = other.case_schedules[cid]
        if cid in (other.case_headers or {}) and cid not in result.case_headers:
            result.case_headers[cid] = other.case_headers[cid]
        if cid in (other.case_case_names or {}) and cid not in result.case_case_names:
            result.case_case_names[cid] = other.case_case_names[cid]
        if cid in (other.candidate_names or {}) and cid not in result.candidate_names:
            result.candidate_names[cid] = other.candidate_names[cid]
    if added:
        print(f"[INFO] cache merge: {project_id} gained {len(added)} id(s) from "
              f"the aliased directory {former}: {', '.join(added)}")
        try:
            save_project_cache(Path(cache_dir), project_id, result)
        except OSError:
            pass
    return added


def save_project_cache(cache_dir: Path, project_id: str, result: DiscoveryResult, view_html: str = "") -> None:
    project_cache = _project_cache_dir(cache_dir, project_id)
    project_cache.mkdir(parents=True, exist_ok=True)

    result_file = project_cache / "result.json"
    result_file.write_text(json.dumps(asdict(result), ensure_ascii=False, indent=2), encoding="utf-8")

    if view_html:
        view_file = project_cache / "view.html"
        view_file.write_text(view_html, encoding="utf-8")

    # Taipei case pages are cached by fetch_url automatically


def cache_is_stale_for(cache_dir: Path, project_id: str, gazette_date: str) -> bool:
    """Whether a project cache was last written before ``gazette_date``.

    The signal is the cache file's mtime, not a stored field: no project cache
    carries a publication date (measured 2026-11-02 on all 726), so a check
    phrased on one would be inert in production. A cache whose milestones were
    captured before an approval was published cannot know that approval — the
    refresh-awaiting-approval-caches change; see also
    ``cached_cases_awaiting_approval`` for the targeted selector.
    """
    rf = resolve_cache_dir(Path(cache_dir), project_id) / "result.json"
    if not rf.exists():
        return False
    try:
        import datetime as _dt
        written = _dt.date.fromtimestamp(rf.stat().st_mtime)
        published = _dt.date.fromisoformat(str(gazette_date)[:10])
    except (ValueError, OSError):
        return False
    return written < published


# The moment a case is in between applying for approval and receiving it. A cache
# holding such a case was written before the approval existed, so re-fetching it is
# the only way the new 核定日期 can reach the payload.
#
# fix-row-order-tiebreak-and-view-badges D2: the application signal covers every
# application track, not only approval applications — 北投區-關渡段二小段-303's
# 11505020 carried only 申請計畫日期/申請權變日期 while the API already held its
# 核定日期 2026/09/30, so the narrow list skipped the cache and node 5 stayed on
# the positional fallback (the wrong badge + the inverted row).
_APPLICATION_FIELDS = (
    "申請核定日期", "權變申請核定日期",
    "申請計畫日期", "申請權變日期", "申請概要核准日期",
)
_APPROVAL_FIELDS = ("核定日期", "權變核定日期", "概要核准日期")


def cached_cases_awaiting_approval(case_milestones: dict | None,
                                   case_schedules: dict | None = None,
                                   case_headers: dict | None = None,
                                   superseded_by: dict | None = None) -> bool:
    """Whether any cached case carries an approval application and no approval.

    Pure, offline: computable from the cache alone, so the refresh pass can
    select its candidates without a single API call. A case whose cached status
    is terminal (自行撤回 / 已駁回 / 已失效) does not count: it was closed without
    approval and will never gain an approval date, yet it made 85 of 176
    projects candidates on 2026-11-02 (refresh-case-status D5).
    """
    schedules = case_schedules or {}
    headers = case_headers or {}
    replaced = superseded_by or {}
    for cid, ms in (case_milestones or {}).items():
        if not isinstance(ms, dict):
            continue
        if schedules.get(cid) in TERMINAL_SCHEDULES:
            continue
        # supersede D5: a re-filed case (header 無, or recorded as superseded)
        # carries an application and no approval forever.
        if cid in replaced or str(headers.get(cid, "x")).strip() in ("", "無"):
            continue
        approved = any(ms.get(f) for f in _APPROVAL_FIELDS)
        applied = any(ms.get(f) for f in _APPLICATION_FIELDS)
        if applied and not approved:
            return True
    return False


def header_has_no_state(header: dict | None) -> bool:
    """A header row that exists and whose NAME is 無 or empty. A missing row
    ({} / None) is no evidence and is NOT this."""
    return bool(header) and str(header.get("NAME", "")).strip() in ("", "無")


def state_of_header(header: dict | None) -> str:
    """Map a case header's 目前辦理情形 (NAME) to a per-case badge state.

    Returns "無" when NAME reads 無, "NA" when NAME is empty, or "" when the row
    is missing or reads anything else. header_has_no_state keeps the broader
    no-state notion (無 and empty) for the supersede trigger; this helper splits
    them so the viewer badge can label each honestly.
    """
    if not header:
        return ""
    name = str(header.get("NAME", "")).strip()
    if name == "無":
        return "無"
    if name == "":
        return "NA"
    return ""


SUPERSEDE_MIN_LABELS = 3


def find_superseding_case(cid: str, case_milestones: dict,
                          header_names: dict) -> tuple[str, str, list[str]]:
    """The case the city re-filed ``cid`` as, or why none. Pure.

    A successor has the identical header case name, a numerically greater id,
    and the same date for every application date ``cid`` carries (the five
    ``_APPLICATION_FIELDS``; at least one required). ``cid`` must also carry at
    least SUPERSEDE_MIN_LABELS dated labels. Other dates may differ: a re-filed
    case restates its filing and re-runs later steps
    (match-superseding-case-on-application-dates, the maintainer's decision
    2026-11-02 — 雅祥227-4's 11009142 → 11510001 held its exhibition again;
    吉林705-3's 10410012 → 11503012 records another 召開幹事會日期). The strict
    every-date rule (supersede D2) refused both.

    Returns ``(succ, "", differs)`` for exactly one candidate, where ``differs``
    lists ``cid``'s dated labels the successor does not share (so the looser
    match stays auditable); ``("", "none", [])`` or ``("", "ambiguous", [])``
    otherwise. Measured: 11211211 → 11409026 and 10806141 → 11510017 differ in
    nothing.
    """
    own = {k: v for k, v in (case_milestones.get(cid) or {}).items() if v}
    applied = {k: own[k] for k in _APPLICATION_FIELDS if own.get(k)}
    name = (header_names.get(cid) or "").strip()
    if len(own) < SUPERSEDE_MIN_LABELS or not applied or not name:
        return "", "none", []
    try:
        own_no = int(cid)
    except ValueError:
        return "", "none", []
    hits = []
    for other, ms in case_milestones.items():
        if other == cid or (header_names.get(other) or "").strip() != name:
            continue
        try:
            if int(other) <= own_no:
                continue
        except ValueError:
            continue
        ms = ms or {}
        if all(ms.get(k) == v for k, v in applied.items()):
            hits.append(other)
    if len(hits) == 1:
        succ_ms = case_milestones.get(hits[0]) or {}
        return hits[0], "", [k for k, v in own.items() if succ_ms.get(k) != v]
    return "", ("ambiguous" if hits else "none"), []

def fetch_taipei_case_header_api(case_id: str) -> dict:
    """Fetch the 基本資料 case header row via get_project168_top.ashx ({} if none).

    Its ``NAME`` is the platform's 目前辦理情形; measured identical to the data1
    辦理進度 (Get_project168_First ``name_progress_no``) on all 13 cases checked
    2026-11-02, so one call per case suffices."""
    body = _post_taipei_api(TAIPEI_TOP_API, {"case_id": case_id})
    try:
        rows = json.loads(body)
    except json.JSONDecodeError:
        return {}
    row = rows[0] if isinstance(rows, list) and rows else rows
    return row if isinstance(row, dict) else {}


def refresh_project(cache_dir: Path, project_id: str, fetch=None,
                    fetch_status=None, search=None, search_key=None,
                    fetch_implementation=None, fetch_rewards=None,
                    fetch_list=None, fetch_portal=None) -> dict:
    """Re-fetch the milestones and status of a cache's cases, in place.

    Thin driver over the platform adapters: ``fetch(case_id) -> {label: date}``
    (default :func:`fetch_taipei_milestones_api`), ``fetch_status(case_id) ->
    header row`` (default :func:`fetch_taipei_case_header_api`) and
    ``search(section, parcel, dropped_out=, anchor_name=)`` (default
    :func:`search_taipei_cases_api`). The status and search adapters default on
    only when ``fetch`` does too — the production call — so a caller injecting a
    milestone fetcher alone stays offline (refresh-case-status D4, supersede D4).
    Every other cached field is preserved, and the report names each change so
    the effect is auditable.

    A non-empty milestone reply REPLACES the case's milestones: the old
    ``{**before, **fetched}`` merge kept dates the city withdrew forever
    (光華段四小段-282 11408032's 申請核定日期). A withdrawn approval date is the one
    exception — it decides the node binding, so it is kept and reported as a
    conflict rather than dropped silently. An empty reply changes nothing.

    supersede-headerless-cases-and-discover-new-ids: before the per-case pass the
    parcel search discovery used is repeated with ``search_key = (section,
    first_parcel, anchor_name)``, and every case id it returns that the cache
    lacks is APPENDED to ``city_case_ids`` — never re-ordered, the positional
    fallback binds by index — because a case filed after the cache was written
    was otherwise invisible (虎林段四小段-38's 11510017). After the pass, a case
    whose header reads 無 is matched to the case the city re-filed it as
    (:func:`find_superseding_case`).

    D7: after the per-case pass the merged milestone projection is re-derived
    from the cases, so it cannot drift from them.

    D8: ``fetch_implementation`` and ``fetch_rewards`` re-fetch the execution
    and rewards layers for every live approved case that has no entry. They
    default on only when ``fetch`` does too — the production call — so an
    offline caller stays offline.

    D13: a case whose header row AND milestones are both empty is labelled 無.
    The id and the cached data stay; no removal is claimed.

    D9c-2a: ``fetch_list`` is the SECOND id source — the city's 168
    fast-track list, which names case ids the parcel search does not index.
    Each id it returns is confirmed by that case's own header before it
    enters the project's case list.

    bind-the-unplaced-by-searching-the-cell-section: ``fetch_portal`` is the
    THIRD id source — the national portal's own title search, which finds a
    unit the parcel search does not index at all (懷生段一小段928's case
    10002141). It is asked only when the parcel search and the 168 list both
    return nothing, so it runs for the projects that need it and not for all
    of them. Each id it names is confirmed by that case's own header before it
    enters the project's case list, and the id is APPENDED — never inserted —
    so the existing ids keep their positions (the positional fallback binds
    by index).
    """
    if fetch is None:
        fetch = fetch_taipei_milestones_api
        if fetch_status is None:
            fetch_status = fetch_taipei_case_header_api
        if search is None:
            search = search_taipei_cases_api
        if fetch_implementation is None:
            fetch_implementation = fetch_taipei_implementation_api
        if fetch_rewards is None:
            fetch_rewards = fetch_taipei_rewards_api
        if fetch_list is None:
            fetch_list = fetch_taipei_168_list_api
    cached = load_project_cache(Path(cache_dir), project_id)
    report: dict = {"project_id": project_id, "updated": [], "still_awaiting": [],
                    "closed": [], "status_changes": [], "removed": [],
                    "conflicts": [], "added": [], "superseded": [],
                    "no_successor": [], "ambiguous": [], "not_searched": False,
                    "view_rejected_ids": [], "view_label_errors": [],
                    "view_not_confirmed": [], "labelled_wu": [],
                    "implementation_refetched": [], "payload_sizes": [],
                    "unconfirmed": [],
                    "error": ""}
    if cached is None:
        report["error"] = "no cache"
        return report
    changed = False
    report_error = ""

    # ── the parcel search, before anything is read or written ───────────────
    search_status: dict[str, str] = {}
    if search and search_key and all(search_key[:2]):
        section, parcel, anchor_name = (list(search_key) + [""])[:3]
        try:
            entries = search(section, parcel, dropped_out={},
                             anchor_name=anchor_name or "") or []
        except Exception as exc:  # a failed search is a failure, not "nothing new"
            report["error"] = f"search: {type(exc).__name__}: {exc}"
            return report
        known = set(cached.city_case_ids) | set(cached.case_milestones)
        for e in entries:
            cid = str(e.get("case_id") or "")
            if not cid or cid in known:
                continue
            known.add(cid)
            cached.city_case_ids.append(cid)
            cached.case_milestones[cid] = {}
            if e.get("case_name"):
                cached.candidate_names[cid] = e["case_name"]
            if e.get("schedule"):
                cached.case_schedules[cid] = e["schedule"]
                search_status[cid] = e["schedule"]
            else:
                search_status[cid] = ""
            changed = True
    elif search:
        report["not_searched"] = True

    # ── the SECOND id source: the 168 list, scoped and confirmed ───────────
    # D9c-2a: the city's parcel search does not index every approved case
    # (10708311, 11412011 — live probe 2026-11-05), so a project whose case
    # the search cannot reach keeps the flag 節點未能對應平台案件 forever.
    # The 168 list names those ids. It is a register of cases, not of one
    # project's cases, so an id from it is a CANDIDATE: it enters the case
    # list only when the case's own header confirms it (a row with a 案名).
    # An empty header is not a confirmation — one empty response is no
    # evidence, the same rule the 無 label follows.
    #
    # The list is SCOPED by the project's own section first, so a refresh
    # spends a header request only on the ids that name its section. The
    # section comes from the search key the refresh already has.
    if fetch_list is not None and search_key and all(search_key[:2]):
        section = str(search_key[0] or "")
        try:
            list_rows = list(fetch_list() or [])
        except Exception as exc:  # a failed list is a failure, not "nothing"
            report["error"] = f"168 list: {type(exc).__name__}: {exc}"
            return report
        known = set(cached.city_case_ids) | set(cached.case_milestones)
        for row in list_rows:
            cid = str((row or {}).get("case_id") or "").strip()
            if not cid or cid in known:
                continue
            case_name = str((row or {}).get("T_name") or "").strip()
            # the scope is the section AND the parcel, ADJACENT — the city
            # writes 玉成段二小段166地號. A section alone names 504 projects
            # (中山段一小段 appears in many), and the parcel alone names 246
            # (the same number in many sections).
            parcel = str(search_key[1] or "")
            if not (section and parcel):
                continue
            if not re.search(re.escape(section) + r"\s*" + re.escape(parcel)
                             + r"(?:地號|$)", case_name):
                continue          # the list names another unit's case
            try:
                header = fetch_status(cid) if fetch_status else None
            except Exception as exc:
                report["error"] = f"{cid}: header {type(exc).__name__}: {exc}"
                return report
            if not header or not str(header.get("CASE_NAME", "") or "").strip():
                report["unconfirmed"].append(cid)
                continue
            known.add(cid)
            cached.city_case_ids.append(cid)
            cached.case_milestones[cid] = {}
            cached.case_case_names[cid] = str(header.get("CASE_NAME", "")).strip()
            name = str(header.get("NAME", "")).strip()
            if name:
                cached.case_headers[cid] = dict(header)
            changed = True
            report["added"].append({"case_id": cid, "schedule": "",
                                    "name": name,
                                    "source": "168 list (header-confirmed)"})

    # ── the per-case pass ──────────────────────────────────────────────────
    header_names: dict[str, str] = {}
    no_state: set[str] = set()
    labelled_wu: list[str] = []
    for cid in list(cached.case_milestones.keys()):
        before = cached.case_milestones.get(cid) or {}
        try:
            fetched = {k: v for k, v in (fetch(cid) or {}).items() if v}
            header = fetch_status(cid) if fetch_status else None
        except Exception as exc:  # a source failure leaves the cache untouched
            report["error"] = f"{cid}: {type(exc).__name__}: {exc}"
            return report
        # D13: the city moved a case to a new id and emptied the old one
        # (青年130's 11501041 → 11510008; 虎林38's 11410001 → 11502012). One
        # empty response is no evidence — the request may have failed — but TWO
        # empty sources in the same refresh is the measured shape. The case
        # keeps its id, its cached data and its place in the case list; the
        # label claims no removal, it only says the case is now 無.
        #
        # The rule is unconditional: the LIVE read decides, not what the cache
        # held. A case whose cached milestones are already empty (虎林38's
        # 11410001) is exactly the shape the rule is for — the city emptied it
        # and the cache never learned.
        if not fetched and not header:
            was = cached.case_schedules.get(cid, "")
            if was != "無":
                cached.case_schedules[cid] = "無"
                labelled_wu.append(cid)
                report["status_changes"].append(
                    {"case_id": cid, "was": was, "now": "無",
                     "name": "header and milestones both empty"})
                changed = True

        if fetched:
            new = dict(fetched)
            for label, was in before.items():
                if label in new or not was:
                    continue
                if label in _APPROVAL_FIELDS:
                    new[label] = was
                    report["conflicts"].append(
                        {"case_id": cid, "label": label, "was": was})
                else:
                    report["removed"].append(
                        {"case_id": cid, "label": label, "was": was})
        else:
            new = dict(before)
        if new != before:
            changed = True
        cached.case_milestones[cid] = new
        old_ok = next((before.get(f) for f in _APPROVAL_FIELDS if before.get(f)), "")
        new_ok = next((new.get(f) for f in _APPROVAL_FIELDS if new.get(f)), "")
        if new_ok and new_ok != old_ok:
            report["updated"].append({"case_id": cid, "核定日期": new_ok, "was": old_ok})
        if header:  # a missing row ({} / None) is no evidence
            name = str(header.get("NAME", "")).strip()
            case_name = str(header.get("CASE_NAME", "") or "").strip()
            header_names[cid] = case_name
            # resolve-recno-case D4: store the header's own approval dates
            # beside the NAME — data2 sometimes copies another case's date
            # (玉泉11's 09504263, 吉林705's 09307104), the header is the
            # second source the node resolver reads offline. Legacy caches
            # carry a bare NAME string; a new write upgrades the entry to the
            # dict shape when the header carries dates.
            hdr_dates = {}
            if header.get("uro_chk_date"):
                hdr_dates["uro_chk_date"] = str(header["uro_chk_date"])
            if header.get("uro_chk_date2"):
                hdr_dates["uro_chk_date2"] = str(header["uro_chk_date2"])
            new_entry = dict(case_header_entry(cached.case_headers, cid))
            new_entry["NAME"] = name
            new_entry.update(hdr_dates)
            wanted = (new_entry["uro_chk_date" if "uro_chk_date" in new_entry
                      else "NAME"] if not hdr_dates and len(new_entry) == 1
                      else None)
            if wanted is not None:
                # no dates on this header and no prior dates: keep the legacy
                # bare-string shape so unchanged caches stay byte-stable
                if cached.case_headers.get(cid) != name:
                    cached.case_headers[cid] = name
                    changed = True
            else:
                if cached.case_headers.get(cid) != new_entry:
                    cached.case_headers[cid] = new_entry
                    changed = True
            # §8: persist the city's own case name beside the state, so the
            # view-verified verification and the offer step decide offline.
            if cached.case_case_names.get(cid) != case_name:
                cached.case_case_names[cid] = case_name
                changed = True
            header_state = state_of_header(header)
            if header_state:
                no_state.add(cid)
            was_status = cached.case_schedules.get(cid, "")
            status = refreshed_schedule(was_status, schedule_from_top(header), new,
                                        header_state=header_state)
            if status != was_status:
                report["status_changes"].append(
                    {"case_id": cid, "was": was_status, "now": status, "name": name})
                if status:
                    cached.case_schedules[cid] = status
                else:
                    cached.case_schedules.pop(cid, None)
                changed = True
        if cid in search_status:
            report["added"].append({"case_id": cid,
                                    "schedule": cached.case_schedules.get(cid, ""),
                                    "name": cached.case_headers.get(cid, "")})

    # ── the implementation layer: re-fetch the cases that lack it ───────────
    # D8: the refresh never fetched data3/data4, so a project whose payload
    # was empty stayed empty forever (文山區-實踐段二小段-641's case 09009032
    # holds 開工 2004/09/24 and 使照 2007/10/31 at the live endpoint, and the
    # cache holds neither). The selection is PER CASE: a project whose payload
    # holds entries for other cases still needs the missing one (青年130 holds
    # entries for two of its three cases, and the third carries the dates).
    for cid in list(cached.case_milestones.keys()):
        if cached.case_schedules.get(cid) in TERMINAL_SCHEDULES:
            continue
        if cached.case_schedules.get(cid) == "無":
            continue
        ms = cached.case_milestones.get(cid) or {}
        if not any(ms.get(f) for f in _APPROVAL_FIELDS):
            continue
        if cached.implementation.get(cid):
            continue
        before_impl = len(cached.implementation.get(cid) or {})
        try:
            impl = fetch_implementation(cid) if fetch_implementation else {}
        except Exception as exc:  # a failed fetch leaves the cache untouched
            report["error"] = f"{cid}: implementation {type(exc).__name__}: {exc}"
            return report
        if impl:
            cached.implementation[cid] = impl
            changed = True
        try:
            rew = fetch_rewards(cid) if fetch_rewards else {}
        except Exception as exc:
            report["error"] = f"{cid}: rewards {type(exc).__name__}: {exc}"
            return report
        if rew:
            cached.rewards[cid] = rew
            changed = True
        report["implementation_refetched"].append(
            {"case_id": cid, "implementation_keys": len(impl),
             "reward_keys": len(rew), "before_keys": before_impl})
        # the before/after size of the PROJECT payload, so a shrink is visible
        # (雅祥227: the 無 case's 26-key payload gives way to the live
        # sibling's 1-key payload — a real shrink, named in the report)
        report["payload_sizes"].append({
            "case_id": cid,
            "implementation_keys": len(impl),
            "reward_keys": len(rew),
        })

    # ── the twin pass: which case did the city re-file a 無 case as? ─────────
    for cid in sorted(no_state):
        succ, why, differs = find_superseding_case(cid, cached.case_milestones,
                                                   header_names)
        if succ:
            if cached.superseded_by.get(cid) != succ:
                cached.superseded_by[cid] = succ
                changed = True
            report["superseded"].append({"case_id": cid, "by": succ,
                                         "differs": differs})
        elif why == "ambiguous":
            report["ambiguous"].append(cid)
        elif any((cached.case_milestones.get(cid) or {}).get(f) for f in _APPLICATION_FIELDS):
            report["no_successor"].append(cid)

    # ── classification ──────────────────────────────────────────────────────
    for cid in cached.case_milestones:
        new = cached.case_milestones[cid]
        new_ok = next((new.get(f) for f in _APPROVAL_FIELDS if new.get(f)), "")
        if new_ok or not any(new.get(f) for f in _APPLICATION_FIELDS):
            continue
        if cid in no_state or cid in cached.superseded_by:
            continue  # reported as superseded / no_successor / ambiguous
        if cached.case_schedules.get(cid, "") in TERMINAL_SCHEDULES:
            report["closed"].append(cid)
        else:
            report["still_awaiting"].append(cid)

    # fix-row-order-tiebreak-and-view-badges D3: re-run the national view-page
    # absorb so a backfilled cache gains view_verified_case_ids (and any case id
    # the page names that the parcel search missed). Once per project — it ran
    # once per case before supersede-headerless-cases (§36 residual).
    view_id = cached.twur_view_id or ""
    if not view_id and cached.twur_url:
        m = re.search(r"view/(\d+)", cached.twur_url)
        view_id = m.group(1) if m else ""
    if view_id and not cached.twur_name:
        # label-by-own-name: the cache predates twur_name — parse the cached
        # view.html (re-parse, no request) before/instead of a re-fetch.
        _vh = resolve_cache_dir(Path(cache_dir), project_id) / "view.html"
        if _vh.is_file():
            try:
                parsed = parse_view_title(_vh.read_text(encoding="utf-8"))
                if parsed:
                    cached.twur_name = parsed
                    changed = True
            except OSError:
                pass
    if view_id:
        try:
            view_html = fetch_view_page(view_id, Path(cache_dir))
            prior_verified = list(cached.view_verified_case_ids)
            parsed = parse_view_title(view_html)
            if parsed and parsed != cached.twur_name:
                cached.twur_name = parsed
                changed = True
            _absorb_view_case_ids(None, cached, view_html, 0.0, {}, {})
            # Merge, never replace: the absorb overwrites the list with the page
            # order, and an already-complete cache must not lose or reorder its
            # entries (test_refresh_view_absorb pins this). S3a: a previously
            # rejected id (§8) is not re-added by the merge — its rejection
            # stands until the offer step moves it to its owner.
            cached.view_verified_case_ids = prior_verified + [
                c for c in cached.view_verified_case_ids
                if c not in prior_verified and c not in cached.view_rejected]
        except Exception as exc:
            report_error = f"view absorb: {type(exc).__name__}: {exc}"

    # ── §8 viewer-UX (reject-foreign-view-cases): the view-verified gate ─────
    # The 相關連結 assertion was treated as unconditional, so case ids of OTHER
    # projects entered the cache as view-verified and rendered as nameless 孤
    # anchors carrying the other project's 建照 / 開工 dates (§8; board B7+B8).
    # The city's own case name decides (§8 decision 1). Runs on every cache
    # holding view-verified ids — the defect does not depend on the awaiting
    # state (中山254 holds none). A rejected id is named in view_rejected,
    # never dropped silently; the driver's offer step moves it to its own
    # project afterwards (the refresh's unit is one project's cache).
    if cached.view_verified_case_ids:
        # S3a: a previously rejected id is not re-decided — the gate only sees
        # evidence from this run (labels + city names), and with none it would
        # "keep" the id on no-evidence grounds, undoing the recorded rejection
        # (10202065 shape). The offer step or a future full re-verify revisits it.
        cached.view_verified_case_ids = [
            c for c in cached.view_verified_case_ids if c not in cached.view_rejected]
        labels: dict[str, str] = {}
        view_html_path = Path(cache_dir) / resolve_cache_dir(Path(cache_dir), project_id).name / "view.html"
        try:
            if view_html_path.is_file():
                labels = _view_labels_for(view_html_path.read_text(encoding="utf-8"),
                                          cached.view_verified_case_ids)
        except OSError:
            labels = {}
        decision = verify_view_verified_ids(
            own_land_core=cached.land_core,
            ids=cached.view_verified_case_ids,
            city_names=cached.case_case_names,
            labels=labels,
        )
        if decision.rejected:
            cached.view_verified_case_ids = list(decision.kept)
            for cid, rec in decision.rejected.items():
                cached.view_rejected[cid] = rec
                # a rejected id must not keep anchoring milestones to this
                # project's timeline: drop it from city_case_ids too (the
                # offer step re-adds it on the owning project's cache), and
                # drop its milestones — S3a: they were fetched by an earlier
                # absorb, no node/orphan/edge/badge reads them, and keeping
                # them made every 相關連結 fallback re-derive a dead label.
                if cid in cached.city_case_ids:
                    cached.city_case_ids.remove(cid)
                if cid in cached.case_milestones:
                    del cached.case_milestones[cid]
                changed = True
            report["view_rejected_ids"] = sorted(decision.rejected)
        if decision.label_errors:
            report["view_label_errors"] = list(decision.label_errors)
        if decision.not_confirmed:
            report["view_not_confirmed"] = list(decision.not_confirmed)

    # ── the THIRD id source: the portal's title search, confirmed ──────────
    # bind-the-unplaced-by-searching-the-cell-section: a unit the city's
    # parcel search does not index AT ALL keeps the flag
    # 節點未能對應平台案件 forever. The 懷生段一小段928 case (10002141) is
    # indexed by no parcel search under any section form the gazette prints;
    # the national portal's own `?title=` search finds it, and the page's
    # 相關連結 names the id.
    #
    # The portal's page is a register of cases, not of one project's cases,
    # so an id from it is a CANDIDATE: it enters the case list only when the
    # case's own header confirms it (a row with a 案名). The same rule the
    # 168 list follows, for the same reason.
    #
    # It runs AFTER the view absorb and its §8 gate, because the absorb adds
    # the page's ids to the case list on the page's own word — no header
    # confirmation. The header confirmation is the last word here: an id the
    # absorb added without one is removed and named as unconfirmed.
    #
    # It is asked only when the parcel search and the 168 list both returned
    # nothing, so it runs for the projects that need it and not for all of
    # them.
    if (fetch_portal is not None and search_key and all(search_key[:2])
            and not cached.city_case_ids):
        section = str(search_key[0] or "")
        try:
            portal_rows = list(fetch_portal(section) or [])
        except Exception as exc:  # a failed search is a failure, not "nothing"
            report["error"] = f"portal title search: {type(exc).__name__}: {exc}"
            return report
        if portal_rows:
            known = set(cached.city_case_ids) | set(cached.case_milestones)
            portal_ids: list[str] = []
            for row in portal_rows:
                view_id = str((row or {}).get("view_id") or "").strip()
                if view_id:
                    cached.twur_view_id = view_id
                    cached.twur_url = f"{VIEW_URL_BASE}{view_id}"
                    milestones = (row or {}).get("milestones") or {}
                    if milestones:
                        for label, value in milestones.items():
                            cached.national_milestones.setdefault(label, value)
                for cid in ((row or {}).get("case_ids") or ()):
                    cid = str(cid or "").strip()
                    if cid and cid not in portal_ids:
                        portal_ids.append(cid)
            for cid in portal_ids:
                if cid in known and cid in cached.city_case_ids:
                    # the absorb already added it — it still needs the header's
                    # confirmation, or it is named as unconfirmed and removed
                    try:
                        header = fetch_status(cid) if fetch_status else None
                    except Exception as exc:
                        report["error"] = f"{cid}: header {type(exc).__name__}: {exc}"
                        return report
                    if header and str(header.get("CASE_NAME", "") or "").strip():
                        cached.case_case_names[cid] = str(header["CASE_NAME"]).strip()
                        name = str(header.get("NAME", "")).strip()
                        if name:
                            cached.case_headers[cid] = dict(header)
                        changed = True
                        continue
                    cached.city_case_ids.remove(cid)
                    cached.case_milestones.pop(cid, None)
                    report["unconfirmed"].append(cid)
                    changed = True
                    continue
                if cid in known:
                    continue
                try:
                    header = fetch_status(cid) if fetch_status else None
                except Exception as exc:
                    report["error"] = f"{cid}: header {type(exc).__name__}: {exc}"
                    return report
                if not header or not str(header.get("CASE_NAME", "") or "").strip():
                    report["unconfirmed"].append(cid)
                    continue
                # APPENDED, never inserted: the existing ids keep their
                # positions (the positional fallback binds by index).
                cached.city_case_ids.append(cid)
                cached.case_milestones[cid] = {}
                cached.case_case_names[cid] = str(header.get("CASE_NAME", "")).strip()
                name = str(header.get("NAME", "")).strip()
                if name:
                    cached.case_headers[cid] = dict(header)
                changed = True
                report["added"].append({"case_id": cid, "schedule": "",
                                        "name": name,
                                        "source": "portal title search (header-confirmed)"})

    # ── D7: re-derive the merged milestone projection ───────────────────────
    # The projection is written ONLY by the discovery path, so the refresh's
    # per-case writes to case_milestones left the two apart: 85 of the 719
    # caches that hold per-case milestones diverged (D7b), 14 projects emitted
    # no construction date a case actually holds (寶清599's 建照 2006/05/12 sat
    # in the cache and never reached the payload).
    #
    # The re-derivation projects the cases EXACTLY (the decided rule): a label
    # no case carries any more leaves the projection, because the city
    # withdrew or re-dated it. The per-case withdrawn-approval conflict rule
    # is a different layer and is unchanged — it keeps a withdrawn approval
    # date on the CASE, because that date decides the node binding.
    #
    # It runs LAST, so it sees every case id the refresh added: the search
    # step's appended ids and the view absorb's ids.
    merged: dict[str, str] = {}
    merged_source: dict[str, str] = {}
    for cid in cached.city_case_ids:
        merge_stage_milestones(merged, merged_source, cid,
                               cached.case_milestones.get(cid) or {})
    if merged != cached.taipei_milestones or merged_source != cached.milestones_source:
        changed = True
    cached.taipei_milestones = merged
    cached.milestones_source = merged_source

    # every case the refresh labelled 無, named (a label that vanished
    # silently would read as a complete dataset)
    report["labelled_wu"] = list(labelled_wu)

    if changed or report["updated"] or cached.view_verified_case_ids:
        save_project_cache(Path(cache_dir), project_id, cached)
    report["error"] = report_error
    return report


def _view_labels_for(view_html: str, ids: list[str]) -> dict[str, str]:
    """{case_id: 相關連結 label} for the given ids from a view page.

    The label is the anchor text of the r_progress_detail link — the other
    project's name in the §8 defect shapes, compared only for the reason text
    (§8 decision 1: the city's own case name decides).
    """
    out: dict[str, str] = {}
    for cid in ids:
        m = re.search(r"case_id=" + re.escape(cid) + r"[^>]*>([^<]*)<", view_html)
        if m:
            out[cid] = m.group(1).strip()
    return out


def _iso_date(s: str) -> str:
    """Normalize a date cell to zero-padded ISO-ish form ('' if empty).

    '2016/07/05', '2016-07-05', and the PDF's own unpadded print '2016/8/23' all
    become '2016-08-23'. The padding matters: the per-node case matcher compares
    these strings against case-milestone dates, and before this fix
    '2016/8/23' -> '2016-8-23' never equalled '2016-08-23', so the matcher missed
    and the attach fell through to the positional fallback — measured as 484
    date-matchable nodes bound to the wrong case (1,164 of 1,442 raw rows carry an
    unpadded date). ROC cells ('115/8/27') keep their own year form; only the
    month and day pad, because the ROC->ISO year conversion is the caller's job.
    The case header's approval dates arrive as ISO datetimes
    ('2023-12-28T00:00:00' — 犁和302's 10203253 uro_chk_date2); the T-time is
    cut here so the resolver's date comparison sees the date (resolve-recno-case
    task 3.3: 21 nodes unresolved because of this exact shape).
    """
    text = s.strip().replace("/", "-") if s else ""
    if "T" in text:
        text = text.split("T", 1)[0]
    m = re.fullmatch(r"(\d{2,4})-(\d{1,2})-(\d{1,2})", text)
    if not m:
        return text
    return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"


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


def select_best_payload(payloads: dict[str, dict],
                        excluded: set[str] | None = None) -> tuple[str, dict, list[str]]:
    """Pick the best-populated payload whole (never field-merged) per design D5.

    Returns (case_id, payload, review_flags). Empty/absent payloads are ignored;
    conflicting values across multiple carriers surface review flags.

    ``excluded`` names the cases that must not be ranked — the cases recorded
    as 無 (D13). Their payload is a stale copy: the city moved the case to a new
    id and emptied the old one, so the copy holds values the live case no
    longer has. The exclusion applies even when the excluded payload is larger
    than the live one (雅祥227: 26 keys vs 1) — a near-empty live payload is
    the live answer, and the refresh report names the shrink.
    """
    skip = set(excluded or ())
    candidates = {cid: p for cid, p in (payloads or {}).items()
                  if p and cid not in skip}
    if not candidates:
        return "", {}, []
    best_cid = max(candidates, key=lambda cid: len(candidates[cid]))
    flags: list[str] = []
    # the conflict flags name EVERY carrier, including an excluded one: the
    # disagreement is real and reporting it is the honest reading.
    others = [cid for cid in candidates if cid != best_cid]
    excluded_ids = [cid for cid in (payloads or {})
                    if cid in skip and payloads[cid]]
    for key, val in candidates[best_cid].items():
        for other in others:
            if key in candidates[other] and candidates[other][key] != val:
                flags.append(
                    f"payload {key} conflicts across cases: {best_cid}={val} vs {other}={candidates[other][key]}"
                )
        for other in excluded_ids:
            if key in payloads[other] and payloads[other][key] != val:
                flags.append(
                    f"payload {key} conflicts across cases: {best_cid}={val} vs {other}={payloads[other][key]}"
                )
    return best_cid, candidates[best_cid], flags


# dates-follow-plan-case (C8a, user rule 2026-11-04): the city keeps 建照
# (data2) and 開工/使照 (data3) on the first 擬訂 plan case. select_best_payload's
# key-count pick drops them when a later case carries more statistics (measured:
# 9 of the 13 "national-only 使照" projects, 德惠573 09710240 holds 開工 2012/07/13
# + 使照 2015/07/13 never emitted).
_PLAN_CASE_RE = re.compile(r"^擬訂.*都市更新(事業計畫|事業計畫及權利變換計畫)案")


def pick_implementation_payload(payloads: dict, candidate_names: dict | None = None,
                                excluded: set[str] | None = None):
    """Dates follow the 擬訂 plan case; statistics keep the one-payload rule.

    Returns (dates, per-date source, statistics case_id, flags):
    - dates: {label: value} union over the 擬訂 plan-case payloads, in
      implementation_milestones label space;
    - source: {label: case_id} provenance per date;
    - statistics case_id: select_best_payload's D5 pick (unchanged consumers);
    - flags: a field no plan case carries falls back to the D5 payload and is
      flagged; differing values for one field on 2+ plan cases conflict-flag.
    An area split is several plan cases (-A區/-B區/…): each carries its own
    building's dates, so the union is the intended reading, not a merge.

    ``excluded`` names the cases recorded as 無 (D13). The exclusion covers
    BOTH layers: the key-count pick and this plan-case date collection. A 無
    case's payload is a stale copy, so it must supply neither a statistic nor
    a date.
    """
    names = candidate_names or {}
    skip = set(excluded or ())
    plan_cids = [cid for cid, p in (payloads or {}).items() if p
                 and cid not in skip
                 and _PLAN_CASE_RE.match(names.get(cid, "") or "")]
    best_cid, best_payload, d5_flags = select_best_payload(payloads, excluded=skip)
    flags = list(d5_flags)
    dates: dict[str, str] = {}
    source: dict[str, str] = {}
    if plan_cids:
        for cid in plan_cids:
            for label, value in implementation_milestones(payloads[cid]).items():
                if label in dates and dates[label] != value:
                    flags.append(f"payload {label} conflicts across plan cases: "
                                 f"{source[label]}={dates[label]} vs {cid}={value}")
                    continue
                if label in dates:
                    # D4a (2026-11-05): an equal value keeps the FIRST plan
                    # case's credit (榮星53's 使照 2007/11/29 on both areas).
                    continue
                dates[label] = value
                source[label] = cid
        # a field no plan case carries falls back to the D5 payload, flagged
        for label, value in implementation_milestones(best_payload or {}).items():
            if label not in dates:
                dates[label] = value
                source[label] = best_cid
                flags.append(f"payload {label} not on any 擬訂 plan case; "
                             f"taken from {best_cid} (D5 fallback)")
    else:
        # no plan case in the payloads at all: D5 for everything, flagged once
        for label, value in implementation_milestones(best_payload or {}).items():
            dates[label] = value
            source[label] = best_cid
            flags.append(f"payload {label} not on any 擬訂 plan case; "
                         f"taken from {best_cid} (D5 fallback)")
    return dates, source, best_cid, flags


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
    """Merge one case's stage milestones, recording which case won each label
    so slot provenance stays provable at the viewer. D4a (2026-11-05): an
    EQUAL value keeps the first case's credit — two plan cases sharing one
    printed date (榮星53's 建照) are one event, and the later read must not
    steal the provenance; a DIFFERENT value keeps last-write-wins (a re-dated
    row is new information)."""
    for label, v in ms.items():
        if label in all_ms and all_ms[label] == v:
            continue
        all_ms[label] = v
        source[label] = cid


def schedule_from_top(top_row: dict) -> str:
    """Map a get_project168_top.ashx row (phase/NAME) to the search-response
    schedule vocabulary — for cases discovered outside the parcel search
    (view-page 相關連結, curated exceptions) where no schedule was returned."""
    name = str((top_row or {}).get("NAME", ""))
    if "駁回" in name:
        return "已駁回"
    if "撤回" in name:
        return "自行撤回"
    if "失效" in name:
        return "已失效"
    # refresh-case-status-and-drop-withdrawn-fields D1: a case WAITING for
    # approval (…申請報府核定中) contains 核定 too, so this must precede the
    # approved test — otherwise an in-review case reads 已核准, whose badge the
    # viewer omits (中正段一小段-68 10406283; the city's search list says 審查中).
    if "核定中" in name:
        return "審查中"
    if "核定" in name:
        return "已核准"
    if "審查" in name or "審議" in name:
        return "審查中"
    if "施工" in name or "備查" in name:
        return "施工中"
    return ""


# Case statuses that close a case without approval: it never gains an approval
# date, so the awaiting-approval refresh must not keep re-selecting it.
TERMINAL_SCHEDULES = ("自行撤回", "已駁回", "已失效")
# The city's search list writes an approved case as 已核准 or 已核定 (cache,
# 2026-11-02: 739 / 14); stages after approval are more specific than either.
_APPROVED_FAMILY = ("已核准", "已核定")
_LATER_THAN_APPROVED = ("施工中", "已完工", "完成成果備查")


def refreshed_schedule(cached: str, derived: str, milestones: dict | None,
                       no_state: bool = False, header_state: str = "") -> str:
    """The status a refreshed case should carry (refresh-case-status D2). Pure.

    ``derived`` is :func:`schedule_from_top` of the case header the refresh just
    read. The header is the platform's current per-case word, so a terminal /
    in-review / construction reading wins. An "approved" header never
    downgrades a later stage the search list already recorded (施工中 beats a
    bare 業經本府核定). A header that reads 無 or empty states the case has no
    current state: the viewer labels it [無] / [NA] instead of showing 審查中.
    (The stand-alone rule was once reversed to silence 立農163-2's 11211211; that
    decision is now overridden — see docs/viewer-UX.md §7 decision 2.)
    """
    cached = cached or ""
    if header_state == "無":
        return "無"
    if header_state == "NA":
        return "NA"
    if no_state:
        # supersede-headerless-cases D1: header exists and reads 無 or empty.
        # Keeping a cached 審查中 put a chip on an approved unit; clear those,
        # keep terminal/later statuses (withdrawn stays withdrawn).
        return "" if cached in ("審查中",) + _APPROVED_FAMILY else cached
    if derived and derived != "已核准":
        return derived
    if derived == "已核准":
        if cached in _APPROVED_FAMILY or cached in _LATER_THAN_APPROVED:
            return cached
        return derived
    ms = milestones or {}
    if cached in _APPROVED_FAMILY and not any(ms.get(f) for f in _APPROVAL_FIELDS):
        return ""
    return cached


def _ghost_node_date(own_milestones: dict, track: str = "") -> str:
    """Ghost/virtual node date — the case's OWN approval, in track order.

    D2a (inspection-batchD, user decision 2026-11-05): a 概要-track case falls
    through 核定日期 → 權變核定日期 → 概要核准日期 (its own approval); a
    plan-track case stops at 核定日期 → 權變核定日期. The city echoes the
    family's 概要核准 into every descendant case's 階段辦理過程 (吉林717's
    triple all carried 2007/01/30), so reading it on a plan case dates the
    ghost with a sibling's approval — a fabricated event. An undated ghost
    renders (未核定), the honest label."""
    labels = ("核定日期", "權變核定日期")
    if track == "事業概要":
        labels = labels + ("概要核准日期",)
    for label in labels:
        iso = _iso_date(own_milestones.get(label, ""))
        if iso:
            return iso
    return ""


def _match_case_by_date(member_date: str, disc) -> str:
    """Find the city case whose 核定日期/權變核定日期 equals the node's date
    (exact first, then ±1 day). Returns case_id or ''. Accepts ISO
    ('2008-01-02'), slash-Gregorian ('2008/01/02') and ROC ('97/1/2') dates —
    the PDF pipeline passes raw ROC gazette dates."""
    if not member_date or not getattr(disc, "case_milestones", None):
        return ""
    target = _iso_date(member_date)
    if not re.fullmatch(r"\d{4}-\d{1,2}-\d{1,2}", target or ""):
        from urtpe.cleanse import roc_to_iso

        iso, _ = roc_to_iso(member_date)
        target = _iso_date(iso or "")
    candidates: dict[str, set[str]] = {}
    for cid, ms in disc.case_milestones.items():
        dates: set[str] = set()
        # 概要核准日期 is the approval milestone of the 事業概要 track — a 概要
        # case has no 核定日期, so omitting it silently degrades 概要-node
        # anchoring to the positional fallback (§6.14 延吉段727 shape).
        for label in ("核定日期", "權變核定日期", "概要核准日期"):
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


# ── resolve-recno-case (S10, C6): the 4-step node-case resolver ─────────────
# The positional fallback (city_case_ids[0/1] by track) bound 71 nodes on 51
# projects to a case the node's own date refutes (measured 2026-11-04). The
# user's rule: every recno has a corresponding city case — find it, never
# guess by position.

_DEAD_SCHEDULES = ("自行撤回", "已駁回", "已失效")
# Area suffix on a city case name: -A區 / 北區 / (A區段) / (FridA區段)-like
# parenthesised 區段 tags. Distinct suffixes across live same-name matches =
# an area split (吉林508 -A區/-B區, 榮星53 北區/南區 — user rule 2026-11-03).
_AREA_SUFFIX_RE = re.compile(r"-?[A-Z北南東西甲乙]區(?:段)?(?:\([^)]*\))?|\([^)]*區段\)")
_PLAN_TYPE_RE = re.compile(r"\(含釐正圖冊\)|暨.*釐正圖冊|釐正圖冊")
_STAGE_WITH_ORDINAL_RE = re.compile(r"^(擬訂|擬定|變更(?:\(第[一二三四五六七八九十百\d]+次\))?)")
# 康寧626's header approves 10 days after the gazette row; measured as the
# only drift case, so the bound is the observation, not a tunable threshold.
_HEADER_DRIFT_DAYS = 10


def node_name_key(name: str) -> str:
    """Tier 1: the 案名 with spaces ignored. The gazette's own stage typo
    變(第二次)更 — the ordinal INSIDE the word (玉泉11 recno 1180) — folds
    to the city's 變更(第二次) form here, so every tier sees one spelling."""
    s = re.sub(r"\s", "", name or "")
    return re.sub(r"變\((第[一二三四五六七八九十百\d]+次)\)更", r"變更(\1)", s)


def node_name_loose(name: str) -> str:
    """Tier 2: count-noise and stage-spelling normalisation.

    Strips 等, `(原N筆)`, a trailing 案, the area suffix and 核定公告_;
    folds 擬定→擬訂, 案及→及, 土地更新→土地都市更新 (the city drops 都市),
    權利變換案→權利變換計畫案. The gazette's own stage typo 變(第二次)更
    (the ordinal INSIDE the word — 玉泉11 recno 1180) folds to 變更(第二次),
    the city's form."""
    s = node_name_key(name)
    s = s.replace("擬定", "擬訂").replace("案及", "及").replace("土地更新", "土地都市更新")
    s = _AREA_SUFFIX_RE.sub("", s)
    s = re.sub(r"\(原[^)]*\)|等|核定公告_?$", "", s)
    s = s.replace("權利變換案", "權利變換計畫案")
    return re.sub(r"案$", "", s)


def node_stage_kind(name: str) -> tuple[str, str]:
    """Tier 3: (stage-with-ordinal, plan type 概/事/權), 釐正圖冊 tags removed."""
    s = node_name_key(name)
    m = _STAGE_WITH_ORDINAL_RE.match(s)
    stage = m.group(1).replace("擬定", "擬訂") if m else ""
    s = _PLAN_TYPE_RE.sub("", s)
    kind = (("概" if "概要" in s else "") +
            ("事" if "事業計畫" in s else "") +
            ("權" if "權利變換" in s else ""))
    return stage, kind


def _kind_matches(node_kind: str, case_kind: str) -> bool:
    """Tier-3 plan-type comparison. The gazette prints one stage word for a
    combined-track approval, so a node named 事業計畫 (東湖34 r73) matches a
    case named 事業計畫及權利變換計畫 (11502008) — the node's kind is a
    subset of the case's. A case with fewer tracks than the node never
    matches (a bare 事業計畫 case is not a 權變 node's case)."""
    return all(k in case_kind for k in (node_kind or ""))


def _tier3_names_match(node_name: str, case_name: str, node_landcore: str = "",
                       node_parcels: tuple | list | None = None,
                       alt_landcores: tuple | list | None = None) -> bool:
    """Tier 3: equal stage-with-ordinal + the kind subset + the same unit —
    the stage+kind pair alone is NOT a match (變更+權 describes half the
    corpus). The land core decides: the node's core comes from its 案名 or
    (the gazette's abbreviated form, 中正河堤段 without the 區) from the
    record's own fields; the case's from its city name. Both parse →
    similarity ≥ 0.85; either is parcel-less (崇仁新村) or unparseable → no
    tier-3 match from the name alone (the case stays an orphan;
    view-verified or twin-bridge evidence binds it instead).

    bind-the-unplaced-by-searching-the-cell-section: the comparison is
    offered ALTERNATIVE cores — the record's own core built with the 地號
    cell's section (the form the city indexes when the 案名 and the cell
    disagree) — and the node's own parcel set, so a case the city declares
    under another parcel of the same unit still matches. A pair matches if
    any alternative matches; the widened rule is a superset of the present
    one (design D1, D2)."""
    cs, ck = node_stage_kind(case_name)
    ns, nk = node_stage_kind(node_name)
    if not (cs and cs == ns and _kind_matches(nk, ck)):
        return False
    lc_case = extract_landcore_from_case_name(case_name)
    if not lc_case:
        return False
    cores = []
    lc_node = extract_landcore_from_case_name(node_name) or node_landcore
    if lc_node:
        cores.append(lc_node)
    for alt in (alt_landcores or ()):
        if alt:
            cores.append(alt)
    for core in cores:
        if compute_landcore_similarity(core, lc_case,
                                       node_parcels=node_parcels) >= 0.85:
            return True
    return False


def _node_area_suffix(name: str) -> str:
    m = _AREA_SUFFIX_RE.search(node_name_key(name))
    return m.group(0) if m else ""


def _record_landcore(member) -> str:
    """The record's land core from its own fields — the gazette's abbreviated
    案名 (中正河堤段, no 區) does not parse, but the record's district_land /
    section / first_parcel / land_count carry the same identity. Delegates to
    build_land_core_key when the member is a CleanRecord; the SimpleNamespace
    test doubles get the same shape inline. Empty when the record carries no
    parcel."""
    if hasattr(member, "district_land") and hasattr(member, "land_count"):
        try:
            core = build_land_core_key(member)
            return core if getattr(member, "first_parcel", "") else ""
        except Exception:
            pass
    district = getattr(member, "district_land", "") or getattr(member, "district", "") or ""
    section = getattr(member, "section", "") or ""
    parcel = getattr(member, "first_parcel", "") or ""
    count = getattr(member, "land_count", None)
    core = f"{district}{section}{parcel}"
    if count:
        core += f"地號等{count}筆"
    return core if parcel else ""


def _probe_name_ok(case_name: str, node_name: str, node_landcore: str = "",
                   node_parcels: tuple | list | None = None,
                   alt_landcores: tuple | list | None = None) -> bool:
    """The probe's name test beyond the loose equality: the tier-3 rule —
    equal stage-with-ordinal, the kind subset and the land core (the board's
    S12 correction: case ids are a city-wide daily serial, so a same-day
    sibling may belong to another project — 10203252 = 中山111)."""
    return _tier3_names_match(node_name, case_name, node_landcore,
                              node_parcels=node_parcels,
                              alt_landcores=alt_landcores)


def _cell_landcore(member) -> str:
    """The record's land core built with the 地號 cell's OWN section.

    The gazette's 案名 and 地號 columns can disagree about which 段小段 a unit
    is in (河堤五小段 vs 河堤段五小段, 萬華段一小段 vs 萬大段一小段), and the
    city indexes the 地號 column's form. This core is offered to the
    comparison as an ALTERNATIVE to the 案名's — the record's `section` field
    itself stays the 案名's, because it is the merge's grouping key (design
    D3).

    A member that carries no `section_land` field (a test double, or a
    payload from before the field existed) gets the cell's section read from
    its own 地號 cell, by the cleanser's own parse."""
    district = getattr(member, "district_land", "") or getattr(member, "district", "") or ""
    section = getattr(member, "section_land", "") or ""
    if not section:
        from urtpe.cleanse import cell_section
        section = cell_section(getattr(member, "land", "") or "")
    parcel = getattr(member, "first_parcel", "") or ""
    if not (district and section and parcel):
        return ""
    count = getattr(member, "land_count", None)
    core = f"{district}{section}{parcel}"
    if count:
        core += f"地號等{count}筆"
    return core


def _node_parcels(member) -> tuple:
    """The node's own parcel set, so the city's declared parcel may be one of
    them and not only the first (the 吳興街二期 unit's first parcel is
    163-2; the city declares 247)."""
    parcels = getattr(member, "parcels", None) or ()
    return tuple(str(p) for p in parcels if p)


def case_header_entry(headers: dict, cid: str) -> dict:
    """Read one case_headers entry in either shape.

    resolve-recno-case D4: new writes store {NAME, uro_chk_date, uro_chk_date2};
    caches written before that carry the bare NAME string. A string reads as
    {NAME: <string>} with no header dates."""
    v = (headers or {}).get(cid)
    if isinstance(v, dict):
        return v
    if isinstance(v, str) and v:
        return {"NAME": v}
    return {}


def header_name(headers: dict, cid: str) -> str:
    """The case header's NAME (the 目前辦理情形), either shape."""
    return str(case_header_entry(headers, cid).get("NAME", "") or "").strip()


def header_approval_dates(headers: dict, cid: str) -> dict[str, str]:
    """{label: date} from the header's uro_chk_date/uro_chk_date2 — the city's
    own approval dates for the case. data2 sometimes copies another case's
    date (玉泉11's 09504263, 吉林705's 09307104); the header is the second
    source. Legacy string entries carry none."""
    entry = case_header_entry(headers, cid)
    out = {}
    if entry.get("uro_chk_date"):
        out["核定日期"] = str(entry["uro_chk_date"])
    if entry.get("uro_chk_date2"):
        out["權變核定日期"] = str(entry["uro_chk_date2"])
    return out


def filter_live_cases(cids: list[str], disc, names: tuple[str, ...] = ()) -> list[str]:
    """The cases a node's name may bind: terminal schedules out; a 無 case
    yields to an approved same-name sibling (東湖34: 11302181 → 11502008,
    the user's resolution 2026-11-04). Two+ live non-無 cases stay ambiguous —
    the caller decides (one = bind, distinct area suffixes = split, otherwise
    no bind); the approved-preference must not collapse them silently."""
    schedules = getattr(disc, "case_schedules", None) or {}
    live = [c for c in cids if schedules.get(c) not in _DEAD_SCHEDULES]
    if len(live) > 1:
        ms = getattr(disc, "case_milestones", None) or {}
        no_state = [c for c in live if schedules.get(c) == "無"]
        if no_state and len(no_state) < len(live):
            # a 無 case yields to live siblings that carry a state
            live = [c for c in live if c not in no_state]
    return live


def _name_tier_hits(names: dict, node_name: str,
                    node_landcore: str = "",
                    node_parcels: tuple | list | None = None,
                    alt_landcores: tuple | list | None = None) -> list[tuple[str, list[str]]]:
    """[(tier, case_ids)] — the cached cases matching the node's 案名, tier by
    tier. Every tier runs over all cached candidate names. Tier 3 matches on
    (stage-with-ordinal, plan type) with the kind-subset rule and the
    land-core check: the gazette prints one stage word for a combined-track
    approval, so a node named 事業計畫 matches a case named
    事業計畫及權利變換計畫 (東湖34 r73 → 11502008; 吉林705 r1311 → 09307101) —
    but only on the same unit (the 崇仁新村 cross-family shape must not
    match)."""
    tiers = (
        ("1 exact", node_name_key),
        ("2 loose", node_name_loose),
        ("3 stage+kind", None),
    )
    out = []
    for label, fn in tiers:
        if fn is None:
            hits = [cid for cid, n in names.items() if n
                    and _tier3_names_match(node_name, n, node_landcore,
                                           node_parcels=node_parcels,
                                           alt_landcores=alt_landcores)]
        else:
            want = fn(node_name)
            hits = [cid for cid, n in names.items() if n and fn(n) == want]
        out.append((label, hits))
    return out


def _bind_from_name_step(node_name: str, live: list[str], names: dict) -> list[str]:
    """The name step's binding: one live case binds; distinct non-empty area
    suffixes on every live match bind all (the area-split rule)."""
    if len(live) == 1:
        return [live[0]]
    suffixes = {_node_area_suffix(names.get(c, "")) for c in live}
    if len(live) >= 2 and "" not in suffixes and len(suffixes) == len(live):
        return sorted(live)
    return []


def resolve_node_cases(member, disc, fetch_header=None, fetch_milestones=None,
                       search=None, sleep=None, probe_headers=None,
                       probe_bases=None) -> list[str]:
    """Bind a date-unmatched node to its city case(s) — the 4 steps, in order.

    Returns the case ids to append to node.links.taipei ([] = nothing found).

    Offline by default (design D7): with no adapters injected the resolver
    reads only what the caches carry — candidate_names, case_milestones,
    case_headers (the header's uro_chk_date/uro_chk_date2) and the
    ``probe_headers`` memo. The live probe (step 2) and the all-parcel search
    (step 4) run only when the caller injects the adapters — the sweep driver
    and the tests; the emission-side attach never issues a request.

    ``probe_headers`` is {case_id: header row} — the ids earlier probing runs
    read (the finds persist in the caches, so later runs re-derive nothing).
    Every accepted find joins the cache in place (append-only) so a second
    run skips the probing.
    """
    live_probe = fetch_header is not None or fetch_milestones is not None \
        or search is not None or bool(probe_headers)
    if fetch_header is None:
        fetch_header = fetch_taipei_case_header_api
    if fetch_milestones is None:
        fetch_milestones = fetch_taipei_milestones_api
    if search is None:
        def search(section, parcel, dropped_out=None, anchor_name="",
                   extra_sections=None):
            # the all-parcel step's own acceptance is the node's 案名 + date;
            # the §6.7 searched-parcel guard would drop exactly the cases this
            # step exists to find (南港566's plan case hides under parcel 567
            # while its name declares 566), so step 4 uses the raw form
            return search_taipei_cases_for_node(section, parcel,
                                                extra_sections=extra_sections)
    if sleep is None:
        sleep = time.sleep
    memo = probe_headers or {}

    def _header(cid: str) -> dict:
        row = memo.get(cid)
        if row:  # a memo row with content is the evidence; empty = no evidence
            return row or {}
        if not live_probe:
            return {}
        try:
            return fetch_header(cid) or {}
        except Exception:
            return {}

    def _milestones(cid: str) -> dict:
        if not live_probe:
            return {}
        try:
            return fetch_milestones(cid) or {}
        except Exception:
            return {}

    names = getattr(disc, "candidate_names", None) or {}
    schedules = getattr(disc, "case_schedules", None) or {}
    ms = getattr(disc, "case_milestones", None) or {}
    headers = getattr(disc, "case_headers", None) or {}
    node_name = getattr(member, "name", "") or ""
    # the record's own land core (the gazette's abbreviated 案名, 中正河堤段
    # without the 區, does not parse): district(_land) + section + first
    # parcel + count, the build_land_core_key form
    node_landcore = extract_landcore_from_case_name(node_name) or _record_landcore(member)
    # bind-the-unplaced-by-searching-the-cell-section: the comparison is also
    # offered the record's own core built with the 地號 cell's section (the
    # form the city indexes when the 案名 and the cell disagree), and the
    # node's own parcel set (so a case the city declares under another
    # parcel of the same unit still matches).
    node_parcels = _node_parcels(member)
    alt_landcores = tuple(c for c in (_cell_landcore(member),) if c)

    # ── step 2 pre-pass: the memo's uncached ids probe BEFORE the name step ─
    # The name step binds a single cached hit and returns — a split sibling
    # named only on the national page (玉成166's 10203262, the memo's seed)
    # would never be probed. When the memo names ids the cache lacks, the
    # probe runs first (the memo seeds its bases) and the name step is
    # SKIPPED for this call: the probe's own acceptance (name + date +
    # land core) decides, and its area-split walk binds every sibling.
    # ``probe_bases`` marks the re-entrant call.
    uncached_memo = [c for c in memo if c not in set(
        getattr(disc, "city_case_ids", None) or [])]
    if uncached_memo and live_probe and not probe_bases:
        pre = resolve_node_cases(
            member, disc, fetch_header=fetch_header,
            fetch_milestones=fetch_milestones, search=search,
            sleep=sleep, probe_headers=memo, probe_bases=uncached_memo)
        return pre

    # ── step 1: the 案名 over cached cases ──────────────────────────────────
    # (skipped on a probe_bases call — the probe decided above; falling
    # through would bind a single cached hit before the siblings are read)
    # a 無 case yields to an approved same-name sibling: the sibling may live
    # at a later tier (東湖34's 11502008 names 及權利變換計畫, so tiers 1–2
    # hit only the 無 case 11302181) — pre-compute the widest (tier-3) hit
    # set so the yield check sees it before binding a lone 無 case.
    if not probe_bases:
        tiers = _name_tier_hits(names, node_name, node_landcore,
                                node_parcels=node_parcels,
                                alt_landcores=alt_landcores)
        widest = sorted(set(tiers[-1][1])) if tiers else []
        for _tier, hits in tiers:
            live = filter_live_cases(hits, disc)
            if not live:
                continue
            if len(live) == 1 and (schedules.get(live[0]) == "無") and widest:
                wider = filter_live_cases(widest, disc)
                if wider and wider != live:
                    live = wider
            bound = _bind_from_name_step(node_name, live, names)
            if bound:
                return bound

    # ── step 3 first over the cache: the header as a second approval source ─
    # (step 2 runs live network probes; the offline header check is free, so
    # it runs before any request). A probe_bases call skips it: the probe's
    # acceptance decides, and an exact date on one cached case would bind
    # before the split sibling is read (玉成166's 10203261 vs 10203262).
    target = _iso_date(getattr(member, "date", "") or "")
    if not re.fullmatch(r"\d{4}-\d{1,2}-\d{1,2}", target or ""):
        # the PDF pipeline passes raw ROC gazette dates (115/8/11); normalise
        # the same way _match_case_by_date does
        from urtpe.cleanse import roc_to_iso

        iso, _ = roc_to_iso(getattr(member, "date", "") or "")
        target = _iso_date(iso or "")
    if not probe_bases:
        stage_kind = node_stage_kind(node_name)
        exact_hits: list[str] = []
        for cid in getattr(disc, "city_case_ids", None) or []:
            hdr_dates = header_approval_dates(headers, cid)
            if not hdr_dates:
                # the header may be silent while the milestones carry the
                # approval (康寧626's 09712204: 核定 2016/11/12 in data2, the
                # node 10 days later) — the same bounded drift applies there
                own_ms = ms.get(cid) or {}
                for label in _APPROVAL_FIELDS:
                    if own_ms.get(label):
                        hdr_dates[label] = str(own_ms[label])
            for label, hdr_date in hdr_dates.items():
                iso = _iso_date(hdr_date)
                if not iso:
                    continue
                if iso == target:
                    # an exact header/milestone date is a candidate; two+ cases
                    # sharing it need the name to separate them (both cases of a
                    # same-day approval carry the same 核定日期 — the date
                    # matcher's own uniqueness rule)
                    exact_hits.append(cid)
                    continue
                shifted = _shift_iso_date(iso, _HEADER_DRIFT_DAYS)
                shifted_back = _shift_iso_date(iso, -_HEADER_DRIFT_DAYS)
                if shifted and shifted_back and shifted_back <= target <= shifted:
                    # bounded drift binds only on an equal stage-with-ordinal
                    if node_stage_kind(names.get(cid, ""))[0] == stage_kind[0] and stage_kind[0]:
                        return [cid]
        if len(exact_hits) == 1:
            return [exact_hits[0]]
        if len(exact_hits) > 1:
            # the name separates a same-day tie: the tier-3 rule (stage + kind
            # subset + land core) over the candidates
            named = [c for c in exact_hits
                     if names.get(c) and _tier3_names_match(
                         node_name, names[c], node_landcore,
                         node_parcels=node_parcels,
                         alt_landcores=alt_landcores)]
            if len(named) == 1:
                return [named[0]]
            # an area split: distinct area suffixes on every named candidate
            live = filter_live_cases(named or exact_hits, disc)
            bound = _bind_from_name_step(node_name, live, names)
            if bound:
                return bound

    # ── step 2: the same-day id probe ───────────────────────────────────────
    # Case ids are a city-wide daily serial (ROC filing date + one digit), so
    # a same-day id is a candidate only: accept on CASE_NAME matching the
    # node's 案名 AND the header approval date matching the node's date.
    # Offline (no memo, no adapters) this walks the memo only — production
    # attach reads the caches' persisted finds and issues no request.
    known = set(getattr(disc, "city_case_ids", None) or [])
    known |= set(getattr(disc, "view_verified_case_ids", None) or [])
    # 10 ids share a filing day's first 7 digits; the node's own date implies
    # no filing day offline, so the probe walks every known id's batch — and
    # every memo id's batch (玉成166's A區/B區 cases 10203261/2 are named only
    # on its own national page, so their batch exists in no cached id).
    bases = sorted({c[:7] for c in known if len(c) >= 8}
                   | {c[:7] for c in memo if len(c) >= 8}
                   | {c[:7] for c in (probe_bases or []) if len(c) >= 8})
    probe_names: dict[str, str] = {}
    probe_dates: dict[str, dict[str, str]] = {}
    # the memo is pre-read: a persisted find needs no request. A memo row
    # without a CASE_NAME (the sweep's view-page seed carries none) stays a
    # probe candidate — the loop below fetches its header live.
    for cid, row in memo.items():
        top = row or {}
        case_name = str(top.get("CASE_NAME", "") or "").strip()
        if not case_name:
            continue
        probe_names[cid] = case_name
        hdr_dates = {}
        if top.get("uro_chk_date"):
            hdr_dates["核定日期"] = str(top["uro_chk_date"])
        if top.get("uro_chk_date2"):
            hdr_dates["權變核定日期"] = str(top["uro_chk_date2"])
        if hdr_dates:
            probe_dates[cid] = hdr_dates
    for b in bases:
        for k in range(10):
            cid = f"{b}{k}"
            if cid in known or cid in probe_names:
                continue
            if not live_probe:
                break
            sleep(0.001)
            top = _header(cid)
            case_name = str(top.get("CASE_NAME", "") or "").strip()
            if not case_name:
                continue
            probe_names[cid] = case_name
            hdr_dates = {}
            if top.get("uro_chk_date"):
                hdr_dates["核定日期"] = str(top["uro_chk_date"])
            if top.get("uro_chk_date2"):
                hdr_dates["權變核定日期"] = str(top["uro_chk_date2"])
            if hdr_dates:
                probe_dates[cid] = hdr_dates
        # a candidate accepted on name AND date ends the probe. A KNOWN id is
        # never a probe candidate (it is already in the cache), but its
        # probed header — read from the memo or live — still persists its
        # dates when it carries the node's date: the offline header step
        # decides on it (玉泉11's 09504263 header approves 2013-08-20 while
        # data2 copies the 2008 plan-case date; 東湖34's 11502008, 康寧626's
        # 09712204 — the sweeps skipped known ids and the header never
        # reached the cache).
        for cid, cname in sorted(probe_names.items()):
            date_known = any(_iso_date(v) == target
                             for v in probe_dates.get(cid, {}).values())
            if cid in known:
                if date_known:
                    hdr = dict(case_header_entry(headers, cid))
                    for lbl, v in probe_dates.get(cid, {}).items():
                        hdr.setdefault("uro_chk_date" if lbl == "核定日期" else "uro_chk_date2", v)
                    if hdr and hdr != case_header_entry(headers, cid):
                        disc.case_headers[cid] = hdr
                continue
            date_ok = any(_iso_date(v) == target
                          for v in probe_dates.get(cid, {}).values())
            name_ok = (node_name_loose(cname) == node_name_loose(node_name)
                       or _probe_name_ok(cname, node_name, node_landcore,
                                         node_parcels=node_parcels,
                                         alt_landcores=alt_landcores))
            if not date_ok and name_ok:
                # a 概要 case carries its approval (概要核准日期) in the
                # milestones, not the header — 陽明291's 10903311 (NAME 事業
                # 概要階段─業經本府核准, header dates empty). Fetch the
                # milestones for a name-matching candidate with no header date.
                fetched = _milestones(cid)
                if fetched:
                    disc.case_milestones.setdefault(cid, fetched)
                    date_ok = any(_iso_date(str(fetched.get(lbl, "") or "")) == target
                                  for lbl in _APPROVAL_FIELDS)
            if not (date_ok and name_ok):
                # a dated header read this run persists even when the name
                # does not loose-match: the header is evidence about the case
                # (康寧626's 09712204 carries its approval only in the header,
                # and its name adds 及變更權利變換計畫案 to the gazette's 案名) —
                # the offline header step decides on the next pass, and the
                # probe is not repeated. Not a binding: no id, name or
                # milestone is written here.
                if date_ok:
                    hdr = dict(case_header_entry(headers, cid))
                    for lbl, v in probe_dates.get(cid, {}).items():
                        hdr.setdefault("uro_chk_date" if lbl == "核定日期" else "uro_chk_date2", v)
                    if hdr and hdr != case_header_entry(headers, cid):
                        disc.case_headers[cid] = hdr
                continue
            # accept: join the cache in place. The area-split rule applies to
            # the probe too: keep walking this base's batch and bind every
            # same-name same-date sibling carrying a distinct area suffix
            # (玉成166's A區/B區 pair, one gazette row).
            disc.city_case_ids = list(getattr(disc, "city_case_ids", None) or []) + [cid]
            disc.candidate_names[cid] = cname
            fetched = _milestones(cid)
            if fetched:
                disc.case_milestones[cid] = fetched
            hdr = dict(case_header_entry(headers, cid))
            hdr.setdefault("NAME", "")
            for lbl, v in probe_dates.get(cid, {}).items():
                hdr.setdefault("uro_chk_date" if lbl == "核定日期" else "uro_chk_date2", v)
            disc.case_headers[cid] = hdr
            bound = [cid]
            if _node_area_suffix(cname):
                for cid2, cname2 in sorted(probe_names.items()):
                    if cid2 == cid or cid2 in known or cid2 in bound:
                        continue
                    if not any(_iso_date(v) == target
                               for v in probe_dates.get(cid2, {}).values()):
                        continue
                    if node_name_loose(cname2) != node_name_loose(node_name):
                        continue
                    if _node_area_suffix(cname2) == _node_area_suffix(cname):
                        continue
                    disc.city_case_ids.append(cid2)
                    disc.candidate_names[cid2] = cname2
                    fetched2 = _milestones(cid2)
                    if fetched2:
                        disc.case_milestones[cid2] = fetched2
                    hdr2 = dict(case_header_entry(headers, cid2))
                    hdr2.setdefault("NAME", "")
                    for lbl, v in probe_dates.get(cid2, {}).items():
                        hdr2.setdefault("uro_chk_date" if lbl == "核定日期" else "uro_chk_date2", v)
                    disc.case_headers[cid2] = hdr2
                    bound.append(cid2)
            return bound

    # ── step 4: the parcel search on every parcel of the node ───────────────
    if not live_probe:
        return []
    section = getattr(member, "section", "") or ""
    # bind-the-unplaced-by-searching-the-cell-section: the 地號 cell's section
    # is a further form to ask for — the gazette's 案名 and 地號 columns can
    # disagree, and the city indexes the 地號 column's form (河堤五小段 vs
    # 河堤段五小段). The step-4 search adapter takes the extra forms.
    extra_sections = []
    cell_section = getattr(member, "section_land", "") or ""
    if not cell_section:
        from urtpe.cleanse import cell_section as _parse_cell_section
        cell_section = _parse_cell_section(getattr(member, "land", "") or "")
    if cell_section and cell_section != section:
        extra_sections.append(cell_section)
    parcels = list(getattr(member, "parcels", None) or [])
    for parcel in parcels:
        try:
            entries = search(section, parcel, extra_sections=extra_sections) or []
        except TypeError:
            # an adapter that does not take the extra forms (a test double, or
            # the sweep driver's own signature) — the 案名's form alone
            try:
                entries = search(section, parcel) or []
            except Exception:
                entries = []
        except Exception:
            entries = []
        for e in entries:
            cid = str(e.get("case_id") or "")
            if not cid or cid in known or cid in probe_names:
                continue
            cname = str(e.get("case_name", "") or "")
            if not (node_name_loose(cname) == node_name_loose(node_name)
                    or _probe_name_ok(cname, node_name, node_landcore,
                                      node_parcels=node_parcels,
                                      alt_landcores=alt_landcores)):
                continue
            # acceptance needs the approval date: read the header first
            top = _header(cid)
            date_ok = any(_iso_date(str(top.get(f, "") or "")) == target
                          for f in ("uro_chk_date", "uro_chk_date2"))
            fetched = {}
            if not date_ok:
                # the milestones may carry the approval the header omits (a
                # 概要 case's 概要核准日期, or a data2 gap)
                fetched = _milestones(cid)
                date_ok = any(_iso_date(str(fetched.get(lbl, "") or "")) == target
                              for lbl in _APPROVAL_FIELDS)
            if not date_ok:
                continue
            disc.city_case_ids = list(getattr(disc, "city_case_ids", None) or []) + [cid]
            disc.candidate_names[cid] = cname or str(top.get("CASE_NAME", "") or "")
            if not fetched:
                fetched = _milestones(cid)
            if fetched:
                disc.case_milestones[cid] = fetched
            hdr = dict(case_header_entry(headers, cid))
            hdr.setdefault("NAME", str(top.get("NAME", "") or ""))
            if top.get("uro_chk_date"):
                hdr["uro_chk_date"] = str(top["uro_chk_date"])
            if top.get("uro_chk_date2"):
                hdr["uro_chk_date2"] = str(top["uro_chk_date2"])
            disc.case_headers[cid] = hdr
            return [cid]

    return []


# 2.6: the unplaced-node flag. A node every resolver step misses is named on
# its record — never silently unbound (the truncated-records rule).
_UNPLACED_FLAG = "節點未能對應平台案件(案名:{name}, 日期:{date})"


def _flag_date(value: str) -> str:
    """The date a review flag quotes, in one shape.

    The node's own date reaches this flag in whatever form the pipeline
    currently holds: slash-western from the PDF (97/1/2), ISO from a
    --from-js rebuild. The flag text then changed between runs, so the
    duplicate collapse (which is by exact text) stopped working and a node
    carried the same finding twice, in two spellings — 15 nodes after the
    D7 re-emit. The flag quotes a normalised date so the text is a function
    of the node, not of the run.
    """
    text = (value or "").strip()
    m = re.fullmatch(r"(\d{4})/(\d{1,2})/(\d{1,2})", text)
    if m:
        return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    m = re.fullmatch(r"(\d{2,3})/(\d{1,2})/(\d{1,2})", text)
    if m:
        from urtpe.cleanse import roc_to_iso
        iso, _ymd = roc_to_iso(text)
        if iso:
            return iso
    return text


def _is_parcel_less_name(case_name: str) -> bool:
    """A settlement-named unit (崇仁新村) carries no 地號 by design; its
    extraction returning "" is the parcel-less rule, not a parse failure
    (orphan-case-anchoring §2 scenario; C4 counts it separately)."""
    return bool(case_name) and "地號" not in case_name and "號等" not in case_name


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


def attach_links_to_projects(projects: list[Project], discovered: dict,
                             probe_headers: dict | None = None,
                             permit_index_getter=None) -> None:
    """Attach discovered links; probe_headers is the resolver's offline memo
    ({case_id: header row}) from earlier probing runs — production emits it
    from the sweep driver, tests pass doubles. ``permit_index_getter`` is a
    zero-arg callable returning the building authority's permit index (or
    None); called once per project so the index builds lazily on first use."""
    disc_by_pid = {}
    for k, v in discovered.items():
        if hasattr(v, 'project_id'):
            disc_by_pid[k] = v
        elif isinstance(v, dict):
            obj = type('DiscoveryDict', (object,), {})()
            obj.project_id = k
            obj.twur_url = v.get("twur", "")
            # label-by-own-name round trip: the payload's twur_name survives a
            # --from-js reload like every other links field.
            obj.twur_name = v.get("twur_name", "")
            obj.city_case_ids = v.get("taipei", [])
            obj.national_milestones = v.get("milestones_national", {})
            obj.taipei_milestones = v.get("milestones_taipei", {})
            obj.case_milestones = v.get("case_milestones", {})
            obj.milestones_source = v.get("milestones_source", {})
            obj.implementation = v.get("implementation", {})
            obj.rewards = v.get("rewards", {})
            obj.search_rejected = v.get("search_rejected", {})
            obj.candidate_names = v.get("candidate_names", {})
            obj.case_schedules = v.get("case_schedules", {})
            # Pass through only when the payload carries it: a legacy payload
            # without the key must emit without the key (the viewer cannot
            # distinguish "no ids" from "never recorded"), and the orphan gate
            # reads it via getattr(..., None).
            if "view_verified_case_ids" in v:
                obj.view_verified_case_ids = v["view_verified_case_ids"]
            # supersede-headerless-cases D6: this object is built field by
            # field, so a field missing here is dropped on the next --from-js
            # run without any error (test_supersede pins the round trip).
            obj.superseded_by = v.get("superseded_by", {})
            # §8 (reject-foreign-view-cases): the same round-trip contract for
            # the ownership-gate fields.
            obj.case_headers = v.get("case_headers", {})
            obj.case_case_names = v.get("case_case_names", {})
            obj.view_rejected = v.get("view_rejected", {})
            obj.adopted_from_view = v.get("adopted_from_view", {})
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
            "taipei": sorted(disc.city_case_ids),
            "milestones_national": disc.national_milestones.copy(),
            "milestones_taipei": disc.taipei_milestones.copy(),
        }
        source_map = dict(getattr(disc, "milestones_source", None) or {})
        # D4a (2026-11-05): a payload round-trip carries the merged dict, so a
        # --from-js rebuild cannot see the per-case order the live merge used.
        # Re-derive the credit ONLY for labels whose per-case values agree on
        # one date across carriers (the equal-value case the first-holder rule
        # governs — 榮星53's shared 建照); a label whose carriers disagree is
        # a live last-write-wins whose true order the payload cannot restore,
        # so its round-tripped credit stands.
        per_case = getattr(disc, "case_milestones", None) or {}
        if per_case:
            for label in list(source_map):
                holders = [cid for cid in disc.city_case_ids
                           if label in (per_case.get(cid) or {})]
                if len(holders) < 2:
                    continue
                values = {per_case[cid][label] for cid in holders}
                if len(values) == 1:
                    source_map[label] = holders[0]
        if source_map:
            project.links["milestones_source"] = source_map
        if getattr(disc, "case_milestones", None):
            project.links["case_milestones"] = {
                k: dict(v) for k, v in disc.case_milestones.items()
            }
        if getattr(disc, "search_rejected", None):
            project.links["search_rejected"] = dict(disc.search_rejected)
        if getattr(disc, "candidate_names", None):
            project.links["candidate_names"] = dict(disc.candidate_names)
        if getattr(disc, "case_schedules", None):
            project.links["case_schedules"] = dict(disc.case_schedules)
        # supersede-headerless-cases D6: {old: new} for a case the city re-filed
        # under a new id; the viewer names the successor in 相關連結.
        if getattr(disc, "superseded_by", None):
            project.links["superseded_by"] = dict(disc.superseded_by)
        # label-by-own-name (C10): the national page's own 案名 rides the
        # payload beside twur_url; the viewer labels 國 with it. A legacy
        # result without the field (or an empty parse) emits without the key.
        _tn = getattr(disc, "twur_name", "") or ""
        if _tn:
            project.links["twur_name"] = _tn
        # fix-row-order-tiebreak-and-view-badges D4: the cases the project's
        # own national view page names in 相關連結 — the portal's assertion —
        # reach the payload so the viewer can badge those nodes 國. A legacy
        # result without the field emits without the key; an empty list is a
        # discovery fact (page had no ids) and is emitted as it is.
        if hasattr(disc, "view_verified_case_ids") and                 disc.view_verified_case_ids is not None:
            project.links["view_verified_case_ids"] = list(
                disc.view_verified_case_ids)
        # §8 (reject-foreign-view-cases): the ownership-gate records ride the
        # payload beside case_schedules, so a rejection is auditable offline.
        # Legacy results without the fields emit without the keys.
        for _f in ("view_rejected", "adopted_from_view"):
            _v = getattr(disc, _f, None)
            if _v:
                project.links[_f] = dict(_v)

        # Implementation (third.ashx) / rewards (fourth.ashx): project-level
        # attachment with case provenance (design D2/D5). Date fields surface as
        # milestones; the rest goes into the emitted objects.
        impl_all = getattr(disc, "implementation", None) or {}
        # D13: a case recorded as 無 carries a stale payload copy (the city
        # moved the case to a new id and emptied the old one), so it is
        # excluded from both selection layers — the key-count pick and the
        # plan-case date collection.
        wu_excluded = {cid for cid, s in (getattr(disc, "case_schedules", None) or {}).items()
                       if s == "無"}
        impl_cid, impl_payload, impl_flags = select_best_payload(impl_all, excluded=wu_excluded)
        # dates-follow-plan-case (C8a): the date fields follow the 擬訂 plan
        # case (per area), the statistics keep the D5 one-payload rule.
        impl_dates, impl_date_source, _stats_cid, impl_date_flags =             pick_implementation_payload(impl_all, getattr(disc, "candidate_names", None) or {}, excluded=wu_excluded)

        if impl_payload:
            impl_out = dict(impl_payload)
            impl_out["case_id"] = impl_cid
            merged_flags = list(impl_flags) + list(impl_date_flags)
            if merged_flags:
                impl_out["review_flags"] = merged_flags
            project.implementation = impl_out
            for label, date in implementation_milestones(impl_payload).items():
                project.links["milestones_taipei"][label] = date
                project.links.setdefault("milestones_source", {})[label] = impl_cid
            # the plan case's dates overwrite the D5 payload's dates, with the
            # plan case as their provenance
            for label, date in impl_dates.items():
                project.links["milestones_taipei"][label] = date
                project.links.setdefault("milestones_source", {})[label] = impl_date_source[label]
        rew_cid, rew_payload, rew_flags = select_best_payload(
            getattr(disc, "rewards", None) or {}, excluded=wu_excluded)
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
            # node whose 核定日期 matches the case's approval date. When dates
            # cannot disambiguate, resolve-recno-case (S10, C6) binds the node
            # by the 4-step resolver — 案名 tiers, same-day probe, header
            # dates, all-parcel search — never by list position (the
            # positional fallback bound 71 nodes on 51 projects to a case the
            # node's own date refutes; the user rule 2026-11-04: every recno
            # has a corresponding city case).
            # member.date is the raw gazette date — ROC (97/1/2) in the PDF
            # pipeline, ISO in --from-js regens; the matcher handles both.
            matched = _match_case_by_date(member.date, disc)
            if matched:
                node_links["taipei"].append(matched)
            else:
                resolved = resolve_node_cases(member, disc,
                                              probe_headers=probe_headers)
                node_links["taipei"].extend(resolved)
                if not resolved:
                    flag = _UNPLACED_FLAG.format(
                        name=(getattr(member, "name", "") or "")[:40],
                        date=_flag_date(getattr(member, "date", "") or ""))
                    if flag not in member.review_flags:
                        member.review_flags = list(member.review_flags) + [flag]
            # D9c-2a: a node that NOW binds a case must not keep the flag
            # that says it binds none. The flag is a property of the node's
            # binding, not of the run: the second id source and the alias
            # merge give a node the case the parcel search could not reach
            # (南港566's nodes 744 and 1063), and the flag carried forward by
            # the --from-js loader then read as a live finding.
            if node_links["taipei"]:
                stale = [f for f in member.review_flags
                         if f.startswith(_UNPLACED_FLAG.split("{")[0])]
                if stale:
                    member.review_flags = [f for f in member.review_flags
                                           if f not in stale]

            # §12 #2 chimera emit fix: the node carries ITS OWN approval's
            # per-case timeline, not the project-level last-write-wins merged
            # dict (319 families have multiple distinct 核定日期 — the merged
            # value shows the newest fetched case's date on every node). The
            # merged dict remains the fallback and stays at project level
            # unchanged (the 階段辦理過程 card + milestones_source provenance).
            anchored_cid = node_links["taipei"][0] if node_links["taipei"] else ""
            own_ms = (getattr(disc, "case_milestones", None) or {}).get(anchored_cid)
            if own_ms:
                node_links["milestones_taipei"] = dict(own_ms)
            else:
                node_links["milestones_taipei"] = dict(
                    getattr(disc, "taipei_milestones", None) or {})

            # §9.4 gazette printing anomaly: the PDF's printed 階段 may
            # disagree with the platform's recorded case state for the
            # anchored case (吉林段四小段603 node 920: gazette 擬訂 vs platform
            # 變更[已核准]). Keep the printed stage (faithful to the PDF) and
            # route the disagreement to human review via a flag.
            if anchored_cid and member.stage:
                case_name = (getattr(disc, "candidate_names", None) or {}).get(anchored_cid, "")
                if case_name:
                    m_case = re.match(r"(擬訂|變更(?:\(第[一二三四五六七八九十]+\))?)", case_name)
                    if m_case and m_case.group(1) != member.stage:
                        # Idempotent: a disagreement is a property of the record/case
                        # pair, not an event that recurs. Appending unconditionally,
                        # combined with --from-js reading clean.tsv back as its input,
                        # made every run add a copy — measured at 1162 occurrences of
                        # one flag across 282 nodes.
                        flag = (f"階段與平台案件狀態不一致"
                                f"(公報{member.stage}/平台{m_case.group(1)})")
                        if flag not in member.review_flags:
                            member.review_flags = list(member.review_flags) + [flag]

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

        anchored_case_ids = set()
        for member in project.members:
            for cid in (member.links or {}).get("taipei", []):
                anchored_case_ids.add(cid)

        orphan_case_ids = set(disc.city_case_ids) - anchored_case_ids
        if orphan_case_ids and project.members:
            anchor_record = next(
                (m for m in project.members if m.recno == project.anchor_recno),
                project.members[0],
            )
            anchor_landcore_str = build_land_core_key(anchor_record)
            source_map = getattr(disc, "milestones_source", None) or {}
            attributed_case_ids = set(source_map.values())
            anchored_date_pool = set()
            for aid in anchored_case_ids:
                anchored_date_pool |= set((disc.case_milestones.get(aid) or {}).items())
            orphan_nodes = []
            view_verified = set(getattr(disc, "view_verified_case_ids", None) or [])
            superseded = set(getattr(disc, "superseded_by", None) or {})
            for cid in orphan_case_ids:
                # hide-superseded-orphans (S6, B2): a re-filed case's undated
                # node showed a process the city has replaced — withhold the
                # node; the case stays in city_case_ids (append-only) and the
                # successor carries the live history
                if cid in superseded:
                    continue
                similar = False
                twin_shared_dates = None
                own_milestones = disc.case_milestones.get(cid) or {}
                case_name = ((getattr(disc, "search_rejected", None) or {}).get(cid, "")
                             or (getattr(disc, "candidate_names", None) or {}).get(cid, ""))
                if cid in view_verified:
                    # Portal-verified: the case is listed on this project's own
                    # national view page 相關連結 — no similarity gate needed
                    # (parcel-less case names would score 0.0).
                    similar = True
                elif case_name:
                    orphan_landcore = extract_landcore_from_case_name(case_name)
                    if orphan_landcore and compute_landcore_similarity(
                        anchor_landcore_str, orphan_landcore
                    ) >= 0.7:
                        similar = True
                elif cid in attributed_case_ids:
                    similar = True
                else:
                    own_dates = set(own_milestones.items())
                    shared = own_dates & anchored_date_pool
                    if len(shared) >= TWIN_BRIDGE_MIN_SHARED_DATES:
                        similar = True
                        twin_shared_dates = dict(shared)
                if not similar:
                    # parse-listed-parcel-names: a named orphan that fails the
                    # gate is named on the anchor record, never dropped
                    # silently (AGENTS.md; C4 measured 8 silent drops). Two
                    # reasons get distinct flags: the name still yields no
                    # land core (unparseable), or it parses but scores below
                    # LINK_THRESHOLD (華中247's A區/B區 cases: first parcel
                    # 201-2 vs the anchor's 247, 0.45 — a merge question, not
                    # a parse one). Parcel-less names (崇仁新村) are the
                    # designed exclusion and are not reported.
                    if case_name and not _is_parcel_less_name(case_name):
                        lc = extract_landcore_from_case_name(case_name)
                        if lc == "":
                            flag = (f"孤兒案件名稱無法解析地段地號(案{cid}:"
                                    f"{case_name[:40]})")
                        else:
                            sim = compute_landcore_similarity(anchor_landcore_str, lc)
                            flag = (f"孤兒案件未達相似度門檻(案{cid}:"
                                    f"{sim:.2f}<{_link_threshold():.2f}:"
                                    f"{case_name[:40]})")
                        if flag not in anchor_record.review_flags:
                            anchor_record.review_flags = list(anchor_record.review_flags) + [flag]
                    continue
                if twin_shared_dates is not None:
                    orphan_milestones_taipei = dict(twin_shared_dates)
                else:
                    orphan_milestones_taipei = {}
                    for label, src_cid in source_map.items():
                        if src_cid == cid and label in disc.taipei_milestones:
                            orphan_milestones_taipei[label] = disc.taipei_milestones[label]
                orphan_milestones_national = dict(disc.case_milestones.get(cid) or {})
                orphan_nodes.append({
                    "case_id": cid,
                    "case_name": case_name,
                    "orphan": True,
                    "provenance": "orphan-case-anchoring",
                    "stage": derive_stage_from_case_name(case_name),
                    "track": derive_track_from_case_name(case_name),
                    "node_date": _ghost_node_date(own_milestones, derive_track_from_case_name(case_name)),
                    "schedule": (getattr(disc, "case_schedules", None) or {}).get(cid, ""),
                    "milestones_taipei": orphan_milestones_taipei,
                    # D1 (inspection-batchD): this dict is the Taipei ashx's
                    # per-case milestones — the old key `milestones_national`
                    # falsely claimed the national data space (name wrong,
                    # data right). `--from-js` aliases the old key on load.
                    "milestones_taipei_case": orphan_milestones_national,
                })
            if orphan_nodes:
                # sorted at publication, not at build: the build order follows the
                # concurrent Taipei fetches, and two runs must emit the same file
                project.links["orphan_nodes"] = _sorted_orphan_nodes(orphan_nodes)

        # building-permit-adapter (S15, C5): the building authority's 使用執照
        # 摘要 witnesses the 使照 date the two portals copy. The index is the
        # caller's (downloaded once per run under the archive root); a project
        # without a permit entry or without both portal dates stays unflagged
        # — the witness never repairs (design D4).
        permit_index = permit_index_getter() if permit_index_getter else None
        if permit_index:
            project_parcels = []
            seen_parcel: set = set()
            for member_p in project.members:
                section_p = getattr(member_p, "section", "") or ""
                district_p = getattr(member_p, "district_land", "") or getattr(member_p, "district", "") or ""
                for parcel in getattr(member_p, "parcels", None) or []:
                    mono = str(parcel).partition("-")[0]
                    key = (district_p.replace(section_p[:len(district_p)], "", 1)
                           if district_p and section_p.startswith(district_p) and district_p
                           else district_p, section_p, mono)
                    if key not in seen_parcel:
                        seen_parcel.add(key)
                        project_parcels.append(key)
            if project_parcels:
                try:
                    permits = match_project_permits(permit_index, project_parcels)
                except Exception:
                    permits = []
                if permits:
                    # D10: the witness is the permit whose 開工日期 equals the
                    # city's. The permit index keys on the mono parcel, so a
                    # section that redeveloped over time accumulates one permit
                    # per building phase, and the old "first of the tie" rule
                    # named the OLDEST one — 43 projects showed a 執照 date
                    # that was not their own 使照, silently.
                    #
                    # The city's 開工 date is read from the SOURCE MAP, not
                    # from the merged dict: the merged dict can be stale, and
                    # the source map names the case that holds the value (the
                    # same rule D4a established for the construction chain).
                    city_start = _city_construction_start(project.links)
                    best, ambiguous = select_permit_witness(permits, city_start)
                    if best is not None:
                        project.links["permit"] = {
                            "permit_no": best.permit_no,
                            "date": best.date,
                            "permits": [p.permit_no for p in permits],
                        }
                    elif ambiguous:
                        # no single permit: show the candidates rather than an
                        # arbitrary one
                        project.links["permit"] = {
                            "ambiguous": True,
                            "permits": [p.permit_no for p in permits],
                        }
                mt = project.links.get("milestones_taipei") or {}
                mn = project.links.get("milestones_national") or {}
                flags = permit_review_flags(
                    mt.get("使照核發日期", ""), mn.get("使用核發日期", ""), permits)
                if flags:
                    anchor = next(
                        (m for m in project.members
                         if m.recno == project.anchor_recno), project.members[0])
                    for flag in flags:
                        if flag not in anchor.review_flags:
                            anchor.review_flags = list(anchor.review_flags) + [flag]

    # §6.8: after node anchoring, surface fragment families as merge
    # candidates (review flags on anchor records; no family mutation).
    _flag_fragment_families(projects, detect_fragment_families(projects, discovered))


def _city_construction_start(links: dict) -> str:
    """The city's 開工日期, read from the milestone SOURCE MAP (D10).

    The permit witness is chosen by the city's 開工 date, so the value must be
    attributable and current. The merged ``milestones_taipei`` dict can be
    stale — that is what D7 found — while ``milestones_source`` names the case
    that holds each value. The same rule D4a established for the construction
    chain.

    The date is normalised to ISO, because the permit record's
    ``construction_start`` is ISO and the city's value may be slash-western.

    Returns "" when the project carries no 開工 date, or when the merged dict
    holds one that no case in the source map backs.
    """
    merged = (links or {}).get("milestones_taipei") or {}
    source = (links or {}).get("milestones_source") or {}
    raw = merged.get("開工日期", "")
    if not raw:
        return ""
    cid = source.get("開工日期")
    if not cid:
        # no source for the label: the value is unattributable, so it cannot
        # choose the witness
        return ""
    m = re.fullmatch(r"(\d{4})/(\d{1,2})/(\d{1,2})", str(raw).strip())
    if m:
        return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", str(raw).strip())
    if m:
        return m.group(0)
    return str(raw).strip()


class LinksDiscovery:
    """High-level discovery orchestrator with CLI-friendly interface."""

    def __init__(self, cache_dir: str = "data/.link_cache", delay: float = 1.0):
        self.cache_dir = Path(cache_dir)
        self.delay = delay

    def _fresh_backup(self) -> None:
        """A destructive --fresh renames the cache to a timestamped backup
        instead of deleting it (P2.2): portal_index.json (the only reachability
        path for the ~110 oldest portal entries), no_match_ledger.json, and the
        per-project result.json dirs are durable state the coverage guard
        cannot resurrect once gone. The five .link_cache_backup_* directories
        in data/ exist because of this class of incident."""
        if self.cache_dir.exists():
            stamp = time.strftime("%Y%m%d_%H%M%S")
            backup = self.cache_dir.parent / f".link_cache_backup_{stamp}"
            suffix = 1
            while backup.exists():          # two backups in the same second
                suffix += 1
                backup = self.cache_dir.parent / f".link_cache_backup_{stamp}_{suffix}"
            self.cache_dir.rename(backup)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def run(self, projects: list[Project], fresh: bool = False, use_playwright: bool = False) -> dict[str, DiscoveryResult]:
        """Run discovery for all projects."""
        if fresh:
            self._fresh_backup()

        portal_index = build_portal_index(self.cache_dir, fresh)
        multimap = build_index_multimap(portal_index)

        sorted_projects = sorted(projects, key=lambda p: p.project_id)

        # A record naming a project this dataset no longer contains is a moved identity.
        # Reporting it here is the only place the whole dataset is enumerated, so it would
        # otherwise never be reported and the record would silently stop applying.
        unattached_overrides(self.cache_dir, [p.project_id for p in projects])

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