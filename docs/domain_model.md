# Domain Model

```mermaid
classDiagram
    direction LR

    class RawRecord {
        int recno
        str date
        str district
        str name
        str land
        str implementer
        str planner
        str parse_error
        str gazette_id
    }

    class CleanRecord {
        int recno
        str iso_date
        tuple ymd
        str district
        str district_land
        str name
        str name_raw
        str land
        str section
        str first_parcel
        list parcels
        dict aliases
        int land_count
        int orig_count
        str named_anchor
        str area_section
        str stage
        int stage_index
        str track
        str implementer
        str planner
        list auto_fixes
        list review_flags
        str gazette_id
        dict links
        dict implementation
        str stage_事業計畫
        str stage_權利變換
        set parcel_set()
    }

    class Project {
        str project_id
        int anchor_recno
        list members
        list borderline
    }

    class DiscoveryResult {
        str project_id
        str land_core
        str twur_view_id
        str twur_url
        list city_case_ids
        dict national_milestones
        dict taipei_milestones
        dict case_milestones
        dict milestones_source
        dict implementation
        dict rewards
        dict search_rejected
        dict candidate_names
        dict case_schedules
        list view_verified_case_ids
        str status
        str error
    }

    class GraphDocument {
        int schema_version
        str generated_at
        str source
        str published_date
        dict counts
        list projects
    }

    class ProjectGraph {
        str project_id
        int anchor_recno
        str district
        str section
        str implementer
        str name
        list member_recnos
        list nodes
        list edges
        dict links
        str published_date
        dict implementation
        dict rewards
    }

    class Node {
        int recno
        str date
        str stage
        str track
        str area
        bool is_current
        str case_name
        str name_raw
        str land
        str section
        str first_parcel
        list parcels
        dict aliases
        int land_count
        int orig_count
        str named_anchor
        str area_section
        str implementer
        str planner
        list review_flags
        list auto_fixes
        str district
        str district_land
        str stage_事業計畫
        str stage_權利變換
        dict links
        dict implementation
    }

    class Edge {
        int from
        int to
        str kind
    }

    %% ---- portal payload shapes (labels are the values) ----
    class TaipeiMilestones {
        dict label ~ date   %% STAGE_FIELD_MAP from second.ashx
    }
    class TaipeiImplementation {
        dict field ~ value  %% third.ashx
    }
    class TaipeiRewards {
        dict field ~ value  %% fourth.ashx
    }
    class NationalMilestones {
        dict label ~ date   %% 推動歷程 from view/<id>
    }

    %% Field descriptions RENDER, so derivation is stated here rather than in a comment.
    class TaipeiCase {
        str case_id "案號 — the only identity"
        str case_name "free text, self-describing"
        str project_id "owning unit"
        list record_recnos "records citing it; empty ⇒ virtual"
        str node_date "ISO; \"\" if none"
        str stage "parsed ← case_name"
        str track "parsed ← case_name"
        str area "區段, parsed ← case_name"
        str declared_parcel "首宗地號, parsed ← case_name"
        int declared_count "筆數, parsed ← case_name; None if omitted"
        str schedule "審查中 · 已核准 · 施工中 · 自行撤回 · 已失效 · 已駁回"
        dict milestones "34 fields — owned HERE, not on the record"
        dict milestones_source "which case a merged milestone came from"
        str provenance "how the case was found"
        bool orphan "true ⇒ no record cites it"
    }
    note for TaipeiCase "The JOIN has landed (case-record-join spec, urtpe/case_join.py).<br/>The unified per-case object is still proposed.<br/>A virtual case is one self-contained object;<br/>a real case is four dictionaries plus a duplicate.<br/>case_id has two source spellings - normalise only to join."

    %% ---- sources ----
    class PDFGazette
    class TaipeiPortal
    class NationalPortal

    PDFGazette --> RawRecord : one row
    RawRecord ..> CleanRecord : cleanse/normalize
    CleanRecord "*" --> Project : members
    Project ..> GraphDocument : build_graph_document

    NationalPortal --> DiscoveryResult : twur_view_id/url + national_milestones
    TaipeiPortal --> DiscoveryResult : city_case_ids + milestones + implementation + rewards

    Project --> DiscoveryResult : discover_project_links (land_core key)
    DiscoveryResult --> NationalMilestones
    DiscoveryResult --> TaipeiMilestones
    DiscoveryResult --> TaipeiImplementation
    DiscoveryResult --> TaipeiRewards

    GraphDocument "*" --> ProjectGraph : projects
    ProjectGraph "1" --> "*" Node : nodes
    ProjectGraph "1" --> "*" Edge : edges

    %% ---- TODAY, and superseded by the case layer below ----
    Node ..> TaipeiImplementation : implementation snapshot
    Node ..> TaipeiMilestones : date-anchored ±1 day (SUPERSEDED)

    ProjectGraph --> links : project-level twur + city links

    %% ---- the case layer: the JOIN has landed (case-record-join spec +
    %% urtpe/case_join.py, Wave 5 2026-11-01); the unified per-case object
    %% below is still proposed --------------------------------------------
    %% Many-to-many by design (D2): recovery.cases may select a subset of the
    %% discovery candidates. Precedence (recovery wins) and the read-side id
    %% normalisation live in the case-record-join spec — stored spellings are
    %% verbatim; normalise only to join.
    CleanRecord "*" --> "0..*" TaipeiCase : joined via case_join
    %% Invariant 3: milestones live on the case; a node may reference them.
    Node ..> TaipeiCase : renders (solid · dashed orphan · recovered)
    TaipeiCase --> TaipeiMilestones : owns

    %% ---- read model: derived in the browser by viewer/dashboard.js, never
    %% emitted (policy-dashboard spec). DashboardRow is one row of flatten();
    %% ReviewYear is one row of reviewOf(), per interval -------------------
    class DashboardRow {
        str project_id
        str status
        float idle_years
        float review_years
        float review2_years
    }
    class ReviewYear {
        int year
        int projects
        float min
        float q1
        float median
        float q3
        float max
    }
    ProjectGraph ..> DashboardRow : flatten (browser, one row per project)
    DashboardRow "*" --> "1" ReviewYear : reviewOf (by year of first approval, per interval)
```

