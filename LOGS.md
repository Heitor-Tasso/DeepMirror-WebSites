
> palmer.dinnerware

- Console Python:
```
Nenhum
```

- Console Web:
```
(index):377 [Fetch Interceptor] Installed with 286 mappings
(index):378 [Fetch Interceptor] Basename index: 286 files
(index):1 Unchecked runtime.lastError: The message port closed before a response was received.
gsap.min.js:10 GSAP target  not found. https://gsap.com
T @ gsap.min.js:10
gsap.min.js:10 GSAP target  not found. https://gsap.com
T @ gsap.min.js:10
about:blank:1 Unchecked runtime.lastError: The message port closed before a response was received.
index.mjs:327 Uncaught TypeError: Cannot read properties of null (reading 'querySelectorAll')
    at Home.initFilters (index.mjs:327:42)
    at new Home (index.mjs:45:10)
    at index.mjs:4988:1
gsap.min.js:10 GSAP target  not found. https://gsap.com
T @ gsap.min.js:10
gsap.min.js:10 GSAP target  not found. https://gsap.com
T @ gsap.min.js:10
gsap.min.js:10 GSAP target  not found. https://gsap.com
T @ gsap.min.js:10
gsap.min.js:10 GSAP target  not found. https://gsap.com
T @ gsap.min.js:10
```

Esse site parece funcionar bem, mas por algum motivo os elementos 3d que eram para aprecer estão invisíveis mesmo que passando por cima aparece uma label incicando que eles estão lá. O fundo está 100% branco sendo que era para ter elementos na página. E estão faltando as animações.

> landonorris.store

- Console Python:
```
----------------------------------------
Exception occurred during processing of request from ('127.0.0.1', 47992)
Traceback (most recent call last):
  File "/usr/lib/python3.12/socketserver.py", line 318, in _handle_request_noblock
    self.process_request(request, client_address)
  File "/usr/lib/python3.12/socketserver.py", line 349, in process_request
    self.finish_request(request, client_address)
  File "/usr/lib/python3.12/socketserver.py", line 362, in finish_request
    self.RequestHandlerClass(request, client_address, self)
  File "/usr/lib/python3.12/http/server.py", line 672, in __init__
    super().__init__(*args, **kwargs)
  File "/usr/lib/python3.12/socketserver.py", line 761, in __init__
    self.handle()
  File "/usr/lib/python3.12/http/server.py", line 436, in handle
    self.handle_one_request()
  File "/usr/lib/python3.12/http/server.py", line 424, in handle_one_request
    method()
  File "/home/htasso/Downloads/sotahtech/DeepMirror-WebSites/downloads/landonorris.store/raw/serve.py", line 93, in do_GET
    super().do_GET()
  File "/usr/lib/python3.12/http/server.py", line 679, in do_GET
    self.copyfile(f, self.wfile)
  File "/usr/lib/python3.12/http/server.py", line 878, in copyfile
    shutil.copyfileobj(source, outputfile)
  File "/usr/lib/python3.12/shutil.py", line 204, in copyfileobj
    fdst_write(buf)
  File "/usr/lib/python3.12/socketserver.py", line 840, in write
    self._sock.sendall(b)
ConnectionResetError: [Errno 104] Connection reset by peer
----------------------------------------
127.0.0.1 - - [11/Mar/2026 08:33:23] code 404, message File not found
127.0.0.1 - - [11/Mar/2026 08:33:23] "GET /cdn/shop/t/119/assets/component-predictive-search.css.map?v=165644661289088488651758883165 HTTP/1.1" 404 -
127.0.0.1 - - [11/Mar/2026 08:33:23] code 404, message File not found
127.0.0.1 - - [11/Mar/2026 08:33:23] "GET /cdn/shop/t/119/assets/base.css.map?v=49735997935341061081758883161 HTTP/1.1" 404 -
```

