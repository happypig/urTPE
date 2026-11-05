import json

with open("data/p168_milestones_summary.json", encoding="utf-8") as f:
    summary = json.load(f)

fields_of_interest = [
    "Uro_Chk_Date", "Uro_Chk_Date2", "核定日期",
    "Plan_Open_Date", "Plan_App_Date", "申請計畫日期",
    "Plan_Hearing_Date", "計畫公聽會日期",
    "Plan_Exhibition_Date", "公告公展日期",
    "Plan_Review_Date", "審議會審議通過日期",
]

rows = []
for cid, info in summary.items():
    kd = info.get("key_dates", {})
    found = {f: kd.get(f, "") for f in fields_of_interest if kd.get(f)}
    rows.append((cid, info["stage"], info["progress"], info["memo"], found, info["name"]))

# Sort: cases with 核定日期 first, then by stage, then case_id
def has_approval(r):
    return bool(r[4].get("核定日期") or r[4].get("Uro_Chk_Date") or r[4].get("Uro_Chk_Date2"))

rows.sort(key=lambda r: (not has_approval(r), r[1], r[0]))

print(f"{'Case ID':<10} {'Stage':<14} {'Memo':<30} {'Key dates'}")
print("-" * 100)
for cid, stage, progress, memo, found, name in rows:
    date_str = " | ".join(f"{k}={v}" for k, v in found.items()) if found else "(no dated milestones)"
    print(f"{cid:<10} {stage:<14} {memo:<30} {date_str}")

print()
print(f"Total: {len(rows)} cases")
print(f"With 核定日期/Uro_Chk_Date: {sum(1 for r in rows if has_approval(r))}")
print(f"Without any approval date: {sum(1 for r in rows if not has_approval(r))}")