## Notes

- **PDF** is the family skeleton and the heartbeat: one `RawRecord` per gazette row → one `CleanRecord` per node. `recno` is the only cross-PDF stable key (gazette renumbers every session).
- **Join identity** is the land core `{district}{section}{first_parcel}地號等{count}筆` (`build_land_core_key`), shared by merge and both portals.
- **Taipei** is pre-approval depth: per-`case_id` timelines (`case_milestones`), merged last-write-wins into `taipei_milestones` with provenance in `milestones_source`, plus `implementation` (`third.ashx`) and `rewards` (`fourth.ashx`).
- **National** is post-approval breadth: one `view/<id>` per project (revision rollup), `national_milestones` (推動歷程 incl. 使用核發, the only occupancy source).
- **Node anchoring** matches the node's date to a case's 核定日期/權變核定日期 exact-then-±1-day; per-record `implementation` snapshots ride onto nodes.
- **Two newer `DiscoveryResult` fields** (added after this diagram was first drawn): `case_schedules` — per-case state (已核准/已駁回/自行撤回/已失效/審查中/施工中) explaining why a project whose cases were all rejected has no national-portal page (§6.14); `view_verified_case_ids` — case_ids read off the project's *own* national view page 相關連結, portal-verified and therefore exempt from the landcore-similarity gate (§6.14 ghost creation).
- **The dashboard is a read model, not payload state**: `viewer/dashboard.js` flattens each `ProjectGraph` to one `DashboardRow` in the browser and emits nothing. Its two review intervals are `review_years` (application → first approval) and `review2_years` (application → the approval before the building permit), both read from the first approval node's own city case. `reviewOf` groups them by the first approval's year into `ReviewYear` rows — shortest, 25th percentile, median, 75th percentile, longest, project count — which the review chart draws as its 中位數 view (the two medians) or its 完整 view (`#review=full`: `review2_years` as a fan, `review_years` as one box per year). Percentiles interpolate linearly between the two nearest ranks, to one decimal; the rules are the `policy-dashboard` spec's.
- Sources: `viewer/dashboard.js`, `urtpe/models.py`, `urtpe/graph.py`, `urtpe/links.py`, `urtpe/archive.py`, `urtpe/ledger.py`, `urtpe/poller.py`, `urtpe/changeset.py`, `openspec/specs/official-link-discovery/spec.md`.

## Gazette cadence — archive, ledger, poller

