# 🗺️ Claude Atlas

> Audite seu setup do Claude Code. Encontre agents duplicados, gatilhos em conflito e arquivos de memória órfãos antes que silenciosamente atrapalhem seu workflow.

**Idiomas:** [English](README.md) · [Português 🇧🇷](README.pt-BR.md)

<p align="center">
  <img src="./docs/screenshots/atlas.png" width="300" alt="Claude Atlas logo" />
</p>

---

Se você vem acumulando coisas no `~/.claude/` há um tempo, provavelmente tem:

- Dois agents que fazem quase a mesma coisa, brigando pelos mesmos gatilhos.
- Um `CLAUDE.md` que você escreveu pra um projeto abandonado há meses.
- Uma skill global silenciosamente sombreada por uma versão com escopo de projeto em um dos seus repos.
- Nenhuma visão clara de quantos artefatos você acumulou no total.

**O Claude Atlas escaneia seu setup e expõe isso em segundos.** Roda no terminal pra um health check rápido, ou gera um relatório HTML interativo pra triagem profunda.

```bash
# Instalar
uv tool install claude-atlas

# Check de saúde em 5 segundos
claude-atlas check

# Relatório interativo completo
claude-atlas scan
```

Offline por padrão. Licença MIT. Docs em EN + PT-BR.

## Instalação

```bash
uv tool install claude-atlas
# ou a partir do código:
uv pip install -e .
```

Requer Python 3.11+.

## Começo rápido

```bash
# Escaneia ~/.claude + diretório atual, gera ./claude-atlas.html
claude-atlas scan

# Árvores específicas
claude-atlas scan --paths ~/work/arco --paths ~/work/flagbridge -o /tmp/atlas.html

# Auto-descoberta de .claude/ aninhados
claude-atlas scan --auto-discover ~/work --auto-discover ~/personal

# Refina candidatos a duplicata com o Claude (precisa de ANTHROPIC_API_KEY)
claude-atlas scan --semantic
```

Abra o HTML no navegador. Clique nos nós pra inspecionar, vá pra aba **Issues** pra ver o que merece atenção.

## O que é detectado

| Tipo de aresta        | Significado                                                              |
|-----------------------|--------------------------------------------------------------------------|
| `duplicate_exact`     | Hash SHA-256 idêntico — é cópia literal mesmo.                           |
| `duplicate_semantic`  | Similaridade de Jaccard ≥ 0.60 (suspeita) / ≥ 0.85 (provável).           |
| `overrides`           | Artefato de projeto sobrescreve global de mesmo nome.                     |
| `trigger_collision`   | Dois artefatos compartilham ≥ 2 triggers distintivos.                     |
| `references`          | O corpo de um artefato menciona o nome do outro.                          |
| `contains`            | Memory file agrupa artefatos do mesmo `.claude/` (só pra visual).        |

Thresholds ficam em `src/claude_atlas/analysis/graph.py` caso queira ajustar.

## Opcional: LLM-as-judge

Com `--semantic`, pares flagados pelo Jaccard vão pra API da Anthropic pra um veredito estruturado (`duplicate` / `overlap` / `distinct`). Pares que o modelo considera "distinct" são removidos do grafo; os outros recebem a justificativa do modelo no detalhe da aresta.

Requer `ANTHROPIC_API_KEY` e `uv pip install "claude-atlas[semantic]"` (adiciona o SDK `anthropic`).

## Comandos

```text
claude-atlas scan        escaneia e gera relatório completo
claude-atlas report      alias de scan com flags padrão
claude-atlas version     imprime a versão
```

Qualquer comando aceita `--help`.

## Uso em CI / pre-commit

Use `claude-atlas check` para checks lint-style em scripts e CI:

```bash
# Default: falha se houver qualquer issue HIGH
claude-atlas check

# Pre-commit hook: só falha em duplicatas e overrides
claude-atlas check --max-severity high --quiet

# CI com annotations do GitHub Actions
claude-atlas check --format github

# Tudo como JSON pra ferramentas customizadas
claude-atlas check --top 0 --format json
```

Exit codes: `0` (limpo), `1` (issues encontradas no threshold), `2` (erro).

## Roadmap

Claude-atlas está em evolução ativa. Veja o [ROADMAP.pt-BR.md](ROADMAP.pt-BR.md) completo com princípios, versões lançadas e o que está planejado.

**Próximo: v0.4.0 — HTML triage dashboard.** O graph view vira aba secundária; a view principal passa a ser um dashboard de triagem em cards, com health score, previews lado a lado e ações por issue. Acompanhe em [#1](https://github.com/grippado/claude-atlas/issues/1).

**Em consideração:** export interativo de fix-prompt (`claude-atlas fix`), diff entre scans, templates de pre-commit hook, plugin de status bar pra editor.

**Não vamos fazer:** edição/deleção automática de artefatos, cloud sync, accounts, nem suporte a AI tools que não sejam Claude Code. Veja o [anti-roadmap](ROADMAP.pt-BR.md#anti-roadmap-não-vamos-fazer) pra entender o porquê.

## Contribuindo

PRs bem-vindos. Antes de abrir:

```bash
uv sync --all-extras
uv run pytest
uv run ruff check .
uv run mypy
```

## Licença

MIT — veja [LICENSE](LICENSE).
