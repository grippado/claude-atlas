"""Heuristics for building the artifact relationship graph."""

from __future__ import annotations

import re
from collections import defaultdict
from itertools import combinations

from claude_atlas.models import Artifact, ArtifactKind, Edge, EdgeKind, Scope

# Thresholds — documented in README; tweak here carefully.
JACCARD_SUSPICIOUS = 0.60
JACCARD_DUPLICATE = 0.85
TRIGGER_COLLISION_MIN_SHARED = 2

_WORD_RE = re.compile(r"[A-Za-z][A-Za-z0-9_-]{2,}")

# Very common English words we don't want dominating similarity scores.
_STOPWORDS = {
    "the", "and", "for", "with", "this", "that", "from", "when", "use", "uses",
    "using", "into", "your", "you", "are", "not", "but", "can", "will", "any",
    "all", "its", "has", "have", "been", "should", "would", "could", "which",
    "what", "where", "who", "whose", "these", "those", "they", "them", "their",
    "there", "here", "about", "also", "just", "only", "other", "more", "most",
    "some", "than", "then", "such", "each", "every", "way", "ways", "one", "two",
    "per", "via", "like", "based", "help", "helps", "make", "makes", "user",
    "users", "users'", "tool", "tools",
}


def _tokens(text: str) -> set[str]:
    """Lowercased word tokens minus stopwords."""
    return {t.lower() for t in _WORD_RE.findall(text or "") if t.lower() not in _STOPWORDS}


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def detect_containment(artifacts: list[Artifact]) -> list[Edge]:
    """
    A `.claude/` root *contains* its artifacts. We model the root as an implicit
    node (via its path string) by connecting each artifact to a synthetic root id.

    In practice: skip synthetic nodes and just connect sibling memory files to
    artifacts in the same project tree. This is mostly useful for UI grouping.
    """
    edges: list[Edge] = []

    by_root: dict[str, list[Artifact]] = defaultdict(list)
    for a in artifacts:
        by_root[str(a.root)].append(a)

    # For each root, connect memory files to everything else in that root as
    # `contains`. That gives the UI a natural cluster center per project.
    for root_artifacts in by_root.values():
        memories = [a for a in root_artifacts if a.kind == ArtifactKind.MEMORY]
        others = [a for a in root_artifacts if a.kind != ArtifactKind.MEMORY]
        for mem in memories:
            for o in others:
                edges.append(
                    Edge(
                        source=mem.id,
                        target=o.id,
                        kind=EdgeKind.CONTAINS,
                        weight=0.5,
                    )
                )

    return edges


def detect_exact_duplicates(artifacts: list[Artifact]) -> list[Edge]:
    """Artifacts with identical body hashes are exact duplicates."""
    edges: list[Edge] = []
    by_hash: dict[str, list[Artifact]] = defaultdict(list)
    for a in artifacts:
        if a.body_hash and a.kind != ArtifactKind.MEMORY:
            by_hash[a.body_hash].append(a)

    for group in by_hash.values():
        if len(group) < 2:
            continue
        for a, b in combinations(group, 2):
            edges.append(
                Edge(
                    source=a.id,
                    target=b.id,
                    kind=EdgeKind.DUPLICATE_EXACT,
                    weight=1.0,
                    detail=f"identical SHA-256: {a.body_hash[:12]}…",
                )
            )
    return edges


def detect_semantic_duplicates(
    artifacts: list[Artifact],
    threshold: float = JACCARD_SUSPICIOUS,
) -> list[Edge]:
    """
    Jaccard similarity over body + description tokens.

    Anything >= ``threshold`` is flagged. Pairs >= JACCARD_DUPLICATE are marked
    as probable duplicates in the edge detail so the LLM judge (if enabled)
    knows which to deprioritize re-checking.
    """
    edges: list[Edge] = []
    # Pre-compute token sets once; skip memory (too noisy).
    pairs: list[tuple[Artifact, set[str]]] = []
    for a in artifacts:
        if a.kind == ArtifactKind.MEMORY:
            continue
        toks = _tokens(a.body) | _tokens(a.description)
        if len(toks) >= 5:  # too short to compare meaningfully
            pairs.append((a, toks))

    for i, (a, ta) in enumerate(pairs):
        for b, tb in pairs[i + 1 :]:
            # Only compare same-kind artifacts; a skill vs a command being
            # similar isn't usually a "duplicate" in any actionable sense.
            if a.kind != b.kind:
                continue
            # Skip exact dup pairs (already covered).
            if a.body_hash and a.body_hash == b.body_hash:
                continue
            score = _jaccard(ta, tb)
            if score >= threshold:
                edges.append(
                    Edge(
                        source=a.id,
                        target=b.id,
                        kind=EdgeKind.DUPLICATE_SEMANTIC,
                        weight=score,
                        detail=f"jaccard={score:.2f}"
                        + (" (probable)" if score >= JACCARD_DUPLICATE else " (suspicious)"),
                    )
                )
    return edges


