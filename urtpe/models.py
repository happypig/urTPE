from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class RawRecord:
    """One row as re-joined from the PDF, verbatim (no normalization)."""

    recno: int
    date: str
    district: str
    name: str
    land: str
    implementer: str
    planner: str
    parse_error: str = ""
    gazette_id: str = ""
    # The recovery pass's mark for a retained publisher-truncated row (in-memory
    # only: raw.tsv rides the mark in parse_error, no extra column — the
    # flag-less TSV bytes must not change).
    source_fault: str = ""
    # Provenance from a resolved recovery, threaded to the emitted node verbatim.
    recovery: dict = field(default_factory=dict)


@dataclass
class CleanRecord:
    """A record after normalization and field derivation."""

    recno: int
    date: str
    iso_date: str
    ymd: tuple[int, int, int]
    district: str
    district_land: str
    name: str
    name_raw: str
    land: str
    section: str
    first_parcel: str
    parcels: list[str]
    aliases: dict[str, list[str]]
    land_count: Optional[int]
    orig_count: Optional[int]
    named_anchor: str
    area_section: str
    stage: str
    stage_index: int
    track: str
    implementer: str
    planner: str
    auto_fixes: list[str] = field(default_factory=list)
    review_flags: list[str] = field(default_factory=list)
    gazette_id: str = ""
    links: dict = field(default_factory=dict)
    stage_事業計畫: Optional[str] = None
    stage_權利變換: Optional[str] = None
    # The 地號 cell's own section, when it names one. The gazette's 案名 and
    # 地號 columns can disagree about which 段小段 a unit is in (河堤五小段 vs
    # 河堤段五小段), and the city indexes the 地號 column's form. The
    # `section` field stays the 案名's — it is the merge's grouping key — so
    # this field carries the cell's form for the link comparison
    # (bind-the-unplaced-by-searching-the-cell-section, design D3).
    section_land: str = ""
    # Provenance for a recovered publisher-truncated row (recovery pass); rides
    # into the emitted node. Never serialized into the TSVs (positional writers).
    recovery: dict = field(default_factory=dict)

    def parcel_set(self) -> set[str]:
        s = set(self.parcels)
        for p, als in self.aliases.items():
            s.add(p)
            s.update(als)
        return s


@dataclass
class Project:
    """A merged project family."""

    project_id: str
    anchor_recno: int
    members: list[CleanRecord]
    borderline: list[tuple[int, int, float]] = field(default_factory=list)


def make_record(
    recno: int,
    date: str,
    district: str,
    name: str,
    land: str,
    implementer: str,
    planner: str,
) -> CleanRecord:
    """Build a bare CleanRecord for unit tests, deriving a valid iso date."""

    from urtpe.cleanse import roc_to_iso

    iso, ymd = roc_to_iso(date)
    return CleanRecord(
        recno=recno,
        date=date,
        iso_date=iso or "",
        ymd=ymd or (0, 0, 0),
        district=district,
        district_land=district,
        name=name,
        name_raw=name,
        land=land,
        section="",
        first_parcel="",
        parcels=[],
        aliases={},
        land_count=None,
        orig_count=None,
        named_anchor="",
        area_section="",
        stage="",
        stage_index=-1,
        track="",
        implementer=implementer,
        planner=planner,
    )