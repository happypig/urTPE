## Why

The left-list project cards now display 基本面積 (base area) next to 實施者, but all values render with the same style. Planners need immediate visual distinction of project scale: small sites (<500 m²) vs. medium (500–2,000 m²) vs. large (≥2,000 m²) to prioritize review. Color-coded thresholds provide at-a-glance triage without opening details.

## What Changes

- **Viewer**: 基本面積 text in left-list project cards receives conditional color/style based on numeric value:
  - < 500 m²: purple (default weight)
  - ≥ 500 and < 1,000 m²: default label text color (no emphasis)
  - ≥ 1,000 and < 2,000 m²: orange (default weight)
  - ≥ 2,000 and < 3,000 m²: orange, bold
  - ≥ 3,000 m²: red, bold

## Capabilities

### Modified Capabilities
- `viewer-filtering`: Left-list project cards apply conditional color/style to 基本面積 based on numeric thresholds.

## Impact

- **Viewer (`viewer/app.js`)**: Left-list rendering logic (around line 551) adds a helper to compute style from `p.implementation.Base_Area` and applies inline styles or CSS classes.
- No pipeline changes. No schema version change.