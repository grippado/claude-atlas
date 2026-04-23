# Launch checklist — claude-atlas

Este é o guia passo-a-passo pra postar o lançamento do claude-atlas no LinkedIn e no dev.to.

## Pré-requisitos (fazer uma vez só)

- [ ] Avatar do repo configurado em https://github.com/grippado/claude-atlas/settings → upload `docs/screenshots/atlas-avatar.png`
- [ ] About section do repo preenchido (description, website, topics)
- [ ] Social preview image configurada (Settings → Options → Social preview → upload `docs/screenshots/atlas-logo.png`)

## Passo 1 — Gerar os screenshots

### Screenshot 1: terminal do `check`

**Comando:**
```bash
claude-atlas check --paths ~/.claude --no-global --top 5
```

**Como capturar:**
- Maximize a janela do terminal
- Tema escuro (iTerm2 com tema "Dracula" ou similar)
- Fonte legível (JetBrains Mono 14-16pt)
- `Cmd + Shift + 4` → `Space` → click na janela do terminal
- Salvar como `~/Desktop/linkedin-check.png`

### Screenshot 2: HTML report

**Gerar o HTML:**
```bash
claude-atlas scan --paths ~/.claude --no-global --output /tmp/atlas-launch.html
open /tmp/atlas-launch.html
```

Isso vai abrir o relatório visual no browser.

**Como capturar:**
- Maximize a janela do browser
- Zoom do browser em 100%
- Clique na aba **Issues** no painel direito
- `Cmd + Shift + 4` → `Space` → click na janela do browser
- Salvar como `~/Desktop/linkedin-html.png`

## Passo 2 — Postar no LinkedIn

- [ ] Abrir https://www.linkedin.com/ → clicar em "Começar publicação"
- [ ] Abrir `comms/linkedin-launch.md` e copiar o texto (a partir de "Abri meu..." até a última hashtag)
- [ ] Colar no LinkedIn
- [ ] Anexar imagens nesta ordem: `linkedin-check.png` primeiro, `linkedin-html.png` segundo
- [ ] Conferir: link está clicável? hashtags em azul? imagens carregaram?
- [ ] **Publicar**

### Nos primeiros 30-60 minutos pós-publicação (crítico!)

- [ ] Responder TODOS os comentários, mesmo que seja só "valeu [nome]!"
- [ ] Se alguém comentar com número ("rodei e encontrei X issues"), responder com pergunta aberta
- [ ] NÃO compartilhar sozinho ainda — deixar a reação orgânica acontecer

### Depois de 1-2h com boa tração (>15 reações)

- [ ] Compartilhar em grupos relevantes (Brasil Dev, GoBR)
- [ ] Mandar pra 2-3 amigos devs pedindo feedback

## Passo 3 — Postar no dev.to (depois do LinkedIn performar, pode ser no dia seguinte)

- [ ] Editar `comms/devto-launch.md` e mudar `published: false` → `published: true`
- [ ] Abrir https://dev.to/new
- [ ] Copiar o arquivo inteiro (incluindo o frontmatter YAML no topo)
- [ ] Colar no editor do dev.to
- [ ] Clicar em "Preview" pra conferir formatação
- [ ] Conferir: cover image carregou? code blocks estão com syntax highlight?
- [ ] **Publish**

## Passo 4 — Monitoramento (primeiros 2-3 dias)

- [ ] Responder comentários em ambos os canais
- [ ] Anotar issues/PRs que chegam no repo
- [ ] Se bater 50+ stars no GitHub em 48h, considerar post em Reddit r/ClaudeAI
- [ ] Capturar métricas pra post meta futuro: stars, issues abertas, comentários qualitativos
