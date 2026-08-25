// Service Worker for Glimpse Media Viewer

// Bumped from v8.1 by `fix-overlay-layering-and-dead-tray-controls`, and from
// v7.3 before that by `replace-boot-time-html-rewriting`. Both bumps are
// load-bearing, not cosmetic.
//
// v7.3 -> v8.1: each server route used to be a physically different index.html,
// so a client upgrading from v7.3 could hold a cached page with a theme and data
// paths baked into its markup.
//
// v8.1 -> v8.2: under v8.1 the assets below were served CACHE-FIRST while the
// app shell was served network-first. The shell therefore upgraded and the
// stylesheets and scripts it loads did not — permanently, because the cache name
// never changed during the whole rewrite. Every client that ever loaded a v8.1
// build is pairing today's markup with whatever CSS and JS it first saw.
//
// That is not a stale-content annoyance, it is a correctness trap: it presented
// as a fixed bug still being broken, and cost a full diagnostic pass to tell
// apart from a real regression. The strategy change below is the actual fix;
// this bump is what evicts the entries already poisoned.
const CACHE_NAME = 'glimpse-media-viewer-v8.2';
const DYNAMIC_CACHE = 'glimpse-media-dynamic-v8.2';

// Assets to cache on install.
//
// manifest.json is generated per-primary-server at container start, so it is
// cached under a version that changes when the scheme does — not held forever.
// (/test.html used to be here; it was a debug page the old entrypoint wrote
// into the web root, and it no longer exists.)
const STATIC_ASSETS = [
  '/manifest.json',
  // The overlay system. Alpine especially: it is vendored rather than fetched
  // from a CDN precisely so the app keeps working offline, and that only holds
  // if it is cached alongside everything else.
  '/assets/alpine.min.js',
  '/assets/overlays.js',
  '/assets/tokens.css',
  '/assets/overlays.css',
  // The offline fallback itself. Cached here rather than inlined into this file
  // as a template literal, which is what it used to be — see the note further
  // down about the copy that went stale.
  '/offline.html',
];

// Install event - cache static assets
self.addEventListener('install', (event) => {
  console.log('Service Worker: Installing');
  event.waitUntil(
    caches
      .open(CACHE_NAME)
      .then((cache) => {
        console.log('Service Worker: Caching static files');
        /* Each entry requested with `cache: 'reload'` so the precache is filled
           from the network rather than from the browser's HTTP cache. A plain
           addAll() is allowed to satisfy itself from that cache, which on an
           upgrading client still holds the PREVIOUS build's files — so the new
           worker would faithfully precache the old app and then serve it as its
           offline fallback. */
        return cache.addAll(STATIC_ASSETS.map((url) => new Request(url, { cache: 'reload' })));
      })
      .then(() => {
        console.log('Service Worker: All static assets added to cache');
        return self.skipWaiting(); // Ensure the new service worker activates right away
      }),
  );
});

// Activate event - clean up old caches
self.addEventListener('activate', (event) => {
  console.log('Service Worker: Activating');
  event.waitUntil(
    caches
      .keys()
      .then((cacheNames) => {
        return Promise.all(
          cacheNames
            .filter((cacheName) => {
              return (
                cacheName.startsWith('glimpse-media-') &&
                cacheName !== CACHE_NAME &&
                cacheName !== DYNAMIC_CACHE
              );
            })
            .map((cacheName) => {
              console.log('Service Worker: Clearing old cache:', cacheName);
              return caches.delete(cacheName);
            }),
        );
      })
      .then(() => {
        console.log('Service Worker: Claiming clients');
        return self.clients.claim(); // Take control of all clients
      }),
  );
});

// Check if a request is for the app shell.
//
// These used to be four physically different files, each with a theme and its
// data paths baked in by sed at container start — hence the old name,
// isThemedHtmlRequest. They are now one file: nginx serves the same index.html
// for every route, and the theme comes from config.json at runtime. The routes
// still need listing because they are distinct URLs, but the RESPONSE is
// identical for all of them.
function isAppShellRequest(request) {
  const url = new URL(request.url);
  const pathname = url.pathname;

  return (
    pathname === '/' ||
    pathname === '/index.html' ||
    /^\/(plex|jellyfin|emby)\/(index\.html)?$/.test(pathname)
  );
}

