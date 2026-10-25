# POC findings — task 1.1/1.2 census (measured 2026-10-26)

Source: `probes/census_declared_counts.py` → `census_declared_counts.txt`
(7 gazettes swept, read-only), plus `probes/raw_cells_1005_and_140.py` for the
two decisive raw cells. The current gazette is 核定案件-2026-10-23.pdf
(統計至 2026-10-15) — it is held in the archive but not yet ingested (index
stops at 2026-10-01); the shipped data/ dataset still reflects 1151006.

## 1. The motivating row is confirmed — and caught by the hyphen fix alone

編號 1005 (2017-02-16, 雙園段二小段505等77筆, page 170 row 5): cell ends
`…577、578、579-` — cut mid-token, closing phrase absent, **76** visible of
77 declared (the proposal says 75; the measured count is 76). Today's
`TRUNCATED_TAIL_RE = [、，,]$|\d$` does not fire → escaped, emitted with a
short list. Extending the regex with `\d-$` (task 3.1) catches it with no
count check at all. The same row escapes in every held gazette
(編號 999 in 2026-08-27, 1003 in 2026-10-01, 1004 in 2026-10-13, 1005 in
2026-10-15 — always `…579-`).

## 2. The proposal's expected blast radius is falsified

Per gazette, mismatches are ~93–107, not 1:

| gazette | rows | visible<declared (flip class) | visible>declared (review class) |
|---|---|---|---|
| 2026-08-11 | 1419 | 39 | 54 |
| 2026-08-20 | 1422 | 39 | 54 |
| 2026-08-27 | 1427 | 39 | 54 |
| 2026-09-24 | 1436 | 59 | 48 |
| 2026-10-01 | 1440 | 59 | 48 |
| 2026-10-06 | 1441 | 59 | 48 |
| **2026-10-15 (current)** | 1442 | **59** | **48** |

Of the current gazette's 59 flip-class rows, 15 are tail-caught (already
excluded today — no flip); **44 would be NEW exclusions** under the specced
check — not the single-row 1,427 → 1,426 the proposal records.

## 2b. Revised rule (option A, settled 2026-10-26) — measured outcome

With the count check scoped to closing-phrase-lost cells, the tail pattern
extended with `\d-$`, and the counter corrections of §3, the outcome changes
are (`probes/completion_outcome_for_new_rows.py`, corpus = every other held
gazette):

- ROC-era gazettes (2026-08-11/20/27): **0 outcome changes.** The documented
  1150827 編號 868/909 rescues survive (count still closes at 110=110 under
  the corrected counter).
- Gregorian gazettes (2026-09-24 → 2026-10-15): the same **7 rows newly
  truncated** each — 永昌段四小段46-4 (117 declared / 107 visible, cell ends
  `…114-`), the four 永昌段三小段159 stages (113/90, ends `…139、139-`),
  雙園段二小段505 事業計畫 (77/76, ends `…579-` — 編號 1005 in the current
  gazette), 萬隆段二小段519 (56/53, ends `…575-`). The ROC renderings of all
  these units are complete (verified in 核定案件-2026-08-27.pdf), which the
  Gregorian re-render cut.

Completion outcomes for those 7 (current gazette 編號): 695/702/726/827
**COMPLETED** from 2026-08-11 編號 684 (complete 113-list, all three checks
hold); **188, 1005, 1206 EXCLUDED** — the mid-token cut token (`114`, `579`,
`575`) is absent from the complete candidate, so the containment check
refuses, exactly as the spec's "bounded differently" clause requires; and for
519 no held publication carries the complete 56-list.

Emission impact (corpus available, as the CLI builds it): the current
gazette emits 1,441 today (1,442 rows − 編號 1131 excluded + 14 completions;
the proposal's "1,427" ignored the corpus path), becoming **1,438**. The
shipped dataset's source (1151006 / 2026-10-01, 1,439 emitted) becomes
**1,436** on re-ingestion. 編號 1005's completion refusal is the designed
behaviour; `recover-truncated-rows-via-api` remains the follow-on for that
class.

## 3. Counter blind spots (verified in raw cells)

The dominant flip rows END with their closing phrase (`地號等N筆土地`) — the
publisher finished drawing those cells. Their mismatches are:

- **Reader counting artifacts** (would misfire under D-4's "no new parsing"):
  - 長安段140 family (4 rows/gazette, e.g. 編號 60): `…162、163 164、165地號等22筆土地`
    — 22 real parcels; the space where `、` belongs is stripped by
    `parcel_token_count`, gluing `163164` → counted 21. Raw cell verified.
  - 編號 14 (萬華段894): `…916 地號等22土地` — terminator without 筆 is not
    stripped, so the count digit `22` leaks in as a token (23 vs real 22).
  - 編號 1237 (桃源段251): `…251、252地號等2筆(原17筆)土地` — the parenthetical
    defeats `LAND_TERMINATOR_RE`, so `2` and `17` count as parcels (4 vs real 2).
  - 編號 485 (中正段44): `…246-3地號等 18 筆土地)等 4 筆土地` — chained tail not
    stripped; `18` and `4` leak in.
- **City-side 案名 inconsistencies** (cell is self-consistent; the 案名 is the
  suspect part): 521 vs the cell's own "地號等52筆" with 52 listed (編號 427);
  案名 16 vs the cell's own "等7筆" with 7 listed (編號 1381); multi-section
  sums (`A地號1筆…及B地號等39筆` → declared takes 1, cell shows 40, 編號 269).
- **Genuine shortfalls even with a closing phrase**: 雙連段一小段197
  (2013/1/8 row): closing phrase claims 72, lists 62 — today EMITTED with
  62/72; `complete_truncated_cell`'s docstring already records that no held
  publication carries the full list. So "ends with the closing phrase" does
  not prove the list is whole — but excluding every such row discards
  complete-as-published records (the 140/894/521 classes) over city-side
  errors.

## 4. Consequence for the spec delta

The delta's ADDED requirement ("SHALL compare … for every row …; visible <
declared → publisher-truncation path") is unsound against the archive as
measured; option A narrows it. Under option A the residual value of the count
check is as a safety net for cuts ending in non-tail characters on cells that
lost their closing phrase (e.g. after `…479(部分)`); the tail regex extended
with `\d-$` catches every mid-list cut observed, because a cut mid-list always
ends on a digit, hyphen, or separator after whitespace strip. Cells whose
closing phrase is present are complete as published and are never
count-checked; their 案名-vs-cell mismatches (48 per Gregorian gazette) are
systemic city-side inconsistencies for the ledger/cleanse review path, not
extraction faults — review-flagging them is out of scope here.

Direction: option A adopted 2026-10-26. Tasks 1.2/2.x/3.x/5.2 rewritten to the
measured flip list above.
