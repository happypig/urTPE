# Tasks — no-silent-data-loss

## 0. Baseline measurement

- [x] 0.1 Record the baseline for each silent failure before fixing it, so each is
  shown to have been caught rather than merely asserted gone. Concretely: the count
  of emitted projects carrying an empty link set, the count of approvals carrying no
  link, the count carrying no implementation snapshot, the coverage guard's verdict on
  a synthetic total re-key, and the record count of a `1150827` ingest.
  — `scripts/baseline_silent_failures.py`, recorded before any fix:

  | # | measure | baseline | already fixed by hand? |
  |---|---|---|---|
  | 1 | projects with an empty link set | 0 of 709 | yes — restored by re-running with `--links` |
  | 1 | approvals carrying no link | 0 of 1422 | yes |
  | 1 | approvals with no implementation snapshot | 37 of 1422 | legitimate: the case payload is empty, which the spec permits |
  | 1 | projects with no implementation object | 18 | likewise |
  | 2 | unguarded `n.links` reads in the detail path | 0 | yes — guarded in the previous session |
  | 3 | header renders `統計至` | **no** | **not fixed** |
  | 4 | fault raised on wholesale orphan | **no** | **not fixed** |
  | 4 | can a total re-key pass the guard | **yes** | **not fixed** |
  | 5 | `--links` documented as | **recommended** | **not fixed** |
  | 6 | records excluded as source-truncated | **5** — 1141, 1198, 1204, 1210, 1381 | **not fixed** |
  | 6 | records emitted from `1150827` | 1422 | — |

  Items 1 and 2 read clean only because they were repaired by hand in the previous
  session. **Neither has a guard**, which is precisely why they regressed: a rebuild
  without `--links` re-broke item 1 silently, and the suite stayed green. Their rows
  here are the "before" that the new checks must make detectable.

## 1. Test-writing group — viewer contract

- [x] 1.1 Test: every field the viewer reads **unguarded** inside its detail renderer
  exists on every record, so a single record cannot blank the pane for all projects.
  **Written behaviourally, not by pattern-matching app.js.** A regex can only
  recognise the guard forms it already knows about and reported false positives on
  `if (!x.field) return`, ternaries and `?.`; instead each optional field is stripped
  from the real dataset and the render path is driven against it. Three tests, one per
  field, plus a targeted pin on the exact expression that blanked 709 panes.
  Passes: the guard applied when the previous regression was fixed holds.
- [x] 1.2 Test: a record lacking a link set still renders its project, omitting only
  the element that field feeds — passes. A 2-project fixture carrying `links: {}` and
  no `links` on any node renders both: header, 2 list entries, a 2,158-char detail pane
  and no throw. Also fixed the smoke harness, which asserted milestone badges
  unconditionally and so failed a fixture that correctly has none to render
- [x] 1.3  — **PASSES.** Header renders `709 個專案 / 1423 筆記錄 · 統計至 2026-08-27`. Two of my own assertions were wrong first and were corrected: the template is built by string concatenation so the label and the date are on different physical lines, and there are two `meta.textContent` assignments (the "not loaded" fallback and the real one)Test: the viewer header renders `統計至` alongside the ISO publication date,
  so the date cannot be read as a generation timestamp — **written, and failing against
  current behaviour, which is the defect.** Two assertions: the label is present, and it
  sits on the header line beside `published_date` rather than merely somewhere in the
  file; plus one that `index.html` does not hardcode it
- [x] 1.4 Fixture: a synthetic dataset whose records carry no link and no implementation
  fields, used to drive the degrade-not-blank assertions without depending on what the
  current emission happens to contain — `_bare_dataset()` in the test module, carrying
  `links: {}` because that is what a rebuild without link discovery actually produces

## 2. Test-writing group — emission report

- [x] 2.1 Test: a dataset in which every project has an empty link set is reported as a
  fault naming the fields and the affected count
