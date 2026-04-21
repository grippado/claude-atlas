"""Render ScanResult → standalone HTML report."""

from __future__ import annotations

import json
from pathlib import Path

import chevron

from claude_atlas.models import ArtifactKind, EdgeKind, ScanResult, Severity

_TEMPLATE_PATH = Path(__file__).parent / "templates" / "report.mustache"

_ISSUE_KINDS = {
    EdgeKind.DUPLICATE_EXACT.value,
    EdgeKind.DUPLICATE_SEMANTIC.value,
    EdgeKind.TRIGGER_COLLISION.value,
    EdgeKind.OVERRIDES.value,
}

_SEVERITY_ORDER = {
    Severity.HIGH.value: 0,
    Severity.MEDIUM.value: 1,
    Severity.LOW.value: 2,
    Severity.NONE.value: 3,
}


def _node_color(kind: str) -> str:
    return {
        ArtifactKind.AGENT.value: "#60a5fa",
        ArtifactKind.SKILL.value: "#34d399",
        ArtifactKind.COMMAND.value: "#f59e0b",
        ArtifactKind.MEMORY.value: "#a78bfa",
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


def _severity_color(sev: str) -> str:
    return {
        Severity.HIGH.value: "#ef4444",
        Severity.MEDIUM.value: "#f97316",
        Severity.LOW.value: "#eab308",
    }.get(sev, "#64748b")


def _suggested_fix(edge_kind: str, src_name: str, tgt_name: str) -> str:
    if edge_kind == EdgeKind.DUPLICATE_EXACT.value:
        return "Identical content. Delete one — keep the one in the narrower scope."
    if edge_kind == EdgeKind.DUPLICATE_SEMANTIC.value:
        return (
            f"Near-duplicate. Merge: keep {src_name}'s strongest description, "
            f"combine triggers, delete the other."
        )
    if edge_kind == EdgeKind.TRIGGER_COLLISION.value:
        return (
            f"Both will compete for activation. Either rename triggers in "
            f"{tgt_name} to disambiguate, or consolidate into one artifact."
        )
    if edge_kind == EdgeKind.OVERRIDES.value:
        return (
            f"Project version shadows global. If intentional, document it in "
            f"{src_name}; if accidental, delete the project copy."
        )
    return ""


def _to_cytoscape(result: ScanResult) -> dict:
    nodes = []
    connected_ids: set[str] = set()
    for e in result.edges:
        connected_ids.add(e.source)
        connected_ids.add(e.target)

    for a in result.artifacts:
        nodes.append({
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
                "is_orphan": a.id not in connected_ids,
            }
        })

    edges = []
    for i, e in enumerate(result.edges):
        edges.append({
            "data": {
                "id": f"e{i}",
                "source": e.source,
                "target": e.target,
                "kind": e.kind.value,
                "weight": e.weight,
                "detail": e.detail,
                "severity": e.severity.value,
                "color": _edge_color(e.kind.value),
                "is_issue": e.kind.value in _ISSUE_KINDS,
            }
        })

    return {"nodes": nodes, "edges": edges}


def _group_issues(result: ScanResult) -> list[dict]:
    by_id = {a.id: a for a in result.artifacts}
    issues = sorted(
        result.issues,
        key=lambda e: (_SEVERITY_ORDER.get(e.severity.value, 9), e.kind.value),
    )

    buckets: dict[str, dict[str, list[dict]]] = {}
    for e in issues:
        sev = e.severity.value if e.severity.value != Severity.NONE.value else "low"
        kind = e.kind.value
        src = by_id.get(e.source)
        tgt = by_id.get(e.target)
        src_name = src.name if src else e.source
        tgt_name = tgt.name if tgt else e.target
        row = {
            "edge_id": f"{e.source}::{e.target}::{e.kind.value}",
            "kind": kind,
            "severity": sev,
            "source_id": e.source,
            "source_name": src_name,
            "source_path": str(src.path) if src else "",
            "target_id": e.target,
            "target_name": tgt_name,
            "target_path": str(tgt.path) if tgt else "",
            "detail": e.detail,
            "weight": f"{e.weight:.2f}",
            "fix": _suggested_fix(kind, src_name, tgt_name),
        }
        buckets.setdefault(sev, {}).setdefault(kind, []).append(row)

    out: list[dict] = []
    for sev in (Severity.HIGH.value, Severity.MEDIUM.value, Severity.LOW.value):
        if sev not in buckets:
            continue
        groups = []
        total = 0
        for kind, rows in sorted(buckets[sev].items()):
            groups.append({"kind": kind, "count": len(rows), "issues": rows})
            total += len(rows)
        out.append({
            "severity": sev,
            "severity_upper": sev.upper(),
            "severity_color": _severity_color(sev),
            "count": total,
            "open_by_default": sev == Severity.HIGH.value,
            "groups": groups,
        })
    return out


def _orphan_list(result: ScanResult) -> list[dict]:
    connected: set[str] = set()
    for e in result.edges:
        connected.add(e.source)
        connected.add(e.target)
    orphans = [a for a in result.artifacts if a.id not in connected]
    return [
        {
            "id": a.id,
            "name": a.name,
            "kind": a.kind.value,
            "scope": a.scope.value,
            "path": str(a.path),
            "color": _node_color(a.kind.value),
        }
        for a in orphans
    ]


def render_html(result: ScanResult, output_path: Path) -> Path:
    output_path = output_path.expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    cy = _to_cytoscape(result)
    stats = result.stats()
    issue_groups = _group_issues(result)
    orphans = _orphan_list(result)

    stats_rows = [{"key": k, "value": v} for k, v in sorted(stats.items())]

    template = _TEMPLATE_PATH.read_text(encoding="utf-8")
    html = chevron.render(
        template,
        {
            "graph_json": json.dumps(cy),
            "issue_groups": issue_groups,
            "has_issues": bool(issue_groups),
            "orphans": orphans,
            "orphans_count": len(orphans),
            "has_orphans": bool(orphans),
            "stats": stats_rows,
            "roots_scanned": [str(p) for p in result.roots_scanned],
            "artifacts_total": stats.get("artifacts_total", 0),
            "issues_total": stats.get("issues_total", 0),
        },
    )

    output_path.write_text(html, encoding="utf-8")
    return output_path
