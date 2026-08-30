"""The media grid renders a window, not the library.

WHAT THESE CAN AND CANNOT DO. The defect was behavioural — 63,248 DOM nodes,
~3fps, 6,611 cards invisible — and behaviour needs a real browser against a real
library. CI has neither: it runs `ruff`, `eslint`, `prettier` and `pytest`, with
no Chromium and no seeded container. A browser test added here would fail every
run.

So these pin the SOURCE decisions whose reversal reintroduces the defect, and
the behavioural proof lives in `tools/grid_metrics.py`, run against a library
seeded to thousands. Both halves are needed: a regex cannot prove the grid is
fast, and a measurement nobody re-runs cannot stop a regression.

The split is spelled out because of the trap this defect was found through: a
test asserting "the DOM is bounded" against a few-hundred-item fixture passes
whatever the code does — it was already true before windowing existed. A
400-item fixture showed nothing wrong here twice, which was not evidence of
health. Such a test is worse than none, because it reports the guarantee as
held.

THAT HAPPENED AGAIN, IN THIS FILE. `test_scrolling_inside_the_window_does_nothing`
pinned `if (first === view.first) return;` — a comparison of the desired ANCHOR
against the current one, which changes every row the viewer crosses, while the
window it anchors is sixty rows deep. So the guarantee in the test's own name
had never once held on a phone, and the suite stayed green over a defect that
rebuilt every card on screen 55 times per window traversal. The test was not
wrong about the code; it was wrong about what the code meant. Read what a guard
compares, not what it is called.

What this round could be checked from source: the re-anchor trigger, the
centring, the refusal to record geometry from a grid without layout, and the
fast path for an already-loaded poster. What could not: any of the numbers. A
zero-height measurement needs a browser, and the flicker needs a library large
enough to scroll a window through. Measured with `tools/browser.py` against a
seeded container at 390px, 2,000 movies and 400 shows:

    |                                                | before  | after   |
    | renderWindow calls per traversal, down         |      55 |       1 |
    | renderWindow calls per traversal, up           |      55 |       1 |
    | sampled frames showing a spinner, scrolling up | 266/269 |   0/269 |
    | TV Shows items reachable by scrolling          |  120/400|  400/400|
    | TV Shows document height                       | 21,649px| 71,776px|

THE CONTROL MATTERS MORE THAN THE AFTER. A probe that returns zero proves
nothing until it has been shown to return non-zero against the defect, so the
same probe was run against the unmodified page — that is where 266/269 comes
from, and without it "0 placeholders" is equally consistent with a probe that
never worked.
"""

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
INDEX = REPO_ROOT / 'web' / 'index.html'


def strip_comments(source: str) -> str:
    source = re.sub(r'<!--.*?-->', '', source, flags=re.S)
    source = re.sub(r'/\*.*?\*/', '', source, flags=re.S)
    return source


@pytest.fixture(scope='module')
def index() -> str:
    return strip_comments(INDEX.read_text())


@pytest.fixture(scope='module')
def raw() -> str:
    return INDEX.read_text()


def function_body(source: str, name: str) -> str:
    """The body of a top-level `function name(...)`, to its 8-space close."""
    match = re.search(
        rf'function {re.escape(name)}\([^)]*\)\s*\{{(.*?)^ {{8}}\}}',
        source,
        flags=re.S | re.M,
    )
    assert match, f'no function {name} found'
    return match.group(1)


# ---------------------------------------------------------------------------
# The bound
# ---------------------------------------------------------------------------


def test_display_media_does_not_build_an_element_per_item(index):
    """The whole defect in one line: `data.forEach` over the whole library.

    Every item became a node, so the browser's per-frame cost scaled with how
    much media the user owns.
    """
    body = function_body(index, 'displayMedia')
    for banned in ('data.forEach', 'data.map(', 'for (const item of data'):
        assert banned not in body, (
            f'displayMedia iterates the whole selection ({banned}); the grid is '
            f'supposed to render a window near the viewport, not the library'
        )


