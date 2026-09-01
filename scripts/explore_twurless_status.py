import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, ".")
sys.stdout.reconfigure(encoding="utf-8")
from urtpe.links import TAIPEI_TOP_API, _post_taipei_api

CACHE = Path("data/.link_cache")
js = Path("viewer/projects.data.js").read_text(encoding="utf-8")
projects = json.loads(js.strip()[len("window.PROJECTS ="):].rstrip().rstrip(";"))["projects"]

twur_less = []
for p in projects:
    rf = CACHE / re.sub(r"[^\w\-]", "_", p["project_id"]) / "result.json"
    d = json.loads(rf.read_text(encoding="utf-8"))
    if not d.get("twur_url"):
        twur_less.append((p, d))

print(f"twur-less: {len(twur_less)}")


def outcome(name: str) -> str:
    if "駁回" in name:
        return "駁回"
    if "撤回" in name:
        return "撤回"
    if "失效" in name:
        return "失效"
    if "核定" in name:
        return "已核定"
    if "審查" in name or "審議" in name:
        return "審查中"
    if "施工" in name or "備查" in name:
        return "施工/完工"
    return "other"


proj_class = {}
case_outcomes = {}
for i, (p, d) in enumerate(twur_less, 1):
    pid = p["project_id"]
    cids = d.get("city_case_ids") or []
    if not cids:
        proj_class[pid] = "no-cases"
        continue
    outs = {}
    for cid in cids:
        try:
            top = json.loads(_post_taipei_api(TAIPEI_TOP_API, {"case_id": cid}))
            row = top[0] if isinstance(top, list) and top else (top if isinstance(top, dict) else {})
            name = str(row.get("NAME", ""))
            phase = str(row.get("phase", ""))
            o = outcome(name)
            outs[cid] = (phase, o, name[:40])
        except Exception as e:
            outs[cid] = ("?", "?", f"ERR {e}")
        time.sleep(0.8)
    case_outcomes[pid] = outs
    ovals = {o for (_, o, _) in outs.values()}
    if "已核定" in ovals:
        proj_class[pid] = "has-approved"
    elif ovals and ovals <= {"駁回", "撤回", "失效"}:
        proj_class[pid] = "never-approved"
    else:
        proj_class[pid] = "mixed/other"
    if i % 15 == 0:
        print(f"  …{i}/{len(twur_less)} probed")

from collections import Counter

dist = Counter(proj_class.values())
print("\n=== classification of", len(twur_less), "twur-less ===")
for k, v in dist.most_common():
    print(f"  {k}: {v}")

print("\n=== never-approved samples ===")
n = 0
for pid, cls in proj_class.items():
    if cls == "never-approved" and n < 8:
        n += 1
        for cid, (ph, o, nm) in case_outcomes[pid].items():
            print(f"  {pid[:34]} | {cid} ph={ph} [{o}] {nm}")
        print()

print("=== has-approved samples (why no twur then?) ===")
n = 0
for pid, cls in proj_class.items():
    if cls == "has-approved" and n < 5:
        n += 1
        for cid, (ph, o, nm) in case_outcomes[pid].items():
            print(f"  {pid[:34]} | {cid} ph={ph} [{o}] {nm}")
        print()

Path("data/_twurless_classification.json").write_text(json.dumps({
    "class": proj_class,
    "cases": case_outcomes,
}, ensure_ascii=False, indent=2), encoding="utf-8")
print("saved -> data/_twurless_classification.json")
