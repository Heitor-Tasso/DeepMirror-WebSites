# AI Design Engineering

## Técnica impecável para Web Design de IA com qualidade 

Este documento sintetiza, contextualiza e expande um conjunto de insights, técnicas e boas práticas sobre como usar IA de forma eficaz para capturar, analisar e reproduzir design de alta fidelidade a partir de sites reais.

## O Problema Fundamental: Por que a IA é Péssima em HTML/CSS Puro

Antes de qualquer coisa é essencial compreender **o problema de raiz**. Sem isso, qualquer workflow será construído sobre uma base errada.

### 1.0 - A IA não tem olhos: Ela processa texto

A IA prevê tokens baseada em padrões estatísticos. Quando você pede para ela gerar um layout Flexbox, ela não "visualiza" o resultado. Isso significa:

- **CSS é espacial, a IA é sequencial.** Fluxos de empilhamento e posicionamento 2D exigem raciocínio que a IA não possui. O código pode fazer sentido linha a linha e ainda assim quebrar completamente na tela.

- **O Cascade é global, a IA é local.** A IA prevê o próximo token com base no contexto imediato. O CSS é global por natureza — uma regra em `styles.css` pode destruir o layout de um elemento aninhado 6 níveis abaixo, numa estrutura que a IA nunca "viu" ao mesmo tempo.

### 1.1 - O viés dos dados de treinamento

O código front-end de alta qualidade disponível publicamente está majoritariamente em React, Vue e similares. O HTML/CSS puro disponível para treino frequentemente remete a épocas mais antigas da web, com padrões desatualizados e soluções de fóruns. Resultado: a IA é melhor no ecossistema moderno por ter aprendido padrões melhores nele.

### 1.2 - Equifinalidade: O problema da múltipla resposta correta

Diferente do código algorítmico (onde poucas soluções são corretas), HTML/CSS tem **equifinalidade**: existem dezenas de formas igualmente válidas de centralizar uma `div`, colorir um botão ou criar um card. Isso faz com que a IA alterne aleatoriamente entre abordagens diferentes ao longo de uma sessão, gerando inconsistência.

### 1.3 - Por que JSX/React funciona melhor

React, JSX e outros frameworks resolvem estruturalmente os três problemas acima:

| Problema | CSS Puro | React/JSX |
| :- | :-: | :-: |
| Escopo | Global (Cascade) | Local (componente isolado) |
| Padrão de treino | Fragmentado, antigo | Rico, moderno, consistente |
| Equifinalidade | Alta | Baixa (padrões estabelecidos) |
| Legibilidade estrutural | Baixa | Alta |

**Conclusão prática:** Para geração de interfaces completas, vá direto para JSX/React com Tailwind. A fricção de debugar CSS puro gerado por IA raramente compensa.

## A Virada de Paradigma

Este é o insight central que diferencia uma abordagem amadora de uma profissional.

### 2.0 - O erro conceitual padrão

A maioria das pessoas tenta fazer a IA **ler e entender** o código de um site para depois reproduzi-lo. Isso falha por razões previsíveis:

- Sites modernos de alto nível têm código minificado, obfuscado ou gerado por bundlers;
- O HTML frequentemente é apenas um "palco vazio" — a mágica acontece na GPU e na memória JS;
- Jogar um arquivo CSS gigante no contexto resulta em alucinação e perda de detalhes;

#### 2.1 - A mudança de paradigma correta

Em vez de "como faço a IA entender esse espaguete minificado?", a pergunta certa é:

> **"Como eu entrego para a IA apenas os ingredientes essenciais — assets, shaders, dados de estado — para ela cozinhar um prato novo?"**

A IA não precisa ler o código do Lottie Player para reproduzir uma animação. Ela precisa do **arquivo JSON de configuração** da animação.

A IA não precisa entender o JS minificado de scroll-jacking da Apple. Ela precisa dos **keyframes matemáticos** mapeados por um script externo.

#### 2.2 - O modelo mental correto: pipeline em três camadas

| MUNDO REAL | PROCESSAMENTO | IA |
| :- | :-: | :-: |
| Site de referência | Scripts + Ferramentas | Geração |
| HTML/CSS/JS minificado | Extração cirúrgica | Prompt rico |
| Assets na rede | Download seletivo | Assets disponíveis |
| Animações na GPU | Mapeamento comportamental | Especificação clara |
| Shaders GLSL | Captura via Spector.js | Tradução para React |

