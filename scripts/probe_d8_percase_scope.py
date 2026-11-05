"""D8 per-case scope + D13 candidates, offline, read-only."""
import json
from pathlib import Path
APPROVAL = ("核定日期", "核准日期", "核備日期", "審議通過日期")
DEAD = ("自行撤回", "已駁回", "已失效")
root = Path(r"D:\project\urTPE\data\.link_cache")
no_impl, projects, no_hdr_live, proj13 = [], set(), [], set()
for d in sorted(root.iterdir()):
    f = d / "result.json"
    if not f.is_file():
        continue
    try:
        r = json.loads(f.read_text(encoding="utf-8"))
    except Exception:
        continue
    impl = r.get("implementation") or {}
    ms = r.get("case_milestones") or {}
    sch = r.get("case_schedules") or {}
    hdr = r.get("case_headers") or {}
    names = r.get("candidate_names") or {}
    for cid in r.get("city_case_ids") or []:
        m = ms.get(cid) or {}
        if any(m.get(k) for k in APPROVAL) and not impl.get(cid) and sch.get(cid) not in DEAD:
            no_impl.append((d.name, cid)); projects.add(d.name)
        if cid not in hdr and sch.get(cid) not in DEAD and sch.get(cid) != "無":
            sib = [c for c in names if c != cid and names.get(c) and names.get(c) == names.get(cid)]
            no_hdr_live.append((d.name, cid, sch.get(cid), sib))
            if sib:
                proj13.add(d.name)
print("cases with approval date, live, no implementation entry:", len(no_impl), "in", len(projects), "projects")
print("live cases with no cached header:", len(no_hdr_live))
print("  of which have a same-name sibling (D13 shape):", sum(1 for x in no_hdr_live if x[3]), "in", len(proj13), "projects")
for x in no_hdr_live:
    if x[3]:
        print("   ", x)
