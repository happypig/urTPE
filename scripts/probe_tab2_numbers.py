"""Measure case/record and virtual-case facts over the ENTIRE payload.

The post-ingest documentation sync imports measure_payload(); the command-line
printer remains available for archaeology. No network or live file is touched
on import: a probe that reads production state at import time cannot be tested.
"""
import json
import re
import statistics
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLAN, RIGHTS, OUTLINE, OLDPLAN = (re.compile("事業計畫"), re.compile("權利變換"),
                                  re.compile("事業概要"), re.compile("都市更新計畫"))
RFORM = re.compile(r"^R\d{6}-\d{2}$")


def lane(nm):
    # cleanse.py repairs this known source typo before deriving track. Counting
    # the raw name without that repair invents a second lane for one record.
    nm = str(nm or "").replace("事業換計畫", "事業計畫")
    p, r, o = bool(PLAN.search(nm)), bool(RIGHTS.search(nm)), bool(OUTLINE.search(nm))
    if p and r:
        return "事業計畫、權利變換"
    if p:
        return "事業計畫"
    if r:
        return "權利變換"
    if o:
        return "事業概要"
    return OLDPLAN.search(nm).group(0) if OLDPLAN.search(nm) else "(none)"


def measure_payload(d):
    """Return facts over every project, record and virtual case in ``d``."""
    projects = d.get("projects") or []
    nodes = [n for p in projects for n in (p.get("nodes") or [])]
    real = Counter(cid for n in nodes
                   for cid in ((n.get("links") or {}).get("taipei") or []))
    recovered = [{"recno": n.get("recno"),
                  "cases": (n.get("recovery") or {}).get("cases"),
                  "links_taipei": (n.get("links") or {}).get("taipei") or [],
                  "flags": {k: v for k, v in ((n.get("recovery") or {}).get("flags") or {}).items() if v}}
                 for n in nodes if n.get("recovery")]
    vent = [g for p in projects for g in ((p.get("links") or {}).get("orphan_nodes") or [])]
    vids = {g["case_id"] for g in vent}
    lanes = Counter(lane(n.get("name_raw") or "") for n in nodes)
    case_lanes = defaultdict(set)
    for n in nodes:
        for cid in ((n.get("links") or {}).get("taipei") or []):
            case_lanes[cid].add(lane(n.get("name_raw") or ""))
    multi_track = {c: ls for c, ls in case_lanes.items()
                   if len(ls - {"(none)", "都市更新計畫"}) > 1}
    per_unit = [len(p.get("nodes") or []) for p in projects]
    return {
        "published_date": d.get("published_date") or "",
        "records": len(nodes), "projects": len(projects),
        "units_le2": sum(v <= 2 for v in per_unit),
        "units_ge3": sum(v >= 3 for v in per_unit),
        "median_records": statistics.median(per_unit) if per_unit else 0,
        "bindings": sum(real.values()), "distinct_real_cases": len(real),
        "cases_multiple_records": sum(v > 1 for v in real.values()),
        "max_records_per_case": max(real.values(), default=0),
        "records_multiple_cases": sum(
            len((n.get("links") or {}).get("taipei") or []) > 1 for n in nodes),
        "recovered_nodes": len(recovered), "recovered": recovered,
        "recovery_disagreements": sum(
            set(r["cases"] or []) != set(r["links_taipei"]) for r in recovered),
        "virtual_entries": len(vent), "distinct_virtual_cases": len(vids),
        "virtual_duplicates": len(vent) - len(vids),
        "virtual_dated": sum(bool(g.get("node_date")) for g in vent),
        "virtual_undated": sum(not g.get("node_date") for g in vent),
        "cases_virtual_and_real": len(vids & set(real)),
        "total_distinct_cases": len(vids | set(real)),
        "cases_multiple_tracks": len(multi_track),
        "lanes": dict(lanes),
        "virtual_by_track": dict(Counter(g.get("track") for g in vent)),
    }


def main():
    text = (ROOT / "viewer" / "projects.data.js").read_text(encoding="utf-8")
    d = json.loads(text[text.find("{"):text.rfind("}") + 1])
    m = measure_payload(d)
    print(json.dumps(m, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
