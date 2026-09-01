## ADDED Requirements

### Requirement: Per-track stage derivation for combined-track nodes

A node whose 事業種類 is 事業計畫、權利變換 (combined track) and whose 案名 carries two stage ordinals — `[stage1]…事業計畫及[stage2]權利變換計畫案` — SHALL derive **per-track stages**: `stage_事業計畫 = stage1`, `stage_權利變換 = stage2` (e.g. 中正區-臨沂段一小段-507 recno 1: 案名 `變更臺北市…事業計畫及變更(第二次)權利變換計畫案` → 事業計畫 at 變更, 權利變換 at 變更(第二次)). Uniform-ordinal 案名 (`…事業計畫及權利變換計畫案` with one shared ordinal, or identical ordinals) keep the single derived stage for both tracks. The single `stage` field remains unchanged for compatibility; the per-track stages are additive fields.

#### Scenario: Split-stage combined node derives both stages
- **WHEN** a combined-track node's 案名 is `變更臺北市中正區臨沂段一小段507地號等3筆土地都市更新事業計畫及變更(第二次)權利變換計畫案`
- **THEN** the record derives `stage_事業計畫 = 變更` and `stage_權利變換 = 變更(第二次)`

#### Scenario: Uniform-ordinal combined node keeps the shared stage
- **WHEN** a combined-track node's 案名 is `變更(第四次)…事業計畫及權利變換計畫案` (one ordinal covering both)
- **THEN** both per-track stages equal the single ordinal

#### Scenario: The single stage field is unchanged
- **WHEN** the per-track derivation runs
- **THEN** `stage` remains the 案名-prefix stage (existing clustering, table, and graph placement are unaffected)