/* The generated configuration. Always the network, never a cache, in either
 * direction — and THIS WORKER IS NOT WHAT MAKES IT AVAILABLE OFFLINE.
 *
 * A browser does not dispatch a fetch event for a synchronous XHR, and the boot
 * read in index.html is a synchronous XHR — parser-blocking, because the theme
 * has to be on <html> before first paint. So this handler never sees that
 * request: it cannot cache it, and it could not answer it from a cache if it
 * had one. Measured rather than assumed; an async fetch() of the same URL does
 * go through here, which is what makes the gap easy to miss.
 *
 * The page therefore retains its own configuration, in localStorage, which is
 * the only same-origin store that can be read before first paint. One offline
 * story, two mechanisms, because no single mechanism covers both halves.
 *
 * What this route IS for: keeping config.json off the cache-first fallback at
 * the bottom of the fetch handler. It does not live under /data/, so without an
 * explicit branch it would be served cache-first, and a container restart with
 * new settings would never be seen by an installed client. That is why the
 * check has to come before the static-asset branch, and why the strategy is
 * network-only rather than the one the snapshots use — a cache this worker can
 * never fill has no business being consulted.
 */
function isConfigRequest(request) {
  return new URL(request.url).pathname === '/config.json';
}

// The app's own stylesheets and scripts.
//
// These are fetched network-first, exactly like the app shell that loads them,
// and NOT cache-first. Pairing a network-first shell with cache-first assets is
// what pinned every installed client to the CSS and JS of whichever build it
// first loaded: the markup upgraded, its behaviour did not, and the two drifted
// apart with nothing to signal it.
//
// They stay in STATIC_ASSETS and are still precached on install, so the cache
// fallback has them when the network is gone. That is the branch that matters
// for an offline-capable PWA — alpine.min.js is vendored rather than fetched
// from a CDN for precisely this reason, and it is still there.
function isAppAssetRequest(request) {
  return new URL(request.url).pathname.startsWith('/assets/');
}

// The library snapshots the fetchers write on a cron schedule.
//
// Fetched fresh for the same reason config.json is, and cached for the same
// reason too: a configuration with no snapshot to go with it starts the app
// offline and shows it an empty grid, which is indistinguishable from a library
// with no items — an ambiguity this project already treats as a defect.
function isJsonDataRequest(request) {
  return request.url.includes('/data/') && request.url.endsWith('.json');
}

// Check if request is for image files (these can be cached more aggressively)
function isImageDataRequest(request) {
  return request.url.includes('/data/') && request.url.endsWith('.jpg');
}

// Fetch event - serve from cache or network
self.addEventListener('fetch', (event) => {
  // Skip cross-origin requests
  if (!event.request.url.startsWith(self.location.origin)) {
    return;
  }

  // The generated configuration - the network and nothing else. Checked first,
  // before anything that could fall through to a caching strategy.
  if (isConfigRequest(event.request)) {
    event.respondWith(networkOnlyStrategy(event.request));
    return;
  }

  // The app shell - network first so an upgrade is picked up, cache as the
  // offline fallback.
  if (isAppShellRequest(event.request)) {
    event.respondWith(networkFirstWithCacheFallback(event.request));
    return;
  }

  // The app's stylesheets and scripts - the same strategy as the shell that
  // loads them, so the two cannot drift apart. See isAppAssetRequest().
  if (isAppAssetRequest(event.request)) {
    event.respondWith(networkFirstWithCacheFallback(event.request));
    return;
  }

  // The library snapshots - the same strategy as the configuration, so a client
  // that can start offline also has something to show.
  if (isJsonDataRequest(event.request)) {
    event.respondWith(networkOnlyWithOfflineFallback(event.request));
    return;
  }

  /* Artwork - stale-while-revalidate, and leave it that way.
   *
   * This is not a performance nicety any more, it is what makes an offline
   * start worth having: a cached snapshot renders with its posters instead of
   * as a grid of gaps. Artwork is addressed by a stable path and re-downloaded
   * by the fetchers only when its MD5 changes, so serving the held copy while
   * revalidating is exactly right for it. */
  if (isImageDataRequest(event.request)) {
    event.respondWith(staleWhileRevalidateStrategy(event.request));
    return;
  }

  // Other static assets - cache first, then network
  event.respondWith(cacheFirstStrategy(event.request));
});

