## Purpose

Ensures the viewer layout works on mobile by stacking the project list above the detail pane at narrow viewports, removing fixed widths, and providing a responsive breakpoint.

## ADDED Requirements

### Requirement: Stack project list above detail on narrow screens

The system SHALL render the project list and detail pane as a vertical stack (list above detail) when the viewport width is below ~768px, and as a side-by-side layout at wider widths.

#### Scenario: Mobile viewport shows list then detail
- **WHEN** the viewport width is 375px (mobile)
- **THEN** the project list occupies the full width at the top
- **AND** the detail pane renders below it, full width
- **AND** no horizontal scrolling is needed

#### Scenario: Desktop viewport shows side-by-side
- **WHEN** the viewport width is 1200px (desktop)
- **THEN** the project list and detail pane render side-by-side
- **AND** the list has a flexible width (not fixed 340px)

#### Scenario: Layout transitions at breakpoint
- **WHEN** the viewport is resized across ~768px
- **THEN** the layout switches between stacked and side-by-side without reload
- **AND** no content is clipped or overflows horizontally

### Requirement: List has flexible width, no fixed pixel size

The system SHALL remove the fixed 340px width on the project list and use a flexible or percentage-based width instead.

#### Scenario: List width adapts to container
- **WHEN** the list container width changes
- **THEN** the list width adjusts proportionally (e.g., 30% on desktop, 100% on mobile)
- **AND** list items remain readable (text does not wrap excessively)

### Requirement: Detail table supports horizontal scroll on mobile

The system SHALL allow the detail record table to scroll horizontally on narrow viewports so all columns remain accessible.

#### Scenario: Table scrolls horizontally on mobile
- **WHEN** the detail table has more columns than fit in the viewport
- **THEN** the table container shows a horizontal scrollbar
- **AND** the user can scroll to see all columns without page-level horizontal scroll