"""Cleansing domain: normalization rules and field derivation.

Pure logic — no file or PDF I/O. Operates on RawRecord and produces
CleanRecord plus auto-fix and review/flag annotations.
"""

from __future__ import annotations

import re

from urtpe.models import CleanRecord, RawRecord

CN_NUM = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
CN_TENS = {"十": 10}

DISTRICT_FIXES = {"松化區": "松山區"}

# 行政區 of Taipei (for mismatch detection)
DISTRICT_RE = re.compile(r"臺北市(.{1,4}?區)")
SECTION_TOKEN = r"[\u4e00-\u9fffA-Za-z]+?(?:段[一二三四五六七八九十]*小段|[一二三四五六七八九十]+小段|段)"
SECTION_RE = re.compile(r"(" + SECTION_TOKEN + ")")
AREA_RE = re.compile(r"\(([A-D甲乙丙丁])區段\)")
COUNT_RE = re.compile(r"地號(?:等)?\s*(\d+)\s*筆")
ALIAS_RE = re.compile(r"(\d+(?:-\d+)?)地號\(原(?:核定地號為)?([^）]+)\)")
ANCHOR_TERMS = ("基地", "國宅", "整宅", "大樓", "市場")
ORIG_RE = re.compile(r"\(原(\d+)筆")
ANCHOR_CAPTURE_RE = re.compile(r"原([^()）\s、]{1,20})")
NAME_ID_RE = re.compile(r"臺北市(.{1,4}?區)(" + SECTION_TOKEN + r")(\d+(?:-\d+)?)地號(?:等)?(\d+)?筆")


def parse_name_id(name: str) -> tuple[str, str, str, int | None]:
    """Parse stable case identity from the 案名: (district, section, parcel, count)."""
    m = NAME_ID_RE.search(name)
    if not m:
        return "", "", "", None
    count = int(m.group(4)) if m.group(4) else None
    return m.group(1), m.group(2), m.group(3), count
STAGE_RE = re.compile(r"^(擬訂|變更(?:\(第([一二三四五六七八九十]+)次\))?)")

AREA_CN = {
    "一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
    "六": 6, "七": 7, "八": 8, "九": 9, "十": 10,
}


def cn_to_int(s: str) -> int:
    if not s:
        return 0
    if s in CN_TENS:
        return 10
    if "十" in s:
        left, _, right = s.partition("十")
        return (CN_NUM.get(left, 1) if left else 1) * 10 + (CN_NUM.get(right, 0) if right else 0)
    return CN_NUM.get(s, 0)


def roc_to_iso(date_str: str) -> tuple[str | None, tuple[int, int, int] | None]:
    """Convert ROC date 'YY/M/D' to ISO-8601 (ROC + 1911)."""
    m = re.fullmatch(r"(\d{1,3})/(\d{1,2})/(\d{1,2})", date_str.strip())
    if not m:
        return None, None
    y, mo, d = (int(g) for g in m.groups())
    iso = f"{y + 1911:04d}-{mo:02d}-{d:02d}"
    return iso, (y + 1911, mo, d)


def normalize_name(name: str) -> str:
    name = name.replace("計劃", "計畫")
    name = name.replace("ㄧ", "一")
    name = re.sub(r"\s+", "", name)
    return name


def _land_district(land_clean: str) -> str:
    m = DISTRICT_RE.search(land_clean)
    return m.group(1) if m else ""


def _section(land_clean: str) -> tuple[str, str]:
    """Return (section, remainder after section)."""
    m = DISTRICT_RE.search(land_clean)
    rest = land_clean[m.end():] if m else land_clean
    m2 = SECTION_RE.search(rest)
    if not m2:
        return "", rest
    section = m2.group(1)
    idx = m2.end()
    if section.startswith(rest[:1]) and len(section) > 1 and "區" in section:
        # leftover district prefix inside section token
        pass
    return section, rest[idx:]


