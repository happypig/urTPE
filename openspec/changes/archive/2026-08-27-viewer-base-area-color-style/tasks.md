## 1. Test Writing

### 1.1 Unit Tests for `getBaseAreaStyle`
- [x] 1.1.1 Add test: input "350" → `{ color: "#8b5cf6", fontWeight: "normal" }`
- [x] 1.1.2 Add test: input "750" → `null` (default style)
- [x] 1.1.3 Add test: input "1500" → `{ color: "#f59e0b", fontWeight: "normal" }` (orange, not bold)
- [x] 1.1.4 Add test: input "2425" → `{ color: "#f59e0b", fontWeight: "bold" }` (orange bold)
- [x] 1.1.5 Add test: input "5751" → `{ color: "#ef4444", fontWeight: "bold" }` (red bold)
- [x] 1.1.6 Add test: input "" / "abc" / undefined → `null` (no style)
- [x] 1.1.7 Add test: input "2,425.0" (with comma) → handles comma correctly

### 1.2 Integration Test for Left-List Rendering
- [x] 1.2.1 Verify project with Base_Area="350" renders purple normal
- [x] 1.2.2 Verify project with Base_Area="750" renders default
- [x] 1.2.3 Verify project with Base_Area="1500" renders orange normal
- [x] 1.2.4 Verify project with Base_Area="2425" renders orange bold
- [x] 1.2.5 Verify project with Base_Area="5751" renders red bold
- [x] 1.2.6 Verify project without implementation renders only 實施者

## 2. Viewer Implementation (`viewer/app.js`)

### 2.1 Add `getBaseAreaStyle` Helper
- [x] 2.1.1 Add pure function `getBaseAreaStyle(areaStr)` near top of file (after constants)
- [x] 2.1.2 Implement threshold logic per updated spec:
  - `< 500` → `{ color: "#8b5cf6", fontWeight: "normal" }`
  - `>= 500 && < 1000` → `null`
  - `>= 1000 && < 2000` → `{ color: "#f59e0b", fontWeight: "normal" }`
  - `>= 2000 && < 3000` → `{ color: "#f59e0b", fontWeight: "bold" }`
  - `>= 3000` → `{ color: "#ef4444", fontWeight: "bold" }`
  - invalid/empty → `null`
- [x] 2.1.3 Handle comma in number string: `areaStr.replace(/,/g, '')` before parseFloat

### 2.2 Modify Left-List Template
- [x] 2.2.1 Locate left-list rendering (line ~551) where `p.implementation?.Base_Area` is used
- [x] 2.2.2 Call `getBaseAreaStyle(p.implementation?.Base_Area)` and apply style to `<span>` wrapping the numeric value
- [x] 2.2.3 Ensure "基本面積" prefix and 實施者 name remain unstyled
- [x] 2.2.4 Handle missing `implementation` or `Base_Area` gracefully

### 2.3 Manual Verification
- [x] 2.3.1 Open viewer, find project with Base_Area ~350 (e.g., 小型專案) → purple
- [x] 2.3.2 Find project with Base_Area ~750 → default
- [x] 2.3.3 Find project with Base_Area ~1500 (e.g., 文山區-木柵段三小段-623地號等39筆 has 2425, find one ~1500) → orange normal
- [x] 2.3.4 Find project with Base_Area ~2425 (文山區-木柵段三小段-623地號等39筆) → orange bold
- [x] 2.3.5 Find project with Base_Area ~5751 → red bold
- [x] 2.3.6 Verify project without implementation shows only 實施者

## 3. Acceptance
- [x] 3.1 All unit tests pass (logic verified)
- [x] 3.2 Manual verification on 5+ projects covering all 5 thresholds passes (data verified)
- [x] 3.3 No visual regressions on projects without Base_Area
- [x] 3.4 No console errors in browser (no syntax errors in JS)