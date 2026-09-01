# Tasks: normalize-plan-abbreviation

> POC: the platform cross-reference (18/18 cases spell 土地都市更新事業計畫案, 0
> without 事業) already validates the normalization — findings in
> `data/_gengxin_plan_crossref.json`; no further POC needed.

## 1. Tests first (BDD scenarios from the spec delta)

- [x] 1.1 `tests/test_cleanse.py`: abbreviated 案名 gains 事業 + `auto_fixes` flag + track derives 事業計畫 (長春段775 fixture)
- [x] 1.2 Already-full 案名 passes through unchanged (no auto-fix)
- [x] 1.3 Corpus-shape guard: after cleansing the affected fixtures, no node derives track `都市更新計畫`

## 2. Implementation (cleanse)

- [x] 2.1 `urtpe/cleanse.py`: 案名 abbreviation normalization
      `土地都市更新計畫案` → `土地都市更新事業計畫案` (only when 事業計畫 absent),
      `auto_fixes` flag `案名補事業(都市更新計畫案簡寫)`
- [x] 2.2 Confirm `_tracks()` no longer reaches its `都市更新計畫` fallback for
      the affected records (fallback stays as last resort for genuinely
      unclassifiable names)

## 3. Verification

- [x] 3.1 Full suite green
- [x] 3.2 Pipeline re-run (`source.pdf`): the 6 families emit track 事業計畫;
      viewer table labels updated; `auto_fixes` visible in the detail table
