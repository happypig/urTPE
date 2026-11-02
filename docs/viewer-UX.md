# Viewer UX improvements

A backlog of planned improvements to the static viewer (`viewer/app.js`, `viewer/app.css`).
Each entry records the problem, the evidence, the chosen design, its trade-offs, and the
spec and test impact. An entry is a candidate, not a change: start an openspec change
(`openspec/changes/<name>/`) before you implement it, and link the change here.

Append new entries at the bottom. Do not renumber entries; other documents may cite them
as `viewer-UX §N`.

| § | Title | Priority | Form | Status |
| --- | --- | --- | --- | --- |
| 1 | Callout gutter: no-overlap implementation callouts | P2 | openspec change A | design settled |
| 2 | 國 badges and national edges bind to the recno node they name | P1 | openspec change C | design settled |
| 3 | Execution events start ½ node row under the nearest node | P3 | openspec change D | design settled |
| 4 | Orphan nodes join the timeline with a dotted edge | P3 | openspec change D | design settled |
| 5 | Center the graph in the panel | P3 | direct `fix:` commit | ready |
| 6 | Remove the 事業種類 legend item and track edges | P3 | openspec change A | ready |
| 7 | Show [無] / [NA] for a case with no 目前辦理情形 | P1 | openspec change B | design settled |
| 8 | A view-verified case must belong to the project | P1 | openspec change E | design settled (1 default to confirm) |

**Priority.** P1: the graph tells the reader something false (a wrong case state, a
national link the portal does not assert). P2: the graph hides data (a box covers a
label). P3: layout and polish; the reader can still read every fact.

**Form.** A direct `fix:` commit when the change makes the viewer match its current
spec. An openspec change when it changes a spec requirement or scenario, or touches the
pipeline.

## Execution order

Execute top to bottom. Each wave names its entries, its form, and its gate. No wave has an
open user decision (2026-11-03). Waves 3, 3b and 4 are P1
and may run before wave 2, but wave 3b must run before wave 4. Wave 5 must run after
wave 2, because it needs the overlap guard.

### Wave 1 — direct `fix:` commit (no gate)

- **§5 Center the graph.** The purpose line of `viewer-graph-layout` already says
  "centered", so this is a bug fix, not a behavior change. Verify with
  `node scripts\viewer_smoke.js` and the 336 project by hand. Do it first: wave 2
  then adds the gutter to a content width that is already centered.

### Wave 2 — openspec change A: `callout-gutter` (§1 + §6)

- **§1** callout gutter, content-sized boxes, overlap guard; **§6** remove the
  事業種類 legend item and the drawn `track` edges.
- Why together: both edit `renderDetail` and its CSS, and both change graph
  scenarios (`viewer-graph-layout` callout requirement; `history-graph/spec.md:60`
  "a track or section edge passes behind a node label"). One run of the new overlap
  guard covers both.
- Gate: the test-first group is the new smoke checks (§1 decision 5). Before the
  proposal, count the nodes that join their family only through a `track` edge (§6
  risk).

### Wave 3 — openspec change B: `show-no-state-case-status` (§7) — ready

- Pipeline + viewer: refresh the caches that lack `case_headers`, keep 無 as a state,
  render it. Reverses supersede-headerless-cases D1.
- Gate: none left (§7 decisions 1–4). Task order and commits are in §7 decision 4.

### Wave 3b — openspec change E: `reject-foreign-view-cases` (§8) — ready

