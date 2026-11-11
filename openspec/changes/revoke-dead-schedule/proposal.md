# Proposal: revoke-dead-schedule

## Why

The city's platform marks a case whose approval it later withdrew with the
header `NAME` 業經本府撤銷核准 (revoked). Measured 2026-11-10: **7 cases in the
corpus** carry that state (中山57's 09801092/09801094, 正義315's 10410211,
臨沂396's 10601181, 溫泉559's 09504082, 辛亥277's 10010091, 美仁800's 09707196),
and none of them has a gazette row — a revoked approval is never gazetted
(inspection-batchD §D9a, line 1090), which is correct publisher behaviour.

The pipeline does not know this state. Every layer that understands closed
cases enumerates the same three-value dead set (自行撤回 / 已駁回 / 已失效) and
misses 撤銷:

1. `schedule_from_top` (`urtpe/links.py:3006`) maps the header `NAME` to a
   schedule vocabulary. 撤銷核准 contains neither 撤回 nor 駁回 nor 核定, so it
   derives **""** — the case carries no state at all. (It does NOT wrongly
   derive 已核准: the string holds 核准, not 核定. Measured live.)
2. The awaiting-approval refresh re-selects such a case forever: its header
   carries `uro_chk_date` (an approval date) but no 核定日期 milestone, and its
   cached status is not terminal, so every refresh run re-fetches it (the
   re-selection loop `TERMINAL_SCHEDULES` exists to stop).
3. The node-case resolver's dead set (`_DEAD_SCHEDULES`,
   `filter_live_cases`) does not exclude a revoked case — a same-name revoked
   case could bind a node. No node binds one today (all 7 bind to zero nodes,
   measured) because none is gazetted; the gap is latent.
4. The viewer's `isDeadEnd` (`viewer/app.js:557`) does not list 已撤銷, and the
   計畫與執行 filter's dead-end states derive from it — a revoked case renders
   as a bare case with no badge instead of a closed one.

A revoked case is dead: approved, then withdrawn by the government. The rule
gives it a name (已撤銷), adds it to every dead set, and labels it honestly.

## Scope

- `urtpe/links.py`: `schedule_from_top` derives 已撤銷 from a `NAME` holding
  撤銷; `TERMINAL_SCHEDULES` and `_DEAD_SCHEDULES` gain 已撤銷.
- `viewer/app.js`: `isDeadEnd` gains 已撤銷 (the dead-end chip, the chain-edge
  refusal and the 計畫與執行 dead-end states follow from it).
- Tests for each layer.

## What this does NOT do

- No spec scenario changes the 無-labelling rule: a revoked header is a state,
  and the existing test (`test_refresh_rederive.py:229`,
  `test_a_revoked_case_is_not_labelled_wu`) already guards that. The new state
  is compatible: 已撤銷 is derived from the same header the 無 rule declines to
  touch.
- No backfill of the 7 existing cases: their caches carry no schedule for
  these ids (measured — the search list gives none). The next refresh of those
  caches derives 已撤銷 from the header they already hold. A whole-corpus
  refresh is not part of this change.
- The 計畫與執行 filter's fixed option list stays as-is (it already offers the
  dead-end states as labels, not an enum); a project whose current case reads
  已撤銷 matches the 已撤銷 state through the same dead-end clause.

## POC

Measured before proposing (2026-11-10, this session):

- Corpus census of header `NAME` values: 7 撤銷核准 cases, none gazetted,
  none bound to a node.
- `schedule_from_top({'NAME': '業經本府撤銷核准'})` returns `""` today.
- The string contains 核准 but not 核定, so no existing branch catches it.
