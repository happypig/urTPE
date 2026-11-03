## Context

Wave 4 (§2 viewer-UX). `viewer/app.js` `getNodeMilestoneBadges` (line ~104) and
`NATIONAL_MAPPED_LABELS` (line ~13) map national milestone labels to events.
`view_verified_case_ids` (140 projects) and the `is_current` rule currently drive 國.
The national labels already name stage+track: 事業計畫核定日期→擬訂/事業計畫,
第一次變更事業計畫核定日期→變更/事業計畫, etc.

## Goals / Non-Goals

**Goals:**
- 國 on exactly the recno node(s) whose stage+track match each national approval label.
- `view_verified_case_ids` stays as a second source.
- National execution events keep their chain position; source edge from latest bound node.

**Non-Goals:**
- Changing which national labels are harvested (pipeline unchanged).
- Changing `view_verified_case_ids` emission.

## Decisions

### 1. Binding by stage+track

`nationalLabelKey(label)` returns `{stage, track}` or null:
- 事業計畫核定日期 → {擬訂, 事業計畫}
- 權利變換計畫核定日期 → {擬訂, 權利變換}
- 第N次變更事業計畫核定日期 → {變更, 事業計畫}
- 第N次變更權利變換計畫核定日期 → {變更, 權利變換}
- 使用核發日期 / …申請日期 → null

A node matches when its stage and track equal the key. Combined track matches either.
When multiple nodes match, the node whose date equals the label's date (民國→ISO) wins;
else none (never guess).

### 2. 現況 rule removed

`getNodeMilestoneBadges`: 國 when a label binds, or D4 view_verified applies. Removed
the `node.is_current` branch.

### 3. National source edge

A national execution event's source group starts from the latest bound node (by date).
If no node is bound, no source edge (answers §2 Q1).

## Risks / Trade-offs

- [Risk] 492 projects lose every 國 badge (no bound node, empty view_verified).
  [Mitigation] Confirmed acceptable per §2 decision; the view/<id> link remains in
  相關連結 debug section.
- [Risk] Label stage vocabulary must match node stage vocabulary.
  [Mitigation] Verified against corpus counts in docs/viewer-UX.md §2 evidence.
