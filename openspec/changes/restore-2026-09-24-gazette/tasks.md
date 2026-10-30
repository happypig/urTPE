# tasks — restore-2026-09-24-gazette

User approval gates: tasks 4.x and 5.x write to the live archive and re-emit
`data/` + `viewer/projects.data.js` (~23 MB diff). The maintainer approves before 4.1
runs. Nothing before group 4 touches the live archive (conftest repoints it).

## 1. Test-writing group — boundary regression + superseded digests (red first)

- [x] 1.1 Write `tests/test_page_head_boundary.py`: the fixture-level boundary test —
      `write_gazette(..., repeat_header_row=True, calendar="gregorian")` over a lineage
      mixing ROC rows with a Gregorian newest row; assert through the reader that every
      編號 is read exactly once (the head dropped because its 編號 duplicates a read
      record, never by position), every date parses ISO, and contiguity 1..N holds so the
      tripwire passes. Include the negative guard: with the head row made *unique*
      (appearing nowhere else), the reader must emit it — pinning content-dedup against
      the v2 positional-skip regression.
- [x] 1.2 Write the quarantined-file acceptance test (skipped unless the archive holds
      the quarantined path; conftest repoints the archive root): reader on
      `skipped since abnormal SN\核定案件-2026-10-02.pdf` yields 統計至 2026-09-24,
      Gregorian, 1,681 raw rows / 1,436 distinct, 編號 1..1436 contiguous, 22 named
      exclusions, zero duplicate 編號 after dedup.
- [x] 1.3 Write `tests/test_superseded_digests.py`: (a) `store()` over a held
      `gazette_id` with different bytes appends an entry naming `supersedes: <old-sha>`
      and the new `sha256`; (b) `verify()` reports no damage when the held member matches
      a digest a later entry supersedes, and still reports damage when no such entry
      exists; (c) the index stays append-only across a re-store.
- [x] 1.4 Write the change-set repair test: restoring a publication between two ingested
      ones moves `predecessor_of` for the successor; the re-derived change set names the
      restored predecessor; the old change-set file is superseded (renamed, content
      preserved); exactly one live change set per transition remains. Run against a
      temp archive built from fixtures, never the live one.
      Note: red on `ChangeSetStore.all()` — it globs `*.json`, so superseded files
      currently leak into consumers' listings; the implementation must skip them.

## 2. Superseded-digest implementation (P3.7) — after group 1 is green-checked

- [x] 2.1 `urtpe/archive.py` `store()`: on same-`gazette_id` content change, append the
      re-store entry (`event: "re-store"`, `supersedes: <old-sha>`) before replacing the
      file; identical bytes remain a no-op.
- [x] 2.2 `urtpe/archive.py` `verify()`: accept a held member whose content matches any
      digest that a later entry for the same `gazette_id` names as superseded; report the
      mismatch otherwise, as today.