- Pipeline: a view-verified case id must match the project (the 相關連結 label and the
  city's own case name). Rejected ids are named, not dropped silently. Then refresh and
  re-emit, as in §7 decision 4.
- Why before wave 4: §2 decision 2 trusts `view_verified_case_ids`; 5 of 186 ids name
  another project. It also removes the 3 nameless 孤 anchors that §4 asks about.
- Gate: none blocking (§8 decisions 1–2). Open question 3 has a stated default.

### Wave 4 — openspec change C: `bind-national-badge-to-named-node` (§2) — ready

- Viewer only: a national approval label binds to the recno node with the same stage
  and track (§2 decision 1); the 現況 rule goes. Changes the 國 badge rules in
  `history-graph`.
- Gate: none left (§2 decisions 1–3).

### Wave 5 — openspec change D: `place-events-and-orphans-by-node` (§3 + §4) — ready after wave 2

- Event pitch under the nearest node; orphans placed by their nearest recno node with
  a dotted edge.
- Why together: both change row geometry and the column model in
  `viewer-graph-layout`, and both need the wave 2 overlap guard to show they add no
  collision. Run it after wave 2.
- Gate: wave 2 done (the overlap guard). §3 and §4 are settled.

### Decisions waiting on the user

| Entry | Questions | Blocks |
| --- | --- | --- |
| ~~§7~~ | all four answered 2026-11-03 — see §7 decisions 1–4 | ~~wave 3~~ unblocked |
| ~~§2~~ | answered 2026-11-03 — see §2 decisions 1–3 | ~~wave 4~~ unblocked |
| ~~§3~~ | answered 2026-11-03 — see §3 decisions 1–2 | — |
| ~~§8~~ | answered 2026-11-03 — see §8 decisions 1–2; question 3 has a default | ~~wave 3b~~ unblocked |
| ~~§4~~ | answered 2026-11-03 — see §4 decision 4 | — |

### Watch, do not fix

- The overlap guard checks estimated rects, not real rendering (§1 C). If a browser
  shows an overlap the guard missed, fix the width helper, not the guard threshold.
- `node scripts\viewer_smoke.js` runs by hand only. Run it after every wave.

---

## §1 Callout gutter: no-overlap implementation callouts

**Status:** design settled (2026-11-03). P2, openspec change A (wave 2). **Scope:**
`viewer/app.js` (`renderDetail`: the callout placement block after `// Callout placement`
and the stage-band block after `// §5.2.6 stage-cluster bands`), `.impl-callout*` and
`.stage-band*` in `viewer/app.css`, `scripts/viewer_smoke.js`. No pipeline run: `data/`
and `viewer/projects.data.js` do not change.

### Problem

Implementation callouts (實施方式 / 基地面積 / 原戶數 / 使用分區) overlap the graph.
Seen on 大安區-通化段四小段-336地號等26筆 (3 records): the first callout covers the
label of its own node, "3 · 2022-08-02 擬訂 [施工中]".

The current placer tries 8 fixed spots around the node, takes the first one that does
not hit an obstacle, and extends the canvas downward when all 8 hit. Four gaps let
overlaps through:

1. The callout's own node is not an obstacle. `nodeRects` filters on
   `n.recno !== ownRecno`, so the placer never protects that node's label.
2. The clamp into the viewBox moves a candidate onto that node. For a node in the first
   row, the "above-left" spot has a negative `y`. The clamp moves it to `y = 4`, on top of
   the node, and gap 1 lets the spot pass.
3. The label width is estimated too small. `headLen * 6.5` sizes every character as
   Latin. CJK glyphs at 11px are about 11px wide, and `headLen` does not include
   `schedTxt` ("[施工中]") or the area suffix.
4. Lines are not obstacles. The track lines, the event edges, and the callout tails can
   cross a box, and nothing checks them.

Gaps 1–3 can be fixed one by one, but each fix removes candidate spots and sends more
callouts to the fallback at the bottom of the canvas. Gap 4 needs segment–rect tests and
tuned weights. This entry removes the cause instead: callouts move out of the graph area.

### Evidence from the dataset (2026-11-03)

Measured on `viewer/projects.data.js` at `30612dd`:

- 676 projects have at least one record with implementation data. The highest count is
  7 records, on 內湖區-潭美段四小段-579-2地號等21筆 (distribution 1: 259, 2: 218,
  3: 120, 4: 52, 5: 15, 6: 11, 7: 1). Callouts are a subset: the first carrying record
  plus each record with a changed value.
- A 4-row callout is 62px high (`rows × 14 + 6`). The pitch between two approval rows
  is 64px (`NODE_ROW`).
- The longest implementation value is 26 characters:
  敦化南北路特定專用區(A區)(原屬第四之一種住宅區), about 260px at 10px. A 160px gutter
  holds about 13 CJK value characters on one line. 99% of all 36,298 implementation
  values have 14 characters or fewer.
- `scripts/viewer_smoke.js` renders a stride sample of 12 projects, not the full list.
- The stage-band chip is drawn at `x = PAD - 36`, inside the planned gutter.

### Decisions (2026-11-03)

1. **Long values wrap to at most 2 lines, then cut.** A value wraps inside its box. A
   value that needs more than 2 lines is cut with an ellipsis on line 2, and the full
   value is in a `title` tooltip.
2. **Stage bands and their count chips are removed from the graph.** The chip collides
   with the gutter, and the band adds a second visual layer behind the tracks. Stage
   clustering stays: it still decides row order and the (未核定) tag on undated members.
   Only the drawn band (`<g class="stage-band">`) and its chip
   (`變更(第四次) · 4 案 · 1 未核定`) go.
3. **The overlap guard checks boxes, not lines.** Callout boxes, node labels, badge
   strips, event rows and ghost anchors must not intersect each other. A leader may
   cross a track line or an edge (a leader from a node in column 2 or later must cross
   the column-1 track). A leader must not cross a callout box or a node label.
4. **Stacked boxes keep a 2px gap.** Two adjacent 4-row callouts then need 64px, equal
   to the row pitch, so they do not drift. Only wrapped boxes (decision 1) push the
   boxes below them down.
5. **The new smoke checks are the test-writing group for the test-first gate.** They are
   Node checks in `scripts/viewer_smoke.js`, not pytest cases. `AGENTS.md` keeps the
   harness outside pytest on purpose, so the change adds no pytest wrapper and does not
   use `> POC:`. Write the checks first and confirm they fail on the current layout:
   大安區-通化段四小段-336地號等26筆 must fail. The overlap check runs on every project
   that has a callout, not on the 12-project sample.
6. **Deploy verification runs after the user pushes.** Acceptance item 4 needs the change
   on GitHub Pages. The agent does not push; the user pushes and then runs
   `python scripts\check_deploy.py`.

### Design

#### A. Dedicated callout gutter

- Reserve a column (`CALLOUT_GUTTER`, at most 160px) to the left of the leftmost track
  column. Draw only callouts in it. Shift all tracks, event columns and ghost anchors
  right by the gutter width. Reserve the gutter only when the project has at least one
  callout.
- Give each callout a target `y` equal to its node's `y` minus half the box height.
- Do one top-to-bottom sweep over the callouts in timeline order. If a box would overlap
  the box above it, move it down to `previous.y + previous.h + 2`. Never move a box up.
- Extend `svgH` to the bottom of the last box.
- Replace the tail polygon with a leader from the right edge of the box to the node
  circle. Keep the `.callout-tail` color so the leader reads as part of the box.
- Remove the 8-spot search, the `hitsAny` tests against node, event and ghost rects, and
  the canvas-extension fallback. The gutter makes them unnecessary.
- Remove the stage-band drawing (`bandHtml`) and the `.stage-band` / `.stage-band-chip`
  CSS rules (decision 2). Keep the cluster computation that orders rows.

#### B. Size the box from its content

- Compute `w` from the longest row: label width + gap + value width + padding. Use the
  same per-character width helper as in C (CJK ≈ 10px at 10px font, ASCII ≈ 6px).
- Clamp `w` to `[CALLOUT_MIN_W, CALLOUT_GUTTER - margin]`. Set the gutter width from the
  widest box in the project, up to the clamp.
- Compute the line count of each value at the clamped width, capped at 2. Compute `h`
  from the total line count, so the sweep in A and the guard in C use the real height.
- Style `.impl-callout-row b` to wrap at 2 lines and cut the rest
  (`display: -webkit-box; -webkit-line-clamp: 2; overflow: hidden`), and put the full
  value in a `title` attribute.

#### C. Overlap guard in the smoke test

- Move the rect geometry into one helper, `layoutRects(p)`, that returns every placed
  rect: callout boxes, node label boxes (circle + title + sub line + badge strip), event
  rows, and ghost anchors, plus each callout's leader segment. `renderDetail` and
  `scripts/viewer_smoke.js` use the same helper, so the test checks the geometry the
  renderer uses.
- Check 1: no two rects intersect. Name the project and the two rects on failure.
- Check 2: every callout box lies fully inside the gutter.
- Check 3: no leader segment crosses a callout box other than its own, or any node label
  box (decision 3).
- Run checks 1–3 on every project that has a callout (decision 5), and name
  大安區-通化段四小段-336地號等26筆 and 內湖區-潭美段四小段-579-2地號等21筆 (7 carrying
  records) explicitly in the output.

### Pros and cons

| | Pros | Cons |
| --- | --- | --- |
| A. Gutter | Overlap cannot happen by construction: nothing else is drawn in the gutter. Predictable: all boxes on one side, in time order. Simpler code (one sweep replaces the search and the fallback). Easy to test. | Each project with a callout gets up to 160px wider, so narrow screens zoom out more. Wrapped boxes push the boxes below them down, and those leaders get long and slanted. Removing the stage band loses the "N 案" count at a glance. Visible layout change, so it needs spec deltas. |
| B. Content width | Values cannot spill out of a box. Most values show in full; only values longer than 2 lines are cut. Short boxes keep the gutter narrow. | Widths and line counts are estimates; the real width depends on the font. A cut value is visible in full only in the tooltip. |
| C. Smoke guard | Turns "no overlap" into a rule a script can check, on the full dataset. Catches regressions from later viewer entries too. | Checks estimated rects, not real rendering. `node scripts\viewer_smoke.js` runs by hand only (no CI), so it protects nothing unless someone runs it after a viewer change. |

### Alternatives not chosen

- **Make the own node an obstacle, and measure label width per character.** Small, and it
  fixes the screenshot. Rejected as the main fix because every extra obstacle removes
  candidate spots and sends more callouts to the bottom-of-canvas fallback, far from
  their node.
- **Score every candidate spot (overlap area + line crossings + distance).** Better
  results than first-fit, but more logic, tuned weights, and still no guarantee on dense
  projects.
- **Cut long values to 1 line.** Keeps every box at a fixed height, but hides text such
  as "(原屬第四之一種住宅區)" for every long 使用分區 value.
- **Keep the stage band and move its chip right of the gutter.** Keeps the count, but
  the chip then competes with node labels in the track area and needs its own collision
  box.

### Spec impact

Two specs change:

1. `openspec/specs/viewer-graph-layout/spec.md`, requirement *Callout placement keeps
   clearance from nodes and labels*, describes best-effort placement around the node with
   a canvas-extension fallback (from archived task 5.3.6 in
   `2026-09-02-viewer-enhancements-and-orphan-case-anchoring`). Replace it with a gutter
   requirement. Proposed scenarios:
   - **WHEN** a project has at least one implementation callout **THEN** the graph
     reserves a callout gutter left of the leftmost track, and every callout box lies
     inside it.
   - **WHEN** two callouts would overlap in the gutter **THEN** the later one moves down,
     never up, keeps a 2px gap, and its leader still connects to its own node.
   - **WHEN** a callout value is wider than the box **THEN** it wraps to at most 2 lines,
     the rest is cut with an ellipsis, and the full value is available as a tooltip.
   - **WHEN** the smoke harness lays out every project that has a callout **THEN** no two
     layout boxes intersect, and no leader crosses a callout box or a node label.
2. `openspec/specs/virtual-milestone-nodes/spec.md`, the clustering requirement, says:
   "Clusters with ≥2 members SHALL render a soft band spanning their rows plus a count
   chip … single-member groups render bare." Remove that sentence. Keep the clustering,
   the (未核定) tag, the member order and every tie-break rule unchanged.

### Acceptance

1. 大安區-通化段四小段-336地號等26筆 shows three callouts in the gutter, and none
   covers a node, a label, a badge, an edge, or an event.
2. No project shows a stage band or a count chip.
3. `node scripts\viewer_smoke.js` passes the new checks 1–3 on every project that has a
   callout. Before the implementation, the same checks fail on
   大安區-通化段四小段-336地號等26筆.
4. `python -m pytest` still passes (the change touches only the viewer).
5. After the user pushes, the published page at `https://happypig.github.io/urTPE` shows
   the new layout, and `python scripts\check_deploy.py` reports the viewer artifacts as
   fresh.

---

## §2 國 badges and national edges bind to the recno node they name

**Status:** design settled (2026-11-03). P1, openspec change C (wave 4). **Scope:**
`getNodeMilestoneBadges` and the national branch of the event-edge loop in
`renderDetail` (`viewer/app.js`).

### Request

Bind a 國 badge only to a node whose case the national view page (`view/<id>`) names.
Remove every other 國 badge and the edges that go with it.

### Current behavior

- `getNodeMilestoneBadges` gives a 國 badge to the 現況 node (`node.is_current`) **and**
  to each node whose anchored case is in `links.view_verified_case_ids`
  (fix-row-order-tiebreak-and-view-badges D4).
- The first national event in the event column gets a source edge from the 現況 node
  (`e.national` branch of the event-edge loop), whatever its case.
- Measured at `30612dd`: 632 of 693 projects have a `twur` link, and 492 of those 632
  have an empty `view_verified_case_ids`. Example: 大安區-通化段四小段-336地號等26筆
  (`view/900`, `view_verified_case_ids: []`) shows 國 on node 1 only because of the 現況
  rule.
- Every national approval label names its own stage and track. Label counts over the
  632 projects: 事業計畫核定日期 632, 權利變換計畫核定日期 377, 第一次變更事業計畫核定日期
  280, 第一次變更權利變換計畫核定日期 204, 第二次變更權利變換計畫核定日期 97,
  第二次變更事業計畫核定日期 66, and so on up to 第六次變更權利變換計畫核定日期 1.
  使用核發日期 (295) is an execution date and names no stage.

### Decisions (2026-11-03)

1. **A national approval label binds to the recno node with the same stage and track.**
   The label's stage (擬訂, or 第N次變更) and track (事業計畫 / 權利變換) must match the
   node's stage and track. A node on the combined track (事業計畫、權利變換) matches a
   label of either track. The badge, the national edge and the national event all
   follow this binding. This answers the three earlier questions:
   - National events with no bound node draw no source edge (question 1).
   - Each label owns its own node, so there is no single "owner" to choose
     (question 2).
   - The `view/<id>` link stays reachable from every bound node; the 336 example binds
     2 nodes, not 0 (question 3).
2. **`view_verified_case_ids` stays as a second source of 國.** A node whose anchored
   case the view page lists keeps its 國 badge, as today.
3. **The 現況 rule goes.** `node.is_current` alone never gives 國.

### Proposed design

- Add a pure helper `nationalLabelKey(label)` that returns `{stage, track}` or `null`.
  事業計畫核定日期 → {擬訂, 事業計畫}; 第一次變更權利變換計畫核定日期 → {變更, 權利變換};
  第二次變更… → {變更(第二次), …}, in the same stage vocabulary as the nodes. Application
  dates (…申請日期) and 使用核發日期 return `null`: they are not approvals.
- For each label with a key, find the recno node with the same key. If more than one
  node matches, take the node whose date equals the label's date (民國 → ISO). If none
  equals, leave the label unbound. Never guess.
- A node gets 國 when a label binds to it, or when the D4 view-verified rule applies.
- A national execution event (使用核發日期) keeps its place in the event chain. If it
  starts a source group, its source edge comes from the latest bound node. If no node
  is bound, it has no source edge.

### Spec impact

`openspec/specs/history-graph/spec.md` describes the 現況 node's 國 badge (around lines
109, 129 and 237–246, including the rollover scenario). Replace it with the binding rule
of decision 1.

