# Proposal: nfkc-fold-compat-ideographs

## Why

CJK compatibility ideographs are distinct byte sequences that render as the
same character. The data carries four, measured on the 680-project payload
(`docs/inspection-batchE.md` E1, re-verified 2026-11-12):

| Codepoint | Character | Where | Count |
| --- | --- | --- | --- |
| U+F901 | 更 | 6 corpus 案名 (`name`/`name_raw`) | 6 rows |
| U+F963 | 北 | 6 corpus 案名 | (same 6 rows) |
| U+FA26 | 都 | 6 corpus 案名 | (same 6 rows) |
| U+F9DD | 利 | one city case name, `11507018` | 1 case |

Two readers break:

1. **The track reader, live.** `_tracks()` (`urtpe/cleanse.py:239`) matches
   the keyword 權利變換 as a literal substring. The city's live case name for
   `11507018` (大安區-復興段三小段-3地號等2筆) writes 利 as U+F9DD **inside**
   權利變換 (index 32 of 38), so the case reads 事業計畫 alone and loses its
   權利變換 track.
2. **`parse_name_id()`, latent.** (`urtpe/cleanse.py:31`) returns
   `('', '', '', None)` for all 6 corpus records, because the regex cannot
   match a compatibility 北 or 都. The 3 projects' own land core is empty
   today; their portal links came from the cached view pages (view/793,
   view/791, view/253), so nothing visible breaks.

**The fix: one `unicodedata.normalize("NFKC", name)` at the cleansing
boundary.** NFKC folds U+F9DD → U+5229 (利), U+F963 → U+5317 (北),
U+FA26 → U+90FD (都), U+F901 → U+66F4 (更). Verified by the batch-D probes
(`scripts/probe_nfkc_effect.py`, `probe_compat_name_id.py`): it makes
`parse_name_id()` succeed on all 6 and restores `_tracks()` on the live case.

**The two hazards the tests must hold** (measured, batch D D16a–D16d):

- The fold changes what the merge's similarity scoring compares, so it can
  join or split a family. The project count must not move. There is one
  count: `urtpe/models.py:80` defines `Project` as the merged family, and
  the emitted count is `len(graphs)` at `urtpe/graph.py:188` — 680 is the
  family count and the project count at once.
- A corpus-only test would pass while the live bug survived: the corpus's
  six characters sit in text no keyword touches (no track keyword carries a
  compatibility ideograph); the live character sits inside one. The
  difference is **where the character sits**, not which character it is.

Scope guard (batch D D16d): a scope is a claim about what was not measured.
Six corrections were made while measuring this finding. If a re-measure
during this change shows a third reader, measure it before widening.

## What Changes

- `urtpe/cleanse.py` — one NFKC normalisation at the cleansing boundary,
  applied to every name the module reads (the 案名 on `cleanse()` entry, so
  every downstream reader sees the folded form). The raw form stays in
  `name_raw` (the PDF's untouched text; the raw column is verbatim by
  contract).
- Tests pin six things (the E1 test-first group, verbatim from
  `docs/DashboardNUXUI.md` §11.3): the live case reads both tracks after
  folding; the 6 corpus records are unchanged in track; the project count
  does not move; the live case is checked by name, not by count; the 6
  records parse to their identity after folding and the 3 projects' land
  core becomes the folded one; the 3 projects' portal links do not move.

## Capabilities

### Modified Capabilities

- `data-cleansing`: the normalization requirement gains the NFKC fold —
  compatibility ideographs fold to their unified forms at the cleansing
  boundary, before any keyword comparison; `name_raw` stays verbatim.

## Impact

- Code: `urtpe/cleanse.py` (the fold), `tests/test_nfkc_fold.py` (new, the
  six pins).
- Payload: no count moves (pinned by test 3). The 6 corpus records' land
  cores become non-empty (pinned by test 5); the live case's track gains
  權利變換 on the next re-emit of the city's case name (the case name lives
  in the link cache, re-read on the next `--links` refresh — the corpus's
  own emission is unchanged until then).
- Not touched: the merge rule, the similarity weights, the link discovery,
  the viewer.
