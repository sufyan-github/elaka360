/* Elaka360 service worker — hand-written, no build step.
 *
 * Bump VERSION whenever this file's caching behaviour or the precache list changes: every cache whose
 * name doesn't end in the current version is deleted on activate.
 *
 * Privacy rules (do not loosen without review):
 *  - only same-origin GET requests are handled; everything else (POST, map tiles, analytics) goes straight
 *    to the network untouched;
 *  - nothing under NEVER_CACHE is ever read from or written to a cache (auth, personal pages, API proxies);
 *    /api/* is not intercepted at all, and personal pages are network-only (offline → the /offline page);
 *  - a response with `Cache-Control: private` or `no-store` is never stored at runtime, unless the server
 *    explicitly marks it public with `X-E360-Cache: public` (Next.js sends `private, no-store` on every
 *    dynamically rendered page, so that marker is how public dynamic pages opt in);
 *  - pages with a query string are not stored (search terms and coordinates stay out of the cache);
 *  - the precache is fetched with `credentials: 'omit'`, so it can never contain a signed-in view.
 *
 * Locales: Bangla pages live at `/…`, English at `/en/…`. Path rules (NEVER_CACHE) apply to both, and an
 * English page that cannot load falls back to `/en/offline`.
 */
const VERSION = 'v2';
const PRECACHE = `e360-precache-${VERSION}`;
const PAGES = `e360-pages-${VERSION}`;
const STATIC = `e360-static-${VERSION}`;
const DATA = `e360-data-${VERSION}`;
const CURRENT = [PRECACHE, PAGES, STATIC, DATA];

const OFFLINE_URL = '/offline';
const OFFLINE_URL_EN = '/en/offline';
/** Must succeed for the install to succeed. */
const PRECACHE_REQUIRED = [OFFLINE_URL, OFFLINE_URL_EN, '/data/hotlines.json', '/icons/icon-192.png', '/manifest.webmanifest'];
/** Best effort: server-rendered pages that need the API; a failure here must not block install. */
const PRECACHE_OPTIONAL = ['/emergency', '/en/emergency'];

const NEVER_CACHE = ['/api', '/login', '/me', '/saved', '/contribute', '/admin', '/auth'];
const NAV_TIMEOUT_MS = 4000;
const MAX_PAGES = 40;
const MAX_STATIC = 200;
const MAX_DATA = 60;

/* ------------------------------------------------------------------------------------------------ */

/** `/en/me` → `/me`: locale-less path, so the same rules cover both languages. */
function unlocalized(pathname) {
  return pathname === '/en' ? '/' : pathname.startsWith('/en/') ? pathname.slice(3) : pathname;
}

function isEnglish(pathname) {
  return pathname === '/en' || pathname.startsWith('/en/');
}

function isNeverCache(pathname) {
  const p0 = unlocalized(pathname);
  return NEVER_CACHE.some((p) => p0 === p || p0.startsWith(p + '/'));
}

function isStorable(res) {
  if (!res || !res.ok || res.status !== 200 || res.type === 'opaque') return false;
  const cc = (res.headers.get('cache-control') || '').toLowerCase();
  if (/\b(no-store|private)\b/.test(cc) && res.headers.get('x-e360-cache') !== 'public') return false;
  if (res.headers.has('set-cookie')) return false; // not readable by JS normally, but never store it if it is
  return true;
}

// Matches use ignoreVary: Next.js varies pages on RSC/router headers, which never apply to the requests we store.

/** Copy of a cached response with `X-From-Cache: 1`, also clearing the `redirected` flag. */
async function markFromCache(res) {
  const headers = new Headers(res.headers);
  headers.set('X-From-Cache', '1');
  const body = await res.blob();
  return new Response(body, { status: res.status, statusText: res.statusText, headers });
}

async function trim(cacheName, max) {
  const cache = await caches.open(cacheName);
  const keys = await cache.keys();
  for (let i = 0; i < keys.length - max; i++) await cache.delete(keys[i]);
}

async function put(cacheName, request, res, max) {
  const cache = await caches.open(cacheName);
  await cache.put(request, res);
  await trim(cacheName, max);
}

async function precache() {
  const cache = await caches.open(PRECACHE);
  const get = (url) =>
    fetch(new Request(url, { credentials: 'omit', cache: 'reload' })).then((res) => {
      if (!res.ok) throw new Error(`precache ${url}: ${res.status}`);
      return cache.put(url, res);
    });
  await Promise.all(PRECACHE_REQUIRED.map(get));
  await Promise.all(PRECACHE_OPTIONAL.map((url) => get(url).catch(() => undefined)));
}

/* ------------------------------------------------------------------------------------------------ */
/* Lifecycle */

self.addEventListener('install', (event) => {
  // No skipWaiting() here: an update waits until the page's "refresh" banner sends SKIP_WAITING.
  event.waitUntil(precache());
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    (async () => {
      const names = await caches.keys();
      await Promise.all(names.filter((n) => n.startsWith('e360-') && !CURRENT.includes(n)).map((n) => caches.delete(n)));
      if (self.registration.navigationPreload) await self.registration.navigationPreload.enable().catch(() => undefined);
      await self.clients.claim();
    })(),
  );
});

/** Client ids whose page was answered from the cache (so the page can show "may be outdated"). */
const servedFromCache = new Set();

self.addEventListener('message', (event) => {
  const data = event.data || {};
  if (data.type === 'SKIP_WAITING') self.skipWaiting();
  else if (data.type === 'GET_PAGE_SOURCE' && event.source) {
    const id = event.source.id;
    event.source.postMessage({ type: 'PAGE_SOURCE', fromCache: servedFromCache.has(id) });
    servedFromCache.delete(id);
  }
});