### Acceptance

1. 大安區-通化段四小段-336地號等26筆 (`view/900`): 國 on recno 3 (擬訂 事業計畫
   2022-08-02 ↔ 事業計畫核定日期 111.08.02) and on recno 370 (變更 2023-03-21 ↔
   第一次變更事業計畫核定日期 112.03.21). No 國 on recno 1.
2. The `view/621` project in `openspec/specs/official-link-discovery/spec.md` keeps 國
   on its view-verified nodes 10803151 and 10105152.
3. No national edge starts at a node without 國.
4. A smoke check counts bound and unbound labels over all 632 projects and prints the
   unbound ones, so a vocabulary gap shows as a list, not as silence.

---

## §3 Execution events start ½ node row under the nearest node

**Status:** design settled (2026-11-03). P3, openspec change D (wave 5). **Scope:** the
row-pitch loop (`// §5.3.1 content-addressed pitch`) in `renderDetail`.

### Request

The first node of the 建照 / 開工 / 使照 chain sits ½ node row under the nearest node.
The events in the chain keep the same pitch to each other (½ node row).

### Current behavior

The timeline interleaves approvals and events by date. An approval row takes
`NODE_ROW` = 64px and an event row takes `EVENT_ROW` = 32px, and each row's height is
counted **below** its own `y`. So an event that follows an approval sits 64px (a full
node row) under it. On 大安區-通化段四小段-336地號等26筆, 建照核發日期 2023/04/27 sits a
full row under node 370 (2023-03-21).

