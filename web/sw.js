// Service Worker for Glimpse Media Viewer

// Bumped from v7.3 by `replace-boot-time-html-rewriting`. The bump is
// load-bearing, not cosmetic: before this change each server route was a
// physically different index.html, so a client upgrading from v7.3 may hold a
// cached page with a theme and data paths baked into its markup. Those entries
// have to be discarded, and changing the cache name is what discards them.
const CACHE_NAME = 'glimpse-media-viewer-v8.1';
const DYNAMIC_CACHE = 'glimpse-media-dynamic-v8.1';

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
        return cache.addAll(STATIC_ASSETS);
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

// The generated configuration. Never cached, and this check must come BEFORE
// the static-asset fallback: config.json does not live under /data/, so without
// it the request falls through to the cache-first strategy and a container
// restart with new settings would never be seen by an installed client.
function isConfigRequest(request) {
  return new URL(request.url).pathname === '/config.json';
}

// Check if request is for JSON data files (these need fresh data)
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

  // The generated configuration - never cached. Checked first, before anything
  // that could fall through to a caching strategy.
  if (isConfigRequest(event.request)) {
    event.respondWith(alwaysFreshStrategy(event.request));
    return;
  }

  // The app shell - network first so an upgrade is picked up, cache as the
  // offline fallback.
  if (isAppShellRequest(event.request)) {
    event.respondWith(networkFirstWithCacheFallback(event.request));
    return;
  }

  // JSON data files - always fetch fresh (no caching)
  if (isJsonDataRequest(event.request)) {
    event.respondWith(alwaysFreshStrategy(event.request));
    return;
  }

  // Image files - use stale-while-revalidate for better performance
  if (isImageDataRequest(event.request)) {
    event.respondWith(staleWhileRevalidateStrategy(event.request));
    return;
  }

  // Other static assets - cache first, then network
  event.respondWith(cacheFirstStrategy(event.request));
});

// Always fetch fresh strategy for JSON data
async function alwaysFreshStrategy(request) {
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
      return response;
    }

    // If fresh fetch fails, try cache as fallback
    console.log('Fresh fetch failed, trying cache:', request.url);
    const cachedResponse = await caches.match(request);
    return cachedResponse || response;
  } catch (error) {
    console.log('Network error, trying cache:', request.url);
    const cachedResponse = await caches.match(request);
    if (cachedResponse) {
      return cachedResponse;
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

/* A SECOND alwaysFreshStrategy() was declared here — the same logic as the
   one above, differing only in its log strings. ESLint found it the first
   time this file was linted.

   In a classic worker the later declaration silently wins, so the FIRST one
   was dead code and any edit made to it did nothing at all. Removed rather
   than merged: there was nothing in it the survivor lacks. */

// Network-first with cache fallback for themed HTML
async function networkFirstWithCacheFallback(request) {
  try {
    console.log('Fetching themed HTML from network:', request.url);
    const networkResponse = await fetch(request);

    if (networkResponse.ok) {
      // Update cache with fresh themed content
      const cache = await caches.open(DYNAMIC_CACHE);
      cache.put(request, networkResponse.clone());
      return networkResponse;
    }

    // If network fails, try cache
    const cachedResponse = await caches.match(request);
    if (cachedResponse) {
      console.log('Network failed, serving cached themed HTML:', request.url);
      return cachedResponse;
    }

    return networkResponse; // Return the error response
  } catch (error) {
    console.log('Network request failed for themed HTML, trying cache:', request.url);

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
      const cache = await caches.open(DYNAMIC_CACHE);
      cache.put(request, networkResponse.clone());
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
