# Project inspection — Batch E · collected 2026-11-12, extended twice the same day (E1–E13)

Nine work items. E1–E3 were carried over from the dashboard exploration notes
(`docs/DashboardNUXUI.md`); E4–E9 were collected the same day from the user's
badge and callout findings. The board follows the
`docs/inspection-batchD.md` structure: findings, then the integrated plan,
then the decisions that gate execution.

**Source and state.** The notes measured everything E1–E3 need and left three
items open (its §13: the unverified column — answered, Option D, the column is
omitted; **Part 1 scope — E2**; the compatibility-ideograph fix — **E1**; the
windowed list — **E3**). E4–E9 came from the user's 2026-11-12 review of the
badges (items 1–3) and the area-split callout (items 4, 4a–4d, 5); E10–E13
came from the same day's second round (item 6 the 懷生16 missing case, item 7
the 施工中 badge, item 8 the dead-set edge rule, item 9 the national
re-crawl). All measured on the payload at `7a1102a`: **1,444 records /
680 projects**, 統計至 2026-10-28. The notes' §14.-1 records what moved with
the 河堤399 merge.

**The items are separate openspec changes or direct fixes, not one.** E1 is a
pipeline defect independent of the UI work. E2 and E3 are viewer work that
shares one harness upgrade. E4/E7 are openspec changes (spec scenarios and a
payload field change); E5/E6/E8/E9/E11/E12 are direct fixes at named sites.
All decisions are made (2026-11-12, the user) — the decision table records
them; the changes open per the standing rule. E10's sweep probe and E13's
phase-1 probe run before (or alongside) the change work. The batch keeps the
items separate so one change's review never blocks the others.

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

**Where the change lands — decided 2026-11-12 (user): the pipeline emits the
resolved binding.** The rule computes once, at graph build (`urtpe/graph.py`),
and the payload carries the result per node: a node whose case is in
`view_verified_case_ids`, or whose 案名 equals the project's `twur_name`, or
which qualifies through the 擬訂 section+parcel fallback (below), carries
`national_badges: true` (name open — the binding labels could ride instead,
but the badge is boolean at render). The viewer reads the field and renders
`getNodeMilestoneBadges` from it; `bindNationalLabels` /
`nationalLabelKey` (`viewer/app.js:149-172`, `:25-35`) retire — the
stage+date matcher is gone, not re-implemented client-side. Cost measured:
one boolean on 1,444 nodes ≈ 16 KB on a 9.3 MB payload. The rule living in
one place means the pipeline's tests pin it (the six-pin shape of E1, not
the viewer-only alternative).

**The name route's fallback (decided 2026-11-12, user): 嚴格 + 擬訂區段後備.**
The exact-name route covers the 擬訂 事業計畫 node (大安590 node 1257). The
權利變換 擬訂 node (node 884, 案名 differing from `twur_name` by one word)
keeps its badge through a **section+parcel fallback**: a 擬訂 node whose
(section, first-parcel) matches the `twur_name`'s parses as the same unit.
This is anchored on the name's own land core, not on dates — it is not the
stage+date binding the rule replaces.

| Population (over the 680-project payload, 2026-11-12) | Count |
| --- | --- |
| nodes with 國 today (per-label binding OR view-verified) | **1,186** |
| nodes with 國 under the rule, exact name + registration only (the pre-fallback measure) | 735 |
| nodes with 國 under the decided rule (with the 擬訂 section+parcel fallback) | **800** |
| nodes that lose it (stage+date-bound only) | **402** — 文林838-1 node 433 is one |
| nodes that gain it through the fallback | **16** — 擬訂 nodes whose land core matches the title and whose 案名 drifts further than one word ((原N筆), 權利變換-only titles) |