- Console Web:
```
(index):1 Unchecked runtime.lastError: The message port closed before a response was received.
(index):402 [Fetch Interceptor] Installed with 744 mappings
(index):403 [Fetch Interceptor] Basename index: 740 files
[Intervention] Slow network is detected. See <URL> for more details. Fallback font will be used while loading: <URL>
(index):326 [Fetch Interceptor] ✓ https://shop.app/pay/session?v=1 -> assets/session_69e69925bcdb.json
(index):331 [Fetch Interceptor] ✗ Blocked tracking call: https://landonorris.store/api/collect
window.fetch @ (index):331
(index):331 [Fetch Interceptor] ✗ Blocked tracking call: https://monorail-edge.shopifysvc.com/v1/produce
window.fetch @ (index):331
about:blank:1 Unchecked runtime.lastError: The message port closed before a response was received.
(index):266 [DOM Interceptor] ✓ script //landonorris.store/cdn/shop/t/119/assets/node_modules_body-scroll-lock_lib_bodyScrollLock_esm_js.min.js -> assets/cdn/shop/t/119/assets/node_modules_body-scroll-lock_lib_bodyScrollLock_esm_js.min.js
radiant_58cce9565a3c.js:3 Unknown config option(s) passed usingSettingsFor
e._validateConfig @ radiant_58cce9565a3c.js:3
radiant_58cce9565a3c.js:3 Trying to initialise Choices on element already initialised Object
e @ radiant_58cce9565a3c.js:3
(index):266 [DOM Interceptor] ✓ script //landonorris.store/cdn/shop/t/119/assets/vendors-node_modules_scrollreveal_dist_scrollreveal_es_js.min.js -> assets/cdn/shop/t/119/assets/vendors-node_modules_scrollreveal_dist_scrollreveal_es_js.min.js
radiant_58cce9565a3c.js:1 CART ITEMS
radiant_58cce9565a3c.js:1 Object
Framing 'https://shop.app/' violates the following Content Security Policy directive: "frame-ancestors https://lando-norris-shop.myshopify.com https://shop.landonorris.com https://basketball.landonorris.com https://lando-norris-shop.account.myshopify.com https://store.landonorris.com https://landonorris.store https://www.landonorris.store https://lando.store https://www.lando.store https://shopify.com". The request has been blocked.

(index):331 [Fetch Interceptor] ✗ Blocked tracking call: https://landonorris.store/api/collect
window.fetch @ (index):331
sendBeacon @ shopify-perf-kit-3.3.0.min.js:1
checkAndSendSignals @ shopify-perf-kit-3.3.0.min.js:1
processAndSendSignals @ shopify-perf-kit-3.3.0.min.js:1
<computed>.<computed>.<computed>.<computed>.<computed>.<computed>.<computed>.<computed>.timeout @ shopify-perf-kit-3.3.0.min.js:1
requestIdleCallback
i @ shopify-perf-kit-3.3.0.min.js:1
(index):331 [Fetch Interceptor] ✗ Blocked tracking call: https://landonorris.store/api/collect
window.fetch @ (index):331
sendBeacon @ shopify-perf-kit-3.3.0.min.js:1
checkAndSendSignals @ shopify-perf-kit-3.3.0.min.js:1
processAndSendSignals @ shopify-perf-kit-3.3.0.min.js:1
<computed>.<computed>.<computed>.<computed>.<computed>.<computed>.<computed>.<computed>.timeout @ shopify-perf-kit-3.3.0.min.js:1
requestIdleCallback
i @ shopify-perf-kit-3.3.0.min.js:1
setTimeout
t @ shopify-perf-kit-3.3.0.min.js:1
(anonymous) @ shopify-perf-kit-3.3.0.min.js:1
Promise.then
<computed>.<computed>.<computed>.<computed>.<computed>.<computed>.<computed>.<computed>.timeout @ shopify-perf-kit-3.3.0.min.js:1
requestIdleCallback
i @ shopify-perf-kit-3.3.0.min.js:1
setTimeout
t @ shopify-perf-kit-3.3.0.min.js:1
(anonymous) @ shopify-perf-kit-3.3.0.min.js:1
Promise.then
<computed>.<computed>.<computed>.<computed>.<computed>.<computed>.<computed>.<computed>.timeout @ shopify-perf-kit-3.3.0.min.js:1
requestIdleCallback
i @ shopify-perf-kit-3.3.0.min.js:1
setTimeout
t @ shopify-perf-kit-3.3.0.min.js:1
(anonymous) @ shopify-perf-kit-3.3.0.min.js:1
Promise.then
<computed>.<computed>.<computed>.<computed>.<computed>.<computed>.<computed>.<computed>.timeout @ shopify-perf-kit-3.3.0.min.js:1
requestIdleCallback
i @ shopify-perf-kit-3.3.0.min.js:1
setTimeout
t @ shopify-perf-kit-3.3.0.min.js:1
(anonymous) @ shopify-perf-kit-3.3.0.min.js:1
Promise.then
<computed>.<computed>.<computed>.<computed>.<computed>.<computed>.<computed>.<computed>.timeout @ shopify-perf-kit-3.3.0.min.js:1
requestIdleCallback
i @ shopify-perf-kit-3.3.0.min.js:1
(index):331 [Fetch Interceptor] ✗ Blocked tracking call: https://landonorris.store/api/collect
window.fetch @ (index):331
sendBeacon @ shopify-perf-kit-3.3.0.min.js:1
checkAndSendSignals @ shopify-perf-kit-3.3.0.min.js:1
processAndSendSignals @ shopify-perf-kit-3.3.0.min.js:1
<computed>.<computed>.<computed>.<computed>.<computed>.<computed>.<computed>.<computed>.timeout @ shopify-perf-kit-3.3.0.min.js:1
requestIdleCallback
i @ shopify-perf-kit-3.3.0.min.js:1
setTimeout
t @ shopify-perf-kit-3.3.0.min.js:1
(anonymous) @ shopify-perf-kit-3.3.0.min.js:1
Promise.then
<computed>.<computed>.<computed>.<computed>.<computed>.<computed>.<computed>.<computed>.timeout @ shopify-perf-kit-3.3.0.min.js:1
requestIdleCallback
i @ shopify-perf-kit-3.3.0.min.js:1
setTimeout
t @ shopify-perf-kit-3.3.0.min.js:1
(anonymous) @ shopify-perf-kit-3.3.0.min.js:1
Promise.then
<computed>.<computed>.<computed>.<computed>.<computed>.<computed>.<computed>.<computed>.timeout @ shopify-perf-kit-3.3.0.min.js:1
requestIdleCallback
i @ shopify-perf-kit-3.3.0.min.js:1
setTimeout
t @ shopify-perf-kit-3.3.0.min.js:1
(anonymous) @ shopify-perf-kit-3.3.0.min.js:1
Promise.then
<computed>.<computed>.<computed>.<computed>.<computed>.<computed>.<computed>.<computed>.timeout @ shopify-perf-kit-3.3.0.min.js:1
requestIdleCallback
i @ shopify-perf-kit-3.3.0.min.js:1
setTimeout
t @ shopify-perf-kit-3.3.0.min.js:1
(anonymous) @ shopify-perf-kit-3.3.0.min.js:1
Promise.then
<computed>.<computed>.<computed>.<computed>.<computed>.<computed>.<computed>.<computed>.timeout @ shopify-perf-kit-3.3.0.min.js:1
requestIdleCallback
i @ shopify-perf-kit-3.3.0.min.js:1
setTimeout
t @ shopify-perf-kit-3.3.0.min.js:1
(anonymous) @ shopify-perf-kit-3.3.0.min.js:1
Promise.then
<computed>.<computed>.<computed>.<computed>.<computed>.<computed>.<computed>.<computed>.timeout @ shopify-perf-kit-3.3.0.min.js:1
requestIdleCallback
i @ shopify-perf-kit-3.3.0.min.js:1
setTimeout
t @ shopify-perf-kit-3.3.0.min.js:1
(anonymous) @ shopify-perf-kit-3.3.0.min.js:1
Promise.then
<computed>.<computed>.<computed>.<computed>.<computed>.<computed>.<computed>.<computed>.timeout @ shopify-perf-kit-3.3.0.min.js:1
requestIdleCallback
i @ shopify-perf-kit-3.3.0.min.js:1
setTimeout
t @ shopify-perf-kit-3.3.0.min.js:1
(anonymous) @ shopify-perf-kit-3.3.0.min.js:1
Promise.then
<computed>.<computed>.<computed>.<computed>.<computed>.<computed>.<computed>.<computed>.timeout @ shopify-perf-kit-3.3.0.min.js:1
requestIdleCallback
i @ shopify-perf-kit-3.3.0.min.js:1
setTimeout
t @ shopify-perf-kit-3.3.0.min.js:1
(anonymous) @ shopify-perf-kit-3.3.0.min.js:1
Promise.then
<computed>.<computed>.<computed>.<computed>.<computed>.<computed>.<computed>.<computed>.timeout @ shopify-perf-kit-3.3.0.min.js:1
requestIdleCallback
i @ shopify-perf-kit-3.3.0.min.js:1
setTimeout
t @ shopify-perf-kit-3.3.0.min.js:1
(anonymous) @ shopify-perf-kit-3.3.0.min.js:1
Promise.then
<computed>.<computed>.<computed>.<computed>.<computed>.<computed>.<computed>.<computed>.timeout @ shopify-perf-kit-3.3.0.min.js:1
requestIdleCallback
i @ shopify-perf-kit-3.3.0.min.js:1
setTimeout
t @ shopify-perf-kit-3.3.0.min.js:1
(anonymous) @ shopify-perf-kit-3.3.0.min.js:1
Promise.then
<computed>.<computed>.<computed>.<computed>.<computed>.<computed>.<computed>.<computed>.timeout @ shopify-perf-kit-3.3.0.min.js:1
requestIdleCallback
i @ shopify-perf-kit-3.3.0.min.js:1
```

