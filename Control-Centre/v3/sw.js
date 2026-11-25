/* AIBO PWA shell. Never cache workspace content, credentials or /api responses. */
self.addEventListener('install', (event) => { event.waitUntil(self.skipWaiting()); });
self.addEventListener('activate', (event) => { event.waitUntil(self.clients.claim()); });
self.addEventListener('fetch', (event) => {
  const request = event.request;
  if (request.method !== 'GET') return;
  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;
  if (!url.pathname.startsWith('/v3/') || url.pathname.startsWith('/api/')) return;
  // Network only: installability does not imply offline data/AI execution.
  event.respondWith(fetch(request, { cache: 'no-store' }));
});
