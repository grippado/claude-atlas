# Symlinked artifacts trigger false-positive `duplicate_exact` edges

- **Reported:** 2026-05-16
- **Fixed in:** `src/claude_atlas/scanner/parsers.py` (`scan_claude_dir`)
- **Affected versions:** ≤ 0.3.1 (likely all prior versions with the current scanner)
- **Severity:** HIGH issue surfaced by the tool, but the issue itself is a low-impact false positive — noisy reports, not data loss.

## Symptom

Running `claude-atlas check` on a `~/.claude/` setup that uses symlinks to alias commands/agents/skills produces `duplicate_exact` edges between paths that are actually the same file on disk.

Real-world example from a user setup managed by `atlas-sync`:

```
duplicate_exact (HIGH)
  Source: /Users/<user>/.claude/commands/organize.md (organize)
  Target: /Users/<user>/.claude/commands/organize:notes.md (organize:notes)
  Detail: identical SHA-256: 386869bec9de…
  Suggested fix: Identical content. Delete one — keep the one in the narrower scope.
```

`ls -la` reveals the chain:

```
organize.md       -> organize:notes.md
organize:notes.md -> ~/.notes/.claude/commands/organize.md   (real file)
```

Acting on the suggested fix would delete the symlink that backs the global `/organize` alias, breaking the command.

## How it was found

A user ran `claude-atlas check` and asked Claude Code to triage the reported issue. Verification:

1. `shasum -a 256` on both reported paths confirmed identical hashes.
2. `ls -la` on the same paths revealed both entries were symlinks.
3. `readlink` walked the chain to a single real file inside the user's `notes` vault.

The symlink chain was intentional: a tooling script (`atlas-sync`) installs a global alias by symlinking it to a scoped command file, which itself lives in a separate repo and is symlinked into `~/.claude/commands/`. The aliasing pattern is documented in the user's `ARCHITECTURE.md`.

## Root cause

`scan_claude_dir` in `src/claude_atlas/scanner/parsers.py` walks each artifact directory with `rglob("*.md")` and calls `parse_artifact_file` on every match. `Path.read_text` transparently follows symlinks, so two symlinks pointing to the same target produce two `Artifact` instances with the **same `body_hash`** but **different `path` values**.

Downstream, `analysis/graph.py::detect_exact_duplicates` groups artifacts by `body_hash` and emits a `DUPLICATE_EXACT` edge for every pair sharing a hash — including these symlink siblings.

The scanner had no notion of "we already processed this real file under a different name."

## Fix

Dedupe at scan time by resolved real path. In `scan_claude_dir`, keep a `set[Path]` of `path.resolve()` values already seen and skip subsequent matches that resolve to the same target:

```python
seen_real_paths: set[Path] = set()

def _scan(md_files: list[Path], kind: ArtifactKind) -> None:
    for md in md_files:
        try:
            real = md.resolve()
        except OSError:
            continue
        if real in seen_real_paths:
            continue
        seen_real_paths.add(real)
        a = parse_artifact_file(md, kind, root)
        if a:
            artifacts.append(a)
```

The first path encountered (alphabetical order, preserved by the existing `sorted(...)` call) wins and becomes the canonical `Artifact.path`. Subsequent symlinks to the same target are silently dropped.

### Why scanner-side, not analysis-side

Two places could have implemented the fix:

1. **Scanner** (chosen): skip duplicate real paths before `parse_artifact_file`. The artifact list never contains the duplicates, so *every* downstream analysis (semantic duplicates, override detection, trigger collisions, report rendering) benefits automatically.
2. **Analysis** (rejected): when grouping by `body_hash` in `detect_exact_duplicates`, skip pairs where `a.path.resolve() == b.path.resolve()`. Narrower, but leaves other detectors unaware that they're processing the same file twice.

The scanner fix is also cheaper: one `resolve()` per match versus N² comparisons during analysis.

### What is preserved

- **Real duplicates across different inodes** (two physically distinct files with identical content) are still detected — they have different real paths and both enter the artifact list.
- **Override detection** (same artifact name across global vs project scope) is unaffected — that uses name + scope, not paths.
- **Determinism**: the `sorted()` on `rglob` results makes "which path wins" deterministic across runs.

## Regression test

`tests/test_core.py::test_scan_claude_dir_dedupes_symlinks_to_same_target` builds a temp `.claude/commands/` containing one real file plus two symlinks pointing at it (one direct, one chained through the other symlink), then asserts that `scan_claude_dir` returns exactly one command artifact whose path is the first alphabetical entry.

## References

- File: `src/claude_atlas/scanner/parsers.py` (`scan_claude_dir`)
- Test: `tests/test_core.py::test_scan_claude_dir_dedupes_symlinks_to_same_target`
- Downstream consumer that emitted the false positive: `src/claude_atlas/analysis/graph.py::detect_exact_duplicates`
