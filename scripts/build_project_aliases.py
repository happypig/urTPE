#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build the project_id alias table for cache migration.

A project's identity is the land-core slug of its newest approval, so it changes
whenever that approval's parcel description changes. The per-project caches under
``data/.link_cache/<project_id>/`` are keyed on the old slug and would be orphaned.

Pairs are formed on member content -- approval date plus normalized parcel cell --
never on the slug itself, because the slug is exactly what moved. A pair is accepted
only when it is unambiguous: if a former identity's members match more than one
current project, no alias is written and the cache directory is reported as
ambiguous for a human to resolve.

    python scripts/build_project_aliases.py [--prev PATH] [--current PATH]
                                            [--cache DIR] [--out PATH]

``--prev`` defaults to the previous projects.json recovered from git, which is the
only place the 115/8/11 dataset still exists.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from urtpe.ledger import normalize_land  # noqa: E402

# The 段/小段 token, and the parcel numbers that precede 地號等 in a land cell.
SECTION_RE = re.compile(r"[一-鿿]{1,3}段[一-鿿]{0,2}小段")
PARCEL_RE = re.compile(r"\d+(?:-\d+)?")


def sanitize(project_id: str) -> str:
    """Match the cache directory naming in urtpe.links."""
    return re.sub(r"[^\w\-]", "_", project_id)


def iso_date(node: dict) -> str:
    from urtpe.extract import to_iso

    date = node.get("date", "") or ""
    return date if re.fullmatch(r"\d{4}-\d{2}-\d{2}", date) else (to_iso(date)[0] or "")


def member_keys(project: dict) -> Counter:
    """Content identity of each member: ISO date plus normalized parcel cell.

    The date must be ISO on both sides. Keying on the printed string matches
    nothing across the city's calendar change: ``115/8/11`` and ``2026/8/11``
    are the same day and were being compared as different.
    """
    keys = Counter()
    for node in project.get("nodes", []):
        keys[(iso_date(node), normalize_land(node.get("land", "") or ""))] += 1
    return keys


def section_of(land: str) -> str:
    """The 段/小段 token, without the district prefix."""
    m = SECTION_RE.search(re.sub(r"\s+", "", land or ""))
    return m.group(0) if m else ""


def parcels_of(land: str) -> set[str]:
    """Parcel numbers from a 地號 cell.

    The city lists parcels ascending, so the first-listed parcel is the *minimum*.
    A scope change that adds a smaller parcel therefore rewrites the slug's parcel
    with no textual overlap, which is why exact matching alone under-reports.
    """
    head = re.sub(r"\s+", "", land or "").split("地號等")[0]
    head = re.sub(r"^臺北市[一-鿿]{1,3}區", "", head)
    head = SECTION_RE.sub("", head, count=1)
    return set(PARCEL_RE.findall(head))


def jaccard(a: set[str], b: set[str]) -> float:
    return len(a & b) / len(a | b) if a and b else 0.0


