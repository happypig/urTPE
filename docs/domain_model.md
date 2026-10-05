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
        dict links
        dict implementation
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
        str land
        str section
        str first_parcel
        list parcels
        dict aliases
        int land_count
        str implementer
        str planner
        list review_flags
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

    %% node snapshots ride from per-case records onto the graph
    Node ..> TaipeiImplementation : implementation snapshot
    Node ..> TaipeiMilestones : date-anchored case (核定 ±1 day)

    ProjectGraph --> links : project-level twur + city links
```

## Notes

- **PDF** is the family skeleton and the heartbeat: one `RawRecord` per gazette row → one `CleanRecord` per node. `recno` is the only cross-PDF stable key (gazette renumbers every session).
- **Join identity** is the land core `{district}{section}{first_parcel}地號等{count}筆` (`build_land_core_key`), shared by merge and both portals.
- **Taipei** is pre-approval depth: per-`case_id` timelines (`case_milestones`), merged last-write-wins into `taipei_milestones` with provenance in `milestones_source`, plus `implementation` (`third.ashx`) and `rewards` (`fourth.ashx`).
- **National** is post-approval breadth: one `view/<id>` per project (revision rollup), `national_milestones` (推動歷程 incl. 使用核發, the only occupancy source).
- **Node anchoring** matches the node's date to a case's 核定日期/權變核定日期 exact-then-±1-day; per-record `implementation` snapshots ride onto nodes.
- **Two newer `DiscoveryResult` fields** (added after this diagram was first drawn): `case_schedules` — per-case state (已核准/已駁回/自行撤回/已失效/審查中/施工中) explaining why a project whose cases were all rejected has no national-portal page (§6.14); `view_verified_case_ids` — case_ids read off the project's *own* national view page 相關連結, portal-verified and therefore exempt from the landcore-similarity gate (§6.14 ghost creation).
- Sources: `urtpe/models.py`, `urtpe/graph.py`, `urtpe/links.py`, `openspec/specs/official-link-discovery/spec.md`.