def test_the_window_is_a_bounded_constant(index):
    """A window sized from the data is not a window."""
    match = re.search(r'const GRID_WINDOW_ITEMS = (\d+);', index)
    assert match, 'GRID_WINDOW_ITEMS is gone; nothing bounds the rendered count'
    size = int(match.group(1))
    # 60fps held at 300 cards and 29.9fps at 800 when this was measured. A
    # window at or above the ceiling is not a bound, it is a slower failure.
    assert 0 < size <= 300, (
        f'GRID_WINDOW_ITEMS is {size}; the measured ceiling was 300 cards at '
        f'60fps and 800 at 29.9fps, so this no longer bounds anything'
    )


def test_the_window_is_rendered_through_a_fragment(index):
    """One insertion, not one per card."""
    body = function_body(index, 'renderWindow')
    assert 'createDocumentFragment' in body, (
        'the window is appended element by element again; that was 7,000 '
        'separate insertions at library scale'
    )


def test_spacers_span_every_column(index):
    """`auto-fill` places a spacer as an ordinary cell without this.

    It then consumes a grid position, every following card shifts one column,
    and the row arithmetic is wrong in a way that reads as an off-by-one in the
    window rather than as a layout bug.
    """
    body = function_body(index, 'makeSpacer')
    assert "gridColumn = '1 / -1'" in body, (
        'the spacer no longer spans the row; it will be laid out as a card'
    )


def test_the_grid_is_measured_not_assumed(index):
    """`auto-fill` decides the column count from the width available.

    A count derived from a breakpoint is wrong at every width the breakpoint did
    not anticipate — the same mistake as the hardcoded 280px backdrop height
    this project already paid for.
    """
    body = function_body(index, 'measureGrid')
    assert 'gridTemplateColumns' in body, (
        'the column count is no longer read from the rendered grid'
    )
    assert 'paddingTop' in body, (
        'the grid is padded; measuring rows from its border box puts every row '
        'boundary a fifth of a row out'
    )


# ---------------------------------------------------------------------------
# Wiring the grid once
# ---------------------------------------------------------------------------


def test_cards_do_not_get_their_own_click_listener(index):
    """7,000 closures, and a recycled card that could open the wrong item."""
    body = function_body(index, 'buildCard')
    assert 'addEventListener' not in body, (
        'a per-card listener is back; the click belongs on the grid, delegated, '
        'or a recycled element carries a handler for the item it used to hold'
    )


def test_the_grid_delegates_its_clicks(index):
    body = function_body(index, 'gridView')
    assert "grid.addEventListener('click'" in body, (
        'the grid no longer has a delegated click handler, so nothing opens'
    )


def test_cards_leaving_the_window_are_unobserved(index):
    """Otherwise the observer accumulates targets no longer in the document —
    the leak windowing exists to prevent, reintroduced through the back door."""
    body = function_body(index, 'renderWindow')
    assert 'imageObserver.unobserve' in body, 'cards are no longer unobserved when the window moves'
    assert 'imageObserver.observe' in body, (
        'the new window is never observed, so posters never load'
    )


# ---------------------------------------------------------------------------
# The entrance animation
# ---------------------------------------------------------------------------


def test_the_entrance_delay_is_capped(index):
    """`index * 0.03s` over the whole library made the 7,000th card wait 209.97
    seconds; 6,611 of 7,000 cards were still `opacity: 0` after 25 seconds.

    The grid was not slow to animate — most of it was invisible.
    """
    match = re.search(r'const GRID_STAGGER_CAP = ([\d.]+);', index)
    assert match, 'GRID_STAGGER_CAP is gone; nothing bounds the entrance delay'
    cap = float(match.group(1))
    assert 0 < cap <= 1.0, (
        f'the entrance cap is {cap}s; a delay beyond about a second is not a '
        f'softer arrival, it is a missing item'
    )

    body = function_body(index, 'buildCard')
    assert 'Math.min(' in body and 'GRID_STAGGER_CAP' in body, (
        'the delay is no longer clamped to the cap'
    )


