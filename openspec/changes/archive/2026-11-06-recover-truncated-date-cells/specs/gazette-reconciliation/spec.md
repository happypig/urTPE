## ADDED Requirements

### Requirement: A recovered date cell is not a publisher edit, and its re-dated twin is not a withdrawal

A row whose 核定日期 cell the publisher left empty and the recovery pass
completed from the city's own case record SHALL be reported as **recovered by
this reader**, not as an edited or withdrawn row.

The comparison has a subtlety the 地號 case does not. The predecessor's read
holds that approval under **its own** date, and the new publication reprints
it with an **empty** date. So the row's identity key — which includes the
date — no longer matches, and the reconciler would report the approval as
**withdrawn from the previous newest cohort** even though the city republished
it and the recovery pass recovered its date.

The recovered row SHALL therefore be excluded from the withdrawn count and from
the edited count, and counted under the recovered count. The approval was
neither withdrawn nor edited: the city reprinted it, and the reader completed
the cell the publisher left blank.

#### Scenario: A re-published approval with an emptied date is not a withdrawal

- **WHEN** a publication reprints an approval the predecessor held, with the
  核定日期 cell empty, and the recovery pass recovers that date from the city's
  case record
- **THEN** the report states `recovered by this reader: 1` and names the row
- **AND** the approval is NOT counted among the withdrawn rows
- **AND** it is NOT counted among the edited rows
- **AND** the net change counts the row as present on both sides

#### Scenario: A date recovered from the platform does not move the approval

- **WHEN** the recovered date equals the date the predecessor's read held for
  the same approval
- **THEN** the approval appears unchanged in the comparison
- **AND** the recovered count names it as recovered
