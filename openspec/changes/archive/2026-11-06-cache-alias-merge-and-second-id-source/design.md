## Context

`resolve_cache_dir` (`urtpe/links.py:1581-1591`) resolves a project's cache
directory:

```python
direct = _project_cache_dir(cache_dir, project_id)
if direct.exists():
    return direct
former = load_alias_table(cache_dir).get(project_id)
if former:
    aliased = _project_cache_dir(cache_dir, former)
    if aliased.exists():
        return aliased
return direct
```

The **direct directory wins whenever it exists**. The alias is consulted only
when there is no direct directory.

That is fine when the direct directory is a full cache. It is a loss when the
direct directory is a **stub**: the 2026-11-02 run wrote a stub under
`南港區-南港段四小段-566地號等1筆` (one case id, `10708312`), while the richer
directory `…等6筆` — the project's former identity, aliased in
`data/project_aliases.json` — held three case ids with full milestones.

The measured loss: 2 of the 16 unplaced nodes (`節點未能對應平台案件`).
Node 744 binds case `10708311` (核定 2019-11-20) and node 1063 binds case
`10006032` (核定 2016-02-25) — both by the date matcher, both from ids the
cache already held.

`11412011` (玉成166) is in **no** cache at all, so it needs an id source.

## Goals / Non-Goals

**Goals:**

- The cache a project resolves to holds everything either of its directories
  holds.
- A case id the parcel search does not index can still reach the payload,
  confirmed by its own header.

**Non-Goals**

- Changing the alias table. It is configuration, and its pairs are correct.
- Deleting the stranded directory. It is the evidence of what was found, and
  the merge is additive.
- Loosening the parcel matcher. AGENTS.md warns against it, and the D6
  override's own `reason` names the cost.
- The parcel search's recall limit. It stays as it is; the second id source
  is the answer to it, not a change to it.

## Decisions

**D1 — The merge happens where the cache is read, not where it is written.**

`load_project_cache` reads the resolved directory. The merge belongs there:
the read is the point where the stub is discovered, and the merge can then be
written back so the next run finds a complete cache.

*Alternative considered:* merge at write time (in `save_project_cache`).
Rejected — the write path does not know the project's former identity, and a
write that silently unions two directories' content is harder to audit than a
read that reports what it added.

**D2 — The current directory wins a conflict.**

The current directory's content is the newer reading (it was written under the
current identity). The aliased directory contributes only what the current one
lacks. The identity fields (`project_id`, `land_core`) are never overwritten —
the current id is the one the dataset holds, and the aliased directory's
`land_core` names the former identity.

**D3 — The second id source is the 168 list, confirmed by the header.**

The 168 list (`Get_project168.ashx`) names case ids the parcel search does not
index. It is a register of cases in the 168 fast-track programme, not of one
project's cases, so an id from it is a **candidate**: it enters the project's
case list only when its own header confirms it (a row with a 案名).

The header is the confirmation because it is the city's own statement about
that case, and it is what the resolver's name step matches against. An empty
header is not a confirmation — the same "one empty response is no evidence"
rule the D13 label follows.

*Alternative considered:* match the header's 案名 against the project's 案名
directly. Rejected — the resolver already does that, and the header
confirmation's job is only to establish that the id names a real case.

**D4 — The ids are appended, never inserted.**

The positional fallback binds by index, so an inserted id would shift every
later id's position. The append rule is the same one the search step already
follows.

## Risks / Trade-offs

- **[The merge adds an id that belongs to another unit]** → The added ids come
  from a directory the alias table pairs with this project on **member
  content** (the alias table's basis is "identical ISO date and parcel cell"),
  so they are this project's cases. The resolver's name-and-date steps bind
  them; the merge does not bind anything by itself.

- **[The 168 list adds ids that do not belong]** → The header confirmation
  establishes that the id names a case; the resolver's name step then decides
  whether the case belongs to this project. An id that does not bind becomes
  an orphan node with its own flag — the same reading as any other unplaced
  case.

- **[The merged cache is written back]** → The write is additive and the
  current directory's own fields are preserved. A backup of the cache is taken
  before the pass.