def detect_overrides(artifacts: list[Artifact]) -> list[Edge]:
    """
    A project-scoped artifact with the same kind+name as a global one `overrides` it.
    """
    edges: list[Edge] = []
    by_key: dict[tuple[str, str], list[Artifact]] = defaultdict(list)
    for a in artifacts:
        if a.kind == ArtifactKind.MEMORY:
            continue
        by_key[(a.kind.value, a.name.lower())].append(a)

    for group in by_key.values():
        globals_ = [a for a in group if a.scope == Scope.GLOBAL]
        projects = [a for a in group if a.scope == Scope.PROJECT]
        for g in globals_:
            for p in projects:
                edges.append(
                    Edge(
                        source=p.id,
                        target=g.id,
                        kind=EdgeKind.OVERRIDES,
                        weight=1.0,
                        detail=f"project '{p.name}' overrides global",
                    )
                )
    return edges


def detect_trigger_collisions(artifacts: list[Artifact]) -> list[Edge]:
    """
    Two artifacts with ``>= TRIGGER_COLLISION_MIN_SHARED`` overlapping trigger
    tokens are flagged. Strong signal that Claude will have to pick between them.
    """
    edges: list[Edge] = []
    candidates = [a for a in artifacts if a.triggers and a.kind != ArtifactKind.MEMORY]

    for i, a in enumerate(candidates):
        ta = set(a.triggers)
        for b in candidates[i + 1 :]:
            # Cross-kind collisions ARE interesting (a skill and a command both
            # claiming "refactor" is a real conflict).
            tb = set(b.triggers)
            shared = ta & tb
            if len(shared) >= TRIGGER_COLLISION_MIN_SHARED:
                edges.append(
                    Edge(
                        source=a.id,
                        target=b.id,
                        kind=EdgeKind.TRIGGER_COLLISION,
                        weight=float(len(shared)),
                        detail=f"shared triggers: {', '.join(sorted(shared))}",
                    )
                )
    return edges


def detect_references(artifacts: list[Artifact]) -> list[Edge]:
    """
    A body that mentions another artifact's name (as a distinct token) references it.

    Deliberately conservative: we only match tokens of length >= 4 to avoid
    coincidental collisions on common short words.
    """
    edges: list[Edge] = []
    by_name: dict[str, list[Artifact]] = defaultdict(list)
    for a in artifacts:
        if len(a.name) >= 4:
            by_name[a.name.lower()].append(a)

    for a in artifacts:
        body_tokens = {t.lower() for t in _WORD_RE.findall(a.body or "")}
        for name, targets in by_name.items():
            if name in body_tokens:
                for t in targets:
                    if t.id == a.id:
                        continue
                    edges.append(
                        Edge(
                            source=a.id,
                            target=t.id,
                            kind=EdgeKind.REFERENCES,
                            weight=0.3,
                            detail=f"mentions '{name}'",
                        )
                    )
    return edges


def build_all_edges(artifacts: list[Artifact]) -> list[Edge]:
    """Run every detector and return the combined edge list."""
    edges: list[Edge] = []
    edges.extend(detect_containment(artifacts))
    edges.extend(detect_exact_duplicates(artifacts))
    edges.extend(detect_semantic_duplicates(artifacts))
    edges.extend(detect_overrides(artifacts))
    edges.extend(detect_trigger_collisions(artifacts))
    edges.extend(detect_references(artifacts))
    return edges
