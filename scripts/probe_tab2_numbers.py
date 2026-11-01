import json, re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(r"D:\project\urTPE")
t = (ROOT / "viewer" / "projects.data.js").read_text(encoding="utf-8")
d = json.loads(t[t.find("{"):t.rfind("}") + 1])

PLAN, RIGHTS, OUTLINE, OLDPLAN = (re.compile("事業計畫"), re.compile("權利變換"),
                                  re.compile("事業概要"), re.compile("都市更新計畫"))
RFORM = re.compile(r"^R\d{6}-\d{2}$")

def lane(nm):
    p, r, o = bool(PLAN.search(nm)), bool(RIGHTS.search(nm)), bool(OUTLINE.search(nm))
    if p and r: return "事業計畫、權利變換"
    if p: return "事業計畫"
    if r: return "權利變換"
    if o: return "事業概要"
    return OLDPLAN.search(nm).group(0) if OLDPLAN.search(nm) else "(none)"

print("published_date : %s" % d.get("published_date"))
recs = sum(len(p["nodes"]) for p in d["projects"])
print("records / units: %d / %d" % (recs, len(d["projects"])))

per_unit = sorted(len(p["nodes"]) for p in d["projects"])
print("units >=3 records: %d (%.0f%%)   <=2: %d (%.0f%%)" % (
    sum(1 for v in per_unit if v >= 3), 100 * sum(1 for v in per_unit if v >= 3) / len(per_unit),
    sum(1 for v in per_unit if v <= 2), 100 * sum(1 for v in per_unit if v <= 2) / len(per_unit)))

# cases & bindings
bindings, real = 0, Counter()
multi_case_rows = 0
rec_lanes = Counter()
no_lane = []
rform_cases, num_cases = set(), set()
recovered = []
for p in d["projects"]:
    for n in p["nodes"]:
        rec_lanes[lane(n.get("name_raw") or "")] += 1
        if rec_lanes and lane(n.get("name_raw") or "") not in (
                "事業計畫、權利變換", "事業計畫", "權利變換", "事業概要") and len(no_lane) < 12:
            no_lane.append(n.get("name_raw"))
        cs = ((n.get("links") or {}).get("taipei") or [])
        if len(cs) > 1: multi_case_rows += 1
        for cid in cs:
            bindings += 1
            real[cid] += 1
            (rform_cases if RFORM.match(cid) else num_cases).add(cid)
        rc = n.get("recovery")
        if rc:
            recovered.append({
                "recno": n.get("recno"),
                "cases": rc.get("cases"), "api_cases": rc.get("api_cases"),
                "links_taipei": cs,
                "flags": {k: v for k, v in (rc.get("flags") or {}).items() if v},
            })

multi1 = sum(1 for v in real.values() if v > 1)
print("\n--- cases & bindings ---")
print("bindings: %d  distinct on >=1 record: %d  covering >1 record: %d (max %d)" % (
    bindings, len(real), multi1, max(real.values())))
print("records naming >1 case (links.taipei): %d" % multi_case_rows)
print("case ids by space: R-form %d, numeric %d" % (len(rform_cases), len(num_cases)))

# recovered rows + the 1005 conflict
print("\n--- recovered rows (%d) ---" % len(recovered))
conflicts = 0
for r in recovered:
    mismatch = set(r["cases"] or []) != set(r["links_taipei"] or [])
    if mismatch: conflicts += 1
    print("  recno=%-5s cases=%-24s links=%-16s flags=%s%s" % (
        r["recno"], ",".join(r["cases"] or []), ",".join(r["links_taipei"] or []),
        sorted(r["flags"]), "   <-- DISAGREE" if mismatch else ""))
print("recovered rows where recovery.cases != links.taipei: %d" % conflicts)

# virtual cases
vent = [g for p in d["projects"] for g in ((p.get("links") or {}).get("orphan_nodes") or [])]
vids = {g["case_id"] for g in vent}
vd = Counter(bool(g.get("node_date")) for g in vent)
both = vids & set(real)
print("\n--- virtual cases ---")
print("entries: %d  distinct: %d  listed>once: %d" % (len(vent), len(vids), len(vent) - len(vids)))
print("dated / undated: %d / %d" % (vd[True], vd[False]))
print("cases BOTH virtual and real: %d   total distinct cases: %d" % (len(both), len(vids | set(real))))
vt = Counter(g.get("track") for g in vent)
print("virtual by track: %s" % dict(vt.most_common()))

# lanes
print("\n--- lanes (records parsed by name + virtual by track) ---")
tot = Counter(rec_lanes)
for k, v in vt.items(): tot[k] += v
for k, v in tot.most_common(): print("   %-22s records=%-5d total=%d" % (k, rec_lanes.get(k, 0), v))
print("   TOTAL nodes: %d" % sum(tot.values()))

# multi-track cases: one case_id cited by records whose lanes differ
case_lanes = defaultdict(set)
for p in d["projects"]:
    for n in p["nodes"]:
        L = lane(n.get("name_raw") or "")
        for cid in ((n.get("links") or {}).get("taipei") or []):
            case_lanes[cid].add(L)
mt = {c: ls for c, ls in case_lanes.items() if len(ls - {"(none)", "都市更新計畫"}) > 1}
print("\ncases spanning >1 track: %d" % len(mt))

# undated virtual with no track filter = gutter question
print("\nno-lane record names (sample):")
for nm in no_lane[:6]: print("   %s" % (nm or "(empty)")[:70])