- [x] 2.2 Test: a partially populated dataset reports both counts and is not called
  conforming because a majority is populated
- [x] 2.3 Test: a conforming dataset reports nothing on this account
- [x] 2.4 Test: the report names the step that did not attach the data, so the cause is
  identifiable from the output alone
- [x] 2.5 Test: a dataset with no implementation snapshot on any record or project is
  reported with both counts

## 3. Test-writing group — coverage guard

- [x] 3.1 Test: an identity set with no overlap before/after is reported as a total
  re-key, not as an absence of regressions
- [x] 3.2 Test: wholesale orphaning is a fault; an ordinary set of newly absent
  identities is reported separately from regressions on identities that survive
- [x] 3.3 Test: an unchanged identity set raises nothing and reports no re-key
- [x] 3.4 Test: the guard's total-re-key outcome and reconciliation's agree on the same
  run

## 4. Test-writing group — bounded completion

- [x] 4.1 Test: a truncated cell is completed when a candidate is in the same
  行政區 and 段/小段, begins with the truncated text, and brings the total to the
  案名's declared count
- [x] 4.2 Test: a candidate whose count does not close is refused and the discrepancy
  is reported
- [x] 4.3 Test: a candidate in a different 段/小段 is never used, even with an exact
  prefix match
- [x] 4.4 Test: a completion names the source gazette and 編號 in the run report
- [x] 4.5 Test: the 1210 case is refused — prefix match at J=0.984 with 62 parcels
  against a 案名 declaring 72 — pinned so the count check cannot be quietly relaxed
- [x] 4.6 Test: a cell holding every declared parcel but missing its closing phrase is
  still emitted with no completion attempted

Groups 2-4 are written and red by design: 2.x cannot import `urtpe.emission`, 3.x
fails on the absent `total_rekey`, 4.x cannot import `complete_truncated_cell`. Red is
the required precondition here — each test encodes a requirement no code implements yet.

## 5. Domain: viewer degrades

- [x] 5.1  — **already satisfied.** Every read of an optional field in the detail path was guarded when the previous regression was fixed; task 1.1 now proves it behaviourally rather than by assertion, so a reintroduction failsGuard every field read in `viewer/app.js`'s detail path, matching the
  convention the file already uses for 18 of its 19 reads
- [x] 5.2  — done in `viewer/app.js`, with a contract test pinning the label to the header assignmentRestore the `統計至` label to the header

## 6. Domain: emission report

- [x] 6.1  — done in `urtpe/emission.py`, `emission_faults`, naming the fields, the count and `--links` as the step that attaches themReport link-derived fields absent from an emitted dataset, with counts,
  naming the step that did not attach them
- [x] 6.2  — done: absent implementation and reward data reported with both countsReport absent implementation and reward fields with both counts
- [x] 6.3  — done, and **the spec scenario was corrected first**. Partial coverage is not a fault — the portals do not cover every project, and the real dataset has 7 of 709 without links. Reporting that as a fault would fire on every run and be ignored, which is the failure mode this change exists to remove. Partial coverage is now `emission_partial`, a count rather than a faultReport a partially populated field set as partial rather than conforming

## 7. Domain: coverage guard

- [x] 7.1  — done: `diff` returns `total_rekey` with both counts, and `coverage_guard` raises with an alert entry naming itReport zero-overlap as a total re-key with the before and after counts
- [x] 7.2  — done: wholesale orphan is a fault; a large ordinary loss stays informational, since a loss threshold would be a judgement about acceptable churnTreat wholesale orphaning as a fault; keep smaller losses informational
- [x] 7.3  — done and tested: a flag lost on a surviving identity and an identity that disappeared are reported as separate factsKeep newly absent identities distinct from regressions on surviving identities

## 8. Adapter: bounded completion