/* Options for reading a cached copy back.
 *
 * `ignoreVary` because nginx has `gzip_vary on`, so every JSON response over a
 * kilobyte carries `Vary: Accept-Encoding`. Cache matching honours that by
 * default, which means a stored copy only answers a request whose
 * Accept-Encoding matches the one that fetched it. Those are the same browser
 * and normally do match — right up until they don't, and then the offline start
 * silently degrades into the configuration error this change exists to remove.
 * The URL is the whole identity of these files; the encoding is not part of it.
 */
const CACHE_MATCH_OPTIONS = { ignoreVary: true };

// The header that tells the page a response came from the cache rather than
// from the container. Read by the app to decide whether to show that it is
// running on saved data.
const FROM_CACHE_HEADER = 'X-Glimpse-From-Cache';

/* Re-wrap a cached response so the page can tell it apart from a live one.
 *
 * By the time a Response reaches the app it looks exactly like one the server
 * sent; this is the only place that knows otherwise. A header carries the fact
 * across without a second channel that has to be kept in step with this one.
 *
 * Rebuilt rather than mutated because a Response handed back by the Cache API
 * has an immutable headers guard, so setting a header on it throws. Buffered
 * rather than streamed because the first consumer is the parser-blocking
 * synchronous XHR in index.html, and these files are small.
 */
async function markAsCached(response) {
  const headers = new Headers(response.headers);
  headers.set(FROM_CACHE_HEADER, '1');
  return new Response(await response.blob(), {
    status: response.status,
    statusText: response.statusText,
    headers,
  });
}

/* Write a successful response to the cache that answers when the network is
 * gone. Successful only — an error or a malformed body must never become the
 * copy a later offline start is given.
 *
 * DYNAMIC_CACHE rather than CACHE_NAME, deliberately. This is received data,
 * not part of the precached shell, and the activate handler only spares the two
 * current names — so a cache-name bump evicts these alongside the assets they
 * belong with. Data that outlived a bump would be its own staleness bug, of
 * exactly the kind the v8.1 -> v8.2 note above describes.
 *
 * GET only, because the Cache API refuses to store a response to any other
 * method and throws rather than declining. This strategy serves requests the
 * app makes, so the guard is what keeps a future non-GET from turning a working
 * fetch into a rejected promise.
 */
async function cacheForOfflineUse(request, response) {
  if (request.method !== 'GET') {
    return;
  }
  const cache = await caches.open(DYNAMIC_CACHE);
  await cache.put(request, response);
}

/* The network, and nothing but. Serves /config.json.
 *
 * No cache read and no cache write, and both absences are the point rather than
 * an omission. The boot read of this file is a synchronous XHR that never
 * reaches this worker (see isConfigRequest), so a cache entry written here
 * could never be served to the one caller that matters — and live code that
 * cannot succeed is the exact shape of the defect this change removed. The
 * page retains its own copy; this route only keeps config.json off the
 * cache-first fallback.
 *
 * Its one rule is the shared one: whatever the container says is what the app
 * gets, and if the container says nothing the failure propagates. */
async function networkOnlyStrategy(request) {
  console.log('Fetching configuration:', request.url);
  return fetch(request, {
    cache: 'no-store', // Bypass all caches
    headers: {
      'Cache-Control': 'no-cache, no-store, must-revalidate',
      Pragma: 'no-cache',
      Expires: '0',
    },
  });
}

