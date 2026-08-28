"""The vertical rhythm of the detail overlay's scrolling body.

What this file CAN check is that the relations hold. What it cannot check is
what any of it renders as: CI has no browser, and an assertion that the CSS says
what the CSS says passes whatever the page looks like. So the pixels are
verified by hand, in DevTools, against a real item — the same split as
`test_grid_windowing.py` and `tools/grid_metrics.py`.

Every relation pinned here is one that would otherwise drift silently, because
each half of it is separately plausible:

  - The heading gap is HALF the section gap. Written as two literals, `12px`
    beside `24px` reads as two independent choices, and either can be edited
    without the other. The defect this replaces was that pair inverted — 5px
    above a heading against 15px below — so every heading grouped with the
    section it did not belong to, and nothing in the source said the two numbers
    were related.
  - The prose trim is derived from the prose's own leading. A literal `-0.35em`
    is a second copy of `1.7`, and when the two disagree the gaps merely look
    almost right.
  - The token has readers in two files. That is the only reason it is a token
    rather than a number at the rule.
"""

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
WEB = REPO_ROOT / 'web'
INDEX = WEB / 'index.html'
TOKENS = WEB / 'assets' / 'tokens.css'
OVERLAYS_CSS = WEB / 'assets' / 'overlays.css'

SECTION_GAP = '--overlay-section-gap'
PROSE_LEADING = '--prose-leading'


def strip_comments(source: str) -> str:
    source = re.sub(r'<!--.*?-->', '', source, flags=re.S)
    source = re.sub(r'/\*.*?\*/', '', source, flags=re.S)
    return source


def css_rules(source: str, indent: int) -> dict[str, str]:
    """Every rule at ONE nesting level, keyed by its whole selector list.

    Keyed by the list rather than found by substring, because `.modal-section`
    is a prefix of `.modal-section-title` and `.modal-section + .modal-section`,
    and a substring search would assert against whichever happened to come
    first. `indent` selects the level: 8 for a top-level rule in index.html's
    inline stylesheet, 12 for one inside a media query, 0 for the standalone
    stylesheets.
    """
    pad = ' ' * indent
    pattern = rf'^{pad}([^\s@{{][^{{}}]*?)\{{(.*?)^{pad}\}}'
    return {
        re.sub(r'\s+', ' ', match.group(1)).strip(): match.group(2)
        for match in re.finditer(pattern, source, flags=re.S | re.M)
    }


def css_block(source: str, selector: str, indent: int) -> str:
    rules = css_rules(source, indent)
    assert selector in rules, (
        f'no rule for `{selector}`; if it was renamed, update this test rather '
        f'than the assertion built on it'
    )
    return rules[selector]


@pytest.fixture(scope='module')
def index() -> str:
    return strip_comments(INDEX.read_text())


@pytest.fixture(scope='module')
def tokens() -> str:
    return strip_comments(TOKENS.read_text())


@pytest.fixture(scope='module')
def overlays() -> str:
    return strip_comments(OVERLAYS_CSS.read_text())


@pytest.fixture(scope='module')
def markup() -> str:
    """Markup with comments removed.

    The comments explaining this change name `.summary-section` and
    `modal-prose`, so a search over the raw file passes judgement on a note
    about the fix rather than on the fix.
    """
    return strip_comments(INDEX.read_text())


# ---------------------------------------------------------------------------
# One separation, with a reader in each file
# ---------------------------------------------------------------------------


def test_the_section_gap_is_a_token(tokens):
    """It is a token because two files have to agree about it, not for tidiness."""
    declared = re.findall(rf'{SECTION_GAP}\s*:\s*([^;}}]+)', tokens)
    assert len(declared) == 1, (
        f'{SECTION_GAP} is declared {len(declared)} times in tokens.css; a token '
        f'declared twice is two values waiting to disagree'
    )
    assert re.fullmatch(r'\d+px', declared[0].strip()), (
        f'{SECTION_GAP} should be a plain pixel length, not {declared[0]!r} — '
        f'the heading gap is derived from it with a calc(), which needs a length'
    )


