## Why

Two live observations in the shipped payload make case-id joins unreliable, and a
third is one API-outage away:

1. **No precedence rule (G1).** recno 1005's `recovery.cases` selected
   `["09610235","09610236"]` (with `ambiguous-zone: true`) while `links.taipei`
   joins the graph on **six** case ids — both recovery cases among them plus
   09610231/33/34/37. The sets overlap; the problem is that recovery *chose 2 of
   6* with no recorded rule for which wins when a downstream consumer needs one.
   Any consumer that takes "the case id" from either field without a precedence
   rule may attach the wrong milestone timeline.
2. **Two id spaces in one field (G2).** `recovery.cases` holds R-form ids
   (`R089213-02` on recno 188 — back in the payload since the API-healthy
   re-run) alongside numeric ids (1005/1206); `api_cases` and `links.taipei` are
   consistently numeric. The same case can appear as `R089213-02` and `089213`
   (`docs/urotpe_api.md` §4: the R-form is the application-attempt form; the
   numeric is the registry form). A join keyed on the raw string misses the pair.

The maintainers affected: every consumer of `recovery.cases`, `api_cases`, and
`links.taipei` — the viewer's badge tooltips, the milestone anchoring, and any
future case-record join.

## What Changes

- A documented **precedence rule** for case-id joins: when `recovery.cases` and
  `links.taipei` disagree on which case anchors a record, the recovery choice
  wins (it is the four-check-verified binding); `links.taipei` supplies the
  broader candidate set. `ambiguous-zone` marks the choice as made under
  ambiguity — it is provenance, not a tiebreak.
- **Id-space normalisation**: a `case_id` normalisation function (R-form →
  numeric base: `R089213-02` → `089213`) applied before any join keyed on case
  id; raw spellings preserved in the fields, joins on the normalised form.
- Both rules test-first; the recovery provenance stays verbatim.

## Capabilities

### New Capabilities

- `case-record-join`: the precedence and normalisation rules for joining case
  ids across `recovery.cases`, `api_cases`, and `links.taipei`.

### Modified Capabilities

(none — the joining consumers are specified under this new capability; the
existing `truncated-row-recovery` and `orphan-case-anchoring` requirements are
unchanged)

## Impact

- New `urtpe/case_join.py` (pure logic: normalise + precedence), or a section in
  `urtpe/links.py` — decided in design.
- Consumers that join on case ids adopt the normaliser (the viewer's
  `buildCaseIndex` in `app.js` is the first; pipeline-side consumers follow).
- No emission-format change: the fields stay verbatim; the rules govern *reads*.
