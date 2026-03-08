# Features e Correções Futuras

Lista de melhorias e bugs conhecidos para implementação futura.

## 🐛 Bugs Conhecidos

### 1. Canvas Hero WebGL não renderiza (landonorris.com)
**Descrição**: O canvas WebGL principal do hero não renderiza, embora outros canvas funcionem.

**Status**: Investigação pendente

**Possíveis causas**:
- Asset específico do hero faltando
- Ordem de inicialização incorreta
- Dependência de algum script que não carrega offline
- Configuração GSAP/Lenis não inicializa

**Prioridade**: Média

---

### 2. Erro ao salvar diretório como arquivo (pocketchangethe.world) ✅ CORRIGIDO

**Status**: ✅ Corrigido em 06/Mar/2026 (Fase 1.1)

**Descrição**: Erro ao baixar `https://pocketchangethe.world/`

**Erro original**:
```
❌ Erro: [Errno 21] Is a directory: 'downloads/.../assets/_next/image/'
```

**Causa**: Sistema tentava salvar um path de diretório (`_next/image/`) como arquivo.

**Solução implementada**:
- Detecta se URL termina com `/` (indica diretório)
- Salva como `index.html` dentro do diretório
- Validação adicional em `_save_resource()` para evitar sobrescrever diretórios existentes

**Arquivo**: `website_downloader/network.py:201-233`

**Pendente**: Validação com teste real de pocketchangethe.world

---

## 🚀 Features Futuras

### 1. Suporte a Lazy Loading mais agressivo
**Descrição**: Algumas imagens/recursos só carregam em interações específicas.

**Implementação sugerida**:
- Adicionar opção de "scroll completo" (rolar até o final múltiplas vezes)
- Clicks automáticos em botões/tabs detectados
- Wait mais longo em sites com muitas animações

**Prioridade**: Baixa

---

### 2. Modo de captura "completa" vs "rápida"
**Descrição**: Permitir usuário escolher entre:
- **Rápida**: Captura básica (atual)
- **Completa**: Todas interações, scroll múltiplo, esperas mais longas

**Prioridade**: Média

---

### 3. Relatório HTML de erros
**Descrição**: Gerar um `report.html` no final do download com:
- Recursos não encontrados (404)
- Recursos falhados (403, 500)
- URLs reescritas
- Estatísticas visuais

**Prioridade**: Baixa

---

### 4. Detecção automática de SPAs
**Descrição**: Melhorar detecção de frameworks SPA (React, Vue, Angular, Next.js, Nuxt).

**Implementação**:
- Detectar `__NEXT_DATA__`, `__NUXT__`, etc
- Aplicar correções específicas por framework
- Preservar state hydration

**Prioridade**: Média

---

### 5. Suporte a fontes locais
**Descrição**: Baixar e embedar Google Fonts, Adobe Fonts automaticamente.

**Prioridade**: Baixa

---

## 📝 Melhorias de Código

### 1. Testes automatizados
**Descrição**: Criar suite de testes com:
- Teste de rewrite de URLs
- Teste de preservação de estrutura
- Teste de integrity removal

**Prioridade**: Média

---

### 2. Configuração via arquivo
**Descrição**: Permitir configurar via `config.yaml`:
```yaml
timeouts:
  browser: 60000
  resource: 15000
  network_idle: 30000

features:
  webgl_interactions: true
  scroll_iterations: 20
  wait_after_webgl: 8000

filters:
  skip_domains:
    - google-analytics.com
    - facebook.com
```

**Prioridade**: Baixa

---

## 🎯 Roadmap

### Fase 1 - Correções Críticas ✅ COMPLETO
- [x] Corrigir erro "Is a directory" (pocketchangethe.world)
- [x] Remover CDN patterns hardcoded (tornar genérico)
- [x] Corrigir sourcemap removal (tornar recursivo)

### Fase 2 - UX e DX ✅ COMPLETO
- [x] Melhorar interface web (reset automático, logs persistentes)
- [x] Incluir servidor local (serve.py) nos downloads
- [x] Script de limpeza para IA (raw/ e clean/)
- [x] Setup unificado (local + deploy)
- [x] Documentação de sites testados (SITES.md)

### Fase 3 - Melhorias de Captura
- [ ] Investigar canvas hero (landonorris.com)
- [ ] Melhorar detecção de lazy loading

### Fase 4 - Developer Experience
- [ ] Testes automatizados
- [ ] Relatório HTML de erros

### Fase 5 - Features Avançadas
- [ ] Modo captura completa vs rápida
- [ ] Configuração via arquivo
- [ ] Suporte a fontes locais

---

## 🤝 Contribuindo

Para adicionar um item a este roadmap:
1. Descreva o problema/feature claramente
2. Adicione exemplos ou URLs que reproduzem o problema
3. Sugira prioridade (Alta/Média/Baixa)
4. Indique arquivos afetados

---

**Última atualização**: 06/Mar/2026

---

## 📝 Mudanças Recentes (06/Mar/2026)

### Correções de Bugs
- ✅ Bug 1.1: Erro "Is a directory" (URLs terminando com `/`)
- ✅ Bug 1.2: CDN patterns hardcoded removidos (agora genérico)
- ✅ Bug 1.3: Sourcemap removal agora recursivo

### Novas Features
- ✅ Interface web com Asimov Academy design (dark mode)
- ✅ Servidor local (`serve.py`) incluído em cada download
- ✅ Script de limpeza para IA (versões raw/ e clean/)
- ✅ Setup unificado (`setup.sh`) para local e deploy
- ✅ Documentação de sites testados (`SITES.md`)

### Próximos Passos
1. **Validação do usuário**: Testar todas as correções com sites reais
2. **Bug canvas hero**: Investigar por que landonorris.com hero não renderiza
3. **Novos testes**: Validar com pocketchangethe.world e outros sites da lista
