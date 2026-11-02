## MODIFIED Requirements

### Requirement: Status-chip vocabulary gains 無 / NA per-case labels

The per-case badge renders 「無」 when 基本資料 / 目前辦理情形 reads 無 and 「NA」 when
it reads empty. These labels apply only to the per-case badge; the family status chip
(審查中 / 撤回) and the never-approved readers skip 無 / NA so they read exactly as
before.

**Reason**: 無 / NA are honest per-case readings and must not be folded into the
family-level chip vocabulary.

#### Scenario: Per-case badge renders 「無」 for 無 reading

- **WHEN** a case's 目前辦理情形 reads 無
- **THEN** its badge shows [無]

#### Scenario: Per-case badge renders 「NA」 for empty reading

- **WHEN** a case's 目前辦理情形 reads empty
- **THEN** its badge shows [NA]

#### Scenario: Family chip ignores 無 / NA

- **WHEN** every case's state is 無 or empty, or mixed with terminal states
- **THEN** the family status chip reads as if 無 / NA cases were absent
