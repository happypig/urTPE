## ADDED Requirements

### Requirement: Case refresh records 無 / empty 目前辦理情形 as readable state

When 基本資料 / 目前辦理情形 reads 無, the refresh SHALL set the case's schedule
state to 「無」, and when the header row exists and 目前辦理情形 is empty, the
refresh SHALL set the state to 「NA」. The refresh SHALL keep these instead of
clearing the cached state to "". A missing header row ({}/None) remains "no
evidence" and SHALL keep the cached state.

**Reason**: 無 and empty are honest platform readings; clearing them hides
information that belongs on the per-case badge.

#### Scenario: 無 reading is stored as 「無」

- **WHEN** the case header NAME reads 無
- **THEN** case_schedules[cid] = 「無」 after refresh

#### Scenario: Empty reading is stored as 「NA」

- **WHEN** the case header row exists and NAME reads ""
- **THEN** case_schedules[cid] = 「NA」 after refresh

#### Scenario: Missing header keeps cached state

- **WHEN** the header fetch returns no row ({} / None)
- **THEN** case_schedules[cid] is unchanged
