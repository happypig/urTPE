# Project inspection — Batch E · collected 2026-11-12

Three work items, carried over from the dashboard exploration notes
(`docs/DashboardNUXUI.md`) as execution-ready findings. The board follows the
`docs/inspection-batchD.md` structure: findings, then the integrated plan,
then the decisions that gate execution.

**Source and state.** The notes measured everything this batch needs and left
three items open (its §13: the unverified column — answered, Option D, the
column is omitted; **Part 1 scope — this batch's E2**; the compatibility-
ideograph fix — **this batch's E1**; the windowed list — **this batch's E3**).
Payload at `7a1102a`: **1,444 records / 680 projects**, 統計至 2026-10-28.
Every figure below was re-verified against that payload on 2026-11-12; the
notes' §14.-1 records what moved with the 河堤399 merge.

**The items are three openspec changes, not one.** E1 is a pipeline defect
independent of the UI work. E2 and E3 are viewer work that shares one
harness upgrade. The notes say so (§11.3, §13); the batch keeps them separate
so one change's review never blocks the other two.

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

## Order

| Step | Item | Priority | Form | Depends on | Notes |
| --- | --- | --- | --- | --- | --- |
| 1 | **E1** — NFKC folding at the cleansing boundary; the six-pin test group | **P1** | openspec change (`data-cleansing`) + pytest | — | Independent of the UI work; smallest; its test group is fully specified |
| 2 | **E2** — URL write-back + keyboard, steps 1–4 only | **P1** | openspec change (viewer) + harness cases | — | The read half exists; this adds the write half and the focus path |
| 3 | **E3** — harness geometry stubs, then the windowed list | **P2** | openspec change (viewer + harness) | E2 (the harness cases E2 adds are the base) | Lands last; the dashboard reuses its helper |

**Why this order.**

- **E1 first.** It is a pipeline defect with a fully specified test group, and
  every other change that touches names or counts benefits from the fold being
  in. It needs no harness work and no viewer work.
- **E2 before E3.** Both need harness cases; E2's are smaller (focus and URL
  assertions). E3's geometry stubs build on a harness that already knows how
  to drive the list, and E3 must keep E2's deep-link write working — landing
  E3 first would mean E2 reviews against a moving base.
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
