## ADDED Requirements

### Requirement: A genre is presented as a tappable choice, not as raw button chrome

Each entry in the genre tray SHALL carry its own background, border and radius,
sized so the whole entry is a comfortable touch target.

It SHALL NOT rely on the browser's default button appearance. The entry is a
`<button>` carrying two `<span>`s, and the rule that styles it was written for
full-width `<div>` rows in a dropdown that no longer exists — so with no
presentation of its own it renders as the user agent's own control: a white box
with a system border, laid out inline and wrapping raggedly.

The entries SHALL wrap within the tray's width, and none SHALL overflow it
horizontally.

The entry representing the active genre SHALL be visually distinct from the
others, and SHALL carry that state in the accessibility tree as well as in its
appearance — a class alone is invisible to a screen reader.

#### Scenario: An entry is presented as a control

- **WHEN** the genre tray is opened
- **THEN** each entry SHALL draw its own background, border and radius rather
  than the browser's default button appearance

#### Scenario: Entries wrap inside the tray

- **WHEN** the genre tray is opened at any supported width
- **THEN** the entries SHALL wrap within the tray and none SHALL extend beyond
  its horizontal bounds

#### Scenario: The active genre is marked

- **WHEN** a genre other than the default is in force and the tray is opened
- **THEN** that entry SHALL be visually distinct and SHALL expose its selected
  state to assistive technology

### Requirement: A genre's count is secondary to its name

Where an entry shows how many items a genre holds, the count SHALL be separated
from the name and SHALL be presented as secondary information — quieter than the
name it qualifies.

The two SHALL NOT run together. With neither element styled, `Action` and `794`
abut as `Action794`, which reads as one word and makes the name unrecognisable at
a glance.

An entry whose count is zero or unknown SHALL show no count rather than a zero.

#### Scenario: Name and count are distinguishable

- **WHEN** an entry with a count is shown
- **THEN** the count SHALL be visually separated from the name and rendered
  less prominently

#### Scenario: No count is shown when there is none

- **WHEN** an entry has no count
- **THEN** no count element SHALL be visible for it
