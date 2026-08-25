# Design — Complete Viewer Field Labels

## Context

Actors: viewer users (planners reviewing renewal projects in the browser) read
the 執行階段 / 獎勵資料 cards rendered by `viewer/app.js` from the emitted
`implementation`/`rewards` objects (schema v2). Domain events in play: stage
approvals (核定 records forming the graph nodes) and construction-phase events
(建照核發 / 開工 / 使照) emitted as project-level milestones. System boundary:
display-only — the batch pipeline (PDF → parse → cleanse → merge →
`projects.json` + `projects.data.js`) is untouched; this change sits entirely
inside the browser-viewer adapter.

Current state: `IMPL_LABELS`/`REWARD_LABELS` were transcribed from one probed
case whose reward flags were empty, so ~37 of 41 observed reward keys plus the
3 third.ashx date fields render as raw English keys. The complete official
label inventory is already captured and frozen in `docs/facts_2_portals.md`
§12.1 (extracted 2026-08-25 from the r_progress_detail.aspx DOM via
`id="detail_<field>"` pairing). See proposal.md for motivation.

## Goals / Non-Goals

**Goals:**

- Every key present in today's 691-cache corpus renders with its official
  Chinese label (or its retained semantic label).
- Construction progress (建照→開工→使照) and the anchor record's key stats
  (實施方式/基地面積/原戶數) are visible directly in the graph, without opening
  milestone cards.
- Zero risk to data: no fetch, cache, emission, or schema change.
- Cheap future maintenance: the inventory lives in one frozen doc section that
  new keys can be diffed against.

**Non-Goals:**

- No i18n/localization framework — the existing two const tables stay the
  mechanism.
- No `phase` surfacing, no top.ashx integration, no pipeline changes (those
  belong to the sync-model change).
- No retro-editing of cached payloads or re-render of historical data beyond
  what regeneration already does.

## Decisions

1. **Hybrid label naming** — keep the five existing informative semantic labels
   (`F`=允建容積, `F0`=基準容積, `F3`=都市更新獎勵, `F5`=其他容積獎勵,
   `F5_3`=人行步道面積); all other keys take the official §12.1 label verbatim
   (including △F accounting notation for the remaining F-family).
   *Alternative rejected:* full official notation — would regress five
   informative names users already see; *full semantic* — invents unofficial
   wording for the remaining ~35 keys with no source to verify against.
   *(Amended during apply: F/F0 originally overlooked as retained semantics.)*

2. **Transcribe from facts §12.1 only; no network work** — the DOM capture is
   done and recorded; implementation is a closed transcription task.
   *Alternative rejected:* re-fetching the detail page at build time — adds
   network dependency for zero information gain.

3. **Extend the existing const tables in place** (`REWARD_LABELS`,
   `IMPL_LABELS`), preserving the `labels[key] || key` fallback in
   `renderObjectCard` for unknown keys.
   *Alternative rejected:* restructuring into per-tab label modules — no
   behavioral gain for a two-table file.

4. **Verification by corpus diff, not unit tests** — the repo has no JS test
   harness; instead the implementation tasks include a one-off scan comparing
   every key in `data/.link_cache/*/result.json` rewards/implementation
   payloads against the two tables (all known keys mapped ⇒ pass). This
   mirrors how the §12 #9 investigation itself was validated.

5. **Chain slots and provenance mapping (viewer-side)** — the chain has three
   fixed slots read from already-emitted project-level fields: 建照核發日期 and
   開工日期 from `milestones_taipei`; the 使照 slot prefers `Ulic_Date`
   (使照核發日期) and falls back to national 使用核發日期 when Taipei has none. A
   node shows the 國 badge exactly when its value comes from (or is
   corroborated by) `milestones_national`. Provenance is decided by label
   name in the viewer — no per-date source field exists in the emission.
   Carrying-case provenance: construction events frequently belong to a
   sibling case, not the anchor approval (仁愛段114地號 — dates only on case
   08610011 while 現況 anchors 08610013). The emitted `implementation.case_id`
   supplies the carrying case; 開工/使照 nodes display it when their value
   exactly equals that payload's date. 建照核發日期 has no per-case breakdown
   in the emission and stays unlabeled.
   *Alternative rejected:* per-case anchoring via `_match_case_by_date` —
   correct but belongs to the chimera-emit-fix / sync-model work ([2]/[5]);
   this change renders what the dataset already says.

6. **Viewer-only rendering, events in the timeline (final iteration)** —
   construction events render as dated pseudo-nodes in a dedicated
   E) 執行階段 column, interleaved chronologically with the approval rows;
   each event's thin attribution edge points at the latest approval dated on
   or before the event (the plan in force), colored by source portal
   (pink Taipei / green national); the 使照 event renders a western date
   (民國 +1911) so display and sorting stay consistent. Per-record callouts
   are compact and collision-dodging: six candidate spots around the carrying
   record, first non-overlapping wins, tail always pointing at its node —
   verified zero occlusion. The whole assembly lives in the graph's scaling
   coordinate space so the uniform-scale guarantee (history-graph spec) holds.
   *Iteration history:* side lane → reserved lane + elbow leader →
   timeline-embedded events (user mockups); each step simplified the mental
   model while strengthening chronological reading. *Alternative rejected:*
   emitting new graph nodes from `graph.py` — changes the data contract for a
   presentation concern (the one emission addition is the per-record
   snapshot, which the callouts genuinely need); *proximity floating next to
   the anchor* — cannot guarantee zero overlap on dense multi-column families.

7. **Test strategy unchanged** — pytest structural tests over `app.js`
   constants extend naturally: assert the chain slot table, the national
   provenance label set (incl. 使用核發日期), and the callout field list exist with
   expected contents. Node v24 exists, but introducing a JS test runner for two
   renderers is out of scope; behavior verification stays corpus sweep +
   visual spot-check.

8. **相關連結 案名 labels via per-node anchoring (viewer-only)** — each Taipei
   link's 案名 comes from joining `project.links.taipei` case_ids against
   `nodes[].links.taipei` (the date-anchored linkage from §6.6) and reading
   that node's `case_name`; the national link shows the anchor (現況)
   record's 案名 since a twur view aggregates all revisions. Unanchored
   case_ids keep the generic label.
   *Alternative rejected:* storing case_name per city case in caches/emission —
   `case_names` is already collected in links.py:536-545 but dropped before
   persistence; wiring it through is a schema change that belongs with the
   sync-model work, not this display change.

## Risks / Trade-offs

- [Platform changes a label wording later] → §12.1 is dated and provenance-
  tagged; a future sweep re-captures the same way. Cosmetic-only impact.
- [New ashx keys appear in future fetches] → fallback renders the raw key;
  visible but non-breaking. Additions are one-line table entries.
- [△F(㎡) notation confuses lay readers] → accepted trade-off recorded above;
  switching individual labels later is trivial once semantics are confirmed
  against the 容積獎勵 documentation.
- [Project-level construction dates may reflect the wrong sibling case before
  chimera emit-fix [2] lands] → accepted: chain shows what today's dataset
  states; re-anchoring per case is deferred to [2]/[5] and needs no spec
  change here.
- [Callout clutter on dense multi-column families] → collision-dodging spots
  (below/above × left/right, two depths) with measured node rects; browser
  bounding-box sweep on multi-record families gates the layout constants.
- [Badges above the label line could clip the row above] → badge row sits at
  y −27 within the 64px row pitch; bounding-box spot-check covers it.
