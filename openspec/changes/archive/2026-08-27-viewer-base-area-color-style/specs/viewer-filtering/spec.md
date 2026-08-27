## ADDED Requirements

### Requirement: 基本面積 displays with conditional color and style based on value thresholds

The left-list project card SHALL render the 基本面積 value with conditional color and font weight based on its numeric value (in square meters, parsed from `p.implementation.Base_Area`):

- **< 500 m²**: purple color (`#8b5cf6`), normal font weight
- **≥ 500 and < 1,000 m²**: default label text color (inherit), normal font weight
- **≥ 1,000 and < 2,000 m²**: orange color (`#f59e0b`), normal font weight
- **≥ 2,000 and < 3,000 m²**: orange color (`#f59e0b`), bold font weight
- **≥ 3,000 m²**: red color (`#ef4444`), bold font weight

The style SHALL apply only to the 基本面積 numeric value and its unit label, not to the 實施者 name or the "基本面積" prefix.

#### Scenario: Small project (<500 m²) shows purple
- **WHEN** a project has `implementation.Base_Area = "350"`
- **THEN** the left-list card renders "基本面積 350" in purple (`#8b5cf6`), normal weight

#### Scenario: Medium-small project (500–999 m²) shows default style
- **WHEN** a project has `implementation.Base_Area = "750"`
- **THEN** the left-list card renders "基本面積 750" with default label color, normal weight

#### Scenario: Medium project (1,000–1,999 m²) shows orange (not bold)
- **WHEN** a project has `implementation.Base_Area = "1500"`
- **THEN** the left-list card renders "基本面積 1500" in orange (`#f59e0b`), normal weight

#### Scenario: Large project (2,000–2,999 m²) shows orange bold
- **WHEN** a project has `implementation.Base_Area = "2425"`
- **THEN** the left-list card renders "基本面積 2425" in orange (`#f59e0b`), bold

#### Scenario: Very large project (≥3,000 m²) shows red bold
- **WHEN** a project has `implementation.Base_Area = "5751"`
- **THEN** the left-list card renders "基本面積 5751" in red (`#ef4444`), bold

#### Scenario: Missing or invalid Base_Area shows no style
- **WHEN** a project has no `implementation` or `Base_Area` is empty/non-numeric
- **THEN** the left-list card shows only 實施者 without 基本面積 (no style applied)