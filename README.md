# 🗺️ Claude Atlas

> Scan, map, and visualize your Claude Code setup: agents, skills, slash commands, and `CLAUDE.md` memory files — all in one interactive graph.

**Languages:** [English](README.md) · [Português 🇧🇷](README.pt-BR.md)

---

## Why

As you accumulate agents, skills, slash commands, and `CLAUDE.md` files across global (`~/.claude/`) and project scopes, it becomes surprisingly hard to answer:

- Which skills are near-duplicates of each other?
- Which project-scoped agent silently overrides a global one?
- Which artifacts share the same triggers and will compete for activation?
- Which `CLAUDE.md` is actually in effect for this repo?

**claude-atlas** scans your machine, builds a relationship graph, and renders a standalone HTML report so you can see all of it at once.

## Install

```bash
uv tool install claude-atlas
# or from source:
uv pip install -e .
```

Python 3.11+ required.

## Quick start

```bash
# Scan ~/.claude + current dir, output to ./claude-atlas.html
claude-atlas scan

# Scan specific trees
claude-atlas scan --paths ~/work/arco --paths ~/work/flagbridge -o /tmp/atlas.html

# Auto-discover nested .claude/ dirs under several trees
claude-atlas scan --auto-discover ~/work --auto-discover ~/personal

# Refine duplicate candidates with Claude (needs ANTHROPIC_API_KEY)
claude-atlas scan --semantic
```

Open the resulting HTML in a browser. Click nodes to inspect, switch to the **Issues** tab to see what needs attention.

## What it detects

| Edge kind             | Meaning                                                                 |
|-----------------------|-------------------------------------------------------------------------|
| `duplicate_exact`     | Identical SHA-256 body hash — one is a literal copy of the other.       |
| `duplicate_semantic`  | Jaccard similarity ≥ 0.60 (suspicious) / ≥ 0.85 (probable).             |
| `overrides`           | Project artifact shadows a same-named global one.                        |
| `trigger_collision`   | Two artifacts share ≥ 2 distinctive trigger tokens.                      |
| `references`          | One artifact's body mentions another's name.                             |
| `contains`            | Memory file groups artifacts in the same `.claude/` root (UI only).      |

Thresholds live in `src/claude_atlas/analysis/graph.py` if you want to tune them.

## Optional: LLM-as-judge

With `--semantic`, pairs flagged by Jaccard are sent to the Anthropic API for a structured verdict (`duplicate` / `overlap` / `distinct`). Pairs the model calls "distinct" are dropped from the graph; the rest get the model's reasoning attached to the edge detail.

Requires `ANTHROPIC_API_KEY` and `uv pip install "claude-atlas[semantic]"` (adds the `anthropic` SDK).

## Commands

```text
claude-atlas scan        full scan + report
claude-atlas report      alias for scan with default flags
claude-atlas version     print version
```

Run any command with `--help` for full flags.

## Project layout

```
src/claude_atlas/
├── cli.py                 # typer CLI
├── models.py              # dataclasses + enums
├── scanner/
│   ├── discovery.py       # find .claude/ dirs and CLAUDE.md files
│   └── parsers.py         # frontmatter → Artifact
├── analysis/
│   ├── graph.py           # heuristics → Edge list
│   └── llm_judge.py       # optional Anthropic refinement
└── report/
    ├── renderer.py        # ScanResult → HTML
    └── templates/report.mustache
```

## Contributing

PRs welcome. Before opening one:

```bash
uv sync --all-extras
uv run pytest
uv run ruff check .
uv run mypy
```

## License

MIT — see [LICENSE](LICENSE).
