# Tasks — twur-manual-override

The `rules` block asks for a POC on PDF parsing and similarity calibration. Neither applies:
no PDF is read, nothing is merged, and the identity question is settled by a person who read
the portal's own page title. Evidence quoted in `design.md`.

## 1. Tests (written first, deliberately failing)

- [x] 1.1 **PASSES.** `load_project_cache` returns view id 18 with its url.Test that a recorded link is applied when a project has none
- [x] 1.2 **PASSES.** A discovered view id of 999 survives; a discovered id with an empty url keeps its own (empty) url rather than borrowing the record's.Test that a recorded link does NOT displace a discovered one
- [x] 1.3 **PASSES.** A record of only `twur_view_id` is ignored.Test that a record without evidence is refused and reported
- [x] 1.4 **PASSES.** `twur_url`, `portal_title`, `verified_on` and `reason` each independently required.Test that the table loads from the same location search as the alias table
- [x] 1.5 **PASSES.** Checked in `cache_dir.parent` then `cache_dir`, mirroring `load_alias_table`.Test that a record naming an unknown project is reported, not silently retained
- [x] 1.6 **PASSES.** Reports orphans; a record naming a known project reports nothing.Test that an unreadable or malformed table degrades to no overrides rather than raising
- [x] 1.7 **PASSES.** Asserts the shipped entry's evidence fields are non-empty.Test that the shipped table's entry carries its evidence fields

## 2. Implementation

- [x] 2.1 **PASSES.** `load_twur_overrides` with the same lookup and per-root caching.`links.load_twur_overrides()`, mirroring `load_alias_table`'s lookup and caching
- [x] 2.2 **PASSES.** Applied only inside `if not result.twur_view_id`.Apply in `load_project_cache`, only where `twur_view_id` is absent
- [x] 2.3 **PASSES.** Incomplete records are dropped with a `[WARN]` naming the missing fields.Refuse records lacking evidence, and report them
- [x] 2.4 **DONE.** One entry, with the portal title verbatim and the two independent causes spelled out.`data/twur_overrides.json` with one entry, evidence included
- [x] 2.5 **DONE.** `!data/twur_overrides.json` beside the alias table's, with a note on why it is not regenerable.`.gitignore` exception, beside the alias table's

## 3. Acquisition and emission

- [x] 3.1 **DONE.** `view/18` fetched; 7 national milestones and city case id `09112120` extracted by the sweep's own extractors.Fetch `view/18` and parse milestones and case ids through the sweep's existing extractors
- [x] 3.2 **DONE.** Written through `update_project_cache`, so the entry is shaped like every other one rather than hand-assembled.Write the cache entry via `update_project_cache`, so it is shaped like every other
- [x] 3.3 **DONE.** Ledger entry cleared; 75 to 74 entries.The project's ledger entry clears
- [x] 3.4 **DONE.** Coverage moved 634 to 635 of 709, and exactly one project gained a link with none lost.Regenerate the viewer and confirm coverage moves 634 → 635

## 4. Documentation

- [x] 4.1 **DONE.** The override table, its gap-fill rule, and the reason the parcel test was not loosened.`docs/cli_flow_v2.md` records the override table, its gap-fill rule, and why the parcel test was not loosened
- [x] 4.2 **DONE.** The population measurement is in the table's `reason` and in `design.md`, so an n=1 decision can be revisited on a second case.The one-entry population measurement is recorded, so the n=1 decision can be revisited on a second data point

## 5. Acceptance

- [x] 5.1 **PASSES.** 580 tests, `validate --specs --strict` 21/21, `validate twur-manual-override --strict` clean.Full suite green; `openspec validate twur-manual-override --strict` clean
- [x] 5.2 **PASSES.** The project renders its portal link and its milestones.The project renders its portal link in the viewer
- [x] 5.3 **PARTIAL.** Verified at the data level: 709 projects before and after, project order identical, +1 twur, -0 twur. NOT verifiable in the committed file — see below.No other project's link state changed
## 6. Why the emitted files are NOT in this commit

Task 5.3 passed on the data but the emitted files are deliberately excluded, because
verifying them turned up a defect that has nothing to do with this change.

**The `--from-js` emission is nondeterministic.** Two consecutive runs of the same input
produce 257 differing project payloads. `nodes[0]` flips between recnos, which cascades
into `edges` and `member_recnos`; some `implementation` values change with it. HEAD's own
committed viewer file does not reproduce either.

The obvious cause was tested and **ruled out**: pinning `PYTHONHASHSEED=12345` still gives
250 differences, so it is not set or dict iteration order. The ingestion path itself *is*
deterministic — two full runs produced byte-identical `member_recnos` — so the variance is
in the emission path specifically.

Committing a viewer file that cannot be reproduced would fold known churn into history and
train reviewers to ignore diffs in the project's primary artifact. So this commit carries
the code, the table, the tests and the spec only. The data and viewer state on disk reflect
the override and are correct; they are simply not committed here.

The nondeterminism is tracked separately.
