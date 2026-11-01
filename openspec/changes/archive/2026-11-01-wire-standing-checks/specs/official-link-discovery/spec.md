# official-link-discovery Delta

## ADDED Requirements

### Requirement: Every emission path runs the emission-fault check

The pipeline's emission path SHALL call the emission-fault check
(`urtpe.emission.emission_faults`) on the projects of the document it is about to
write, after link data would have been attached and before any artifact is
written. Wholesale absence of link data (no project carrying any link field)
SHALL be reported as a fault naming the fields, the counts, and the run step that
attaches them; partial coverage SHALL NOT be raised as a fault. The check SHALL
report through the run report and the console. The check is a warning: it SHALL
NOT refuse the run, because `--links` is advisory by design (D5).

#### Scenario: A run without --links still reports the missing link data

- **WHEN** a run completes without link discovery and every project carries no
  link field
- **THEN** the run reports the wholesale-absence fault, naming the fields and the
  step that attaches them
- **AND** the report appears in `review_report.txt` and on the console
- **AND** the run exits 0 — the report is a warning, not a refusal

#### Scenario: A run with link data reports no emission fault

- **WHEN** a run completes with link discovery and at least one project carries a
  link field
- **THEN** no wholesale-absence fault is reported
- **AND** partial coverage (some projects without portal records) is reported,
  if at all, as a count rather than a fault