def test_both_files_read_the_section_gap(index, overlays):
    """The cross-file agreement is the whole justification for the token.

    If either of these stops reading it, the token has one reader and the
    argument for putting it in tokens.css has gone with it.
    """
    division = css_block(overlays, '.modal__fixed + .modal__body', indent=0)
    assert f'var({SECTION_GAP})' in division, (
        'the gap below the division under a pinned region must read the shared '
        'section gap; a literal here is how it drifts from the sections below it'
    )

    between = css_block(index, '.modal-section + .modal-section', indent=8)
    assert f'var({SECTION_GAP})' in between


def test_the_division_is_not_the_smallest_gap_in_the_body(overlays):
    """It reads the gap whole — not half of it, and not a number of its own.

    The border under the identity block is the heaviest division in the body. A
    heading stands one separation clear of whatever precedes it, and this border
    is one of the things that can precede it.
    """
    division = css_block(overlays, '.modal__fixed + .modal__body', indent=0)
    padding = re.search(r'padding-top\s*:\s*([^;]+)', division)
    assert padding, '.modal__fixed + .modal__body declares no padding-top'
    assert padding.group(1).strip() == f'var({SECTION_GAP})', (
        f'expected the bare token, got {padding.group(1).strip()!r} — dividing '
        f'or offsetting it here puts the division at a gap no section uses'
    )


# ---------------------------------------------------------------------------
# The rhythm: between sections, and inside one
# ---------------------------------------------------------------------------


def test_a_section_carries_no_trailing_margin(index):
    """The gap is between siblings, so the body's padding is the body's padding.

    A `margin-bottom` on every section adds itself to `.modal__body`'s own
    `padding-bottom` under the last one, which made the foot of the body 25px
    against 20px at its sides — the sum of two rules, neither written for it.
    """
    rules = css_rules(index, indent=8)
    bare = rules.get('.modal-section')
    assert bare is None or 'margin-bottom' not in bare, (
        'a bare `.modal-section` rule sets a bottom margin again; that is the '
        'route the inverted rhythm arrived on, and it puts an unchosen number '
        'under the last section'
    )


def test_a_section_stays_transparent_to_margin_collapsing(index):
    """The prose trim rides on collapsing THROUGH `.modal-section`.

    The trim's negative bottom margin has to escape the section to meet the next
    section's top margin. Padding, a border, or a formatting context of its own
    stops that, and every prose gap silently grows by the half-leading — from an
    edit that looks like it has nothing to do with spacing.
    """
    rules = css_rules(index, indent=8)
    for selector in ('.modal-section', '.modal-section + .modal-section'):
        body = rules.get(selector)
        if body is None:
            continue
        for prop in ('padding', 'border', 'overflow', 'display'):
            assert not re.search(rf'(?<![-\w]){prop}[-\w]*\s*:', body), (
                f'`{selector}` declares `{prop}`; that blocks the margin '
                f'collapsing `.modal-prose` depends on, and the gaps grow by '
                f'the trim with nothing failing'
            )


def test_the_heading_gap_is_derived_from_the_section_gap(index):
    """Half, in a calc(), so the two cannot be edited apart.

    The relation is the decision: a heading groups downward because its own gap
    is the smaller one. A second token holding `12px` would state the same thing
    today and permit a build tomorrow in which a heading sits equidistant
    between two sections.
    """
    title = css_block(index, '.modal-section-title', indent=8)
    margin = re.search(r'margin-bottom\s*:\s*([^;]+)', title)
    assert margin, '.modal-section-title declares no margin-bottom'
    value = margin.group(1).strip()

    assert f'var({SECTION_GAP})' in value, (
        f'the heading gap is {value!r} — a literal, which is a second copy of a '
        f'number whose whole point is being half of another one'
    )
    divisor = re.search(rf'var\({SECTION_GAP}\)\s*/\s*([\d.]+)', value)
    assert divisor and float(divisor.group(1)) > 1, (
        f'the heading gap must be a fraction of the section gap, not {value!r}; '
        f'equal or larger and every heading groups with the section above it, '
        f'which is the defect this replaced'
    )