def test_the_delay_is_not_computed_from_the_library_index(index):
    """The defect precisely: a per-item delay multiplied by a number the
    application does not control."""
    body = function_body(index, 'buildCard')
    assert not re.search(r'index\s*\*\s*0?\.\d+', body), (
        "the entrance delay is computed from the item's index in the library "
        'again; that is what produced a 209.97s delay'
    )


def test_no_timer_per_card(index):
    """7,000 `setTimeout`s to flip opacity. One frame is all the browser needs
    to have taken the starting value."""
    body = function_body(index, 'buildCard')
    assert 'setTimeout' not in body, 'a timer per card is back'


# ---------------------------------------------------------------------------
# Scrolling
# ---------------------------------------------------------------------------


def test_scroll_updates_are_coalesced_to_a_frame(index):
    """A `scroll` listener that recomputes per event does layout work at the
    scroll's own frequency."""
    body = function_body(index, 'watchScrollForWindow')
    assert 'requestAnimationFrame' in body, 'scroll updates are no longer coalesced'
    assert 'passive: true' in body, 'the scroll listener is no longer passive'


def test_scrolling_inside_the_window_does_nothing(index):
    """The window moves when the viewer reaches its EDGE, not every row.

    THIS TEST'S PREVIOUS FORM ASSERTED A GUARANTEE THE CODE NEVER PROVIDED. It
    pinned `if (first === view.first) return;` under this name, and that guard
    compares the desired ANCHOR against the current one. The anchor is derived
    from the viewer's row, so it changes every single row they cross — while the
    window it anchors is sixty rows deep at two columns. So "scrolling inside
    the window" rebuilt the entire window, including every card on screen, and
    the test reported the opposite.

    Measured at 2,000 movies on a 390px viewport: 55 rebuilds per window
    traversal in each direction, against 1 after this changed. Each of those
    rebuilds returned every visible poster to a loading placeholder, which is
    what was reported — and it was reported while scrolling BACK UP over
    posters that had finished loading seconds earlier.

    A test derived from a spec inherits the spec's blind spot. This one did, and
    it is the reason the defect had a green suite sitting on top of it.
    """
    body = function_body(index, 'updateGridWindow')
    assert 'windowNeedsMove(view)' in body, (
        'the window no longer moves on the viewer reaching its edge; if this is '
        'back to comparing the desired anchor against the current one, it '
        'rebuilds every card on screen once per row scrolled'
    )
    assert re.search(r'if\s*\(!windowNeedsMove\(view\)\)\s*return', body), (
        're-rendering is no longer skipped while the viewer is inside the window'
    )


def test_the_window_is_centred_on_the_viewer(index):
    """Runway in both directions, or scrolling up has none.

    The window used to start `GRID_OVERSCAN_ROWS` above the viewer and run its
    full depth downward — four rows above against fifty-six below. Upward
    scrolling therefore had four rows of margin, and upward scrolling is the
    direction most likely to be crossing artwork the viewer has already loaded.
    """
    body = function_body(index, 'desiredFirstIndex')
    assert 'viewportRows(view)' in body, (
        'the window no longer accounts for what the viewport shows, so it '
        'cannot be centred on the viewer'
    )
    assert 'windowRows(view)' in body, 'the window size is no longer read here'
    assert 'data.length - 1' not in body, (
        'the anchor is clamped to the last ITEM again; that allows a first '
        'index of length - 1, which renders exactly one card at the foot of a '
        'large library'
    )


def test_the_window_does_not_chase_an_end_of_the_library(index):
    """Proximity to an end is not a reason to move.

    There is nothing further to render in that direction, so treating it as a
    reason re-renders on every row at the top and bottom of the grid — the
    defect this replaced, reached from its two edges.
    """
    body = function_body(index, 'windowNeedsMove')
    assert 'totalRows(view)' in body, (
        'windowNeedsMove() no longer knows where the library ends, so it will '
        'ask for a window past it once per row'
    )
    assert 'firstRow > 0' in body, (
        'the top of the library is no longer excluded from the edge trigger'
    )


