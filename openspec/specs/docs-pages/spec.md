# docs-pages Specification

## Purpose

The two hand-written doc pages — `docs/etl_process.html` and
`docs/domain-model.html` — are the site's prose write-ups. The site's readers
are zh_TW policy readers; every generated page they arrive from is zh_TW, so
these two open zh_TW too, carry both renderings in one DOM (pairing-based
en/zh spans; technical names verbatim), and hold the language switch at the
header's right edge beside the 關於 chip. The generators' reports
(release-diff, coverage) are generator-emitted zh_TW-only and out of scope.

## Requirements
### Requirement: The hand-written doc pages are bilingual

`docs/etl_process.html` and `docs/domain-model.html` SHALL carry both an
English and a zh_TW rendering of their prose — both in the DOM, one hidden by
CSS — with a language switch in the header that toggles between them without
a reload. The page SHALL render exactly one reading of each passage with
scripting disabled. Technical names — file paths, module names, command
lines, flags, exit codes, spec section numbers — SHALL stay verbatim in both
renderings.

#### Scenario: The switch toggles the language

- **WHEN** the reader uses the header's language switch
- **THEN** the prose swaps between the English and the zh_TW rendering without a reload
- **AND** technical names render identically in both

#### Scenario: The page renders with scripting disabled

- **WHEN** either page is opened with JavaScript disabled
- **THEN** exactly one rendering of each passage shows, chosen by the default-language rule below

### Requirement: The hand-written doc pages default to zh_TW

Both pages SHALL open showing the zh_TW rendering: the document element
declares `lang="zh-Hant"`, and the CSS hides the English rendering until the
reader switches to it. The switch sits at the header's right edge,
immediately left of the 關於 chip — not centre-aligned between the title and
the chip.

#### Scenario: A fresh visit shows zh_TW

- **WHEN** either page is opened with no stored state
- **THEN** the zh_TW rendering is shown and the document element declares `lang="zh-Hant"`

#### Scenario: The switch sits beside the 關於 chip

- **WHEN** either page's header is read
- **THEN** the language switch is the element immediately before the 關於 chip, at the header's right edge
- **AND** the 關於 chip remains the header's last link