The pre-fallback measure read "0 gain" because the 擬訂 nodes' dates always
matched the national 核定日期 labels — the binding found them. The fallback
finds **16 more**: 擬訂 nodes the binding MISSED (their dates differ from the
title's by more than the tie-break window) but whose land core matches it.
What the rule buys is **precision**: a 國 badge means "the view page names
this unit", not "a date matched".

**Spec surface.** `viewer-related-links` (the badge requirement's scenarios
change; the archive guard needs the live body carried) and
`official-link-discovery` (what `view_verified_case_ids` asserts; the
`national_badges` emission joins the payload requirement).

**Form:** openspec change (pipeline emission + viewer render + one re-emit).

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
corroborated case loses its badge sentence. The same rule reaches the
推動歷程 card (E6): a 使用核發日期 row keeps its per-row 國 only in the 2
national-only projects — the 288 corroborated rows lose it there too
(measured 2026-11-12: 290 rows carry 使用核發日期; 288 corroborated, 2
national-only).

---

## E6 — the 國 badges in the graph and on the 推動歷程 card become links; the card's badge follows the graph rule (user, 2026-11-12)

**The user's rule (item 1, refined the same day).** Two badge sites become
links, and the card's per-row 國 adopts the graph badge's rule:

| Site | Today | Change |
| --- | --- | --- |
| Node badges — 北 (`viewer/app.js:184`), 國 (`viewer/app.js:193`) | `<a>` with `href` | **works — unchanged** |
| Construction-event 國 (`viewer/app.js:1398`) | `<span title="國土署里程碑">` | **becomes `<a href={twur}>`**, title `view/<id>` |
| 推動歷程 card — summary badge (`viewer/app.js:697`) and per-row badge (`:704`) | `<span>` | **become `<a href={twur}>`** |
| 階段辦理過程 card badges (`:715`–`:731`) | `<span>` | **stay spans** — they label the Taipei card's source, and the Taipei case link lives on the node's 北 badge |

**The card badge's rule joins E4/E5's vocabulary.** The 推動歷程 card's
per-row 國 renders on every national row today. Under the graph badge's rule
the row badge fires on the rows the view page names by the same standard —
practically: a 使用核發日期 row keeps its 國 only in the 2 national-only
projects (E5's survivors); the other national rows (核定日期 labels, 申請
labels) keep theirs, because the card *is* the national page's data and the
badge there says "this row is the national page's". The rule that changes is
the 使用核發日期 row: corroborated rows lose the badge, exactly as the event
row does. The summary badge (the card's title row) stays — the whole card is
the national page's content.

**Form:** direct `fix:`, two template sites (`viewer/app.js:1398`, `:697`,
`:704`), landed with E5 (one rule, one vocabulary). The `viewer_smoke.js`
overlap check walks badges; the `<a>` keeps the same footprint.

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

## E10 — 懷生16: a live -A區 plan case the parcel search never returns (user, 2026-11-12)

**The user's finding (item 6).** 大安區-懷生段二小段-16地號等6筆 shows a case in
the platform's own 相關連結 that this dataset has never held: **`09503201`** —
擬訂…事業計畫案-A區 (and, on the platform, re-titled 變更…事業計畫案-A區; one id,
two titles over its life).

**Measured 2026-11-12:**

| Check | Result |
| --- | --- |
| `links.taipei` holds it | **no** — 8 ids, `09503200/03/04/05/06/08/10`, `11301151` |
| `candidate_names`, `case_headers`, the cache's `result.json` | **no** — the string appears nowhere in the file |
| the cached `view.html` (view/53) | **no** — names `09503200` only |
| the city's parcel search (`search_taipei_cases_api('懷生段二小段','16')`, live) | **no** — returns exactly the 8 held ids |
| the milestone API for `09503201` (live, one request) | **live** — 14 fields, 申請計畫 2006/11/01, 核定 2007/12/06 |

**The shape.** The platform's parcel-search index omits a real case; the case
is reachable only from a sibling case's page. This is the C8b shape
(`docs/inspection-batchBC.md`: 新光101, 寶清599, 敦化585-11 were found by
probing sibling case ids) — measured again here on a live case.

**The user's rule: join it.** The fix layer is the one batch D step 6b built
(`second-id-source`): confirm each candidate id by its header, then add it to
`city_case_ids` in a refresh step. The candidate here comes from the sibling
page's 相關連結 — a source the discovery does not read today.

**The question the change must answer first: how wide is the gap?** One case
is measured. The candidate source (sibling 相關連結) is not harvested at all —
the `view.html` parse takes the view page's links, not the case pages'. A
sweep that fetched each project's first case page and read its 相關連結 would
find every sibling-referenced id (WAF-permitting). Measure the gap before
opening the change: the corpus's 623 twur-bearing projects carry case ids
whose pages may name siblings; each is one request.

**Form:** measurement first (the sweep probe), then an openspec change
(`official-link-discovery` — the second-id-source rule gains the sibling-page
source) + cache refresh + one re-emit. The 懷生16 fix itself rides the change.

---

## E11 — no 施工中 badge in 相關連結 (user, 2026-11-12)

**The user's rule (item 7).** The 相關連結 status badge names a case's
*state of approval*, not its construction progress. 施工中 renders there 463
times (`scheduleBadgeText`, `viewer/app.js:477` — everything except
已核准/已核定 renders; 無 → [無], NA → [NA]).

**Measured** (case_schedules corpus-wide, 2026-11-12): 施工中 **463**,
自行撤回 131, 已核准 712, 已駁回 40, 已失效 74, 審查中 82, 已核定 24,
已完工 5, 完成成果備查 1, 已撤銷 1, 無 16.

**The change:** `scheduleBadgeText` (or its call site at
`viewer/app.js:1573`) drops 施工中 from the 相關連結 badge list. The other
statuses keep their badges: a reviewer needs 已駁回/自行撤回/已失效/審查中 in
this list — they are the approval states the list exists to name. 施工中
stays visible where it belongs: the construction-stage chip and the dead-end
chip on the graph node, and the dashboard's status column.

**Scope guard:** the user's word was 施工中 (the user wrote [已施工]; the
payload's value is 施工中 — same status, the badge text differs from the
schedule value by one character). The change drops exactly that value, not
已完工 (5 cases — a completion state a reviewer may still want named here;
the decision table asks).

**Form:** direct `fix:` + one test (the badge contract test in
`tests/test_viewer_dashboard.py`-style: the 相關連結 render of a 施工中 case
carries no badge; an 已駁回 case keeps one).

---

## E12 — no edge below a dead node, 無 joins the dead set (user, 2026-11-12)

**The user's rule (item 8).** A node whose case is 已駁回 / 自行撤回 / 已失效 /
**無** renders no edge below. The D4b rule (2026-11-05) already refuses the
under-fallback for the first three plus 已撤銷 — the dead set lives at
`viewer/app.js` `isDeadEnd`:

```js
const isDeadEnd = s => s === "已失效" || s === "自行撤回" || s === "已駁回" || s === "已撤銷";
```

**無 is not in it.** Measured (2026-11-12):

| Population | Count |
| --- | --- |
| orphan nodes with schedule 無 | **11** — the D4b refusal does not cover them |
| orphan nodes with a dead schedule (covered) | 240 |
| recno nodes whose first case is 無 | **0** — the approval nodes never carry 無 |

The 11 無 orphans can take a dotted edge below today (`nearestRecnoRowUnder`
runs when `isDeadEnd` says no). Under the rule they render undotted, like the
240 dead orphans.

**The pipeline side must agree.** `schedules.py`'s dead set
(`TERMINAL_SCHEDULES` / `_DEAD_SCHEDULES`) gained 已撤銷 in
`revoke-dead-schedule`; 無 is a *missing* state, not a terminal one — the
two sets serve different rules (chain-edge refusal vs status derivation).
The viewer-side `isDeadEnd` gains 無; the pipeline sets stay as they are.

**Form:** direct `fix:` — one entry in `isDeadEnd` + the test (a 無 orphan
with only dead neighbours renders no dotted edge). The smoke harness's
overlap checks count dotted edges; the fixture gains a 無 orphan.

---

## E13 — the national re-crawl, under the WAF cap (user, item 9)

**The state.** The national portal's crawl is WAF-capped; the corpus holds
110 index entries and names 622 view ids. The last full sweep is the
`fetch_remaining_national_portal.py` pattern: title search per project,
60–180 s sleeps (revert to 180–300 s on a WAF reset), 3 retries with
exponential backoff, stop at 06:30, log to `fetch_failures.json`.

**What a re-crawl would touch, measured 2026-11-12:**

| Population | Count |
| --- | --- |
| projects with no twur link (the sweep's own target) | **57** |
| the no-match ledger's census | has-approved 16, mixed/other 32, never-approved 15, no-cases 6, miss 5 |
| view ids named by the payload but absent from the 110-entry index | **514** (622 − 108) |
| projects whose `no-cases` verdict may have flipped since their last probe | 3 of 6 (河堤399, 吳興163-2, 懷生928 gained pages through other routes) |

**The plan, three phases — each gated on the previous one's failure rate:**

1. **Probe the WAF's current temper (1 evening).** The sweep's own
   `--max-projects 10` against the 57: if the reset window has tightened
   (a `Request Rejected` inside the 180 s spacing), the pacing is the
   finding, and phase 2 waits.
2. **The 57 twur-less projects (the sweep as-is).** Paced 180 s, 06:30
   deadline, nightly until the set stops moving. The E10 sibling-page source
   joins here: a project whose title search misses still gets its first
   case page read, and the 相關連結 links it names are candidates.
3. **The 514 unindexed view ids (a second sweep mode).** The index is the
   bulk entry point; the 514 were resolved before the cap or never indexed.
   The sweep's title search re-finds them one by one — this is the long
   tail, run only when phase 2's failure rate stays under the threshold the
   first two nights set.

**The rules that do not change.** The sweep writes into the same
`.link_cache` (single-writer lock); it never ingests; every write lands in a
cache the next `--from-js` re-emit reads. `check_deploy.py` after the
re-emit. The 14-day TTL on `no_match_ledger.json` governs re-probes — the
re-crawl is not a second ledger.

**Form:** probe first (phase 1 is read-mostly), then run the existing sweep —
no openspec change unless the sweep gains the E10 sibling-source (that edit
is E10's change). The re-emit after the crawl rides the usual path.

---

## Order

| Step | Item | Priority | Form | Depends on | Notes |
| --- | --- | --- | --- | --- | --- |
| 1 | **E1** — NFKC folding at the cleansing boundary; the six-pin test group | **P1** | openspec change (`data-cleansing`) + pytest | — | Independent of the UI work; smallest; its test group is fully specified |
| 2 | **E2** — URL write-back + keyboard, steps 1–4 only | **P1** | openspec change (viewer) + harness cases | — | The read half exists; this adds the write half and the focus path |
| 3 | **E11** — drop 施工中 from the 相關連結 badges | **P1** | direct `fix:` + test | — | One value off one badge list; 463 badges |
| 4 | **E12** — 無 joins `isDeadEnd`; the 無 orphans lose the dotted edge | **P1** | direct `fix:` + test | — | One entry in the dead set; 11 orphans |
| 5 | **E4** — the 國 badge rules re-stated; the pipeline emits the resolved binding | **P1** | openspec change (`official-link-discovery` + `viewer-related-links`) + pipeline emission + viewer + re-emit | — | 451 badges move; `national_badges` per node (≈16 KB); the 擬訂 section+parcel fallback keeps node 884 |
| 6 | **E5** — the construction-event 國 badge: national-only, not corroborated | **P1** | direct `fix:` + viewer test | E4 (one badge vocabulary) | 288 badges go, 2 stay |
| 7 | **E6** — badge links: the event 國 becomes a link to view/<id> | **P2** | direct `fix:` | E5 | One element swap |
| 8 | **E7** — the joined node's 北 badge covers both area cases; the callout splits by section | **P2** | openspec change (viewer + `case-record-join`) | — | 30 joined nodes, 28 area pairs |
| 9 | **E8** — area labels [A區]/[B區] beside the badge or callout | **P2** | direct `fix:` | E7 | Derives from E7's section split |
| 10 | **E9** — callout values never wrap; the gutter grows to content | **P3** | direct `fix:` + harness measurement | — | 744 of 1,431 callouts wrap; the widest value needs 302 px |
| 11 | **E10** — the sibling-page id source; 懷生16's 09503201 joins | **P2** | probe first, then openspec change (`official-link-discovery`) + cache refresh + re-emit | the WAC temper probe (E13 phase 1) | The sweep-scale gap is unmeasured — measure before opening |
| 12 | **E13** — the national re-crawl: WAF probe → the 57 → the 514 | **P2** | probe + the existing sweep; no openspec change | E10's sibling-source edit, if agreed | Phase-gated on the failure rate |
| 13 | **E3** — harness geometry stubs, then the windowed list | **P2** | openspec change (viewer + harness) | E2 | Lands last; the dashboard reuses its helper |

**Why this order.**

- **E1, E2 first — unchanged.** E1 is a pipeline defect with a fully
  specified test group. E2 needs the harness cases E3 builds on. Neither
  touches the badge or callout work.
- **E11 and E12 are one-liners and go before the badge redesigns.** Each is a
  named value in one set (`scheduleBadgeText`'s list; `isDeadEnd`). Landing
  them first means E4–E9 review against a viewer that already reads the dead
  set the user expects.
- **E4 before E5/E6.** Both reshape the badge vocabulary; E4 defines when a
  國 exists (emitted per node), E5/E6 remove and link the badges that
  contradict it. E4's re-emit carries the new field; E5/E6's viewer edits
  read it.
- **E5 and E6 are one edit site.** The event badge at `viewer/app.js:1398`
  changes from `natCorroborated`-driven span to `nationalHit`-driven link in
  the same template; the 推動歷程 card's badges (`:697`, `:704`) join the
  same edit, and its 使用核發日期 rows adopt E5's rule (288 corroborated
  rows lose the badge there too).
- **E7 → E8 → E9 are one review unit** with three separable edits. E9 is
  independent and can land any time, but reviewing the callout three times
  costs more than reviewing it once.
- **E10 probes before it opens.** One case is measured; the sweep-scale gap
  is not. The sibling-page source (one request per project) is a new crawl
  surface, and E13's phase-1 WAF probe measures whether that surface is
  affordable at all this week.
- **E13 runs last and nightly.** It writes nothing but caches; its re-emit
  rides the usual path. Its phase-1 probe is also E10's gate, so the probe
  runs before E10 opens.
- **E3 last, with the dashboard in mind.** The windowing helper is written
  once for both lists.

## Decisions made (2026-11-12, user)

| Entry | Decision | Blocks |
| --- | --- | --- |
| **E4** | **嚴格 + 擬訂區段後備** — the 國 rule: case-registered OR exact-`twur_name` OR a 擬訂 node whose (section, first-parcel) matches the title's land core. The 451 stage+date-bound badges go; node 884 (大安590) keeps its badge through the fallback. **The pipeline emits the resolved binding** (`national_badges` per node) so the rule lives in one place and the pipeline tests pin it | E4 (opens) |
| **E5** | **同意：national-only.** The 使照 event's 國 fires only when the city has no 使照 and the view does (288 go, 2 stay) | E5 |
| **E6** | **Graph event 國 + 推動歷程 card badges become links** (to view/<id>); the card's per-row 國 follows the same rule as the graph badge; the 階段辦理過程 card badges stay spans | E6 |
| **E7** | **在負載中按案例發出** — the payload carries implementation keyed by case id on joined nodes; the viewer renders one box per section, diffs compared within a section | E7 (opens) |
| **E10** | **同意：先探測** — the one-request-per-project sibling sweep sizes the gap before the change opens | E10 |
| **E1** | **立即開啟變更** — the NFKC change opens now | E1 (opens) |
| **E2** | **開啟，步驟 1–4** — the Part 1 change opens with URL write-back + keyboard, no windowing/debounce | E2 (opens) |
| **E3** | **在 E2 之後開啟** — the windowed list follows E2's harness cases | E3 |
| **E8** | **徽章 + 標註** — the [A區]/[B區] label renders beside the 北 badge AND on the callout section headers | E8 |
| **E9** | **同意：無換行，與 E7/E8 一起** — the 160 px cap goes; the gutter takes the widest box; the D2 wrap-height model retires; lands with E7/E8 as one review unit | E9 |
| **E11** | **移除兩者：施工中 + 已完工** — the 相關連結 badge names approval states only (施工中 463, 已完工 5 go; 審查中/dead states stay) | E11 |
| **E12** | **同意：無加入死集合** — `isDeadEnd` gains 無 (11 orphans lose the dotted edge); the pipeline's TERMINAL/_DEAD sets stay unchanged | E12 |
| **E13** | **同意：今晚探測** — phase-1 runs tonight (`--max-projects 10` on the 57, paced 180 s) | E13 (probe opens) |

## Decisions waiting on the user

None — every open question in this batch was answered on 2026-11-12. The
changes open on the user's word, per the standing rule; the table above
records which are cleared to open.

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
- E10's precedent: batch B/C's C8b (新光101, 寶清599, 敦化585-11 — plan cases
  the parcel search does not index, found by probing sibling ids) and batch D
  step 6b (the second-id-source change that landed the confirm-by-header
  rule).
- E13's tool: `scripts/fetch_remaining_national_portal.py` (the sweep; its
  header documents the pacing, the retry ladder and the 06:30 deadline).
- The lesson that scopes this batch: **a scope is a claim about what was not
  measured** (batch D D16d; `docs/DashboardNUXUI.md` §11.4; the memory
  `scope-is-a-claim-about-what-was-not-measured`).