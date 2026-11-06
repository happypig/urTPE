## 1. Test-writing group — the gates (domain)

- [x] 1.1 `tests/test_emission_completeness.py` — the rebuild path refuses a document whose nodes do not sum to its own record count (exit 4)
- [x] 1.2 the rebuild path refuses a document that lost a record **and** had its count rewritten, using the output tree's `clean.tsv` as the reference (exit 4)
- [x] 1.3 the rebuild path accepts a complete document and emits it
- [x] 1.4 the rebuild path names the missing record in its report
- [x] 1.5 the rebuild path refuses a document whose family lost its anchor record, and does not fail with an unhandled error
- [x] 1.6 the census gate compares against the emitted family set, and reports the count the payload carries
- [x] 1.7 the badge/flag check: a record with no case id and no flag is reported
- [x] 1.8 the badge/flag check: a record with a case id and the stale flag is reported
- [x] 1.9 the badge/flag check: a record with no case id and the flag is not a fault
- [x] 1.10 the badge/flag check: a project discovery never reached is not a fault

## 2. Test-writing group — the proof (adapter)

- [x] 2.1 `scripts/probe_three_coverage_proofs.py` re-derives the partition from the emitted files and states whether it is total and disjoint
- [x] 2.2 the proof names a record it cannot account for, rather than counting it
- [x] 2.3 the proof answers the three coverage questions: projects not in the lists, recno in no project, records without a badge

## 3. Implementation — the partition gate (domain)

- [x] 3.1 `Tripwire.check_emitted_partition` — the payload-document partition check: the count against the nodes, each family's member list against that family's nodes, each family's anchor against that family's nodes
- [x] 3.2 `Tripwire.check_emitted_partition` — the `clean.tsv` reference, naming the records the payload lost and the records it holds that the reference does not
- [x] 3.3 the check is pure: it takes a document and returns strings, with no filesystem access of its own

## 4. Implementation — the wiring (adapter)

- [x] 4.1 `urtpe/cli.py` — the rebuild path gates on the document before the loader rebuilds it, and refuses with exit 4
- [x] 4.2 `urtpe/cli.py` — `_reference_recnos` reads the output tree's `clean.tsv`, and returns nothing when the file is absent
- [x] 4.3 `urtpe/cli.py` — `_read_payload_document` reads the document as it is on disk, and the loader reuses it
- [x] 4.4 `urtpe/cli.py` — the ledger runs before the census gate and before the tripwire report, so both speak about the emitted family set
- [x] 4.5 the reconciler still compares against the post-ledger family set, and the identity comparison is unchanged

## 5. Implementation — the badge/flag check (domain)

- [x] 5.1 `urtpe/emission.py` — `_badge_flag_faults` reports a record with no case id and no flag, and a record with a case id and the stale flag
- [x] 5.2 the check applies only to a project link discovery reached — the project's own link set is the proxy
- [x] 5.3 the check is a warning under the existing emission-fault contract, and does not refuse the run

## 6. Verification

- [x] 6.1 the full suite passes (`python -m pytest`)
- [x] 6.2 the re-emit of the real payload succeeds and the payload is byte-identical before and after
- [x] 6.3 the three corruption shapes are refused with exit 4 on the real corpus, each naming the lost record
- [x] 6.4 the viewer smoke test passes (`node scripts/viewer_smoke.js`)
- [x] 6.5 the baseline silent-failure script reads its expected values

## 7. Documentation

- [x] 7.1 `docs/inspection-batchD.md` — D18, the three questions answered and the two gates that did not hold, with the measured numbers
- [x] 7.2 `docs/inspection-batchD.md` — the board header names the findings and the fix