## Camadas de Pocessamento e Desenvolvimento

###  Captura: Como Extrair o DNA Visual de Qualquer Site

#### 3.0 - Runtime Network Recording

A técnica mais poderosa é o **Runtime Network Recording**: em vez de parsear HTML estático, você executa o site real (via Playwright), intercepta **todas** as requisições de rede e salva o que foi realmente carregado.

Por que isso é superior a qualquer parser estático:

1. Captura recursos que não estão no HTML (dinâmicos via fetch/XHR)
2. Captura o estado **após a hidratação** de SPAs (Next.js, Nuxt, etc.)
3. Captura assets de CDNs externos
4. Garante que apenas recursos que realmente foram usados sejam baixados

#### 3.1 - A dualidade raw/clean: Nunca confunda as camadas

Uma das descobertas práticas mais valiosas é manter **duas versões** do site capturado:

- **`raw/`**: Backup fiel. Nunca modificar. Fonte de verdade para assets, animações, comportamentos.
- **`clean/`**: Otimizado para leitura por IA. Desminifica, remove tracking, normaliza JS, comenta SVGs, tira comentários dos códigos e seções desnecessárias.

**Regra de ouro:** Sempre comece pelo `clean/`. Recorra ao `raw/` apenas quando algo visual estiver faltando — uma animação perdida, um asset específico, um comportamento de canvas.

#### 3.2 - Estratégia de captura por tipo de site

| Tipo de site | Estratégia primária | Assets-alvo |
| :- | :-: | :-: |
| Site estático simples | HTML/CSS direto | `.css`, `.woff2`, imagens |
| SPA (Next.js, Nuxt) | Runtime Recording + DOM hidratado | JS chunks, API responses visuais |
| Site com Three.js/WebGL | Network Recording focado em binários | `.glb`, `.gltf`, `.hdr`, `.wasm` |
| Site com Rive | Network Recording + canvas | `.riv` |
| Animações Lottie | Interceptar XHR/fetch | JSONs Bodymovin |
| Scroll-jacking (Apple-style) | Playwright Profiler + CDP | Mapeamento de keyframes matemáticos |

### Processamento: Como Preparar o Material para a IA

Esta é a camada mais determinante para a qualidade do resultado final. O processamento correto pode transformar um arquivo de 10.000 linhas em um contexto rico e denso de apenas 2.000 linhas.

#### 4.0 - Nunca use Regex para estrutura HTML: Use AST

Regex é inadequado para HTML hierárquico. Para limpar e fatiá-lo, use ferramentas de AST:

- **Python:** BeautifulSoup
- **Node.js:** Cheerio ou unified/rehype

**Por que o placeholder de SVG é crítico:** SVGs inline gigantes consomem milhares de tokens sem adicionar nenhuma informação visual para a IA. Substituir por `<svg data-icon="logo">...</svg>` economiza contexto para o que realmente importa.

> Dessa forma, é extremamente importante separar o css e js do html para aplicar as próximas regras em cada um deles e remover comentários dele gigantes dele, mas manter os pequenos que podem ajudar no contexto.

#### 4.1 - CSS é onde o Regex brilha: Use-o com precisão

Diferente do HTML, o CSS tem estrutura previsível o suficiente para Regex ser eficaz para:

- Extrair todas as variáveis CSS (Design System de bandeja);
- Extrair paleta de cores bruta (HEX, RGB, HSL);
- Extrair todas as @font-face declarations;
- Extrair todos os @keyframes;
- Separar listas gigantes de classes, ids e elementos para um simples "margem: 0;" e colocar em um arquivo separado;

**O fluxo correto:** Rodar esses scripts, salvar os resultados, e passar **os tokens extraídos** em um arquivo de contexto para o prompt — não o CSS completo. Enquanto o que é ação, pode ser feita na estrutura mesmo.

#### 4.2 - Raciocínio visual via `getComputedStyle`

Em vez de pedir para a IA adivinhar qual classe CSS produz qual visual, você usa código para "ler" a tela renderizada:

**Por que isso é revolucionário:** A IA não precisa mais ler o arquivo CSS gigante. Ela recebe um JSON com os valores reais, computados, de cada elemento. Elimina completamente a ambiguidade do Cascade.

