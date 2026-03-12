````markdown

> site.com

- Console Python:
```

```

- Console Web:
```

```

- Outras Observações:
```

```


> palmer-dinnerware.com

- Console Python:
```
# 3 requisições com 404 - assets com espaço no nome sem extensão:
127.0.0.1 - - [12/Mar/2026 09:54:55] "GET /assets/677b8a552071e1f09b594a24/67d96e928ecc7b3bd19d4b83_Kiryu%20Bowl%2012 HTTP/1.1" 404 -
127.0.0.1 - - [12/Mar/2026 09:54:55] "GET /assets/677b8a552071e1f09b594a24/67d96fb9117eab84723fbe43_Lotus%20Plate%2020 HTTP/1.1" 404 -
127.0.0.1 - - [12/Mar/2026 09:54:55] "GET /assets/677b8a552071e1f09b594a24/67d970cf3163f9824c3a12c2_Midori%20Plate%2023 HTTP/1.1" 404 -
```

- Console Web:
```
(índice):1 Unchecked runtime.lastError: The message port closed before a response was received.
(índice):658 [Fetch Interceptor] Installed with 284 mappings
(índice):659 [Fetch Interceptor] Basename index: 284 files
SplitText.min.js:11 SplitText called before fonts loaded

# Problema: srcset com vírgula no nome do arquivo (ex: "23,5") → o browser tenta parsear
# a vírgula como separador de descriptor, resultado: "Dropped srcset candidate" repetido
# por imagem (até 14x para o mesmo asset). Exemplo representativo:
Failed parsing 'srcset' attribute value since it has an unknown descriptor.
(índice):328 Dropped srcset candidate "/assets/677b8a552071e1f09b594a24/6836ddc773361f5d3c9a6156_Plate"
# [... ~100 entradas "Dropped srcset candidate" + "localizeMediaElement @" para outros produtos omitidas ...]

# DOM Interceptor reescrevendo URLs com sucesso. Exemplo:
(índice):329 [DOM Interceptor] ✓ img assets/677b8a552071e1f09b594a24/6836ddc773361f5d3c9a6156_Plate%2019-1-p-500.webp 500w, (...) -> /assets/677b8a552071e1f09b594a24/6836ddc773361f5d3c9a6156_Plate 19-1-p-500.webp 500w, (...)
# [... ~60 entradas [DOM Interceptor] para outros produtos omitidas ...]

# 4 imagens com 404 no browser (nomes com vírgula truncados pelo parser do srcset):
67d96e928ecc7b3bd19d4b83_Kiryu%20Bowl%2012:1  Failed to load resource: 404 (File not found)
67d96fb9117eab84723fbe43_Lotus%20Plate%2020:1  Failed to load resource: 404 (File not found)
67d970cf3163f9824c3a12c2_Midori%20Plate%2023:1  Failed to load resource: 404 (File not found)
67d96da117b01f6cf8cb0379_Eccentric%20Bowl%207:1  Failed to load resource: 404 (File not found)

# GSAP não encontra elementos alvo (animações de texto falhando):
gsap.min.js:10 GSAP target not found. https://gsap.com
# [stack trace omitido - ocorre múltiplas vezes em animFocusedText @ index.mjs:3609]

# Atualização de DOM detectada (interceptor funcionando):
Element: 
Nouvelle valeur: Deep Plate ⌀ 29
textContent actuel: Deep Plate ⌀ 29
```

- Outras Observações:
```

```


> activetheory.net

- Console Python:
```
[0312/100349.264408:WARNING:chrome/app/chrome_main_linux.cc:82] Read channel stable from /app/extra/CHROME_VERSION_EXTRA
Abrindo em uma sessão de navegador existente.
127.0.0.1 - - [12/Mar/2026 10:03:49] "GET / HTTP/1.1" 200 -
127.0.0.1 - - [12/Mar/2026 10:03:49] "GET /assets/js_94535c51081d.js HTTP/1.1" 200 -
127.0.0.1 - - [12/Mar/2026 10:03:49] "GET /assets/images/unsupported-bg.jpg HTTP/1.1" 200 -
127.0.0.1 - - [12/Mar/2026 10:03:49] "GET /assets/fonts/NBArchitektStd-Regular-export/NBArchitektStd-Regular.woff2 HTTP/1.1" 200 -
127.0.0.1 - - [12/Mar/2026 10:03:49] "GET /favicon.ico HTTP/1.1" 404 -
127.0.0.1 - - [12/Mar/2026 10:03:53] "GET /.well-known/appspecific/com.chrome.devtools.json HTTP/1.1" 204 -
```

- Console Web:
```
(index):664 [Fetch Interceptor] Installed with 34 mappings
(index):665 [Fetch Interceptor] Basename index: 34 files
(index):736 Unchecked runtime.lastError: The message port closed before a response was received.
:8000/favicon.ico:1  Failed to load resource: 404 (File not found)
```

- Outras Observações:
```
Abrindo o Site online vai normal, mas quando baixo e entro, aparece: "Your browser is not supported"
```
````
