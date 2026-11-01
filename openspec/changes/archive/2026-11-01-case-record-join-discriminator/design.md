# Design — case-record-join-discriminator

## Context

Three fields carry case ids; two spellings exist for one id space; one live
payload shows recovery choosing a subset of the discovery candidates under an
`ambiguous-zone` flag. The payload evidence (measured 2026-11-01):
recno 188 `recovery.cases=["R089213-02"]`, `api_cases=["10403071"]`;
recno 1005 `recovery.cases=["09610235","09610236"]` inside
`links.taipei=[09610231,33,34,35,36,37]`.

## Goals / Non-Goals

Goals:

1. A pure normalisation function with tests pinning both spellings.
2. A precedence function the joining consumers call; provenance travels.
3. No rewrite of stored data.

Non-Goals:

- Rewriting the viewer's `app.js` in this change (the pipeline-side functions
  land first; the viewer adoption is a following commit in the same wave — the
  normaliser is mirrored client-side if JS needs it, else the pipeline pre-joins).
- Changing what recovery chooses (that rule is `truncated-row-recovery`'s).

## Decisions

### D1 — New module `urtpe/case_join.py`, two pure functions

`normalise_case_id(raw) -> str` (R-form → numeric base; numeric → itself) and
`join_case_ids(recovery_cases, api_cases, links_taipei) -> JoinResult` carrying
`anchored` (the precedence winner), `candidates` (the discovery set), and
`ambiguous` (the flag). Pure logic per the domain/adapter split; the alternative
(a section in `links.py`) buries a domain rule in the largest adapter.

### D2 — R-form → numeric is a documented transformation, not a guess

`docs/urotpe_api.md` §4 records the pairing (`R089213-02` is application 02 of
registry case `089213`). The normaliser strips the `R` prefix and the `-NN`
suffix; a bare `R089213` (no suffix) normalises to `089213`. Any id matching
neither shape returns unchanged — normalisation never destroys an id it does not
recognise.

### D3 — Precedence is recovery-first *for anchoring*, with the candidate set preserved

The four checks (identity, date, containment, count) make recovery's binding the
only verified one. `links.taipei` remains the family's candidate set — the join
result carries both, so a consumer needing breadth (badge tooltips) and one
needing the verified anchor (milestone anchoring) read different fields of the
same result instead of guessing.

## Risks / Trade-offs

- **A consumer that already reads `links.taipei` for anchoring changes
  behaviour.** That is the point (G1); the change's tests pin the new result
  shape, and the payload's only affected record is 1005 (both recovery cases are
  already in the discovery set, so no tooltip disappears).

## Open Questions

(none)
