## Why

In the detail overlay's scrolling body, every heading sits closer to the section
*above* it than to the content it labels — 5px above, 15px below — so "Genres"
reads as a footer for the summary rather than as the start of the genre list.
The gaps between sections are not even either: three different values, because
the summary section imposes its prose leading on its own heading and because
some sections end in text and others in filled boxes.

The result is a body that reads as one undifferentiated column with headings
floating in the wrong places. It is the last part of the detail overlay that has
not been given the same treatment as its head, its artwork and its division.

## What Changes

- **One separation between sections, stated once.** The gap between a section
  and the next one becomes a single declared value, and the gap from a heading
  to its own content becomes exactly half of it — so a heading always groups
  downward, with what it introduces.
- **The first heading clears the division by that same separation.** The border
  under the poster block is the strongest break in the body; it may not be the
  smallest gap. Today it is 20px against section gaps that will be larger.
- **A heading's leading is stated by the rule that sets a heading's type**, so no
  section can change where its own heading sits by setting leading for its prose.
  The summary section does exactly that today: `line-height: 1.7` on the section
  is inherited by the "Overview" heading, which is why that one heading sits
  ~2px lower and ~5px further from its text than the other three.
- **Prose trims its half-leading at a section's edges**, so a section that ends
  in text and one that ends in a filled box (a genre pill, a cast card) leave the
  same visible gap. The eye measures to the glyph for bare text and to the edge
  for a filled object; without the trim those two differ by the prose's
  half-leading, which is ~5.6px on a ~24px gap.
- The dead `.summary-section` rule goes: once its leading moves to the prose, its
  only other declaration restates the inherited body colour.
- No behaviour changes. Nothing opens, closes, scrolls or drags differently.

Not breaking. Nothing about the frozen `docker-compose.yml` surface is touched:
no environment variable, no image name, no port, no volume. An existing user's
compose file runs this unchanged.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `media-detail`: the detail overlay's scrolling body gains a stated vertical
  rhythm — one separation between its sections, half that between a heading and
  its content, prose trimmed so a text-ended section and a box-ended section
  leave the same gap. The existing requirement that the scrolling region starts
  clear of the division above it is tightened: that clearance is now the same
  separation the sections use, rather than a number of its own.

## Impact

- `web/index.html` — the `.modal-section`, `.modal-section-title` and
  `.summary-section` rules, the detail overlay's body markup, and the two
  strings `openModal()` writes as prose (the Date Added value and the
  no-genres / no-cast fallbacks).
- `web/assets/overlays.css` — `.modal__fixed + .modal__body` reads the shared
  separation instead of restating 20px.
- `web/assets/tokens.css` — one new token for that separation. It is genuinely
  cross-file: two rules in two files have to agree about it, which is the
  condition tokens.css exists for.
- `tests/` — a new test pinning the rhythm's source decisions. CI has no
  browser, so it pins the relations (heading gap is half the section gap; the
  prose trim is derived from the prose's own leading) rather than rendered
  pixels.
- `CLAUDE.md` — the grouping rule and the leading trim are the kind of decision
  that is invisible in the diff and easy to undo.
- No Python, no Dockerfile, no entrypoint, no nginx config. `make docker-smoke`
  is not required.
