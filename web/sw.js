// Service Worker for Glimpse Media Viewer

// Bumped from v7.3 by `replace-boot-time-html-rewriting`. The bump is
// load-bearing, not cosmetic: before this change each server route was a
// physically different index.html, so a client upgrading from v7.3 may hold a
// cached page with a theme and data paths baked into its markup. Those entries
// have to be discarded, and changing the cache name is what discards them.
const CACHE_NAME = "glimpse-media-viewer-v8.0";
const DYNAMIC_CACHE = "glimpse-media-dynamic-v8.0";

// Assets to cache on install.
//
// manifest.json is generated per-primary-server at container start, so it is
// cached under a version that changes when the scheme does — not held forever.
// (/test.html used to be here; it was a debug page the old entrypoint wrote
// into the web root, and it no longer exists.)
const STATIC_ASSETS = ["/manifest.json"];

// Install event - cache static assets
self.addEventListener("install", (event) => {
  console.log("Service Worker: Installing");
  event.waitUntil(
    caches
      .open(CACHE_NAME)
      .then((cache) => {
        console.log("Service Worker: Caching static files");
        return cache.addAll(STATIC_ASSETS);
      })
      .then(() => {
        console.log("Service Worker: All static assets added to cache");
        return self.skipWaiting(); // Ensure the new service worker activates right away
      })
  );
});

