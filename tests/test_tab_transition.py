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
    body = function_body(index, 'switchTabAnimated')
    for probe in (
        'getBoundingClientRect',
        'offsetHeight',
        'offsetTop',
        'offsetWidth',
        'getComputedStyle',
    ):
        assert probe not in body, (
            f'switchTabAnimated() calls {probe} -- a forced layout between the '
            f'freeze and the transform costs ~78ms on the first frame of every '
            f'swipe'
        )


def test_the_scroll_position_is_read_before_anything_is_written(index):
    """The offset must be the pre-freeze position.

    Reading it after the tab is out of flow reads the collapsed document, and
    the frozen tab renders somewhere the viewer never was.
    """
    body = function_body(index, 'switchTabAnimated')
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
    body = function_body(index, 'switchTabAnimated')
    render = body.index('filterAndSortMedia(')
    reveal = body.index("classList.add('tab-entering')")
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
    body = function_body(index, 'switchTabAnimated')
    match = re.search(r'filterAndSortMedia\(([^)]*)\)', body)
    assert match, 'switchTabAnimated() does not render the incoming tab'
    assert 'false' in match.group(1), (
        'the sliding tab still animates its cards in; that is redundant under a '
        'slide and is the largest cost on the opening frame'
    )


# ---------------------------------------------------------------------------
# The axis
# ---------------------------------------------------------------------------


@pytest.mark.parametrize('selector', ('.content.tab-leaving', '.content.tab-entering'))
def test_the_transition_translates_horizontally_only(index, selector):
    """firstVisibleRow() derives the grid's window from getBoundingClientRect().top.

    A translateY or a scale moves that top while the transition runs, so a
    scroll mid-flight re-windows the grid against a position the viewer never
    occupied. It presents as an off-by-one in the window, not as a layout bug.
    """
    rule = css_rule(index, selector)
    assert 'translateX(' in rule, f'{selector} does not translate horizontally'
    for banned in ('translateY(', 'scale(', 'translate3d(', 'rotate('):
        assert banned not in rule, (
            f'{selector} uses {banned} -- a vertical or scaling transform '
            f'corrupts the grid window arithmetic mid-transition'
        )


def test_layer_promotion_is_declared_on_the_setup_state_not_the_slide(index):
    """will-change alongside the transform pays for promotion on the worst frame.

    Declared on the frozen and parked states instead, the layer is promoted
    during the setup frame. Measured at 83ms of a 280ms slide when it was not.
    """
    for selector in ('.content.tab-leaving', '.content.tab-entering'):
        assert 'will-change' in css_rule(index, selector), (
            f'{selector} does not promote its layer during setup'
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
    body = function_body(index, 'switchTabAnimated')
    assert 'setTimeout(endTabTransition' in body, (
        'the teardown has no fallback timer; a dropped transitionend leaves a '
        'tab pinned and transformed'
    )
    assert body.index('endTabTransition()') < body.index('window.scrollY'), (
        'switchTabAnimated() does not resolve a transition already in flight '
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
    assert "getPropertyValue('--dur-tab')" in index, (
        'the safety timer restates the duration instead of reading the token'
    )


def test_the_transition_scrolls_instantly(index, overlays_js):
    """scroll-behavior: smooth is set on the document.

    The default animates for about a second underneath a 280ms transition and is
    still travelling when it ends, so the page drifts to the top afterwards.
    Measured before this was fixed: still at 3000px two frames in, settling at
    12px rather than 0.
    """
    body = function_body(index, 'switchTabAnimated')
    assert re.search(r"scrollPageTo\(0,\s*'instant'\)", body), (
        'the transition does not scroll instantly; a smooth scroll outlives the '
        'slide and the page drifts to the top after it ends'
    )
    assert re.search(r'function scrollPageTo\(y, behavior = ', overlays_js), (
        'scrollPageTo() does not accept a behavior, so every caller is smooth'
    )
