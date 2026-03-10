# Changelog

Todas as mudanças notáveis neste projeto serão documentadas neste arquivo.

## [Unreleased]

### Fixed - Etapa de Manutenção: Captura Runtime e Integridade de Assets

- **Contexto**: Correções focadas nos sites `beda.imb.br`, `osmo.supply` e na robustez geral do pipeline de captura via runtime.
- **Arquivos**:
  - `website_downloader/network.py`
  - `website_downloader/post_process.py`
  - `website_downloader/url_rewrite.py`

- **Melhorias implementadas**:
  - **Preservação de nomes reais de chunks/assets**: arquivos top-level passaram a ser salvos com o nome original quando não são endpoints com query/API, evitando 404 em imports dinâmicos offline.
  - **Extração genérica de assets a partir de bundles JS**: o scanner de referências literais em `.js` foi ampliado para baixar chunks JS/CSS e outros assets sem depender de parse específico de framework.
  - **Normalização correta de paths root-relative dentro de JS**: referências como `assets/...`, `_next/...` e `static/...` agora resolvem contra a base do site, evitando URLs inválidas do tipo `assets/assets/...`.
  - **Baseline do HTML original capturado da rede**: o pós-processamento agora distingue scripts realmente presentes no documento original de scripts injetados em runtime, evitando reexecução duplicada offline.
  - **Remoção segura apenas de scripts injetados em runtime**: widgets/scripts anexados dinamicamente ao DOM não são mais persistidos cegamente no HTML final quando isso causa dupla inicialização offline.
  - **Reescrita segura de sourcemaps**: remoção de `sourceMappingURL` limitada a comentários reais no fim do arquivo, evitando corromper bundles minificados.
  - **Reescrita de JSON para assets locais absolutos**: valores de URLs em respostas JSON/manifest agora apontam para paths locais root-absolute, evitando 404 em recursos consumidos por runtime.
  - **Preservação de bibliotecas de scroll/runtime**: o pós-processamento deixou de remover bibliotecas como Lenis/Locomotive, mantendo o runtime original e usando apenas CSS mínimo para desbloqueio de scroll.
  - **Escopo mínimo real no scroll fix**: o CSS injetado passou a atuar apenas em `html/body` e loaders, deixando wrappers, `main` e containers de scroll do site intactos.
  - **Restauração de transforms SVG a partir do HTML original**: atributos `transform="matrix(...)"` persistidos pelo runtime em elementos SVG agora são restaurados ao estado server-rendered antes do replay offline.
  - **Preservação do hydration do App Router do Next.js**: scripts inline como `self.__next_f.push(...)` não são mais removidos do HTML salvo.
  - **Restauração de CSS crítico server-rendered**: blocos `<style>` do HTML original passam a ser reaproveitados quando o DOM hidratado contém placeholders vazios de CSS-in-JS.

- **Validação prática nesta etapa**:
  - `beda.imb.br`: imports dinâmicos e imagens de `/storage/...` passaram a carregar corretamente offline.
  - `osmo.supply`: erros de JS corrompido e dupla inicialização de widgets foram eliminados; `data-radial-marquee-rotate` voltou a rodar e o `data-footer-logo-wrap` passou a zerar corretamente no fim da página offline.
  - `pocketchangethe.world`: hydration do Next e CSS crítico voltaram ao HTML salvo; a página offline deixou de abrir branca e voltou a carregar estrutura, estilos e scroll sem erros de página.

### Fixed - Bug 2.0: Canva do site Landonorris Duplicado ✅

- **Problema**: O Playwright salva o HTML depois do Three.js já ter criado o canvas. Quando recarregamos offline, o script roda novamente e cria outro canvas.
- **Solução**: Remover canvas com atributos de dimensão fixa (aquele criado pelo Playwright)
- **Arquivo**: `website_downloader/post_process.py`

### Fixed - Bug 1.1: Erro "Is a directory" ✅

- **Problema**: URLs terminando com `/` (ex: `_next/image/`) causavam erro `[Errno 21] Is a directory`
- **Causa**: Sistema tentava salvar diretório como arquivo
- **Solução**: Detectar URLs terminando em `/` e salvar como `index.html` dentro do diretório
- **Arquivo**: `website_downloader/network.py`

### Fixed - Bug 1.2: CDN Patterns Hardcoded (Overfitting) ✅

- **Problema**: Patterns de CDN específicos de landonorris.com estavam hardcoded
- **Violação**: Manifesto (regra C + constraint 3) — código genérico, não site-específico
- **Solução**: Derivar automaticamente domínios de CDN a partir do `resource_map`
- **Implementação**: Extrai domínios únicos do `resource_map` e gera patterns dinamicamente
- **Arquivo**: `website_downloader/post_process.py`
- **Benefício**: Funciona para QUALQUER site, não apenas landonorris.com