def test_geometry_is_not_recorded_from_a_grid_without_layout(index):
    """A hidden grid answers with zeros, not with an error.

    An element inside a `display: none` ancestor has no boxes, so its card
    measures 0 tall and `getComputedStyle` returns the COMPUTED track list
    rather than the used one — on a desktop `repeat(auto-fill, minmax(200px,
    1fr))` splits into three fragments and yields a column count of 3 that no
    width ever produced. Both look like measurements.

    The incoming tab is rendered while hidden on purpose, so this is the
    ordinary path, not an exceptional one. Measured before this existed: a phone
    swiping to a 400-show tab reached item 120 of 400, on a document 21,649px
    tall against the 71,926px it should have been.
    """
    body = function_body(index, 'measureGrid')
    assert 'view.measured = false' in body, (
        'measureGrid() no longer records that it could not measure; a failed '
        'read will be stored as a row pitch of zero and believed'
    )
    assert re.search(r'if\s*\(cardHeight\s*<=\s*0\)', body), (
        'measureGrid() no longer detects a grid that has not been laid out'
    )
    # The refusal must come before anything is written, or a hidden grid still
    # overwrites a good column count with a parsed-but-meaningless one.
    assert body.index('cardHeight <= 0') < body.index('view.perRow ='), (
        'the geometry is written before the measurement is checked, so a hidden '
        'grid still overwrites it'
    )


def test_an_unmeasured_grid_is_distinguishable_from_one_needing_no_window(index):
    """`rowPitch = 0` meant both, which is why this failed silently.

    A tab that was never measurable presented as a healthy tab that simply ended
    early — the same shape as a misconfigured install that looks like a working
    one, which this project refuses everywhere else.
    """
    view = function_body(index, 'gridView')
    assert 'measured: false' in view, (
        'the grid view no longer carries an explicit measured flag, so an '
        'unmeasured grid is back to being indistinguishable from a measured one '
        'whose rows have no height'
    )
    body = function_body(index, 'updateGridWindow')
    assert '!view.measured' in body, (
        'updateGridWindow() no longer refuses an unmeasured view; it will '
        'compute a window from placeholder geometry'
    )


def test_a_tab_is_measured_when_it_lands(index):
    """The swipe is the only way into the other tab at phone widths.

    `.header-content .tabs` is `display: none` below 768px, so a tab reached by
    the gesture that was never measured is a tab that is never measured at all.
    A rotation repaired it, because `resize` re-measures — which is not a fix.
    """
    body = function_body(index, 'endTabTransition')
    assert 'measureGrid(' in body, (
        'the tab that just landed is no longer measured, so a tab rendered '
        'while hidden keeps placeholder geometry until something resizes'
    )
    assert 'renderWindow(' in body, (
        'the landed tab is measured but its window is never rebuilt from the '
        'real geometry, so its spacers stay collapsed'
    )


def test_an_already_loaded_poster_is_built_as_loaded(index):
    """A rebuilt card starts with no `src`, so its poster blinks.

    This is the flicker: moving the window rebuilds every card it holds, and a
    poster the viewer is looking at returns to its placeholder and fades in
    again. Measured scrolling back up over loaded posters: 266 of 269 sampled
    frames showed a spinner, at worst on all 8 visible cards. After: 0 of 269.
    """
    body = function_body(index, 'buildCard')
    assert 'loadedPosters.has(posterPath)' in body, (
        'buildCard() no longer takes the fast path for a poster that has '
        'already loaded, so moving the window blinks every card on screen'
    )
    assert 'poster loaded' in body, (
        'the fast path no longer marks the poster loaded, so it will fade in '
        'from transparent even with its src set'
    )
    # The lazy path must survive: a poster that has never loaded still needs its
    # placeholder and its error handling.
    assert 'poster-placeholder' in body, (
        'the lazy path lost its placeholder; a poster that has never loaded now '
        'shows nothing while it loads'
    )


def test_resize_recomputes_the_column_count(index):
    """`perRow` changes with width, so every row index computed for the old
    column count is wrong."""
    body = function_body(index, 'watchScrollForWindow')
    assert "addEventListener('resize'" in body, 'the grid no longer responds to a resize'
    assert 'measureGrid' in body, 'a resize no longer re-measures the geometry'
