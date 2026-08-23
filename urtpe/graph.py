"""History graph domain: build per-project JSON from merged projects."""

from __future__ import annotations

from urtpe.links import attach_links_to_projects
from urtpe.models import CleanRecord, Project


def _sort(members: list[CleanRecord]) -> list[CleanRecord]:
    return sorted(members, key=lambda r: (r.ymd, r.recno))


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
            "review_flags": r.review_flags,
            "auto_fixes": r.auto_fixes,
            # District fields for link discovery core building
            "district": r.district,
            "district_land": r.district_land,
        }
        # Include links if present on the member record
        if hasattr(r, 'links') and r.links:
            node["links"] = r.links
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
    return {
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


def build_graph_document(projects: list[Project], meta: dict, link_results: dict | None = None) -> dict:
    # Attach discovered links to projects if available
    if link_results:
        attach_links_to_projects(projects, link_results)

    graphs = []
    published_date = meta.get("published_date", "")
    for p in projects:
        anchor = next(r for r in p.members if r.recno == p.anchor_recno)
        graphs.append(build_project_graph(p, implementer=anchor.implementer, name=anchor.name, published_date=published_date))
    return {
        "schema_version": 1,
        "generated_at": meta.get("generated_at", ""),
        "source": meta.get("source", ""),
        "published_date": meta.get("published_date", ""),
        "counts": {"projects": len(graphs), "records": sum(len(p.members) for p in projects)},
        "projects": graphs,
    }