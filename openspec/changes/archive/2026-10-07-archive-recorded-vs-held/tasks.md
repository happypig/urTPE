> Every task in group 1 is a test-writing task and every task in group 2 is an
> implementation task. Per `openspec/config.yaml`'s test-first gate, **all of group 1
> must be checked before group 2 begins**, and each test must be observed failing for the
> stated reason first — a test that passes before its implementation exists is not
> testing the change.

## 1. Tests (write and check first)

- [x] 1.1 `recorded_ids()` reports a publication the index records, whether or not its
      document is on disk; `index_ids_on_disk()` does not. Two tenses, two answers, from
      one archive whose index names four publications and whose disk holds three.
- [x] 1.2 A recorded-but-absent publication **still occupies its position**: with 08-11,
      08-20, 08-27 recorded and held but 09-24 recorded and *not* held, the predecessor of
      10-01 is `2026-09-24`, not `2026-08-27`. This is the exact substitution that produced
      the 41 phantom vanished rows on 2026-10-07.
- [x] 1.3 Reconciliation reports that the predecessor is recorded but not held, **names** it,
      and states no comparison was possible.
- [x] 1.4 Reconciliation does **not** fall back: `previous_total`, `current_total`,
      `net_change` and `new_approvals` carry no value derived from a non-adjacent
      publication, and `calendar_current` does not claim a change against the wrong
      predecessor.
- [x] 1.5 The two "no comparison" states are distinguishable — the recorded-but-not-held
      report names a publication; the never-recorded report does not. A reader must be able
      to tell "we hold nothing earlier" from "we recorded it and lost it".
- [x] 1.6 The absence reaches the **persisted** change set's `note`, so it survives the
      terminal, and reads back later without re-running the ingestion.
- [x] 1.7 An ingestion reports an indexed-but-missing member, and **still writes its
      output** — the gate must not halt on damage it cannot repair.
- [x] 1.8 An ingestion reports a member whose bytes were replaced (content differs from
      the indexed digest), naming the digest recorded and the digest found.
- [x] 1.9 An ingestion reports a document present with no index entry.
- [x] 1.10 An intact archive reports nothing — absence of a report is the ordinary case.
- [x] 1.11 An ordinary adjacent comparison is unaffected: predecessor recorded *and* held
      compares normally, and no absence language appears.
- [x] 1.12 `index_ids_on_disk()`, `publication_count()` and `newest()` keep their
      present-tense contracts. Guards against D1 being implemented by reinterpreting an
      existing accessor, which design.md rejects.

## 2. Implementation (after all of group 1 is checked)

- [x] 2.1 Add `recorded_ids()` to `GazetteArchive`, documented as history rather than
      presence. Its docstring must say which question it answers, since that distinction
      is the whole point of D1.
- [x] 2.2 `predecessor_of()` resolves from `recorded_ids()`. `index_ids_on_disk()` is
      untouched and keeps serving `verify()` and `archived_ids()`.
- [x] 2.3 `_ingest_pdf` distinguishes three predecessor states — never recorded,
      recorded-but-not-held, readable — and the middle one yields `comparable=False` with a
      note naming the publication. Reuse the existing `note` channel; no new field.
- [x] 2.4 Invoke `verify()` during ingestion and print its findings. Report only; do not
      block, per design.md D3.

## 3. Verification

- [x] 3.1 Full suite green. Refresh the collected count rather than carrying a stale one
      from `AGENTS.md`. → **653 collected, 652 passed, 1 skipped** (the deliberate skip at
      `tests/test_idempotent_flags.py:117`).
- [x] 3.2 Confirm the emitted dataset is unchanged: 1,439 records / 693 projects at
      `published_date 2026-10-01`, viewer equal to `data/`. This change carries reporting
      risk only — if a record count moved, something is wrong. → confirmed, `viewer ==
      data` byte-for-byte on projects.
- [x] 3.3 Confirm the 2026-10-01 change set still records `08-27 -> 10-01` with its 41
      vanished rows, i.e. this change did **not** silently rewrite history, and
      `2026-10-01.superseded-with-09-24.json` is still present as the record of the correct
      comparison. → confirmed: `08-27 -> 10-01`, vanished 41, `roc -> gregorian`; the
      superseded file is present.
- [x] 3.4 `python scripts\baseline_silent_failures.py` — items 1-4 still read 'no', item 5
      still reads 'yes'. → confirmed, item 5 with the D5 note intact.
- [x] 3.5 Append a dated entry to `docs/portal_operations_log.md` recording that the three
      fixes landed, and that they are preventive: the 2026-10-07 misattribution stands and
      is not repaired. → appended as §24.