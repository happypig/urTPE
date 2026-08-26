# Tasks — add-stage-filter-621-repair

## 1. Stage filter (test first)

- [x] 1.1 Structural tests in `tests/test_viewer_labels.py`: `app.js` DIMS
      gains a `stage` dimension (labelled 施工階段， options 建照/開工/使照)
      positioned next to 事業種類， and `matches()` restricts by
      `constructionStage(p).short` when the dimension is active
- [x] 1.2 Run pytest — expect failure (red)

## 2. Filter implementation

- [x] 2.1 `viewer/app.js`: add the DIMS entry (fixed options, next to
      事業種類) and the `matches()` clause — stage-less projects excluded
      while any stage is selected; derivation via `constructionStage` only
- [x] 2.2 Run pytest + `node --check` — green

## 3. recno 621 repair (option B)

- [x] 3.1 `scripts/repair_621_track_2026_08_26.py`: patch
      `viewer/projects.data.js`, `data/projects.json`, and
      `data/.link_cache/北投區-大業段三小段-184-1地號等10筆/result.json` —
      recno 621: track 其他 → 事業計畫， 案名 事業換計畫 → 事業計畫，
      `auto_fixes += 案名錯字→事業計畫` (idempotent)
- [x] 3.2 Run the repair; re-read all three files and verify the patched
      values (track/案名/auto_fixes)

## 4. Acceptance

- [x] 4.1 Browser verify: 施工階段 dropdown beside 事業種類； 使照-only
      selection shows completed projects with 使照 badges; combining with
      大安區 narrows further; stage-less projects excluded; clearing restores
- [x] 4.2 Browser verify recno 621 family renders track 事業計畫 in the list
      filter facet and detail table, and 事業種類=其他 no longer matches it