/* ------------------------------------------------------------------------------------------------ */
/* Strategies */

async function cachedPage(request) {
  return (await caches.match(request, { cacheName: PAGES, ignoreVary: true })) || (await caches.match(request, { cacheName: PRECACHE, ignoreVary: true }));
}

/** Navigation: network first (4 s), then the cached copy of this page, then /offline. */
async function networkFirstPage(event) {
  const { request } = event;
  const url = new URL(request.url);
  const storable = !url.search && !isNeverCache(url.pathname);
  const fromCache = async () => {
    const hit = storable ? await cachedPage(request) : undefined;
    if (hit) {
      if (event.resultingClientId) servedFromCache.add(event.resultingClientId);
      return markFromCache(hit);
    }
    return undefined;
  };

  const network = (async () => {
    const preloaded = await event.preloadResponse;
    const res = preloaded || (await fetch(request));
    if (storable && isStorable(res)) event.waitUntil(put(PAGES, url.pathname, res.clone(), MAX_PAGES));
    return res;
  })();

  let timer;
  const timeout = new Promise((resolve) => {
    timer = setTimeout(() => resolve('timeout'), NAV_TIMEOUT_MS);
  });

  try {
    const first = await Promise.race([network, timeout]);
    if (first !== 'timeout') {
      clearTimeout(timer);
      if (first.status >= 500) return (await fromCache()) || first;
      return first;
    }
    // Slow network: show the cached copy if there is one, otherwise keep waiting.
    event.waitUntil(network.catch(() => undefined)); // still refresh the cache in the background
    return (await fromCache()) || (await network);
  } catch {
    clearTimeout(timer);
    return (await fromCache()) || offlineFallback(url.pathname);
  }
}

/** The precached offline page in the request's language (status 503), or plain text if even that is missing. */
async function offlineFallback(pathname) {
  const english = isEnglish(pathname || '/');
  const offline =
    (await caches.match(english ? OFFLINE_URL_EN : OFFLINE_URL, { cacheName: PRECACHE, ignoreVary: true })) ||
    (await caches.match(OFFLINE_URL, { cacheName: PRECACHE, ignoreVary: true }));
  if (offline) {
    const res = await markFromCache(offline);
    return new Response(res.body, { status: 503, statusText: 'Offline', headers: res.headers });
  }
  const text = english ? 'Offline — no internet connection.' : 'অফলাইন — ইন্টারনেট সংযোগ নেই।';
  return new Response(text, { status: 503, headers: { 'Content-Type': 'text/plain; charset=utf-8' } });
}

/** Personal pages (/me, /login, …): network only, nothing stored; offline → the /offline page. */
async function networkOnlyPage(event) {
  try {
    return (await event.preloadResponse) || (await fetch(event.request));
  } catch {
    return offlineFallback(new URL(event.request.url).pathname);
  }
}

/** Hashed build assets and icons: cache first. */
async function cacheFirst(request, cacheName, max) {
  const hit = (await caches.match(request, { cacheName, ignoreVary: true })) || (await caches.match(request, { cacheName: PRECACHE, ignoreVary: true }));
  if (hit) return hit;
  const res = await fetch(request);
  if (isStorable(res)) await put(cacheName, request, res.clone(), max);
  return res;
}

/** Public JSON (boundaries, hotlines): serve the cached copy immediately, refresh it in the background. */
async function staleWhileRevalidate(event, cacheName, max) {
  const { request } = event;
  const hit = (await caches.match(request, { cacheName, ignoreVary: true })) || (await caches.match(request, { cacheName: PRECACHE, ignoreVary: true }));
  const refresh = fetch(request).then(async (res) => {
    if (isStorable(res)) await put(cacheName, request, res.clone(), max);
    return res;
  });
  if (hit) {
    event.waitUntil(refresh.catch(() => undefined));
    return markFromCache(hit);
  }
  return refresh;
}

/* ------------------------------------------------------------------------------------------------ */

self.addEventListener('fetch', (event) => {
  const { request } = event;
  if (request.method !== 'GET') return;
  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return; // third-party (map tiles, fonts CDN): browser default
  if (url.pathname === '/api' || url.pathname.startsWith('/api/')) return; // API proxies: never touched
  if (request.headers.has('range')) return;

  if (request.mode === 'navigate') {
    event.respondWith(isNeverCache(url.pathname) ? networkOnlyPage(event) : networkFirstPage(event));
    return;
  }
  if (isNeverCache(url.pathname)) return;
  // Next.js client-side navigations (RSC payloads) and prefetches: network only, never cached.
  if (request.headers.get('rsc') || request.headers.get('next-router-prefetch') || url.searchParams.has('_rsc')) return;

  if (url.pathname.startsWith('/_next/static/')) {
    event.respondWith(cacheFirst(request, STATIC, MAX_STATIC));
  } else if (url.pathname.startsWith('/icons/')) {
    event.respondWith(cacheFirst(request, STATIC, MAX_STATIC));
  } else if (/^\/(geo|data)\/[^/]+\.json$/.test(url.pathname)) {
    event.respondWith(staleWhileRevalidate(event, DATA, MAX_DATA));
  } else if (url.pathname === '/manifest.webmanifest') {
    event.respondWith(fetch(request).catch(async () => (await caches.match(request, { cacheName: PRECACHE, ignoreVary: true })) || Response.error()));
  }
  // Anything else: not intercepted.
});