### Decisions (2026-11-03)

1. **"Nearest node" is the approval node directly above the event in the timeline**, in
   any swimlane (column). It is not the event's owning node.
2. **Date order wins.** When a later approval falls between two events of one chain,
   the chain stays in date order and that approval row splits it.

### Proposed design

When an event row follows an approval row, advance `y` by `NODE_ROW / 2` (32px), not by
`NODE_ROW`. Event-to-event pitch stays `EVENT_ROW` (32px). After the last event of a run,
the next approval row keeps its full clearance, so its badge strip (from `y - 30`) does
not touch the last event. Because of decision 2, one chain can have more than one run:
each run of events after an approval starts 32px under that approval.

### Risk

The node label (`x + 14`, up to about 200px wide) is in a different column from the
event, but a long label can reach the event column. At 32px vertical distance the label
and the event text can touch. The §1 overlap guard must include both boxes.

### Acceptance

1. On 大安區-通化段四小段-336地號等26筆, 建照核發日期 sits 32px under node 370, and
   開工日期 sits 32px under 建照核發日期.
2. On 北投區-關渡段二小段-303地號等5筆, 建照核發日期 2021/04/26 sits 32px under node 669
   (2020-07-28).
3. The §1 overlap guard passes on every project with events.

---

## §4 Orphan nodes join the timeline with a dotted edge

