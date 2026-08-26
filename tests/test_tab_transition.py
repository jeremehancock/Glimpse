"""The tab transition slides, and cannot leave a tab stranded.

WHAT THESE CAN AND CANNOT DO. The change is an animation, and CI has no browser:
`make test` runs `pytest` with no Chromium and no seeded library. A frame-rate
assertion added here would be meaningless at best and red on every run at worst.
Worse, this is the one feature where the usual headless fallback is actively
misleading — `chromium --headless --virtual-time-budget --dump-dom` never fires
`requestAnimationFrame`, so a driver using it cannot observe a transition at all
and reports a stationary page as a passing one.

So these pin the SOURCE decisions whose reversal reintroduces a defect that was
actually hit while building this, and the behavioural proof is a real browser
driven over CDP through `tools/browser.py` against a library seeded to
thousands. Both halves are needed. Measured there, recorded in
`openspec/changes/animate-tab-transition/design.md`:

    slide steady state          16.7ms/frame (59.9fps), 0 dropped on a repeat switch
    transform on a 1.2M-px box  free -- the layer size is not the axis that matters
    forced layout during freeze 77.7ms, on the animation's opening frame
    card render on frame one    183.4ms of a 280ms slide, before it was separated

A note on what a browser check must actually assert, because the first version
of this one got it wrong: `transform !== 'none'` is satisfied by the START value
of the transition, so it passes just as well for a slide that never moves. It
did. Sample the path across frames, not a point.
"""

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
INDEX = REPO_ROOT / 'web' / 'index.html'
TOKENS = REPO_ROOT / 'web' / 'assets' / 'tokens.css'
OVERLAYS_JS = REPO_ROOT / 'web' / 'assets' / 'overlays.js'


def strip_comments(source: str) -> str:
    """Drop HTML and block comments.

    The comments here name the defects and their numbers, so asserting against
    prose would let a test pass on its own explanation.
    """
    source = re.sub(r'<!--.*?-->', '', source, flags=re.S)
    source = re.sub(r'/\*.*?\*/', '', source, flags=re.S)
    return source


@pytest.fixture(scope='module')
def index() -> str:
    return strip_comments(INDEX.read_text())


@pytest.fixture(scope='module')
def tokens() -> str:
    return strip_comments(TOKENS.read_text())


@pytest.fixture(scope='module')
def overlays_js() -> str:
    return strip_comments(OVERLAYS_JS.read_text())


def function_body(source: str, name: str) -> str:
    """The body of a top-level `function name(...)`, to its 8-space close."""
    match = re.search(
        rf'function {re.escape(name)}\([^)]*\)\s*\{{(.*?)^ {{8}}\}}',
        source,
        flags=re.S | re.M,
    )
    assert match, f'no function {name} found'
    return match.group(1)


def css_rule(source: str, selector: str) -> str:
    """The declaration block of a single CSS rule, by exact selector."""
    match = re.search(
        rf'^\s*{re.escape(selector)}\s*\{{(.*?)\}}',
        source,
        flags=re.S | re.M,
    )
    assert match, f'no rule found for {selector!r}'
    return match.group(1)


# ---------------------------------------------------------------------------
# The freeze
# ---------------------------------------------------------------------------


def test_the_freeze_reads_no_geometry(index):
    """Taking the outgoing tab out of flow is free; measuring it afterwards is not.

    Setting the frozen styles costs 0.2-0.4ms. A single getBoundingClientRect()
    after doing so costs 77.7ms -- a forced synchronous layout landing on the
    animation's opening frame. The transform itself is free, so the hitch reads
    as "the slide is janky" and the transform takes the blame.
    """
    body = function_body(index, 'beginTabTransition') + function_body(index, 'trackTabDrag')
    for probe in (
        'getBoundingClientRect',
        'offsetHeight',
        'offsetTop',
        'offsetWidth',
        'getComputedStyle',
    ):
        assert probe not in body, (
            f'the setup or the tracker calls {probe} -- a forced layout '
            f'between the freeze and the transform costs ~78ms on the first '
            f'frame of every swipe, and the tracker would pay it every frame'
        )


