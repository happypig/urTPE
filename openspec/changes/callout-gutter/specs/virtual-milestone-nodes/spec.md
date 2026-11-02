## MODIFIED Requirements

### Requirement: Stage-key clusters group base/split case files

Nodes SHALL cluster by 第N次 (stage) within the family — not by date. Undated members SHALL join their
stage's dated cluster, rendered after the dated members and tagged (未核定). The cluster date SHALL be
the real member's date, else the minimum dated member's date (±1-day splits span the band). Clusters
SHALL render bare without a soft band or count chip (the viewer's callout gutter reserves that space; see
viewer-graph-layout). Members SHALL order base(real) first, then splits by 區段, then undated.
**Tie-break (2026-08-31 decision, viewer change design.md D12)**: dated members SHALL order row-by-row by
**effective case_id ascending** — a real node's key is its anchored case_id (`links.taipei[0]`), a virtual
node's key is its own `case_id`; real nodes without an anchored case carry an empty key and sort first
(`""` < any case_id, keeping the order strictly ascending). The 區段 ordering applies only between members
whose case keys are equal or both empty. **Family-wide interleave (Amendment 3, 603 exploration)**: the
case_id ordering extends across the family — undated virtual attempts interleave between their case_id
neighbors instead of being pushed to the tail, reproducing the 相關連結 case_id order in the graph.
**Same-key date tie-break (2026-11-02, row-order fix)**: when two or more real nodes share one effective
case_id, they SHALL order by **node date ascending** within that key — the recno-string comparison decides
only between members whose dates are equal or absent — because 編號 is a newest-first coordinate and a
recno tie-break alone renders a newer approval above an older one sharing its case.

**Reason**: The stage-band + count chip rendering requirement moved out of this spec; the clustering,
ordering, (未核定) tagging and tie-break rules are unchanged.

#### Scenario: Cluster renders without band or chip

- **WHEN** a stage cluster has ≥2 members
- **THEN** no soft band rectangle and no count chip text render behind those members; clustering order and
  (未核定) tagging still apply
