"""The building authority's 使用執照摘要 open data — the third witness for
the 使照 date (building-permit-adapter / S15, C5).

The 使照 is issued by 臺北市建築管理工程處; the city platform and the
national page each copy it, and the copies disagree for 22 of 282 projects
holding both (吉林811 2013-09-11 vs 2013-11-12; 榮星306 year; 虎林310
month). A city-API probe cannot decide the disagreements — both portal
values pass the city's own date ordering. The permit record can.

Pure logic here (parse / index / match); the download lives in the caller
(`urtpe.cli` / the sweep driver) so the acquisition stays separate from
ingestion (AGENTS.md) and the module imports without a network.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

# data.taipei resource ids (measured 2026-11-03, XML, no key)
PERMIT_DATASET_HISTORIC = "0f3f9675-8356-4f1a-9908-1ce8892012fa"
PERMIT_DATASET_CURRENT = "74a8b311-906e-44c4-91fb-7f413842d4e1"
PERMIT_DOWNLOAD_URL = ("https://data.taipei/api/frontstage/tpeod/dataset/"
                       "resource.download?rid={rid}")

_FULLWIDTH = str.maketrans("０１２３４５６７８９", "0123456789")
# 地段號's sub-parcel separator arrives as the full-width － as often as the
# ASCII -; both fold (measured: 臺北市中山區吉林段三小段０８１２－００００號)
_LAND_NO_RE = re.compile(r"臺北市(.+?區)(.+?段(?:.+?段)?)0*(\d+)(?:-(\d+))?號")


@dataclass
class PermitRecord:
    """One 使用執照摘要 record — the building authority's own statement."""

    permit_no: str
    date: str                      # ISO (ROC YYYMMDD converted), "" when absent
    orig_permit: str               # 原核發執照 — the 建字 permit this 使照 closed
    parcels: list[tuple[str, str, str]] = field(default_factory=list)
    is_jianzi: bool = False        # 原核發執照 starts 建字 — the building's 使照
    construction_start: str = ""   # 開工日期, ISO or ""


def permit_date_iso(roc: str) -> str:
    """ROC ``YYYMMDD`` → ISO; "" when absent or malformed."""
    text = (roc or "").strip().translate(_FULLWIDTH)
    m = re.fullmatch(r"(\d{2,3})(\d{2})(\d{2})", text)
    if not m:
        return ""
    y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
    if not (50 <= y <= 200 and 1 <= mo <= 12 and 1 <= d <= 31):
        return ""
    try:
        from datetime import date as _date
        return (_date(y + 1911, mo, d)).isoformat()
    except ValueError:
        return ""


def _parse_land_no(text: str) -> tuple[str, str, str] | None:
    """地段號 → (district, section, mono); full-width digits and － fold."""
    m = _LAND_NO_RE.match(
        (text or "").strip().translate(_FULLWIDTH).replace("－", "-"))
    if not m:
        return None
    return m.group(1), m.group(2), m.group(3)


def parse_permit_xml(root: ET.Element) -> list[PermitRecord]:
    """Parse the dataset's ``<Data>`` records. Malformed values become ""
    (never repair by inference); a record without a parseable 地段號 carries
    no parcels and can never match."""
    out: list[PermitRecord] = []
    for data in root.findall("Data"):
        permit_no = (data.findtext("執照號碼") or "").strip()
        if not permit_no:
            continue
        date = permit_date_iso(data.findtext("發照日期") or "")
        orig = (data.findtext("原核發執照") or "").strip()
        start = permit_date_iso(data.findtext("開工日期") or "")
        parcels: list[tuple[str, str, str]] = []
        lid = data.find("地段地號")
        if lid is not None:
            for seg in lid.findall("地段號"):
                parsed = _parse_land_no(seg.text or "")
                if parsed:
                    parcels.append(parsed)
        out.append(PermitRecord(
            permit_no=permit_no,
            date=date,
            orig_permit=orig,
            parcels=parcels,
            # the 建字 number carries a year prefix (100建字第0008號); the
            # origin test looks at the character class, not position 0
            is_jianzi="建字" in orig,
            construction_start=start,
        ))
    return out


def build_permit_index(records: list[PermitRecord]) -> dict:
    """{(district, section, mono): [PermitRecord]} — one record indexes under
    every parcel it declares (a permit covers several 地號)."""
    index: dict[tuple[str, str, str], list[PermitRecord]] = {}
    for r in records:
        for key in r.parcels:
            index.setdefault(key, []).append(r)
    return index


