# Tasks — refine-event-source-edges

## 1. milestones_source emission (test first)

- [x] 1.1 `tests/test_links.py`: after attach, `project.links["milestones_source"]`
      names the winning case per merged label (single-carrier 建照 case → that
      case_id; two-carrier overwrite → later winner; no milestones → map absent)
- [x] 1.2 Run pytest — expect failure (red)

## 2. Emission implementation

- [x] 2.1 `urtpe/links.py`: build the label → winning-case map inside the
      existing stage-milestone merge loop; attach as additive optional
      `milestones_source` on project links (absent when empty)
- [x] 2.2 Run pytest — green

## 3. Viewer: source-group edges, tooltips, callout zones (test first)

- [x] 3.1 Structural tests in `tests/test_viewer_labels.py`: builder groups
      events by provenance (implementation.case_id exact-match,
      milestones_source map, national-only), renders `event-edge` solid within
      groups and a dashed variant between groups, drops event hyperlinks when
      the carrying case anchors, badge tooltips carry `案<case_id>` /
      `view/<id>`, and the callout renders the abbreviated 使用分區 row
- [x] 3.2 Run pytest — expect failure (red)
- [x] 3.3 Implement in `viewer/app.js`: source-group edge builder replacing
      plan-in-force attribution; hyperlink rule; badge tooltip titles; zone
      abbreviator + 4th callout row; `app.css` for dashed variant
- [x] 3.4 Run pytest + `node --check` — green

## 3b. Callout selection & visibility (test first)

- [x] 3b.1 Extend structural tests: callout selection = first carrying record
      + diff-triggered records only (identical successors silent); placement
      collision set excludes the callout's own record; candidate rects clamp
      into the viewBox (svgW/svgH extend when needed)
- [x] 3b.2 Run pytest — expect failure (red)
- [x] 3b.3 Implement selection + own-record exclusion + clamping in the
      callout placement
- [x] 3b.4 Run pytest + `node --check` — green

## 4. Acceptance

- [x] 4.1 Browser verify on 大安區-金華段四小段-513-3地號等13筆 (single pink
      group 1040 → 建照 → 開工 → 使照； no edge to recno 797; no event
      hyperlinks; 北 tooltips 案10011041/案10011042; callout with
      住三/住三之一 — after the pending `--links` regen populates snapshots)
- [x] 4.2 Browser verify mixed-source family (e.g. 中山區-北安段一小段-14-2):
      pink group + green dashed transition into the national-only 使照 with
      國 badge and western date
- [x] 4.3 Browser verify callout selection & visibility on
      中正區-永昌段四小段-366-3地號等14筆 (4 carriers → exactly 2 callouts:
      recno 761 baseline + recno 8 with red 事業計畫及權利變換計畫； both fully
      inside the viewBox, covering no node or label)
- [x] 4.4 Collision sanity: callouts and dashed edges cover no approval nodes
      or labels

## 5. Post-completion feedback (2026-08-26 session)

- [x] 5.1 使用分區 diff compares as a set (order-insensitive, post-dedupe);
      joined display deduped as well
- [x] 5.2 milestones_source backfilled into 691 caches
      (scripts/backfill_milestones_source_2026_08_26.py) + --links attach
      re-run, so 建照核發日期 groups by its true winning case without waiting
      for the nightly sweep
- [x] 5.3 Verified on 永昌段四小段-366-3 (建照 ← 761, case 10410261) and
      寶清段一小段-57-13 (single group 1068 → 建照 → 開工 → 使照)

## 6. Provenance completeness: BDD rule, corpus guard, CLI inspector (test first)

- [x] 6.1 `tests/test_milestones_provenance.py`: corpus scan over
      `viewer/projects.data.js` implementing the BDD scenarios — every
      建照/開工/使照 value resolves via milestones_source, implementation
      case_id exact-match, or national 使用核發日期； failures list
      family/slot/value
- [x] 6.2 Run pytest — confirm green on the current corpus (1,353/1,353
      provable baseline) and that a synthetic isolated slot flips it red
- [x] 6.3 `scripts/inspect_slot.py <project_id> [slot]`: CLI provenance
      explainer — merged value, milestones_source entry, per-case
      case_milestones values, implementation payload dates + case_id,
      national value
- [x] 6.4 Run the inspector on 金華段四小段-513-3 and 寶清段一小段-57-13 and
      verify the breakdown matches the merge records

## 7. List-item construction stage badge (test first)

- [x] 7.1 Structural tests in `tests/test_viewer_labels.py`: the list-item
      renderer derives a 2-char stage badge (建照/開工/使照) from the latest
      of the three construction dates (使照 falls back to national
      使用核發日期) and renders no badge when none exist
- [x] 7\.2 Run pytest — expect failure (red)
- [x] 7.3 Implement the stage badge in the list-item renderer (`app.js` +
      `app.css` chip style)
- [x] 7.4 Run pytest + `node --check` — green

## 8. Acceptance — list stage badge

- [x] 8.1 Browser verify: a 使照-stage project shows 使照 badge; a 建照-only
      project shows 建照； a no-construction project shows none; badges sort
      neutral (list order stays 現況 recno ascending)