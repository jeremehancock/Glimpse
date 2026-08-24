/* ==========================================================================
   Overlay behavior: drag-to-dismiss, page scroll lock, focus management.

   Three independent pieces, and all three share one design decision: none of
   them knows which overlays exist. They find their subjects in the DOM — by
   class, by the inline `display` Alpine writes, by `role="dialog"` — rather
   than from a registry.

   That is not elegance for its own sake. A registry has to be updated when an
   overlay is added, and the failure when it is not is silent: the overlay opens
   and looks completely normal, but cannot be swiped away, does not lock the
   page, and strands a keyboard user behind its backdrop. Keying on the DOM
   means an overlay is managed by being marked up correctly, including one
   created at runtime.

   Ported from Marquee.
   ========================================================================== */

(function () {
    'use strict';

    // Every overlay root. The scroll lock and focus manager both scan these.
    const OVERLAY = '.sheet, .modal';

    /* ----------------------------------------------------------------------
       Drag to dismiss

       A downward drag starting on the grab handle, the head, or a pinned region
       above the body — never on the scrolling body — dismisses the overlay by
       clicking its own backdrop. That indirection is the point: whatever an
       overlay does when its backdrop is clicked is what it does when it is
       dragged away, so the gesture needs to know nothing about which Alpine
       scope owns it.

       `.modal__fixed` is in the list because the detail overlay pins the item's
       poster and metadata there. Once that block is visually part of the fixed
       top of a tray, a drag on it that does nothing reads as broken — the user
       is pulling on the largest still object on the screen.

       Buttons inside a drag region keep working. A tap without movement ends
       below the dismissal threshold, so nothing is dismissed and the click
       proceeds; `touch-action: none` suppresses browser panning, not activation.

       This relies on the markup keeping the drag regions and the scrolling
       region as SEPARATE elements. They carry `touch-action: none`, which the
       browser honours only if they are not themselves the scroller. Collapsing
       the head into the body — or giving a pinned region its own overflow —
       hands the gesture back to the browser as a scroll, silently.
       ---------------------------------------------------------------------- */
    (function () {
        let drag = null;

        document.addEventListener(
            'touchstart',
            function (e) {
                const grip = e.target.closest(
                    '.sheet__grip, .sheet__head, .modal__head, .modal__fixed'
                );
                const panel = grip ? grip.closest('.sheet__panel, .modal__panel') : null;
                if (!panel) return;
                drag = {
                    panel: panel,
                    startY: e.touches[0].clientY,
                    dy: 0,
                    height: panel.offsetHeight,
                };
                panel.style.transition = 'none';
            },
            { passive: true }
        );

        document.addEventListener(
            'touchmove',
            function (e) {
                if (!drag) return;
                const dy = e.touches[0].clientY - drag.startY;
                // Downward only. An upward drag on the handle is not a gesture
                // this overlay has, and following it would let the user lift a
                // tray off the bottom of the screen.
                drag.dy = dy > 0 ? dy : 0;
                drag.panel.style.transform = 'translateY(' + drag.dy + 'px)';
            },
            { passive: true }
        );

        function endDrag() {
            if (!drag) return;
            const panel = drag.panel;
            const dismissed = drag.dy > Math.min(120, drag.height * 0.3);

            // Both inline styles are cleared BEFORE the dismissal below, and the
            // order matters. The leave transition animates the panel out through
            // a class, and an inline transform left from the drag would outrank
            // it — the backdrop would fade while the panel sat frozen wherever
            // the finger let go. Clearing first hands the panel back to the
            // stylesheet, so a released drag settles and the exit runs from
            // there.
            panel.style.transition = '';
            panel.style.transform = '';

            if (dismissed) {
                const overlay = panel.closest(OVERLAY);
                const backdrop =
                    overlay && overlay.querySelector('.sheet__backdrop, .modal__backdrop');
                if (backdrop) backdrop.click();
            }
            drag = null;
        }

        document.addEventListener('touchend', endDrag);
        document.addEventListener('touchcancel', endDrag);
    })();

    /* ----------------------------------------------------------------------
       Page scroll lock

       Overlays are fixed layers over a document that is otherwise still live,
       so without this the page scrolls behind them: a drag on a backdrop has
       nothing of its own to scroll and chains straight to the document.

       Watches the DOM rather than subscribing to state, for the reason at the
       top of this file — open state is spread across every overlay's own Alpine
       scope, and one of them is teleported.
       ---------------------------------------------------------------------- */
    (function () {
        let scrollY = 0;
        let locked = false;
        let queued = false;

        // An overlay that is transitioning out does not count. Alpine keeps the
        // element displayed for the length of the leave animation, so without
        // this the page stays pinned for an extra beat after every dismissal —
        // the user closes an overlay, flicks to scroll, and the first flick is
        // swallowed. The class is the same one that makes a dying overlay stop
        // taking clicks.
        function anyOverlayOpen() {
            const overlays = document.querySelectorAll(OVERLAY);
            for (let i = 0; i < overlays.length; i++) {
                if (overlays[i].style.display === 'none') continue;
                if (overlays[i].classList.contains('overlay-closing')) continue;
                return true;
            }
            return false;
        }

        function sync() {
            queued = false;
            const open = anyOverlayOpen();
            if (open === locked) return;

            const root = document.documentElement;
            if (open) {
                scrollY = window.scrollY;
                // Pinning the body collapses the document's scroll height,
                // which takes a classic desktop scrollbar with it and shifts
                // the layout sideways. Hold its width back as padding.
                const gap = window.innerWidth - root.clientWidth;
                if (gap > 0) document.body.style.paddingRight = gap + 'px';
                document.body.style.top = -scrollY + 'px';
                root.classList.add('is-overlay-open');
            } else {
                root.classList.remove('is-overlay-open');
                document.body.style.top = '';
                document.body.style.paddingRight = '';
                window.scrollTo(0, scrollY);
            }
            locked = open;
        }

        function schedule() {
            if (queued) return;
            queued = true;
            requestAnimationFrame(sync);
        }

        // `style` catches x-show writing display; `class` catches the closing
        // class arriving and leaving.
        new MutationObserver(schedule).observe(document.documentElement, {
            subtree: true,
            childList: true,
            attributes: true,
            attributeFilter: ['style', 'class'],
        });

        schedule();
    })();

    /* ----------------------------------------------------------------------
       Focus management

       An overlay is managed because its panel declares role="dialog" and
       tabindex="-1". NOTHING ELSE MAKES IT SO. An overlay added without them
       opens, looks completely correct, and leaves a keyboard user on the page
       behind the backdrop with no way in.
       ---------------------------------------------------------------------- */
    (function () {
        // What is open, and where focus came from, innermost last.
        const stack = [];

        // The dialog an open overlay root stands for, or null if it is not one.
        // Descendant-or-self, because an overlay may declare the role on its own
        // root when it has no inner panel.
        function nextDialog(root) {
            if (root.style.display === 'none') return null;
            // A closing overlay is not open — the same reason the scroll lock
            // releases on this class rather than waiting for `display: none`
            // several frames later. Waiting would hold focus inside an overlay
            // the user has already dismissed.
            if (root.classList.contains('overlay-closing')) return null;
            if (root.matches('[role="dialog"]')) return root;
            return root.querySelector('[role="dialog"]');
        }

        function openDialogs() {
            const found = [];
            const roots = document.querySelectorAll(OVERLAY);
            for (let i = 0; i < roots.length; i++) {
                const dialog = nextDialog(roots[i]);
                if (dialog) found.push(dialog);
            }
            return found;
        }

        function held(dialog) {
            return stack.some((entry) => entry.dialog === dialog);
        }

        // Where focus was when an overlay opened, remembered as a CHAIN rather
        // than a single element, because the origin is often gone by the time it
        // is wanted — the card whose button opened a tray can be filtered away
        // while the tray is up. Restoring then walks to the nearest ancestor
        // still in the document, so the user resumes near where they were.
        //
        // Stops short of <body>. An origin of <body> is what a touch tap leaves
        // behind, and "restore to the body" is the failure this whole block
        // exists to end — so an empty chain restores nothing and leaves focus
        // alone.
        function chainFor(node) {
            const chain = [];
            while (node && node !== document.body && node !== document.documentElement) {
                chain.push(node);
                node = node.parentElement;
            }
            return chain;
        }

        // Focus without moving the page: while an overlay is open the body is
        // pinned, so an unguarded focus scroll would fight the scroll lock.
        //
        // A surviving ancestor is not necessarily focusable, so an element that
        // refuses focus is given a negative tabindex and asked again. The
        // attribute is taken back if it did not help, and that is not tidiness:
        // an element also refuses focus while hidden, and a negative tabindex
        // left on a button that merely happened to be hidden would drop it out
        // of the tab order for good once the page showed it again — which is
        // precisely the failure this block exists to end.
        function focus(node) {
            node.focus({ preventScroll: true });
            if (document.activeElement === node) return true;

            const had = node.hasAttribute('tabindex');
            if (!had) node.setAttribute('tabindex', '-1');
            node.focus({ preventScroll: true });
            if (document.activeElement === node) return true;

            if (!had) node.removeAttribute('tabindex');
            return false;
        }

        function restore(chain) {
            for (let i = 0; i < chain.length; i++) {
                if (chain[i].isConnected && focus(chain[i])) return;
            }
        }

        function sync() {
            const open = openDialogs();

            // Closed since last time, innermost first.
            for (let i = stack.length - 1; i >= 0; i--) {
                if (open.indexOf(stack[i].dialog) === -1) {
                    restore(stack[i].origin);
                    stack.splice(i, 1);
                }
            }

            // Newly opened.
            for (let i = 0; i < open.length; i++) {
                if (held(open[i])) continue;
                stack.push({ dialog: open[i], origin: chainFor(document.activeElement) });
                focus(open[i]);
            }
        }

        let queued = false;
        function schedule() {
            if (queued) return;
            queued = true;
            requestAnimationFrame(function () {
                queued = false;
                sync();
            });
        }

        new MutationObserver(schedule).observe(document.documentElement, {
            subtree: true,
            childList: true,
            attributes: true,
            attributeFilter: ['style', 'class'],
        });

        // Keep focus inside the topmost dialog. Without this, tabbing past the
        // last control in an overlay lands on the page behind it — which is
        // reachable, invisible behind a backdrop, and impossible to navigate.
        document.addEventListener('keydown', function (e) {
            if (e.key !== 'Tab' || stack.length === 0) return;
            const dialog = stack[stack.length - 1].dialog;
            if (!dialog.isConnected) return;

            const focusable = dialog.querySelectorAll(
                'a[href], button:not([disabled]), input:not([disabled]), ' +
                    'select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
            );
            const visible = Array.prototype.filter.call(focusable, function (el) {
                return el.offsetParent !== null || el === document.activeElement;
            });
            if (visible.length === 0) {
                // Nothing to move to; hold focus on the panel itself.
                e.preventDefault();
                return;
            }

            const first = visible[0];
            const last = visible[visible.length - 1];
            if (e.shiftKey && (document.activeElement === first || document.activeElement === dialog)) {
                e.preventDefault();
                focus(last);
            } else if (!e.shiftKey && document.activeElement === last) {
                e.preventDefault();
                focus(first);
            }
        });

        schedule();
    })();
})();