Por algum motivo, está vindo dois botões data-keen-next no lugar que era para ter um só, e o currency-selector está sempre aberto e não está sendo possível fechar ele.

> pocketchangethe.world

- Console Python:
```
127.0.0.1 - - [11/Mar/2026 08:25:35] code 404, message File not found
127.0.0.1 - - [11/Mar/2026 08:25:35] "GET /_next/image/?url=%2Fcookie-icon.png&w=96&q=75 HTTP/1.1" 404 -
127.0.0.1 - - [11/Mar/2026 08:25:35] code 404, message File not found
127.0.0.1 - - [11/Mar/2026 08:25:35] "GET /sw.js HTTP/1.1" 404 -
127.0.0.1 - - [11/Mar/2026 08:25:35] code 404, message File not found
127.0.0.1 - - [11/Mar/2026 08:25:35] "GET /manifest.json HTTP/1.1" 404 -
127.0.0.1 - - [11/Mar/2026 08:25:35] code 404, message File not found
127.0.0.1 - - [11/Mar/2026 08:25:35] "GET /_next/image/?url=%2Fcookie-icon.png&w=96&q=75 HTTP/1.1" 404 -
127.0.0.1 - - [11/Mar/2026 08:25:44] code 404, message File not found
127.0.0.1 - - [11/Mar/2026 08:25:44] "GET /manifest.json HTTP/1.1" 404 -
127.0.0.1 - - [11/Mar/2026 08:25:50] code 404, message File not found
127.0.0.1 - - [11/Mar/2026 08:25:50] "GET /cookies/?_rsc=1r34m HTTP/1.1" 404 -
127.0.0.1 - - [11/Mar/2026 08:25:50] code 404, message File not found
127.0.0.1 - - [11/Mar/2026 08:25:50] "GET /privacy/?_rsc=1r34m HTTP/1.1" 404 -
```

