"""Compare 使照核發日期 vs 執照日期 for the two named cases.

松山區-寶清段一小段-57-13地號等1筆  case 10212211
大安區-金華段一小段-719地號等1筆    case 10308211

Reads the emitted payload, the per-project cache, and the raw third.ashx
payload, and prints every field that carries a permit-ish date.
"""
from __future__ import annotations

import json
from pathlib import Path

TARGETS = {
    "10212211": "松山區-寶清段一小段-57-13地號等1筆",
    "10308211": "大安區-金華段一小段-719地號等1筆",
}

PAYLOAD_DATE_KEYS = [
    "Blic_Date", "Ulic_Date", "Eng_Start_Date", "Report_Date",
    "Uro_Chk_Date", "Uro_Chk_Date2", "Plan_App_Date", "Plan_App_Date2",
    "jud_ok_date", "jud_ok_date2", "App_Chk_Date", "App_Chk_Date2",
    "Show_Bull_Date", "Show_Bull_Date2", "Show_Open_Date", "Show_Open_Date2",
    "Stew_App_Date", "Stew_Hold_Date", "Review_app_date", "Review_hold_date",
    "App_Hear_Date", "Hold_Hear_Date", "comm_hold_date", "comm_hold_date2",
    "comm_hold_date0", "jud_ok_date0", "outline_ok_date", "outline_app_date",
]


def main():
    with open("data/projects.json", encoding="utf-8") as f:
        data = json.load(f)

    print("=" * 90)
    print("1. EMITTED PAYLOAD — every node of the two projects, and its links")
    print("=" * 90)
    for proj in data.get("projects", []):
        if proj.get("project_id") not in TARGETS.values():
            continue
        print(f"\n### {proj['project_id']}  (anchor_recno={proj.get('anchor_recno')})")
        print(f"    project-level links.taipei = {proj.get('links', {}).get('taipei')}")
        mt = proj.get("links", {}).get("milestones_taipei", {})
        print(f"    project-level milestones_taipei:")
        for k, v in mt.items():
            print(f"        {k} = {v}")
        impl = proj.get("implementation", {})
        if impl:
            print(f"    project-level implementation:")
            for k, v in impl.items():
                if v and any(t in k.lower() for t in ("date", "lic", "eng", "report")):
                    print(f"        {k} = {v}")
        for node in proj.get("nodes", []):
            print(f"  -- node recno={node.get('recno')} date={node.get('date')} "
                  f"stage={node.get('stage')} track={node.get('track')}")
            print(f"     links.taipei = {node.get('links', {}).get('taipei')}")
            nmt = node.get("links", {}).get("milestones_taipei", {})
            for k, v in nmt.items():
                if "照" in k or "開工" in k or "成果" in k:
                    print(f"     {k} = {v}")
            nimpl = node.get("implementation", {})
            if nimpl:
                for k, v in nimpl.items():
                    if v and any(t in k.lower() for t in ("date", "lic", "eng", "report")):
                        print(f"     impl.{k} = {v}")

    print()
    print("=" * 90)
    print("2. PER-PROJECT CACHE — case_milestones + implementation payload")
    print("=" * 90)
    cache = Path("data/.link_cache")
    for case_id, project_id in TARGETS.items():
        d = cache / project_id
        rj = d / "result.json"
        print(f"\n### {project_id} / case {case_id}")
        print(f"    cache dir: {d}  result.json: {rj.exists()}")
        if not rj.exists():
            continue
        c = json.loads(rj.read_text(encoding="utf-8"))
        print(f"    status={c.get('status')} city_case_ids={c.get('city_case_ids')}")
        cm = c.get("case_milestones") or {}
        print(f"    case_milestones keys: {sorted(cm.keys())}")
        for cid, ms in cm.items():
            hits = {k: v for k, v in ms.items() if v and ("照" in k or "開工" in k or "成果" in k)}
            print(f"      {cid}: {hits}")
        impl = c.get("implementation") or {}
        print(f"    implementation keys: {sorted(impl.keys())[:20]}...")
        for cid, payload in impl.items():
            hits = {k: v for k, v in payload.items()
                    if v and any(t in k.lower() for t in ("date", "lic", "eng", "report"))}
            print(f"      {cid}: {hits}")
        print(f"    case_schedules = {c.get('case_schedules')}")
        print(f"    case_headers = {c.get('case_headers')}")

    print()
    print("=" * 90)
    print("3. THE LABELS: what the viewer calls 使照核發 vs 執照")
    print("=" * 90)


if __name__ == "__main__":
    main()
