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

The trap `docs/handover.md` records for this item is the reason the split is
spelled out. A test asserting "the DOM is bounded" against a few-hundred-item
fixture passes whatever the code does — it was already true before windowing
existed. Such a test is worse than none, because it reports the guarantee as
held.
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
    """Or the fix reintroduces per-frame work by another route."""
    body = function_body(index, 'updateGridWindow')
    assert 'if (first === view.first) return;' in body, (
        're-rendering is no longer skipped when the window has not moved'
    )


def test_resize_recomputes_the_column_count(index):
    """`perRow` changes with width, so every row index computed for the old
    column count is wrong."""
    body = function_body(index, 'watchScrollForWindow')
    assert "addEventListener('resize'" in body, 'the grid no longer responds to a resize'
    assert 'measureGrid' in body, 'a resize no longer re-measures the geometry'
