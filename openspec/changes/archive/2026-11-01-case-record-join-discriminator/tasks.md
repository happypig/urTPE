# tasks — case-record-join-discriminator

## 1. Test-writing group (red first; all checked before any implementation task)

- [x] 1.1 `tests/test_case_join.py`:
      (a) `normalise_case_id("R089213-02") == "089213"`;
      (b) `normalise_case_id("R089213") == "089213"` (bare R-form);
      (c) `normalise_case_id("09610235") == "09610235"` (numeric unchanged);
      (d) an unrecognised shape returns unchanged (never destroyed);
      (e) `join_case_ids` with recovery ⊂ discovery: `anchored` = the recovery
      set, `candidates` = the discovery set, `ambiguous` = the flag;
      (f) the recno 1005 payload shape (2 recovery cases inside 6 candidates,
      ambiguous-zone true) yields anchored=2, candidates=6, ambiguous=True;
      (g) the recno 188 payload shape (R-form recovery, numeric api_cases)
      joins via normalisation: `normalise_case_id("R089213-02")` matches
      `"089213"`-shaped ids;
      (h) agreement (recovery == discovery) yields the common set, no flag.

## 2. Implementation (after group 1 is fully checked)

- [x] 2.1 New `urtpe/case_join.py`: `normalise_case_id`, `join_case_ids`
      (pure; dataclass JoinResult with anchored/candidates/ambiguous).

## 3. Acceptance

- [x] 3.1 Full suite green; no emission change (the fields stay verbatim).
- [x] 3.2 `openspec validate` passes; both boards updated; commit.

---

Completed 2026-11-01 (commit `1c9082b`): 3.1 ran at 739 passed / 1 skipped (740 collected).
3.2: validate passed; the main spec synced (requirement replaced /
new capability written); both boards' Wave entries marked done in the same
commit. Checkbox completion added post-archive after review — the same
batched-update gap as wire-standing-checks/emit-stage-index, caught on the
user's audit of Wave 4-6 tasks.
