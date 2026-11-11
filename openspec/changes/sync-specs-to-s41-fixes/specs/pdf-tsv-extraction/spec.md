## MODIFIED Requirements

### Requirement: Capture the official published date from the document

The system SHALL read the "統計至" line from the document and emit it as publication metadata alongside the raw TSV, without treating it as page furniture. The publication date SHALL be derived from the document's own content and SHALL NOT be a fixed value.

When the viewer data is written, every cacheable asset reference in `index.html` SHALL carry the derived asset version — script references and stylesheet references alike. A cacheable reference left unversioned is a fault: a browser can then pair a re-fetched script with a stale cached stylesheet, and a CSS change ships only to viewers whose cache happens to be empty. The rewrite SHALL report an unversioned reference rather than leave it silently un-busted.

#### Scenario: Published date is read from the document

- **WHEN** a PDF whose 統計至 line reads `統計至115年9月24日` is processed
- **THEN** the metadata records that publication date rather than any previously known value
- **AND** the 統計至 line itself appears in no data row

#### Scenario: Publication date differs from any prior run

- **WHEN** a PDF is processed whose 統計至 date differs from the date recorded for the previously ingested gazette
- **THEN** the metadata carries the date found in this document
- **AND** no previously recorded date is substituted

#### Scenario: Published date threads through pipeline meta

- **WHEN** the CLI runs with the extracted publication date
- **THEN** it appears in the pipeline meta dict, in projects.json, in projects.data.js
- **AND** the viewer header displays the publication date rather than a generation timestamp

#### Scenario: A run refreshes the viewer without being asked

- **WHEN** a run targets the repository's own output tree
- **THEN** the viewer's `projects.data.js` is rewritten from the dataset that run emitted, whether or not a viewer target was passed
- **AND** the viewer cannot continue to serve a dataset an earlier or abandoned publication produced

#### Scenario: The cache-bust names the publication the data carries

- **WHEN** the viewer data is written
- **THEN** the asset version referenced by `index.html` is derived from the emitted dataset's publication date
- **AND** it is not a literal maintained by hand, so it cannot name a publication the data does not carry

#### Scenario: Every cacheable reference carries the version

- **WHEN** the viewer data is written and the asset version is rewritten into `index.html`
- **THEN** each script reference and each stylesheet reference carries the derived version
- **AND** a stylesheet left without the version is reported as a fault, because the measured
  failure paired a re-fetched `app.js` with a stale cached `app.css` and shipped a CSS fix
  only to viewers with an empty cache