def test_the_scroll_position_is_read_before_anything_is_written(index):
    """The offset must be the pre-freeze position.

    Reading it after the tab is out of flow reads the collapsed document, and
    the frozen tab renders somewhere the viewer never was.
    """
    body = function_body(index, 'beginTabTransition')
    read = body.index('window.scrollY')
    for write in ('applyTabState(', 'classList.add', 'filterAndSortMedia('):
        assert read < body.index(write), (
            f'window.scrollY is read after {write} -- it must be captured before '
            f'anything is written'
        )


# ---------------------------------------------------------------------------
# Sequencing
# ---------------------------------------------------------------------------


def test_the_incoming_tab_is_rendered_before_it_is_shown(index):
    """A tab that has never been active has never been rendered.

    It carries an empty grid and a live .loading spinner from first paint --
    displayMedia() retires that spinner only for the tab it renders. Revealing
    the incoming tab before its render lands therefore does not show blank rows
    on the first switch; it shows a spinner.
    """
    body = function_body(index, 'beginTabTransition')
    render = body.index('filterAndSortMedia(')
    reveal = body.index("classList.add('tab-entering'")
    assert render < reveal, (
        'the incoming tab is revealed before it is rendered -- the first switch '
        'to a tab would show its loading spinner'
    )


def test_the_slide_starts_a_frame_after_the_render(index):
    """A rAF callback runs BEFORE that frame's layout and paint.

    Starting the transform in the first callback puts the cost of laying out a
    fresh 120-card grid on the animation's opening frame: measured at 183.4ms of
    a 280ms slide, with every frame after it a clean 16.7ms. The slide was never
    slow -- two thirds of it was over before it became visible.
    """
    body = function_body(index, 'switchTabAnimated')
    tail = body[body.index('requestAnimationFrame') :]
    slide = tail.index("classList.add('tab-sliding')")
    nested = len(re.findall(r'requestAnimationFrame', tail[:slide]))
    assert nested >= 2, (
        'the slide starts one frame after the render, so the layout and paint '
        'of the incoming grid land on the first frame of the animation'
    )


def test_a_tab_arriving_on_a_slide_does_not_also_stagger_its_cards(index):
    """The entrance fade softens a grid appearing IN PLACE.

    A tab crossing the viewport as one object is already a soft arrival, and the
    stagger was the most expensive thing on the opening frame -- 120 inline
    transitions and 120 rAF closures, doubled on a tab's first render because an
    unmeasured row pitch makes displayMedia() render twice.
    """
    body = function_body(index, 'beginTabTransition')
    match = re.search(r'filterAndSortMedia\(([^)]*)\)', body)
    assert match, 'beginTabTransition() does not render the incoming tab'
    assert 'false' in match.group(1), (
        'the sliding tab still animates its cards in; that is redundant under a '
        'slide and is the largest cost on the opening frame'
    )


# ---------------------------------------------------------------------------
# The axis
# ---------------------------------------------------------------------------


def test_the_transition_translates_horizontally_only(index):
    """firstVisibleRow() derives the grid's window from getBoundingClientRect().top.

    A translateY moves that top while the transition runs, so a scroll mid-flight
    re-windows the grid against a position the viewer never occupied. It presents
    as an off-by-one in the window, not as a layout bug.

    The lift's scale is the one exception and it is checked separately below --
    it moves that top exactly as a translateY would, and is admissible only
    because the windowing refuses outright for the gesture's duration.
    """
    rule = css_rule(index, '.content.tab-leaving,\n        .content.tab-entering')
    assert 'translateX(' in rule, 'the tabs do not translate horizontally'
    for banned in ('translateY(', 'translate3d(', 'rotate(', 'skew('):
        assert banned not in rule, (
            f'the tab transform uses {banned} -- a vertical transform corrupts '
            f'the grid window arithmetic mid-transition'
        )


def test_the_lift_is_paired_with_a_windowing_refusal(index):
    """The scale and the guard arrive together or neither does.

    A scale moves every card's getBoundingClientRect().top, which is
    firstVisibleRow()'s only input. It is admissible ONLY because
    updateGridWindow() refuses while a gesture is live.

    This asserts the pairing rather than either half, because either half alone
    is the defect: a scale without the guard re-windows the grid against a
    position the viewer never occupied, and this repo has already shipped two
    conditions meant to describe one capability that drifted apart.
    """
    rule = css_rule(index, '.content.tab-leaving,\n        .content.tab-entering')
    if 'scale(' not in rule:
        return  # No lift, no guard needed.

    body = function_body(index, 'updateGridWindow')
    assert re.search(r'if\s*\(tabGestureActive\(\)\)\s*return', body), (
        'the tabs scale during a gesture but updateGridWindow() does not refuse '
        'while one is live -- the window would be computed against a scaled rect'
    )
    assert body.index('tabGestureActive()') < body.index('rowPitch'), (
        'the windowing guard runs after the geometry checks rather than first'
    )


