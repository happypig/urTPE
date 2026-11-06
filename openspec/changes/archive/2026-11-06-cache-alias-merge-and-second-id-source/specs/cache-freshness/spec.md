## ADDED Requirements

### Requirement: An aliased cache directory is merged, not shadowed

When a project's current cache directory exists and an **aliased** directory
(the project's former identity, per `data/project_aliases.json`) also exists,
the system SHALL **merge** the aliased directory's content into the current
one rather than ignoring it.

The merge SHALL add the aliased directory's case ids and per-case milestones
that the current directory lacks, and SHALL keep the current directory's own
content on a conflict. The current directory's identity fields (its own
`project_id` and `land_core`) SHALL NOT be overwritten — the current id is the
one the dataset holds.

**Reason:** the current directory can be a stub. A run that wrote a fresh
directory under a project's new identity, before the old directory's content
was carried over, left the richer directory unreadable — `resolve_cache_dir`
returned the current directory whenever it existed, so the alias was never
consulted. The result was silent: two nodes kept the flag
`節點未能對應平台案件` although the case and its milestones were in the cache
all along (南港566: case `10708311`, 核定 2019-11-20, and `10006032`, 核定
2016-02-25).

#### Scenario: A stub and a richer aliased directory are merged

- **WHEN** a project's current cache directory holds one case id and an aliased
  directory holds three
- **THEN** the current directory holds all three case ids
- **AND** the current directory's own `project_id` and `land_core` are unchanged

#### Scenario: A conflict keeps the current directory's value

- **WHEN** both directories carry milestones for the same case id and they
  differ
- **THEN** the current directory's value is kept

#### Scenario: No aliased directory changes nothing

- **WHEN** a project has no aliased directory
- **THEN** the cache is read and written exactly as before

#### Scenario: The merge is reported

- **WHEN** a merge added case ids or milestones to a project's cache
- **THEN** the run names the project and what was added
