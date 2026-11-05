"""Cross-reference P_project168 case list with gazette data (projects.json).

Loads:
  data/p168_all.json           -- all 466 cases from the Taipei platform list
  data/p168_in_processing.json -- 54 cases not yet approved
  data/projects.json           -- gazette-emitted project graph

Outputs:
  data/p168_crossref_summary.json
  data/p168_crossref_report.txt
"""
from __future__ import annotations

import json
from pathlib import Path
from collections import defaultdict

P168_ALL = Path("data/p168_all.json")
P168_IN_PROC = Path("data/p168_in_processing.json")
PROJECTS = Path("data/projects.json")
OUT_SUMMARY = Path("data/p168_crossref_summary.json")
OUT_REPORT = Path("data/p168_crossref_report.txt")


def load_project_case_ids(path: Path) -> dict[str, list[dict]]:
    """Return {case_id: [project_info, ...]} from gazette data."""
    with path.open(encoding="utf-8") as f:
        data = json.load(f)

    case_to_projects: dict[str, list[dict]] = defaultdict(list)
    for proj in data.get("projects", []):
        for node in proj.get("nodes", []):
            case_ids = node.get("links", {}).get("taipei", [])
            for cid in case_ids:
                case_to_projects[cid].append({
                    "project_id": proj.get("project_id"),
                    "anchor_recno": proj.get("anchor_recno"),
                    "recno": node.get("recno"),
                    "date": node.get("date"),
                    "stage": node.get("stage"),
                    "track": node.get("track"),
                    "name": proj.get("name"),
                    "published_date": data.get("published_date"),
                })
    return dict(case_to_projects)


def main():
    with P168_ALL.open(encoding="utf-8") as f:
        p168_all = json.load(f)

    with P168_IN_PROC.open(encoding="utf-8") as f:
        p168_in_proc = json.load(f)

    case_to_projects = load_project_case_ids(PROJECTS)

    p168_ids = {c["case_id"] for c in p168_all}
    in_proc_ids = {c["case_id"] for c in p168_in_proc}

    report_lines: list[str] = []
    summary = {
        "p168_total": len(p168_all),
        "in_processing_total": len(p168_in_proc),
        "gazette_projects": len(case_to_projects),
        "found_in_gazette": [],
        "not_found_in_gazette": [],
        "in_processing_found": [],
        "in_processing_not_found": [],
    }

    report_lines.append("=" * 100)
    report_lines.append("CROSS-REFERENCE: P_project168 (Taipei platform) vs gazette (projects.json)")
    report_lines.append("=" * 100)
    report_lines.append(f"P_project168 total cases: {len(p168_all)}")
    report_lines.append(f"In processing (not approved): {len(p168_in_proc)}")
    report_lines.append(f"Gazette projects in projects.json: {len(case_to_projects)}")
    report_lines.append(f"Gazette published_date: {json.load(open(PROJECTS, encoding='utf-8')).get('published_date')}")
    report_lines.append("")

    # --- All 466 cases ---
    report_lines.append("-" * 100)
    report_lines.append("ALL 466 CASES FROM P_project168")
    report_lines.append("-" * 100)
    report_lines.append(f"{'Case ID':<10} {'Stage':<14} {'Memo':<32} {'In gazette?'}  Gazette match(es)")
    report_lines.append("-" * 100)

    for case in p168_all:
        cid = case["case_id"]
        stage = case.get("stage", "")
        memo = case.get("MEMO", "")[:30]
        matches = case_to_projects.get(cid, [])
        found = bool(matches)

        if found:
            summary["found_in_gazette"].append({
                "case_id": cid,
                "stage": stage,
                "memo": memo,
                "matches": matches,
            })
        else:
            summary["not_found_in_gazette"].append({
                "case_id": cid,
                "stage": stage,
                "memo": memo,
            })

        match_str = "; ".join(
            f"{m['project_id']} (recno={m['recno']}, stage={m['stage']}, track={m['track']})"
            for m in matches
        ) if matches else "-"
        report_lines.append(f"{cid:<10} {stage:<14} {memo:<32} {'YES' if found else 'NO '}   {match_str}")

    report_lines.append("")
    report_lines.append(f"Summary: {len(summary['found_in_gazette'])} found in gazette, "
                        f"{len(summary['not_found_in_gazette'])} not found")
    report_lines.append("")

    # --- 54 in-processing cases ---
    report_lines.append("-" * 100)
    report_lines.append("54 IN-PROCESSING CASES (not yet approved on Taipei platform)")
    report_lines.append("-" * 100)
    report_lines.append(f"{'Case ID':<10} {'Stage':<14} {'Memo':<32} {'In gazette?'}  Gazette match(es)")
    report_lines.append("-" * 100)

    for case in p168_in_proc:
        cid = case["case_id"]
        stage = case.get("stage", "")
        memo = case.get("MEMO", "")[:30]
        matches = case_to_projects.get(cid, [])
        found = bool(matches)

        if found:
            summary["in_processing_found"].append({
                "case_id": cid,
                "stage": stage,
                "memo": memo,
                "matches": matches,
            })
        else:
            summary["in_processing_not_found"].append({
                "case_id": cid,
                "stage": stage,
                "memo": memo,
            })

        match_str = "; ".join(
            f"{m['project_id']} (recno={m['recno']}, stage={m['stage']}, track={m['track']})"
            for m in matches
        ) if matches else "-"
        report_lines.append(f"{cid:<10} {stage:<14} {memo:<32} {'YES' if found else 'NO '}   {match_str}")

    report_lines.append("")
    report_lines.append("=" * 100)
    report_lines.append("KEY FINDINGS")
    report_lines.append("=" * 100)
    report_lines.append(f"1. All 466 P_project168 cases: {len(summary['found_in_gazette'])} found in gazette, "
                        f"{len(summary['not_found_in_gazette'])} NOT found")
    report_lines.append(f"2. 54 in-processing cases: {len(summary['in_processing_found'])} found in gazette, "
                        f"{len(summary['in_processing_not_found'])} NOT found")
    report_lines.append("")
    report_lines.append("3. In-processing cases NOT in gazette (these are genuinely new / not yet in gazette):")
    for item in summary["in_processing_not_found"]:
        report_lines.append(f"   {item['case_id']} | {item['stage']} | {item['memo']}")
    report_lines.append("")
    report_lines.append("4. In-processing cases that ARE in gazette (amendment pending; previous version approved):")
    for item in summary["in_processing_found"]:
        match_str = "; ".join(
            f"{m['project_id']} (recno={m['recno']}, gazette_date={m['date']})"
            for m in item["matches"]
        )
        report_lines.append(f"   {item['case_id']} | {item['stage']} | {item['memo']} -> {match_str}")

    OUT_SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    OUT_REPORT.write_text("\n".join(report_lines), encoding="utf-8")

    print(f"\nWrote {OUT_SUMMARY}")
    print(f"Wrote {OUT_REPORT}")
    print(f"\nIn-processing NOT in gazette: {len(summary['in_processing_not_found'])} cases")
    for item in summary["in_processing_not_found"]:
        print(f"  {item['case_id']} | {item['stage']} | {item['memo']}")


if __name__ == "__main__":
    main()
