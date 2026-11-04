# Tasks: building-permit-adapter

## 1. Tests (test-first — all checked before any implementation task)

- [ ] 1.1 Unit test: the XML record parser (執照號碼, 發照日期 ROC→ISO,
      原核發執照, 地段號 → (district, section, mono, suno)) —
      `tests/test_permit_sources.py::TestPermitRecord`
- [ ] 1.2 Unit test: the parcel index (full-width digits, leading zeros,
      -0000 sub-parcel forms fold to the mono) — `TestPermitIndex`
- [ ] 1.3 Unit test: the 建字-origin rule (a 雜字 permit does not witness; a
      second 建字 on an area split both witness) — `TestJianziRule`
- [ ] 1.4 Unit test: the match (max parcel overlap; a tie keeps all; no
      overlap → no witness) — `TestPermitMatch`
- [ ] 1.5 Unit test: the attach-side flag texts (城市/國/執照 confirms,
      執照 matches neither, 無執照佐證) — `tests/test_permit_flags.py`
- [ ] 1.6 Viewer test: `fmtDate` renders an out-of-range ROC year verbatim
      with the warning class (橋北574-1's `291.08.02`), and a normal ROC
      year still converts — `tests/test_viewer_labels.py` or the DOM-stub
      smoke path
- [ ] 1.7 Offline acceptance: the archive-cached XML (SHA-256 keyed, no
      re-download) matches 吉林811 and 虎林310 to the values measured on the
      board — `TestCachedMatch`

## 2. Implementation

- [ ] 2.1 `urtpe/permit_sources.py`: download (SHA-256 cache under the
      archive root), parse, index, match — pure logic separated from I/O
- [ ] 2.2 Wire the match into the attach path (`links.permit` + flags) with
      the archive-root override honoured
- [ ] 2.3 Viewer: the permit witness in the 使照 callout, the disagreement
      review note, and the `fmtDate` range guard

## 3. Verification

- [ ] 3.1 `python -m pytest` full suite green
- [ ] 3.2 Live: download both datasets once, re-measure the 22 disagreements
      and the 13 national-only projects against the board's numbers (8 city /
      9 national / 4 neither / 1 no-permit; 12 of 13 confirmed)
- [ ] 3.3 Re-emit; smoke + baseline pass; `openspec validate --all`; archive
      and sync the deltas
