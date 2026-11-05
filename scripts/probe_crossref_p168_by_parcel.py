"""Cross-reference the 125 'not found' P_project168 cases by parcel.

Instead of matching on case_id, parse section + first parcel from each case's
T_name and match against gazette projects' anchor section/first_parcel.

Outputs:
  data/p168_crossref_by_parcel.json
  data/p168_crossref_by_parcel_report.txt
"""
from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

P168_ALL = Path("data/p168_all.json")
P168_IN_PROC = Path("data/p168_in_processing.json")
PROJECTS = Path("data/projects.json")
PREV_SUMMARY = Path("data/p168_crossref_summary.json")
OUT_SUMMARY = Path("data/p168_crossref_by_parcel.json")
OUT_REPORT = Path("data/p168_crossref_by_parcel_report.txt")

# Parse "擬訂臺北市<區><段小段><parcels>地號..." or "變更臺北市..."
# District ends with 區; section follows; then one or more parcel numbers separated by
# 頓號, then 地號.  We need the section (everything before the first parcel digit) and
# the first parcel.
T_NAME_RE = re.compile(r"臺北市(?P<district>[^段]*?區)(?P<rest>.*)")


def parse_land_from_name(name: str) -> tuple[str, str] | None:
    """Return (section, first_parcel) from a case name, or None."""
    # Normalise compatibility ideographs
    norm = (
        name.replace("北", "北")
        .replace("都", "都")
        .replace("利", "利")
    )
    m = T_NAME_RE.search(norm)
    if not m:
        return None
    rest = m.group("rest")
    # Strip trailing "地號等N筆..." suffix
    rest = re.sub(r"地號.*", "", rest).strip()
    # Now rest is like "中山段一小段246、269" or "金華段四小段126"
    # Split on transition from section (non-digit) to first parcel (digit)
    m2 = re.match(r"^(.*?)(\d+(?:-\d+)?)", rest)
    if not m2:
        return None
    section = m2.group(1).strip().rstrip("、")
    parcel = m2.group(2)
    return (section, parcel)


def build_gazette_index(path: Path) -> dict[tuple[str, str], list[dict]]:
    """Index gazette projects by (section, first_parcel) from anchor node."""
    with path.open(encoding="utf-8") as f:
        data = json.load(f)

    index: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for proj in data.get("projects", []):
        for node in proj.get("nodes", []):
            section = node.get("section", "")
            first_parcel = node.get("first_parcel", "")
            if section and first_parcel:
                key = (section, first_parcel)
                index[key].append({
                    "project_id": proj.get("project_id"),
                    "anchor_recno": proj.get("anchor_recno"),
                    "recno": node.get("recno"),
                    "date": node.get("date"),
                    "stage": node.get("stage"),
                    "track": node.get("track"),
                    "name": proj.get("name"),
                    "published_date": data.get("published_date"),
                })
    return dict(index)


