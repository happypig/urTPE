## Why

The viewer fixes of 2026-11-10 (commit `9d1eeaf`, operations log §41) exposed two
places where the shipped code now enforces a rule the specs never state:

1. **The approval/execution interleave key is unspecified.** The version graph
   interleaved execution events (建照/開工/使照) into the approval timeline using
   `m.date || cluster.effDate` — but `effDate` is the *cluster sort sentinel*
   (including `"9999-12-31"` for undated-only clusters), not a row key. An undated
   orphan row in a dated cluster inherited the cluster's date, so on
   北投區-桃源段四小段424-8地號等15筆 the 建照核發(2021/10/28) and 開工(2022/07/27)
   rows rendered above the 2021-01-12 approval they follow. 8 projects and 22
   inverted pairs measured before the fix; 0 after. The fix made the interleave key
   identical to the member sort key: `m.date || ownEventDate(m, p) || ""`.
   A regression to the old shape passes today's spec, because the spec never says
   which date an undated row contributes.

2. **The cache-bust does not force the stylesheet.** `pdf-tsv-extraction`'s
   cache-bust scenario says the asset version "referenced by `index.html`" is
   derived from the publication date — but nothing requires *every* cacheable
   reference to carry a version. `viewer/index.html` loaded `app.css` with no
   `?v=`, so `urtpe/viewer.py:_asset_version`'s rewrite had nothing to match, and
   browsers paired the fixed `app.js` with a stale cached `app.css`; the
   `flex-shrink: 0` callout rule never applied until the link was bumped by hand.
   The fix versioned the stylesheet link (`app.css?v=…`) and taught `_ASSET_VERSION_RE`
   to rewrite it.

Both defects are already fixed and deployed (all 5 artifacts FRESH, suite
1180 passed / 1 skipped). This change only closes the spec gap so the archive
carries the rule the code now enforces — the user asked for the spec sync
explicitly.

## What Changes

- **`viewer-graph-layout`**: MODIFY the requirement "The version graph interleaves
  approvals and execution events chronologically" — add the missing rule that the
  interleave key for an approval row is the member's own sort key
  (`m.date || ownEventDate || ""`), never the cluster's `effDate` (a sort sentinel),
  plus one scenario pinning the 桃源424-8 shape (undated row in a dated cluster:
  its execution events still interleave by its own event date).
- **`pdf-tsv-extraction`**: MODIFY the cache-bust requirement — every cacheable
  asset reference in `index.html` (scripts **and** stylesheets) carries the derived
  version, and an unversioned reference is a fault the rewrite reports, plus one
  scenario pinning the app.css shape.

No code changes: the behavior described is what commit `9d1eeaf` already shipped.

## Capabilities

### New Capabilities

<!-- none — both capabilities exist -->

### Modified Capabilities

- `viewer-graph-layout`: the approval/execution interleave requirement gains the
  rule that the per-row interleave key is the member sort key, never the cluster
  `effDate` sort sentinel, with a scenario for the undated-row-in-dated-cluster shape.
- `pdf-tsv-extraction`: the cache-bust requirement gains the rule that every
  cacheable reference in `index.html` (scripts and stylesheets alike) carries the
  derived version, with a scenario for an unversioned stylesheet link.

## Impact

- `openspec/specs/viewer-graph-layout/spec.md` — one requirement MODIFIED
  (interleave), all five existing scenarios carried verbatim, one scenario added.
- `openspec/specs/pdf-tsv-extraction/spec.md` — one requirement MODIFIED
  (cache-bust), its four existing scenarios carried verbatim, one scenario added.
- Verification evidence already in hand: browser sweep of all 681 projects
  (0 inverted pairs, 0 clipped boxes), `node scripts/viewer_smoke.js` clean,
  `python scripts/check_deploy.py` all 5 FRESH, live 桃源424-8 graph ordered
  correctly. The pinned tests live in `tests/test_viewer_labels.py`
  (`9d1eeaf`); the archive steps assert them rather than re-writing code.
