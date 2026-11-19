# documentation-dataset-sync Specification

## Purpose
Keep measured, current-payload facts in the two bilingual documentation
pages synchronised with the emitted dataset, while preserving authored
explanations and the historical evidence they cite.
## Requirements
### Requirement: Documentation facts are derived from the whole current payload

The system SHALL provide scripts that synchronise `docs/etl_process.html`
and `docs/domain-model.html` from the emitted graph and its related local
artifacts. They SHALL derive every current-payload figure across the whole
payload, not a sample. Domain measurements SHALL reuse the existing
`probe_tab2_numbers.py` payload rules and the real viewer construction-chain
logic exercised by `probe_tab1_numbers.js`.

The ETL figures SHALL include the publication date, records, projects,
flagged nodes, live correction count, and relevant local artifact counts.
The domain figures SHALL include all current measurements in §2, §4 and §5
that those probes can derive. Each figure SHALL retain a machine-readable
field identity. Re-running with unchanged inputs SHALL leave unchanged
content byte-identical apart from an explicit generation timestamp.

#### Scenario: The current gazette has moved

- **WHEN** the emitted payload has a new publication date or new counts
- **THEN** both documentation pages state the new current-payload figures
- **AND** no figure is copied from a previous payload without re-derivation

#### Scenario: Every record is included in the measurement

- **WHEN** a payload-derived ratio or count is rendered
- **THEN** its numerator and denominator are measured over the full payload
- **AND** the source population is stated beside the measurement

#### Scenario: Synchronisation is repeatable

- **WHEN** either script runs twice without a changed input
- **THEN** the second run makes no content change other than a permitted
  generation timestamp

### Requirement: Authored prose and historical examples remain distinguishable

The scripts SHALL update only explicitly marked measured regions. Authored
prose, bilingual span pairings, page structure, historical examples and
historical defect measurements SHALL remain intact. A historical value
SHALL NOT be presented as a current-payload measurement. Current figures
SHALL be labelled with their payload date and measurement date.

A required marked region that is missing or ambiguous SHALL cause a
non-zero result rather than a guessed replacement. Both English and zh_TW
renderings of a measured region SHALL be updated together. The scripts
SHALL NOT use an external documentation service or add a runtime dependency
to the self-contained pages.

#### Scenario: Historical evidence remains visible

- **WHEN** a section compares an older defective payload with the current
  payload
- **THEN** the older measurements remain identified by their original date
- **AND** the current measurements are separately derived and dated

#### Scenario: A marker is missing

- **WHEN** a required field has no unambiguous marked destination
- **THEN** the script stops without claiming synchronisation succeeded

#### Scenario: Both languages stay paired

- **WHEN** a measured bilingual region changes
- **THEN** its English and zh_TW values agree
- **AND** the existing language switch and no-script rendering still work

### Requirement: Documentation synchronisation is independently checkable

The system SHALL provide a check mode that reports stale documentation
without writing it. The check SHALL fail when a current marked figure
disagrees with the payload or a required measurement cannot be produced.
Offline tests SHALL cover successful generation, stale-content detection,
missing markers and repeatability without requiring network access.

#### Scenario: Documentation is current

- **WHEN** check mode runs after successful synchronisation
- **THEN** it exits successfully and names the verified payload date

#### Scenario: Documentation is stale

- **WHEN** a current marked figure is manually changed away from its derived
  value
- **THEN** check mode exits non-zero and names the stale field
