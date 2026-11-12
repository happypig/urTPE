"""History graph domain: build per-project JSON from merged projects."""

from __future__ import annotations

import re

from urtpe.links import attach_links_to_projects
from urtpe.models import CleanRecord, Project


def _sort(members: list[CleanRecord]) -> list[CleanRecord]:
    return sorted(members, key=lambda r: (r.ymd, r.recno))


def _dedupe(flags) -> list[str]:
    """Collapse repeated flag strings, preserving first-appearance order.

    The 2026-10-06 dataset carried 1162 copies of one flag across 282 nodes, accumulated
    one per --links run. The copies were identical, so collapsing loses no distinct
    finding; order is kept as first-seen so the review report still reads in the order the
    conditions were met.
    """
    seen, out = set(), []
    for f in flags or []:
        if f not in seen:
            seen.add(f)
            out.append(f)
    return out


# D15 (inspection-batchD): the case id a flag names. The orphan and conflict
# flags name the case they are about; the cleansing flags name none.
_FLAG_CASE_RE = re.compile(r"案(\d+)")


def _flag_key(flag: str) -> tuple[str, str]:
    """The stable order key of a review flag: the case id it names, then the
    text.

    The order the flags were raised in was a function of the pipeline's
    traversal order, and that order follows the family's member order — so a
    ledger merge that reorders one family reorders the flags on the node it
    anchors, with nothing in the data to say so (D5's 吉林676 merge moved
    three orphan flags on 大龍265-7 node 1242). Sorting here, at the emitter,
    covers every raising path at once.
    """
    m = _FLAG_CASE_RE.search(flag)
    return (m.group(1) if m else "", flag)


def _stable_flags(flags) -> list[str]:
    """The node's flags: duplicates collapsed, then sorted by a stable key."""
    return sorted(_dedupe(flags), key=_flag_key)


def build_project_graph(project: Project, implementer: str, name: str, published_date: str = "") -> dict:
    ordered = _sort(project.members)
    anchor_recno = project.anchor_recno

    nodes = []
    for r in ordered:
        node = {
            "recno": r.recno,
            "date": r.iso_date,
            "stage": r.stage,
            "track": r.track,
            "area": r.area_section,
            # The cleanser's stage index, emitted so a rebuild from emitted state
            # groups section branches identically (emit-stage-index; the bug was
            # the same class as the ymd one documented in cli.py).
            "stage_index": r.stage_index,
            "is_current": r.recno == anchor_recno,
            # Full CleanRecord fields for detail table
            "case_name": r.name,
            "name_raw": r.name_raw,
            "land": r.land,
            "section": r.section,
            "first_parcel": r.first_parcel,
            "parcels": r.parcels,
            "aliases": r.aliases,
            "land_count": r.land_count,
            "orig_count": r.orig_count,
            "named_anchor": r.named_anchor,
            "area_section": r.area_section,
            "implementer": r.implementer,
            "planner": r.planner,
            "review_flags": _stable_flags(r.review_flags),
            "auto_fixes": r.auto_fixes,
            # District fields for link discovery core building
            "district": r.district,
            "district_land": r.district_land,
            # §10 per-track stages for combined-track nodes (additive)
            "stage_事業計畫": getattr(r, "stage_事業計畫", None),
            "stage_權利變換": getattr(r, "stage_權利變換", None),
        }
        # Include links if present on the member record
        if hasattr(r, 'links') and r.links:
            node["links"] = r.links
        # Per-record implementation snapshot (additive optional)
        impl_snapshot = getattr(r, "implementation", None)
        if impl_snapshot:
            node["implementation"] = impl_snapshot
        # Recovery provenance (additive, recovered rows only — the flag-less
        # emission must stay byte-identical, so this key exists only here)
        recovery = getattr(r, "recovery", None)
        if recovery:
            node["recovery"] = recovery
        # national-badge-by-registration: the resolved binding survives a
        # reload verbatim (the mark step recomputes it when links are present;
        # the record's field covers the no-links rebuild).
        if getattr(r, "national_badges", False):
            node["national_badges"] = True
        nodes.append(node)

    edges: list[dict] = []
    seen: set[tuple[int, int, str]] = set()

    def add_edge(frm: int, to: int, kind: str) -> None:
        key = (frm, to, kind)
        if key in seen:
            return
        seen.add(key)
        edges.append({"from": frm, "to": to, "kind": kind})

    # Overall revision chain converging on the anchor (last member).
    for a, b in zip(ordered, ordered[1:]):
        add_edge(a.recno, b.recno, "revision")

    # Per-track chains.
    by_track: dict[str, list[CleanRecord]] = {}
    for r in ordered:
        for t in r.track.split("、"):
            by_track.setdefault(t, []).append(r)
    for track, members in by_track.items():
        if len(members) < 2:
            continue
        ms = sorted(members, key=lambda r: (r.ymd, r.recno))
        for a, b in zip(ms, ms[1:]):
            add_edge(a.recno, b.recno, "track")

    # Section branches within the same stage/track.
    stage_groups: dict[tuple, list[CleanRecord]] = {}
    for r in ordered:
        stage_groups.setdefault((r.stage_index, r.track), []).append(r)
    for (_si, _tk), members in stage_groups.items():
        areas = {m.area_section for m in members if m.area_section}
        if len(areas) < 2:
            continue
        ms = sorted(members, key=lambda r: r.recno)
        for a, b in zip(ms, ms[1:]):
            add_edge(a.recno, b.recno, "section")

    project_links = getattr(project, 'links', {})
    graph = {
        "project_id": project.project_id,
        "anchor_recno": anchor_recno,
        "district": ordered[0].district,
        "section": ordered[0].section,
        "implementer": implementer,
        "name": name,
        "member_recnos": [r.recno for r in ordered],
        "nodes": nodes,
        "edges": edges,
        "links": project_links,
        "published_date": published_date,
    }
    # Optional schema-v2 objects (absent when discovery found no data)
    if getattr(project, "implementation", None):
        graph["implementation"] = project.implementation
    if getattr(project, "rewards", None):
        graph["rewards"] = project.rewards
    return graph