def test_layer_promotion_is_declared_on_the_setup_state_not_the_slide(index):
    """will-change alongside the transform pays for promotion on the worst frame.

    Declared on the frozen and parked states instead, the layer is promoted
    during the setup frame. Measured at 83ms of a 280ms slide when it was not.
    """
    setup = css_rule(index, '.content.tab-leaving,\n        .content.tab-entering')
    assert 'will-change' in setup, (
        'the frozen and parked states do not promote their layer during setup'
    )
    assert 'will-change' not in css_rule(index, '.content.tab-sliding'), (
        'will-change is declared on the sliding state, so the layer is promoted '
        'on the first frame of the transform -- the one that can least afford it'
    )


# ---------------------------------------------------------------------------
# Gating
# ---------------------------------------------------------------------------


def test_the_animation_is_gated_with_the_gesture_not_a_breakpoint(index):
    """Two conditions describing one capability drift.

    This project has already shipped the rule hiding a page control and the rule
    showing the overlay trigger that replaced it as separate media queries; they
    reached 992px and 768px independently and left every width between with
    neither. `isMobile` is the gesture's own flag, borrowed on purpose.
    """
    body = function_body(index, 'shouldAnimateTabs')
    assert 'isMobile' in body, (
        'shouldAnimateTabs() does not read isMobile -- the animation and the '
        'gesture that triggers it must be gated by one condition'
    )
    assert 'matchMedia' not in body and 'innerWidth' not in body, (
        'shouldAnimateTabs() re-derives a breakpoint instead of reusing the '
        'condition the gesture uses; the two will drift'
    )


def test_the_pointer_path_does_not_animate(index):
    """Desktop tab clicks stay an instant cut.

    The click handler passes no direction, and switchTab() requires one to take
    the animated path -- so the gate is structural rather than a second check
    that could be forgotten.
    """
    body = function_body(index, 'switchTab')
    assert re.search(r'shouldAnimateTabs\(\)\s*&&\s*direction', body), (
        'switchTab() does not require a direction for the animated path'
    )


# ---------------------------------------------------------------------------
# Teardown
# ---------------------------------------------------------------------------


def test_teardown_clears_everything_the_freeze_sets(index):
    """An animation is presentation; the state it leaves behind is correctness.

    A tab left pinned, transformed, or with the page's overflow contained is a
    broken app, not a cosmetic problem.
    """
    body = function_body(index, 'endTabTransition')
    for cleared in (
        'tab-leaving',
        'tab-entering',
        'tab-sliding',
        '--tab-shift',
        'top',
        'tab-transitioning',
    ):
        assert cleared in body, (
            f'endTabTransition() does not clear {cleared!r} -- an interrupted '
            f'transition would strand it'
        )


def test_teardown_does_not_depend_on_transitionend_alone(index):
    """A transitionend that never arrives must not strand a tab.

    Reduced motion collapses the duration app-wide rather than removing the
    transition, so the event still fires there -- this covers the cases where it
    does not, including a second swipe landing mid-flight.
    """
    assert 'setTimeout(endTabTransition' in function_body(index, 'commitTabState'), (
        'the teardown has no fallback timer; a dropped transitionend leaves a '
        'tab pinned and transformed'
    )
    setup = function_body(index, 'beginTabTransition')
    assert setup.index('endTabTransition()') < setup.index('window.scrollY'), (
        'beginTabTransition() does not resolve a transition already in flight '
        'before starting another'
    )


def test_teardown_is_idempotent(index):
    """It is called by the transition ending AND by a new one starting."""
    body = function_body(index, 'endTabTransition')
    assert re.search(r'if\s*\(!tabTransition\)\s*return', body), (
        'endTabTransition() has no guard, so the second call throws or double-clears'
    )


# ---------------------------------------------------------------------------
# The dead rule, and the numbers that must live in one place
# ---------------------------------------------------------------------------


