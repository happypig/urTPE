## Context

Current state: The previous change (`viewer-enhancements-and-orphan-case-anchoring`) added 基本面積 display to left-list project cards in `viewer/app.js` (line ~551). It renders as plain text: ` · 基本面積 ${p.implementation.Base_Area}`. No styling is applied.

The value comes from `p.implementation.Base_Area` (string, e.g., "2425.0", "5751.0", "350").

## Goals / Non-Goals

**Goals:**
- Apply conditional color/font-weight to 基本面積 value in left-list cards per the threshold spec
- Minimal, localized change to `viewer/app.js` left-list rendering
- No pipeline changes, no schema changes

**Non-Goals:**
- No changes to detail view, graph, or table
- No new CSS file — inline styles or existing CSS classes only
- No threshold configuration externalization (thresholds are fixed per spec)

## Decisions

### 1. Implementation location: inline style via helper function

**Decision**: Add a small pure function `getBaseAreaStyle(areaStr)` in `app.js` that returns an object `{ color, fontWeight }` or `null`. Call it in the left-list template (line ~551) and apply via `style` attribute on a `<span>` wrapping the numeric value.

**Rationale**: 
- Single-file change, no CSS file needed
- Pure function = testable, no side effects
- Inline style avoids CSS specificity issues with existing `.cnt` class

**Alternative**: CSS classes (e.g., `.base-area-purple`, `.base-area-orange-bold`).
- Rejected: Requires CSS file edit; inline is simpler for 4 thresholds.

### 2. Threshold logic: numeric parse with fallback

**Decision**: Parse `Base_Area` as `parseFloat(areaStr)`. If `isNaN` or value < 0, return `null` (no style). Thresholds are hardcoded constants matching the spec exactly.

**Rationale**: 
- `Base_Area` is a string like "2425.0" — `parseFloat` handles it
- Hardcoded thresholds = zero config, matches spec exactly
- Invalid/missing → no style (graceful degradation)

### 3. Style application: wrap only the numeric value

**Decision**: In the template, wrap the numeric value + unit in a `<span>` with the computed style. The "基本面積" prefix and 實施者 name remain unstyled.

```js
const area = p.implementation?.Base_Area;
const areaStyle = area ? getBaseAreaStyle(area) : null;
const areaHtml = area && areaStyle
  ? ` · 基本面積 <span style="color:${areaStyle.color};font-weight:${areaStyle.fontWeight}">${escapeHtml(area)}</span>`
  : area ? ` · 基本面積 ${escapeHtml(area)}` : "";
```

**Rationale**: 
- Only the number gets color/weight; "基本面積" label stays default
- Minimal DOM change, no layout shift

### 4. Color values: use existing design tokens

**Decision**: Use the same color constants already in `app.js`:
- Purple: `#8b5cf6` (matches `DISTRICT_COLORS` purple)
- Orange: `#f59e0b` (matches construction badge orange)
- Red: `#ef4444` (matches construction badge red)

**Rationale**: Consistent with existing UI palette; no new colors introduced.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| `Base_Area` string format varies (e.g., "2,425.0" with comma) | `parseFloat` handles commas? Actually it doesn't — add `.replace(/,/g, '')` before parse |
| Very large values (≥3000) all look the same (red bold) | Spec defines ≥3000 as red bold; 2000–2999 is orange bold — distinct |
| Projects without implementation show nothing | Already handled: no 基本面積 rendered |
| Color blind accessibility | Purple/orange/red are distinct hues; weight adds redundant encoding for orange/red tiers |

## Migration Plan

1. Edit `viewer/app.js`: add `getBaseAreaStyle` helper + modify left-list template (line ~551)
2. Open viewer, verify thresholds on known projects:
   - 350 → purple
   - 750 → default
   - 1500 → orange (not bold)
   - 2425 → orange bold
   - 5751 → red bold
3. No cache regeneration needed (viewer-only)

## Open Questions

None — thresholds and colors are fully specified.