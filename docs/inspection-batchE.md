# Project inspection — Batch E · collected 2026-11-12, extended 2026-11-12 (E4–E9)

Nine work items. E1–E3 were carried over from the dashboard exploration notes
(`docs/DashboardNUXUI.md`); E4–E9 were collected the same day from the user's
badge and callout findings. The board follows the
`docs/inspection-batchD.md` structure: findings, then the integrated plan,
then the decisions that gate execution.

**Source and state.** The notes measured everything E1–E3 need and left three
items open (its §13: the unverified column — answered, Option D, the column is
omitted; **Part 1 scope — E2**; the compatibility-ideograph fix — **E1**; the
windowed list — **E3**). E4–E9 came from the user's 2026-11-12 review of the
badges (items 1–3) and the area-split callout (items 4, 4a–4d, 5), measured
the same day on the payload at `7a1102a`: **1,444 records / 680 projects**,
統計至 2026-10-28. The notes' §14.-1 records what moved with the 河堤399
merge.

**The items are separate openspec changes or direct fixes, not one.** E1 is a
pipeline defect independent of the UI work. E2 and E3 are viewer work that
shares one harness upgrade. E4/E7 are openspec changes (spec scenarios and a
payload field change); E5/E6/E8/E9 are direct fixes at named sites. The batch
keeps them separate so one change's review never blocks the others.

---

## E1 — the compatibility ideographs: one folding, two readers

The full measurements live in batch D (D16, D16a–D16d) and in
`docs/DashboardNUXUI.md` §11; they are not repeated here. This section records
only what execution needs, re-verified 2026-11-12 on the 680-project payload.

**The defect.** CJK compatibility ideographs are distinct byte sequences that
render as the same character. The data carries four:

| Codepoint | Character | Where | Count |
| --- | --- | --- | --- |
| U+F901 | 更 | 6 corpus 案名 (`name`/`name_raw`) | 6 rows |
| U+F963 | 北 | 6 corpus 案名 | (same 6 rows) |
| U+FA26 | 都 | 6 corpus 案名 | (same 6 rows) |
| U+F9DD | 利 | one city case name, `11507018` | 1 case |

**Reader 1 — broken live.** `_tracks()` (`urtpe/cleanse.py:239`) matches the
keyword 權利變換 as a literal substring. The live case
`11507018` (大安區-復興段三小段-3地號等2筆) writes 利 as U+F9DD **inside**
權利變換 (index 32 of 38), so the case reads 事業計畫 alone and loses its
權利變換 track. This is the one live break.

**Reader 2 — broken latent.** `parse_name_id()` (`urtpe/cleanse.py:31`)
returns `('', '', '', None)` for all 6 corpus records, because the regex
cannot match a compatibility 北 or 都. The 3 projects' own land core is empty
today; their portal links came from the cached view pages (view/793, view/791,
view/253), so nothing visible breaks. Re-verified 2026-11-12: the 6 rows are
recnos 8, 121, 179, 611, 613, 615 and they map to the same 3 projects the
batch-D table printed.

**What NFKC does.** `unicodedata.normalize("NFKC", name)` folds U+F9DD →
U+5229 (利), U+F963 → U+5317 (北), U+FA26 → U+90FD (都), U+F901 → U+66F4 (更).
Verified in the batch-D probes: it makes `parse_name_id()` succeed on all 6
and restores `_tracks()` on the live case.

**The two hazards the tests must hold.** First, the fold changes what the
merge's similarity scoring compares, so it can join or split a family — the
project count must not move (there is one count: `urtpe/models.py:80` defines
`Project` as the merged family, and the emitted count is `len(graphs)` at
`urtpe/graph.py:188`; 680 is the family count and the project count at once).
Second, a corpus-only test would pass while the live bug survived: the
corpus's six characters sit in text no keyword touches (no track keyword
carries a compatibility ideograph — measured, batch D D16a); the live
character sits inside one. The difference is **where the character sits**, not
which character it is.

**Form:** openspec change (`case-merging` is not touched; the cleanse module
and the `data-cleansing` spec carry it). Test-first group: the six pins from
`docs/DashboardNUXUI.md` §11.3, re-verified verbatim on 2026-11-12:

1. the live case reads both tracks after folding;
2. the 6 corpus records are unchanged in track;
3. the project count does not move;
4. the live case is checked by name, not by count;
5. the 6 records parse to their identity after folding, and the 3 projects'
   land core becomes the folded one;
6. the 3 projects' portal links do not move.

