## ADDED Requirements

### Requirement: Classify ledger negatives by case outcome (never-approved vs recoverable)

A ledger negative (a project the strict title matcher could not match) SHALL be classified by the outcome of its own Taipei cases via `get_project168_top.ashx` (`phase`/`NAME`): a project whose every case is 本府駁回 / 實施者自行撤回 / 業已失效 SHALL be marked **never-approved** — the national portal will never list it — and excluded from future re-probe waves (liveness policy). Projects with at least one 業經本府核定 case SHALL be marked **recoverable** (the portal page should exist; the identity connection failed) and re-enter the targeted queue.

#### Scenario: Lapsed-概要 units are marked never-approved
- **WHEN** a twur-less project's only case is phase-A `事業概要階段─事業概要業已失效`
- **THEN** the ledger entry is annotated `never-approved` and excluded from TTL re-probes

#### Scenario: Approved-case units re-enter the queue
- **WHEN** a twur-less project carries a case with `業經本府核定` (e.g. 梨和段二小段261-4, 11409012)
- **THEN** the ledger entry is annotated `recoverable` and re-enters the targeted queue with the case's own 案名 fragments as search keys

#### Scenario: Corpus classification is measurable
- **WHEN** the classification runs over the twur-less population (2026-08-29 baseline: 71 = 15 never-approved · 17 has-approved · 33 mixed/other · 6 no-cases)
- **THEN** the counts are reportable per class so the remaining twur-less tail is explained, not just counted
