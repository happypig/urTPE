## Context

The correction ledger (`urtpe/ledger.py`, spec `correction-ledger`) was built
for manual fixes keyed on content (normalized land cell + ISO approval date) and
applied after cleansing, before merge. It has never held an entry. Two facts
block its first real use (`docs/inspection-batchD.md` D5):

1. 吉林676's 編號 1303 prints `676地號1筆` for an 18-parcel unit. With a
   `land_count` correction the pair 1303 ↔ 1347 scores
   .35 (section) + .2 (first parcel) + .3 × 1/18 (Jaccard) + .1 (count) = 0.667,
   still below `LINK_THRESHOLD` 0.7. The only field-level ways past the threshold
   are a parcel list (absent data — not publishable by inference) or a shared
   `named_anchor` (a field that means 原…基地/國宅 and is emitted — misuse).
2. `--ledger` defaults to `None` (`urtpe/cli.py:613`), and the ledger block in
   `_ingest_pdf` (`urtpe/cli.py:379-386`) runs only when a path is given.

`--from-js` rebuilds load families as emitted (`_load_projects_from_js`) and never
re-merge, so any correction applied at a PDF ingest persists through them.

## Goals / Non-Goals

**Goals:**
- A person can answer a §6.8 merge-candidate flag with one ledger entry.
- Every PDF ingest applies the ledger unless the operator points elsewhere.
- Merge 吉林676 (1303 ↔ 1347) with family name `…676地號等18筆`.

**Non-Goals:**
- No change to the similarity rule, weights or thresholds.
- No "split" entry (forcing two records apart). Not needed yet.
- No ledger application on `--from-js` (families are kept as emitted).
- No parcel-list correction field.

## Decisions

### D1 — `confirm_merge` is a separate entry kind, not a field correction

A field correction sets one attribute on one record; a confirmation relates two
records and sets nothing. Encoding it as a field (e.g. a synthetic
`named_anchor`) would leak into the payload and into the land-core semantics.

Shape (one JSONL line, same file, same append-only and supersede rules):

```json
{"match_land_core": "<1303 land, normalized>", "match_iso_date": "2010-03-25",
 "field": "", "to": null, "confirm_merge": true,
 "with_land_core": "<1347 land, normalized>", "with_iso_date": "2008-12-31",
 "why": "...", "by": "...", "at": "..."}
```

`Correction` gains `confirm_merge: bool = False`, `with_land_core: str = ""`,
`with_iso_date: str = ""`; `__post_init__` accepts an empty `field` when
`confirm_merge` is set (as it already does for `accept_removal`) and rejects a
confirmation with an empty `with_*` key. `describe()` names both keys so the
supersede-by-description mechanism keeps working.

Alternative rejected: a separate `merges.jsonl`. Same author, same keys, same
history rules — one ledger keeps one report and one isolation path in tests.

### D2 — `apply()` resolves confirmations to recno pairs; `merge()` unions them first

`CorrectionLedger.apply()` already walks the clean records with `key_of`. It
additionally returns `confirmed_pairs: list[tuple[int, int]]` on
`LedgerOutcome` — the recnos of both sides when each key matches exactly one
record. A key matching no record makes the confirmation unmatched (reported, no
link). A key matching 2+ records (a land cell + date printed twice) is reported
unmatched as ambiguous rather than guessed.

`merge(records, confirmed_pairs=())` passes the pairs into `_clusters`, which
calls `union(a, b)` for each pair before scoring the candidate pairs. Recnos are
valid within one ingestion, which is the only scope the pairs live in — they are
derived from content keys on every run, never stored.

Alternative rejected: make `score()` return 1.0 for a confirmed pair. The pair
may not even be a candidate pair (`_candidates` buckets by district+section), and
a scorer that reads the ledger couples a pure function to I/O.

### D3 — `--ledger` defaults to `DEFAULT_LEDGER_PATH`

`argparse` default becomes `str(ledger_mod.DEFAULT_LEDGER_PATH)`, which already
honours `URTPE_LEDGER`. The `if ledger_path:` guard stays (an explicit empty
string still opts out, for the rare forensic run). An absent file yields an empty
outcome; `report()` prints `manual corrections applied: 0` — the spec's "Ledger is
empty" scenario. Tests are safe: `tests/conftest.py` sets `URTPE_LEDGER` into the
session temp dir at configure time, before `urtpe.ledger` is imported, and its
isolation fixture asserts nothing escapes.

The re-merge at `urtpe/cli.py:385` already re-runs `merge` after `apply`; it
gains the `confirmed_pairs` argument.

### D4 — The first two entries are written by a dated, append-only call

The entries for 吉林676 are appended with `CorrectionLedger.append` from a
one-shot command in the task list (keys copied from `data/clean.tsv` of the
current gazette and checked to match exactly one record each). Both entries cite
D5 of the inspection board. `by` is the user's git name (`happypig`).

## Risks / Trade-offs

- [The live ledger now applies to every ingest] → An entry that turns out wrong
  affects every run until superseded. Mitigation: the run report names every
  applied entry; supersede rather than edit.
- [Coverage guard on the vanished `…等1筆` identity] → The family's
  `.link_cache` directory `中山區-吉林段四小段-676地號等1筆` becomes stranded; the
  guard may flag a dropped project. Mitigation: run the ingest, read the guard's
  output; a stranded dir for a merged family is the expected shape (the
  `stranded_report.py` / `project_aliases.json` path), not a bypass case.
- [~23 MB tracked diff] → The ingest rewrites `data/*.tsv`, `projects.json`,
  `viewer/projects.data.js`. Mitigation: diff the emitted dataset against the
  previous one before staging; expect exactly one family fewer (682 → 681) and no
  other identity change.
- [Ambiguous key] → `normalize_land` + date may match two records. Mitigation:
  D2 reports it unmatched; the two keys used here were checked unique.

## Migration Plan

1. Land code + tests (test-first).
2. Append the two entries to `urtpe-gazettes/corrections.jsonl`.
3. Re-ingest the newest archived gazette with `--links` (cache-backed) under the
   single-writer lock; read the ledger and coverage reports.
4. Verify: 681 projects; `…676地號等18筆` holds 1303 + 1347; no
   `片段家族合併候選` flag on either; no other project_id changed.
Rollback: append a superseding entry and re-ingest; or restore the tracked
`data/` files from git.

## Open Questions

None blocking. (Whether to add a "split" entry later is out of scope.)
