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


def to_iso(date_str: str) -> tuple[str | None, tuple[int, int, int] | None]:
    """Convert a 核定日期 cell to ISO-8601, accepting either calendar.

    The city published ROC dates (``115/8/27``) until the 1151002 gazette, which
    switched to Gregorian (``2026/9/24``). ROC years are 1-3 digits and always below
    1912, so a year under 1911 is unambiguously ROC and the decision is safe per
    cell — one publication may mix calendars.

    Kept as an alias of :func:`urtpe.extract.to_iso` so the cleansing layer and the
    reader agree on exactly one calendar rule.
    """
    from urtpe.extract import to_iso as _to_iso

    return _to_iso(date_str)


def roc_to_iso(date_str: str) -> tuple[str | None, tuple[int, int, int] | None]:
    """Deprecated alias for :func:`to_iso`."""
    return to_iso(date_str)


def normalize_name(name: str) -> str:
    name = name.replace("計劃", "計畫")
    name = name.replace("ㄧ", "一")
    name = re.sub(r"\s+", "", name)
    return name


def _printed_district(land_clean: str) -> str:
    """The district token as the 地號 cell prints it.

    D14(b): this is the strict 臺北市-anchored read, kept for the mismatch
    flag. It is what the cell literally shows — `投區` on the 臺北市投區 rows —
    so the flag keeps quoting the publisher's own text. The field
    ``district_land`` holds the normalized district instead.
    """
    m = DISTRICT_RE.search(land_clean)
    return m.group(1) if m else ""


def _land_district(land_clean: str, districts: tuple[str, ...] | None = None) -> str:
    """The 地號 cell's district.

    D14(b): with a collected enum, the cell's district is read from that enum
    — the city prints 臺北大安區 / 臺北士林區 (no 市) and 臺北市投區 (no 北),
    and the strict 臺北市-anchored regex read the first two as no district and
    the third as the non-district 投區 (which then travelled into the land
    core). A cell naming a district the enum lacks reads '' — the system never
    infers the missing character.

    Without an enum the strict reading stays, so the single-record call sites
    keep today's answers.
    """
    if not districts:
        m = DISTRICT_RE.search(land_clean)
        return m.group(1) if m else ""
    m = _enum_district_re(districts).search(land_clean)
    return m.group(1) if m else ""


_ENUM_RE_CACHE: dict[tuple[str, ...], re.Pattern] = {}


def _enum_district_re(districts: tuple[str, ...]) -> re.Pattern:
    """A pattern for the enum's district names, anchored on the optional
    臺北市 prefix. Longest name first, so 中山區 cannot shadow 中山區X."""
    key = tuple(districts)
    pat = _ENUM_RE_CACHE.get(key)
    if pat is None:
        names = sorted(key, key=lambda s: (-len(s), s))
        pat = re.compile("臺北市?(" + "|".join(map(re.escape, names)) + ")")
        _ENUM_RE_CACHE[key] = pat
    return pat


def collect_districts(records) -> tuple[str, ...]:
    """The corpus's own 行政區 values, as the enum for the district read.

    D14(b): the set of known districts comes from the data, not from a list in
    the reader — a hard-coded list would be a second source of truth that
    drifts from what the city publishes. The known typo (松化區 → 松山區) is
    corrected here, so the enum holds the districts the corpus publishes (12),
    not the typo the city printed on one row.
    """
    seen = set()
    for r in records:
        d = str(getattr(r, "district", "") or "").strip()
        d = DISTRICT_FIXES.get(d, d)
        if d and d.endswith("區"):
            seen.add(d)
    return tuple(sorted(seen))


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


