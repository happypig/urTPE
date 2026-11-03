## Context

`buildRelatedLinkLabels` labels each case a node anchors with the node's
`case_name` (byCase built from nodes first). The city's own name is harvested
per case in `candidate_names[cid]` but consulted only for cases no node
anchors. The 國 label takes `anchorName` = the current node's gazette name;
the national page's own name (the `<title>`) is never stored.

## Goals / Non-Goals

**Goals:**
- One name per case: the city's own (`candidate_names[cid]`), falling back to
  the node label when the harvest lacks the id.
- 國 labelled by the page's own name (`twur_name`).

**Non-Goals:**
- The graph's node label (gazette row) is unchanged — it is the PDF's own text.
- No fetch: `twur_name` comes from the cached `view.html`.

## Decisions

### 1. Chain order: city name before node label for anchored cases

The existing chain keeps its levels for orphan ids; for an id a node anchors,
`candidate_names[cid]` precedes `node.case_name`. A candidate_names entry the
harvest wrote is the platform's own word; the node label is the gazette's
abbreviation of it.

### 2. twur_name from the cached page

At absorb (and for caches the refresh re-absorbs), parse
`<title>(.*?)-都更查詢` from `view.html` and store `result.twur_name`. The
viewer labels 國 with it when present, else falls back to the current name.
