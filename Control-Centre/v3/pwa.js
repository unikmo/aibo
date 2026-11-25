/* Installable desktop-window experience without Store/Developer publisher accounts. */
(function () {
  'use strict';
  const eligible = location.protocol === 'https:' ||
    ['localhost', '127.0.0.1'].includes(location.hostname);
  if (!eligible || !('serviceWorker' in navigator)) return;
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/v3/sw.js', {scope: '/v3/'})
      .catch((error) => console.warn('AIBO installable-app support unavailable:', error));
  });
})();