def cleanse(rec: RawRecord, districts: tuple[str, ...] | None = None) -> CleanRecord:
    """Normalize one raw record into a CleanRecord with fixes and flags.

    ``districts`` is the collected district enum (see :func:`collect_districts`).
    When it is supplied, the 地號 cell's district is read from it (D14(b));
    when it is not, the strict 臺北市-anchored reading stays.
    """
    fixes: list[str] = []
    flags: list[str] = []

    district = rec.district.strip()
    if district in DISTRICT_FIXES:
        fixes.append("行政區錯字→松山區")
        district = DISTRICT_FIXES[district]

    iso, ymd = to_iso(rec.date)
    if iso is None:
        flags.append("日期無法解析")

    name_raw = re.sub(r"\s+", "", rec.name)
    # PDF extraction sometimes glues the 地號 cell onto the end of 案名 and
    # leaves the 地號 cell empty (recno 1354 崇仁新村: 案名…案臺北市…地號土地).
    # Recover the trailing land fragment so the record gets a land core and can
    # cluster with its family instead of becoming 未解析-{recno}.
    recovered_land = ""
    if not re.sub(r"\s+", "", rec.land):
        idx = name_raw.rfind("臺北市")
        if idx > 0:
            tail = name_raw[idx:]
            pl_tail = _parse_land(tail)
            if pl_tail["section"] and pl_tail["parcels"]:
                if pl_tail["land_count"] is None:
                    # cross-section lists (711-3、青年段二小段18) keep only the
                    # first-section parcel in `parcels` — count land tokens
                    pl_tail["land_count"] = tail.count("、") + 1
                recovered_land = tail
                fixes.append("地號自案名尾端復原(地號欄黏入案名)")
                name_raw = name_raw[:idx]
    name = normalize_name(name_raw)
    # 事業換計畫 is a scrambled 事業計畫 (recno 621 大業段三小段184-1): the
    # 換/計 transposition otherwise drops the record into track 其他.
    if "事業換計畫" in name:
        fixes.append("案名錯字→事業計畫")
        name = name.replace("事業換計畫", "事業計畫")
    # 土地都市更新計畫案 is a PDF-era abbreviation of 土地都市更新事業計畫案 —
    # the platform's own CASE_NAME always writes 事業 (cross-ref 18/18,
    # operations log §6.14). Recover the dropped 事業 so the track derives
    # 事業計畫 instead of the synthetic 都市更新計畫 fallback.
    if "都市更新計畫" in name and "事業計畫" not in name:
        fixes.append("案名補事業(都市更新計畫案簡寫)")
        name = name.replace("土地都市更新計畫", "土地都市更新事業計畫")

    land_clean = re.sub(r"\s+", "", recovered_land or rec.land)
    land_district = _land_district(land_clean, districts)
    # D14(b): the flag reports the PUBLISHER's contradiction, so it quotes the
    # PRINTED token. The field holds the normalized district. A cell reading
    # 臺北市投區 therefore yields district_land = '' and keeps the flag
    # 行政區與地號行政區不一致(地號為投區) — the contradiction stays visible.
    printed_district = _printed_district(land_clean)
    if printed_district and district and printed_district != district:
        flags.append(f"行政區與地號行政區不一致(地號為{printed_district})")

    pl = pl_tail if recovered_land else _parse_land(rec.land)
    if not pl["section"]:
        flags.append("地號無法解析(缺少段小段)")
    elif not pl["parcels"]:
        flags.append("地號無法解析(缺少地號清單)")

    # 案名 carries the stable case identity even when the 地號 cell is a
    # wrapped continuation missing its 段小段 prefix. Prefer it, fall back to
    # the land cell.
    nd, ns, np, nc = parse_name_id(name)
    section = ns or pl["section"]
    # Name fallback: when the 地號 cell cannot supply a parcel list (missing 地號
    # separator, 及-split list, …), seed the set from the 案名 land fragment.
    # count == 1 names the exact parcel; count > 1 names only the first parcel,
    # so the set stays {first} (partial but non-empty). The source cell is still
    # flagged below.
    if not pl["parcels"] and np:
        parcels = [np]
    else:
        parcels = pl["parcels"]
    first_parcel = np or (parcels[0] if parcels else "")
    land_count = nc if nc is not None else pl["land_count"]
    # repair-contradicted-single-parcel-cell (recno 759, 2026-10-15 gazette):
    # the city printed `… 1 地號1筆土地` under the 案名 …615地號1筆土地… — the
    # publisher typoed the single parcel (verified in the source PDF; the
    # platform API and national portal both print 615 for case 10410272).
    # The 案名 is the identity authority the record already trusts for
    # section/first_parcel/land_count (land-identity-fallback); a single-count
    # 案名 that names its exact parcel fully determines the parcel set, so a
    # one-token cell contradicting it is repaired — never multi-token cells
    # (cross-section lists, merge histories: different shapes). Structural, not
    # keyed to 615: any future PDF with the same typo shape fires the rule.
    if (nc == 1 and np and len(parcels) == 1 and parcels[0] != np):
        flags.append(f"地號欄單筆地號與案名矛盾(地號欄印{parcels[0]}，案名為{np})")
        fixes.append("地號欄單筆地號與案名矛盾→依案名")
        parcels = [np]
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

    # §10 per-track stage derivation: combined-track 案名 may carry two
    # stage ordinals — [stage1]…事業計畫及[stage2]權利變換計畫案 — because
    # 事業計畫 (bonus floor area) and 權利變換 (builder/owner share) progress
    # independently. Additive fields; the single `stage` stays the prefix.
    stage_事業計畫 = stage_權利變換 = None
    if "事業計畫" in name and "權利變換" in name and "事業計畫、權利變換" == track:
        m_head = STAGE_RE.match(name)
        s1 = m_head.group(1) if m_head else ""
        i_qb = name.find("及")
        m2 = None
        if i_qb >= 0:
            m2 = re.match(r"(擬訂|變更(?:\(第[一二三四五六七八九十]+次\))?)", name[i_qb + 1:])
        if m2 and m2.group(1) != s1:
            stage_事業計畫 = s1
            stage_權利變換 = m2.group(1)
        else:
            stage_事業計畫 = stage_權利變換 = s1

    return CleanRecord(
        recno=rec.recno,
        gazette_id=rec.gazette_id,
        date=rec.date,
        iso_date=iso or "",
        ymd=ymd or (0, 0, 0),
        district=district,
        district_land=land_district,
        name=name,
        name_raw=name_raw,
        land=recovered_land or rec.land,
        section=section,
        first_parcel=first_parcel,
        parcels=parcels,
        aliases=pl["aliases"],
        land_count=land_count,
        orig_count=orig,
        named_anchor=anchor,
        area_section=pl["area_section"],
        stage=stage,
        stage_index=stage_index,
        track=track,
        stage_事業計畫=stage_事業計畫,
        stage_權利變換=stage_權利變換,
        implementer=re.sub(r"\s+", "", rec.implementer),
        planner=re.sub(r"\s+", "", rec.planner),
        auto_fixes=fixes,
        review_flags=flags,
        recovery=rec.recovery,
    )


def cleanse_all(records: list[RawRecord],
                districts: tuple[str, ...] | None = None) -> list[CleanRecord]:
    """Cleanse every record, collecting the district enum from the corpus.

    D14(b): the enum is the corpus's own 行政區 column, so the set of known
    districts never becomes a second source of truth in the reader. A caller
    may pass its own enum; otherwise it is collected here.
    """
    # Retained publisher-truncated rows bypass cleansing and merge (tasks 3.2);
    # the recovery pass either resolved them (mark gone) or abandoned them (mark
    # kept — they rejoin the plain exclusion path and are named in the report).
    rows = [r for r in records if not r.source_fault]
    enum = districts if districts is not None else collect_districts(rows)
    return [cleanse(r, enum) for r in rows]