### Fixed - Bug 1.3: Sourcemap Removal Não-Recursivo ✅

- **Problema**: `_remove_sourcemaps()` usava `os.listdir()`, processava apenas raiz de `assets/`
- **Solução**: Trocar para `os.walk()` para processar TODOS arquivos JS em subpastas
- **Arquivo**: `website_downloader/post_process.py`

### Added - Fase 2: UX da Interface Web ✅

- **Problema**: Reset automático após 2s, logs desapareciam, nenhuma ação clara pós-download
- **Correções implementadas**:
  - NÃO resetar automaticamente após download/erro
  - Logs sempre visíveis com altura expandida (400px vs 200px)
  - Botão "Copiar Logs" ao lado do container de logs
  - Mensagem de erro clara e persistente
  - Link de download permanente (não desaparece)
- **Design**: Aplicado Asimov Academy Vibe Design (Dark Mode)
- **Arquivos**: `templates/index.html`, `templates/style.css`, `templates/main.js`

### Added - Fase 3: Servidor Local nos Downloads ✅

- **Feature**: Script `serve.py` incluído em cada site baixado
- **Funcionalidade**:
  - Servidor HTTP local com CORS habilitado
  - MIME types especiais (`.wasm`, `.glb`, `.riv`, `.webp`, `.woff2`)
  - Auto-detecção de porta disponível (8000+)
  - Abre navegador automaticamente
  - Instruções claras no terminal
- **Uso**: `python3 serve.py` ou `python serve.py`
- **Requisitos**: Python 3.7+ (stdlib apenas, sem deps externas)
- **Arquivo**: `downloader.py`

### Added - Fase 4: Script de Limpeza para IA (TODO: Necessita melhorar) ⏳

- **Feature**: Otimização de sites para consumo por IA (redução de tokens)
- **Implementação**: Módulo `website_downloader/clean.py`
- **Resultado**: Duas versões no ZIP:
  - `raw/`: Cópia exata do download original (backup funcional)
  - `clean/`: Otimizado para IA (menos linhas, sem comentários)
- **Processamento HTML**:
  - Remove comentários HTML (preserva IE conditionals)
  - Remove meta tags de SEO/social (og:, twitter:)
  - Remove atributos `data-*` vazios
  - Normaliza indentação para 2 espaços
  - Reduz múltiplas linhas em branco para max 1
- **Processamento CSS**:
  - Remove comentários CSS
  - Normaliza indentação para 2 espaços
  - Reduz linhas em branco
  - NÃO minifica (mantém legibilidade)
- **Processamento JS**:
  - Remove comentários de linha (`//`) e bloco (`/* */`)
  - Remove linhas em branco excessivas
  - NÃO minifica, NÃO reformata lógica
  - Pula arquivos já minificados (< 10 linhas)
- **NÃO faz**: Minificação, alteração de lógica, remoção de código funcional
- **Integração**: Chamado automaticamente em `app.py` após download

### Added - Fase 5: Setup de Ambiente Local ✅

- **Problema**: `build.sh` era exclusivo para Docker/Deploy, desenvolvedores tinham problemas locais
- **Solução**: Script `setup.sh` unificado que detecta ambiente
- **Comportamento Local**:
  - Verifica se `uv` está instalado (orienta instalação se não)
  - Limpa `__pycache__` (evita bug de cache do Flask)
  - Executa `uv sync` para dependências
  - Instala Playwright Chromium via `uv run`
  - Mostra instruções de uso
- **Comportamento Docker/Deploy**:
  - Usa `pip install -r requirements.txt`
  - Instala Playwright + deps do sistema
  - Comportamento idêntico ao `build.sh` original
- **Arquivos**:
  - Criado: `setup.sh` (unificado, detecta ambiente)
  - Atualizado: `build.sh` (chama `setup.sh` com flag Docker)

### Added - Fase 6: Documentação de Sites Testados ✅

- **Arquivo**: `SITES.md` criado
- **Conteúdo**:
  - Lista de sites testados com status (✅/⚠️/❌)
  - Detalhes: URL, complexidade, recursos, fidelidade, observações
  - Template para novos testes
  - Estatísticas gerais
  - Lista de sites próximos a testar
- **Propósito**: Registro vivo de validações, facilita tracking de bugs por site

### Fixed - Correção: CSS Integrity + Basenames Relativos + URL Decode ✅

- **Novos problemas identificados** (após teste do usuário - layout quebrado):
  1. **CSS bloqueado**: Atributo `integrity` fazia browser rejeitar CSS principal offline → layout quebrado
  2. **Basenames relativos**: CSS inline tinha `url("67e2c...svg")` sem `assets/` → 404 para SVGs
  3. **URL encoding**: Arquivo salvo como `MonaSans_wdth%2Cwght.woff2` (com `%2C`) não era servido pelo http.server → 404 para font