#### 4.3 - Isolamento por relevância: Descarte o código morto

Para sites complexos (Apple AirPods, por exemplo), mais de 80% do JS baixado é irrelevante: polyfills, rotas não visitadas, lógica de carrinho. Use o Chrome DevTools Protocol (CDP) para mapear apenas o código executado:

```python
# Conceito: usar CDP para tracing de execução
async with page.expect_event('load'):
    await page.goto(url)

# Ativar cobertura de JS
await page.coverage.start_js_coverage()
await scroll_page_fully(page)  # Acionar todas as animações
coverage = await page.coverage.stop_js_coverage()

# Filtrar apenas blocos executados durante a animação
executed_ranges = [
    entry for entry in coverage 
    if entry['url'].endswith('animation.js')
]
```

**Resultado:** Em vez de milhares de funções minificadas, você tem apenas o fluxo das animações. Esse bloco filtrado é o que vai para a IA.

### Geração: Como Instruir a IA para Resultados de Alta Fidelidade

#### 5.0 - Separar estrutura (html) e estilos (css)

Esta é a regra mais simples e mais poderosa:

**Errado:**
> "Crie um card HTML/CSS com sombra e tipografia moderna."

**Correto:**
> **Turno 1:** "Aqui está o JSON de estilos computados do elemento `.card` do site X. Crie a estrutura semântica em HTML para este componente, usando as classes evidenciadas."
> **Turno 2:** "Agora escreva o CSS para este HTML, usando **apenas** estas variáveis CSS extraídas: `[lista de tokens]`. Não invente valores."

A separação elimina a equifinalidade: a IA toma uma decisão estrutural de cada vez, sem precisar reconciliar duas camadas conflitantes simultaneamente.

#### 5.1 - Design System como âncora de contexto

Nunca inicie uma geração sem ancorar o contexto. O formato mais eficaz:

```
CONTEXTO DO PROJETO:
- Framework: React + Tailwind v4
- Tokens CSS disponíveis: [lista extraída por script]
- Fontes carregadas: [lista extraída por script]
- Paleta aprovada: [lista extraída por script]

REGRA HARD: Não use valores de cor, espaçamento ou tipografia que não estejam nesta lista.
REGRA HARD: Não normalize ou simplifique o visual. O objetivo é máxima fidelidade à referência.
```

#### 5.2 - Forçar BEM quando CSS puro for inevitável

Se o projeto exige CSS puro, imponha BEM explicitamente no prompt:

```
Gere o HTML e CSS usando estritamente a convenção BEM:
- Block: .card
- Element: .card__title, .card__image, .card__body
- Modifier: .card--featured, .card--compact

Não use seletores aninhados além de 2 níveis. Não use !important.
```

Isso força a IA a simular isolamento de componente dentro do CSS global.

#### 5.3 - Tailwind como lingua franca da IA

A IA ama Tailwind porque ele resolve estruturalmente o problema do escopo: os estilos são aplicados localmente via classes no próprio HTML, semelhante à mentalidade do JSX. A IA consegue mapear o token de texto diretamente para o resultado visual sem se preocupar com especificidade.

**Quando detectar Tailwind em um site:** não tente converter para CSS puro. Preserve as classes utilitárias no design system e apenas liste as cores/fontes customizadas no `style.css`.

### Sites Complexos: WebGL, Three.js, Rive e Scroll-Jacking

Esta seção trata dos casos onde todas as abordagens convencionais falham — e onde a engenharia reversa de comportamento e assets também deve ser aplicada.

#### 6.0 - O diagnóstico crítico: quando o HTML é um palco vazio

Sites como Apple AirPods Pro ou Lando Norris têm um HTML mais simples (ainda com css, mas não é focado nele):
```html
<div id="app"></div>
<canvas id="webgl-canvas"></canvas>
```

Toda a magia — iluminação 3D, física de scroll, interpolação de Rive, Motion — acontece na GPU e na memória JavaScript. Tentar ler o HTML/CSS desses sites para extrair design é útil, mas não é suficiente para replicar os comportamentos e estilos. A estratégia precisa mudar.

#### 6.1 - Network Recording focado em binários

Para sites Three.js/WebGL, foque nos binários e depois no html e css:

