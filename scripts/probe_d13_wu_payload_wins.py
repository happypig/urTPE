"""D13 step-2 constraint scope: projects where a 無 case wins the payload today. Read-only, offline."""
import json, sys
from pathlib import Path
sys.path.insert(0, r"D:\project\urTPE")
from urtpe.links import select_best_payload, pick_implementation_payload, _PLAN_CASE_RE
root = Path(r"D:\project\urTPE\data\.link_cache")
stats_win, plan_in, rew_win = [], [], []
for d in sorted(root.iterdir()):
    f = d / "result.json"
    if not f.is_file():
        continue
    try:
        r = json.loads(f.read_text(encoding="utf-8"))
    except Exception:
        continue
    sch = r.get("case_schedules") or {}
    hdr = r.get("case_headers") or {}
    def wu(c):
        h = hdr.get(c)
        name = h if isinstance(h, str) else (h or {}).get("NAME", "")
        return sch.get(c) == "無" or str(name).strip() == "無"
    impl = r.get("implementation") or {}
    names = r.get("candidate_names") or {}
    cid, _, _ = select_best_payload(impl)
    if cid and wu(cid):
        stats_win.append((d.name, cid, {k: len(v or {}) for k, v in impl.items()}))
    _, src, _, _ = pick_implementation_payload(impl, names)
    if any(wu(c) for c in set(src.values())):
        plan_in.append((d.name, sorted({c for c in src.values() if wu(c)})))
    rcid, _, _ = select_best_payload(r.get("rewards") or {})
    if rcid and wu(rcid):
        rew_win.append((d.name, rcid))
print("implementation statistics won by a 無 case:", len(stats_win))
for x in stats_win: print("  ", x)
print("implementation dates sourced from a 無 case:", len(plan_in))
for x in plan_in: print("  ", x)
print("rewards won by a 無 case:", len(rew_win))
for x in rew_win: print("  ", x)
