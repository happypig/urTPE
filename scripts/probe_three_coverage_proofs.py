"""Three coverage proofs over the emitted dataset. Read-only.

The three questions, and what proves each:

  1. Are there projects not in the lists?
     A project is IN a list when some case id it carries appears in that list.
     The lists are the city's 168 fast-track register (466 cases, read from
     Get_project168.ashx) and the national portal's project list (the
     twur.nlma.gov.tw view index). A project with no case id at all is in
     NEITHER list by construction.

  2. Are there recno not in any project?
     The merge partition must be total and disjoint over the cleansed records.
     The pipeline proves this at ingest time (Tripwire.check_partition, exit 4).
     This probe re-derives it from the emitted files, because the emitted
     payload is what a reader sees and the gate only covers the ingest path.

  3. Is every recno attached to a 北 badge (case_id)?
     The badge is drawn from a node's `links.taipei`. A node with an empty
     `links.taipei` renders no 北 badge. The unplaced-node flag names the same
     condition, so the flag count and the badge-less node count must agree.

Every number is printed with the check that produced it, so a reader can
re-derive it by hand. Nothing is written.

    python scripts/probe_three_coverage_proofs.py
"""
from __future__ import annotations

import csv
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]

PROJECTS = ROOT / "data" / "projects.json"
CLEAN = ROOT / "data" / "clean.tsv"
MERGED = ROOT / "data" / "merged.tsv"
P168 = ROOT / "data" / "p168_all.json"
PORTAL_INDEX = ROOT / "data" / ".link_cache" / "portal_index.json"


def load_json(path: pathlib.Path):
    return json.loads(path.read_text(encoding="utf-8"))


def tsv_recnos(path: pathlib.Path) -> set[int]:
    with path.open(encoding="utf-8") as fh:
        return {int(r["recno"]) for r in csv.DictReader(fh, delimiter="\t")}


