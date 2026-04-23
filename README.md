# 🗺️ Claude Atlas

> Audit your Claude Code setup. Find duplicate agents, conflicting triggers, and orphaned memory files before they silently break your workflow.

**Languages:** [English](README.md) · [Português 🇧🇷](README.pt-BR.md)

<p align="center">
  <img src="./docs/screenshots/atlas.png" width="300" alt="Claude Atlas logo" />
</p>

---

If you've been building out `~/.claude/` for a while, you probably have:

- Two agents that do nearly the same thing, competing for the same triggers.
- A `CLAUDE.md` you wrote for a project you abandoned months ago.
- A global skill quietly shadowed by a project-scoped version in one of your repos.
- No clear picture of how many artifacts you've accumulated total.

**Claude Atlas scans your setup and surfaces these in seconds.** Run it in your terminal for a quick health check, or generate an interactive HTML report for deeper triage.

```bash
# Install
uv tool install claude-atlas

# 5-second health check
claude-atlas check

# Full interactive report
claude-atlas scan
```

Offline by default. MIT licensed. Docs in EN + PT-BR.

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

## CI / pre-commit usage

Use `claude-atlas check` for lint-style health checks in scripts and CI:

```bash
# Default: fail on any HIGH-severity issue
claude-atlas check

# Pre-commit hook: only fail on duplicates and overrides
claude-atlas check --max-severity high --quiet

# CI with GitHub Actions annotations
claude-atlas check --format github

# Get everything as JSON for custom tooling
claude-atlas check --top 0 --format json
```

Exit codes: `0` (clean), `1` (issues found at threshold), `2` (error).

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

## Roadmap

Claude-atlas is in active evolution. See the full [ROADMAP.md](ROADMAP.md) for principles, released versions, and what's planned.

**Next up: v0.4.0 — HTML triage dashboard.** The graph view becomes a secondary tab; the primary view becomes a card-based triage dashboard with health score, side-by-side previews, and per-issue actions. Follow progress in [#1](https://github.com/grippado/claude-atlas/issues/1).

**Considering:** interactive fix-prompt export (`claude-atlas fix`), scan history diffing, pre-commit hook templates, editor status-bar plugin.

**Won't do:** automatic editing/deletion of artifacts, cloud sync, accounts, or support for non-Claude-Code AI tools. See the [anti-roadmap](ROADMAP.md#anti-roadmap-wont-do) for why.

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
