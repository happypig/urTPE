"""I/O adapters: TSV read/write and JSON write."""

from __future__ import annotations

import json

from urtpe.models import CleanRecord, Project, RawRecord


def _cell(value) -> str:
    if value is None:
        return ""
    if isinstance(value, (list, tuple)):
        return "|".join(str(v) for v in value)
    if isinstance(value, dict):
        return ";".join(f"{k}:{','.join(map(str, vs))}" for k, vs in value.items())
    return str(value)


RAW_HEADERS = ["編號", "核定日期", "行政區", "案名", "地號", "實施者", "更新規劃單位", "parse_error"]

CLEAN_HEADERS = [
    "recno", "iso_date", "date", "district", "district_land", "name", "name_raw",
    "land", "section", "first_parcel", "parcels", "aliases", "land_count",
    "orig_count", "named_anchor", "area_section", "stage", "stage_index", "track",
    "implementer", "planner", "auto_fixes", "review_flags",
]

MERGE_HEADERS = CLEAN_HEADERS + ["project_id", "is_current", "anchor_recno"]


def raw_to_tsv(records: list[RawRecord]) -> str:
    lines = ["\t".join(RAW_HEADERS)]
    for r in records:
        lines.append("\t".join([
            str(r.recno), r.date, r.district, r.name, r.land, r.implementer, r.planner, r.parse_error,
        ]))
    return "\n".join(lines) + "\n"


def clean_to_tsv(records: list[CleanRecord]) -> str:
    lines = ["\t".join(CLEAN_HEADERS)]
    for r in records:
        lines.append("\t".join([
            str(r.recno), r.iso_date, r.date, r.district, r.district_land, r.name, r.name_raw,
            r.land, r.section, r.first_parcel, _cell(r.parcels), _cell(r.aliases),
            _cell(r.land_count), _cell(r.orig_count), r.named_anchor, r.area_section,
            r.stage, str(r.stage_index), r.track, r.implementer, r.planner,
            _cell(r.auto_fixes), _cell(r.review_flags),
        ]))
    return "\n".join(lines) + "\n"


def merged_to_tsv(projects: list[Project]) -> str:
    lines = ["\t".join(MERGE_HEADERS)]
    for p in projects:
        for r in p.members:
            lines.append("\t".join([
                str(r.recno), r.iso_date, r.date, r.district, r.district_land, r.name, r.name_raw,
                r.land, r.section, r.first_parcel, _cell(r.parcels), _cell(r.aliases),
                _cell(r.land_count), _cell(r.orig_count), r.named_anchor, r.area_section,
                r.stage, str(r.stage_index), r.track, r.implementer, r.planner,
                _cell(r.auto_fixes), _cell(r.review_flags),
                p.project_id, "true" if r.recno == p.anchor_recno else "false", str(p.anchor_recno),
            ]))
    return "\n".join(lines) + "\n"


def write_json(path: str, obj) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=2)


def write_text(path: str, text: str) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)