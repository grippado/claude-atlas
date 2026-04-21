---
name: claude-atlas
description: Meta-skill for evolving the claude-atlas project itself. Use this skill whenever working inside the claude-atlas repository — adding new artifact kinds (agent/skill/command/memory + future ones), adding new edge detectors (duplicate, override, collision, reference + future ones), tuning heuristic thresholds (Jaccard, trigger overlap), extending the HTML report, or touching the Anthropic SDK LLM-judge pass. Triggers on: "claude-atlas", "atlas graph", "artifact detector", "edge kind", "jaccard threshold", "semantic duplicate", "trigger collision", "report template", "cytoscape", or any work inside this repo's `src/claude_atlas/` tree.
---

# claude-atlas meta-skill

You are working on **claude-atlas**, a CLI that scans a user's Claude Code setup and renders a relationship graph. This skill tells you the invariants that must survive every change.

## When to use

- Adding new `ArtifactKind` values (e.g., hooks, plugins).
- Adding new `EdgeKind` values or new detectors in `analysis/graph.py`.
- Tuning thresholds (`JACCARD_SUSPICIOUS`, `JACCARD_DUPLICATE`, `TRIGGER_COLLISION_MIN_SHARED`).
- Evolving the HTML report (`report/renderer.py` + `report/templates/report.mustache`).
- Touching the LLM-as-judge pass in `analysis/llm_judge.py`.

## Core invariants

1. **Heuristics are deterministic and LLM-free by default.** The `--semantic` flag is opt-in. Never make network I/O a default. The CLI must be usable offline.
2. **Detectors are pure functions.** `detect_*` in `graph.py` take `list[Artifact]` and return `list[Edge]`. No side effects, no I/O, no global state. Makes them trivially testable.
3. **Artifact IDs are stable and unique.** The current recipe is `"{kind}:{scope}:{name}:{path}"`. If you change it, update every detector that builds edges by ID.
4. **The HTML report is self-contained.** Cytoscape is loaded via CDN, but there's no other runtime network dependency. Don't add fetches to the template.
5. **PT-BR + EN docs are mandatory.** Every user-facing doc change goes in both `README.md` and `README.pt-BR.md`. Keep them structurally identical.
6. **Copyright / ownership:** every new file Gabriel's tooling creates stays MIT. Never add a non-OSI-approved header.

## Adding a new edge detector (pattern)

1. Add the enum value to `EdgeKind` in `models.py`.
2. If it should appear in the "Issues" tab, add it to `_ISSUE_KINDS` in `report/renderer.py` and to `ScanResult.issues` in `models.py`.
3. Write a `detect_<thing>(artifacts: list[Artifact]) -> list[Edge]` in `analysis/graph.py`. Keep it pure.
4. Call it from `build_all_edges`.
5. Pick a color in `_edge_color` (`report/renderer.py`) and add a legend entry in the Mustache template.
6. Write at least one focused test in `tests/test_core.py` that constructs artifacts by hand and asserts exactly the edges you expect.

## Adding a new artifact kind

1. Add to `ArtifactKind` enum.
2. Extend `scan_claude_dir` in `scanner/parsers.py` to find it.
3. Add a color in `_node_color` and a legend dot in the template.
4. Decide whether existing detectors should include it. Default: most detectors skip `MEMORY` — follow that precedent unless there's a reason not to.

## Threshold changes

Thresholds live at the top of `analysis/graph.py` as module constants. Never hardcode them inside detector bodies — keep them discoverable. If you add a new threshold, mention it in both READMEs' "What it detects" section.

## LLM judge etiquette

- `llm_judge.py` imports `anthropic` lazily inside `refine_with_llm`. Never add a top-level import.
- The default model is pinned to `DEFAULT_MODEL` (currently `claude-sonnet-4-6`). The CLI already exposes `--model` for overrides — don't bypass it.
- The judge only ever re-examines `DUPLICATE_SEMANTIC` edges. Don't widen its scope without updating docs.
- Output must stay structured JSON. If you extend the verdict schema, update both the prompt and the parser together.

## Testing discipline

- `pytest` must pass on every commit. The suite is cheap; run it.
- `ruff check .` and `mypy` are soft-gated (not strict), but new code should not introduce new warnings.
- Prefer constructing `Artifact` objects directly in tests (see `_make_artifact` in `test_core.py`) rather than writing files to disk — fewer moving parts.