```python
EXTENSOES_ALVO = [
    '.glb',   # Modelos 3D (Three.js)
    '.gltf',  # Modelos 3D alternativos
    '.riv',   # Animações Rive
    '.hdr',   # Mapas de iluminação ambiente
    '.wasm',  # WebAssembly (Draco, compressão)
    '.json',  # Verificar se tem estrutura Lottie/Bodymovin
]

# Identificar JSONs Lottie
def is_lottie_json(json_data):
    return all(k in json_data for k in ['v', 'fr', 'ip', 'op', 'layers'])
```

#### 6.2 - Mapeamento comportamental de scroll-jacking

Para sites que atrelam animações complexas ao scroll (Apple-style), não tente ler o JS minificado. Mapeie a **física** diretamente:

```python
async def map_scroll_physics(page):
    scroll_map = []
    
    # Rolar de 100 em 100 pixels
    for scroll_y in range(0, 5000, 100):
        await page.evaluate(f'window.scrollTo(0, {scroll_y})')
        await asyncio.sleep(0.1)  # Aguardar animação estabilizar
        
        # Capturar estado computado dos elementos de interesse
        state = await page.evaluate('''() => {
            const hero = document.querySelector('.hero-image');
            const title = document.querySelector('h1');
            const style_hero = window.getComputedStyle(hero);
            const style_title = window.getComputedStyle(title);
            
            return {
                scrollY: window.scrollY,
                hero: {
                    opacity: style_hero.opacity,
                    transform: style_hero.transform,
                },
                title: {
                    opacity: style_title.opacity,
                    transform: style_title.transform,
                }
            };
        }''')
        
        scroll_map.append(state)
    
    return scroll_map
```

**O prompt resultante para a IA:**
> *"Este JSON representa o mapeamento exato da física de animação atrelada ao scroll. Recrie esse comportamento em JSX usando React e Framer Motion (`useTransform` e `useScroll`)."*

#### 6.3 - Captura de Shaders GLSL

Para efeitos de distorção de imagem fluida em Canvas (sites Awwwards-level), o segredo está nos Fragment e Vertex Shaders:

- **Ferramenta:** Spector.js (extensão Chrome para interceptar chamadas WebGL);
- **O que captura:** Código GLSL exato rodando na GPU naquele frame;
- **O que fazer:** Colar o shader capturado para a IA e pedir tradução para React Three Fiber;

**Insight crítico:** A IA é excepcionalmente boa em ler GLSL. Você cola o shader capturado e pede uma versão manipulável como prop de componente React.

### O Design System como Produto: Estrutura e Contrato de Saída

#### 7.0 - A estrutura mínima viável

Todo Design System extraído deve ter exatamente esta estrutura:

```
design-system/
├── main.html     # Showcase ao vivo, todas as seções
├── style.css     # Apenas CSS necessário + tokens
├── main.js       # Apenas JS de interação e demos
└── assets/       # Apenas assets usados (sem dumps)
```

**Regra crítica:** A pasta final nunca deve depender de `raw/` ou `clean/`. Ela deve funcionar de forma completamente autônoma.

#### 7.1 - Ordem canônica das seções do showcase

O `index.html` deve seguir esta ordem invariavelmente:

1. **Hero**: Prova o DNA visual. Deve ser reconhecível como derivado da referência.
2. **Motions**: Uso de todos os motions, animações e modelos 3d.
3. **Typography**: Famílias, pesos, tamanhos, line-height, letter-spacing com exemplos ao vivo.
4. **Colors & Surfaces**: Cores base, texto, backgrounds, borders, glows, gradientes, opacidades.
5. **Components**: Buttons, inputs, cards, navbars, badges, accordions, CTAs, footers.
6. **Layout & Spacing**: Container widths, grids, composição de hero, negative space.
7. **Frames & Transições**: @keyframes, transições, reveals, hover effects, loops decorativos.
8. **Icons & Assets** — Sistema de ícones, logos, texturas, ilustrações.

## Armadilhas Clássicas e Como Evitá-las

### 8.0 - Desofuscação em massa

**O erro:** Tentar desofuscar cada função minificada de um arquivo JS grande.

**Por que falha:**
- Funções minificadas perdem escopo e closure — sem contexto global, a IA alucina nomes inúteis;
- Uma variável `a` pode ser uma função de animação em um módulo e um contador de loop em outro, substituição global via Regex corrompe o código;
- Um arquivo JS de 200KB pode ter milhares de blocos, o volume inviabiliza o processo;

