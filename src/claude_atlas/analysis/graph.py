"""Heuristics for building the artifact relationship graph."""

from __future__ import annotations

import re
from collections import defaultdict
from itertools import combinations

from claude_atlas.models import Artifact, ArtifactKind, Edge, EdgeKind, Scope, Severity

JACCARD_SUSPICIOUS = 0.60
JACCARD_DUPLICATE = 0.85
TRIGGER_COLLISION_MIN_SHARED = 2
TRIGGER_COLLISION_MIN_DISTINCTIVE_LEN = 5

_WORD_RE = re.compile(r"[A-Za-z][A-Za-z0-9_-]{2,}")

_ENGLISH_STOPWORDS = {
    "the", "and", "for", "with", "this", "that", "from", "when", "use", "uses",
    "using", "into", "your", "you", "are", "not", "but", "can", "will", "any",
    "all", "its", "has", "have", "been", "should", "would", "could", "which",
    "what", "where", "who", "whose", "these", "those", "they", "them", "their",
    "there", "here", "about", "also", "just", "only", "other", "more", "most",
    "some", "than", "then", "such", "each", "every", "way", "ways", "one", "two",
    "per", "via", "like", "based",
}

_DOMAIN_STOPWORDS = {
    "agent", "agents", "skill", "skills", "command", "commands",
    "user", "users", "task", "tasks", "work", "working", "works",
    "code", "file", "files", "folder", "folders", "project", "projects",
    "tool", "tools", "help", "helps", "helpful", "make", "makes", "create",
    "creating", "created", "update", "updating", "updated", "write", "writing",
    "read", "reading", "run", "running", "need", "needs", "needed",
    "proactively", "automatically", "should", "must",
    "done", "begin", "start", "starts", "started", "starting",
    "stuck", "overwhelmed", "seem", "seems",
    "example", "examples", "thing", "things", "stuff",
    "new", "old", "good", "great", "best", "better", "well",
    "claude", "anthropic",
}

_STOPWORDS = _ENGLISH_STOPWORDS | _DOMAIN_STOPWORDS


def _tokens(text: str) -> set[str]:
    return {t.lower() for t in _WORD_RE.findall(text or "") if t.lower() not in _STOPWORDS}


def _distinctive_triggers(triggers: list[str]) -> set[str]:
    return {
        t.lower() for t in triggers
        if t.lower() not in _STOPWORDS
        and len(t) >= TRIGGER_COLLISION_MIN_DISTINCTIVE_LEN
    }


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def detect_containment(artifacts: list[Artifact]) -> list[Edge]:
    edges: list[Edge] = []
    by_root: dict[str, list[Artifact]] = defaultdict(list)
    for a in artifacts:
        by_root[str(a.root)].append(a)
    for root_artifacts in by_root.values():
        memories = [a for a in root_artifacts if a.kind == ArtifactKind.MEMORY]
        others = [a for a in root_artifacts if a.kind != ArtifactKind.MEMORY]
        for mem in memories:
            for o in others:
                edges.append(Edge(source=mem.id, target=o.id, kind=EdgeKind.CONTAINS,
                                  weight=0.5, severity=Severity.NONE))
    return edges


def detect_exact_duplicates(artifacts: list[Artifact]) -> list[Edge]:
    edges: list[Edge] = []
    by_hash: dict[str, list[Artifact]] = defaultdict(list)
    for a in artifacts:
        if a.body_hash and a.kind != ArtifactKind.MEMORY:
            by_hash[a.body_hash].append(a)
    for group in by_hash.values():
        if len(group) < 2:
            continue
        for a, b in combinations(group, 2):
            edges.append(Edge(
                source=a.id, target=b.id, kind=EdgeKind.DUPLICATE_EXACT,
                weight=1.0, detail=f"identical SHA-256: {a.body_hash[:12]}…",
                severity=Severity.HIGH,
            ))
    return edges


def detect_semantic_duplicates(artifacts: list[Artifact], threshold: float = JACCARD_SUSPICIOUS) -> list[Edge]:
    edges: list[Edge] = []
    pairs: list[tuple[Artifact, set[str]]] = []
    for a in artifacts:
        if a.kind == ArtifactKind.MEMORY:
            continue
        toks = _tokens(a.body) | _tokens(a.description)
        if len(toks) >= 5:
            pairs.append((a, toks))
    for i, (a, ta) in enumerate(pairs):
        for b, tb in pairs[i + 1:]:
            if a.kind != b.kind:
                continue
            if a.body_hash and a.body_hash == b.body_hash:
                continue
            score = _jaccard(ta, tb)
            if score >= threshold:
                severity = Severity.HIGH if score >= JACCARD_DUPLICATE else Severity.MEDIUM
                edges.append(Edge(
                    source=a.id, target=b.id, kind=EdgeKind.DUPLICATE_SEMANTIC,
                    weight=score,
                    detail=f"jaccard={score:.2f}" + (" (probable)" if score >= JACCARD_DUPLICATE else " (suspicious)"),
                    severity=severity,
                ))
    return edges


def detect_overrides(artifacts: list[Artifact]) -> list[Edge]:
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
                edges.append(Edge(
                    source=p.id, target=g.id, kind=EdgeKind.OVERRIDES,
                    weight=1.0, detail=f"project '{p.name}' overrides global",
                    severity=Severity.HIGH,
                ))
    return edges


def detect_trigger_collisions(artifacts: list[Artifact]) -> list[Edge]:
    edges: list[Edge] = []
    candidates = []
    for a in artifacts:
        if a.kind == ArtifactKind.MEMORY:
            continue
        distinctive = _distinctive_triggers(a.triggers)
        if distinctive:
            candidates.append((a, distinctive))
    for i, (a, ta) in enumerate(candidates):
        for b, tb in candidates[i + 1:]:
            shared = ta & tb
            if len(shared) < TRIGGER_COLLISION_MIN_SHARED:
                continue
            if a.kind != b.kind:
                severity = Severity.LOW
            elif len(shared) >= 4:
                severity = Severity.MEDIUM
            else:
                severity = Severity.LOW
            edges.append(Edge(
                source=a.id, target=b.id, kind=EdgeKind.TRIGGER_COLLISION,
                weight=float(len(shared)),
                detail=f"shared triggers: {', '.join(sorted(shared))}",
                severity=severity,
            ))
    return edges


def detect_references(artifacts: list[Artifact]) -> list[Edge]:
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
                    edges.append(Edge(
                        source=a.id, target=t.id, kind=EdgeKind.REFERENCES,
                        weight=0.3, detail=f"mentions '{name}'",
                        severity=Severity.NONE,
                    ))
    return edges


def build_all_edges(artifacts: list[Artifact]) -> list[Edge]:
    edges: list[Edge] = []
    edges.extend(detect_containment(artifacts))
    edges.extend(detect_exact_duplicates(artifacts))
    edges.extend(detect_semantic_duplicates(artifacts))
    edges.extend(detect_overrides(artifacts))
    edges.extend(detect_trigger_collisions(artifacts))
    edges.extend(detect_references(artifacts))
    return edges