- **Soluções implementadas**:
  - **Remover integrity de CSS** (`post_process.py`): Remove `integrity`, `crossorigin`, `nonce` de `<link rel="stylesheet">`
  - **Processar HTML final** (`post_process.py:52`): Chama `_rewrite_basenames_in_content()` no HTML antes de salvar
  - **Substituir basenames no HTML** (`post_process.py`): Método dedicado para HTML inline - substitui `url("basename.svg")` → `url("/assets/path/basename.svg")`
  - **URL decode em filenames** (`network.py:155`): Usa `urllib.parse.unquote()` para decodificar `%2C` → `,` antes de salvar arquivo

- **Validação completa**:
  - ✅ CSS carrega sem erro de integrity
  - ✅ Basenames substituídos: `url("/assets/67b5a02dc5d338960b17a7e9/67e2c781...svg")`
  - ✅ Font salva com vírgula: `MonaSans-VariableFont_wdth,wght.woff2`
  - ✅ Layout funcional (não mais quebrado)
  - ✅ **Validado com sucesso**: landonorris.com baixado com 264 arquivos, 15MB, quase todas animações funcionando
  - ⚠️ Canvas hero ainda não renderiza (investigação futura)

### Fixed - Correção: Cache de Módulos no Flask ✅

- **Problema**: App via Flask baixava 240 arquivos (14MB) vs script direto 264 arquivos (15MB)
- **Causa**: Flask `use_reloader=True` mantém cache de módulos Python entre reinicializações
- **Solução**: Adicionado `use_reloader=False` em `app.py:221` para desabilitar auto-reload e evitar cache
- **Status**: Resolvido - app.py agora baixa corretamente após limpeza de cache

### Fixed - Correção: Rewrite Recursivo + CDN Externo ✅

- **Problema REAL identificado** (após análise detalhada dos logs):
  1. **Recursos foram capturados corretamente** (118 arquivos, incluindo texturas WebGL)
  2. **MAS**: O `_global_url_rewrite` só processava arquivos na RAIZ de `assets/`, não em subpastas
  3. **Resultado**: JavaScript em `assets/dev-js/lando.OFF+BRAND.js` não foi reescrito
  4. **JavaScript continha**: `var vQ="https://lando.itsoffbrand.io/gl"` (base path do CDN)
  5. **Por isso**: Todas texturas eram pedidas do CDN externo (403), não do disco local

- **Solução implementada** (`post_process.py`):
  - **Rewrite recursivo**: Mudado de `os.listdir()` para `os.walk()` - processa TODOS arquivos em subpastas
  - **Substituição de CDN**: Adicionados padrões para substituir base URLs de CDNs externos:
    - `"https://lando.itsoffbrand.io/"` → `"/assets/"`
    - `"lando.itsoffbrand.io/"` → `"assets/"`
    - `"https://cdn.prod.website-files.com/"` → `"/assets/"`
  - **Resultado**: JavaScript reescrito com `var vQ="/assets/gl"` em vez do CDN

- **Validação completa**:
  - ✅ 118 recursos capturados (antes: 118, mantido)
  - ✅ 3 arquivos JS reescritos (antes: 1 - agora processa subpastas)
  - ✅ JavaScript NÃO contém mais referências ao CDN externo
  - ✅ Base path reescrito: `"https://lando.itsoffbrand.io/gl"` → `"/assets/gl"`
  - ✅ Teste local: 0 erros 403, 0 erros 404 para recursos WebGL
  - ✅ Estrutura preservada: `assets/gl/textures/head/webp/diffuse.webp`

- **Status**: **CORRIGIDO** - WebGL funcionando offline

### Fixed - Correção: Captura de Texturas WebGL ✅

- Implementada detecção automática de elementos `<canvas>` WebGL (largura/altura > 100px)
- Adicionado método `interact_with_webgl_canvases()` com interações focadas em canvas
- Primeiro pass: hover no centro + varredura em 5 pontos (cantos + centro) + espera 3s por canvas
- Segundo pass: hover repetido no centro após 5s (para texturas que dependem de assets prévios)
- Espera estendida de 5s após segundo pass para texturas grandes
- Wait final aumentado de 5-8s para 8-10s para capturar todas as requisições WebGL
- **Genérico:** Funciona para Three.js, Babylon.js, PixiJS, qualquer WebGL — sem código específico
- **Validado landonorris.com:** Captura aumentou de 118 para 264 assets (+146), incluindo 189 .webp (texturas diffuse, normal, alpha, depth, roughness, metallic)
- **Tempo:** +76s no download (de ~95s para ~171s) devido às interações estendidas — aceitável para sites WebGL
- **Decisão:** Se texturas ainda não carregarem após 2 passes, aceita graciosamente (logar no relatório)

