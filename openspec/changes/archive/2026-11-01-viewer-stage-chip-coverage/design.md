# Design — viewer-stage-chip-coverage

## Context

Three render-path findings share one file (`viewer/app.js`) and one test surface
(`node scripts/viewer_smoke.js` + structural tests). The payload measured:
195 cards without a chip, of which the `case_schedules` data explains most
(59 審查中, 130 自行撤回); raw JSON in three table columns; three date formats
in one pane.

## Goals / Non-Goals

Goals:

1. The grey status chip per the delta (審查中 / 撤回), derived from
   `case_schedules`.
2. Human-readable table cells (prose lists, em dashes).
3. ISO dates at display time.
4. The payload unchanged — all rules are display-time.

Non-Goals:

- Changing `neverApproved` (verified correct; untouched).
- Changing the stage filter (its three options are construction stages; a grey
  status chip is not a construction stage and is correctly excluded from that
  filter's derivation).
- Touching the badge colours of the three construction stages.

## Decisions

### D1 — The status chip derives from `case_schedules` with a clear precedence

`statusChip(p)`: if `constructionStage(p)` returns a stage, no status chip (the
construction badge wins — it is the later fact). Else if any schedule is 審查中 →
`審查中`. Else if any schedule is 自行撤回/已駁回/已失效 → `撤回`. Else nothing.
Precedence 審查中 over 撤回: a family with one live application is not
"withdrawn" even if an earlier one was.

### D2 — Cell formatting is a small render helper, applied at cell-write time

`fmtCell(value)`: list → `、`-join; empty list/dict/null/undefined → `—`;
string → as-is. Applied in the table's column renderer for the three affected
columns and any future free-text column. The date conversion is a separate
`fmtDate(text)` handling the three observed input forms; applied at every
date-render site in the detail pane.

### D3 — The ROC conversion uses the existing calendar rule

`toISO`-equivalent client-side: `100.12.20` → year+1911 → `2011-12-20`. The
same rule as `urtpe/extract.to_iso` (< 1911 ⇒ ROC), reimplemented client-side
(the viewer is a `file://` page with no Python).

## Risks / Trade-offs

- **A grey chip on 195 cards changes the list's look.** That is the finding; the
  smoke test's sampled renders assert the pane still fills.
- **The 撤回 chip lumps 自行撤回/已駁回/已失效.** Two characters cannot carry
  three states; the tooltip (V11's accessible-name fix, still on the watch
  list) is where the detail belongs. Recorded as a deliberate simplification.

## Open Questions

(none)
