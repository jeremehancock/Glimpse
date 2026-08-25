## Context

Six overlays, six implementations:

| Overlay | Today |
| --- | --- |
| Mobile menu | `.mobile-menu` — a slide-down panel, not a dialog |
| Genre filter | `.genre-menu` dropdown on desktop **and** `.genre-drawer` on phones — two implementations of one control |
| Media detail | `.modal-overlay` — centred box at every width |
| Trailer | `.trailer-modal-overlay` — its own centred box |
| Roulette | `.roulette-overlay` — its own centred box |
| Server switcher | a popover, added by the previous change |

Each has its own open/close code, its own backdrop, its own class-toggling. None
locks the page behind it, moves focus, or can be swiped away.

Marquee has already solved this, and solved it in a way worth copying rather
than re-deriving: one presentation with two shapes, a gesture and a scroll lock
that stay agnostic of which overlay they are acting on, and a focus manager that
finds its subjects by an attribute rather than a registry. That last property is
what makes the system survive contact with future work — an overlay added later
is managed by being marked up correctly, not by remembering to register it.

Constraints:

- No build step. `web/` is served exactly as authored; Alpine is vendored.
- `docker-compose.yml` is frozen.
- Every feature keeps working identically. This change is presentation only.
- The entrypoint generates and never mutates, so nothing here can rely on
  server-side rewriting.

## Goals / Non-Goals

**Goals:**

- One overlay presentation, used by all six.
- A tray on a phone, a dialog on a pointer device, from the same markup.
- Swipe-to-dismiss, a scroll lock, and managed focus — for all of them, from
  code that does not enumerate them.
- The token vocabulary the rest of the frontend rewrite will build on.
- Delete the genre filter's duplicate implementation.

**Non-Goals:**

- Splitting `index.html` into ES modules. That is the next change; doing it here
  would mean two large diffs landing as one and no way to tell which broke what.
- Restyling the poster grid, the header, or the search field.
- Any change to the fetchers, the snapshot, or `checksums.pkl`.
- New features. If something cannot be done today, it cannot be done after.

## Decisions

### 1. Alpine drives open state; CSS drives appearance

Alpine owns *when* an overlay is shown (`x-show`) and applies classes at the
right moments (`x-transition`). The stylesheet owns *how* it looks and moves.
The division matters because it is what lets one set of transition classes serve
both shapes: a dialog and a tray differ in how they move, not in when, and the
stylesheet keys that difference off the panel inside — `.modal__panel` scales,
`.sheet__panel` slides.

```
.overlay-opening / .overlay-closing   the transition
.overlay-shut    / .overlay-shown     the two resting states
```

`enter-start` and `leave-end` are the same class, as are `enter-end` and
`leave-start`: an overlay has two resting appearances, and a transition is a trip
between them in one direction or the other.

*Alternative considered:* a vanilla controller. Rejected in favour of matching
Marquee exactly — the CSS, the gesture, and the focus code port unchanged either
way, so the only thing a hand-rolled controller buys is one fewer file and one
more thing of mine to get wrong.

### 2. `.sheet` and `.modal` are the same overlay wearing two shapes

Both have a backdrop, a grab handle, a head with a title, and a body that
scrolls. `.sheet` docks to the bottom edge and slides; `.modal` centres and
scales. Which one an overlay uses is a product decision per overlay, not a
breakpoint — the detail view is a tray on a phone and a dialog on desktop, but
the trailer is a dialog everywhere because it is sized to a video.

**The panel clips; its body scrolls.** Keeping the scroll on the body rather than
the panel means an overlay pinned inside a tray stays put while content moves
under it.

**`overscroll-behavior: contain` on the body.** Without it, a flick that reaches
the end of a tray's content hands the rest of the gesture to the page behind it,
which then scrolls — or, at the top, pulls to refresh — from under an overlay the
user thought had the screen.

### 3. The drag gesture is bound to the document, not to an overlay

One listener on `document`, keyed on `.sheet__grip, .sheet__head, .modal__head`.
A downward drag dismisses by clicking the overlay's own backdrop, reusing
whatever close behavior that overlay already has. So the gesture works for all
six without knowing which Alpine scope owns any of them, and works for a seventh
added later.

**This relies on the drag region and the scrolling region being separate
elements.** The grip and head carry `touch-action: none`, which the browser
honours only if they are not themselves the scroller. Collapsing the head into
the body would silently return the gesture to the browser as a scroll.

