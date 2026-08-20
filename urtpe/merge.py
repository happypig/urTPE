"""Similarity merge domain.

Pure logic: candidate generation, weighted similarity scoring, clustering
into project families, latest-anchored project_id slugging.
"""

from __future__ import annotations

from collections import defaultdict, Counter

from urtpe.models import CleanRecord, Project

LINK_THRESHOLD = 0.7
FLAG_THRESHOLD = 0.5


def _candidates(records: list[CleanRecord]) -> set[tuple[int, int]]:
    """Candidate pairs sharing district+section, plus shared named anchors."""
    by_loc: dict[tuple[str, str], list[CleanRecord]] = defaultdict(list)
    by_anchor: dict[str, list[CleanRecord]] = defaultdict(list)
    for r in records:
        by_loc[(r.district, r.section)].append(r)
        if r.named_anchor:
            by_anchor[r.named_anchor].append(r)

    pairs: set[tuple[int, int]] = set()
    for group in by_loc.values():
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                a, b = group[i].recno, group[j].recno
                pairs.add((min(a, b), max(a, b)))
    for group in by_anchor.values():
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                a, b = group[i].recno, group[j].recno
                pairs.add((min(a, b), max(a, b)))
    return pairs


def score(r1: CleanRecord, r2: CleanRecord) -> float:
    """Weighted similarity in [0, 1]. Weights: sec .35, first-parcel .2, parcels .3, count .1."""
    if r1.named_anchor and r1.named_anchor == r2.named_anchor:
        return 1.0

    if r1.district != r2.district or r1.section != r2.section:
        return 0.0
    sec = 1.0

    p1, p2 = r1.first_parcel, r2.first_parcel
    fp = 0.0
    if p1 and p2:
        if p1 == p2:
            fp = 1.0
        elif (p2 in r2.parcels and p1 in r2.aliases.get(p2, [])) or (
            p1 in r1.parcels and p2 in r1.aliases.get(p1, [])
        ):
            fp = 0.95  # renumbering alias bridges
        elif p1 in r2.parcel_set() or p2 in r1.parcel_set():
            fp = 0.7

    cnt = 0.0
    if r1.land_count and r2.land_count:
        if r1.land_count == r2.land_count:
            cnt = 1.0
        elif r1.orig_count == r2.land_count or r2.orig_count == r1.land_count:
            cnt = 0.8

    s1, s2 = r1.parcel_set(), r2.parcel_set()
    if s1 and s2:
        inter = len(s1 & s2)
        union = len(s1 | s2)
        jac = inter / union if union else 0.0
    elif not s1 and not s2 and fp >= 1.0 and cnt >= 1.0:
        # Both parcel sets are empty (unparseable 地號 cells) but the full land
        # key — district, section, first parcel, count — agrees. Redistribute
        # the lost .3 Jaccard weight across the surviving components so a full
        # match scores 1.0 and links (e.g. across implementer changes). A
        # partial land-key match keeps the old (≤0.65) value: no over-merging.
        return (0.35 * sec + 0.2 * fp + 0.1 * cnt) / (0.35 + 0.2 + 0.1)
    else:
        jac = 0.0

    return 0.35 * sec + 0.2 * fp + 0.3 * jac + 0.1 * cnt


def _clusters(records: list[CleanRecord], pairs: set[tuple[int, int]]) -> tuple[list[list[CleanRecord]], list[tuple[int, int, float]]]:
    """Union-find connected components on links >= 0.7; collect borderline pairs."""
    by_recno = {r.recno: r for r in records}
    parent = {r.recno: r.recno for r in records}
    rank = {r.recno: 0 for r in records}

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra == rb:
            return
        if rank[ra] < rank[rb]:
            ra, rb = rb, ra
        parent[rb] = ra
        if rank[ra] == rank[rb]:
            rank[ra] += 1

    borderline: list[tuple[int, int, float]] = []
    for a, b in pairs:
        s = score(by_recno[a], by_recno[b])
        if s >= LINK_THRESHOLD:
            union(a, b)
        elif s >= FLAG_THRESHOLD:
            borderline.append((a, b, round(s, 3)))

    groups: dict[int, list[CleanRecord]] = defaultdict(list)
    for r in records:
        groups[find(r.recno)].append(r)
    return [sorted(g, key=lambda r: r.recno) for g in groups.values()], borderline


def slug_for(anchor: CleanRecord) -> str:
    """project_id from the anchor's normalized name-core (append-friendly)."""
    core = f"{anchor.district}-{anchor.section}-{anchor.first_parcel}地號等{anchor.land_count or '?'}筆"
    core = core.replace("計劃", "計畫").replace("ㄧ", "一").replace(" ", "")
    if not anchor.section:
        return f"未解析-{anchor.recno}"
    return core


def pick_anchor(members: list[CleanRecord]) -> CleanRecord:
    """Newest by 核定日期; tie-break = closest to 編號 1 (lowest recno)."""
    top = max(m.ymd for m in members)
    tied = [m for m in members if m.ymd == top]
    return min(tied, key=lambda m: m.recno)


def merge(records: list[CleanRecord]) -> list[Project]:
    """Cluster records into project families, anchor each, assign ids."""
    pairs = _candidates(records)
    clusters, borderline = _clusters(records, pairs)
    projects = []
    recno_to_project: dict[int, Project] = {}
    for members in clusters:
        anchor = pick_anchor(members)
        pid = slug_for(anchor)
        p = Project(project_id=pid, anchor_recno=anchor.recno, members=members)
        projects.append(p)
        for m in members:
            recno_to_project[m.recno] = p
    for (a, b, s) in borderline:
        recno_to_project[a].borderline.append((a, b, s))
    projects.sort(key=lambda p: (p.project_id, p.anchor_recno))
    used: Counter = Counter()
    for p in projects:
        used[p.project_id] += 1
        if used[p.project_id] > 1:
            p.project_id = f"{p.project_id}-{used[p.project_id]}"
    projects.sort(key=lambda p: p.project_id)
    return projects