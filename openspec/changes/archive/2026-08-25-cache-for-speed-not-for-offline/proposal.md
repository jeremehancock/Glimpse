## Why

The service worker held two pieces of live code that could not succeed, and one
that would have become dangerous the moment it could.

`/config.json` and the library snapshots were fetched with a `caches.match()`
fallback against a cache **nothing ever populated**. The fallback line existed,
read correctly, and had never once returned anything. That is worse than no code
at all: everyone who read it saw offline support, so nobody looked.

The same function also fell back to cache on **any non-OK response**, not only on
a failed fetch. That was inert while the cache was empty. It would not have
stayed inert, and what it would have become is a mechanism for hiding a container
whose entrypoint failed behind the last response that worked — the failure this
project spent years on, arrived at from a new direction.

This change deletes the dead fallback rather than making it work, and fixes the
dangerous one.

> **This change reversed direction during implementation.** It began as
> `serve-the-library-offline` and made the app fully offline-capable: snapshots
> cached, configuration retained, a header indicator while stale. That was built,
> verified 30/30 in a real browser, and then **withdrawn at the user's direction**
> — showing a library that may be out of date is the same ambiguity this app
> refuses everywhere else, and offline browsing was never the goal. What the
> punch-list item actually asked was whether the caching layers make the app
> *fast*. See design decision 0.

## What Changes

- **The library data is never cached, in either direction.** `/config.json` and
  `/data/*.json` are network-only: no cache read, no cache write. The app shows
  the container's answer or it shows an error, and never something in between.

- **A response the server actually returned is never replaced by a cached one.**
  Only a fetch that *threw* may be answered from cache. A status is the server
  speaking; the absence of a status is the network. This applies to every
  strategy in the file, not just the one that had the bug.

- **What makes the app fast is kept and stated.** Artwork stays
  stale-while-revalidate, so a repeat visit paints its grid without a single
  round trip. The app's own CSS and JS stay network-first with a cache fallback,
  so the interface renders immediately and still upgrades. Neither was changed;
  both are now pinned by tests, because they are the whole point.

- **It is written down that the worker cannot cache `config.json` even if
  someone wants it to.** The boot read is a synchronous XHR, and browsers
  dispatch no fetch event for one. Measured, not assumed. Without that note,
  "cache config.json too" looks like a one-line improvement.

## Capabilities

### Modified Capabilities

- `pwa`: the caching contract becomes explicit — what is cached and why, what is
  never cached and why, and the one rule that governs both.
- `application-shell`: unchanged in behavior. The `config.json` rule gains a note
  recording that an exception was tried and withdrawn.
- `media-browsing`: the grid always reflects the container's current snapshot,
  and an unreachable container is reported rather than papered over.