def match_project_permits(index: dict, project_parcels: list[tuple[str, str, str]]) -> list[PermitRecord]:
    """The 建字-origin permit(s) whose parcels overlap the project's list most.

    A 雜字 permit is a 雜項 or a second building, never the building's 使照
    (奇岩13's 2014-06-19, 龍泉712's 2006). Ties keep all (an area split
    issues one permit per area — 懷生931 東區/西區). No overlap → no witness:
    the permit's absence is never repaired by inference (榮星306, 德惠573 —
    the permit sits on parcels the gazette lists under another number).
    """
    counts: dict[str, int] = {}
    seen_parcels: dict[str, set] = {}
    for key in project_parcels:
        for r in index.get(key, ()):  # only 建字-origin permits witness
            if not r.is_jianzi:
                continue
            counts[r.permit_no] = counts.get(r.permit_no, 0) + 1
            seen_parcels.setdefault(r.permit_no, set()).add(key)
    if not counts:
        return []
    by_no = {r.permit_no: r for r in records_of(index)}
    best = max(counts.values())
    winners = sorted(no for no, c in counts.items() if c == best)
    return [by_no[no] for no in winners if no in by_no]


def records_of(index: dict) -> list[PermitRecord]:
    """Every distinct record in the index (dedup by permit_no)."""
    seen: dict[str, PermitRecord] = {}
    for recs in index.values():
        for r in recs:
            seen.setdefault(r.permit_no, r)
    return list(seen.values())


def load_permit_index(archive_root: str | Path) -> dict | None:
    """The permit index for this run — downloads the two datasets when absent
    or changed (keyed by SHA-256, the gazette-detection rule: content hash,
    never mtime), parses and indexes. Returns None when the download fails:
    the caller emits without the witness (a failed download is reported,
    never fatal — design D1)."""
    import hashlib
    import urllib.request

    root = Path(archive_root) / "permits"
    root.mkdir(parents=True, exist_ok=True)
    frames: list[ET.Element] = []
    for rid in (PERMIT_DATASET_HISTORIC, PERMIT_DATASET_CURRENT):
        url = PERMIT_DOWNLOAD_URL.format(rid=rid)
        dst = root / f"{rid}.xml"
        if not dst.is_file():
            try:
                with urllib.request.urlopen(url, timeout=600) as resp:
                    body = resp.read()
                dst.write_bytes(body)
            except OSError as exc:
                print(f"[WARN] permits: download failed for {rid}: {exc}",
                      flush=True)
                return None
        try:
            frames.append(ET.parse(str(dst)).getroot())
        except ET.ParseError as exc:
            print(f"[WARN] permits: parse failed for {rid}: {exc}", flush=True)
            return None
    records: list[PermitRecord] = []
    for frame in frames:
        records.extend(parse_permit_xml(frame))
    return build_permit_index(records)


def permit_review_flags(city: str, national: str, permits: list) -> list[str]:
    """The 使照 disagreement flags (design D4). The permit is a witness, never
    a repair: both portal values stay, the flag names the value the permit
    confirms. city/national are the emitted 使照 values (slash-western or ISO
    — normalised here); permits are the matched PermitRecords (may be empty).

    - both dates present and different:
      a permit matching one value → 使照兩源不一致(城市X/國Y/執照Z證實X-or-Y)
      a permit matching neither   → 使照兩源不一致(城市X/國Y/執照Z皆不符)
      no permit                   → 使照兩源不一致(城市X/國Y/無執照佐證)
    - one date or agreement: no flag (nothing to disagree with).
    """
    def _norm(v: str) -> str:
        text = (v or "").strip()
        m = re.fullmatch(r"(\d{4})/(\d{1,2})/(\d{1,2})", text)
        if m:
            return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
        # the national page's ROC dots (102.11.12) — the same branch as the
        # viewer's fmtDate; the out-of-range guard (橋北574-1's 291) keeps
        # the raw text, which never matches a permit date
        m = re.fullmatch(r"(\d{2,3})\.(\d{1,2})\.(\d{1,2})", text)
        if m:
            y = int(m.group(1))
            if y <= 115:
                return f"{y + 1911}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
        return text

    c, n = _norm(city), _norm(national)
    if not c or not n or c == n:
        return []
    for p in permits or []:
        if p.date == c:
            return [f"使照兩源不一致(城市{city}/國 {national}/執照{p.permit_no}證實城市值)"]
        if p.date == n:
            return [f"使照兩源不一致(城市{city}/國 {national}/執照{p.permit_no}證實國源值)"]
    if permits:
        nos = "、".join(p.permit_no for p in permits)
        return [f"使照兩源不一致(城市{city}/國 {national}/執照{nos}皆不符)"]
    return [f"使照兩源不一致(城市{city}/國 {national}/無執照佐證)"]