**Scope guard.** D16d is the lesson this item carries: six scope corrections
were made while measuring it, in both directions, and the rule that came out
is **a scope is a claim about what was not measured**. "One reader" was wrong
in both directions before it was right. If a re-measure during the change
shows a third reader, measure it before widening or shrinking the change.

---

## E2 — Part 1: URL write-back + keyboard access, as one change

**The state, re-verified 2026-11-12.** The list items are `div` elements with
an `onclick` handler (`viewer/app.js:911`). The codepoint-level search over
`viewer/app.js` (1,710 lines) reads: `tabindex` **0**, `keydown`/`keyup` **0**,
`role=` **0**, `aria-` **0**. The items are not focusable and cannot be
activated by keyboard.

The URL's **read half exists**: the dashboard change (94cd3e8) shipped the
read-only deep link. `openFromHash` (`viewer/app.js:1626`) reads
`#project=<project_id>` on load and on `hashchange`, opens that project's
graph, and scrolls it into view (`viewer/app.js:1637`). The dashboard writes
the links (`viewer/dashboard.js:490`,
`index.html#project=<encoded project_id>`). The **write half is missing**:
clicking an item does not touch the hash (`viewer/app.js:1624-1625` says so in
a comment), so a reader who selects a project cannot copy the selection out of
the address bar.

