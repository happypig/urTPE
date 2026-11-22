# Tasks: hide-superseded-orphans

## 1. Tests (test-first — all checked before any implementation task)

- [x] 1.1 Unit test: a superseded case (recorded in `superseded_by`) whose
      name is landcore-similar creates NO ghost node, stays in `links.taipei`
      (虎林38's 10806141 → 11510017 shape) —
      `tests/test_links.py::TestOrphanGhostAnchoring::test_superseded_orphan_is_withheld`
- [x] 1.2 Unit test: a superseded case whose successor anchors by date still
      hides the old node; the successor's node carries the history —
      `test_superseded_successor_carries_the_history`

## 2. Implementation

- [x] 2.1 `attach_links_to_projects`'s orphan loop skips `superseded_by`
      cases before the similarity gate (they would pass it — their names are
      the unit's own)

## 3. Verification

- [x] 3.1 `python -m pytest` full suite green
- [x] 3.2 Re-emit; the 4 measured undated superseded orphans (10410012,
      10806141, 11009142, 11211211) are gone; smoke + baseline pass
- [x] 3.3 `openspec validate --all` green; archive the change and sync the
      delta