The model above describes one gazette. Everything that survives *between* gazettes lives
outside the repo, under `D:\project\urtpe-gazettes\` (override: `URTPE_ARCHIVE_ROOT` /
`URTPE_LEDGER`), so a bad run cannot destroy the only copy of a publication:

```mermaid
classDiagram
    direction TB

    %% Context classes: declared in the diagram above, drawn empty here on purpose.
    class PDFGazette
    class CleanRecord

    class GazetteArchive {
        str root "DEFAULT_ARCHIVE_ROOT, overridable"
        list entries "index.jsonl — append-only"
    }

    class IndexEntry {
        str gazette_id "publication identity"
        str published_date "from the 統計至 line"
        str ingested_at "when this read ran"
        int record_count
        int project_count
        str reader_version "table-lines-v3; v1 is legacy"
        str filename
        str calendar "roc · gregorian"
        str source_path
        str sha256 "content identity — the only newness test"
        str event "first_ingest · reread"
        str acquisition "manual · fetched"
        str publisher_stamp "provenance only, never newness"
        int date_order_violations "-1 = not measured"
        int dated_records "-1 = not measured"
        bool is_verified()
    }

    class Correction {
        str match_land_core "what it applies to"
        str match_iso_date "and on which approval"
        str field "CORRECTABLE_FIELDS only"
        object to
        str why
        str by
        str at
        str gazette_id
        str supersedes "earlier correction this replaces"
        bool accept_removal "lets reconciliation pass a real deletion"
    }

    class CorrectionLedger {
        str path "corrections.jsonl"
        list entries "append-only; an ambiguous match is refused"
    }

    class PollState {
        str page_sha256
        int page_bytes
        str last_checked
        str last_gazette_id
        dict known_hashes
    }

    class PollOutcome {
        str status "new_gazette · reuploaded · unchanged · failed"
        str gazette_id
        str publisher_stamp
        str sha256
        str detail
        bool ingested "always false — acquisition never ingests"
        str pending_gazette_id "what an explicit ingest would take"
        bool dry_run
    }

    class ChangeSet {
        str previous_id
        str current_id
        bool comparable "false ⇒ nothing was measured"
        dict authoritative "new_approvals · net_change · previous_total · current_total"
        dict unresolvable "redated · edited · vanished · withdrawn_recent — counts only"
        str calendar_previous
        str calendar_current
        bool total_rekey "every project_id changed — the 2026-08-24 shape"
        int moved_project_ids
        list blocking
        str event "first_ingest · reread"
        str recorded_at
    }

    PDFGazette --> GazetteArchive : retained copy
    GazetteArchive "1" --> "*" IndexEntry : index.jsonl
    CorrectionLedger "1" --> "*" Correction : corrections.jsonl
    Correction ..> CleanRecord : applied after cleanse, before merge
    PollOutcome ..> PollState : written on success
    PollState ..> IndexEntry : last_gazette_id
    IndexEntry ..> ChangeSet : the pair compared
