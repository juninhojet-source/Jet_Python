/**
 * Service Worker do SIGAZ
 * Estratégia: network-first para HTML/API, cache-first para assets estáticos.
 */
const CACHE_VERSION = 'sigaz-v5';
const ASSETS = [
  '/css/app.css',
  '/css/login.css',
  '/js/comum.js',
  '/js/mascaras.js',
  '/assets/brasao.png',
  '/assets/brasao_small.png'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_VERSION)
      .then(cache => cache.addAll(ASSETS))
      .catch(err => console.warn('[SW] Falha ao popular cache:', err))
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE_VERSION).map(k => caches.delete(k)))
    )
  );
  self.clients.claim();
});

/**
 * Verifica se a requisição pode ser cacheada.
 * A Cache API só aceita http(s):// — qualquer outro scheme (chrome-extension://,
 * data:, blob:, file:, etc.) gera TypeError. Filtramos aqui antes de cachear.
 */
function podeCachear(request) {
  if (request.method !== 'GET') return false;
  const url = request.url;
  return url.startsWith('http://') || url.startsWith('https://');
}

/**
 * Encapsula put no cache de forma segura — nunca lança exceção mesmo se
 * a Cache API rejeitar (ex.: requisição de extensão, resposta opaca, etc.)
 */
function cachearSeguro(cacheName, request, response) {
  if (!podeCachear(request)) return;
  if (!response || !response.ok) return;
  try {
    const clone = response.clone();
    caches.open(cacheName)
      .then(cache => cache.put(request, clone))
      .catch(err => console.warn('[SW] put falhou (ignorado):', err.message));
  } catch (err) {
    // Ignora silenciosamente
  }
}

self.addEventListener('fetch', (event) => {
  // 1) Só GET é interceptado
  if (event.request.method !== 'GET') return;

  // 2) Só http/https — ignora chrome-extension://, devtools://, ws://, etc.
  if (!event.request.url.startsWith('http://') && !event.request.url.startsWith('https://')) {
    return;
  }

  let url;
  try {
    url = new URL(event.request.url);
  } catch {
    return;
  }

  // 3) Origem diferente (ViaCEP, OSM, CDN) — deixa o navegador resolver direto
  if (url.origin !== self.location.origin) return;

  // 4) Chamadas à API — sempre rede, nunca cache
  if (url.pathname.startsWith('/api/')) return;

  // 5) Assets estáticos: cache-first
  if (url.pathname.startsWith('/assets/') ||
      url.pathname.startsWith('/css/') ||
      url.pathname.startsWith('/js/')) {
    event.respondWith(
      caches.match(event.request).then(cached => {
        if (cached) return cached;
        return fetch(event.request).then(res => {
          cachearSeguro(CACHE_VERSION, event.request, res);
          return res;
        }).catch(() => caches.match(event.request));
      })
    );
    return;
  }

  // 6) HTML e demais: network-first com fallback ao cache
  event.respondWith(
    fetch(event.request).then(res => {
      cachearSeguro(CACHE_VERSION, event.request, res);
      return res;
    }).catch(() => caches.match(event.request))
  );
});
