## Why

Every overlay in Glimpse is built its own way. The genre filter is a CSS
dropdown on desktop and a hand-rolled drawer on phones — two implementations of
one control, in two places, that have to be kept in agreement. The detail view is
a centred modal at every width, so on a phone it is a box floating in the middle
of the screen with a small × in its corner, which is neither what a phone user
expects nor easy to reach one-handed. The trailer and roulette overlays are
centred boxes too, each with its own show/hide code, its own backdrop, and its
own idea of how to close.

None of them can be dismissed by swiping. None of them lock the page behind
them, so scrolling a backdrop scrolls the library underneath. None of them move
keyboard focus, so opening one leaves a keyboard user on the page behind it with
no way in and no way out but Tab. The mobile menu is a slide-down panel that is
not a dialog at all.

Marquee solved this once: a single overlay presentation that is a **bottom sheet
on a phone and a centred dialog on a pointer device**, with a grab handle, a
drag-to-dismiss gesture, a scroll lock, and a focus manager that finds its
subjects by `role="dialog"` rather than by a registry. This change ports that
system to Glimpse and moves every overlay onto it.

## What Changes

- **Alpine.js is vendored** (~46KB, no build step, served as authored), matching
  how Marquee ships it. Overlay open state becomes declarative — `x-show`,
  `x-transition`, `x-teleport` — instead of six sets of hand-written class
  toggles.
- **One overlay presentation, two shapes.** `.sheet` docks to the bottom edge on
  a phone; `.modal` centres on a pointer device. Both carry a backdrop, a grab
  handle, a head with a title, and a scrollable body.
- **All six overlays move onto it:**
  - the mobile menu becomes an Actions tray
  - the genre filter becomes **one** tray, replacing the desktop dropdown *and*
    the phone drawer
  - the media detail modal becomes a tray on phones, a dialog on desktop
  - the trailer overlay becomes a dialog sized to the video
  - the roulette overlay becomes a dialog
  - the server switcher menu becomes a tray, replacing the popover added by the
    previous change
- **Drag-to-dismiss**, ported from Marquee: a downward drag starting on the grab
  handle or the head — never on the scrolling body — dismisses the overlay by
  reusing its backdrop close, so it works for every tray without knowing which
  one it is.
- **The page is locked while an overlay is open**, by pinning the body, which is
  the only technique that holds on iOS Safari.
- **Focus is managed.** An overlay declares `role="dialog"` and `tabindex="-1"`;
  focus moves into it on open and returns to where it came from on close, via an
  origin *chain* so it still works when the element that opened it is gone.
- **Escape closes**, and a control that closes one overlay to open another moves
  focus first.
- **Design tokens arrive** for the surfaces, elevation, radii, durations and
  easings the overlay system needs — the beginning of the token contract the
  `visual-design` capability describes.
- **`prefers-reduced-motion` is honoured**: transitions collapse to instant.

**No feature is removed and no feature is added.** Every overlay shows the same
content, reached the same way, as it does today.

## Capabilities

### New Capabilities

- `visual-design`: The overlay presentation contract — the token set, the two
  overlay shapes and when each applies, transition timing, the drag gesture, the
  scroll lock, and where focus goes when an overlay opens and closes.
- `media-detail`: the per-item view — what it shows and how it is presented,
  reached, and dismissed.
- `genre-filter`: genre extraction with counts, and the single tray that replaces
  today's desktop dropdown and phone drawer.
- `trailers`: the trailer overlay and its embed.
- `roulette`: the random pick and the overlay it runs in.

### Modified Capabilities

None. `openspec/specs/` is empty until `replace-boot-time-html-rewriting`
archives, so there is no existing requirement for this change to modify — every
capability it touches is being specified for the first time.

**`multi-server` is deliberately absent.** Its switcher requirement already reads
"a menu SHALL be shown listing the servers that are not active", which a tray
satisfies: the requirement constrains what the control offers, not how it is
drawn. Presentation is `visual-design`'s to own, and duplicating it here would
give two capabilities a claim on the same pixels.

## Impact

**Code**

- `web/assets/alpine.min.js` — new, vendored.
- `web/index.html` — every overlay's markup replaced; Alpine directives added.
- `web/assets/overlays.css` — new: tokens, `.sheet`, `.modal`, transitions.
- `web/assets/overlays.js` — new: drag gesture, scroll lock, focus manager.
- `web/sw.js` — cache the two new assets and Alpine.
- `tests/` — markup assertions for the traps below, which no runtime test can
  catch.

**The traps this inherits from Marquee, and why they are worth stating**

- **An overlay is managed for focus because it declares `role="dialog"` and
  `tabindex="-1"`, and nothing else makes it so.** One added without them opens
  and strands a keyboard user behind the backdrop, looking no different.
- **A control that closes its own tray and opens another must move focus to
  something still on screen first.** Alpine hides on the flush *after* the
  handler; hiding a focused element hands focus to `<body>`, which the manager
  reads a frame later and declines to restore from. The overlay opens correctly
  and dismissing it drops the user at the top of the page. Nothing errors.
- **The drag region and the scrolling region must stay separate elements.** The
  grip and head carry `touch-action: none`, which the browser only honours if
  they are not themselves the scroller.
- **A closing overlay is not an open one.** The scroll lock and the focus manager
  both key off the closing class, or the page stays pinned for a beat after every
  dismissal and the first flick is swallowed.

**Risk**

This touches every interactive surface in the app at once. Mitigated by keeping
content and behavior identical — only presentation changes — and by validating on
`:dev` before anything reaches `main`.