def _parse_land(land: str) -> dict:
    """Parse the 地號 cell into parcels, aliases, counts, section."""
    clean = land.replace(" ", "").replace("\u3000", "")
    clean = clean.replace("計劃", "計畫").replace("ㄧ", "一")
    section, rest = _section(clean)
    if not section:
        rest = clean  # continuation cell without the 段小段 prefix

    area = ""
    am = AREA_RE.search(clean)
    if am:
        area = am.group(1)

    aliases: dict[str, list[str]] = {}
    for pm in ALIAS_RE.finditer(rest):
        vals = []
        for a in pm.group(2).split("、"):
            a = re.sub(r"地號$", "", a.strip())
            if a and a not in vals:
                vals.append(a)
        if vals:
            aliases.setdefault(pm.group(1), []).extend(vals)
    rest2 = ALIAS_RE.sub(r"\1地號", rest)

    land_count = None
    cm = COUNT_RE.search(rest2)
    parcels_raw = rest2
    if cm:
        land_count = int(cm.group(1))
        parcels_raw = rest2[: cm.start()]

    # drop trailing parenthetical noise (e.g. (現況整併為68及92地號等2筆))
    parcels_raw = re.sub(r"[\(（][^)）]*[\)）]\s*$", "", parcels_raw)
    parcels_raw = parcels_raw.replace("土地", "")

    parcels: list[str] = []
    for tok in parcels_raw.split("、"):
        t = tok.strip()
        t = re.sub(r"\([^)）]*\)", "", t)  # strip inline (部分)/(B區段)
        t = re.sub(r"地號$", "", t)
        t = re.sub(r"^0*", "", t)
        if re.fullmatch(r"\d+(?:-\d+)?", t) and t not in parcels:
            parcels.append(t)

    return {"section": section, "parcels": parcels, "aliases": aliases,
            "land_count": land_count, "area_section": area}


def _stage(name: str) -> tuple[str, int]:
    m = STAGE_RE.match(name)
    if not m:
        return "", -1
    if m.group(1) == "擬訂":
        return "擬訂", 0
    if m.group(2):
        return f"變更(第{m.group(2)}次)", cn_to_int(m.group(2))
    return "變更", 1


def _tracks(name: str) -> list[str]:
    found = []
    if "事業概要" in name:
        found.append("事業概要")
    if "事業計畫" in name:
        found.append("事業計畫")
    if "權利變換" in name:
        found.append("權利變換")
    if not found:
        if "都市更新計畫" in name:
            found.append("都市更新計畫")
        else:
            found.append("其他")
    return found


def _orig_count(name: str, land: str) -> int | None:
    for hay in (name, land):
        m = ORIG_RE.search(hay)
        if m:
            return int(m.group(1))
    return None


def cleanse(rec: RawRecord) -> CleanRecord:
    """Normalize one raw record into a CleanRecord with fixes and flags."""
    fixes: list[str] = []
    flags: list[str] = []

    district = rec.district.strip()
    if district in DISTRICT_FIXES:
        fixes.append("行政區錯字→松山區")
        district = DISTRICT_FIXES[district]

    iso, ymd = roc_to_iso(rec.date)
    if iso is None:
        flags.append("日期無法解析")

    name_raw = re.sub(r"\s+", "", rec.name)
    name = normalize_name(name_raw)

    land_clean = re.sub(r"\s+", "", rec.land)
    land_district = _land_district(land_clean)
    if land_district and district and land_district != district:
        flags.append(f"行政區與地號行政區不一致(地號為{land_district})")

    pl = _parse_land(rec.land)
    if not pl["section"]:
        flags.append("地號無法解析(缺少段小段)")
    elif not pl["parcels"]:
        flags.append("地號無法解析(缺少地號清單)")

    # 案名 carries the stable case identity even when the 地號 cell is a
    # wrapped continuation missing its 段小段 prefix. Prefer it, fall back to
    # the land cell.
    nd, ns, np, nc = parse_name_id(name)
    section = ns or pl["section"]
    first_parcel = np or (pl["parcels"][0] if pl["parcels"] else "")
    land_count = nc if nc is not None else pl["land_count"]
    if ns and pl["section"] and ns != pl["section"]:
        flags.append(f"案名與地號段小段不一致(地號為{pl['section']})")

    orig = _orig_count(name, rec.land)
    stage, stage_index = _stage(name)
    tracks = _tracks(name)
    track = "、".join(tracks)

    anchor = ""
    for am in (ANCHOR_CAPTURE_RE.search(name), ANCHOR_CAPTURE_RE.search(land_clean)):
        if am and re.search(r"(基地|國宅|整宅|大樓|市場)$", am.group(1)):
            anchor = "原" + am.group(1)
            break

    return CleanRecord(
        recno=rec.recno,
        date=rec.date,
        iso_date=iso or "",
        ymd=ymd or (0, 0, 0),
        district=district,
        district_land=land_district,
        name=name,
        name_raw=name_raw,
        land=rec.land,
        section=section,
        first_parcel=first_parcel,
        parcels=pl["parcels"],
        aliases=pl["aliases"],
        land_count=land_count,
        orig_count=orig,
        named_anchor=anchor,
        area_section=pl["area_section"],
        stage=stage,
        stage_index=stage_index,
        track=track,
        implementer=re.sub(r"\s+", "", rec.implementer),
        planner=re.sub(r"\s+", "", rec.planner),
        auto_fixes=fixes,
        review_flags=flags,
    )


def cleanse_all(records: list[RawRecord]) -> list[CleanRecord]:
    return [cleanse(r) for r in records]