def test_content_declares_no_transition_that_cannot_run(index):
    """`.content` used to declare a fade that had never once run.

    display:none -> display:block does not transition, so the tabs cut instantly
    while the stylesheet described an animation. A rule that appears to animate
    the tabs and does not is where the next live one hides.
    """
    rule = css_rule(index, '.content')
    assert 'transition' not in rule, (
        '.content declares a transition again -- a display swap cannot run one'
    )
    for dead in ('opacity', 'transform'):
        assert dead not in rule, f'.content declares {dead}, which a display swap cannot animate'


def test_the_duration_lives_in_tokens_and_is_read_back(index, tokens):
    """Chrome never restates a number the token file owns."""
    assert '--dur-tab:' in tokens, 'tokens.css does not declare --dur-tab'
    assert 'var(--dur-tab)' in index, 'the transition does not read its duration from the token'
    assert re.search(r"readToken\('--dur-tab'", index), (
        'the safety timer restates the duration instead of reading the token'
    )


def test_the_transition_scrolls_instantly(index, overlays_js):
    """scroll-behavior: smooth is set on the document.

    The default animates for about a second underneath a 280ms transition and is
    still travelling when it ends, so the page drifts to the top afterwards.
    Measured before this was fixed: still at 3000px two frames in, settling at
    12px rather than 0.
    """
    body = function_body(index, 'beginTabTransition')
    assert re.search(r"scrollPageTo\(0,\s*'instant'\)", body), (
        'the transition does not scroll instantly; a smooth scroll outlives the '
        'slide and the page drifts to the top after it ends'
    )
    assert re.search(r'function scrollPageTo\(y, behavior = ', overlays_js), (
        'scrollPageTo() does not accept a behavior, so every caller is smooth'
    )


# ---------------------------------------------------------------------------
# The drag
#
# The gesture IS the transition now. These pin the decisions whose reversal
# reintroduces a defect that was actually hit building it -- and, as above,
# they pin SOURCE decisions. A drag cannot be observed without a browser, and
# the behavioural half is `tools/browser.py` driving Chromium over CDP with
# `Input.dispatchTouchEvent`, sampling the transform across the touch path.
#
# What that browser check must assert, because the obvious version does not:
# a drag's proof is that the transform CORRESPONDS to the finger, not that it
# changed. A handler setting a constant offset on the first move passes any
# single-point check ever written -- and `transform !== 'none'` passes for a
# slide that never moves, which it did here once already.
# ---------------------------------------------------------------------------


def test_the_axis_locks_before_the_gesture_is_claimed(index):
    """preventDefault() has to be available on the first move that crosses it.

    The old handler claimed the gesture only after 100px of horizontal travel.
    That is far too late to drive a drag -- nothing can move until the gesture is
    claimed -- and on iOS a touch whose early moves went uncancelled has already
    been given to the scroller, where later preventDefault() calls are ignored.
    """
    assert 'TAB_AXIS_LOCK_PX' in index, 'there is no axis-lock distance'
    lock = re.search(r'const TAB_AXIS_LOCK_PX = (\d+)', index)
    assert lock, 'the axis-lock distance is not a named constant'
    assert int(lock.group(1)) <= 20, (
        'the axis locks too late to precede a scroll; the browser will have '
        'taken the touch before the gesture claims it'
    )

    commit = re.search(r'const TAB_COMMIT_FRACTION = ([^;]+);', index)
    assert commit, 'there is no commit distance'
    assert 'TAB_AXIS_LOCK_PX' not in commit.group(1), (
        'the lock distance and the commit distance are the same number -- they '
        'answer different questions and the old handler conflating them is why '
        'nothing could move until the finger lifted'
    )


def test_the_touch_listener_is_not_passive(index):
    """A passive listener cannot call preventDefault() at all.

    Registered passive, the gesture works everywhere except the platform it was
    written for: iOS hands an uncancelled sequence to the scroller and ignores
    every later attempt to take it back.
    """
    move = re.search(
        r"addEventListener\('touchmove',(.*?)\{\s*passive:\s*(\w+)\s*\}",
        index,
        flags=re.S,
    )
    assert move, 'no touchmove listener found'
    assert move.group(2) == 'false', (
        'the touchmove listener is passive, so it cannot preventDefault() and '
        'the page scrolls out from under the drag'
    )