def test_a_heading_states_its_own_leading(index):
    """A rule that sets a heading's type must set all of it.

    Leading is not decoration in a gap: the distance the eye reads runs to the
    glyph, so half of it sits inside every gap above and below the heading. Left
    unstated it was inherited, and `.summary-section`'s `line-height: 1.7` for
    the summary's prose reached the Overview heading — which is why that one
    heading sat lower, and further from its own text, than the other three.
    """
    title = css_block(index, '.modal-section-title', indent=8)
    assert re.search(r'(?<![-\w])line-height\s*:', title), (
        '.modal-section-title sets size, weight and colour but not leading; the '
        'value it inherits is then whichever ancestor set one last'
    )


def test_no_section_imposes_prose_leading_on_its_heading(index, markup):
    """`.summary-section` is gone, rule and class.

    Its `line-height` belongs to the prose and has moved there; its `color`
    restated the `--light-text` that `body` already sets. A class with no rule
    and a rule with only dead declarations are the same kind of thing.
    """
    assert '.summary-section' not in index, (
        'a `.summary-section` rule is back; leading set on a section reaches '
        "that section's heading, which is the defect it was removed for"
    )
    assert 'summary-section' not in markup, (
        'the class is still in the markup with no rule behind it'
    )


# ---------------------------------------------------------------------------
# Prose leaves the same gap as a filled block
# ---------------------------------------------------------------------------


def test_the_prose_trim_is_derived_from_the_prose_leading(index):
    """One number, read twice, so the trim cannot drift from what it trims.

    The trim is exactly the half-leading a line box adds above and below its
    glyphs. Written as a literal it is a second copy of the leading, and when
    the two disagree nothing fails — the gaps just stop being equal, by a few
    pixels, which is the thing this whole change is about.
    """
    prose = css_block(index, '.modal-prose', indent=8)

    assert re.search(rf'{PROSE_LEADING}\s*:\s*[\d.]+\s*;', prose), (
        f'.modal-prose does not declare {PROSE_LEADING}; without it the trim '
        f'below has nothing to derive from'
    )
    assert re.search(rf'line-height\s*:\s*var\({PROSE_LEADING}\)', prose), (
        f'.modal-prose must set its leading FROM {PROSE_LEADING}, or the token '
        f'describes a leading the element does not have'
    )

    trim = re.search(r'margin-block\s*:\s*([^;]+)', prose)
    assert trim, (
        '.modal-prose declares no margin-block; without the trim, bare text '
        'leaves a bigger gap than a genre pill or a cast card does'
    )
    assert f'var({PROSE_LEADING})' in trim.group(1), (
        f'the trim is {trim.group(1).strip()!r} — a literal, which is a second '
        f'copy of the leading it is supposed to cancel'
    )


def test_every_bare_prose_block_in_the_body_carries_the_class(markup):
    """Including the three `openModal()` builds at runtime.

    The two placeholders are the ones that would never be reported: bare text in
    a slot that normally holds pills or cards, on the path taken only by an item
    with no genres or no cast.
    """
    sites = {
        'the summary': r'id="modal-summary"[^>]*class="[^"]*\bmodal-prose\b',
        'the Date Added value': r'id="modal-added-date"[^>]*class="[^"]*\bmodal-prose\b',
        'the no-genres placeholder': r'class="modal-prose">No genres available',
        'the no-cast placeholder': r'class="modal-prose">No cast information',
    }
    for name, pattern in sites.items():
        assert re.search(pattern, markup), (
            f'{name} is bare prose without `.modal-prose`, so its half-leading '
            f'is left in the gap and that seam runs long'
        )