**A alternativa correta:** Usar CDP para mapear apenas o código que **realmente executa** durante a interação relevante, e passar esse bloco filtrado para um LLM robusto.

### 8.1 - Normalização genérica

**O erro:** Normalizar tudo para um visual "bonitinho porém genérico" — o famoso azul `#007bff`, os 8px de border-radius, as shadows padrão do Bootstrap.

**Por que falha:** O objetivo é extrair o DNA visual do site, não criar uma interpretação. Se o site tem um gradiente de neon específico `#FF006E -> #8338EC`, esse é o token correto — não "algum gradiente roxa".

**A regra:** Nunca invente componentes, estilos ou estados que não estejam evidenciados no download.

### 8.2 - Contexto gigante

**O erro:** Jogar o CSS inteiro único, o HTML completo e todos os assets no contexto da IA de uma vez.

**Por que falha:** Modelos de IA degradam em qualidade quando o contexto excede sua capacidade de atenção efetiva. Isso resulta em alucinação sobre os detalhes das primeiras 2.000 linhas quando a IA está processando as últimas 2.000.

**A regra:** Sempre pré-processar e entregar o mínimo necessário. Tokens de contexto são um recurso escasso.

### 8.3 - Snapshot DOM em sites WebGL

**O erro:** Usar um MCP simples ou um scraper de DOM para capturar sites como Apple AirPods Pro ou Three.js-heavy.

**Por que falha:** O HTML desses sites é um palco vazio. O design não está no DOM — está na GPU.

**A regra:** Para sites com WebGL/Three.js/Rive, mude a estratégia para Network Recording de binários + mapeamento comportamental.

### 8.4 - Extração de múltiplos sites

**O erro:** Misturar referências de sites diferentes no mesmo design system.

**Por que falha:** Design systems são destilações de uma única identidade visual coesa. Misturar cria inconsistência de DNA.

**A regra:** Um site por extração. Sempre.

## Novas Fronteiras: O Que Ainda Não Existe Mas Deveria

Esta seção vai além do que foi discutido e propõe extensões naturais da metodologia.

### 9.0 - Processor de Shaders Automatizado

Um script que vasculha arquivos JS baixados buscando por strings GLSL (`void main()`, `gl_FragColor`, `gl_Position`) e extrai automaticamente os shaders para arquivos `.glsl` separados. Isso seria adicionado ao `SiteCleaner` como um processor dedicado.

### 9.1 - Design Token Diff: Comparar evoluções

Uma ferramenta que compara dois design systems extraídos do mesmo site em momentos diferentes (v1 vs v2) e gera um diff visual dos tokens alterados. Útil para acompanhar evoluções de identidade de marca.

- `development/diff_raw_clean.py`

### 9.2 - Scroll Physics Recorder como feature nativa

Integrar o mapeamento de física de scroll diretamente no DeepMirror WebSites como uma etapa opcional da pipeline, gerando automaticamente um `scroll_physics.json` para cada elemento animado detectado durante a navegação.

### 9.3 - Multi-pass de extração por intenção

Ao invés de uma única extração, rodar múltiplos passes especializados:

- **Pass 1:** Estrutura e componentes (HTML)
- **Pass 2:** Tokens visuais (CSS)
- **Pass 3:** Comportamento e motion (JS/keyframes)
- **Pass 4:** Assets binários (imagens, fontes, modelos)

Cada pass tem seu próprio script de limpeza e seu próprio prompt otimizado para aquela intenção específica.

## Sumário Executivo

> Capture comportamento, não código. Destile evidências, não suposições. Entregue ingredientes, não dumps. E deixe a IA cozinhar.

O ciclo completo é:

```
1. CAPTURAR     ->  Runtime Network Recording
2. CLASSIFICAR  ->  raw/ vs clean/ + tipo de site;
3. PROCESSAR    ->  AST para HTML + Regex para CSS + CDP para JS;
4. DESTILAR     ->  Mínimo necessário + tokens extraídos + assets relevantes;
5. INSTRUIR     ->  Separar HTML/CSS + âncora de design system + regras hard;
6. CRIAR SITE DESIGN SYSTEM.
```
