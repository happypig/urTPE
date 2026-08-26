# Tasks — fix-cross-family-case-pollution

## 1. Search guard (test first)

- [x] 1.1 `tests/test_links.py`: guard tests for `search_taipei_cases_api`
      (monkeypatched POST) — own-family cases kept (57-13 set), foreign
      same-section case dropped (11102211 for parcel 115), sibling R13 概要
      cases dropped (§6.7 set), notation drift tolerated (263之19 ↔ 263-19,
      full-width digits)
- [x] 1.2 Run pytest — expect failure (red)

## 2. Guard implementation

- [x] 2.1 `urtpe/links.py` `search_taipei_cases_api`: keep only entries whose
      `case_name` contains the searched parcel (mono part, 之↔- and
      full-width↔ASCII tolerant)
- [x] 2.2 Run pytest — green

## 3. Fragment merge-candidate detection (test first)

- [x] 3.1 `tests/test_links.py`: fragment detection — a family whose
      discovered cases ALL anchor inside one other family gets a
      review flag naming that family; mixed/nowhere anchoring unflagged
- [x] 3.2 Run pytest — expect failure (red)

## 4. Fragment detection implementation

- [x] 4.1 `urtpe/links.py`: after node anchoring, detect fragment families
      and append the merge-candidate review flag (臨界對-style review output;
      no family mutation)
- [x] 4.2 Run pytest — green

## 5. Re-merge + investigation

- [x] 5.1 Run `--links` regeneration; corpus re-verify: isolated events drop
      from 162 toward the anchored baseline; 金華段513-3 / 南港段19-1 /
      懷生段249 / 正義段115 spot-checks show no foreign-case events
      (isolated 162→73, families 82→32, double-display 94→40)
- [x] 5.2 Investigate 11102211's land list on the platform — 11102211 is
      **133地號等1筆's case** (per cache), NOT containing 115/132/243 parcels.
      The pollution was search false positive (B1b shape: overlap=0), not a
      shared big case. Verdict recorded in facts §6.8.
- [x] 5.3 Update facts §6.8 status (fix applied; post-fix counts: 73 isolated
      across 32 families; 40 double-display)

## 6. Acceptance

- [x] 6.1 Browser verify on motivating families: 正義段115 (1 case, 11102211
      rejected), 南港19-1 (3 cases, 10809251 rejected), 南港101 (1 case +
      fragment flag), 懷生段249 (mutual fragment flags), 金華段513-3 (3 own
      cases, 建照 from 10011041). 相關連結 debug list shows only own-unit cases.
      永昌段366-3 callouts unchanged (no regression).
