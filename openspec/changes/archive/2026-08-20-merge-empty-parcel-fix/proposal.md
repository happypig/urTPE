## Why

The merge step splits families that share the same land when the source 地號 cell is malformed. In the raw PDF, cells like "臺北市中山區中山段二小段1251筆土地" are missing the "地號" separator, so the cleanser cannot build a parcel list and flags `地號無法解析(缺少地號清單)`. The scoring then drops the entire 0.3 Jaccard weight (`if s1 and s2` fails on empty sets), capping a perfect land-key match at 0.65 — just below the 0.7 link threshold. Result: 擬訂→變更→變更(第二次)→… approvals of one unit become separate projects, e.g. 南港段一小段531地號等2筆 split into four (`-`, `-2`, `-3`, `-4`) even though the implementer merely changed (台灣肥料 → 愛山林). Same land must mean same project regardless of implementer.

## What Changes

- When both records in a candidate pair have unparseable (empty) parcel sets but agree on the full land key (district + section + first parcel + land count), redistribute the Jaccard weight across the surviving components so the pair can link instead of capping at 0.65.
- Fall back to the 案名 when the 地號 cell is missing its parcel list: `parse_name_id()` already derives section/first-parcel/count from the name; extend it to seed the parcel set where recoverable (e.g. `125地號1筆` → `{125}`).
- Implementer stays entirely out of the similarity score — land is the sole identity (already true; unchanged).
- Records whose land remains genuinely unparseable after the name fallback keep the existing `缺少地號清單` review flag and the existing 0.5–0.7 borderline handling.

## Capabilities

### New Capabilities

- `land-identity-fallback`: deriving a record's parcel identity from the 案名 when the 地號 cell is malformed, so land-based linking survives source-data gaps.

### Modified Capabilities

- `case-merging`: the link-records-by-similarity requirement changes — pairs with empty parcel sets on both sides must no longer lose the Jaccard weight; a full land-key agreement must be able to link them across implementer changes.
- `data-cleansing`: the derive-structured-fields requirement changes — parcel-set derivation must consult the 案名 as a fallback source when the 地號 cell cannot supply a parcel list.

## Impact

- `urtpe/cleanse.py`: name-derived parcel fallback in `_parse_land` / `parse_name_id`.
- `urtpe/merge.py`: weight renormalization when both parcel sets are empty; scores in `score()`.
- Tests: `tests/test_cleanse.py`, `tests/test_merge.py` — new cases for the 125/302/531 families.
- Requires re-running the pipeline (`python -m urtpe.cli source.pdf -o data --viewer viewer`) and regenerating `data/*.tsv`, `data/projects.json`, `viewer/projects.data.js`.