### Added - Fase 6: Retry, Relatório, Limites ✅

- Implementado retry com 2 tentativas e backoff exponencial em fallback downloads
- Adicionado limite de 100MB por recurso (recursos maiores são ignorados)
- Implementado timeout de 15s por recurso individual
- Adicionado tracking completo de falhas (URL + motivo resumido)
- Adicionado tracking de recursos ignorados (tracking domains, size limit)
- Implementado relatório final detalhado: total por tipo, percentuais, falhas (max 20), ignorados agrupados por razão
- Adicionado tracking de tempo total de download
- **Validado:** Relatório formatado aparece nos logs, falhas não travam processo

### Changed - Fase 5: CSS Fix Seguro ✅

- Removida lógica de remover inline styles de elementos individuais (previne quebra de animações)
- CSS fix reduzido para escopo MÍNIMO: apenas html/body, scroll containers e loaders
- Removidas regras que forçavam `opacity: 1 !important` em elementos genéricos
- Removidas regras que forçavam `transform: none !important` em elementos genéricos
- Removidas regras que forçavam `visibility: visible !important` fora de html/body
- Filosofia: "não quebrar scroll" em vez de "mostrar tudo forçadamente"
- **Decisão:** Sites ficam "congelados no estado de load" para elementos animados (esperado e aceitável)

### Added - Fase 4: Processadores Extras + Limpezas ✅

- Implementado processamento de `<link rel="preload|prefetch|modulepreload">` com reescrita de href
- Implementada remoção completa de `<link rel="preconnect">` e `<link rel="dns-prefetch">` (inúteis offline)
- Implementada remoção de scripts de tracking por domínios conhecidos (Google Analytics, GTM, Facebook Pixel, etc)
- Implementada remoção de `sourceMappingURL` de arquivos JS baixados
- **Validado:** Preconnects removidos, preloads reescritos, JS sem sourcemaps

### Added - Fase 3: URL Rewriting Global + Fetch Interceptor ✅

- Implementado "Blind Mapping": substituição literal de URLs em todos arquivos de texto (HTML, CSS, JS, JSON, SVG, XML)
- URLs substituídas por paths locais (variantes: com protocolo, protocol-relative)
- Substituição acontece APÓS salvamento de todos os recursos capturados
- Implementado Fetch Interceptor injetado como PRIMEIRO `<script>` do `<head>`
- Interceptor contém resource_map serializado (inline se <500 entradas, senão JSON externo)
- Sobrescreve `window.fetch` e `XMLHttpRequest.prototype.open` para redirecionar para arquivos locais
- Trata URLs como string e como objeto Request
- Console log de cada redirecionamento para debug
- **Filosofia:** Site "pensa" que está online, JS carrega assets via fetch do disco
- **Validado:** 264 mapeamentos no landonorris.com, interceptor presente no HTML, nenhum request falhado

### Added - Fase 2: Network Recording Aprimorado ✅

- Adicionada simulação de interações do mouse para trigger de lazy loading em hover
- Implementado wait adaptativo para network idle (5-8s randômico para capturar XHRs tardios)
- Adicionada classificação automática de recursos por tipo (image, script, css, font, media, other)
- Implementado log detalhado de recursos capturados por categoria com emojis
- Melhorado filtro de tracking domains (aplicado no interceptor antes de salvar)
- Fluxo de download estendido: scroll → interações → wait → captura
- **Validado:** Sistema funciona com melhorias, logs mais informativos

### Changed - Fase 1: Estrutura + Migração ✅

- Refatorado código monolítico de `downloader.py` (~920 linhas) para estrutura modular
- Criada arquitetura em 3 módulos dentro de `website_downloader/`:
  - `browser.py`: Controle do Playwright (launch, scroll, iframes, cookies)
  - `network.py`: Interceptação de rede, salvamento de recursos, retry logic
  - `post_process.py`: Processamento de HTML/CSS, limpezas, SPA frameworks
  - `__init__.py`: Configurações e constantes centralizadas (timeouts, limites, skip domains)
- Transformado `downloader.py` em fachada que mantém interface pública intacta
- Interface pública preservada 100%: `WebsiteDownloader`, `get_site_name()`, `zip_directory()`
- Nenhuma funcionalidade alterada - migração isomórfica do código existente
- Configurado `pyproject.toml` para usar uv + Python 3.12
- Código original preservado em `downloader_old.py` (backup)
- **Validado:** Download real funcionando (example.com), app.py sem modificações
