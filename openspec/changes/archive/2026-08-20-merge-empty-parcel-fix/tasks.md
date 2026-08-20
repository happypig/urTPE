> POC: threshold calibration was completed in the archived urban-renewal-pdf-pipeline change (link ≥ 0.7, flag band 0.5–0.7, feature weights, ground-truth clusters 中華工程 寶清段 / 永昌段三小段159 / 逸仙段二小段151 / 東星大樓基地). This change only fixes the empty-parcel weight collapse; the POC finding is the 0.65 ceiling on full land-key matches, which these tasks address.

## 1. Test-writing (cleansing domain logic)

- [x] 1.1 Add a unit test: a malformed 地號 cell "…1251筆土地" (missing 地號) with a name "…125地號1筆土地…" yields parcels `{125}` derived from the 案名
- [x] 1.2 Add a unit test: a name "…531地號等2筆…" preserves section, first_parcel `531`, and land_count `2` via the name fallback
- [x] 1.3 Add a unit test: the malformed source cell still records the `缺少地號清單` review flag after the fallback

## 2. Test-writing (merge domain logic)

- [x] 2.1 Add a unit test: two records with empty parcel sets and identical district+section+first_parcel+land_count score ≥ 0.7 and link
- [x] 2.2 Add a unit test: the 125 family (擬訂 478 + 變更 234, different implementers) merges into one project
- [x] 2.3 Add a unit test: the 531 family (971/748/473/416, 台灣肥料 → 愛山林) merges into one project instead of four
- [x] 2.4 Add a unit test: the 302 family (擬訂 830 + 變更 261) merges into one project
- [x] 2.5 Add a regression test: records with different first parcels or counts still do NOT link when parcels are empty (no over-merging)

## 3. Implementation (cleansing domain logic)

- [x] 3.1 Extend `parse_name_id` / `_parse_land` in `cleanse.py` to derive parcels from the 案名 land fragment when the 地號 cell yields no parcel list
- [x] 3.2 Keep the `缺少地號清單` review flag on records whose parcels came from the name fallback

## 4. Implementation (merge domain logic)

- [x] 4.1 Modify `score()` in `merge.py` to renormalize the Jaccard weight when both parcel sets are empty and the full land key (district+section+first_parcel+land_count) agrees
- [x] 4.2 Confirm implementer remains absent from the score (unchanged behavior)

## 5. Acceptance run (pipeline)

- [x] 5.1 Re-run the pipeline end-to-end: `python -m urtpe.cli source.pdf -o data --viewer viewer`
- [x] 5.2 Verify 125/302/531 families each form one project in `data/merged.tsv` and `data/projects.json`
- [x] 5.3 Verify ground-truth clusters (永昌159, 中華工程, 逸仙151, 東星) still merge correctly and project count regression is limited to the fixed splits
- [x] 5.4 Run the full test suite (`python -m unittest discover -s tests`) — all tests pass