- [x] 8.1  — done in `extract.complete_truncated_cell`, cheapest disqualifier first. **The prefix check compares whitespace-normalised text**: 1150827 writes `332 、333` where 1151002 writes `332、333`, and comparing raw text refused a genuine continuation on spacing alone. Parcel containment is a separate check, so a candidate omitting an already-read parcel is still refusedImplement the three checks — same unit, literal prefix, count closes — against
  the corpus, in that order, so the cheapest disqualifier runs first
- [x] 8.2  — done: `CompletionResult` carries the source gazette and 編號, and `audit_entry()` renders one auditable lineEmit a completion record with the source gazette and 編號 alongside the data
- [x] 8.3  — done: `completed_count` and `completed_from` reach the extraction meta, and refusals carry their reasonReport completions and refusals with their reasons in the run report
- [x] 8.4  — unchanged and verified: reader faults still raise under `strict`, publisher faults still do notKeep the reader's own faults fatal and the publisher's non-fatal throughout

## 9. Acceptance

- [x] 9.1  — **PASSES.** 1423 records, 4 excluded, against the 1422/5 baselineRe-ingest `1150827` and confirm 1423 records with 4 excluded, against the
  1422/5 baseline
- [x] 9.2  — **PASSES.** 編號 1198 emitted with 110 parcels matching its 案名, sourced from 1151002 編號 1194; 編號 1210 still excludedConfirm 編號 1198 is present with 110 parcels and 編號 1210 remains excluded
  with its count discrepancy reported
- [x] 9.3  — **PASSES.** 709 entries, 528 stage badges, a 14,824-char detail pane, 12 sampled projects all rendering, header `709 個專案 / 1423 筆記錄 · 統計至 2026-08-27`Confirm the viewer header, the full left pane and a sampled set of detail
  panes all render, with construction-stage badges present
- [x] 9.4  — **PASSES.** `scripts/baseline_silent_failures.py` re-run: items 1-4 each read `no` for their failure line, item 5 reads `yes` because `--links` stays advisory by design with the emission check covering it. Two of the script's own detectors were wrong and were fixed — it probed for a raise on `d['lost']` rather than `total_rekey`, and it read the corpus-less record countRe-run the baseline from 0.1 and show each failure now caught
- [x] 9.5  — **PASSES.** 469 tests, `openspec validate --strict` cleanConfirm the full suite passes and `openspec validate --strict` is clean
- [x] 9.6  — remaining 4 exclusions and the 2 stranded cache directories recorded belowRecord the two remaining stranded cache directories and the 4 remaining
  exclusions as final, with their causes, so they are not rediscovered as new

## 10. Final dispositions

Recorded so they are not rediscovered as new (task 9.6).

**Four records remain excluded** from the `1150827` build, all because the publisher
truncated the 地號 cell at the row height and the remainder is not in the PDF:

| 編號 | unit | why no completion |
|---|---|---|
| 1141 | 南港段一小段720等105筆 | no candidate in the same 段/小段 shares a prefix |
| 1204 | 萬隆段二小段519等56筆 | no candidate shares a prefix (best J=0.35) |
| 1210 | 雙連段一小段197等72筆 | prefix matches and containment holds, but the candidate closes at 62 parcels against a 案名 declaring 72 — **neither publication holds the list** |
| 1381 | 長春段二小段559-5等83筆 | no candidate shares a prefix; the counts across publications disagree (83 / 81 / 80) |

**Two cache directories remain stranded**, both because their project's only record
is among those four: 南港區-南港段一小段-720地號等105筆 (編號 1141) and
文山區-萬隆段二小段-519地號等56筆 (編號 1204). No identity pairs them, so no alias is
possible; recovering them needs a portal re-scrape, which is out of scope here.

**編號 1198 was completed**, sourced from `1151002` 編號 1194. That source gazette is
the one excluded from the dataset for carrying 15 truncated cells of its own; using
it is defensible only because all three checks agree and the provenance is recorded
in the extraction meta as `completed_from`.
