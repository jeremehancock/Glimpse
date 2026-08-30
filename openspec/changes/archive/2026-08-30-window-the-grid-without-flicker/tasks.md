## 1. Establish the baseline

- [x] 1.1 Seed a library large enough to scroll a window through (thousands of
      items) and record, with `tools/grid_metrics.py` against a real browser at
      phone width, how many times `renderWindow()` runs per full window
      traversal in each scroll direction. This is the number the change has to
      move, and without it there is nothing to compare against.
- [x] 1.2 Confirm the geometry defect directly: swipe to the second tab, then
      read `rowPitch` and the document's scroll extent. Record how many items
      are reachable before the document ends, and confirm a resize repairs both.

## 2. Refuse geometry from a grid without layout

- [x] 2.1 Give the grid view an explicit unmeasured state, distinct from a row
      pitch of zero, so "never measured" and "no window needed" stop being the
      same value.
- [x] 2.2 Make `measureGrid()` detect that it is reading a grid with no layout
      and leave the view's geometry untouched, marking it unmeasured. Decide it
      from the measurement itself, not from whether the tab is active — a second
      condition describing the same fact will drift from the paths that render
      hidden tabs.
- [x] 2.3 Make `updateGridWindow()` and `renderWindow()` refuse to act on an
      unmeasured view rather than computing a window from placeholder numbers,
      and make the refusal visible in the code as a deliberate one.
- [x] 2.4 Measure a tab's geometry when it becomes visible — after
      `commitTabState()` and before its window is next moved — so the repair the
      `resize` handler performs by accident happens without a resize.
- [x] 2.5 Walk every path that renders a grid — `beginTabTransition()`,
      `warmInactiveTab()`, `switchTab()`'s non-animated branch, the search and
      sort path, and `resize` — and confirm each reaches a measurement before it
      needs a window. A louder refusal renders nothing where it used to render
      something wrong, so a path that never measures is now a blank grid.

## 3. Stop rebuilding what is on screen

- [x] 3.1 Centre the rendered window on the viewer instead of anchoring it four
      rows above them, so upward and downward scrolling carry comparable runway.
- [x] 3.2 Re-anchor on the viewer's approach to a window edge rather than on
      every row crossed. Derive the trigger from the window's own edges so the
      threshold cannot drift out of step with the window size.
- [x] 3.3 Re-check `filterAndSortMedia()`'s skip path and `renderSignature()`
      against the new anchoring rule. A tab about to be shown from its top must
      still have its window at its top; the existing requirement covering that
      does not change.
- [x] 3.4 Verify the spacer arithmetic still holds with a centred window — the
      rows above and below must continue to sum to the full selection, and the
      spacers must still span every column.

## 4. Make a re-anchor invisible

- [x] 4.1 Track the poster paths whose images have loaded, recorded where the
      load is already observed rather than through a new listener per card.
- [x] 4.2 Have `buildCard()` emit a known-loaded poster with its `src` set and
      no placeholder, so it paints from cache without an observer round trip, a
      load event or a fade.
- [x] 4.3 Confirm the error path still works for an item whose artwork is
      missing: a poster that has never loaded must still reach its text
      placeholder, and a known-loaded poster must not be able to enter that path
      spuriously.
- [x] 4.4 Confirm the `IntersectionObserver` is still unobserved on the way out
      for the cards that do carry a placeholder, so the leak windowing exists to
      prevent is not reintroduced through the shortened path.

## 5. Tests

- [x] 5.1 Rewrite `test_scrolling_inside_the_window_does_nothing` to pin the new
      re-anchoring policy. It currently asserts `if (first === view.first)
      return;` under a name describing a guarantee that has never held on a
      phone. Do not relax it to let the change pass — it has to describe what
      the code now does, and the name has to be true.
- [x] 5.2 Add a source test pinning that geometry is not recorded from a grid
      without layout, and that an unmeasured view is distinguishable from one
      needing no window.
- [x] 5.3 Add a source test pinning that an already-loaded poster is built
      without a placeholder, so the flicker cannot return by someone
      "simplifying" `buildCard()` back to one path.
- [x] 5.4 Extend the notes at the top of `tests/test_grid_windowing.py` to say
      what this round could and could not be checked from source, keeping the
      split that file already documents honest.

## 6. Verify in a browser

- [x] 6.1 Re-run 1.1 against a seeded library and confirm a window traversal
      costs about two rebuilds rather than about sixty, in both directions.
- [x] 6.2 Drive a real scroll over CDP and sample the posters across frames, not
      at a point. A resting screenshot shows nothing here — every screenshot
      ever taken of this grid looked fine. Assert no on-screen poster returns to
      a placeholder.
- [x] 6.3 Verify the upward case explicitly. The reported symptom was scrolling
      back over already-loaded posters, and the downward case is the one that
      looks fixed first.
- [x] 6.4 Swipe to the second tab on a phone-width viewport and scroll to the
      end without rotating. Confirm the last item is reachable, and confirm the
      same on the first tab after a search or sort change followed by a swipe —
      that path zeroes the geometry today for whichever tab is swiped into.
- [x] 6.5 Confirm the tab slide and drag still behave: the window must not move
      mid-gesture, and an abandoned drag must still restore the captured offset.

## 7. Gates and docs

- [x] 7.1 `make lint` and `make test` pass.
- [x] 7.2 Check whether `CLAUDE.md`'s grid section needs the two rules this
      change establishes — that a re-anchor may not rebuild what is on screen,
      and that geometry is never recorded from a hidden grid — and update it in
      the same commit. Both are the kind of thing that is expensive to
      rediscover. If nothing else user-facing changed, say so explicitly rather
      than inventing edits.
