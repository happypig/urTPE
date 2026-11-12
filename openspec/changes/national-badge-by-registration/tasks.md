# Tasks: national-badge-by-registration

## 1. Tests first (test-first gate)

- [x] 1.1 `tests/test_national_badge.py` — the emission rule, by name: a node
  whose anchored case is in `view_verified_case_ids` carries
  `national_badges: true`; a node whose 案名 equals `twur_name` carries it; a
  node qualifying only by stage+date match does NOT (the 文林838-1 node 433
  shape: two labels hit its date, its case unregistered — no badge).
- [x] 1.2 `tests/test_national_badge.py` — the 擬訂 section+parcel fallback:
  a 擬訂 node whose (section, first-parcel) parses from `twur_name` carries
  the badge (the 大安590 node 884 shape); a 變更 node with the same
  section+parcel does NOT (the fallback is 擬訂-only).
- [x] 1.3 `tests/test_national_badge.py` — the round trip: the field
  survives `--from-js` (the supersede-headerless-cases D6 contract; the
  loader reads it back).
- [ ] 1.4 `tests/test_national_badge.py` — the counters on the live payload:
  1,186 nodes carry 國 today → 735 under the rule; 451 lose it; 0 gain it.
- [x] 1.5 `scripts/viewer_smoke.js` — the national-binding check re-targets
  the field: every node the payload marks `national_badges` renders exactly
  one 國; no node without the field renders one.

## 2. Implementation

- [x] 2.1 `urtpe/graph.py` — compute the rule in `build_project_graph`:
  `national_badges` per node (case-registered OR exact-name OR 擬訂
  fallback), only when `twur` exists.
- [x] 2.2 `urtpe/links.py` — the `--from-js` round trip reads the field back
  (the D6 field-by-field contract; cite this change).
- [x] 2.3 `viewer/app.js` — `getNodeMilestoneBadges` reads
  `n.national_badges`; `bindNationalLabels` and `nationalLabelKey` retire;
  the comment at the badge site names this change.
- [x] 2.4 Re-emit the payload (`--from-js`).

## 3. Verify

- [x] 3.1 `python -m pytest` — full suite green. *(1292 passed / 1 skipped; the 800-count superseded the board's 735 pre-fallback figure)*
- [x] 3.2 `node scripts/viewer_smoke.js` — green (the re-targeted check
  included).
- [x] 3.3 The two named examples hold in the emitted payload: 文林838-1 node
  433 carries no 國; 大安590 nodes 1257/884 carry it, node 90 does not.