def main():
    with P168_ALL.open(encoding="utf-8") as f:
        p168_all = json.load(f)

    with PREV_SUMMARY.open(encoding="utf-8") as f:
        prev = json.load(f)

    found_case_ids = {item["case_id"] for item in prev["found_in_gazette"]}
    not_found = [c for c in p168_all if c["case_id"] not in found_case_ids]

    gazette_index = build_gazette_index(PROJECTS)

    matched: list[dict] = []
    still_unmatched: list[dict] = []
    unparseable: list[dict] = []

    for case in not_found:
        cid = case["case_id"]
        name = case["T_name"]
        stage = case.get("stage", "")
        memo = case.get("MEMO", "")

        parsed = parse_land_from_name(name)
        if parsed is None:
            unparseable.append({"case_id": cid, "stage": stage, "memo": memo, "name": name})
            still_unmatched.append(case)
            continue

        section, parcel = parsed
        key = (section, parcel)
        matches = gazette_index.get(key, [])

        if matches:
            matched.append({
                "case_id": cid,
                "stage": stage,
                "memo": memo,
                "name": name,
                "parsed_section": section,
                "parsed_parcel": parcel,
                "matches": matches,
            })
        else:
            still_unmatched.append(case)

    # Build report
    lines: list[str] = []
    lines.append("=" * 100)
    lines.append("CROSS-REFERENCE BY PARCEL: P_project168 'not found' cases vs gazette")
    lines.append("=" * 100)
    lines.append(f"Not found by case_id: {len(not_found)}")
    lines.append(f"Unparseable names: {len(unparseable)}")
    lines.append(f"Matched by parcel: {len(matched)}")
    lines.append(f"Still unmatched: {len(still_unmatched) - len(unparseable)}")
    lines.append(f"Gazette published_date: {json.load(open(PROJECTS, encoding='utf-8')).get('published_date')}")
    lines.append("")

    # Separate in-processing from the not-found set
    with P168_IN_PROC.open(encoding="utf-8") as f:
        in_proc = json.load(f)
    in_proc_ids = {c["case_id"] for c in in_proc}

    matched_in_proc = [m for m in matched if m["case_id"] in in_proc_ids]
    matched_not_in_proc = [m for m in matched if m["case_id"] not in in_proc_ids]
    still_in_proc = [c for c in still_unmatched if c["case_id"] in in_proc_ids and c["case_id"] not in {m["case_id"] for m in matched}]

    lines.append("-" * 100)
    lines.append(f"MATCHED BY PARCEL ({len(matched)} total)")
    lines.append(f"  - In-processing: {len(matched_in_proc)}")
    lines.append(f"  - Already approved (核定階段): {len(matched_not_in_proc)}")
    lines.append("-" * 100)

    for m in matched:
        cid = m["case_id"]
        tag = " [IN-PROCESSING]" if m["case_id"] in in_proc_ids else ""
        lines.append(f"\n{cid}{tag} | {m['stage']} | {m['memo']}")
        lines.append(f"  Parsed: section={m['parsed_section']}, parcel={m['parsed_parcel']}")
        lines.append(f"  Name: {m['name']}")
        for mt in m["matches"]:
            lines.append(
                f"    -> {mt['project_id']} (recno={mt['recno']}, stage={mt['stage']}, "
                f"track={mt['track']}, gazette_date={mt['date']})"
            )

    lines.append("")
    lines.append("-" * 100)
    lines.append(f"STILL UNMATCHED ({len(still_unmatched) - len(unparseable)} cases)")
    lines.append("-" * 100)
    for c in still_unmatched:
        tag = " [IN-PROCESSING]" if c["case_id"] in in_proc_ids else ""
        lines.append(f"  {c['case_id']}{tag} | {c.get('stage','')} | {c.get('MEMO','')} | {c['T_name'][:80]}")

    if unparseable:
        lines.append("")
        lines.append("-" * 100)
        lines.append(f"UNPARSEABLE NAMES ({len(unparseable)})")
        lines.append("-" * 100)
        for u in unparseable:
            lines.append(f"  {u['case_id']} | {u['stage']} | {u['name']}")

    summary = {
        "not_found_by_case_id": len(not_found),
        "unparseable": len(unparseable),
        "matched_by_parcel": len(matched),
        "matched_in_processing": len(matched_in_proc),
        "matched_already_approved": len(matched_not_in_proc),
        "still_unmatched": len(still_unmatched) - len(unparseable),
        "still_unmatched_in_processing": len(still_in_proc),
        "matched": matched,
        "still_unmatched": still_unmatched,
        "unparseable": unparseable,
    }

    OUT_SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    OUT_REPORT.write_text("\n".join(lines), encoding="utf-8")

    print(f"\nWrote {OUT_SUMMARY}")
    print(f"Wrote {OUT_REPORT}")
    print(f"\nMatched by parcel: {len(matched)} (of {len(not_found)} not found by case_id)")
    print(f"  - In-processing matched: {len(matched_in_proc)}")
    print(f"  - Already approved matched: {len(matched_not_in_proc)}")
    print(f"Still unmatched: {len(still_unmatched) - len(unparseable)}")
    print(f"  - Still unmatched in-processing: {len(still_in_proc)}")
    print(f"Unparseable: {len(unparseable)}")


if __name__ == "__main__":
    main()
