"""Data models for claude-atlas."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class ArtifactKind(str, Enum):
    AGENT = "agent"
    SKILL = "skill"
    COMMAND = "command"
    MEMORY = "memory"


class Scope(str, Enum):
    GLOBAL = "global"
    PROJECT = "project"
    USER = "user"
    UNKNOWN = "unknown"


class EdgeKind(str, Enum):
    CONTAINS = "contains"
    OVERRIDES = "overrides"
    REFERENCES = "references"
    DUPLICATE_EXACT = "duplicate_exact"
    DUPLICATE_SEMANTIC = "duplicate_semantic"
    TRIGGER_COLLISION = "trigger_collision"


class Severity(str, Enum):
    """Severity of an issue edge. Non-issue edges use ``NONE``."""

    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class Artifact:
    """A single Claude Code artifact discovered on disk."""

    id: str
    kind: ArtifactKind
    name: str
    path: Path
    scope: Scope
    root: Path
    description: str = ""
    triggers: list[str] = field(default_factory=list)
    body: str = ""
    body_hash: str = ""
    frontmatter: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["kind"] = self.kind.value
        d["scope"] = self.scope.value
        d["path"] = str(self.path)
        d["root"] = str(self.root)
        return d


@dataclass
class Edge:
    """A relationship between two artifacts."""

    source: str
    target: str
    kind: EdgeKind
    weight: float = 1.0
    detail: str = ""
    severity: Severity = Severity.NONE

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "target": self.target,
            "kind": self.kind.value,
            "weight": self.weight,
            "detail": self.detail,
            "severity": self.severity.value,
        }


@dataclass
class ScanResult:
    """The full output of a scan: nodes + edges + issues summary."""

    artifacts: list[Artifact] = field(default_factory=list)
    edges: list[Edge] = field(default_factory=list)
    roots_scanned: list[Path] = field(default_factory=list)

    @property
    def issues(self) -> list[Edge]:
        return [
            e
            for e in self.edges
            if e.kind
            in (
                EdgeKind.DUPLICATE_EXACT,
                EdgeKind.DUPLICATE_SEMANTIC,
                EdgeKind.TRIGGER_COLLISION,
                EdgeKind.OVERRIDES,
            )
        ]

    def stats(self) -> dict[str, int]:
        by_kind: dict[str, int] = {}
        for a in self.artifacts:
            by_kind[a.kind.value] = by_kind.get(a.kind.value, 0) + 1
        by_edge: dict[str, int] = {}
        by_severity: dict[str, int] = {}
        for e in self.edges:
            by_edge[e.kind.value] = by_edge.get(e.kind.value, 0) + 1
            if e.severity != Severity.NONE:
                by_severity[e.severity.value] = by_severity.get(e.severity.value, 0) + 1
        return {
            "artifacts_total": len(self.artifacts),
            "edges_total": len(self.edges),
            "issues_total": len(self.issues),
            "roots_scanned": len(self.roots_scanned),
            **{f"artifacts_{k}": v for k, v in by_kind.items()},
            **{f"edges_{k}": v for k, v in by_edge.items()},
            **{f"severity_{k}": v for k, v in by_severity.items()},
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "artifacts": [a.to_dict() for a in self.artifacts],
            "edges": [e.to_dict() for e in self.edges],
            "roots_scanned": [str(p) for p in self.roots_scanned],
            "stats": self.stats(),
        }
