## 1. Test setup (browser acceptance tests)

- [x] 1.1 Stand up the viewer locally (`python -m http.server 8000 --directory viewer`) and open it in a browser for manual acceptance testing
- [x] 1.2 Define a checklist of user-visible acceptance checks from the viewer-filtering and history-graph specs: filter combinations, result count, empty state, uniform SVG scale, label legibility, dynamic height, district chips

## 2. Test-writing (filtering behavior)

- [x] 2.1 Verify in the browser that checking 中山區 and 大安區 in 地區 narrows the list to those districts and updates the live count
- [x] 2.2 Verify AND semantics across dimensions: 地區=大安區 + 年度=2023 + 事業種類=事業計畫 shows only projects matching all three
- [x] 2.3 Verify any-member semantics: a multi-year project appears for any of its member years and any of its member tracks
- [x] 2.4 Verify an unchecked filter is inactive and search combines (AND) with the active selectors
- [x] 2.5 Verify the empty state renders when no project matches and "顯示 N / 718" is correct

## 3. Test-writing (readability behavior)

- [x] 3.1 Verify at a narrow panel width the SVG scales uniformly (labels legible, no horizontal squish) via viewBox
- [x] 3.2 Verify node labels stay readable over track/section edges (halo knockout)
- [x] 3.3 Verify a single-record project renders a compact graph box sized to its nodes
- [x] 3.4 Verify list items and detail headers carry the district color chip and match each other

## 4. Implementation (viewer UI — adapter layer)

- [x] 4.1 Build the multi-select dropdown component (地區 / 年度 / 事業種類) with checkboxes and 全選/清除, closing on outside click
- [x] 4.2 Derive filter option sets client-side from `PROJECTS.projects` (district set, year set from all node dates, fixed track value set)
- [x] 4.3 Implement filter state, AND-combined evaluation (district single-value; year/track any-member), and live "顯示 N / 718" count
- [x] 4.4 Add the empty-state message for zero matches
- [x] 4.5 Add the filter bar markup to `index.html` and styling to `app.css`

## 5. Implementation (SVG rendering — adapter layer)

- [x] 5.1 Switch detail SVG to `viewBox` + `width:100%`/`height:auto` for uniform scaling
- [x] 5.2 Apply paint-order white halo to node label text
- [x] 5.3 Make SVG height follow the node count instead of a fixed minimum
- [x] 5.4 Add the 12-color district palette and render chips on list items and the detail header

## 6. Acceptance run

- [x] 6.1 Run the full acceptance checklist from group 2 and 3 in a narrow and a wide browser viewport
- [x] 6.2 Verify the 718-project list loads and searches without errors after the changes