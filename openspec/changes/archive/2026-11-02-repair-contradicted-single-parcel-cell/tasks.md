# tasks — repair-contradicted-single-parcel-cell

## 1. Test-writing group (red first; all checked before any implementation task)

- [x] 1.1 `tests/test_cleanse.py` addition: the 759 shape — a record whose
      案名 is `擬訂臺北市內湖區文德段二小段615地號1筆土地都市更新事業計畫案`
      and whose 地號 cell is `臺北市內湖區文德段二小段 1 地號1筆土地`
      cleanses with `parcels == ['615']`, `first_parcel == '615'`, an
      `auto_fix` entry `地號欄單筆地號與案名矛盾→依案名`, and a review flag
      quoting the printed cell. RED: the rule does not exist (parcels stay
      `['1']`).
- [x] 1.2 `tests/test_cleanse.py` additions: the negative shapes stay as
      published — (a) the cross-section shape (中正段一小段 446-1 +
      中正段三小段 21…82-9, recno 269) keeps its multi-parcel list; (b) the
      merge-history shape (`518地號1筆(原15筆)`, recno 957) keeps its
      absorbed list; (c) an agreeing single-count cell emits no auto_fix
      and no flag; (d) a multi-count 案名 (`等4筆`) with a
      first-token mismatch is untouched; (e) an unparseable 案名 is
      untouched; (f) **generalization** — a future PDF with the same typo
      shape on different numbers (大橋段 77 vs printed 9) fires the rule
      (maintainer requirement: the rule is structural, not keyed to 615).
      Group verified red via 1.1's failure; (a)–(e) pass today and must
      stay green through implementation.
- [x] 1.3 `tests/test_merge.py` addition (acceptance): with the 759 record
      repaired by cleansing, `merge.score(536, 759) >= 0.7` and a full
      merge places recno 759 in the same family as 84/314/536 with
      `project_id == '內湖區-文德段二小段-615地號等1筆'` — the `-2` twin
      does not form. Uses `CleanRecord`s built from the real clean.tsv
      shapes (the 0.65 → 0.95 path). RED until 1.1's rule exists.

## 2. Implementation (after group 1 is fully checked)

- [x] 2.1 `urtpe/cleanse.py`: in `cleanse()`, after the parcel derivation
      block — when `land_count == 1` from the 案名 (`nc == 1`), the cell
      yielded exactly one parcel, and it differs from `np` (the named
      parcel): set `parcels = [np]`, append the auto_fix and the review
      flag (design D1/D2). The flag text quotes the printed cell.
- [x] 2.2 Run the full suite; confirm 1.1–1.3 green and no other test
      moved (the corpus census predicts zero other firings, so no fixture
      anywhere carries the contradiction shape). 803 passed / 1 skipped
      (was 796 — +7 from this change); smoke passes.

## 3. Acceptance

- [x] 3.1 Full suite green (803 passed / 1 deliberate skip); smoke passes
      (`node scripts/viewer_smoke.js`).
- [x] 3.2 Corpus check, 2026-11-02, full run over the held 2026-10-15
      gazette (`--links --recover-truncated`, exit 0): 1,442 records, **693
      projects (was 694)**. Diff of `merged.tsv` against HEAD: no record
      added or removed, **exactly one project_id changed** — recno 759,
      `內湖區-文德段二小段-615地號等1筆-2` → `內湖區-文德段二小段-615地號等1筆`.
      The family holds 84/314/536/759; the `-2` twin is absent from
      merged.tsv and the payload. clean.tsv carries 759's `parcels=615`,
      the auto_fix and the flag (`地號欄印1，案名為615`); review_report.txt
      lists both lines. A first run without `--recover-truncated` emitted
      1,438 records / 690 projects — the standing emission is the recovered
      one, so that run was discarded and redone with the flag.
- [x] 3.3 Viewer re-emitted; the payload carries the main project with the
      2019 node (case 10410272 anchored) and no twin; smoke passes. The
      orphaned twin cache dir holds the same four cases and the same twur
      page as the main cache, so it is redundant. It stays on disk (AGENTS.md:
      do not delete caches casually). `scripts/build_project_aliases.py`
      recorded one `exact` alias (former `-2` → current) in
      `data/project_aliases.json`; 0 ambiguous, 0 unmatched.
- [x] 3.4 Acceptance recorded in the ops log (§35) and the `inspection.md`
      suite row (803 passed, 1 skipped, 804 collected).