- Console Web:
```
(index):377 [Fetch Interceptor] Installed with 128 mappings
(index):378 [Fetch Interceptor] Basename index: 128 files
(index):1524 Unchecked runtime.lastError: The message port closed before a response was received.
(index):301 [Fetch Interceptor] ✓ Request -> assets/coin.glb
(index):301 [Fetch Interceptor] ✓ Request -> assets/draco/versioned/decoders/1.5.5/draco_wasm_wrapper.js
(index):301 [Fetch Interceptor] ✓ Request -> assets/draco/versioned/decoders/1.5.5/draco_decoder.wasm
(index):270 [DOM Interceptor] ✓ link https://cdn.jsdelivr.net/gh/hiunicornstudio/unicornstudio.js@v2.0.1/dist/unicornStudio.umd.js -> assets/gh/hiunicornstudio/unicornstudio.js@v2.0.1/dist/unicornStudio.umd.js
image/:1  Failed to load resource: the server responded with a status of 404 (File not found)
3b0d6bcc3e310ca2.js:95 Service Worker registration failed: TypeError: Failed to register a ServiceWorker for scope ('http://localhost:8000/') with script ('http://localhost:8000/sw.js'): A bad HTTP response code (404) was received when fetching the script.
(anonymous) @ 3b0d6bcc3e310ca2.js:95
image/:1  Failed to load resource: the server responded with a status of 404 (File not found)
manifest.json:1  Failed to load resource: the server responded with a status of 404 (File not found)
(index):1 Manifest fetch from http://localhost:8000/manifest.json failed, code 404
(index):241 [DOM Interceptor] ✓ script https://cdn.jsdelivr.net/gh/hiunicornstudio/unicornstudio.js@v2.0.1/dist/unicornStudio.umd.js -> assets/gh/hiunicornstudio/unicornstudio.js@v2.0.1/dist/unicornStudio.umd.js
d434b5794abcb2c8.js:1 THREE.THREE.Clock: This module has been deprecated. Please use THREE.Timer instead.
L @ d434b5794abcb2c8.js:1
d434b5794abcb2c8.js:1 THREE.THREE.Clock: This module has been deprecated. Please use THREE.Timer instead.
L @ d434b5794abcb2c8.js:1
(index):301 [Fetch Interceptor] ✓ /animated-bg.json -> assets/animated-bg_8f776789733a.json
d434b5794abcb2c8.js:1 THREE.THREE.Clock: This module has been deprecated. Please use THREE.Timer instead.
L @ d434b5794abcb2c8.js:1
68d4134def199930.js:50 Scene already initialized with this configuration, skipping...
d434b5794abcb2c8.js:1 THREE.WebGLRenderer: Context Lost.
manifest.json:1  Failed to load resource: the server responded with a status of 404 (File not found)
68d4134def199930.js:50 Scene already initialized with this configuration, skipping...
(index):317  GET http://localhost:8000/cookies/?_rsc=1r34m 404 (File not found)
window.fetch @ (index):317
R @ e92d492086a8c1b6.js:1
er @ e92d492086a8c1b6.js:1
Y @ e92d492086a8c1b6.js:1
(anonymous) @ e92d492086a8c1b6.js:1
(anonymous) @ e92d492086a8c1b6.js:1
A @ e92d492086a8c1b6.js:1
(index):317  GET http://localhost:8000/privacy/?_rsc=1r34m 404 (File not found)
window.fetch @ (index):317
R @ e92d492086a8c1b6.js:1
er @ e92d492086a8c1b6.js:1
Y @ e92d492086a8c1b6.js:1
(anonymous) @ e92d492086a8c1b6.js:1
(anonymous) @ e92d492086a8c1b6.js:1
A @ e92d492086a8c1b6.js:1
```

- Ele conseguiu fazer funcionar as animações de fundo, do mouse, e ir mudando conforme vai scrollando a página. Agora só falta corrigir um problema na imagem do popup de cookie e resolver uns logs.
