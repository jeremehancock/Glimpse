## ADDED Requirements

### Requirement: A dragged tab is moved, and nothing else is done to it

A tab being dragged SHALL be displaced horizontally and SHALL NOT be given any
other presentational treatment for the duration of the gesture. It SHALL NOT be
scaled, and the surface behind it SHALL NOT be dimmed, tinted, or otherwise
altered.

It SHALL also keep the box it had in the page. Taking a tab out of the scroller
SHALL NOT change its width or its horizontal position, so the grid inside it
holds its column count and its card size for the whole gesture. A fixed element
does not inherit its container's padding, so a tab pinned to the viewport's
edges is wider than the tab was — measured at +20px, which the grid spends on
its cards. A grid that grows when a thumb lands and shrinks when it lifts is the
same defect as one that drops.

The raised presentation was built and shipped, and the viewer's report of it was
that the grid drops. A scale anchored to the centre of the viewport moves
everything above that centre downward — measured at roughly 23px of vertical
displacement on a phone-sized viewport, arriving instantly as the gesture is
claimed and reversing on release. In a gesture whose entire meaning is
horizontal, a vertical movement is not read as depth. It is read as the page
misbehaving, and it lands before any horizontal motion has begun, so it is the
first thing seen.

The scrim SHALL go with the scale rather than survive it. What it dimmed was the
gap the scale opened between the two tabs — 23px of page down each side, which
is what made the panels read as lifted. Unscaled, what separates them is the
page's own padding: the same strip of background the page shows at its edges
while nobody is touching it. Dimming that does not read as depth; it reads as a
tinted stripe tracking the thumb, which is precisely how the drop shadow failed
before it.

Depth on these panels SHALL NOT be reintroduced by another route. Elevation and
corner radius were tried before the scale and removed for a reason that still
holds and is not about taste: a tab is as tall as the whole library and pinned at
the viewer's scroll offset, so only one viewport of it is ever on screen and
neither end of it is. A shadow renders as a band down each vertical edge tracking
the thumb; a radius renders nothing at all.

#### Scenario: A dragged tab keeps its size

- **WHEN** a horizontal tab drag is claimed and driven across the viewport
- **THEN** neither tab SHALL change size at any point, and no content in either
  tab SHALL move vertically

#### Scenario: Taking a tab out of the scroller does not resize it

- **WHEN** a tab is pinned for a drag or a transition
- **THEN** its width and its horizontal position SHALL be those it had in the
  page, and the cards in its grid SHALL keep the size they had at rest

#### Scenario: The page behind the tabs is not dimmed

- **WHEN** a tab drag is in progress at any offset
- **THEN** no scrim, tint or overlay SHALL be drawn behind or over either tab

#### Scenario: The gesture's first frame is horizontal

- **WHEN** a drag is claimed at the axis-lock distance
- **THEN** the only change on screen SHALL be the tabs' horizontal offset

## REMOVED Requirements

### Requirement: A tab being dragged is lifted off the page

**Reason**: The lift's scale is anchored to the viewport centre, so claiming the
gesture displaces the visible grid downward by about 23px with no easing and
restores it on release. The intended reading was depth; the received reading is
that the grid drops and bounces, which is the complaint this change answers. The
scrim is removed with it because without the scale the two tabs sit edge to edge
and it has nowhere to render.

**Migration**: None — no configuration, no data, and no user-facing surface
depended on it. The gesture keeps its horizontal follow, its commit threshold,
its flick test, its resisted end and its settle unchanged. `--tab-drag-lift` and
`--tab-drag-scrim` are removed from the token set; nothing outside the tab
gesture read either. The behaviour that replaces this requirement is stated
positively above, so a future reintroduction has to argue with a requirement
rather than with an absence.
