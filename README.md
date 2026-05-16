# 🗺️ Claude Atlas

> Audit your Claude Code setup. Find duplicate agents, conflicting triggers, and orphaned memory files before they silently break your workflow.

**Languages:** [English](README.md) · [Português 🇧🇷](README.pt-BR.md)

<p align="center">
  <img src="https://raw.githubusercontent.com/grippado/claude-atlas/main/docs/screenshots/atlas.png" width="300" alt="Claude Atlas logo" />
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

**Prerequisites:** Python 3.11+ and [`uv`](https://docs.astral.sh/uv/) (or `pipx` / `pip`).

If you don't have `uv` yet:

```bash
# macOS (Homebrew)
brew install uv

# macOS / Linux (official installer)
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Then install claude-atlas:

```bash
# Recommended: isolated tool install (from PyPI)
uv tool install claude-atlas

# Or with pipx
pipx install claude-atlas

# Or plain pip
pip install claude-atlas
```

To upgrade: `uv tool upgrade claude-atlas`.

### From source

```bash
git clone https://github.com/grippado/claude-atlas.git
cd claude-atlas
uv sync --all-extras
uv run claude-atlas --help
```

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

Requires `ANTHROPIC_API_KEY`. Reinstall with the `semantic` extra to pull the `anthropic` SDK:

```bash
uv tool install "claude-atlas[semantic]"
```

## Commands

```text
claude-atlas scan        full scan + report
claude-atlas check       lint-style health check (CI-friendly)
claude-atlas fix         generate a Claude Code prompt for selected issues
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

### Track health over time

`--since` diffs the current scan against a previous snapshot you wrote yourself — no state directory, no telemetry, just two JSON files:

```bash
# Today: save a snapshot
claude-atlas check --top 0 --format json > /tmp/atlas-snap.json

# Tomorrow (after some refactoring): see what changed
claude-atlas check --since /tmp/atlas-snap.json
# → Found 9 issues (...) in 93 artifacts. Health: 82/100 (B).
#   Since snapshot: +1 new, -4 resolved. Health 75→82 (+7).
```

Useful before/after big refactors to confirm you actually moved the needle.

### Generate a fix prompt for Claude Code

`claude-atlas fix` turns detected issues into a markdown prompt you paste into Claude Code. The tool itself never edits files — it just hands you the prompt.

```bash
claude-atlas fix                          # interactive picker
claude-atlas fix --all                    # include every issue, no prompt
claude-atlas fix --severity high --all    # all HIGH-severity issues
claude-atlas fix | pbcopy                 # copy prompt to clipboard (macOS)
```

The interactive picker accepts comma/range syntax: `1,3,5-7` picks issues 1, 3, 5, 6, 7. Pass `all` (or just press Enter) to take everything, `q` to cancel.

### As a [pre-commit](https://pre-commit.com) hook

Add to your `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/grippado/claude-atlas
    rev: v0.5.0  # or any tag from https://github.com/grippado/claude-atlas/releases
    hooks:
      - id: claude-atlas           # fails only on HIGH severity
      # - id: claude-atlas-strict  # fails on MEDIUM and HIGH
```

Both hooks run `claude-atlas check --quiet` against your repo's `.claude/` directory on every commit.

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
