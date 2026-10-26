# -*- coding: utf-8 -*-
"""Pure recovery logic for publisher-truncated gazette rows (recover-truncated-rows-via-api).

No I/O lives here — the HTTP surfaces are adapters in :mod:`urtpe.recovery_sources`
and the orchestration is :mod:`urtpe.recovery_pass`. Everything in this module is
calibrated against the measured POC (``openspec/changes/
recover-truncated-rows-via-api/poc_findings.md``, tasks 1.2–1.7):

* identity comes from the row's own 案名 (D-B/D-C), verified by the four checks —
  15/15 rows of the 2026-10-15 gazette closed with an exact date;
* list completion is the calibrated positional rule (T8): the printed list is
  complete-sorted up to the cut, so a true member outside the fragment sorts after
  the fragment's last visible parcel, carries ≥1 ring vertex inside the boundary
  (the adapter's geometry), and the count must close — never a subset forced to
  the declared count (美仁段: 75 ≠ 74 → refuse);
* a GIS-verified fragment typo is repaired with a flag, never silently (D-F).
"""

from __future__ import annotations

import difflib
import re
from dataclasses import dataclass, field

from urtpe.extract import PARCEL_TOKEN_RE, SECTION_PREFIX_RE

# The similarity fallback band reuses the link thresholds (config's provisional
# starting points). The POC measured 0 rows in the band — containment held raw
# for all 15 — so acceptance must not depend on it (poc_findings.md T2).
LINK_THRESHOLD = 0.7
FLAG_THRESHOLD = 0.5


# --- normalization (T2 table) ------------------------------------------------

def normalize_name(text: str) -> str:
    """Presentation-level normalization applied to both sides before comparing.

    The table is defensive: on the measured gazette the raw containment already
    held for every accepted pair. Corpus-known city-side drift per
    openspec/config.yaml: 計劃→計畫, ㄧ→一, full-width parens, spacing.
    """
    text = re.sub(r"\s+", "", text or "")
    text = text.replace("（", "(").replace("）", ")")
    return text.replace("計劃", "計畫").replace("ㄧ", "一")


_NAME_RE = re.compile(r"臺北市(\w+區)(\S+?段(?:[一二三四五]小段)?)(\d+)(?:-(\d+))?地號")
_CORE_RE = re.compile(r"臺北市\w+區.*?地號等\d+筆(?:\(原\d+筆\))?")
_COUNT_FRAG_RE = re.compile(r"等\d+筆(?:\(原\d+筆\))?")


@dataclass(frozen=True)
class RowIdentity:
    """The identity key derived from the row's own surviving 案名 (D-C)."""

    district: str
    section: str
    mono: str          # 4-digit zero-padded 母號, as Get_updcase_list wants
    suno: str          # 4-digit zero-padded 子號, "0000" when none
    count_fragment: str  # e.g. 等74筆(原54筆) — normalized
    address_core: str    # 臺北市<區><段><parcel>地號等N筆[(原M筆)] — normalized
    name: str            # the full normalized 案名, for the similarity fallback

    @property
    def declared_count(self) -> int | None:
        m = re.search(r"等(\d+)筆", self.count_fragment)
        return int(m.group(1)) if m else None


def parse_identity(name: str) -> RowIdentity | None:
    """Parse the identity from a surviving 案名; None when it carries no land core."""
    norm = normalize_name(name)
    m = _NAME_RE.search(norm)
    if not m:
        return None
    core_m = _CORE_RE.search(norm)
    frag_m = _COUNT_FRAG_RE.search(norm)
    return RowIdentity(
        district=m.group(1),
        section=m.group(2),
        mono=m.group(3).zfill(4),
        suno=(m.group(4) or "0").zfill(4),
        count_fragment=frag_m.group(0) if frag_m else "",
        address_core=core_m.group(0) if core_m else "",
        name=norm,
    )


def name_similarity(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, a, b).ratio()


# --- check 4: the date closes in either stage field ---------------------------

_ISO_RE = re.compile(r"(\d{4})-(\d{1,2})-(\d{1,2})")


def _iso(s: str) -> str:
    m = _ISO_RE.match((s or "")[:10])
    return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}" if m else ""