def main() -> int:
    doc = load_json(PROJECTS)
    projects = doc["projects"]

    # --- the universe the payload names ---------------------------------
    project_ids: set[str] = set()
    node_ids: set[str] = set()
    for p in projects:
        links = p.get("links") or {}
        project_ids.update(links.get("taipei") or [])
        for node in p.get("nodes") or ():
            node_ids.update((node.get("links") or {}).get("taipei") or [])
    payload_ids = project_ids | node_ids

    p168_ids = {r["case_id"] for r in load_json(P168)}
    portal = load_json(PORTAL_INDEX) if PORTAL_INDEX.exists() else []
    portal_cores = {e.get("core", "") for e in portal}

    print("=" * 72)
    print("the corpus")
    print("=" * 72)
    print("  projects:              %d" % len(projects))
    print("  records:               %d" % doc["counts"]["records"])
    print("  distinct case ids:     %d" % len(payload_ids))
    print("  the 168 list:          %d cases" % len(p168_ids))
    print("  the portal list crawl: %d entries" % len(portal))

    # =====================================================================
    print()
    print("=" * 72)
    print("Q1  are there projects not in the lists?")
    print("=" * 72)
    no_id = []
    only_off_list = []
    in_168 = 0
    for p in projects:
        links = p.get("links") or {}
        ids = set(links.get("taipei") or [])
        for node in p.get("nodes") or ():
            ids.update((node.get("links") or {}).get("taipei") or [])
        if not ids:
            no_id.append(p)
        elif ids & p168_ids:
            in_168 += 1
        else:
            only_off_list.append(p)

    print()
    print("  a project is IN the 168 list when one of its case ids is on it.")
    print("  %d of %d projects are on the 168 list." % (in_168, len(projects)))
    print("  %d carry case ids, none of them on the 168 list." % len(only_off_list))
    print("     -> the 168 list is a SUBSET, not a register of every case.")
    print("        A case in review outside the 168 program is not on it.")
    print("  %d carry no case id at all -> in NEITHER list by construction."
          % len(no_id))
    for p in no_id:
        print("        %s" % p["project_id"])

    print()
    print("  the national portal list is reached by land core, not case id.")
    print("  a project whose core is in the crawled index is in that list:")
    in_portal = 0
    for p in projects:
        core = "%s%s%s" % (p.get("district", ""), p.get("section", ""),
                           _first_parcel_of(p))
        if core in portal_cores:
            in_portal += 1
    print("  %d of %d projects match a crawled portal core." % (in_portal, len(projects)))
    print("  the crawl holds %d entries and the payload names %d distinct"
          % (len(portal), len(payload_ids)))
    print("  case ids; the crawl is WAF-capped, so a partial crawl is not a")
    print("  missing project. Proof of completeness for that list is a live")
    print("  re-crawl, not this file.")

    # =====================================================================
    print()
    print("=" * 72)
    print("Q2  are there recno not in any project?")
    print("=" * 72)
    node_recnos = [n["recno"] for p in projects for n in p["nodes"]]
    clean = tsv_recnos(CLEAN)
    with MERGED.open(encoding="utf-8") as fh:
        merged_rows = list(csv.DictReader(fh, delimiter="\t"))

    seen = set()
    duplicates = sorted({r for r in node_recnos if r in seen or seen.add(r)})
    lost = sorted(clean - set(node_recnos))
    extra = sorted(set(node_recnos) - clean)

    print()
    print("  the check is a partition: every cleansed record is in exactly one")
    print("  project, and no project holds a record cleansing does not.")
    print()
    print("  clean.tsv records:            %d" % len(clean))
    print("  payload nodes:                %d" % len(node_recnos))
    print("  distinct node recnos:         %d" % len(set(node_recnos)))
    print("  a recno in two nodes:         %d %s"
          % (len(duplicates), duplicates[:10]))
    print("  a cleansed record in no project: %d %s" % (len(lost), lost[:10]))
    print("  a node whose record is not cleansed: %d %s" % (len(extra), extra[:10]))
    print("  merged.tsv rows:              %d" % len(merged_rows))
    print("  distinct project_id in merged.tsv: %d"
          % len({r["project_id"] for r in merged_rows}))
    print()
    ok2 = not duplicates and not lost and not extra
    print("  VERDICT: %s" % ("the partition is total and disjoint."
                            if ok2 else "THE PARTITION IS BROKEN."))

    # =====================================================================
    print()
    print("=" * 72)
    print("Q3  is every recno attached to a 北 badge (case_id)?")
    print("=" * 72)
    unbadged = []
    flagged = 0
    flagged_with_id = 0
    for p in projects:
        for node in p.get("nodes") or ():
            has = bool((node.get("links") or {}).get("taipei"))
            is_flagged = any("節點未能對應平台案件" in f
                             for f in (node.get("review_flags") or []))
            if is_flagged:
                flagged += 1
                if has:
                    flagged_with_id += 1
            if not has:
                unbadged.append((p["project_id"], node["recno"], node.get("date", ""),
                                 node.get("case_name", "")))

    print()
    print("  the badge is drawn from a node's links.taipei (viewer/app.js,")
    print("  getNodeMilestoneBadges). An empty links.taipei renders no badge.")
    print()
    print("  nodes:                        %d" % len(node_recnos))
    print("  nodes carrying a case id:     %d" % (len(node_recnos) - len(unbadged)))
    print("  nodes carrying NO case id:    %d" % len(unbadged))
    print("  nodes flagged 節點未能對應平台案件: %d" % flagged)
    print("  of those, carrying a case id: %d" % flagged_with_id)
    print()
    if unbadged:
        print("  the %d badge-less nodes:" % len(unbadged))
        for pid, recno, date, name in unbadged:
            print("    recno %-5s %s  %s" % (recno, date, name[:56]))
        print()
    same = flagged == len(unbadged) and flagged_with_id == 0
    print("  VERDICT: %s" % (
        "the flag and the badge agree exactly — %d nodes have neither, and no"
        % len(unbadged) if same else
        "the flag and the badge DISAGREE."))
    if same:
        print("           node carries a case id while the flag says it does not.")
        print("           Every badge-less node is named, not silently unbound.")

    return 0


def _first_parcel_of(project: dict) -> str:
    """The project's first parcel, as the portal index's core carries it."""
    for node in project.get("nodes") or ():
        fp = node.get("first_parcel")
        if fp:
            return "%s地號等%s筆" % (fp, node.get("land_count") or 1)
    return ""


if __name__ == "__main__":
    raise SystemExit(main())