/* Network-only, with the last copy this client received as an OFFLINE fallback.
 *
 * Serves the library snapshots — what the app renders once it knows which
 * server it is browsing.
 *
 * The distinction it draws is the whole of this strategy, and it is invisible
 * on a working network:
 *
 *   fetch() throws        the request never reached the container. The network
 *                         is what failed and the server said nothing, so the
 *                         last copy this client received may answer.
 *   fetch() returns !ok   the container ANSWERED, and what it said was that
 *                         something is wrong. That answer is returned as-is.
 *   fetch() returns ok    returned, and written to the cache so the first
 *                         branch has something to serve later.
 *
 * A status is the server speaking; the absence of a status is the network.
 *
 * This used to fall back to cache on ANY non-OK response, which was inert only
 * because nothing ever populated the cache. Populating it — which is the rest
 * of this change — turns that line into a mechanism for hiding a container
 * whose entrypoint failed behind the last configuration that worked. That is
 * the oldest failure mode in this project, reached from a new direction, and it
 * is why the split is a spec requirement rather than an implementation detail.
 *
 * NOT called alwaysFreshStrategy any more. It answers from cache now, so that
 * name had stopped being true, and a name that lies is how the next person
 * reintroduces the bug.
 */
async function networkOnlyWithOfflineFallback(request) {
  try {
    console.log('Fetching fresh data:', request.url);
    const response = await fetch(request, {
      cache: 'no-store', // Bypass all caches
      headers: {
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        Pragma: 'no-cache',
        Expires: '0',
      },
    });

    if (response.ok) {
      console.log('Fresh data fetched successfully:', request.url);
      await cacheForOfflineUse(request, response.clone());
      return response;
    }

    // The container answered. Return what it said, whatever it said. Do not
    // look in the cache here — see the note above.
    console.log('Server answered with', response.status, 'for', request.url);
    return response;
  } catch (error) {
    console.log('Container unreachable, trying cache:', request.url);
    const cachedResponse = await caches.match(request, CACHE_MATCH_OPTIONS);
    if (cachedResponse) {
      return markAsCached(cachedResponse);
    }
    throw error;
  }
}

// Stale-while-revalidate strategy for images
async function staleWhileRevalidateStrategy(request) {
  const cache = await caches.open(DYNAMIC_CACHE);
  const cachedResponse = await cache.match(request);

  // Fetch fresh version in background
  const fetchPromise = fetch(request)
    .then((response) => {
      if (response.ok) {
        cache.put(request, response.clone());
      }
      return response;
    })
    .catch(() => {
      console.log('Background fetch failed for image:', request.url);
      return null;
    });

  // Return cached version immediately if available, otherwise wait for network
  if (cachedResponse) {
    console.log('Serving cached image while revalidating:', request.url);
    fetchPromise; // Fire and forget
    return cachedResponse;
  } else {
    console.log('No cached image, waiting for network:', request.url);
    return fetchPromise;
  }
}

/* A SECOND copy of the strategy above was declared here — back when it was
   called alwaysFreshStrategy() — with the same logic and different log strings.
   ESLint found it the first time this file was linted.

   In a classic worker the later declaration silently wins, so the FIRST one
   was dead code and any edit made to it did nothing at all. Removed rather
   than merged: there was nothing in it the survivor lacks. */

/* Network-first with cache fallback.
 *
 * Serves the app shell AND the stylesheets and scripts it loads. Those two used
 * to be split — a network-first shell over cache-first assets — which meant an
 * upgraded page ran on assets that could never be replaced. One strategy across
 * both is what keeps markup and behaviour from drifting apart.
 *
 * `caches.match()` searches every cache, so the fallback finds entries this
 * function wrote to DYNAMIC_CACHE and entries the install step precached under
 * CACHE_NAME alike. That is what keeps the app working offline: the assets are
 * still precached, and a failed fetch lands on them.
 *
 * Named for the strategy rather than for one caller, because it now has two. */
