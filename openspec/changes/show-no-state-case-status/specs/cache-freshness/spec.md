## MODIFIED Requirements

### Requirement: Case refresh records 無 / empty 目前辦理情形 as readable state

When 基本資料 / 目前辦理情形 reads 無, the case's schedule state becomes 「無」, and
when the header row exists and 目前辦理情形 is empty, the state becomes 「NA」. The
refresh keeps these instead of clearing the cached state to "". A missing header row
({} / None) remains "no evidence" and keeps the cached state.

**Reason**: 無 and empty are honest platform readings; clearing them hides information
that belongs on the per-case badge.

#### Scenario: 無 reading is stored as 「無」

- **WHEN** the case header NAME reads 無
- **THEN** case_schedules[cid] = 「無」 after refresh

#### Scenario: Empty reading is stored as 「NA」

- **WHEN** the case header row exists and NAME reads ""
- **THEN** case_schedules[cid] = 「NA」 after refresh

#### Scenario: Missing header keeps cached state

- **WHEN** the header fetch returns no row ({} / None)
- **THEN** case_schedules[cid] is unchanged

### Requirement: case_headers stores CASE_NAME

The refresh persists the header row's CASE_NAME into case_headers[cid] so land-core
comparison can verify that a view-verified case really belongs to the project.

#### Scenario: CASE_NAME stored on refresh

- **WHEN** the case header is refreshed
- **THEN** case_headers[cid] carries CASE_NAME