- [x] 2.3 Run group 1's tests green; run the full suite; note any noise change in
      `verify()` output on the live archive (expected: none — no re-store has happened
      there yet). Full suite 700 passed, 1 skipped; one existing test
      (`test_archive_verify_detects_a_member_swapped_for_another`) updated to the new
      contract — a recorded re-store is accepted, an undocumented substitution still
      reported. Live-archive `verify()` now reports 1 problem (10-13 unindexed); 10-30
      was removed from the archive root by the OpenCode session mid-session (digest held
      under 10-15; not this change's doing). Also fixed en route (red from task 1.4):
      `ChangeSetStore.all()` now skips superseded files, so consumers never read a
      superseded change set as live.

## 3. Re-filing support (adapter) — after group 1 is green-checked

- [x] 3.1 Add `GazetteArchive.refile_from_quarantine(quarantine_path, gazette_id)`:
      copy-out under the publication name, refuse when the digest matches nothing
      previously recorded, return the new index entry carrying `restored_from` provenance.
      No deletion of the quarantine file.
- [x] 3.2 Test 3.1 against a temp archive: digest-matched candidate is re-filed and
      indexed with provenance; a digest-unmatched candidate is refused with a report.
      (`tests/test_refile_quarantine.py`, 5 tests: re-file+provenance, two refusal
      paths, verify-after-refile, idempotent re-file. IndexEntry gained the
      `restored_from` field; `supersedes` already added by task 2.1.)

## 4. The restoration act — USER APPROVAL REQUIRED before running

- [ ] 4.1 Re-file the quarantined PDF as `核定案件-2026-09-24.pdf` (task 3.1 path);
      verify the index entry's digest equals the poller's `5066b108…` record.
- [ ] 4.2 Ingest 09-24 under the single-writer lock with `--recover-truncated`:
      reconcile against 08-27 (calendar change ROC→Gregorian reported, not blocking);
      tripwire PASS with 1,436 records / 692 projects; the 22 residuals recovered or
      named; the change set 08-27→09-24 written.
- [ ] 4.3 Re-ingest 10-01 under the lock: its change set re-derives against 09-24;
      cross-check the new 09-24→10-01 counts against the 2026-10-07 superseded file
      (+4/0/0 expected; a divergence is documented in the change-set note, not
      force-matched); supersede the live `2026-10-01.json` to
      `2026-10-01.superseded-pre-09-24-restore.json` (content preserved).
- [ ] 4.4 Verify the chain: exactly one live change set per transition
      (08-11, 08-20, 08-27, 09-24, 10-01, 10-06, 10-15); `predecessor_of` correct for
      every link; `verify()` reports the three benign unindexed re-uploads and nothing
      new.

## 5. Docs correction

- [ ] 5.1 Correct `AGENTS.md:105`: the calendar boundary is 2026-08-27 → 2026-09-24;
      note the 1151002 label as the quarantine artifact; cite this change.
- [ ] 5.2 Correct `openspec/config.yaml:18` the same way (it currently names 1151002
      while giving the 09-24 date).
- [ ] 5.3 Record in `docs/inspection.md` that the restoration ran, with the final counts
      and the change-set cross-check result.
- [ ] 5.4 `openspec validate` the change; archive with its spec deltas.

## 6. Forward re-emission — 10-06/10-15 re-ingested (USER APPROVED 2026-10-30)

Approval recorded in design.md Open Questions. Runs only after group 4 completes:
the forward re-emission's value (1005 completing from print) exists only once 09-24
is in the corpus. Each run takes the single-writer lock; ~23 MB emission diff expected
across the two runs together (projects.json + viewer/projects.data.js + the tracked
TSVs).

- [ ] 6.1 Re-ingest 2026-10-06 under the lock (`python -m urtpe.cli
      urtpe-gazettes\核定案件-2026-10-06.pdf -o data --links --recover-truncated`):
      tripwire PASS; the corpus now includes 09-24, so 雙園段二小段505-class truncated
      cells complete from print; reconcile against 09-24 (calendar both Gregorian);
      change set 09-24→10-06 re-derived and the previous file superseded
      (`*.superseded-pre-09-24-restore.json`).
- [ ] 6.2 Re-ingest 2026-10-15 under the lock (same flags): tripwire PASS; 編號 1005's
      雙園段505 row emits with 77 parcels from print (verify in raw.tsv/merged.tsv);
      the recovery provenance for 1005 changes from API-partial to print-complete —
      record which of the recovery-four (188/1005/1131/1206) still need the API pass
      and which closed from print; change set 10-06→10-15 re-derived, previous
      superseded.
- [ ] 6.3 Refresh the viewer + tracked outputs: confirm `viewer/projects.data.js`
      carries the 77-parcel list for the 雙園段505 unit and that
      `node scripts\viewer_smoke.js` still passes; review the ~23 MB diff and stage
      deliberately (projects.json, raw.tsv, clean.tsv, merged.tsv, review_report.txt,
      viewer/projects.data.js).
- [ ] 6.4 Cross-check the record↔project partition is unchanged except for the
      completed rows (no new merges, no lost families — the census assertion from
      audit Appendix A: partition total, disjoint, counts match).
- [ ] 6.5 Append the outcome to `docs/portal_operations_log.md` (append-only; new
      sessions append at the bottom): the restoration, the forward re-emission, and
      1005's provenance change, so the citation chain stays resolvable.