async function networkFirstWithCacheFallback(request) {
  try {
    console.log('Fetching from network:', request.url);
    /* `cache: 'reload'` — go past the browser's own HTTP cache, do not merely
       ask it politely.
       A plain fetch() consults that cache, so a client still holding an entry
       from before the Cache-Control fix keeps serving it until it expires on
       its original schedule. Correcting the header stops NEW responses being
       held; it cannot retract an entry the browser was already told to keep,
       and under the old `max-age=604800` that is up to a week of an upgraded
       app running week-old code. Bypassing here is what heals those clients on
       their next load instead. The response is still written to the caches
       below, so the offline fallback is unaffected. */
    const networkResponse = await fetch(request, { cache: 'reload' });

    if (networkResponse.ok) {
      // Update cache with fresh themed content
      await cacheForOfflineUse(request, networkResponse.clone());
      return networkResponse;
    }

    /* The container answered, and what it answered was an error. Return it.
     *
     * This branch used to consult the cache first, which is the same defect
     * that was in the strategy above and it is wrong here for the same reason:
     * a shell served from cache over a 500 hides a container whose entrypoint
     * failed behind the last page that loaded. The rule is one rule and it
     * holds for every strategy in this file — a cached copy answers for a
     * server that could not be reached, never for one that spoke. */
    console.log('Server answered with', networkResponse.status, 'for', request.url);
    return networkResponse;
  } catch (error) {
    console.log('Network request failed, trying cache:', request.url);

    // Try to get from cache
    const cachedResponse = await caches.match(request);
    if (cachedResponse) {
      return cachedResponse;
    }

    // If no cache and it's an HTML request, return offline page
    if (request.headers.get('Accept')?.includes('text/html')) {
      return caches.match('/offline.html');
    }

    throw error;
  }
}

// Cache-first strategy: try cache, fall back to network
async function cacheFirstStrategy(request) {
  const cachedResponse = await caches.match(request);
  if (cachedResponse) {
    return cachedResponse;
  }

  try {
    const networkResponse = await fetch(request);
    // Cache successful responses for next time
    if (networkResponse.ok) {
      await cacheForOfflineUse(request, networkResponse.clone());
    }
    return networkResponse;
  } catch (error) {
    console.error('Fetch failed:', error);
    // If it's an HTML request, return a simple offline page
    if (request.headers.get('Accept')?.includes('text/html')) {
      return caches.match('/offline.html');
    }
    // For other resources, just return the error
    throw error;
  }
}

// Clear specific cache types when receiving a message from the app.
//
// CLEAR_THEMED_CACHE was removed by `replace-boot-time-html-rewriting`. It
// existed because each server route was a physically different index.html, so
// switching servers could serve the previous server's page from cache — and the
// app had to race a cache-clearing handshake against a navigation to avoid it.
// The routes now return identical markup, themed from config.json at runtime, so
// there is no stale page to clear and no race to lose.
self.addEventListener('message', async (event) => {
  if (event.data && event.data.type === 'CLEAR_DATA_CACHE') {
    console.log('Service Worker: Clearing data cache');

    // Clear all data files from cache
    const cache = await caches.open(DYNAMIC_CACHE);
    const keys = await cache.keys();

    for (const request of keys) {
      if (request.url.includes('/data/')) {
        await cache.delete(request);
        console.log('Deleted from cache:', request.url);
      }
    }

    // Send confirmation back to the app
    event.ports[0]?.postMessage({ success: true });
  }

  if (event.data && event.data.type === 'CLEAR_ALL_CACHE') {
    console.log('Service Worker: Clearing all caches');

    const cacheNames = await caches.keys();
    for (const cacheName of cacheNames) {
      if (cacheName.startsWith('glimpse-media-')) {
        await caches.delete(cacheName);
        console.log('Deleted cache:', cacheName);
      }
    }

    // Send confirmation back to the app
    event.ports[0]?.postMessage({ success: true });
  }
});

/* A hardcoded copy of the offline page used to live here — the whole document,
   inlined as a template literal, plus a second `install` listener that cached it
   as a fallback if fetching /offline.html failed.

   It was a duplicate that had already gone stale. web/offline.html is themed
   from the design tokens and follows the active server; this copy had Plex
   orange (#e5a00d) hardcoded, so on the fallback path a Jellyfin or Emby install
   was shown the wrong brand — and the two files had to be edited together for
   that not to happen, which nothing enforced and nobody would notice.

   The page is now simply cached like any other static asset (see STATIC_ASSETS),
   so there is one offline page and it is the one in the repo. */