**Inline styles are cleared before the dismissal, and the order matters.** The
leave transition animates the panel out through a class; an inline `transform`
left from the drag would outrank it, and the backdrop would fade while the panel
sat frozen where the finger left it.

### 4. The scroll lock pins the body and watches the DOM

`overflow: hidden` on the body is unreliable on iOS Safari and
`overscroll-behavior` is not honoured on the document at all, so the body is
pinned with `position: fixed` and the scroll position restored on release.

It watches for the inline `display` that `x-show` writes rather than subscribing
to six pieces of state — the same reason the gesture is document-bound. **A
closing overlay does not count**: Alpine keeps the element displayed for the
length of the leave transition, so without that check the page stays pinned for
an extra beat after every dismissal and the user's first flick is swallowed.

Pinning the body collapses the document's scroll height, which takes a desktop
scrollbar with it and shifts the layout; the lock holds its width back.

### 5. Focus is managed by attribute, and restored by chain

An overlay is managed because its panel declares `role="dialog"` and
`tabindex="-1"`. Nothing else makes it so. An overlay added without them opens
and looks identical — and leaves a keyboard user on the page behind the backdrop
with no way in.

Where focus came from is remembered as a **chain**, not a single element, because
the origin is often gone by the time it is wanted. The chain stops short of
`<body>`: an origin of `<body>` is what a touch tap leaves behind, and restoring
to the body is the failure the whole mechanism exists to end, so an empty chain
restores nothing.

`aria-modal="true"` carries modality rather than `inert`, because every overlay
here is a descendant of the content it covers — there is nothing to mark. Using
`inert` would mean teleporting overlays to `<body>` first, which is a change, not
a wiring decision.

### 6. The mobile menu is teleported to `<body>`

The menu's state lives on the header, and the header will become a translucent
surface. `backdrop-filter` makes an element a containing block for its
fixed-position descendants — the same rule that catches `transform` — so a
`position: fixed; inset: 0` tray inside it stops resolving against the viewport
and renders squashed into the height of the bar that opened it.

`x-teleport` moves the rendered element out while leaving it inside the reactive
scope. It renders correctly on a desktop viewport either way, because the tray is
hidden there, which is exactly what makes this easy to "simplify" back into a
bug.

### 7. The genre filter becomes one implementation

The desktop dropdown and the phone drawer are replaced by a single tray. Two
implementations of one control is the clearest duplication in the file, and every
genre feature has had to be written twice.

### 8. Reduced motion collapses transitions to instant

Stated once, app-wide, rather than per overlay. An overlay that animates when the
user has asked for no motion is the most noticeable place to get this wrong,
because it moves the largest area of the screen.

## Risks / Trade-offs

**Every interactive surface changes at once** → Content and behavior are held
identical; only presentation moves. Markup assertions pin the traps that no
runtime test catches. Validated on `:dev` before `main`.

**A future overlay is added without its role and silently unmanaged** → A test
asserts every `.sheet__panel` and `.modal__panel` in the markup carries both
attributes. It cannot catch an overlay injected at runtime with neither, which is
why it is also written into `CLAUDE.md`.

**Alpine is a new dependency** → Vendored, versioned in the repo, served as
authored, cached by the service worker. No build step, no CDN, no network
dependency at runtime — the app stays offline-capable.

**46KB more to download** → Once, then cached. Against ~4,000 lines of hand-rolled
overlay code it replaces, and it is the same trade Marquee already makes.

**The detail view is the highest-traffic overlay and the most changed** → It
keeps its exact content and its open path; what changes is the frame around it.
Worth exercising first on `:dev`.

## Migration Plan

No user action. Presentation only; nothing on disk changes shape.

1. Vendor Alpine; add the token and overlay stylesheets.
2. Port the gesture, scroll lock, and focus manager.
3. Convert overlays one at a time, simplest first: menu → server switcher →
   genre → roulette → trailer → detail. Each is independently checkable.
4. Delete the superseded CSS and JS as each lands.
5. Cache the new assets in the service worker; bump the cache version.
6. `make check`, `make docker-smoke`, then validate on `:dev`.

Rollback is the previous image tag.

## Open Questions

1. **Should the detail view be a tray on desktop too?** Specified as a dialog on
   a pointer device, matching Marquee. A full-height tray on a wide screen is
   defensible for a media detail view with a backdrop image, but it is a
   departure, so it is not assumed.

2. **Does the genre tray keep the desktop dropdown's position?** Specified as a
   centred dialog on desktop rather than a popover anchored to its button. The
   anchored popover is more conventional for a filter; the dialog is one fewer
   presentation to maintain. Reversible either way.