def build_graph_document(projects: list[Project], meta: dict, link_results: dict | None = None,
                         permit_index: dict | None = None) -> dict:
    # Attach discovered links to projects if available
    if link_results:
        attach_links_to_projects(
            projects, link_results,
            permit_index_getter=(lambda: permit_index) if permit_index else None)

    graphs = []
    published_date = meta.get("published_date", "")
    for p in projects:
        anchor = next(r for r in p.members if r.recno == p.anchor_recno)
        graphs.append(build_project_graph(p, implementer=anchor.implementer, name=anchor.name, published_date=published_date))
    _mark_national_badges(graphs)
    return {
        "schema_version": 2,
        "generated_at": meta.get("generated_at", ""),
        "source": meta.get("source", ""),
        "published_date": meta.get("published_date", ""),
        "counts": {"projects": len(graphs), "records": sum(len(p.members) for p in projects)},
        "projects": graphs,
    }


def _mark_national_badges(graphs: list[dict]) -> None:
    """Resolve the 國 badge once, at graph build (national-badge-by-registration,
    user decision 2026-11-12). A recno node carries `national_badges: true`
    when the national view page names it:

    1. registration — the node's anchored case is in
       `links.view_verified_case_ids`;
    2. exact name — the node's 案名 equals `links.twur_name`;
    3. 擬訂 section+parcel fallback — a 擬訂 node whose (section,
       first-parcel) parses from the twur_name's land core (the 權利變換
       擬訂 案名 differs from the title by one word; the unit is the same by
       its own land core, not by a date).

    The former per-label stage+date binding is retired: a date matching is
    not the portal naming. Measured 2026-11-12: 1,186 badged under the old
    rule, 735 under this one, 451 lose, 0 gain. The viewer renders from the
    field; it must not re-implement the matcher.
    """
    from urtpe.cleanse import parse_name_id

    for proj in graphs:
        links = proj.get("links") or {}
        twur = links.get("twur") or ""
        if not twur:
            # No national page: no badge field may survive (a reloaded payload
            # whose project lost its link must not keep a stale mark).
            for node in proj.get("nodes", []):
                node.pop("national_badges", None)
            continue
        vv = set(links.get("view_verified_case_ids") or [])
        twur_name = links.get("twur_name") or ""
        core = parse_name_id(twur_name) if twur_name else ("", "", "", None)
        core_section, core_parcel = core[1], core[2]
        for node in proj.get("nodes", []):
            cases = (node.get("links") or {}).get("taipei") or []
            registered = any(c in vv for c in cases)
            exact_name = bool(twur_name) and node.get("case_name") == twur_name
            fallback = (core_section and core_parcel
                        and node.get("stage") == "擬訂"
                        and node.get("section") == core_section
                        and node.get("first_parcel") == core_parcel)
            if registered or exact_name or fallback:
                node["national_badges"] = True
            else:
                # Recompute wins over a reloaded record's stale mark.
                node.pop("national_badges", None)