**Why one change, not two.** A shareable URL must be writable, and the only
writer is a selection. A selection must be reachable, and the only reach is
focus. Focus, activation and write-back are one edit in one function
(`renderList`'s item construction at `viewer/app.js:901-913`). Splitting them
publishes half a feature.

**The six steps** (the notes' §8.3, unchanged, with the current line anchors):

1. Make each list item focusable and give it a role.
2. Handle Enter and Space to select.
3. Write the selection into the URL with `history.replaceState`.
4. Read the URL on load and select that project.
5. Add a windowed list (this is E3, a separate change).
6. Add a 250 ms debounce on top.

Steps 5 and 6 are named here only to mark the boundary: **E2 delivers steps
1–4 and stops.** The debounce is a one-line follow-up that needs no change of
its own; the notes rank it Low value.

**The four details that decide the review:**

- **`replaceState`, not `pushState`.** A selection is not a page view. One
  history entry per page load; a push per click would drown the back button.
- **The comment at `viewer/app.js:1623-1625` documents the old behaviour**
  ("clicking an item in the list does not rewrite the hash"). The change
  reverses it; the comment must be updated in the same edit, or the next
  reader inherits a lie.
- **The deep link's read path must not move.** The dashboard's links and
  `openFromHash` are a working pair. E2 adds a writer; it does not change the
  reader, the hash format, or the `encodeURIComponent` encoding
  (`viewer/dashboard.js:490`).
- **Focus styling.** A focusable `div` with no visible focus indicator fails
  the reader it was fixed for. The `:focus-visible` rule lands with the
  `tabindex` change, in `viewer/app.css`.

**Form:** openspec change. Spec surface: `viewer-related-links` does not carry
this; a new requirement joins the viewer specs (the deep-link requirement
gains its write half; the keyboard requirement is new).

---

## E3 — the windowed list (Part 1's successor; harness first)

**The measurement** (the notes' §6, method held on the 680-row payload
2026-11-12):

| Step | Time |
| --- | --- |
| Build and insert 680 DOM rows | 17 ms |
| Force layout and paint | **63 ms** |

`list.scrollHeight` is ~34,000 px against a `clientHeight` of 920 px. The
browser paints all 680 rows and discards most off-screen. **Paint is the
cost, not JavaScript** — and the finding is the *ratio* (a full render costs
~8× the 86-row render), not the milliseconds: the same code measured 110 ms,
294 ms and 344 ms on different runs of the same machine.

**The fix.** Render only the rows near the viewport; hold spacer height for
the rest. A full render then costs what the 86-row render costs, ~13 ms.
The rows are built one at a time with `appendChild` into the live list
(`viewer/app.js:901-913`), so each append touches a node the browser must lay
out; windowing removes most of the appends and most of the layout.

**The gate is the harness, not the viewer.** `scripts/viewer_smoke.js`
(331 lines) stubs `getBoundingClientRect()` to return all zeros
(`scripts/viewer_smoke.js:70`) and provides no `scrollTop`, `clientHeight` or
`offsetHeight`. A windowed list reads exactly those. **Nothing checks the
harness automatically** — it runs by hand and reaches no network
(`AGENTS.md`). A windowed list without harness support ships with no automated
check at all. So the change's first task is harness geometry, and the
test-first gate (`docs/DashboardNUXUI.md` §13.1) is satisfied by the harness
cases, not by pytest.

**The four details that decide the review:**

- **The scrollbar must not jump.** Spacers at both ends hold the full list
  height (`scrollHeight` stays ~34,000 px); only the row nodes inside the
  window are real.
- **The deep link must still scroll.** `openFromHash` calls
  `scrollIntoView({ block: "center" })` (`viewer/app.js:1637`). Under
  windowing, the target row may not exist yet: the change must render the
  window that contains the target **before** the scroll, or the deep link
  silently selects without showing.
- **The smoke harness's overlap and badge checks must survive.** The harness
  walks the rendered items; a windowed list renders fewer of them. The harness
  cases decide whether it walks the real window or a fixture that forces the
  full render — that decision is part of the change, not an afterthought.
- **The dashboard inherits the requirement.** If the dashboard lists projects
  for drill-down it takes the same full-render cost (the notes' §8.4); the
  windowing helper must be written so the dashboard can call it, not so only
  `renderList` can.

**Form:** openspec change (viewer + `viewer_smoke.js` harness upgrade in one
change, so the gate and the code land together).

---

## E4 — the 國 badge on a recno node: registration and name, not stage+date (user, 2026-11-12)

**The user's rule, restated.** The 國 badge attaches to a recno node when the
national view page names that node's case or the project itself — and it must
NOT attach by stage+date matching alone. Two counter-examples name the rule:

- **2c — 大安區-大安段一小段-590地號等18筆.** The current node (recno 90,
  變更(第三次)權利變換, case `11411007`) carries no 國 today and must carry
  none under the rule: `11411007` is not in `view_verified_case_ids`
  (`09904270`, `10205193` are), and the node's 案名 differs from the view
  title. Verified: today's render agrees — no badge. This row states the
  rule's *ceiling*: a current node qualifies only through its own case.
- **2d — 北投區-文林段三小段-838-1地號等7筆, node recno 433.** It carries 國
  today **only** through per-label binding: two national labels
  (第一次變更事業計畫核定日期 and 第一次變更權利變換計畫核定日期, both
  111.09.20 = 2022-09-20) hit the node's exact date. Its case `10611282` is
  not registered by view/766 (`10611281` is), and its 案名 (變更…) differs
  from the title (擬訂…). **Under the rule, node 433 loses the badge.**

**The proposed predicate** — a node carries 國 when its anchored case is in
`view_verified_case_ids` (the view page's own 相關連結 registration, 2b) **or**
the node's 案名 equals the project's `twur_name` (the view page names the
project with that title; the 擬訂 first-plan node carries it, 2a):

| Population (over the 680-project payload, 2026-11-12) | Count |
| --- | --- |
| nodes with 國 today (per-label binding OR view-verified) | **1,186** |
| nodes with 國 under the proposed rule | **735** |
| nodes that lose it (stage+date-bound only) | **451** — 文林838-1 node 433 is one |
| nodes that gain it | **0** — every name-route node is already bound today |
| of the 735, current nodes | 259 (230 via a view-verified case, 29 via the name route) |

**The measured cost is one-directional: the rule only removes.** No node gains
a badge, because the 擬訂 node's dates always match the national 核定日期
labels — the binding already finds them. What the rule buys is **precision**:
a 國 badge means "the view page names this", not "a date matched".

**The one decision the measurement surfaces.** The name route (2a) matches the
擬訂 node exactly (大安590 node 1257's 案名 equals the title). The 權利變換
擬訂 node (node 884) differs from the title by one word (權利變換計畫案 vs 事業
計畫案) and would lose its badge under an exact-name rule. Its case `10205192`
is not view-verified. If the user wants node 884 to keep 國, the name route
needs a section+parcel fallback — which is close to the binding it replaces.
The decision table below asks.

**Where the change lands.** The badge logic is `viewer/app.js:186-194`
(`getNodeMilestoneBadges`); the binding it replaces is `bindNationalLabels`
(`viewer/app.js:149-172`) plus `nationalLabelKey` (`viewer/app.js:25-35`). The
spec surface is `viewer-related-links` (the badge requirement) and
`official-link-discovery` (what `view_verified_case_ids` asserts). The payload
needs no change: `twur_name` and `view_verified_case_ids` both exist.

**Form:** openspec change (the badge requirement's scenarios change; the
archive guard needs the live body carried).

---

## E5 — the construction-event 國 badge: national-only, never corroborated (user, 2026-11-12)

**The user's rule.** The 使照核准 event row's 國 badge fires today when the
national portal holds 使用核發日期 — even when the city holds 使照核發日期
too (`natCorroborated`, `viewer/app.js:361`, `:407`, `:1398`). The badge
should fire **only when the city case has no 使照 and the view page does**.

**Measured** (over the 680-project payload, 2026-11-12):

| Population | Count | Under the rule |
| --- | --- | --- |
| projects with both 使照核發日期 and 使用核發日期 (the corroborated shape) | **288** | badge removed |
| projects with 使用核發日期 only (the city has no 使照) | **2** | badge stays |

§3.6 of the dashboard notes measured the same population from the other side:
the two fields agree on 267 of 288 projects where both exist — they are the
same event seen by two portals. A 國 badge on a city-sourced event claims a
second witness where the portals merely agree. Removing it makes the badge
mean "this date came from the national page because the city had none".

**The 2 national-only projects keep their badge and their green edge** — that
is the fallback the D4a rule built, and it stays.

**Form:** direct `fix:` (one flag at `viewer/app.js:407`:
`natCorroborated` stops driving the badge; `nationalHit` alone drives it) +
the viewer test that pins both counts. The history-graph spec's
"National-mapped event shows the 國 badge" scenario keeps its reading; the
corroborated case loses its badge sentence.

---

## E6 — every 國 badge that names a page is a link to that page (user, 2026-11-12)

**The user's rule (item 1).** A badge that names a portal must open it.

**The three badge sites, measured:**

| Site | Today | Link? |
| --- | --- | --- |
| Node badges — 北 (`viewer/app.js:184`), 國 (`viewer/app.js:193`) | `<a>` with `href` | **works** |
| Construction-event 國 (`viewer/app.js:1398`) | `<span title="國土署里程碑">` | **no link** |
| Milestone-card badges — 推動歷程 (`viewer/app.js:697`, `:704`), 階段辦理過程 (`:715`–`:731`) | `<span>` | no link |

**The gap is the event badge** (and the cards, which are out of scope here —
a card badge labels a whole portal, not one addressable page). Under E5's
rule the event 國 appears only on a national-only date, and the URL is known:
the project's `links.twur` (view/<id>). The change swaps the `<span>` for an
`<a>` with `href={twur}` and the `title` becomes `view/<id>` — the same shape
the node badge already uses (`viewer/app.js:191-193`).

**Form:** direct `fix:`, one template edit at `viewer/app.js:1398`, landed
with E5 (same edit site). The `viewer_smoke.js` overlap check walks badges;
the `<a>` keeps the same footprint.

---

## E7 — the joined node: one 北 badge over both area cases; the callout splits by section (user, 2026-11-12)

**The shape.** 30 nodes carry 2+ city case ids; 28 of them are area splits
(the city filed -A區 and -B區 cases for one approval, and the pipeline binds
both to the one recno — the 民生134-6 / 敦化363-1 shape). The list shows one
row; the graph shows one node. But:

- the 北 badge links **only `cases[0]`** (`viewer/app.js:184`) — the second
  case is invisible on the graph (it lives in the debug 相關連結 list, and in
  the milestone card's per-case entries);
- the callout shows one box per node reading the node's **one** `implementation`
  payload — the payload picks one case's statistics (the D5 statistics pick),
  so 敦化363-1 node 537 shows -A區's 使照 (2025-04-29) and hides -B區's
  (2025-05-06, cached at `implementation["10906102"]`).

**The user's rule.** The cases are already joined on the recno — so the badge
covers both, and the callout shows both, per section, with the differences
visible per section.

**Measured** (2026-11-12):

| Population | Count |
| --- | --- |
| nodes carrying 2+ case ids | **30** |
| of those, at least one case name carries an area suffix | **28** |
| projects with 2+ area-suffixed case names | **19** |
| projects whose area cases sit on 2+ different recnos (a different shape — see below) | **14** |
| joined-node case-label tuples | (A,B) 20 · (北,南) 5 · (東,西) 3 · (A,B,C) 1 · (A,B,C,D,E) 1 |

The 14 "different recnos" projects are **not** this finding: their area cases
sit on distinct approval nodes (榮星53's 北區/南區 pairs each anchor their own
recno) — the per-node badge rule already covers them, one badge per node per
its own case. E7 is about the 30 joined nodes only.

**The design, three parts:**

1. **The badge (4b).** `cases.length` 北 badges on the joined node, one per
   case, each linking its own `r_progress_detail.aspx?case_id=` — the same
   `<a>` shape, repeated. The `title` carries the case id as today.
2. **The area label (4d).** The suffix parses from the case name
   (`-[A-Z]區` / `-北區`…; the corpus holds A, B, C, D, E, 北, 南, 東, 西 —
   measured counts 32/39/5/5/1/2/5/3/5). The label renders beside the badge
   (`[A區]`) and beside each callout section header.
3. **The callout (4c).** The cache holds implementation **per case**
   (`implementation` is keyed by case id — verified: 敦化363-1's cache holds
   7 entries, and -A/-B differ on Ulic_Date 2025/04/29 vs 2025/05/06). The
   joined node renders one box **per section**, and the diff marker (the
   changed-value highlight) compares within a section across nodes, not
   across sections.

**The one open measurement.** The per-section callout needs the node's
implementation payload per case in the **payload**, not only the cache. Today
`n.implementation` carries one case's payload (the pick). E7's change must
either emit `implementation` keyed by case id on joined nodes, or have the
viewer read `links.case_milestones`-style per-case data. Both exist in the
cache; only the emission decision is open. The decision table asks.

**Form:** openspec change (the payload schema grows on joined nodes; the
`case-record-join` and `viewer-related-links` specs carry it) + viewer + one
re-emit.

---

## E8 — the area label beside the badge and the callout (user, 2026-11-12)

**The user's rule (4d).** Show `[A區]` / `[B區]` next to the corresponding 北
badge, or next to the callout section when there is one.

This is E7 part 2, listed separately because it survives E7's failure modes:
if the per-section callout proves too wide (E9's finding), the label still
belongs on the badge. The label's source is the case name's suffix, parsed
once per case (`candidate_names` holds every case's full name). Nodes whose
cases carry no suffix render nothing — the 2 joined nodes without an area
suffix stay silent.

**Form:** direct `fix:` (a label helper + one template site), landed with E7.
The tuple measurement above ((A,B) 20, (北,南) 5, …) is the test fixture set.

---

## E9 — callout values never wrap; the gutter grows to the content (user, 2026-11-12)

**The user's rule (5).** A callout row is one line, however long the value.
The box width follows the content; no clamping to the gutter cap.

**Measured** (over the 680-project payload, the `cjkUnits` width model from
the fix-callout-wrap-height D2 rules, 2026-11-12):

| Population | Count |
| --- | --- |
| nodes rendering a callout | **1,431** |
| nodes where some value wraps to 2 lines under the 160 px cap | **744** |
| the widest value | 敦化南北路特定專用區(A區)(原屬第四之一種住宅區) — **~302 px** |
| projects whose widest callout exceeds the 160 px cap | **225 of 677** |
| per-project widest box: median / p90 | 142 px / 207 px |

**The design.** Drop `CALLOUT_GUTTER_CAP` as a hard clamp and let the gutter
take the widest box, with a reflow guard: the graph's SVG width grows with the
gutter (the §5.3.3 centering already handles `svgW > W`), and the `implBoxH`
height model collapses to `rows * 14 + 6` (one line each). The wrap-height
machinery from fix-callout-wrap-height D2 (`implValueLines`, the two-line
case) is retired by this change — the height model the D2 fix built exists to
predict wrapping that no longer happens.

**The cost, stated honestly.** The median project loses nothing (142 < 160).
The p90 project's gutter grows ~47 px; the extreme project's ~142 px. On the
pinch-zoom viewport (`attachGraphViewport`, `viewer/app.js:1652`) the graph
scales, so the widest gutter costs pan, not readability.

**Form:** direct `fix:` + a harness measurement (the smoke harness's zero-rect
stub cannot measure rendered width; the measurement above is the payload-side
model, and the change pins it as a test). Depends on nothing — but lands with
E7/E8 so the callout is reviewed once.

---

## Order

| Step | Item | Priority | Form | Depends on | Notes |
| --- | --- | --- | --- | --- | --- |
| 1 | **E1** — NFKC folding at the cleansing boundary; the six-pin test group | **P1** | openspec change (`data-cleansing`) + pytest | — | Independent of the UI work; smallest; its test group is fully specified |
| 2 | **E2** — URL write-back + keyboard, steps 1–4 only | **P1** | openspec change (viewer) + harness cases | — | The read half exists; this adds the write half and the focus path |
| 3 | **E3** — harness geometry stubs, then the windowed list | **P2** | openspec change (viewer + harness) | E2 (the harness cases E2 adds are the base) | Lands last; the dashboard reuses its helper |
| 4 | **E4** — the 國 badge rules re-stated; the per-label route narrows to registration + name | **P1** | openspec change (`official-link-discovery` + `viewer-related-links`) + viewer + payload? | — | 451 badges move; the pipeline may need `twur_name` on more nodes |
| 5 | **E5** — the construction-event 國 badge: national-only, not corroborated | **P1** | direct `fix:` + viewer test | E4 (one badge vocabulary) | 288 badges go, 2 stay; a viewer-side rule change |
| 6 | **E6** — badge links: the event 國 becomes a link to view/<id> | **P2** | direct `fix:` | E5 | One element swap |
| 7 | **E7** — the joined node's 北 badge covers both area cases; the callout splits by section | **P2** | openspec change (viewer + `case-record-join`) | — | 30 joined nodes, 28 area pairs |
| 8 | **E8** — area labels [A區]/[B區] beside the badge or callout | **P2** | direct `fix:` | E7 | Derives from E7's section split |
| 9 | **E9** — callout values never wrap; the gutter grows to content | **P3** | direct `fix:` + harness measurement | — | 744 of 1,431 callouts wrap today; the widest value needs 302 px |

**Why this order.**

- **E1 first.** It is a pipeline defect with a fully specified test group, and
  every other change that touches names or counts benefits from the fold being
  in. It needs no harness work and no viewer work.
- **E2 before E3.** Both need harness cases; E2's are smaller (focus and URL
  assertions). E3's geometry stubs build on a harness that already knows how
  to drive the list, and E3 must keep E2's deep-link write working — landing
  E3 first would mean E2 reviews against a moving base.
- **E4 before E5.** Both reshape the badge vocabulary; E4 defines when a 國
  exists on a node, E5 removes the event badge that contradicts it. Landing
  E5 first would remove badges E4's rule may re-home.
- **E5 and E6 are one edit site.** The event badge at `viewer/app.js:1398`
  changes from `natCorroborated`-driven span to `nationalHit`-driven link in
  the same template; they are split here only because E5's rule is a
  measurement and E6's is a swap.
- **E7 → E8 → E9 are one review unit** with three separable edits: the
  section split (E7), its labels (E8), and the box sizing (E9). E9 is
  independent and can land any time, but reviewing the callout three times
  costs more than reviewing it once.
- **E3 last, with the dashboard in mind.** The windowing helper is written
  once for both lists. If the dashboard's drill-down list ships first without
  it, the dashboard inherits the full-render cost and pays for the refactor
  twice.

## Decisions waiting on the user

| Entry | Decision | Blocks |
| --- | --- | --- |
| **E1** | Open the change? The six-pin test group is specified (§11.3) and re-verified. The fix is one `NFKC` call at the cleansing boundary plus the tests | E1 |
| **E2** | Open the change with scope = steps 1–4 (no windowing, no debounce)? | E2 |
| **E3** | Open the change (harness + windowing together)? Sequence after E2? | E3 |
| **E4** | Confirm the narrowed 國 rule: case-registered OR exact-`twur_name` name; the 451 stage+date-bound badges go. Confirm with it whether the name route covers the 權利變換 擬訂 node (大安590 node 884) — its 案名 differs from `twur_name` by one word | E4 |
| **E5** | Confirm: the 使照 event keeps 國 only when the city case has no 使照 and the view does (288 go, 2 stay)? | E5 |
| **E7** | Confirm the joined callout shows one box per section, with per-section diffs — and whether the merged 基地面積 rows stay or go | E7 |

One change opens per the user's word — a recommended option is not a decision.
`openspec list` before proposing: another session may already have opened one.

## Cross-references

- The measurements: `docs/DashboardNUXUI.md` §6 (render cost), §7
  (accessibility), §8 (scope), §11 + batch D D16a–D16d (the ideographs), §13
  (the gate).
- The probes: `scripts/probe_nfkc_effect.py`,
  `scripts/probe_nfkc_plan_cases.py`, `scripts/probe_nfkc_live_case.py`,
  `scripts/probe_compat_field.py`, `scripts/probe_compat_name_id.py`,
  `scripts/probe_compat_index_core.py`, `scripts/probe_nfkc_keyword_exposure.py`
  (all read-only, offline).
- The lesson that scopes this batch: **a scope is a claim about what was not
  measured** (batch D D16d; `docs/DashboardNUXUI.md` §11.4; the memory
  `scope-is-a-claim-about-what-was-not-measured`).
