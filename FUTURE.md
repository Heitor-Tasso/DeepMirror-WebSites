# Features e Correções Futuras

### 1. Suporte a Lazy Loading mais agressivo
**Descrição**: Algumas imagens/recursos só carregam em interações específicas.

**Implementação sugerida**:
- Adicionar opção de "scroll completo" (rolar até o final múltiplas vezes)
- Clicks automáticos em botões/tabs detectados
- Wait mais longo em sites com muitas animações

**Prioridade**: Baixa

### 2. Modo de captura "completa" vs "rápida"
**Descrição**: Permitir usuário escolher entre:
- **Rápida**: Captura básica (atual)
- **Completa**: Todas interações, scroll múltiplo, esperas mais longas

**Prioridade**: Média

### 3. Detecção automática de SPAs
**Descrição**: Melhorar detecção de frameworks SPA (React, Vue, Angular, Next.js, Nuxt).

**Implementação**:
- Detectar `__NEXT_DATA__`, `__NUXT__`, etc
- Aplicar correções específicas por framework
- Preservar state hydration

**Prioridade**: Média

### 4. Suporte a fontes locais
**Descrição**: Baixar e embedar Google Fonts, Adobe Fonts automaticamente.

**Prioridade**: Baixa

## 🤝 Contribuindo

Para adicionar um item a este roadmap:
1. Descreva o problema/feature claramente
2. Adicione exemplos ou URLs que reproduzem o problema
3. Sugira prioridade (Alta/Média/Baixa)
4. Indique arquivos afetados
