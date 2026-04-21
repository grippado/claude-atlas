# 🗺️ Claude Atlas

> Escaneia, mapeia e visualiza sua configuração do Claude Code: agents, skills, slash commands e arquivos `CLAUDE.md` — tudo num grafo interativo.

**Idiomas:** [English](README.md) · [Português 🇧🇷](README.pt-BR.md)

---

## Por quê

Conforme você acumula agents, skills, slash commands e `CLAUDE.md` entre escopo global (`~/.claude/`) e projetos, fica surpreendentemente difícil responder:

- Quais skills são quase-duplicatas umas das outras?
- Qual agent de projeto está silenciosamente sobrescrevendo um global?
- Quais artefatos compartilham os mesmos triggers e vão competir pela ativação?
- Qual `CLAUDE.md` está de fato em vigor pra este repo?

**claude-atlas** escaneia sua máquina, monta o grafo de relacionamentos e gera um relatório HTML standalone pra você ver tudo de uma vez.

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
