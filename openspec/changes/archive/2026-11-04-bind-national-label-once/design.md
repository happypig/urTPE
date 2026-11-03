## Context

`nationalBoundTo(node, national)` scores one node against all labels
(viewer/app.js:130). Multi-candidate labels badge every candidate: the label
chooses nobody, so 16 nodes wear an unearned 國 (C1, measured 2026-11-03 at
`370ddb2`).

## Goals / Non-Goals

**Goals:**
- One binding decision per label, made once per project: label → at most one
  recno.
- Exact date, then ±1 day, then nothing (2+ survivors after a step bind
  nothing).
- The 國 badge renders only on a bound node or a view-verified node.

**Non-Goals:**
- No change to which labels are harvested or to `view_verified_case_ids`.
- Far drift on a single candidate is not a binding bug (42 labels ≥120 days;
  a review flag, later).

## Decisions

### 1. Bind per label, not per node

`bindNationalLabels(project)` groups recno nodes by (stage, track) once, then
for each national approval label (nationalLabelKey): candidates = nodes of that
stage+track; if 1 → bound; if more → exact-date survivors (1 → bound, 2+ →
unbound); else ±1-day survivors (1 → bound, 2+ → unbound). Returns
{recno: [labels]}.

### 2. ±1 day is a spec change

The tie-break tolerance enters the delta (the archived 國-badge requirement
says "date tie-break" with no window). 17 of the 19 multi-candidate labels
bind under ±1 day; exact-only binds 10.

### 3. One 國 per node

A node both bound and view-verified renders exactly one 國 badge (unchanged).
