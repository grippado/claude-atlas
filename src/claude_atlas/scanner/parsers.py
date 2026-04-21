"""Parse individual Claude artifact files into Artifact dataclasses."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

import frontmatter

from claude_atlas.models import Artifact, ArtifactKind, Scope

# Token pattern for Jaccard/trigger extraction: alphanumeric words of length >= 3.
_WORD_RE = re.compile(r"[A-Za-z][A-Za-z0-9_-]{2,}")

# Fallback regex for when python-frontmatter chokes on malformed YAML.
# Many real-world agent/skill files use multi-line `description:` values without
# proper YAML block scalar indicators (e.g., `description: text that wraps\nacross lines\n`),
# which is technically invalid YAML and makes the parser raise.
_FRONTMATTER_BLOCK_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?(.*)", re.DOTALL)
_FM_NAME_RE = re.compile(r"^name:\s*(.+?)\s*$", re.MULTILINE)
_FM_DESC_RE = re.compile(
    r"^description:\s*(.+?)(?=^[a-zA-Z_][a-zA-Z0-9_-]*:\s|\Z)",
    re.MULTILINE | re.DOTALL,
)


def _best_effort_frontmatter(raw: str) -> tuple[dict[str, Any], str]:
    """
    Best-effort extraction when python-frontmatter can't parse the YAML block.

    Returns ``(metadata, body)``. If no frontmatter block is present at all,
    returns ``({}, raw)`` unchanged.
    """
    block_match = _FRONTMATTER_BLOCK_RE.match(raw)
    if not block_match:
        return {}, raw

    fm_block = block_match.group(1)
    body = block_match.group(2)

    meta: dict[str, Any] = {}

    name_m = _FM_NAME_RE.search(fm_block)
    if name_m:
        meta["name"] = name_m.group(1).strip().strip("'\"")

    desc_m = _FM_DESC_RE.search(fm_block)
    if desc_m:
        # Collapse whitespace in multi-line descriptions so the regex survives
        # the multi-line YAML that broke the real parser in the first place.
        desc = re.sub(r"\s+", " ", desc_m.group(1).strip()).strip("'\"")
        meta["description"] = desc

    return meta, body


def _hash_body(body: str) -> str:
    return hashlib.sha256(body.strip().encode("utf-8")).hexdigest()


def _scope_for(root: Path) -> Scope:
    """Infer scope from the .claude root path."""
    try:
        home = Path.home().resolve()
        if root.resolve() == (home / ".claude").resolve():
            return Scope.GLOBAL
    except Exception:
        pass
    return Scope.PROJECT


def _extract_triggers(fm: dict[str, Any], body: str, description: str) -> list[str]:
    """
    Pull trigger-ish tokens from frontmatter fields and the description.

    We're deliberately loose here: triggers/keywords/when_to_use/aliases are all
    common patterns across agents/skills/commands. For everything else we fall
    back to distinctive tokens from the description.
    """
    triggers: list[str] = []

    for key in ("triggers", "keywords", "aliases", "tags", "when_to_use"):
        v = fm.get(key)
        if isinstance(v, list):
            triggers.extend(str(x) for x in v)
        elif isinstance(v, str):
            triggers.extend(s.strip() for s in v.split(",") if s.strip())

    if not triggers and description:
        tokens = _WORD_RE.findall(description.lower())
        # Keep the first ~8 longer, more distinctive tokens.
        seen: set[str] = set()
        for t in tokens:
            if len(t) >= 5 and t not in seen:
                seen.add(t)
                triggers.append(t)
                if len(triggers) >= 8:
                    break

    return [t.lower().strip() for t in triggers if t]


def parse_artifact_file(
    path: Path,
    kind: ArtifactKind,
    root: Path,
) -> Artifact | None:
    """Parse a single file into an Artifact. Returns None if unparseable."""
    try:
        raw = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None

    try:
        post = frontmatter.loads(raw)
        fm: dict[str, Any] = dict(post.metadata)
        body: str = post.content
    except Exception:
        # YAML parsing failed — commonly due to multi-line description values
        # without proper block-scalar indicators. Fall back to regex extraction
        # so we at least capture name + description + body correctly.
        fm, body = _best_effort_frontmatter(raw)

    # Name resolution precedence: frontmatter `name` > filename stem > parent dir name.
    name = str(fm.get("name") or path.stem)
    if kind == ArtifactKind.SKILL and path.name == "SKILL.md":
        # Skills live in folders; the folder name is the skill name.
        name = str(fm.get("name") or path.parent.name)

    description = str(fm.get("description") or "").strip()

    scope = _scope_for(root)
    artifact_id = f"{kind.value}:{scope.value}:{name}:{path}"

    return Artifact(
        id=artifact_id,
        kind=kind,
        name=name,
        path=path,
        scope=scope,
        root=root,
        description=description,
        triggers=_extract_triggers(fm, body, description),
        body=body,
        body_hash=_hash_body(body),
        frontmatter=fm,
    )


def scan_claude_dir(root: Path) -> list[Artifact]:
    """Walk a single .claude/ root and return all artifacts inside it."""
    root = root.resolve()
    artifacts: list[Artifact] = []

    # Agents: .claude/agents/*.md
    agents_dir = root / "agents"
    if agents_dir.is_dir():
        for md in sorted(agents_dir.rglob("*.md")):
            a = parse_artifact_file(md, ArtifactKind.AGENT, root)
            if a:
                artifacts.append(a)

    # Skills: .claude/skills/<n>/SKILL.md
    skills_dir = root / "skills"
    if skills_dir.is_dir():
        for skill_md in sorted(skills_dir.rglob("SKILL.md")):
            a = parse_artifact_file(skill_md, ArtifactKind.SKILL, root)
            if a:
                artifacts.append(a)

    # Commands: .claude/commands/**/*.md  (supports nested namespaces)
    commands_dir = root / "commands"
    if commands_dir.is_dir():
        for md in sorted(commands_dir.rglob("*.md")):
            a = parse_artifact_file(md, ArtifactKind.COMMAND, root)
            if a:
                artifacts.append(a)

    return artifacts


def parse_memory_file(path: Path) -> Artifact | None:
    """Parse a CLAUDE.md as a memory artifact."""
    try:
        body = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None

    name = path.parent.name or "root"
    scope = Scope.GLOBAL if str(path).startswith(str(Path.home() / ".claude")) else Scope.PROJECT

    return Artifact(
        id=f"memory:{scope.value}:{path}",
        kind=ArtifactKind.MEMORY,
        name=f"CLAUDE.md ({name})",
        path=path,
        scope=scope,
        root=path.parent,
        description="",
        triggers=[],
        body=body,
        body_hash=_hash_body(body),
        frontmatter={},
    )
