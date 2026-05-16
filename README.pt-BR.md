# 🗺️ Claude Atlas

> Audite seu setup do Claude Code. Encontre agents duplicados, gatilhos em conflito e arquivos de memória órfãos antes que silenciosamente atrapalhem seu workflow.

**Idiomas:** [English](README.md) · [Português 🇧🇷](README.pt-BR.md)

<p align="center">
  <img src="https://raw.githubusercontent.com/grippado/claude-atlas/main/docs/screenshots/atlas.png" width="300" alt="Claude Atlas logo" />
</p>

---

Se você vem acumulando coisas no `~/.claude/` há um tempo, provavelmente tem:

- Dois agents que fazem quase a mesma coisa, brigando pelos mesmos gatilhos.
- Um `CLAUDE.md` que você escreveu pra um projeto abandonado há meses.
- Uma skill global silenciosamente sombreada por uma versão com escopo de projeto em um dos seus repos.
- Nenhuma visão clara de quantos artefatos você acumulou no total.

**O Claude Atlas escaneia seu setup e expõe isso em segundos.** Roda no terminal pra um health check rápido, ou gera um dashboard HTML interativo de triagem pra trabalho mais profundo.

```bash
# Instalar
uv tool install claude-atlas

# Health check em 5 segundos (com health score 0-100)
claude-atlas check

# Dashboard de triagem completo
claude-atlas scan
```

Você recebe:

- Um **health score** (0-100) pra saber de relance se seu setup tá melhorando ou piorando.
- Um **dashboard de triagem** com previews lado a lado de cada par conflitante, "Copy fix prompt for Claude Code" em um clique, e um toggle de "Show diff".
- Um comando **`fix`** que te entrega um prompt prontinho pra colar no Claude Code — sem nunca tocar nos seus arquivos.
- Uma flag **`check --since`** que faz diff contra um run anterior pra você provar que o refactor de fato ajudou.
- Um **pre-commit hook** pra impedir que novos conflitos entrem sem ninguém ver.

Offline por padrão. Sem telemetria. Licença MIT. Docs em EN + PT-BR.

## Instalação

**Pré-requisitos:** Python 3.11+ e [`uv`](https://docs.astral.sh/uv/) (ou `pipx` / `pip`).

Se ainda não tem o `uv`:

```bash
# macOS (Homebrew)
brew install uv

# macOS / Linux (instalador oficial)
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Depois instale o claude-atlas:

```bash
# Recomendado: instalação isolada como ferramenta (a partir do PyPI)
uv tool install claude-atlas

# Ou com pipx
pipx install claude-atlas

# Ou pip puro
pip install claude-atlas
```

Para atualizar: `uv tool upgrade claude-atlas`.

### A partir do código-fonte

```bash
git clone https://github.com/grippado/claude-atlas.git
cd claude-atlas
uv sync --all-extras
uv run claude-atlas --help
```

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

Abra o HTML no navegador. O relatório abre direto na view **Triage**:

- Issues agrupadas por severidade (high / medium / low), cada uma como um card com frontmatter e trecho de body dos dois artefatos lado a lado.
- Ações por card: **Open source / target** no seu editor, **Show diff**, **Copy fix prompt** (com ou sem diff), **Skip** pra descartar falsos-positivos — o skip persiste no navegador via `localStorage`.
- Um **treemap de concentração** no topo mostra onde os problemas estão concentrados (por scope × kind); clique numa célula pra filtrar os cards.
- A aba **Graph** continua disponível pra explorar relacionamentos — é lazy-loaded, então o relatório fica leve se você fica só na triagem.

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

Requer `ANTHROPIC_API_KEY`. Reinstale com o extra `semantic` para trazer o SDK `anthropic`:

```bash
uv tool install "claude-atlas[semantic]"
```

## Comandos

```text
claude-atlas scan        escaneia e gera relatório completo
claude-atlas check       health check estilo lint (CI-friendly)
claude-atlas fix         gera prompt pro Claude Code com issues selecionadas
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

### Acompanhar a saúde ao longo do tempo

`--since` faz diff do scan atual contra um snapshot que você mesmo gravou — sem diretório de estado, sem telemetria, só dois arquivos JSON:

```bash
# Hoje: salva um snapshot
claude-atlas check --top 0 --format json > /tmp/atlas-snap.json

# Amanhã (depois de refatorar): veja o que mudou
claude-atlas check --since /tmp/atlas-snap.json
# → Found 9 issues (...) in 93 artifacts. Health: 82/100 (B).
#   Since snapshot: +1 new, -4 resolved. Health 75→82 (+7).
```

Útil antes/depois de refactors grandes pra confirmar que você realmente mexeu o ponteiro.

### Gerar um prompt de fix pro Claude Code

`claude-atlas fix` transforma issues detectadas num prompt markdown que você cola no Claude Code. A ferramenta nunca edita arquivos — só te entrega o prompt.

```bash
claude-atlas fix                          # picker interativo
claude-atlas fix --all                    # inclui todas as issues, sem prompt
claude-atlas fix --severity high --all    # todas as issues HIGH
claude-atlas fix | pbcopy                 # copia o prompt pro clipboard (macOS)
```

O picker aceita vírgula/range: `1,3,5-7` pega as issues 1, 3, 5, 6, 7. Use `all` (ou Enter direto) pra pegar tudo, `q` pra cancelar.

Se preferir escolher visualmente, abra o relatório HTML e use **Copy fix prompt** (ou **Copy prompt + diff**) em cards individuais — mesmo output, uma issue de cada vez.

### Como hook do [pre-commit](https://pre-commit.com)

Adicione ao seu `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/grippado/claude-atlas
    rev: v0.5.1  # ou qualquer tag de https://github.com/grippado/claude-atlas/releases
    hooks:
      - id: claude-atlas           # falha só em HIGH severity
      # - id: claude-atlas-strict  # falha em MEDIUM e HIGH
```

Os dois hooks rodam `claude-atlas check --quiet` contra o diretório `.claude/` do seu repo a cada commit.

## Estrutura do projeto

```
src/claude_atlas/
├── cli.py                 # CLI typer
├── models.py              # dataclasses + enums
├── scanner/
│   ├── discovery.py       # acha dirs .claude/ e arquivos CLAUDE.md
│   └── parsers.py         # frontmatter → Artifact
├── analysis/
│   ├── graph.py           # heurísticas → lista de Edge
│   └── llm_judge.py       # refinamento opcional via Anthropic
└── report/
    ├── renderer.py        # ScanResult → HTML
    └── templates/report.mustache
```

## Roadmap

Claude-atlas está em evolução ativa. Veja o [ROADMAP.pt-BR.md](ROADMAP.pt-BR.md) completo com princípios, versões lançadas e o que está planejado. Tracker ao vivo: [GitHub Milestones](https://github.com/grippado/claude-atlas/milestones).

**Lançado recentemente:**
- **v0.5.1** — `Show diff` por issue + `Copy prompt + diff` pra fixes mais afiados no Claude Code.
- **v0.5.0** — HTML triage dashboard: triage view como default, previews lado a lado, ações por issue, treemap de concentração, grafo como aba secundária lazy-loaded.
- **v0.4.0** — Fundação backend: health score, `check --since` diff, comando `fix`, templates de pre-commit.

**Em consideração:** plugin de status bar pra editor (VS Code) pra ter consciência ambiente do health score.

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
