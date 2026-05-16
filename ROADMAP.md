# Roadmap

> **Languages:** [English](ROADMAP.md) · [Português 🇧🇷](ROADMAP.pt-BR.md)
>
> **Live tracker:** [GitHub Milestones](https://github.com/grippado/claude-atlas/milestones) — each bullet below links to its tracking issue.

## Principles

These guide every release. They're also the easiest way to know if a feature request fits the project.

- **Heuristics first, LLM optional.** Detection runs offline by default. The Anthropic API is opt-in via `--semantic` and only refines pre-flagged candidates.
- **Always offline-capable.** No telemetry, no auth, no cloud. Your `.claude/` setup never leaves your machine.
- **Apoia decisão humana.** The tool surfaces issues and suggests fixes. It does not delete, edit, or modify your artifacts. You decide.
- **Bilingual docs (EN + PT-BR).** Always.
- **Single-file outputs where possible.** The HTML report is one self-contained file. The CLI prints to stdout. No state directories required.

## Released

| Version | Theme                                | Highlights                                                                       |
|---------|--------------------------------------|----------------------------------------------------------------------------------|
| v0.1.0  | Initial release                      | Scan agents/skills/commands/CLAUDE.md, Cytoscape graph view, MIT license.        |
| v0.1.1  | Frontmatter resilience               | Fallback regex parser for malformed multi-line YAML descriptions.                |
| v0.2.0  | Signal + UX overhaul                 | Severity classification, domain stopwords, grouped issues, search, orphan panel. |
| v0.3.0  | `check` command for CI               | Lint-style output, exit codes, text/json/github formats.                         |
| v0.4.0  | Backend foundation                   | Health score, `check --since` diff, `fix` command, pre-commit hook templates.    |
| v0.5.0  | HTML triage dashboard                | Triage view as default, side-by-side previews, per-issue actions, treemap, lazy graph. |
| v0.5.1  | Diff button                          | Per-issue `Show diff` + `Copy prompt + diff` for sharper Claude Code fixes.      |
| v0.5.2  | Symlink dedupe                       | Scanner dedupes artifacts by real path, killing false-positive duplicates from symlinks. |

## Considering for v0.6.0+

Documented but uncommitted. Order is rough priority.

- **Editor status bar plugin.** ([#17](https://github.com/grippado/claude-atlas/issues/17)) Tiny VS Code extension that runs `check --quiet` and shows the health score. Bonus: click to open the full HTML report. Likely a separate repo.

## Anti-roadmap (won't do)

These are explicit "no". Comunicating them up front keeps the project focused and avoids wasted PRs.

- **Automatic deletion or modification of artifacts.** Even with confirmation. The blast radius is too high; we trust the user, not the heuristic.
- **Cloud sync, accounts, or telemetry.** Claude-atlas is a local DX tool. It stays local.
- **Support for non-Claude-Code AI tools.** Cursor rules, Aider configs, Continue files, etc. are out of scope. The detection heuristics are tuned for Claude Code's specific structure.
- **A web service.** No SaaS version. No "claude-atlas as a service". The CLI + HTML report is the product.

## Contributing

PRs welcome, especially for:

- New artifact kinds (Claude Code may add hooks, plugins, etc.).
- Better heuristics — particularly false-positive reductions you've found in your own setup.
- PT-BR or EN doc improvements.
- Pre-commit hook templates and CI examples.

Before submitting, run:

```bash
uv sync --all-extras
uv run pytest
uv run ruff check .
```

And if your change touches user-visible behavior, update both `README.md` and `README.pt-BR.md`. Both languages, always.