```

| File | Object | Why it exists |
| --- | --- | --- |
| `index.jsonl` | `IndexEntry` | one append-only line per ingest **or re-read**; `event` keeps them apart, so twelve entries describing three publications can no longer read as twelve publications |
| `<gazette_id>.pdf` | `GazetteArchive` | the retained copy a run rebuilds from |
| `corrections.jsonl` | `Correction` / `CorrectionLedger` | manual fixes keyed on land core + approval date, never on 編號 |
| `poll_state.json` | `PollState` | last page fingerprint and known digests |
| `poll_log.jsonl` | `PollOutcome` | append-only poll results |
| `change_sets/<gazette_id>.json` | `ChangeSet` | the reconciliation conclusion, kept after the terminal that printed it |

Three properties the classes encode, each with an incident behind it:

- **Newness is a hash, never a timestamp.** `IndexEntry.sha256` and `PollState.known_hashes`
  are the only tests. `publisher_stamp` is provenance: the city re-uploads a byte-identical
  PDF under a later stamp, so `Last-Modified` would report a new gazette every week for one
  already held. `IndexEntry.is_verified()` is deliberately stricter than "has a digest" — a
  legacy `reader_version` means the counts came from a reader that cannot be trusted to
  reproduce them.
- **Acquisition never ingests.** `PollOutcome.ingested` is always `false`; the poller
  reports `pending_gazette_id` and stops. The single-writer lock serialises writers without
  deciding which writer is correct, so wiring polling into ingestion would turn a
  concurrency guard into an ordering assumption.
- **A change set is keyed by publication, not by run.** Re-ingesting overwrites one
  publication's conclusion instead of accumulating competing records. `authoritative`
  (`new_approvals`, `net_change`, totals) is kept apart from `unresolvable` (`redated`,
  `edited`, `vanished`, `withdrawn_recent`) because this data cannot tell a deletion from an
  edit or a re-dating — filing them together would assert more than the comparison supports.
  `total_rekey` is the 2026-08-24 shape: when every `project_id` changes, the before/after
  intersection is empty and a naive diff reports success while every cache is orphaned.

## TaipeiCase (proposed — not implemented)

The gazette and the portals do not agree on what a thing is. The gazette counts
**核定案件** — one approval. The Taipei portal counts **案** — one application, which can
span several approvals. Nothing in the current model names that second thing, so it is
carried as loose keys.

**What it costs today, measured 2026-11-01 on the post-restore payload
(published_date 2026-10-15, 1,442 records / 694 projects, 1,412 case→record
bindings counted as `links.taipei` pairs — both emitted artifacts agree; a
Wave-7 note had recorded 1,430 under an unstated method, corrected here —
4 recovered nodes, the recovery-four 188/1005/1131/1206; 編號 188's recovery
carries the R-form id `R089213-02`, see the id-space note below):**

> **Amended 2026-11-01 (post-restore).** Three facts the 2026-10-24 version
> predates: (1) recovered rows are payload state — `node.recovery` with
> `cases`/`api_cases`/`flags`; (2) `recovery.cases` spans two id spellings
> (R-form vs numeric, `docs/urotpe_api.md` §4) — joins go through
> `urtpe.case_join.normalise_case_id` (`case-record-join` spec); (3) the
> case-record join is many-to-many by design (D2 of
> `case-record-join-discriminator`): `recovery.cases` may select a subset of
> `links.taipei`, and the precedence rule lives in that spec, not here.
>
> **Synced 2026-11-01 (TAB-2 review).** The join half of this proposal has
> landed (Wave 5): `normalise_case_id` + `join_case_ids` exist, and the spec
> fixes recovery-wins precedence with `ambiguous-zone` carried as provenance.
> Still proposed: the unified per-case object itself. Measured corrections:
> bindings 1,412 (not 1,430); 344 cases cover >1 record; 342 ambiguous markers
> (320 resolvable / 22 not); 973 virtual entries / 953 distinct; total 1,926.

- A **virtual** case (no matching record) is a self-contained 11-field object in `orphan_nodes`.
- A **real** case is scattered across four dictionaries — `case_milestones[case_id]` on the
  project, `case_schedules[case_id]` beside it, `links.taipei` on the node — and the node
  additionally carries a *flattened duplicate* of the milestones.
- So drawing a virtual case is reading one object, and drawing a real case is joining four.
  That asymmetry is why the viewer handles them differently, and why 342 progress markers
  are anchored ambiguously (their case sits on more than one of the 344 multi-record cases'
  records) while a further 225 name a source case that is on no record at all.
- Two integrity problems this shape would expose, both currently invisible because
  `orphan_nodes` is a flat list keyed by nothing: **20** virtual cases are listed more than
  once (973 entries, 953 distinct case ids), and **9** case ids appear *both* as virtual and
  as real — so the total is 1,926 or 1,917 depending on which wins.

**Three invariants, each of which a measurement supports:**

1. **The joined case set is the only relation between a case and the gazette.** Measured:
   1,412 bindings via `links.taipei`; 344 cases cover more than one record (up to 4); **0**
   records name more than one case *there* — but the relation is many-to-many by design:
   `recovery.cases` may select a subset of the discovery candidates (recno 1005 selects
   `09610235`/`09610236` against a `links.taipei` of `09610231`), and the spec fixes that
   the recovery binding wins, with `ambiguous-zone` carried as provenance. Ids are stored
   verbatim in their source spelling and normalised only to join.
2. **`case_name` is parsed, never compared.** It self-declares 段, 首宗地號, 筆數, 階段
   and track. That is what separates the 493 groups of cases sharing 段 and 首宗地號 — 365
   differ on count or stage, and 128 are identical on both. Comparing the name for equality
   — or ignoring the parts that differ — collapses those groups. 29 of 1,981 names yield no
   parcel at all and are not groupable.
3. **Milestones belong to the case, never to the record.** The node's flattened copy is a
   denormalised duplicate and is the reason a milestone can be dated two years before the
   record it is drawn against.

**Two rules fall out of it, and both fix a measured defect:**

- *Anchor resolution.* When several records carry a case, a milestone attaches to **the
  latest record approved on or before the milestone's date** — not the last one iterated.
  320 of 342 ambiguous markers resolve this way; 22 have no prior approval and should
  stay unanchored rather than be attached to something.
- *Discriminator.* When several cases share 段 and 首宗地號, separate them by declared
  count and stage. Where they are identical on both, **attach none** and report the group
  as ambiguous — a wrong attachment is worse than an admitted gap. 128 groups today.

**Open question.** 194 of 953 distinct virtual cases carry no date at all. They are retained
today because `orphan_nodes` holds them, but a class with no position on the time axis needs
a stated home — a gutter column, or listed beneath the graph. That is a decision, not a
default.