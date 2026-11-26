## MODIFIED Requirements

### Requirement: Targeted portal search by land core

The system SHALL search the national portal list endpoint for each project lacking a twur link, using the project's section and its anchor record's **named first parcel** — the parcel immediately preceding 地號 in the anchor case name — as keywords in a `?title=` query parameter. The parcel keyword SHALL NOT be derived positionally from an enumerated land string. The system SHALL read the list pages of that search in order until a page adds no result it has not already seen, bounded by a fixed page cap, so that a section with more results than one list page holds is searched in full. A search that could not read every page it set out to read SHALL NOT be reported as a negative.

#### Scenario: Single unique view_id found
- **WHEN** the search for "中山段一小段254" returns exactly one `/view/` link
- **THEN** the system records that view_id and proceeds to fetch the view page

#### Scenario: Multiple view_ids found
- **WHEN** the search returns multiple `/view/` links
- **THEN** the system probes them in screened order under the probe-breadth rule and takes the first strict identity match

#### Scenario: No view_ids found
- **WHEN** the search returns zero `/view/` links
- **THEN** the system logs "no match" and skips to the next project

#### Scenario: Enumerated land string resolves to named first parcel
- **WHEN** the anchor record's land string enumerates parcels before 地號 (e.g., "寶清段四小段599、599-1、601、…、623地號等27筆土地")
- **THEN** the parcel keyword is the named first parcel (599), never the last enumerated parcel (623)

#### Scenario: Anchor parcel used verbatim across runs
- **WHEN** two projects share a section but are named after different parcels
- **THEN** each candidate carries its own anchor parcel and neither can satisfy the other's strict match

#### Scenario: Results span several list pages
- **WHEN** the search for a section returns 10 results on its first list page and 8 on its second
- **THEN** all 18 results are candidates for the probe-breadth rule, not only the first 10

#### Scenario: A page that adds no new result ends the reading
- **WHEN** a list page holds no `/view/` link that earlier pages did not already hold, or the page cap is reached
- **THEN** the system requests no further list page for that search

#### Scenario: A later list page fails after earlier pages answered
- **WHEN** the first list page answers and a later list page fails, or the stop time passes between list pages, and no probed page satisfies the strict identity match
- **THEN** the search is reported as an error, never as a negative, and no no-match entry is recorded for the project

#### Scenario: A later list page fails but a probed page matches
- **WHEN** a later list page fails and one of the results already read satisfies the strict identity match
- **THEN** the match is used, as for any partial failure that still matched

### Requirement: Strict view-page identity match

The system SHALL accept a searched view page as a candidate project's national page only when the page `<title>` parses to the same section, the same named first parcel, and — where both candidate and title carry a land count — an equal land count. All parcel and count comparisons SHALL be type-safe and SHALL tolerate notation drift (`之` ↔ `-` for sub-parcel suffixes, full-width ↔ ASCII digits). A page failing any applicable comparison SHALL be rejected and the next candidate probed. A title that carries no land count in any form, and therefore does not parse, SHALL be accepted when it names the candidate's section followed by the candidate's **whole** named first parcel and 地號, with no count after 地號, and the page text outside its `<title>` and its meta tags also names the parcel. A parcel is whole when no digit or hyphen directly precedes it and 地號 directly follows it, so `51-13` is not found inside `1-13`, `13` or `51-130`, and `51-1` is not found in `51-13`.

#### Scenario: Counted candidate matches its own page
- **WHEN** the candidate carries the text count `'27'` and the view title parses to the numeric count `27`
- **THEN** the count comparison passes and the page is accepted when section and parcel also agree

#### Scenario: Differing counts rejected
- **WHEN** both counts are present and differ after normalization (e.g., 等7筆 vs 等17筆)
- **THEN** the page is rejected

#### Scenario: Absent count skips the count check
- **WHEN** either the candidate or the parsed title carries no land count
- **THEN** acceptance is decided by section and parcel alone

#### Scenario: Sub-parcel notation drift tolerated
- **WHEN** the candidate parcel is written `263-19` and the title writes `263之19` (or digits differ only in full-width/ASCII form)
- **THEN** the parcels compare equal

#### Scenario: Wrong parcel or section rejected
- **WHEN** the parsed title's section or parcel differs from the candidate's keywords after normalization
- **THEN** the page is rejected even if the parcel string appears elsewhere in the page body

#### Scenario: Countless title matches by section and whole parcel
- **WHEN** the candidate is 寶清段一小段 `51-13` and the view title reads "…松山區寶清段一小段51-13地號土地都市更新事業計畫案…", with no 等N筆 and no N筆
- **THEN** the page is accepted, because the title names the section and the whole parcel before 地號 and the page text outside the title and meta tags names the parcel

#### Scenario: A countless title needs the parcel in the page text
- **WHEN** the title is countless and names the candidate's section and whole parcel, but the page text outside its title and meta tags does not name the parcel
- **THEN** the page is rejected

#### Scenario: A sibling parcel is not a countless match
- **WHEN** the candidate is `51-13` and the view title names `51-3` or `51-17` or `51-1`, or the candidate is `1-13` or `13` and the title names `51-13`
- **THEN** the page is rejected, whether or not the title carries a count

#### Scenario: A countless title for another section is rejected
- **WHEN** the title is countless and names the candidate's parcel under a different section
- **THEN** the page is rejected

#### Scenario: A title that parses keeps the strict rule
- **WHEN** the title carries a count in any form and parses to a different parcel or section than the candidate's
- **THEN** the countless rule does not apply and the page is rejected

### Requirement: Configurable view-probe breadth

The system SHALL probe a project's search-result view pages until one satisfies the strict identity match or the probe limit is reached. It SHALL probe first the results whose list title names the candidate's section followed by the candidate's whole named first parcel and 地號, and then the remaining results, each group in returned order. A list title SHALL only choose the order of probes: it SHALL NOT accept a page, reject a page, or remove a result from the candidates, and it SHALL NOT be parsed for a land count, because list titles can be cut short. The probe limit SHALL default to 8 and be overridable per run. When the limit truncates unprobed results without a match, the system SHALL note the truncation in run output while recording the no-match as usual.

#### Scenario: Match within limit
- **WHEN** one of the probed pages satisfies the strict identity match
- **THEN** probing stops there and the matched view_id is used

#### Scenario: Limit reached without match
- **WHEN** the probe limit is exhausted with no strict match and unprobed results remain
- **THEN** the project is recorded as a no-match and the run output notes how many results were left unprobed

#### Scenario: Probe limit overridden
- **WHEN** the script is started with an explicit probe-limit override
- **THEN** the override replaces the default of 8 for that run

#### Scenario: A title hit beyond the limit is probed first
- **WHEN** a search returns 18 results, the only result whose list title names the candidate's section and whole parcel is the 15th, and its page satisfies the strict identity match
- **THEN** that result is probed first and matched, and no other result is probed

#### Scenario: No title hit keeps the returned order
- **WHEN** no list title names the candidate's section and whole parcel, or the list carries no titles
- **THEN** the results are probed in returned order, up to the probe limit, as before

#### Scenario: A title hit that fails the strict match does not end the probing
- **WHEN** a result whose list title names the parcel is probed and its page fails the strict identity match
- **THEN** probing continues through the remaining results in order until the probe limit

#### Scenario: A cut-short list title only orders the probes
- **WHEN** a list title is cut off before its land count, or its count differs from the view page's
- **THEN** acceptance is still decided by the view page's own title under the strict identity match