def test_the_axis_is_decided_once_and_held(index):
    """A gesture that re-arbitrates can hand a moving page back to the scroller."""
    body = re.search(
        r"addEventListener\('touchmove'.*?\}, \{ passive: false \}\)",
        index,
        flags=re.S,
    )
    assert body, 'no touchmove listener found'
    assert re.search(r"if\s*\(axis === 'y'.*?\)\s*return", body.group(0)), (
        'the touchmove handler does not bail out for a touch already assigned '
        'to the scroller, so a vertical scroll can still be stolen mid-gesture'
    )


def test_the_drag_is_refused_at_touchstart_not_at_release(index):
    """A drag that discovers the conflict late has already moved two tabs.

    The old handler checked at touchend, which is enough when nothing has moved.
    By the time a drag could abort it has suppressed the browser's handling and
    taken both tabs out of the scroller.
    """
    start = re.search(
        r"addEventListener\('touchstart'(.*?)\}, \{ passive: true \}\)",
        index,
        flags=re.S,
    )
    assert start, 'no touchstart listener found'
    assert 'gestureRefused' in start.group(1), (
        'the drag is not refused at touchstart; an overlay conflict would be '
        'discovered only after the tabs had been pinned and moved'
    )


def test_the_overlay_check_is_not_a_registry(index, overlays_js):
    """A list of overlay names has to be updated when an overlay is added.

    Forgetting is silent: the new overlay opens, and a swipe across it drags the
    library behind it. The overlay system already answers this question by
    scanning the DOM, so the drag asks it rather than keeping its own list.
    """
    assert 'GlimpseOverlays.anyOverlayOpen' in overlays_js, (
        'overlays.js does not export anyOverlayOpen(), so index.html has to '
        'reimplement it -- which means a registry'
    )
    body = function_body(index, 'gestureRefused')
    assert 'GlimpseOverlays.anyOverlayOpen()' in body, (
        'the drag does not use the overlay system to decide whether one is open'
    )
    for name in ('detailOpen', 'menuOpen', 'genreOpen', 'trailerOpen', 'rouletteOpen'):
        assert name not in body, (
            f'the refusal names {name} -- a registry by another route, and an '
            f'overlay added later inherits nothing'
        )


def test_touchcancel_resolves_the_drag(index):
    """A system gesture ends the touch without a touchend.

    Without this the tabs stay pinned out of the scroller and the grid stays
    refusing to re-window: a page that will not scroll, with nothing on screen
    to explain it.
    """
    assert re.search(r"addEventListener\('touchcancel'", index), (
        'touchcancel is not bound; an interrupted drag strands both tabs pinned'
    )
    cancel = re.search(
        r"addEventListener\('touchcancel'(.*?)\}, \{ passive: true \}\)",
        index,
        flags=re.S,
    )
    assert 'settleTabDrag()' in cancel.group(1), (
        'touchcancel does not route to the same resolution as a release'
    )


def test_the_tracker_writes_once_per_frame(index):
    """touchmove fires at the digitiser's rate, not the frame rate.

    On a 120Hz panel that is two style writes per frame, the second discarding
    the first, on the frames that can least afford it.
    """
    body = function_body(index, 'trackTabDrag')
    assert 'requestAnimationFrame' in body, 'the tracker does not coalesce to a frame'
    assert re.search(r'if\s*\(record\.frame !== null\)\s*return', body), (
        'the tracker schedules a frame per move rather than coalescing them'
    )


def test_a_drag_is_never_latched(index):
    """A drag past the threshold that comes back is an abandon.

    Latching would mean the tabs keep following a finger whose gesture has
    already been decided, which is the thing this change removes.
    """
    body = function_body(index, 'dragCommits')
    assert 'drag.offset' in body, (
        "the commit test does not read the drag's CURRENT offset, so it cannot "
        'tell a drag that came back from one that did not'
    )
    assert 'latch' not in index.lower(), 'something latches the commit decision'


def test_the_settle_is_timed_from_the_distance_remaining(index, tokens):
    """A fixed duration is wrong at both ends.

    A tab released at 95% of its travel spends the full time crossing the last
    sliver; one released at 5% covers nearly the whole viewport in it.
    """
    assert '--dur-tab-settle-min:' in tokens, 'tokens.css does not declare a floor for the settle'
    body = function_body(index, 'settleDuration')
    assert 'TAB_TRANSITION_MS' in body and 'TAB_SETTLE_MIN_MS' in body, (
        'the settle is not bounded by both the tab duration and the floor'
    )
    assert 'var(--dur-tab-settling, var(--dur-tab))' in index, (
        'the sliding rule does not fall back to --dur-tab, so a slide from rest '
        'has no duration at all'
    )


