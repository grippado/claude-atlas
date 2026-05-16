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
| v0.5.0  | HTML triage dashboard               | Triage view como default, previews lado a lado, ações por issue, treemap, grafo lazy. |
| v0.5.1  | Botão de diff                       | `Show diff` por issue + `Copy prompt + diff` pra fixes mais afiados no Claude Code.   |

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
