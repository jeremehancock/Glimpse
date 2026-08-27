## 1. Stop the label crossing

- [x] 1.1 In `web/index.html`, add `color: var(--light-text)` to the `.tab` base
      rule (`:295`), so the resting label colour is declared where the selected
      one is decided rather than inherited.
- [x] 1.2 Replace `transition: all var(--transition-speed)` in `.tab` with
      `transition: background-color var(--transition-speed), box-shadow
      var(--transition-speed)` — `box-shadow` named because `.tab.active` adds
      `var(--shadow-sm)`, `color` omitted on purpose.
- [x] 1.3 Replace `transition: all var(--transition-speed)` in the
      `.sort-button, .genre-button` rule (`:406`) with
      `transition: background-color var(--transition-speed)`. Those rules
      already declare `color: var(--light-text)`; leave it.
- [x] 1.4 Add a short comment above each changed transition saying why `color`
      is absent — that interpolating a label between the neutral and accent
      fills passes it through a value with no contrast, and that this is the
      whole reason the rules do not use `all`.
- [x] 1.5 Confirm nothing else changed: `.genre-badge` (`:1668`),
      `.scroll-to-top` (`:945`), `.roulette-close-btn` (`:5240`),
      `.genre-item` (`:483`), `.tabs` (`:292`), `.search-input` (`:344`) and
      `.server-toggle-button` (`:1676`) are untouched.

## 2. Pin the decision

- [x] 2.1 Create `tests/test_pill_contrast.py` with a module docstring saying
      what a browser would catch here and CI cannot, matching the voice of
      `tests/test_cache_policy.py`.
- [x] 2.2 Extract the three base rule bodies by selector from
      `web/index.html`, and fail loudly if a selector is not found — a regex
      that silently matches nothing is a test that cannot fail.
- [x] 2.3 Assert each base rule declares a `color`.
- [x] 2.4 Assert each base rule's `transition` names its properties: no `all`,
      and no `color` in the list.
- [x] 2.5 Assert the always-accent controls are NOT covered by the test, by
      keeping the selector list explicit rather than scanning for
      `background-color: var(--primary-color)`.
- [x] 2.6 Run `make test` and confirm the new test passes; temporarily restore
      `transition: all` on `.tab` and confirm it fails, then revert. A test that
      has never failed has not been shown to work.

## 3. Verify by eye

Group 5 supersedes tasks 1.2–1.4 and 2.4; these remain as authored so the
record of what was tried is not rewritten. Verify against group 5.

- [ ] 3.1 Serve the app locally and, with DevTools animation playback slowed to
      10–25%, watch a tab **selection** on the Plex palette. The label must be
      black from the first frame, on an already-accent fill.
- [ ] 3.2 Watch a tab **deselection** at the same speed. This is the reported
      direction: the label must be white from the first frame and must never
      sit light on a still-yellow pill.
- [ ] 3.3 Sample the computed `color` across several frames of the change rather
      than at one point — a single sample passes for a transition that has not
      started moving yet.
- [ ] 3.4 Repeat 3.1 and 3.2 for a sort pill and a genre pill.
- [ ] 3.5 Check the Jellyfin and Emby palettes by switching `data-server` on
      `<html>` in DevTools; the crossing must be clean in each.
- [ ] 3.6 Confirm the pill's fill and label step on the **same frame** in both
      directions. Sample the computed `color` and `background-color` together,
      not one of them.

## 4. Gates and docs

- [x] 4.1 Run `make lint` and `make fmt`; both must pass.
- [x] 4.2 Run `make test`; it must pass.
- [x] 4.3 Decide whether `README.md`, `docs/` or `CLAUDE.md` went stale. Nothing
      user-facing or configurable changed, so the expected answer is no — if so,
      say that explicitly in the commit rather than inventing edits. `CLAUDE.md`
      is the one to weigh: it records this class of CSS trap, and a rule about
      labels crossing between fills may belong in its conventions list.
- [x] 4.4 No `Dockerfile`, `config/` or entrypoint change, so `make docker-smoke`
      is not required. Confirm that is still true of the final diff.

## 5. Correction: the fill and the label are one pair

The first implementation eased the fill and switched only the label. It reached
`:dev` and a user reported it: deselecting a tab put a fully white label on a
fully yellow pill and held it while the yellow drained — worse than the defect
it replaced. Contrast is a relation between two properties, so moving one alone
only reflects the bad window. See the correction in `design.md`.

- [x] 5.1 Remove the `transition` declaration from `.tab` entirely. With both
      `color` and `background-color` barred, `box-shadow` alone would ease a
      shadow in after the fill it belongs to had already snapped.
- [x] 5.2 Remove the `transition` declaration from `.sort-button,
      .genre-button` for the same reason.
- [x] 5.3 Rewrite the comment above `.tab` to name all three orderings that were
      shipped and why only "both together" has no bad frame — two of the three
      look like fixes for the third, which is how the second one got written.
- [x] 5.4 Widen the test: neither `color` nor `background-color` may be
      transitioned, directly or by `all`. A transition over anything else stays
      permitted, so the rule constrains the pair rather than banning motion.
- [x] 5.5 Accept that the hover tint snaps. Hover and selection share one
      `background-color` and CSS cannot distinguish `.tab:not(.active)` reached
      by hovering from `.tab:not(.active)` reached by deselection.
- [x] 5.6 Mutation-test all three orderings — both eased, fill eased, label
      eased — plus a `box-shadow`-only transition that must still PASS. The
      previous mutation pass only drove the ordering that had been reported.
- [x] 5.7 Reconcile `proposal.md`, `design.md`, `specs/visual-design/spec.md`
      and `CLAUDE.md` with the corrected rule. The spec is what got this wrong;
      the test inherited its blind spot and passed the broken build.
