# Tasks: nfkc-fold-compat-ideographs

## 1. Tests first (test-first gate)

- [x] 1.1 `tests/test_nfkc_fold.py` — the live case by name: the city case
  name for `11507018` (copy the exact string from the payload's
  `candidate_names`, which carries U+F9DD) reads BOTH tracks
  (`['事業計畫', '權利變換']`) after cleansing, not `['事業計畫']` alone.
- [x] 1.2 `tests/test_nfkc_fold.py` — the 6 corpus records (recnos 8, 121,
  179, 611, 613, 615, cleansed from fixtures carrying U+F901/F963/FA26) are
  UNCHANGED in track: each still derives its single track, and no corpus row
  changes track under folding (0 of 1,444 at the 2026-11-12 census).
- [x] 1.3 `tests/test_nfkc_fold.py` — the project count does not move:
  merging the cleansed corpus yields the same family count with and without
  the fold (the merge-scoring hazard). Run the merge over the fixture
  corpus both ways.
- [x] 1.4 `tests/test_nfkc_fold.py` — pin 4 of the E1 group: the live case
  is asserted by its name (the U+F9DD string present), not by a count — a
  corpus-only pass must not mask a live failure.
- [x] 1.5 `tests/test_nfkc_fold.py` — the 6 records parse to their identity
  after folding: `parse_name_id` returns
  `('北投區','桃源段四小段','424-8',15)`, `('信義區','三興段一小段','972',9)`,
  `('南港區','南港段三小段','274',16)` for the three pairs, and the land core
  becomes the folded one.
- [x] 1.6 `tests/test_nfkc_fold.py` — the 3 projects' portal links do not
  move: the view ids the payload carries for the 3 projects (view/793,
  view/791, view/253) are unaffected by the fold (a payload-level assertion
  over the current emission).

## 2. Implementation

- [x] 2.1 `urtpe/cleanse.py` — one NFKC fold at the cleansing boundary: the
  案名 is normalised on `cleanse()` entry, before every reader
  (`parse_name_id`, `_tracks`, the merge's inputs). `name_raw` stays
  verbatim. The comment cites this change and the D16d scope lesson.
- [x] 2.2 `urtpe/cleanse.py` — the folded 案名 is what `parse_name_id` and
  `_tracks` compare; no second normalisation site.

## 3. Verify

- [x] 3.1 `python -m pytest` — full suite green; the project count holds at
  680 / 1,444. *(1285 passed / 1 skipped)*
- [x] 3.2 `python scripts/probe_doc_figures.py` — the dashboard notes'
  figures still reproduce (failures: 0).