**Status:** design settled (2026-11-03). P3, openspec change D (wave 5). **Scope:** the virtual-node rows and the interim orphan anchors
(`interimOrphans`, `ghostPos`) in `renderDetail`.

### Request

Connect each orphan node to the nearest recno node with a dotted edge. Put the orphan
above or under that node; put it above when the orphan is earlier than the first recno
node. When the orphan is in the same swimlane (column) as that node, shift it right by
½ node height.

### Current behavior

- **Named orphans** (593 in the corpus at `30612dd`) are virtual nodes in the grid, in
  the column of their track, and join each other with `edge virtual` chain lines. They
  sit **on** the track line of their column. Example: 北投區-關渡段二小段-303地號等5筆,
  where "(未核定) 變更 [自行撤回]" (權利變換) sits on the blue revision line between
  node 669 and node 5.
- **Nameless orphans** (interim anchors, 孤) sit in their own right-most column at
  `y = PAD + i × NODE_ROW`, in list order, not in date order. They have no edge to a
  recno node, only source edges to execution events. The code comment at
  `viewer/app.js:792` says "corpus: 0 post-harvest"; that is stale. There are 3:

  | Project | case_id | node date | schedule | recno nodes |
  | --- | --- | --- | --- | --- |
  | 中山區-中山段一小段-254地號等13筆 | 10202065 | 2020-11-03 | — | 1232 (2012-08-27 擬訂), 1039 (2016-08-23 變更), 992 (2017-04-13 變更(第二次)) |
  | 大安區-大安段一小段-557地號等16筆 | 09511211 | 2013-06-18 | 施工中 | 1170 (2013-10-24 擬訂) |
  | 大安區-龍泉段一小段-169地號等29筆 | 09807161 | 2013-11-29 | — | 1146 (2014-01-28 擬訂), 574 (2021-06-30 變更) |

  None of them has a case_name, stage or track, so none has a column of its own. All 3
  belong to **other** projects; see §8.

### Decisions (2026-11-03)

1. **Every node and orphan has a place on one time axis, top to bottom by date.** An
   orphan takes its own timeline row by its date, like a recno node.
2. **Earlier above later.** When an orphan and a node share a date, the existing D12
   order decides which one is on top.
3. **A 32px right shift is enough.** Confirmed against the 303 screenshot: the shifted
   virtual node clears the track line and does not hit the label of node 669 or node 5.
4. **A nameless 孤 anchor follows the same rule as a named orphan.** It takes its date
   row (decision 1) in the column of the recno node nearest to it in time, shifted 32px
   right, with a dotted edge to that node. The right-most ghost column is removed.
   Reason: one time axis for every node, one placement rule, and one less column in the
   `viewer-graph-layout` column model. The current corpus has no legitimate nameless
   anchor (the 3 above are §8 defects), so this rule applies to future cases only.

### Proposed design

- Named orphans: keep their column, take their own row by date (decision 1), and shift
  right by `NODE_ROW / 2` (32px) when their column holds a track line (decision 3).
- Draw a dotted edge (new class `edge orphan`) from each orphan to the nearest recno node
  in time: the recno node directly above it, or directly under it when the orphan is
  earlier than every recno node.
- Undated named orphans keep today's rule: they follow their stage's dated members.

### Open questions

1. ~~Nameless 孤 anchors~~ — decided, see decision 4.

### Spec impact

`openspec/specs/orphan-case-anchoring/spec.md` and the column model in
`openspec/specs/viewer-graph-layout/spec.md` (four fixed columns, orphans in the
right-most column) must change.

### Acceptance

1. On 北投區-關渡段二小段-303地號等5筆, "(未核定) 變更 [自行撤回]" sits 32px right of
   the 權利變換 track line, with a dotted edge to its nearest recno node.
