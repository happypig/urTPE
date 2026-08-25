# Tasks — complete-viewer-field-labels

> Adapter-layer note: every task below is browser-viewer (adapter) work; this
> change touches no domain/pipeline logic, so there are no domain-side task
> groups to separate.

## 1. Label-coverage regression test (write first)

- [x] 1.1 Add `tests/test_viewer_labels.py`: parse `REWARD_LABELS` and
      `IMPL_LABELS` out of `viewer/app.js` (regex over the const blocks) and
      assert every key of the official inventory (facts §12.1: all fourth.ashx
      volume/incentive keys — `F`, `F0`, `F1..F6`, `F4_1..F4_3`, `F5_1..F5_6`,
      `Park_Area`, `Park_Cars`, `name_reward_no`, and the ~20 incentive keys —
      plus `Eng_Start_Date`/`Ulic_Date`/`Report_Date`) has a non-empty mapping;
      allow exactly five documented semantic exceptions (`F`, `F0`, `F3`,
      `F5`, `F5_3`) to carry their retained labels instead of official
      accounting notation
- [x] 1.2 Run pytest — expect failure (red) before implementation
- [x] 1.3 Extend `tests/test_viewer_labels.py` with structural assertions for
      the graph annotations: `app.js` defines (a) a construction-chain slot
      table for exactly 建照核發日期 / 開工日期 / 使照核發日期, (b) a national
      provenance label set containing 使用核發日期 (drives the 國 badge), and
      (c) an implementation callout field list of exactly `Exe_Way`,
      `Base_Area`, `Old_Doors`

## 2. Implementation (viewer/app.js only)

- [x] 2.1 Extend `REWARD_LABELS` with the missing entries transcribed verbatim
      from facts §12.1 (keep `labels[key] || key` fallback untouched)
- [x] 2.2 Add `Eng_Start_Date`=開工日期, `Ulic_Date`=使照核發日期,
      `Report_Date`=成果報備日期 to `IMPL_LABELS`
- [x] 2.3 Implement the construction-phase chain renderer: solid vertical
      建照→開工→使照 node chain to the right of the source recno node, drawn
      only for existing dates, with 國 badge on national-mapped slots
      (使照 falls back to 使用核發日期 when 使照核發日期 absent)
- [x] 2.4 Implement the implementation summary callout: dialog box attached
      top-right of the source recno node listing 實施方式/基地面積/原戶數 rows
      that have values, hidden when none do; styles keep chain, callout, and
      node badges legible in the scaling coordinate space
- [x] 2.5 Run pytest — green

## 3. Acceptance

- [x] 3.1 Corpus sweep: one-off scan confirming every implementation/rewards
      key across `data/.link_cache/*/result.json` resolves to a label in the
      updated tables (zero raw-key rows for inventory keys); also report how
      many projects would render the chain and the callout (sanity counts)
- [x] 3.2 Viewer spot-check on two projects with populated rewards (e.g.
      南港區-南港段二小段-671-6地號等521筆 [10806041], 中山區-吉林段三小段-811
      [09605192]): 獎勵資料 card shows incentive labels (時程獎勵,
      綠建築標章之建築設計, …), 執行階段 card shows 開工日期/使照核發日期/
      成果報備日期 instead of English field names
- [x] 3.3 Graph spot-check on a completed multi-record family: chain renders
      right of the anchor with correct dates and 國 badge only where
      national-mapped; callout shows 實施方式/基地面積/原戶數; a no-data project
      renders neither annotation
- [x] 3.4 Update facts §12 #9 resolution note: viewer label completion landed
      (change name + date)

## 4. 相關連結 案名 labels (test first)

- [x] 4.1 Extend `tests/test_viewer_labels.py`: assert `app.js` defines a
      related-link label builder (`buildRelatedLinkLabels`) whose source joins
      `nodes[].links.taipei` case_ids to `case_name` and picks the 現況
      anchor's 案名 for the national link
- [x] 4.2 Run pytest — expect failure (red) before implementation
- [x] 4.3 Implement the builder + wire into the 相關連結 section: Taipei links
      get `— <anchored record's 案名>`, the national link `— <anchor 案名>`,
      unanchored case_ids keep the generic label; styles for the suffix

## 5. Acceptance — 案名 labels

