"""D9g step 2: is every changed project explained by the step's change?

The hard stop says a re-emit that changes more projects than the step can
explain must report the diff first. This probe attributes every changed
project to one of the step's three causes, and names the projects that no
cause explains.

The causes:
  D7  — the project's merged milestone projection (links.milestones_taipei)
        changed: the re-derivation replaced a stale dict.
  D8  — the project's implementation or rewards payload changed: the
        per-case fetch filled a missing entry, or the 無 exclusion changed
        the pick.
  D13 — a case of the project was labelled 無, or the project's payload
        pick moved off a 無 case.
  D15 — a node's review_flags changed order (the stable sort).
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def main():
    before = load(ROOT / "data" / "_projects_before_step2.json")
    after = load(ROOT / "data" / "projects.json")
    b_by = {p["project_id"]: p for p in before["projects"]}
    a_by = {p["project_id"]: p for p in after["projects"]}

    explained = {"D7": [], "D8": [], "D10": [], "D13": [], "D15": [], "D15b": [], "REFRESH_STATUS": []}
    unexplained = []
    for pid, b in b_by.items():
        a = a_by.get(pid)
        if a is None or b == a:
            continue
        reasons = []
        bl = (b.get("links") or {})
        al = (a.get("links") or {})
        if bl.get("milestones_taipei") != al.get("milestones_taipei"):
            reasons.append("D7")
        if bl.get("milestones_source") != al.get("milestones_source"):
            reasons.append("D7")
        # the orphan nodes read their dates from the merged dict, so the D7
        # re-derivation moves them too
        bo = {o.get("case_id"): o for o in (bl.get("orphan_nodes") or [])}
        ao = {o.get("case_id"): o for o in (al.get("orphan_nodes") or [])}
        for cid in set(bo) & set(ao):
            if bo[cid].get("milestones_taipei") != ao[cid].get("milestones_taipei"):
                reasons.append("D7")
                break
        if b.get("implementation") != a.get("implementation"):
            reasons.append("D8")
        if b.get("rewards") != a.get("rewards"):
            reasons.append("D8")
        # D10: the permit witness moved to the permit the city's 開工 names
        if bl.get("permit") != al.get("permit"):
            reasons.append("D10")
        # D13: a case of the project is now labelled 無
        bs = (bl.get("case_schedules") or {})
        as_ = (al.get("case_schedules") or {})
        wu = [c for c, s in as_.items() if s == "無" and bs.get(c) != "無"]
        if wu:
            reasons.append("D13")
        # the refresh re-derives each case's status from the city's header
        if bs != as_:
            reasons.append("REFRESH_STATUS")
        # D15: a node's review_flags changed but only in order
        order_only = False
        # D15b: a flag's quoted date was normalised, so the text changed
        date_normalised = False
        bn = {n["recno"]: n for n in b.get("nodes", [])}
        an = {n["recno"]: n for n in a.get("nodes", [])}
        for recno in set(bn) & set(an):
            xf, yf = bn[recno].get("review_flags") or [], an[recno].get("review_flags") or []
            if xf == yf:
                continue
            if sorted(xf) == sorted(yf):
                order_only = True
                continue
            # the same finding, one spelling of the date
            def norm(flags):
                return sorted(re.sub(r"日期:[0-9/.-]+", "日期:*", f) for f in flags)
            if norm(xf) == norm(yf):
                date_normalised = True
        if order_only:
            reasons.append("D15")
        if date_normalised:
            reasons.append("D15b")
        if not reasons:
            unexplained.append(pid)
        else:
            for r in set(reasons):
                explained[r].append(pid)

    print("projects changed:", sum(len(v) for v in explained.values()) + len(unexplained))
    for k, v in explained.items():
        print("   %-4s %d" % (k, len(v)))
    print()
    print("projects with NO explained cause:", len(unexplained))
    for pid in unexplained:
        print("   ", pid)
    return unexplained


if __name__ == "__main__":
    main()