2. Every orphan's row is in date order with the recno nodes.
3. The §1 overlap guard passes on every project with orphans.

---

## §5 Center the graph in the panel

**Status:** requested (2026-11-03). **Scope:** `svgW` and the x origin in
`renderDetail`; `.graph-zoom` in `viewer/app.css`.

### Request

Keep the graph center-aligned in the panel.

### Current behavior

`svgW` is at least `W` = 960px, and the columns start at `x = PAD` (60px). A project with
one or two columns uses about 300px, so the graph sits at the left of a 960px canvas with
empty space on the right (see the 大安區-通化段四小段-336地號等26筆 screenshot). The SVG
is `width: 100%` with `preserveAspectRatio="xMidYMid meet"`. That centers the canvas,
not the content.

### Proposed design

Compute the content width (the §1 gutter + track columns + event column; §4 decision 4 removes the ghost
column).
Keep `svgW = max(W, content width)`, and offset every x by `(svgW - content width) / 2`.
Keep `W` as the minimum, so a narrow graph is not scaled up to fill the panel.

### Spec impact

The purpose line of `openspec/specs/viewer-graph-layout/spec.md` already says
"centered". Add a scenario: **WHEN** the content is narrower than the canvas **THEN**
the content is centered horizontally.

### Acceptance

1. On 大安區-通化段四小段-336地號等26筆, the left and right margins of the content differ
   by no more than 1px.
2. Pinch-zoom (`attachGraphViewport`, `transform-origin: top center`) still zooms around
   the content.

---

## §6 Remove the 事業種類 legend item and track edges

**Status:** requested (2026-11-03). **Scope:** the legend and the edge loop in
`renderDetail`; `.legend .trk` and the `track` edge style in `viewer/app.css`.

### Request

Remove the green 事業種類 legend item (dashed teal line, `.legend .trk`, `#0f766e`) and
the graph edges it describes.

### Current behavior

`urtpe/graph.py` emits three edge kinds: `revision`, `track` and `section`. The viewer
draws all three and lists all three in the legend. 394 of 693 projects have at least one
`track` edge.

### Proposed design

Skip `kind === "track"` edges in the viewer edge loop, and remove the legend item and its
CSS. Keep the `track` edges in `projects.json`: they are graph data, and other tools can
read them. This is a viewer-only change.

### Risk

A node that joins its family only through a `track` edge becomes visually unconnected.
Count those nodes before the change, and name them in the proposal.

### Spec impact

`openspec/specs/history-graph/spec.md:60` has a scenario for "a track or section edge
passes behind a node label". Change it to name only the section edge. No spec rule names
the legend items. This spec change is why §6 is in openspec change A, not a direct
commit.

### Acceptance

1. No project shows a dashed teal edge or the 事業種類 legend item.
2. `projects.json` still carries the `track` edges.

---

## §7 Show [無] / [NA] for a case with no 目前辦理情形

**Status:** design settled (2026-11-03). P1, openspec change B (wave 3). **Scope:** the pipeline
(`refreshed_schedule` and the cache refresh in `urtpe/links.py`) and the viewer
(`scheduleBadgeText`, `caseScheduleOf`, the 相關連結 list, the orphan node label).

### Request

When the platform's 基本資料 / 目前辦理情形 for a case is 無 or empty, show that, not
[審查中], in the 相關連結 list and on orphan nodes. Reported examples:

- 11110171 — 擬訂臺北市信義區雅祥段一小段599地號等22筆土地都市更新事業計畫及權利變換計畫案 [審查中]
- 11410008 — the same 案名 [審查中]
- 09607081 — 擬訂臺北市中正區永昌段五小段248地號等47筆土地都市更新事業計畫案 [審查中]
  (shown twice)

### Current behavior

- `data/.link_cache/信義區-雅祥段一小段-599地號等22筆/result.json` and
  `data/.link_cache/中正區-永昌段五小段-248地號等47筆/result.json` hold
  `case_schedules` = 審查中 for all three cases, and they have **no** `case_headers` key.
  So the header refresh, which reads 目前辦理情形 from get_project168_top, never ran on
  them. The 審查中 comes from the parcel-search list.
- When the refresh does read 無, `refreshed_schedule(..., no_state=True)` clears 審查中
  to "" (supersede-headerless-cases D1). The viewer then shows **no** badge, not 無.
- 68 of 693 projects carry at least one 審查中 case.

### Proposed design

1. Run the header refresh on the caches that lack `case_headers`, under the
   single-writer lock. This changes `data/.link_cache/` and needs a re-emit (the ~23 MB
   diff in `AGENTS.md`).
2. Keep the no-state reading as its own state instead of clearing it, with two values
   (decision 1): store `case_schedules[cid] = "無"` or `"NA"`, and render `[無]` or
   `[NA]` in `scheduleBadgeText`.
3. Split `header_has_no_state`: today it returns true for both a NAME of 無 and an
   empty NAME (`str(header.get("NAME", "")).strip() in ("", "無")`), so the two cases
   cannot be told apart after it. Keep it as the supersede trigger, and add a pure
   helper that returns `"無"`, `"NA"` or `""` for the badge.
4. Keep the supersede logic: a 無 or NA case still triggers `find_superseding_case`.
5. A **missing** header row (`{}` / `None`, the fetch returned nothing) stays "no
   evidence", as now. It is neither 無 nor NA, and it keeps the cached state.