- [x] 5.1 Browser spot-check on 北安段一小段-14-2 (4 anchored cases → 4 distinct
      案名) and on an unanchored/unresolved project (generic labels, no error)

## 6. Annotation lane + callout tail (test first)

- [x] 6.1 Extend `tests/test_viewer_labels.py`: assert `app.js` draws a leader
      (`chain-leader` class) from the source recno through the bottom margin
      into the annotation lane, and a callout tail (`callout-tail`) joining the
      dialog to that leader; assert `app.css` styles both classes
- [x] 6.2 Run pytest — expect failure (red)
- [x] 6.3 Implement reserved-lane geometry: lane right of all columns, elbow
      leader (recno → bottom margin → lane → chain), chain stacked in-lane,
      callout under the chain with tail onto the leader; extend viewBox for
      lane width and corridor height

## 7. Acceptance — non-overlap

- [x] 7.1 Browser collision check on multi-record families (e.g. 北安段14-2,
      4 nodes / 3 columns): zero bounding-box intersections between annotation
      elements (chain/leader/callout/tail) and approval nodes or labels

## 8. Carrying-case provenance on chain nodes (test first)

- [x] 8.1 Extend `tests/test_viewer_labels.py`: assert the chain builder reads
      `implementation.case_id` and only labels a slot when its value exactly
      equals that payload's date
- [x] 8.2 Run pytest — expect failure (red)
- [x] 8.3 Implement provenance suffix: 開工/使照 nodes show the carrying
      case_id (e.g. 案08610011) when provable; 建照 stays unlabeled

## 9. Acceptance — provenance

- [x] 9.1 Browser check on 大安區-仁愛段四小段-114地號等2筆: 開工/使照 nodes show
      案08610011 while the leader still attaches to the 現況 recno 1345 node

## 10. Per-record implementation emission (test first)

- [x] 10.1 `tests/test_links.py`: record whose anchored case carries a
      third.ashx payload gets an `implementation` snapshot (with case_id);
      sibling with empty payload carries none
- [x] 10.2 Implement in `urtpe/links.py` attach flow (additive optional node
      field; schema_version unchanged) — green

## 11. Graph redesign: events-in-timeline + per-record callouts + link migration (test first)

- [x] 11.1 Structural tests: `event-edge`/`event-link`/`phase-header`/
      `callout-diff`/ghost markers present in app.js+css; superseded markers
      (`chain-leader`, `related-links`, `buildRelatedLinkLabels`) absent;
      event labels wrapped as hyperlinks; 北/國 badges hyperlinked (red)
- [x] 11.2 Implement: construction events as dated pseudo-nodes in an
      E) 執行階段 column (chronological rows); attribution edges colored by
      source (pink Taipei / green national) to the latest approval dated on
      or before the event; 開工→使照 connector in the 使照 source colour;
      event labels hyperlinked to their portal; provenance sub-labels kept;
      dashed styling for 事業概要 records;
      per-record callouts tail-attached to carrying records with red
      diff vs the nearest earlier carrying record; 北/國 badges hyperlinked;
      remove 相關連結 section, buildRelatedLinkLabels, and the lane
      chain/leader. (Mockup grey grid lines and A–E header texts are
      annotation aids only — not rendered.)
- [x] 11.3 pytest + `node --check` green

## 12. Acceptance — graph redesign

- [x] 12.1 Browser verify on 中正區-河堤段四小段-263-19地號等25筆 (2 records:
      建照+開工 attributed pink to recno 1042 w/ case link, 使照 green w/
      twur link + 國; per-record callouts; no default 相關連結)
- [x] 12.2 Legibility/collision sanity on a multi-record family

## 13. User-driven refinements (2026-08-25 session)

- [x] 13.1 北/國 badges above the first label line, left-aligned (never cover
      labels); node labels stay synced with the detail-list columns
- [x] 13.2 相關連結 kept as debug-only toggle (default hidden) instead of full
      removal; 案名 builder restored for it
- [x] 13.3 Project list sorted by 現況 record's recno ascending
- [x] 13.4 Cleansing: 事業換計畫 → 事業計畫 (recno 621 大業段三小段184-1 typo;
      test in test_cleanse.py; propagates on next full pipeline build)
- [x] 13.5 Callouts compact + collision-dodging (six candidate spots, first
      non-overlapping wins; tail always points at its node); verified zero
      node/label occlusion with synthetic two-record scenario
