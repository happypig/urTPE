## Context

Link layer only, beside PDF → … → projects.json (+ viewer). Actors: the
platform's case header and data2, the refresh script, the link cache, the
viewer's 相關連結 note. The pure rule `find_superseding_case` is the only
decision that moves.

## Goals / Non-Goals

**Goals:** match a re-filed case whose later steps were re-run; keep every
refusal guard that is not about dates; make the looser match auditable.

**Non-Goals:** fuzzy name matching; matching across projects; changing which
projects are selected.

## Decisions

### D1 — Application dates are the identity of a filing

The application date is when the implementer filed; a re-filing restates it
and re-runs the steps after it (exhibition, committee, review). So the `無`
case's application dates (`_APPLICATION_FIELDS`, those it carries, ≥ 1) must
all equal the candidate's. Name equality, a greater id, ≥ 3 dated labels and
exactly one candidate still apply.

### D2 — The report names what differs

`find_superseding_case` returns `(succ, why, differs)` where `differs` lists the
`無` case's dated labels the successor does not share; the refresh puts it in
the `superseded` entry and the script prints it. The cache stores only
`superseded_by` (no shape change).

## Risks / Trade-offs

- [Two filings with the same name and application date that are different
  units] → several candidates → ambiguous, nothing recorded; across projects is
  out of reach by construction (same-project only).
- [A match on application dates hides a real data difference] → every
  differing label is printed in the run report.
