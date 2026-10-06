# A human-verified portal link, recorded so it survives the next sweep

## Why

`萬華區-崇仁新村青年段一小段-711-3地號等?筆` does have a national-portal page —
`view/18` — and the sweep will never find it, for two independent reasons:

**The search key is wrong.** We search `崇仁新村青年段一小段`. The portal indexes the unit
as `崇仁新村`; searching that returns `['18']`. The 段 token sits after the neighbourhood
name in our identity and nowhere in the portal's.

**The strict matcher is right to refuse.** `view_page_matches` returns `False`, and
`parse_name_id` extracts nothing from the portal's title at all:

```
擬訂臺北市萬華區青年段一小段711地號、二小段18地號(原崇仁新村)都市更新事業計畫及權利變換…
  -> district='' section='' parcel='' count=None
```

The portal writes a two-section title with a parenthetical anchor, which a single-section
pattern cannot read. And our parcel is **711-3** where the portal says **711** — a
renumbering, the `689地號(原726地號)` case the project context names as breaking exact-key
matching.

Neither fix alone would find it: a different search key still fails the matcher, and a
relaxed parcel rule still never sees the page.

**The population is one.** Measured across all 75 twur-less projects: exactly one has a
`project_id` of the form `等?筆`, meaning the current node's land string carries no `等N筆`
clause and the count never parsed. Two case names contain no digits at all; thirteen carry
a `(原…)` anchor; twenty-three have a sub-parcel first parcel. Only this one has all the
properties that make the portal's title unreadable.

## What Changes

- **A tracked override table** mapping `project_id` to a portal view id, applied at
  cache-load time — the same pattern as `data/project_aliases.json`, which is already
  tracked for the same reason.
- **The override fills a gap and never displaces a machine match.** If a project already has
  a `twur_view_id` from discovery, the override is inert for it.
- **The override records its evidence**: the portal URL, the title it was verified against,
  the date, and why the strict matcher could not claim it. Without that, a future reader
  would either re-investigate or "fix" it by loosening the parcel rule.
- **Milestones and case ids are still fetched from the real page**, through the sweep's
  existing cache-update path, so the resulting entry is a normal one rather than a
  hand-assembled one.

## What this deliberately does not do

**It does not relax the parcel test.** A rename-tolerant rule that accepts `711` for `711-3`
would have to adjudicate 23 sub-parcel projects, and the asymmetry is decisive: a false
positive attaches another project's milestones to this one, while a false negative leaves one
project without a link. Trading 634 correct matches for 1 is not a close call.

**It does not add a general fallback matcher.** That is the same loosening by another route.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `official-link-discovery`: a human-verified portal link may be recorded as configuration
  and applied when discovery found nothing, carrying the evidence it was verified against.

## Impact

- **New, tracked:** `data/twur_overrides.json` — configuration, not derived data, with a
  `.gitignore` exception alongside the alias table.
- **Changed:** `urtpe/links.py` — `load_twur_overrides()` and its application in
  `load_project_cache`.
- **Data:** the project gains its portal link, its ledger entry clears, and
  `viewer/projects.data.js` regenerates. Coverage moves 634 → 635 of 709.