def date_check(d1: str, d2: str, want: str) -> tuple[str, str]:
    """Resolve the gazette date against ``uro_chk_date`` and ``uro_chk_date2``.

    權變 stages carry their date in field 2 alone (measured: 851, 863, 902, 912,
    930, 997), so both fields are checked and the provenance records which one
    closed. Returns (``exact`` | ``pm1`` | ``none``, field name or "").
    """
    for field_name, value in (("uro_chk_date", d1), ("uro_chk_date2", d2)):
        if _iso(value) == want:
            return "exact", field_name
    from datetime import date as _date

    for field_name, value in (("uro_chk_date", d1), ("uro_chk_date2", d2)):
        iso = _iso(value)
        if not iso:
            continue
        try:
            delta = abs((_date.fromisoformat(iso) - _date.fromisoformat(want)).days)
        except ValueError:
            continue
        if delta == 1:
            return "pm1", field_name
    return "none", ""


# --- the four checks and the acceptance selection -----------------------------

@dataclass
class RowMatch:
    """Outcome of the four-check identity match for one truncated row."""

    status: str                      # "matched" | "residual"
    cases: list[dict] = field(default_factory=list)   # accepted candidates
    flags: list[str] = field(default_factory=list)
    date_field: str = ""


def match_row(identity: RowIdentity, gazette_iso: str, candidates: list[dict],
              *, link_threshold: float = LINK_THRESHOLD) -> RowMatch:
    """Accept a candidate only when all four checks hold, independently:

    1. same unit (district + 段/小段), 2. the surviving name is contained (or the
    similarity fallback band is reached *with* the count fragment matching),
    3. the declared count appears, 4. the date closes in either field — exact
    preferred; a ±1-day match only when no exact candidate exists, and flagged.
    (``FLAG_THRESHOLD`` marks the review band; the POC measured no row in it.)
    """
    accepted: list[dict] = []
    pm1: list[dict] = []
    band = False
    for cand in candidates:
        name = normalize_name(cand.get("case_name") or "")
        # check 1 — same unit
        if not (identity.district in name and identity.section in name):
            continue
        # check 3 — the declared count appears
        if not (identity.count_fragment and identity.count_fragment in name):
            continue
        # check 2 — containment, or the similarity fallback band
        contained = bool(identity.address_core) and identity.address_core in name
        if not contained:
            if name_similarity(identity.name, name) < link_threshold:
                continue
        # check 4 — the date closes in either field
        result, date_field = date_check(cand.get("uro_chk_date") or "",
                                        cand.get("uro_chk_date2") or "",
                                        gazette_iso)
        if result == "exact":
            if not contained:
                band = True  # accepted on similarity, not containment; flagged
            accepted.append({**cand, "date_result": "exact",
                             "date_field": date_field})
        elif result == "pm1":
            pm1.append({**cand, "date_result": "pm1", "date_field": date_field})

    if accepted:
        chosen, flag = accepted, []
    elif pm1:
        # a ±1-day match is accepted only when no exact candidate exists (D4)
        chosen, flag = pm1, ["date-pm1"]
    else:
        return RowMatch(status="residual")

    if len(chosen) > 1:
        # several same-unit same-date cases attach together (D-E): the 930 zone
        # pair, both exact on 2017-12-12
        flag.append("ambiguous-zone")
    if band:
        flag.append("similarity-band")
    return RowMatch(status="matched", cases=chosen, flags=flag,
                    date_field=chosen[0]["date_field"] if chosen else "")


# --- zone markers vs named anchors (D-G / T11) --------------------------------

_ZONE_MARKER_RE = re.compile(
    r"-[AB]區"                              # the 案名's -A區/-B區 suffix
    r"|[（(][甲乙]區段[）)]"                 # (甲區段) / (乙區段)
    r"|[（(](?!原)[^（）()]{1,12}基地[）)]"   # (X基地); (原XX基地) is a named anchor
)


def is_zone_marker(text: str) -> bool:
    """Whether a case name carries a zone marker rather than a named anchor.

    The A/B census measured ~55 true zone-marked cases against ~37 ``(原XX基地)``
    hits that the domain treats as anchors, never zones (poc_findings.md, design
    D-G) — so ``(原東星大樓基地)`` must never split or flag a land core.
    """
    return bool(_ZONE_MARKER_RE.search(normalize_name(text)))


# --- the calibrated positional list completion (T8) ---------------------------

def gazette_order_key(token: str) -> tuple[int, int]:
    """Gazette parcel order: 母號 then 子號, numerically (93-16 < 93-17)."""
    a, _, b = token.partition("-")
    return (int(a), int(b) if b else -1)


def fragment_parcels(land: str) -> list[str]:
    """The parcels visible in a 地號 cell, in printed order, section prefix gone.

    Spaces inside a token are joined (`573 -6` stays one token) and duplicates
    dropped, mirroring the published counter in :mod:`urtpe.extract`.
    """
    body = SECTION_PREFIX_RE.sub("", (land or "").strip())
    seen: set[str] = set()
    out: list[str] = []
    for t in PARCEL_TOKEN_RE.findall(body):
        t = t.replace(" ", "").replace("\u3000", "")
        if t and t not in seen:
            seen.add(t)
            out.append(t)
    return out


