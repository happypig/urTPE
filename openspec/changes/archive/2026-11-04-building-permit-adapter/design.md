# Design: building-permit-adapter

## Context

Actors: the building authority's open data (data.taipei, XML, no key), the
archive root (`D:\project\urtpe-gazettes\`, the gazettes' durable home, overridable
with `URTPE_ARCHIVE_ROOT`), `urtpe/links.py` (the attach path), and the
viewer (`viewer/app.js` `buildConstructionChain`, `fmtDate`).

Flow: the adapter downloads the two 使用執照摘要 datasets (歷年 + 115年度)
into `<archive_root>/permits/`, keyed by SHA-256 (`AGENTS.md`: content-hash
detection, never mtime); parses each `<Data>` record; indexes by
(district, section, parcel-mono); `attach_links_to_projects` (or the sweep)
looks each project's parcel list up in the index and attaches the best
建字-origin permit as `links.permit`; the viewer renders the permit as the
third witness beside the two portals and flags disagreement.

## Decisions

### D1 — The permit file is acquisition, not ingestion

The download lives in the adapter module and its cache under the archive
root; nothing touches the emitted dataset at download time. The single-writer
lock serialises the download with every other writer. A failed download is
reported, never fatal — the pipeline emits without the permit witness.

### D2 — Index by (district, section, parcel-mono), match by parcel overlap

Each `<地段號>` reads `臺北市{district}{section}{mono}-{suno}號`; the mono is
the key (full-width digits normalised, leading zeros stripped). A project
matches when its parcel list (the nodes' `parcels`) overlaps the permit's
parcel set; the permit(s) with the most overlapping parcels win. Ties keep
all (an area split issues one permit per area — 懷生931 東區/西區).

### D3 — 建字 origin is the 使照; 雜字 is not

`原核發執照` carries the building permit the 使照 closed. Permits whose
`執照號碼` is 雜字 (雜項執照 — 奇岩13's 2014-06-19, 龍泉712's 2006) or whose
`原核發執照` is not 建字 are not the building's 使照. The rule: take the
permit whose `原核發執照` starts 建字; when several, one per area split.

### D4 — The permit is a witness, never a repair

The emitted `links.permit` is `{permit_no, date}` (ISO). The 使照 slot's
value keeps its current preference (city, then national). The disagreement
flag names the permit that confirms one side:
`使照兩源不一致(城市X/國Y/執照Z證實Y)` — or `執照Z介於兩者之間` when the
permit matches neither (4 measured). When no permit matches the parcel list,
both portal dates stay and the flag reads `使照兩源不一致(無執照佐證)` — the
never-repair-by-inference rule.

### D5 — fmtDate guards the out-of-range ROC year

`fmtDate`'s ROC branch (year < 1911 ⇒ +1911) fabricated 2202 from
橋北574-1's `291.08.02`. The guard: an ROC year above the current 民國 year
(>115 at emit time) renders the raw text plus the `date-range-warning` class;
the 使照 slot and the stage chip keep the city's value. The same guard sits
in the viewer's construction-chain normaliser, which currently maps any
`\d{2,3}` ROC year.

### D6 — Where the adapter runs

Download + index build: on demand, in the discovery run (`--links`), gated by
the SHA-256 cache. Index build takes seconds over 8,946 records; the 65 MB
XML parses once per download. The match runs per project at attach time —
no per-project request.

## Consequences

- 17 of 22 disagreements name a confirming permit; 12 of 13 national-only
  dates gain a witness; 4 permit-matches-neither keep both values and the
  named flag; 2 parcel-list misses keep the flag (D4).
- The archive root gains `permits/` (2 files + hashes) — the cadence layer's
  pattern, not a new mechanism.
- S7's flag-only plan is superseded; its `fmtDate` range guard ships here.
