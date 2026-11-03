## 1. Test writing — fully checked before any implementation task

- [x] 1.1 Unit tests in tests/test_gaiyao_track.py (TestSingleDuanExtraction or a
  new class): 、-list, `(原NNN)` ×2 positions, spaced 地號/筆, NFKC U+F963,
  plus the unchanged cases (single-段, 段小段) and the unchanged exclusions
  (parcel-less 崇仁新村 → "").
- [x] 1.2 A gate test: an orphan whose case_name is unparseable is named in the
  refresh/attach report (key + name), not silently dropped.
- [x] 1.3 Confirm 1.1/1.2 fail on the current extractor.

## 2. Pipeline implementation

- [x] 2.1 `extract_landcore_from_case_name`: NFKC-normalise, then learn the 3
  shapes (、-list → first parcel; strip `(原NNN)`; allow spaces).
- [x] 2.2 The orphan gate collects unparseable orphan case_names into the
  attach report.

## 3. Re-emit (no fetch)

- [x] 3.1 Re-run `--from-js` under the lock. Result (corrected while
  executing): 09205060 (長安709) and 09406102 (南港531-4) return as orphan
  nodes; 華中247's 6 cases now PARSE (201-2、352地號 extracts first parcel
  201-2) but score 0.45 < 0.7 against the anchor's first parcel 247 — a real
  gate decision, not a parse failure. They are named per case on the anchor
  record (孤兒案件未達相似度門檻, 6 flags). The plan's "8 return" claim was
  wrong about 華中247: its 6 cases need a merge decision (C9 shape), not a
  parse fix. Also learned: `…土地都市更新概要案` (short 概要) derives 事業概要,
  or the ghost renders no row (南港531-4's 09406102).
- [x] 3.2 Coverage guard passes (no flag drop, no total re-key).

## 4. Verification

- [x] 4.1 pytest passes.
- [x] 4.2 scripts/viewer_smoke.js passes.