def repair_fragment(land: str, cadastre: set[str],
                    unit_candidates: set[str] | None = None,
                    ) -> tuple[str, list[tuple[str, str]]]:
    """Repair a GIS-verified cell typo (D-F), never silently and never by guess.

    The published cell is printed in ascending gazette order, so a token that
    sorts BEFORE its printed predecessor is contradicted by the cell itself.
    Measured: the city prints ``…717-2、718、78-1、719…`` where the cadastre holds
    ``718-1`` — and the section cadastre alone cannot decide (708-1 and 738-1
    are equally one deletion away and equally boundary candidates), so the repair
    must also FIT the token's printed slot (between its printed neighbours).
    When the unit's boundary candidates are supplied they narrow the match
    further. Anything not uniquely determined — two candidates, or none — stays
    as published.
    """
    repairs: list[tuple[str, str]] = []
    tokens = fragment_parcels(land)
    for i, token in enumerate(tokens):
        if token in cadastre:
            continue
        prev_key = gazette_order_key(tokens[i - 1]) if i else None
        next_key = gazette_order_key(tokens[i + 1]) if i + 1 < len(tokens) else None
        # contradiction 1: the cell's own printed order
        if prev_key is None or gazette_order_key(token) >= prev_key:
            continue
        mono, hyphen, suno = token.partition("-")
        matches = set()
        for cand in cadastre:
            c_mono, c_hyphen, c_suno = cand.partition("-")
            if hyphen != c_hyphen or len(c_mono) != len(mono) + 1:
                continue
            if hyphen and c_suno != suno:
                continue
            if any(c_mono[:i2] + c_mono[i2 + 1:] == mono for i2 in range(len(c_mono))):
                matches.add(cand)
        if unit_candidates is not None:
            matches &= unit_candidates
        # contradiction 2 resolved: the repair must fit the token's printed slot
        if prev_key is not None and next_key is not None:
            matches = {m for m in matches
                       if prev_key < gazette_order_key(m) < next_key}
        if len(matches) == 1:
            repairs.append((token, matches.pop()))
    repaired = land
    for old, new in repairs:
        repaired = repaired.replace(old, new, 1)
    return repaired, repairs


@dataclass(frozen=True)
class ListCompletion:
    """Outcome of the two-tier list completion (D-D)."""

    ok: bool
    parcels: tuple[str, ...]
    reason: str  # closed | fragment-not-contained | count-mismatch | no-parcels


def complete_unit_list(land: str, candidates: set[str],
                       declared: int) -> ListCompletion:
    """Reconstruct the unit's parcel list from the fragment plus the GIS tail.

    The calibrated rule (T8): a candidate outside the fragment is a member only
    when it sorts after the fragment's last visible parcel — the printed list is
    complete-sorted up to the cut, so a true member outside the fragment must
    sort after it — and carries ≥1 ring vertex inside the boundary (the adapter
    only supplies such parcels). The reconstruction is accepted only when the
    count closes to the declared count; a subset is never picked to force it
    (美仁段: 72 + 3 tail candidates = 75 ≠ 74 → refuse).
    """
    frag = fragment_parcels(land)
    if not frag:
        return ListCompletion(False, (), "no-parcels")
    frag_set = set(frag)
    if not frag_set <= candidates:
        # the T10 guard: R089305's two polygons are not the unit's boundary, and
        # this precondition is what refuses them
        return ListCompletion(False, tuple(frag), "fragment-not-contained")
    last = max(frag_set, key=gazette_order_key)
    tail = sorted((c for c in candidates if c not in frag_set
                   and gazette_order_key(c) > gazette_order_key(last)),
                  key=gazette_order_key)
    reconstructed = sorted(frag_set, key=gazette_order_key) + tail
    if len(reconstructed) == declared:
        return ListCompletion(True, tuple(reconstructed), "closed")
    return ListCompletion(False, tuple(reconstructed), "count-mismatch")


def rebuild_land_cell(land: str, parcels: list[str] | tuple[str, ...],
                      declared: int) -> str:
    """Render a reconstructed list as a 地號 cell, mirroring the published shape.

    The closing phrase is the canonical rendering of a provably whole list
    (``…地號等N筆土地``), the shape the corpus-completion path already emits.
    """
    m = SECTION_PREFIX_RE.match((land or "").strip())
    prefix = m.group(0) if m else ""
    return prefix + "、".join(parcels) + f"地號等{declared}筆土地"
