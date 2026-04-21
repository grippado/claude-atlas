"""Render ScanResult → standalone HTML report."""

from __future__ import annotations

import json
from pathlib import Path

import chevron

from claude_atlas.models import ArtifactKind, EdgeKind, ScanResult

_TEMPLATE_PATH = Path(__file__).parent / "templates" / "report.mustache"


_ISSUE_KINDS = {
    EdgeKind.DUPLICATE_EXACT.value,
    EdgeKind.DUPLICATE_SEMANTIC.value,
    EdgeKind.TRIGGER_COLLISION.value,
    EdgeKind.OVERRIDES.value,
}


def _node_color(kind: str) -> str:
    return {
        ArtifactKind.AGENT.value: "#60a5fa",  # blue
        ArtifactKind.SKILL.value: "#34d399",  # emerald
        ArtifactKind.COMMAND.value: "#f59e0b",  # amber
        ArtifactKind.MEMORY.value: "#a78bfa",  # violet
    }.get(kind, "#94a3b8")


def _edge_color(kind: str) -> str:
    return {
        EdgeKind.DUPLICATE_EXACT.value: "#ef4444",
        EdgeKind.DUPLICATE_SEMANTIC.value: "#f97316",
        EdgeKind.TRIGGER_COLLISION.value: "#eab308",
        EdgeKind.OVERRIDES.value: "#ec4899",
        EdgeKind.REFERENCES.value: "#64748b",
        EdgeKind.CONTAINS.value: "#334155",
    }.get(kind, "#64748b")


def _to_cytoscape(result: ScanResult) -> dict:
    nodes = []
    for a in result.artifacts:
        nodes.append(
            {
                "data": {
                    "id": a.id,
                    "label": a.name,
                    "kind": a.kind.value,
                    "scope": a.scope.value,
                    "path": str(a.path),
                    "description": a.description,
                    "triggers": a.triggers,
                    "color": _node_color(a.kind.value),
                    "body_preview": (a.body or "")[:400],
                }
            }
        )

    edges = []
    for i, e in enumerate(result.edges):
        edges.append(
            {
                "data": {
                    "id": f"e{i}",
                    "source": e.source,
                    "target": e.target,
                    "kind": e.kind.value,
                    "weight": e.weight,
                    "detail": e.detail,
                    "color": _edge_color(e.kind.value),
                    "is_issue": e.kind.value in _ISSUE_KINDS,
                }
            }
        )

    return {"nodes": nodes, "edges": edges}


def render_html(result: ScanResult, output_path: Path) -> Path:
    """Render the scan result to a self-contained HTML file."""
    output_path = output_path.expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    cy = _to_cytoscape(result)
    stats = result.stats()

    issue_rows = []
    by_id = {a.id: a for a in result.artifacts}
    for e in result.issues:
        src = by_id.get(e.source)
        tgt = by_id.get(e.target)
        issue_rows.append(
            {
                "kind": e.kind.value,
                "source_name": src.name if src else e.source,
                "source_path": str(src.path) if src else "",
                "target_name": tgt.name if tgt else e.target,
                "target_path": str(tgt.path) if tgt else "",
                "detail": e.detail,
                "weight": f"{e.weight:.2f}",
            }
        )

    stats_rows = [{"key": k, "value": v} for k, v in sorted(stats.items())]

    template = _TEMPLATE_PATH.read_text(encoding="utf-8")
    html = chevron.render(
        template,
        {
            "graph_json": json.dumps(cy),
            "issues": issue_rows,
            "has_issues": bool(issue_rows),
            "stats": stats_rows,
            "roots_scanned": [str(p) for p in result.roots_scanned],
            "artifacts_total": stats.get("artifacts_total", 0),
            "issues_total": len(issue_rows),
        },
    )

    output_path.write_text(html, encoding="utf-8")
    return output_path
