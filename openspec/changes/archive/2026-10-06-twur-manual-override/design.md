# Design — twur-manual-override

## Context

One project of 709 has a portal page the sweep cannot reach:

```
view/18  擬訂臺北市萬華區青年段一小段711地號、二小段18地號(原崇仁新村)都市更新事業計畫及權利變換…
```

Two independent causes, either of which alone is fatal:

| | ours | portal |
|---|---|---|
| search key | `崇仁新村青年段一小段` → nothing | `崇仁新村` → `['18']` |
| first parcel | `711-3` | `711` |
| title shape | single section + `等N筆` | two sections + `(原崇仁新村)`, no `等N筆` |

`parse_name_id` extracts nothing from that title, so the strict matcher cannot match it and
the project stays twur-less indefinitely.

## Goals

- The verified link survives a fresh clone and a re-sweep.
- It cannot displace a machine-discovered link.
- The decision is auditable: the evidence travels with the record.

## Decisions

### D1 — Configuration, not a cache artefact

The precedent is `data/project_aliases.json`: tracked, with a `.gitignore` exception, because
a clone without it strands work that cannot be regenerated. A per-project `result.json`
write would satisfy today's dataset and nothing else — the next `--fresh` run would drop it
with no record that it had ever been found, which is exactly how the 14 zero-result entries
became unauditable in the first place.

### D2 — Gap-fill only

`load_project_cache` applies a recorded link **only when `twur_view_id` is absent**. A
recorded link is a human assertion about a project discovery could not resolve; letting it
override a real discovery result would mean one careless record silently rewrites data the
portal actually returned. Gap-fill makes the blast radius of a wrong record zero when
discovery succeeds, and the full project only when discovery has nothing.

### D3 — Refuse a record without evidence

A record carrying only a view id is refused and reported. An unattributed link cannot be
audited, and the failure mode of a wrong link — another project's 推動歷程 attached to this
one — is invisible downstream. Requiring `verified_url`, `portal_title` and `verified_on`
makes the record self-describing, and the *reason* field specifically exists to stop someone
later "fixing" this by loosening the parcel rule.

### D4 — Fetch milestones, do not hand-enter them

The override supplies identity only. The portal page is fetched and parsed by the sweep's
existing `extract_tuidui_history_from_view` / `extract_case_ids_from_view`, and written
through `update_project_cache`, which is the same path a discovered match takes. A
hand-assembled cache entry would differ in shape from all 634 others and would be the kind of
one-off that AGENTS.md calls obsolete by construction.

### D5 — No general fallback matcher

The obvious generalisation — accept a parcel whose base matches after stripping the sub-part,
or parse multi-section titles — would have to adjudicate 23 sub-parcel projects and an
unknown number of two-section titles. Asymmetry decides it: a false positive attaches the
wrong project's milestones and 執行階段 to this one, silently and invisibly in the viewer; a
false negative leaves one project without a link, visibly. Trading 634 correct for 1 is not
close.

If a second project ever turns out to need this, the measurement repeats and the decision can
be revisited on two data points rather than one.

## Risks

- **Staleness.** A recorded view id could be superseded if the city renumbers a project. The
  `verified_on` date is the audit trail; nothing invalidates it automatically, by design —
  an automatic check would be the general matcher this change refuses to build.
- **Identity churn.** If this project's `project_id` moves, the record stops applying. D3's
  "report a record naming an unknown project" scenario exists so that surfaces as a warning
  rather than silence.

## Migration

None. The table starts with one entry. Nothing existing reads it.