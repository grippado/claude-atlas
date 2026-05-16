# Roadmap

> **Idiomas:** [English](ROADMAP.md) · [Português 🇧🇷](ROADMAP.pt-BR.md)
>
> **Tracker ao vivo:** [GitHub Milestones](https://github.com/grippado/claude-atlas/milestones) — cada bullet abaixo aponta para a issue correspondente.

## Princípios

Guiam cada release. Também são a forma mais rápida de saber se uma feature pedida faz sentido no projeto.

- **Heurísticas primeiro, LLM opcional.** A detecção roda offline por padrão. A API da Anthropic é opt-in via `--semantic` e só refina candidatos já flagados.
- **Sempre offline-capable.** Sem telemetria, sem auth, sem cloud. Sua configuração `.claude/` nunca sai da sua máquina.
- **Apoia decisão humana.** A ferramenta expõe issues e sugere fixes. Não deleta, edita nem modifica seus artefatos. Você decide.
- **Docs bilíngues (EN + PT-BR).** Sempre.
- **Outputs em arquivo único quando possível.** O relatório HTML é um arquivo self-contained. O CLI imprime no stdout. Sem diretórios de estado obrigatórios.

## Released

| Versão  | Tema                                | Destaques                                                                      |
|---------|-------------------------------------|--------------------------------------------------------------------------------|
| v0.1.0  | Release inicial                     | Scan de agents/skills/commands/CLAUDE.md, graph Cytoscape, licença MIT.        |
| v0.1.1  | Resiliência de frontmatter          | Fallback regex pro parser quando o YAML multi-linha é inválido.                |
| v0.2.0  | Sinal + reforma de UX               | Severidade, stopwords de domínio, issues agrupadas, search, painel de órfãos.  |
| v0.3.0  | Comando `check` pra CI              | Output lint-style, exit codes, formatos text/json/github.                      |
| v0.4.0  | Fundação backend                    | Health score, `check --since`, comando `fix`, templates de pre-commit.         |

## Próximo: v0.5.0 — HTML triage dashboard

**Status:** Planejado. A v0.4.0 (backend: health score, diff, fix prompts) deu a camada de dados; a v0.5.0 coloca tudo isso atrás de uma UI focada em ação, não em exploração.

### Por quê

O relatório HTML atual usa graph view estilo Obsidian como peça central. Depois de dogfooding, observamos um mismatch fundamental:

> Graph views são boas pra *descobrir* estrutura desconhecida. São medianas pra *decidir* o que fazer.

Quando você abre o relatório, geralmente quer **agir** — triar issues, decidir o que mergear, o que deletar, o que renomear. O grafo te obriga a interpretar topologia antes de chegar à ação. O trabalho real acontece na aba Issues do sidebar.

A v0.5.0 inverte a prioridade: **o dashboard vira a view principal; o grafo vira aba secundária pra quando você realmente quiser explorar estrutura**.

### O que muda

- **Triage view como default.** ([#9](https://github.com/grippado/claude-atlas/issues/9)) Issues renderizadas como cards completos na área central, não numa lista apertada no sidebar.
- **Preview lado a lado.** ([#10](https://github.com/grippado/claude-atlas/issues/10)) Cada card mostra frontmatter e trecho do body dos dois artefatos um ao lado do outro, pra comparar sem abrir arquivos.
- **Ações por issue.** ([#11](https://github.com/grippado/claude-atlas/issues/11)) Cada card tem botões `[skip]`, `[open in editor]` e `[copy fix prompt]`. O skip persiste localmente, então você dispensa falsos-positivos conhecidos.
- **Overview de concentração.** ([#12](https://github.com/grippado/claude-atlas/issues/12)) Um treemap pequeno por scope → kind, dimensionado por densidade de issues. Substitui o grafo como resposta instantânea pra "onde estão concentrados os problemas?".
- **Grafo como aba secundária.** ([#13](https://github.com/grippado/claude-atlas/issues/13)) Ainda disponível, ainda útil pra explorar relacionamentos. Só não é mais a porta de entrada.

O health-score ([#8](https://github.com/grippado/claude-atlas/issues/8), entregue na v0.4.0) já está no header.

### Wireframe

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ 🗺️  Claude Atlas        Health: 78/100  ●  72 artifacts · 17 issues  [search]│
├──────────────────────────────────────────────────────────────────────────────┤
│ severity: ☑ high  ☑ medium  ☐ low      view: ◉ Triage  ○ Graph  ○ Stats     │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─ HIGH ─────────────────────────────────────────────────────────────────┐ │
│  │  🔴  studio-coach.md  ↔  coach-old.md            [skip] [open] [fix]   │ │
│  │      duplicate_exact · identical SHA-256                                │ │
│  │      ┌─ studio-coach.md ──────┐  ┌─ coach-old.md ─────────┐            │ │
│  │      │ name: studio-coach     │  │ name: studio-coach     │            │ │
│  │      │ description: PROACT... │  │ description: PROACT... │            │ │
│  │      │ ...                    │  │ ...                    │            │ │
│  │      └────────────────────────┘  └────────────────────────┘            │ │
│  │      💡 Delete one — keep the one in the narrower scope.               │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  ┌─ MEDIUM ───────────────────────────────────────────────────────────────┐ │
│  │  🟠  refactor-helper.md  ↔  code-cleaner.md      [skip] [open] [fix]   │ │
│  │      trigger_collision · 4 shared distinctive triggers                 │ │
│  │      shared: refactor, cleanup, quality, architecture                  │ │
│  │      💡 Rename triggers in code-cleaner to disambiguate.               │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  ┌─ Concentration overview ───────────────────────────────────────────────┐ │
│  │  ┌──────────────┬──────────────┬─────────┐                             │ │
│  │  │              │              │         │   block size = artifact     │ │
│  │  │   agents/    │   skills/    │ commands│   color = max severity      │ │
│  │  │              │              │         │                             │ │
│  │  └──────────────┴──────────────┴─────────┘                             │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Fora de escopo (deliberadamente)

- Aplicação automática de fixes. A ferramenta nunca vai editar ou deletar seus artefatos sozinha. O botão `[fix]` copia um prompt pra você colar no Claude Code — sem automação.
- Renderização server-side, login, ou sync. O output continua um único arquivo HTML offline.
- Persistência além de `localStorage`. Decisões de "skip" ficam no seu navegador. Nenhum diretório `~/.claude-atlas/` de estado, a menos que revisitemos isso numa versão futura.

## Em consideração para v0.6.0+

Documentado mas sem compromisso. Ordem é prioridade aproximada.

- **Plugin de status bar pra editor.** ([#17](https://github.com/grippado/claude-atlas/issues/17)) Extensão pequena do VS Code que roda `check --quiet` e mostra o health score. Bônus: click abre o relatório HTML completo. Provavelmente em repo separado.

## Anti-roadmap (não vamos fazer)

Isso é "não" explícito. Comunicar de cara mantém o projeto focado e evita PRs desperdiçados.

- **Deleção ou modificação automática de artefatos.** Mesmo com confirmação. O blast radius é alto demais; confiamos no usuário, não na heurística.
- **Cloud sync, accounts, ou telemetria.** Claude-atlas é uma ferramenta de DX local. Continua local.
- **Suporte pra AI tools que não sejam Claude Code.** Rules do Cursor, configs do Aider, arquivos do Continue, etc. estão fora de escopo. As heurísticas são calibradas pra estrutura específica do Claude Code.
- **Um web service.** Sem versão SaaS. Sem "claude-atlas as a service". CLI + relatório HTML é o produto.

## Contribuindo

PRs bem-vindos, especialmente pra:

- Novos tipos de artefato (o Claude Code pode adicionar hooks, plugins, etc.).
- Heurísticas melhores — principalmente reduções de falso-positivo que você tenha descoberto no seu próprio setup.
- Melhorias em docs PT-BR ou EN.
- Templates de pre-commit hook e exemplos de CI.

Antes de mandar, roda:

```bash
uv sync --all-extras
uv run pytest
uv run ruff check .
```

E se sua mudança afeta comportamento user-visible, atualiza `README.md` e `README.pt-BR.md`. Os dois idiomas, sempre.
