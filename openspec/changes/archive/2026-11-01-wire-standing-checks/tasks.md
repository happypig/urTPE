# tasks — wire-standing-checks

## 1. Test-writing group (red first; all checked before any implementation task)

- [x] 1.1 `tests/test_census_gate.py`: (a) green path — a clean/partition pair
      with every record in exactly one family passes `Tripwire.check_partition`
      with no faults; (b) lost record — a clean record absent from all families
      yields a fault naming the recno; (c) double-counted record — a recno in two
      families yields a fault naming the recno and both project_ids; (d) count
      disagreement — `doc.counts.records != len(clean)` yields a fault; (e) the
      census is pure — no file I/O in the check.
- [x] 1.2 `tests/test_emission_wiring.py`: (a) a `_run_locked`-level test where
      `build_graph_document` returns projects with no link data — the fault text
      appears in the run report and on the console, and the run still exits 0;
      (b) the same run with link data reports no emission fault; (c) partial
      coverage (some projects linked, some not) reports a count, not a fault.
      Wire through the CLI on a fixture gazette with a stubbed/no-network links
      path, using a temp archive (conftest).

## 2. Implementation — census gate (after group 1 is fully checked)

- [x] 2.1 `urtpe/tripwire.py`: add `check_partition(clean, projects)` returning
      the faults list per 1.1's four cases; pure, no I/O.
- [x] 2.2 `urtpe/cli.py` `_ingest_pdf`: after the final ledger re-merge (and
      before `result` is returned), run the census; faults join the tripwire
      faults so the exit-4 contract applies. The tripwire result's report
      includes the census faults.

## 3. Implementation — emission wiring (after group 1 is fully checked)

- [x] 3.1 `urtpe/cli.py` `_run_locked`: after `build_graph_document`, call
      `emission_mod.emission_faults(doc["projects"])`; print faults to stderr and
      pass them into `report_mod.review_report` (new `emission=` parameter) so
      `review_report.txt` carries them.
- [x] 3.2 `urtpe/report.py`: accept and render the `emission` faults section
      (additive text after the existing sections).

## 4. Acceptance

- [x] 4.1 Full suite green (including groups 1-3's tests); the flag-less-path
      golden bytes (if any pin emission format) unchanged apart from the additive
      report section.
- [x] 4.2 Run the CLI once on the 10-15 gazette without `--links` into a scratch
      outdir: the report carries the wholesale-absence fault, exit 0, and the
      live `data/`+viewer are untouched (scratch outdir).
- [x] 4.3 `openspec validate` passes; both boards updated; commit.

---

Completed 2026-11-01 (commit `b6b112b`): all items above verified before the
archive moved. 4.1: 720 passed / 1 skipped at the time (the recovery-acceptance
golden re-captured to carry the additive [EMISSION] section, per the delta's
"additive text" clause). 4.2: the scratch run printed both [EMISSION] faults and
exited 0; `data/` and the live viewer untouched by the run itself (the viewer
side effect that DID leak into `b6b112b` was caught by the viewer-contract tests
and restored from `a90c2a1` in `9e553f1` — recorded there, not here, because it
was Wave 3's fix). 4.3: validate passed; both boards updated in the same commit.
