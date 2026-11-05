"""Deep cross-reference of the 90 un-gazetted cases against gazette projects.

Matches on section + any parcel in the project's full parcels list (not just
first_parcel), plus a case-name parcel subset check.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

P168_ALL = Path("data/p168_all.json")
PROJECTS = Path("data/projects.json")
BY_PARCEL = Path("data/p168_crossref_by_parcel.json")
OUT = Path("data/p168_unmatched_deep.json")

NAME_RE = re.compile(
    r"臺北市(?P<district>[^段]*?區)(?P<rest>.*)"
)


def parse_case(name: str):
    """Return (district, section, [parcels]) or None."""
    norm = name.replace("北", "北").replace("都", "都").replace("利", "利")
    m = NAME_RE.search(norm)
    if not m:
        return None
    district = (m.group("district") or "").strip()
    rest = m.group("rest")
    # Section = everything before the first digit
    m2 = re.match(r"^(.*?)(\d[\d、\-]*)地號", rest)
    if not m2:
        return None
    section = m2.group(1).strip().rstrip("、")
    parcel_str = m2.group(2)
    parcels = [p.strip() for p in parcel_str.split("、") if p.strip()]
    return district, section, parcels


def main():
    with P168_ALL.open(encoding="utf-8") as f:
        p168_all = json.load(f)

    with BY_PARCEL.open(encoding="utf-8") as f:
        bp = json.load(f)

    already_matched = {m["case_id"] for m in bp["matched"]}
    unmatched = [c for c in p168_all if c["case_id"] not in already_matched]

    with PROJECTS.open(encoding="utf-8") as f:
        data = json.load(f)

    # Index gazette projects by section -> list of projects
    by_section: dict[str, list[dict]] = {}
    for proj in data.get("projects", []):
        for node in proj.get("nodes", []):
            section = node.get("section", "")
            parcels = node.get("parcels", [])
            if section and parcels:
                by_section.setdefault(section, []).append({
                    "project_id": proj.get("project_id"),
                    "anchor_recno": proj.get("anchor_recno"),
                    "recno": node.get("recno"),
                    "date": node.get("date"),
                    "stage": node.get("stage"),
                    "track": node.get("track"),
                    "parcels": parcels,
                    "first_parcel": node.get("first_parcel"),
                    "name": proj.get("name"),
                })

    results: list[dict] = []
    for case in unmatched:
        cid = case["case_id"]
        name = case["T_name"]
        stage = case.get("stage", "")
        memo = case.get("MEMO", "")
        parsed = parse_case(name)
        if parsed is None:
            results.append({
                "case_id": cid, "stage": stage, "memo": memo, "name": name,
                "parsed": None, "matches": [], "verdict": "unparseable",
            })
            continue
        district, section, parcels = parsed

        # Look up gazette projects with matching section
        section_projects = by_section.get(section, [])
        matches: list[dict] = []
        for gp in section_projects:
            # Check if any of the case's parcels appear in the project's parcel list
            common = [p for p in parcels if p in gp["parcels"]]
            if common:
                matches.append({
                    **gp,
                    "common_parcels": common,
                })

        if matches:
            verdict = "found_by_section_parcel"
        else:
            verdict = "genuinely_unmatched"

        results.append({
            "case_id": cid, "stage": stage, "memo": memo, "name": name,
            "parsed": {"district": district, "section": section, "parcels": parcels},
            "matches": matches,
            "verdict": verdict,
        })

    found = [r for r in results if r["verdict"] == "found_by_section_parcel"]
    genuinely = [r for r in results if r["verdict"] == "genuinely_unmatched"]
    unparseable = [r for r in results if r["verdict"] == "unparseable"]

    # Categorize genuinely unmatched by stage
    in_proc_genuinely = [r for r in genuinely if r["stage"] not in ("核定階段", "-")]
    approved_genuinely = [r for r in genuinely if r["stage"] == "核定階段"]
    undated_genuinely = [r for r in genuinely if r["stage"] == "-"]

    summary = {
        "total_unmatched": len(unmatched),
        "found_by_section_parcel": len(found),
        "genuinely_unmatched": len(genuinely),
        "unparseable": len(unparseable),
        "genuinely_in_processing": len(in_proc_genuinely),
        "genuinely_approved": len(approved_genuinely),
        "genuinely_undated": len(undated_genuinely),
        "found": found,
        "genuinely_unmatched": genuinely,
        "unparseable": unparseable,
    }

    OUT.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Total unmatched: {len(unmatched)}")
    print(f"  Found by section+parcel (deeper match): {len(found)}")
    print(f"  Genuinely unmatched: {len(genuinely)}")
    print(f"    - In processing: {len(in_proc_genuinely)}")
    print(f"    - Already approved (核定階段): {len(approved_genuinely)}")
    print(f"    - Undated (-): {len(undated_genuinely)}")
    print(f"  Unparseable: {len(unparseable)}")
    print(f"\nWrote {OUT}")

    print("\n--- Genuinely unmatched, in processing ---")
    for r in in_proc_genuinely:
        print(f"  {r['case_id']} | {r['stage']} | {r['memo']} | {r['name'][:90]}")

    print("\n--- Genuinely unmatched, already approved ---")
    for r in approved_genuinely:
        print(f"  {r['case_id']} | {r['stage']} | {r['memo']} | {r['name'][:90]}")

    print("\n--- Genuinely unmatched, undated ---")
    for r in undated_genuinely:
        print(f"  {r['case_id']} | {r['stage']} | {r['memo']} | {r['name'][:90]}")


if __name__ == "__main__":
    main()
