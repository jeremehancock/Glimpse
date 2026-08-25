## 1. Establish the measurement harness first

- [x] 1.1 Seed a large library and run a container against it:
      `python3 tools/seed_library.py --out <dir> --movies 7000 --shows 500 --posters 60`,
      then copy the snapshots in **after** the container is up — the entrypoint
      deletes them on a failed fetch.
- [x] 1.2 Record the BEFORE numbers at 390×844 with `tools/browser.py`: DOM node
      count, `.media-item` count, document `scrollHeight`, idle frame interval,
      forced-layout cost of the scroll lock, and how many cards are still
      `opacity: 0` after load. These are the numbers the change is judged
      against; capture them before touching code.
- [x] 1.3 Repeat at 1280×900. The grid's column count differs, and one width
      proves nothing.

## 2. Bound the rendered window

- [x] 2.1 Read the grid's geometry from the rendered DOM — card width, card
      height, row gap, and `perRow` from the grid's width. Never derive `perRow`
      from a breakpoint; `auto-fill` decides it from the available width.
- [x] 2.2 Add the window constant with the measured table beside it in a comment
      (60fps at 300 cards, 29.9fps at 800, 6 cards on screen at 390px), so the
      number has its justification attached rather than looking arbitrary.
- [x] 2.3 In `displayMedia()`, render only the window's slice into a
      `DocumentFragment` and insert it in one operation.
- [x] 2.4 Add the leading and trailing spacers, each `grid-column: 1 / -1` and
      sized `rows * rowHeight`. Comment that without the column span `auto-fill`
      places them as ordinary cells, which shifts every following card into the
      wrong column and reads as an off-by-one in the window rather than a layout
      bug.
- [x] 2.5 Recompute the window on scroll, coalesced with
      `requestAnimationFrame`, and **re-render only when the window actually
      moves** — scrolling inside the current window must do no work.
- [x] 2.6 Recompute geometry and re-render on resize, since `perRow` changes
      with width.

## 3. Wire the grid once instead of per card

- [x] 3.1 Replace the per-card `click` listener with one delegated listener on
      the grid, resolving the item through `closest('.media-item')` and its
      `dataset.id`.
- [x] 3.2 `unobserve` cards as they leave the window, so `imageObserver` cannot
      accumulate targets that are no longer in the document.
- [x] 3.3 Confirm a recycled card cannot carry a stale handler or a stale
      `data-src`.

## 4. Fix the entrance animation

- [x] 4.1 Compute the entrance delay from the item's index **within the rendered
      window**, capped, instead of `index * 0.03s` over the whole library.
- [x] 4.2 Remove the per-card `setTimeout` that flips opacity; the reveal
      belongs to the fragment insertion.
- [x] 4.3 Verify no rendered card remains at `opacity: 0` once its animation has
      run — this is the assertion that would have caught 6,611 invisible cards.

## 5. Keep everything that feeds the grid working

- [x] 5.1 Search: typing narrows the selection and the window follows the
      filtered array, including down to zero results and back.
- [x] 5.2 Genre filter and sort: each re-renders from the top of the new
      selection.
- [x] 5.3 Movies/TV tabs, including the horizontal swipe between them — this
      change must not break the existing swipe.
- [x] 5.4 Scroll-to-top, and the overlay scroll lock's restore: open an overlay
      mid-library, dismiss it, and confirm the page returns to the same row.
- [x] 5.5 The detail overlay still opens for an item rendered after the grid has
      been scrolled and re-windowed.

## 6. Pin it with tests

- [x] 6.1 Add a test asserting the rendered element count stays bounded for a
      library far larger than the bound. **It must be run against a fixture big
      enough to fail the old code** — a small fixture makes this test incapable
      of failing, which is the trap `docs/handover.md` records for this item.
- [x] 6.2 Add a test asserting the last item of a large selection is reachable —
      the bound must not become a limit on what can be browsed.
- [x] 6.3 Add a test asserting no entrance delay exceeds the cap regardless of
      library size.
- [x] 6.4 Verify each new test fails when its defect is reintroduced, rather
      than assuming it would.

## 7. Verify in a real browser at both widths

- [x] 7.1 Re-measure everything from 1.2 and 1.3 and put the before/after in the
      PR: node count, idle frame interval, scroll-lock cost, invisible cards.
- [x] 7.2 Hold a scroll position across a window change and confirm the
      on-screen content does not move.
- [x] 7.3 Scroll continuously to the end of the 7,000 item library and confirm
      the last item renders and the scrollbar does not jump.
- [x] 7.4 Open a tray at 390×844 and confirm the open now reads as motion rather
      than a jump — the symptom punch-list item 2 was reported as.
- [x] 7.5 Decide the open question on `content-visibility: auto`: measure with
      and without at the final window size, and keep it only if it still helps.

## 8. Gates and docs

- [x] 8.1 Run `make fmt`, then `make lint` and `make test`; both must pass.
      Note `make lint` needs Node 18+ — the default Node 16 on this machine
      fails with `structuredClone is not defined`.
- [x] 8.2 No `Dockerfile`, `config/` or entrypoint change is expected, so
      `make docker-smoke` should not be required — confirm before skipping it.
- [x] 8.3 Check whether `README.md` should say anything about large libraries,
      and whether `CLAUDE.md` should record that the grid is windowed and why
      per-card listeners and observers are not acceptable at this scale. Fix in
      the same commit, or state explicitly that nothing documented changed.
- [x] 8.4 Update `docs/handover.md`: punch-list item 2 is diagnosed and its
      cause is not the trays. Note whether item 5 is now unblocked.