def test_the_drag_numbers_live_in_tokens(index, tokens):
    """Two files must agree about the parallax, so one of them owns it.

    The ratio is also how far out the incoming tab parks -- a tab entering at a
    third of the finger's speed must start a third of a viewport out, or it does
    not arrive as the outgoing one leaves. Two literals drift; one token cannot.
    """
    for token in ('--tab-drag-parallax:', '--tab-drag-lift:', '--tab-drag-scrim:'):
        assert token in tokens, f'tokens.css does not declare {token}'
    for read in ("readToken('--tab-drag-parallax'", "readToken('--tab-drag-lift'"):
        assert read in index, f'index.html restates a token instead of reading it: {read}'


def test_the_lift_declares_no_radius_it_cannot_draw(index):
    """The frozen tab is as tall as the library; its corners are not on screen.

    A rounded corner is the obvious third ingredient of a lift and it would draw
    nothing. A declaration that appears to shape the panel and does not is where
    the next live one hides.
    """
    rule = css_rule(index, '.content.tab-lifted')
    assert 'box-shadow' in rule, 'the lift has no elevation'
    assert 'border-radius' not in rule, (
        'the lifted tab declares a radius it cannot draw -- it is pinned at the '
        'captured scroll offset and is as tall as the whole library'
    )


def test_the_drag_is_gated_with_the_gesture_not_a_breakpoint(index):
    """One condition cannot drift from itself.

    This project has already shipped a hide-control rule and its show-the-
    replacement rule as separate media queries that reached 992px and 768px
    independently, leaving every width between them with neither.
    """
    assert re.search(r'const isMobile = .*?innerWidth < 768', index), (
        'the gesture flag is gone or changed shape'
    )
    for handler in ('touchstart', 'touchmove', 'touchend', 'touchcancel'):
        assert f"addEventListener('{handler}'" in index, f'{handler} is not bound'
    binding = index.index("addEventListener('touchstart'")
    gate = index.index('if (isMobile) {')
    assert gate < binding, (
        'the touch listeners are bound outside the isMobile gate, so a width '
        'could drag without the animation being enabled'
    )


def test_teardown_clears_everything_the_drag_sets(index):
    """Enumerated, so a setup line without a teardown line is visible here.

    A drag takes two tabs out of the scroller and stops the grid re-windowing.
    Leaving that in place because a touch was cancelled gives the viewer a page
    that cannot scroll and a grid that cannot render new rows, with nothing on
    screen to explain it.
    """
    body = function_body(index, 'endTabTransition')
    for cls in ('tab-leaving', 'tab-entering', 'tab-pinned', 'tab-sliding', 'tab-lifted'):
        assert cls in body, f'the teardown does not clear {cls}'
    for prop in ('--tab-shift', '--tab-lift', '--dur-tab-settling', 'top'):
        assert prop in body, f'the teardown does not clear {prop}'
    for root in ('tab-transitioning', 'tab-dragging'):
        assert root in body, f'the teardown does not clear {root} from the root'
    assert 'cancelAnimationFrame' in body, (
        "the teardown leaves the tracker's pending frame scheduled, so one more "
        'write lands after everything it writes to has been cleared'
    )


def test_an_abandoned_drag_restores_the_scroll_after_unpinning(index):
    """Order is the whole of it.

    Un-pinning restores the document's full height with the page at the top of
    the library; the scroll must follow in the same synchronous block, with no
    paint between, or the viewer sees one frame at row 0.
    """
    body = function_body(index, 'endTabTransition')
    unpin = body.index('classList.remove(')
    restore = body.index('scrollPageTo(restoreY')
    assert unpin < restore, (
        'the scroll is restored before the tabs are un-pinned, so it is clamped '
        'against the collapsed document and lands at 0'
    )
    assert re.search(r"scrollPageTo\(restoreY,\s*'instant'\)", body), (
        'the restore is smooth, so an abandoned drag animates a correction that '
        'is supposed to be invisible'
    )