### Decisions (2026-11-03)

1. **Two labels, one per platform reading.** `[無]` when 基本資料 / 目前辦理情形 is the
   word 無. `[NA]` when the header row exists and 目前辦理情形 is empty.
2. **The label follows the header reading only.** A case shows `[無]` or `[NA]` exactly
   when its 基本資料 / 目前辦理情形 reads 無 or empty, whatever its approval dates. So
   立農163-2's 11211211 (header 無, cache at `30612dd`:
   `case_headers["11211211"] = "無"`) shows `[無]`. This reverses
   supersede-headerless-cases D1 for the badge only; D1's other effect stays: a 無 or NA
   reading never keeps a cached 審查中, so no 審查中 chip comes back.
3. **Only the per-case badge changes; family-level readers ignore 無 / NA.** Checked at
   `30612dd`: the family status chip (`statusChip`, 審查中 / 撤回) is drawn only in the
   left project list (`renderList`, `viewer/app.js:761`). Two more family-level readers
   read the same `case_schedules`: `neverApproved` (`app.js:363`, the 未曾核定 chip) and
   the 相關連結 未曾核定 note (`app.js:1268`). All three use `every(...)` over the
   schedules, so a stored 無 / NA would change them: a family of withdrawn cases plus
   one 無 case would lose 未曾核定. All three must skip 無 and NA, so the left list and
   the never-approved note read exactly as before.
4. **Pipeline and viewer go in one change, with the re-emit on its own commit.** One
   openspec change B, because the viewer label means nothing until the cache holds the
   reading. The tasks run in this order, which is the repo's pattern (`53bc832` feat →
   `767bc81` chore re-emit → `30612dd` openspec archive):
   1. Tests first: the new helper and `refreshed_schedule` for 無 / empty / missing row;
      the smoke checks for `[無]`, `[NA]`, and the unchanged family readers.
   2. `feat:` commit: pipeline helper + storage, viewer label + family-reader skip.
   3. Run the header refresh on the caches that lack `case_headers` under the
      single-writer lock, then re-emit. Stage `data/` and `viewer/projects.data.js` in
      a separate `chore:` commit (the ~23 MB diff in `AGENTS.md`).
   4. `openspec:` archive commit.

### Superseded cases

A superseded case (`links.superseded_by`, D6) shows `已由 <successor> 取代` and no
status badge today (`app.js:1263`). With decision 2 it shows both: `[無]` (or `[NA]`)
and the successor note. For 立農163-2: `11211211 … [無] 已由 11409026 取代`.

### Open questions

None. Questions 1–4 were answered on 2026-11-03 (decisions 1–4).

### Spec impact

`openspec/specs/cache-freshness/spec.md` (the refresh and its no-state rule) and
`openspec/specs/history-graph/spec.md` (the status chip vocabulary 審查中 / 撤回).

### Acceptance

1. 11110171, 11410008 and 09607081 show [無] or [NA] in 相關連結 and on their nodes,
   matching what their 基本資料 / 目前辦理情形 reads after the refresh.
2. 立農163-2 shows `[無] 已由 11409026 取代` on 11211211 and no 審查中 chip in the left
   list.
3. The left-list status chip and both 未曾核定 readers show the same result before and
   after the change on all 693 projects (a smoke check compares them).
4. `python -m pytest` passes, with new cases in `refreshed_schedule` and the new helper
   for each reading: 無 → `[無]`, empty → `[NA]`, missing row → cached state kept.

---

## §8 A view-verified case must belong to the project

**Status:** design settled (2026-11-03). P1, openspec change E (wave 3b). **Scope:**
the pipeline — the view-page absorb that fills `view_verified_case_ids`
(`urtpe/links.py`, `extract_case_ids_from_view` and its callers), the orphan anchoring
that emits `links.orphan_nodes`; then a cache refresh and a re-emit.

### Problem

The 3 nameless 孤 anchors in §4 are cases of **other** projects (reported by the user,
2026-11-03):

| Project | case_id | The city's case name for that id | Owning project |
| --- | --- | --- | --- |
| 中山區-中山段一小段-254地號等13筆 | 10202065 | 變更(第四次)臺北市大安區辛亥段一小段163地號等5筆…權利變換計畫案 | 大安區-辛亥段一小段-163地號等5筆 |
| 大安區-大安段一小段-557地號等16筆 | 09511211 | 擬訂臺北市中山區吉林段四小段603地號等40筆…事業計畫案 [施工中] | 中山區-吉林段四小段-603地號等40筆 |
| 大安區-龍泉段一小段-169地號等29筆 | 09807161 | 擬訂臺北市內湖區康寧段二小段262地號等29筆…事業計畫及權利變換計畫案 | 內湖區-康寧段二小段-262地號等29筆 |

### Cause

All 3 entered through `view_verified_case_ids`. Each project's own national view page
(`view/136`, `view/178`, `view/193`) lists the case in its 相關連結.
`openspec/specs/orphan-case-anchoring/spec.md` keeps a view-verified case even when its
similarity is below 0.7, because "the portal itself asserts the case belongs". Here the
national portal is wrong, in two shapes:

- **Shape A — the link names another project.** The 相關連結 label is the other
  project's name. view/136 labels 10202065 "變更(第四次)…辛亥段一小段163地號…"; view/193
  labels 09807161 "擬訂…內湖區康寧段二小段262地號…". The pipeline takes the id and
  ignores the label.
