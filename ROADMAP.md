# Roadmap

> **Languages:** [English](ROADMAP.md) · [Português 🇧🇷](ROADMAP.pt-BR.md)

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

## Next: v0.4.0 — HTML triage dashboard

**Status:** Planned. Will start ~2 weeks after v0.3.0 release, informed by real usage.

### Why

The current HTML report uses an Obsidian-style graph view as its centerpiece. After dogfooding, we've observed a fundamental mismatch:

> Graph views are good for *discovering* unknown structure. They're mediocre for *deciding* what to do.

When you open the report, you usually want to **act** — triage issues, decide what to merge, what to delete, what to rename. The graph forces you to interpret topology before reaching action. The actual work happens in the sidebar's Issues tab.

v0.4.0 inverts the priority: **the dashboard becomes the primary view; the graph becomes a secondary tab for when you genuinely want to explore structure**.

### What changes

- **Triage view as the default.** Issues rendered as full cards in the main area, not a cramped sidebar list.
- **Side-by-side preview.** Each issue card shows both artifacts' frontmatter and body excerpt next to each other, so you can compare without opening files.
- **Health score.** A 0-100 number at the top, computed from issue count weighted by severity. Gives a quick sense of "is this getting better or worse over time".
- **Per-issue actions.** Each card has `[skip]`, `[open in editor]`, and `[copy fix prompt]` buttons. Skip persists locally so you can dismiss known false-positives.
- **Concentration overview.** A small treemap by scope → kind, sized by issue density. Replaces the graph as the at-a-glance "where are the problems concentrated?" answer.
- **Graph as secondary tab.** Still available, still useful for exploring relationships. Just not the front door.

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

### Out of scope (deliberately)

- Automatic application of fixes. The tool will never edit or delete your artifacts on its own. The `[fix]` button copies a prompt for you to paste into Claude Code — no automation.
- Server-side rendering, login, or sync. The output stays a single offline HTML file.
- Persistence beyond `localStorage`. "Skip" decisions stay in your browser. No `~/.claude-atlas/` state directory unless we revisit this in a later version.

## Considering for v0.5.0+

Documented but uncommitted. Order is rough priority.

- **`claude-atlas fix --interactive`** — terminal version of the `[copy fix prompt]` button. Pick issues, get a markdown prompt ready for Claude Code.
- **Scan history / diff.** `claude-atlas check --since last` would show what changed in your setup since the previous run. Useful for "did my refactor make things better?".
- **Pre-commit hook templates.** A `.pre-commit-hooks.yaml` so users add `claude-atlas check` to their repos with one line.
- **Editor status bar plugin.** Tiny VS Code extension that runs `check --quiet` and shows the health score. Bonus: click to open the full HTML report.

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
