"""Discovery of Claude artifact locations on the filesystem."""

from __future__ import annotations

import os
from pathlib import Path

# Directory/file names we should NEVER descend into during auto-discover.
# Keeps walk cheap and avoids venvs, vendored deps, build artifacts.
_WALK_IGNORE = {
    "node_modules",
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    ".next",
    "dist",
    "build",
    "target",
    ".cache",
    ".turbo",
    ".nuxt",
    ".svelte-kit",
    ".idea",
    ".vscode",
}


def global_claude_dir() -> Path | None:
    """Return ~/.claude if it exists, else None."""
    p = Path.home() / ".claude"
    return p if p.is_dir() else None


def find_claude_dirs(
    roots: list[Path],
    max_depth: int = 4,
    follow_symlinks: bool = False,
) -> list[Path]:
    """
    Find `.claude/` directories underneath each root, up to ``max_depth`` levels.

    Depth is measured from the root (root itself = depth 0). A `.claude/` child of
    a directory at depth ``d`` is reported and its own subtree is pruned from the walk
    (we never descend into a `.claude/` while looking for *more* `.claude/` dirs).

    The global ``~/.claude`` dir is handled separately by ``global_claude_dir``;
    this function only walks user-provided roots.
    """
    found: list[Path] = []
    seen: set[Path] = set()

    for root in roots:
        root = root.expanduser().resolve()
        if not root.is_dir():
            continue

        for dirpath, dirnames, _filenames in os.walk(root, followlinks=follow_symlinks):
            current = Path(dirpath)
            # Depth relative to the root we started walking.
            try:
                depth = len(current.relative_to(root).parts)
            except ValueError:
                # Shouldn't happen, but be defensive with symlinks.
                continue

            # Prune noisy dirs before we descend.
            dirnames[:] = [
                d for d in dirnames if (d not in _WALK_IGNORE and not d.startswith("."))
                or d == ".claude"
            ]

            if ".claude" in dirnames:
                claude_path = (current / ".claude").resolve()
                if claude_path not in seen:
                    seen.add(claude_path)
                    found.append(claude_path)
                # Don't descend into `.claude/` itself looking for more `.claude/`.
                dirnames.remove(".claude")

            # Respect max_depth: stop descending past it.
            if depth >= max_depth:
                dirnames.clear()

    return found


def find_memory_files(roots: list[Path], max_depth: int = 4) -> list[Path]:
    """
    Find CLAUDE.md files hierarchically under each root.

    CLAUDE.md works by convention at any level of a repo, so we walk each root
    and collect every CLAUDE.md (and its common variants) we encounter.
    """
    found: list[Path] = []
    seen: set[Path] = set()
    names = {"CLAUDE.md", "CLAUDE.local.md"}

    for root in roots:
        root = root.expanduser().resolve()
        if not root.is_dir():
            continue

        for dirpath, dirnames, filenames in os.walk(root):
            current = Path(dirpath)
            try:
                depth = len(current.relative_to(root).parts)
            except ValueError:
                continue

            dirnames[:] = [d for d in dirnames if d not in _WALK_IGNORE]

            for fn in filenames:
                if fn in names:
                    p = (current / fn).resolve()
                    if p not in seen:
                        seen.add(p)
                        found.append(p)

            if depth >= max_depth:
                dirnames.clear()

    return found


def resolve_scan_targets(
    paths: list[Path],
    include_global: bool = True,
    auto_discover_from: list[Path] | None = None,
    max_depth: int = 4,
) -> list[Path]:
    """
    Resolve the final list of `.claude/` roots we should parse.

    - ``paths``: explicit `.claude/` dirs or dirs containing one.
    - ``include_global``: if True, prepend ``~/.claude`` if present.
    - ``auto_discover_from``: extra trees to walk looking for `.claude/` dirs.
    """
    roots: list[Path] = []
    seen: set[Path] = set()

    def _add(p: Path) -> None:
        p = p.resolve()
        if p not in seen and p.is_dir():
            seen.add(p)
            roots.append(p)

    if include_global:
        g = global_claude_dir()
        if g is not None:
            _add(g)

    for p in paths:
        p = p.expanduser()
        if p.name == ".claude":
            _add(p)
        elif (p / ".claude").is_dir():
            _add(p / ".claude")
        # Otherwise treat it as a tree to scan.
        elif p.is_dir():
            for c in find_claude_dirs([p], max_depth=max_depth):
                _add(c)

    if auto_discover_from:
        for c in find_claude_dirs(auto_discover_from, max_depth=max_depth):
            _add(c)

    return roots
