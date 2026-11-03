## Context

`docs/viewer-UX.md` §3 (§3 execution events) and §4 (§4 orphan nodes), both design-settled (2026-11-03), P3, openspec change D (wave 5). Wave 2 (callout gutter) is done; its overlap guard in scripts/viewer_smoke.js runs on all 676 callout projects and passes (0 failures). Wave 5 needs that guard to prove its layout changes add no collision.

The viewer pipeline flow: `projects.json` -> `renderDetail` -> SVG with tracks (columns 1–3), events (column 4), node labels, callout gutter (§1), execution events interleaved by date, orphan virtual nodes.

## Goals / Non-Goals

**Goals:**
- §3: execution events start ½ node row (32px) under the nearest approval node directly above them in any swimlane; date order wins; event→approval keeps full 64px clearance.
- §4: every named orphan takes its own timeline row by date; shifts 32px right when in a track column; dotted edge (new class `edge orphan`) to nearest recno node in time; nameless 孤 anchors follow the same rule (by date, nearest recno node column, 32px right shift, dotted edge); the right-most ghost column is removed.
- §1 overlap guard extended to cover orphan rects + dotted edges, runs on every project with callouts or orphans.

**Non-Goals:**
- No pipeline change; `projects.json` / `projects.data.js` unchanged.
- Virtual-node ordering, stage clustering, and the ½-pitch semantics between non-event rows are unchanged (only approval→event pitch changes).

## Decisions

### A. §3 — ½ node row between approval and following event

In `renderDetail` row pitch: `rowAcc += t.kind === "approval" ? NODE_ROW : EVENT_ROW` stays for event→approval, but when an approval is immediately followed by an event, advance `NODE_ROW / 2` (32px) instead of `NODE_ROW`. Equivalent: compute pitch based on the pair (previous row, current row) — approval→event = 32, otherwise normal.

Implementation: in the `timeline.forEach` that builds `rowYs`, look at `(prev, current)`: if `prev.kind === "approval" && current.kind === "event"`, pitch = NODE_ROW / 2 = 32; else approval→approval = NODE_ROW, event→anything = EVENT_ROW (32), and event→approval = NODE_ROW (64).

### B. §4 — orphan placement by date + dotted edge + 32px right shift

Named orphans (already virtual nodes in the grid by track): keep their column (trackPosition), take their own row by date in the timeline (they already flow through `allMembers`/`timeline` via `clusterOfStage`... actually virtual nodes flow through `allMembers` which sorts by case_id, not date — need to verify). Per §4 decision 1, every node/orphan has its own timeline row by date. The existing `timeline` interleave sorts `allMembers` by effectiveCaseKey (case_id attempt order), not date — that's the D12 ordering. §4 decision 1 says orphan rows are in date order with recno nodes.

Simplest conforming approach consistent with D12: orphans already enter `allMembers` and thus `timeline`; their `date` is `g.node_date`. For undated orphans, D12 puts them after their stage's dated members. The row pitch (decision A) applies uniformly.

For the dotted edge: from each orphan (virtual node) to the nearest recno node in time — the recno node directly above it, or directly under it when the orphan is earlier than every recno node. Draw as `line class="edge orphan"` (dotted style in CSS).

32px right shift: when the orphan's column holds a track line (colOf not at the event column), shift its node x by NODE_ROW / 2 = 32px right. Track this shifted x in `pos` so label rects and edges use it.

### C. Nameless 孤 anchors

Remove `interimOrphans`/`ghostPosRaw`/`ghostColX`/`ghostRows` machinery. Nameless orphans follow §4 decision 4: they take their date row in the column of the nearest recno node in time, shifted 32px right, with a dotted edge to that node. But nameless orphans have no date, stage, or track — per §4 the corpus has no legitimate nameless anchor (the 3 are §8 defects). After §8 they're removed from data anyway. For safety: if a nameless orphan has no node_date, skip rendering it (keep the §8-cleaned invariant).

Actually, per §4 decision 4: "The current corpus has no legitimate nameless anchor (the 3 above are §8 defects), so this rule applies to future cases only." So in the current data, nameless orphans exist (3) but are §8 defects to be removed by wave 3b. For wave 5, we keep rendering nameless orphans the same way as named ones IF they have a date; otherwise they don't get a row. Given they lack node_date, they won't render. That's acceptable — wave 3b removes them.

### D. Spec deltas

viewer-graph-layout/spec.md: replace the Callout placement requirement's "canvas-extension fallback" language with gutter (already done by wave 2 — wave 2 archived its spec deltas). For wave 5, add scenarios:
- Execution dates start ½ node row under the nearest approval node directly above them (new scenario under Content-addressed row pitch).
- Orphan nodes take their own timeline row by date with dotted edge to nearest recno node (new scenario, or under orphan-case-anchoring).

orphan-case-anchoring/spec.md: update "Viewer renders orphan ghost node with dotted construction-chain edges" requirement to say placement by date + dotted edge to nearest recno node + 32px right shift; remove ghost-column language.

## Risks / Trade-offs

- Label boxes include badge strip footprint (already true per wave 2).
- Event labels can reach the node column at 32px vertical distance — the §1 overlap guard includes both boxes (check 1 covers all rects).
- The dotted edge style must not be confused with `event-link.dashed` (cross-source transition) or `edge.virtual` (chain). Use `.edge.orphan` with its own dash pattern.

## Test writing (test-first gate)

Per AGENTS.md / openspec config, test-writing tasks come before implementation. The viewer smoke guard is the test-writing group (Node checks in scripts/viewer_smoke.js, not pytest). No `> POC:` hatch needed — the change has a test-writing group.

Test-writing tasks:
- T1: extend smoke guard rect sources to include orphan virtual-node label rects + nameless-orphan rects (shifted 32px).
- T2: add smoke check that orphan dotted edges exist for each orphan → nearest recno node (verify the line is drawn with class edge orphan).
- T3: extend overlap guard (check 1) to run on every project with orphans (named or nameless), not just callouts.
- T4: confirm checks fail on 北投區-關渡段二小段-303地號等5筆 with current layout (orphan on track line, no dotted edge).
- T5: pytest viewer labels/structural tests still pass.

Implementation tasks:
- I1: §3 row pitch change (approval→event = 32px).
- I2: §4 named orphan dotted edge + 32px right shift + remove ghost column.
- I3: §4 nameless orphan by-date placement rule (no date → no row).
- I4: CSS `.edge.orphan` dotted style.
- I5: smoke guard updates.

Verification:
- V1: `node scripts/viewer_smoke.js` passes (guard on callouts + orphans).
- V2: `python -m pytest` passes.
- V3: manual: 336 events sit 32px under node 370; 303 orphan "(未核定) 變更 [自行撤回]" 32px right of 權利變換 track with dotted edge.