def load(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    text = re.sub(r"^window\.PROJECTS\s*=\s*", "", text.strip())
    text = re.sub(r";\s*$", "", text)
    return json.loads(text)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--prev", default=str(ROOT / "data" / "projects.previous.json"))
    ap.add_argument("--current", default=str(ROOT / "data" / "projects.json"))
    ap.add_argument("--cache", default=str(ROOT / "data" / ".link_cache"))
    ap.add_argument("--out", default=str(ROOT / "data" / "project_aliases.json"))
    ap.add_argument("--overlap-threshold", type=float, default=0.5,
                    help="parcel Jaccard at which a scope-changed unit is accepted")
    ap.add_argument("--no-overlap", action="store_true",
                    help="exact content matching only")
    args = ap.parse_args(argv)

    prev_path, cur_path = Path(args.prev), Path(args.current)
    if not prev_path.exists():
        print(f"[ERROR] previous dataset not found: {prev_path}", file=sys.stderr)
        print("        recover it with: git show HEAD:data/projects.json > data/projects.previous.json",
              file=sys.stderr)
        return 2

    prev = load(prev_path)["projects"]
    cur = load(cur_path)["projects"]
    cache_dir = Path(args.cache)

    cur_by_key: dict[tuple[str, str], list[str]] = {}
    for p in cur:
        for key in member_keys(p):
            cur_by_key.setdefault(key, []).append(p["project_id"])

    cur_ids = {p["project_id"] for p in cur}
    cached = {d.name for d in cache_dir.iterdir() if d.is_dir()} if cache_dir.exists() else set()

    aliases: dict[str, str] = {}
    basis: dict[str, str] = {}
    ambiguous: dict[str, list[str]] = {}
    unmatched: list[str] = []
    claimed: set[str] = set()
    orphaned: list[str] = []

    # -- tier 1: exact ISO date + normalized land --------------------------
    pending: list[dict] = []
    for p in prev:
        old = p["project_id"]
        if old in cur_ids:
            continue
        if sanitize(old) not in cached:
            continue  # no cache to preserve
        orphaned.append(old)
        candidates: Counter = Counter()
        for key in member_keys(p):
            for cid in cur_by_key.get(key, ()):
                candidates[cid] += 1
        if not candidates:
            pending.append(p)
            continue
        best, score = candidates.most_common(1)[0]
        rivals = [c for c, s in candidates.items() if s == score and c != best]
        if rivals or best in claimed:
            ambiguous[old] = [best, *rivals] if rivals else [best]
            continue
        aliases[old] = best
        basis[old] = "exact"
        claimed.add(best)

    # -- tier 2: same 段/小段, high parcel overlap -------------------------
    # Applies to a unit whose parcel scope changed. Because the city lists parcels
    # ascending, adding a smaller parcel moves the minimum and rewrites the slug
    # even though most parcels are shared; measured at 94.6% verbatim match rate,
    # the residual is dominated by exactly this case.
    by_section: dict[str, list[dict]] = {}
    for p in cur:
        for n in p.get("nodes", []):
            if n.get("orphan"):
                continue
            sec = section_of(n.get("land", ""))
            if sec:
                by_section.setdefault(sec, []).append({"pid": p["project_id"], "parcels": parcels_of(n.get("land", ""))})

    if not args.no_overlap:
        for p in pending:
            old = p["project_id"]
            nodes = [n for n in p.get("nodes", []) if not n.get("orphan")]
            old_parcels = set()
            sections = set()
            for n in nodes:
                sections.add(section_of(n.get("land", "")))
                old_parcels |= parcels_of(n.get("land", ""))
            if not old_parcels:
                unmatched.append(old)
                continue
            scores: Counter = Counter()
            for sec in sections:
                for cand in by_section.get(sec, []):
                    j = jaccard(old_parcels, cand["parcels"])
                    if j >= args.overlap_threshold:
                        scores[cand["pid"]] = max(scores[cand["pid"]], j)
            if not scores:
                unmatched.append(old)
                continue
            ranked = scores.most_common()
            best, best_j = ranked[0]
            tied = [c for c, j in ranked if abs(j - best_j) < 1e-9]
            if len(tied) > 1 or best in claimed:
                ambiguous[old] = tied
                continue
            aliases[old] = best
            basis[old] = f"overlap J={best_j:.2f}"
            claimed.add(best)
    else:
        unmatched.extend(p["project_id"] for p in pending)

    out = {
        "_comment": "project_id aliases for cache migration; former -> current. "
                    "Regenerate with scripts/build_project_aliases.py",
        "_buckets": {
            "aliases": "former -> current. basis 'exact' = identical ISO date and "
                       "parcel cell; 'overlap J=' = same 段/小段 with the parcels "
                       "overlapping above the threshold, i.e. a scope change",
            "ambiguous": "several current projects match equally well; needs a human",
            "unmatched": "nothing above the threshold; the cache directory is stranded",
        },
        "overlap_threshold": args.overlap_threshold,
        "previous_published_date": load(prev_path).get("published_date", ""),
        "current_published_date": load(cur_path).get("published_date", ""),
        "aliases": aliases,
        "alias_basis": basis,
        "ambiguous": ambiguous,
        "unmatched": unmatched,
        "orphaned": orphaned,
    }
    Path(args.out).write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"previous projects: {len(prev)}   current: {len(cur)}")
    print(f"cache directories: {len(cached)}")
    print(f"orphaned (cached, absent from current): {len(orphaned)}")
    print(f"aliases written: {len(aliases)}")
    for old in sorted(aliases):
        print(f"  [{basis[old]:>12}]  {old}  ->  {aliases[old]}")
    print(f"ambiguous (needs a human): {len(ambiguous)}")
    for old, cands in sorted(ambiguous.items()):
        print(f"  {old}  ->  {cands}")
    print(f"unmatched (investigate): {len(unmatched)}")
    for old in sorted(unmatched):
        print(f"  {old}")
    print(f"\nwritten to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())