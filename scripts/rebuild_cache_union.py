"""Union-restore data/.link_cache from ordered cache generations.

Recovers a wiped/partially-regenerated link cache by rebuilding it as a
best-of-N union across generation snapshots (backup dirs + WIP partials).
For every project directory, each candidate result.json is parsed and ranked;
the winner's result.json is copied into the target together with its sibling
view.html when present.

Winner selection (design.md Decision 6):
  1. full-current-schema gate: case_milestones, milestones_source,
     implementation, rewards, search_rejected must ALL be present — old-schema
     files cannot represent guard state and are never selected
  2. status == "resolved"
  3. richness: len(city_case_ids), len(taipei_milestones),
     len(national_milestones), no error
Ties favor the earlier-listed (fresher) generation.

Root-level artifacts (portal_index.json, no_match_ledger.json) are copied from
the root-gen snapshot (default: .link_cache_backup_20260826_fix).

The target directory must not already exist or must be empty — move partials
aside first (e.g., to data/.link_cache_wip_20260827).

Usage:
  python scripts/rebuild_cache_union.py [--out data/.link_cache] \
      [GEN ...]                       # default gens listed below, in order
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from collections import Counter
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

DEFAULT_GENS = [
    "data/.link_cache_wip_20260827",
    "data/.link_cache_backup_20260826_fix",
    "data/.link_cache_backup_20260825_matcher",
    "data/.link_cache_backup_20260824",
]
ROOT_GEN = "data/.link_cache_backup_20260826_fix"
ROOT_FILES = ["portal_index.json", "no_match_ledger.json"]
REQUIRED_FIELDS = {
    "case_milestones",
    "milestones_source",
    "implementation",
    "rewards",
    "search_rejected",
}


def load_candidate(path: Path):
    """Parse a result.json; return dict or None when unreadable."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def score(data: dict):
    """Ranking tuple; None when the candidate fails the full-schema gate."""
    if not REQUIRED_FIELDS.issubset(data.keys()):
        return None
    return (
        1 if data.get("status") == "resolved" else 0,
        len(data.get("city_case_ids") or []),
        len(data.get("taipei_milestones") or {}),
        len(data.get("national_milestones") or {}),
        0 if data.get("error") else 1,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", default="data/.link_cache", help="target cache dir")
    parser.add_argument(
        "--root-gen", default=ROOT_GEN, help="snapshot donating root-level files"
    )
    parser.add_argument("gens", nargs="*", help="generation dirs, freshest first")
    args = parser.parse_args()

    gens = [Path(g) for g in (args.gens or DEFAULT_GENS)]
    for g in gens:
        if not g.is_dir():
            sys.exit(f"missing generation dir: {g}")
    out = Path(args.out)
    if out.exists() and any(out.iterdir()):
        sys.exit(f"target {out} exists and is not empty; move it aside first")

    # ── Scan phase ───────────────────────────────────────────────────────────
    candidates: dict[str, list[tuple[int, Path]]] = {}
    gen_stats: dict[int, Counter] = {}
    for gi, g in enumerate(gens):
        stats = gen_stats.setdefault(gi, Counter())
        for d in sorted(g.iterdir()):
            rf = d / "result.json"
            if not d.is_dir() or not rf.is_file():
                continue
            stats["files"] += 1
            data = load_candidate(rf)
            if data is None:
                stats["unparsed"] += 1
                continue
            st = data.get("status", "?")
            stats[f"status:{st}"] += 1
            if REQUIRED_FIELDS.issubset(data.keys()):
                stats["schema_full"] += 1
            else:
                stats["schema_old"] += 1
            candidates.setdefault(d.name, []).append((gi, d))

    names = sorted(candidates)
    print(f"scanned {len(names)} distinct projects across {len(gens)} generations\n")

    # ── Report per-generation composition ───────────────────────────────────
    header = f"{'gen':34} {'files':>5} {'full':>5} {'old':>4} {'unp':>4} {'resolved':>8} {'unres':>6}"
    print(header)
    for gi, g in enumerate(gens):
        s = gen_stats[gi]
        print(
            f"{g.name[-33:]:34} {s['files']:>5} {s['schema_full']:>5} "
            f"{s['schema_old']:>4} {s['unparsed']:>4} "
            f"{s['status:resolved']:>8} {s['status:unresolved']:>6}"
        )
    print()

    # ── Restore phase ────────────────────────────────────────────────────────
    winner_from: Counter = Counter()
    raw_fallback: list[str] = []
    view_carried = 0
    schema_ok = 0
    for name in names:
        best_gi, best_dir, best_score = None, None, None
        for gi, d in candidates[name]:  # gens pre-ordered freshest-first
            data = load_candidate(d / "result.json")
            sc = score(data) if data is not None else None
            if sc is None:
                continue
            if best_score is None or sc > best_score:  # strict > keeps earlier gen on ties
                best_gi, best_dir, best_score = gi, d, sc

        target = out / name
        target.mkdir(parents=True, exist_ok=True)

        if best_dir is None:
            # No full-schema candidate anywhere: preserve newest raw file so no
            # project silently vanishes; flagged in the report.
            gi, d = candidates[name][0]
            shutil.copyfile(d / "result.json", target / "result.json")
            raw_fallback.append(name)
            continue

        shutil.copyfile(best_dir / "result.json", target / "result.json")
        winner_from[gens[best_gi].name] += 1
        if (best_dir / "view.html").is_file():
            shutil.copyfile(best_dir / "view.html", target / "view.html")
            view_carried += 1
        schema_ok += 1

    # ── Root-level artifacts from the designated root gen ───────────────────
    root_gen = Path(args.root_gen)
    copied_root = []
    if root_gen.is_dir():
        for fn in ROOT_FILES:
            src = root_gen / fn
            if src.is_file():
                shutil.copyfile(src, out / fn)
                copied_root.append(fn)

    # ── Final report ────────────────────────────────────────────────────────
    total = len(names)
    print(f"restored {total} projects -> {out}")
    print(f"  full-schema winners : {schema_ok}/{total}")
    for gname, n in winner_from.most_common():
        print(f"  winners from {gname}: {n}")
    if raw_fallback:
        print(f"  RAW FALLBACK (no full-schema candidate): {len(raw_fallback)}")
        for n in raw_fallback[:10]:
            print(f"    {n}")
    print(f"  view.html carried   : {view_carried}")
    print(f"  root files copied   : {', '.join(copied_root) or '(none)'}")


if __name__ == "__main__":
    main()