- **Shape B — the label is right, the id is wrong.** view/178 labels 09511211
  "擬訂臺北市大安區大安段一小段557地號等16筆…", but the city's case 09511211 is
  吉林段四小段603. Only the city's own case name for the id shows this.

Because the anchors carry the other project's milestones, the graph can show another
project's 建照 / 開工 dates (09511211 is 施工中, 09807161 is 已完工). With §2 decision 2,
a wrong view-verified id would also give a wrong 國 badge.

### Evidence (scan of `data/.link_cache/` at `30612dd`)

- 186 view-verified ids in 140 caches. For 181, the 相關連結 label names the project's
  own section and first parcel. 5 labels name something else:
  10202065 (辛亥段163), 09807161 (康寧段262), 10906092 (萬華區莒光段三小段519-3, on
  中山區-吉林段二小段-898地號等3筆), 09608220 (犁和段一小段165, on
  信義區-犁和段一小段-102地號等3筆), 09112120 (崇仁新村, no 地號 — the spec's own
  legitimate example, so not a defect).
- 9 view-verified ids are also in another cache dir's `city_case_ids`. 4 are alias or
  old-generation dirs of the same project (萬慶段95 中山/文山, 吳興段790-6 等29/等4,
  大龍段265 / 265-7, 崇仁新村 等2/等_). The others are the cross-project cases above.
  09511211 (shape B) shows only here: both 吉林段四小段603 and 大安段557 claim it.

### Decisions (2026-11-03)

1. **The city's case name decides.** The case_id is a city number, and the graph takes
   its dates and badges from that id, not from the label. So check 2 (the city's
   `CASE_NAME`) decides, and check 1 (the 相關連結 label) only gives the reason text:

   | Label (check 1) | City name (check 2) | Result | Reason in `view_rejected` |
   | --- | --- | --- | --- |
   | match | match | accept | — |
   | no match | no match | reject | label and city name name another project (shape A) |
   | match | no match | reject | label is right, id is wrong (shape B) |
   | no match | match | accept | — (the label error is logged in the run report) |

2. **A rejected id is offered to its own project.** Find the project whose land core
   matches the city's case name, and add the id to that project's cache. Match on the
   land core, never on 編號 or `project_id`, which both churn.

### Proposed design

1. **Keep the city's case name.** The refresh already reads each case header
   (get_project168_top). Store its `CASE_NAME` in the cache (today only `NAME`, the
   state, is kept).
2. **Decide by the city name (decision 1).** Accept a view-verified id only when the
   land core of its `CASE_NAME` matches the project's (the existing similarity,
   `LINK_THRESHOLD = 0.7`, or the parcel-less rule for a name with no 地號, such as
   崇仁新村). Compare the label too, only to write the reason.
3. **Offer the id to its own project (decision 2).**
   - If exactly one other project's land core matches, add the id to that project's
     `city_case_ids` and fetch its milestones, unless that cache already holds it
     (09807161 → 內湖區-康寧段二小段-262地號等29筆 already does). Record the move in
     both caches: `view_rejected` in the source, `adopted_from_view` in the target.
   - If no project matches, keep the id only in `view_rejected`.
   - If more than one project matches, do not guess: keep it in `view_rejected` with
     the reason "ambiguous owner", the same rule that `data/project_aliases.json` uses
     for ambiguous pairs.
4. **Never drop silently.** Every rejected id, and every id offered to another project,
   is named and counted in the run report, the same way truncated records are named
   and counted.
5. **Then refresh and re-emit**, under the single-writer lock, on the caches that hold
   a view-verified id and on the target caches of step 3. One run writes both, so the
   single-writer rule holds. Same commit pattern as §7 decision 4.

### Effect on other entries

- **§4:** after this change, the 3 nameless anchors disappear, and the corpus has 0
  nameless orphans. §4 decision 4 then applies only to future nameless anchors.
- **§2:** decision 2 (view-verified ids give 國) is safe only after §8. Run wave 3b
  before wave 4.

### Open questions

1. ~~Which check wins~~ — decided, see decision 1.
2. ~~Offer or only remove~~ — decided, see decision 2.
3. **City name not available** (the header fetch failed, or the refresh has not reached
   that cache). Proposal, used unless you say otherwise: decide by the label alone,
   mark the id "not confirmed" in the run report, and do not reject it for missing
   data. A missing header is no evidence, which is the rule `header_has_no_state`
   already follows.

### Spec impact

`openspec/specs/orphan-case-anchoring/spec.md` (the view-verified exception),
`openspec/specs/official-link-discovery/spec.md` and
`openspec/specs/cache-freshness/spec.md` (`view_verified_case_ids`).

### Acceptance

1. 10202065, 09511211 and 09807161 are not in the `view_verified_case_ids` or the
   `orphan_nodes` of the 3 projects above. Each is in `view_rejected` with its reason.
2. Each of the 3 ids is in the cache of its own project (辛亥段一小段163,
   吉林段四小段603, 康寧段二小段262), and the run report names the move.
3. 09112120 (崇仁新村) stays view-verified.
4. The run report names every rejected id and every offered id.
5. `python -m pytest` passes, with cases for all four rows of the decision 1 table, the
   parcel-less name, the ambiguous owner, and the missing city name.