// Activate event - clean up old caches
self.addEventListener("activate", (event) => {
  console.log("Service Worker: Activating");
  event.waitUntil(
    caches
      .keys()
      .then((cacheNames) => {
        return Promise.all(
          cacheNames
            .filter((cacheName) => {
              return (
                cacheName.startsWith("glimpse-media-") &&
                cacheName !== CACHE_NAME &&
                cacheName !== DYNAMIC_CACHE
              );
            })
            .map((cacheName) => {
              console.log("Service Worker: Clearing old cache:", cacheName);
              return caches.delete(cacheName);
            })
        );
      })
      .then(() => {
        console.log("Service Worker: Claiming clients");
        return self.clients.claim(); // Take control of all clients
      })
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
    pathname === "/" ||
    pathname === "/index.html" ||
    /^\/(plex|jellyfin|emby)\/(index\.html)?$/.test(pathname)
  );
}

// The generated configuration. Never cached, and this check must come BEFORE
// the static-asset fallback: config.json does not live under /data/, so without
// it the request falls through to the cache-first strategy and a container
// restart with new settings would never be seen by an installed client.
function isConfigRequest(request) {
  return new URL(request.url).pathname === "/config.json";
}

// Check if request is for JSON data files (these need fresh data)
function isJsonDataRequest(request) {
  return request.url.includes("/data/") && request.url.endsWith(".json");
}

// Check if request is for image files (these can be cached more aggressively)
function isImageDataRequest(request) {
  return request.url.includes("/data/") && request.url.endsWith(".jpg");
}

// Check if request is for dynamic media data
function isMediaDataRequest(request) {
  return isJsonDataRequest(request) || isImageDataRequest(request);
}

// Fetch event - serve from cache or network
self.addEventListener("fetch", (event) => {
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
    console.log("Fetching fresh data:", request.url);
    const response = await fetch(request, {
      cache: "no-store", // Bypass all caches
      headers: {
        "Cache-Control": "no-cache, no-store, must-revalidate",
        Pragma: "no-cache",
        Expires: "0",
      },
    });

    if (response.ok) {
      console.log("Fresh data fetched successfully:", request.url);
      return response;
    }

    // If fresh fetch fails, try cache as fallback
    console.log("Fresh fetch failed, trying cache:", request.url);
    const cachedResponse = await caches.match(request);
    return cachedResponse || response;
  } catch (error) {
    console.log("Network error, trying cache:", request.url);
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
    .catch((error) => {
      console.log("Background fetch failed for image:", request.url);
      return null;
    });

  // Return cached version immediately if available, otherwise wait for network
  if (cachedResponse) {
    console.log("Serving cached image while revalidating:", request.url);
    fetchPromise; // Fire and forget
    return cachedResponse;
  } else {
    console.log("No cached image, waiting for network:", request.url);
    return fetchPromise;
  }
}

// Always fetch fresh strategy for JSON data (no caching)
async function alwaysFreshStrategy(request) {
  try {
    console.log("Fetching fresh JSON data:", request.url);
    const response = await fetch(request, {
      cache: "no-store", // Bypass all browser caches
      headers: {
        "Cache-Control": "no-cache, no-store, must-revalidate",
        Pragma: "no-cache",
      },
    });

    if (response.ok) {
      console.log("Fresh JSON data fetched successfully:", request.url);
      return response;
    }

    // If fresh fetch fails, try cache as last resort
    console.log("Fresh fetch failed, trying cache:", request.url);
    const cachedResponse = await caches.match(request);
    return cachedResponse || response;
  } catch (error) {
    console.log("Network error for JSON, trying cache:", request.url);
    const cachedResponse = await caches.match(request);
    if (cachedResponse) {
      return cachedResponse;
    }
    throw error;
  }
}

// Network-first with cache fallback for themed HTML
async function networkFirstWithCacheFallback(request) {
  try {
    console.log("Fetching themed HTML from network:", request.url);
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
      console.log("Network failed, serving cached themed HTML:", request.url);
      return cachedResponse;
    }

    return networkResponse; // Return the error response
  } catch (error) {
    console.log(
      "Network request failed for themed HTML, trying cache:",
      request.url
    );

    // Try to get from cache
    const cachedResponse = await caches.match(request);
    if (cachedResponse) {
      return cachedResponse;
    }

    // If no cache and it's an HTML request, return offline page
    if (request.headers.get("Accept")?.includes("text/html")) {
      return caches.match("/offline.html");
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
    console.error("Fetch failed:", error);
    // If it's an HTML request, return a simple offline page
    if (request.headers.get("Accept")?.includes("text/html")) {
      return caches.match("/offline.html");
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
self.addEventListener("message", async (event) => {
  if (event.data && event.data.type === "CLEAR_DATA_CACHE") {
    console.log("Service Worker: Clearing data cache");

    // Clear all data files from cache
    const cache = await caches.open(DYNAMIC_CACHE);
    const keys = await cache.keys();

    for (const request of keys) {
      if (request.url.includes("/data/")) {
        await cache.delete(request);
        console.log("Deleted from cache:", request.url);
      }
    }

    // Send confirmation back to the app
    event.ports[0]?.postMessage({ success: true });
  }

  if (event.data && event.data.type === "CLEAR_ALL_CACHE") {
    console.log("Service Worker: Clearing all caches");

    const cacheNames = await caches.keys();
    for (const cacheName of cacheNames) {
      if (cacheName.startsWith("glimpse-media-")) {
        await caches.delete(cacheName);
        console.log("Deleted cache:", cacheName);
      }
    }

    // Send confirmation back to the app
    event.ports[0]?.postMessage({ success: true });
  }
});

// Simple offline fallback page
const OFFLINE_HTML = `
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Offline - Glimpse Media Viewer</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
            background-color: #1a1a1a;
            color: #fff;
            text-align: center;
            padding: 40px 20px;
            margin: 0;
            height: 100vh;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
        }
        .container {
            max-width: 500px;
        }
        h1 {
            color: #e5a00d;
            margin-bottom: 20px;
        }
        p {
            font-size: 18px;
            line-height: 1.6;
            margin-bottom: 30px;
        }
        .icon {
            font-size: 64px;
            margin-bottom: 30px;
        }
        button {
            background-color: #e5a00d;
            color: #000;
            border: none;
            padding: 12px 20px;
            border-radius: 24px;
            font-weight: bold;
            cursor: pointer;
            font-size: 16px;
            transition: background-color 0.3s;
        }
        button:hover {
            background-color: #f1b020;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="icon">📶</div>
        <h1>You're Offline</h1>
        <p>It looks like you're not connected to the internet. Glimpse Media Viewer needs a connection to show your media content.</p>
        <button onclick="window.location.reload()">Try Again</button>
    </div>
</body>
</html>
`;

// Create offline page on install
self.addEventListener("install", (event) => {
  const offlineRequest = new Request("/offline.html");
  event.waitUntil(
    fetch(offlineRequest)
      .catch(() => {
        return new Response(OFFLINE_HTML, {
          headers: { "Content-Type": "text/html" },
        });
      })
      .then((response) => {
        return caches.open(CACHE_NAME).then((cache) => {
          return cache.put(offlineRequest, response);
        });
      })
  );
});
