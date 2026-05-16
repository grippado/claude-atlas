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


_FRONTMATTER_PRIORITY_KEYS = ("name", "description", "kind", "scope", "triggers")
_FRONTMATTER_MAX_VALUE_LEN = 120
_FRONTMATTER_MAX_FIELDS = 6
_BODY_EXCERPT_LEN = 220


def _truncate(text: str, limit: int) -> str:
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def _frontmatter_preview(frontmatter: dict | None) -> list[dict]:
    """Render a small list of frontmatter rows for side-by-side display."""
    if not frontmatter:
        return []
    fm = dict(frontmatter)
    # Stable ordering: priority keys first, then the rest alphabetically.
    ordered_keys: list[str] = []
    for k in _FRONTMATTER_PRIORITY_KEYS:
        if k in fm:
            ordered_keys.append(k)
    for k in sorted(fm.keys()):
        if k not in ordered_keys:
            ordered_keys.append(k)
    rows: list[dict] = []
    for key in ordered_keys[:_FRONTMATTER_MAX_FIELDS]:
        value = fm[key]
        if isinstance(value, list):
            text = ", ".join(str(x) for x in value)
        elif isinstance(value, dict):
            text = ", ".join(f"{k}={v}" for k, v in value.items())
        else:
            text = str(value)
        rows.append({"key": key, "value": _truncate(text, _FRONTMATTER_MAX_VALUE_LEN)})
    if len(ordered_keys) > _FRONTMATTER_MAX_FIELDS:
        rows.append({
            "key": "…",
            "value": f"({len(ordered_keys) - _FRONTMATTER_MAX_FIELDS} more)",
        })
    return rows


def _artifact_preview(artifact: object | None) -> dict:
    """Return frontmatter rows + a short body excerpt for an artifact."""
    if artifact is None:
        return {"frontmatter": [], "body_excerpt": "", "has_frontmatter": False}
    fm_rows = _frontmatter_preview(getattr(artifact, "frontmatter", None))
    body = _truncate(getattr(artifact, "body", "") or "", _BODY_EXCERPT_LEN)
    return {
        "frontmatter": fm_rows,
        "body_excerpt": body,
        "has_frontmatter": bool(fm_rows),
        "has_body": bool(body),
    }


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
        src_preview = _artifact_preview(src)
        tgt_preview = _artifact_preview(tgt)
        row = {
            "edge_id": f"{e.source}::{e.target}::{e.kind.value}",
            "kind": kind,
            "severity": sev,
            "source_id": e.source,
            "source_name": src_name,
            "source_path": str(src.path) if src else "",
            "source_scope": src.scope.value if src else "",
            "source_kind": src.kind.value if src else "",
            "target_scope": tgt.scope.value if tgt else "",
            "target_kind": tgt.kind.value if tgt else "",
            "source_frontmatter": src_preview["frontmatter"],
            "source_body_excerpt": src_preview["body_excerpt"],
            "source_has_frontmatter": src_preview["has_frontmatter"],
            "source_has_body": src_preview["has_body"],
            "target_id": e.target,
            "target_name": tgt_name,
            "target_path": str(tgt.path) if tgt else "",
            "target_frontmatter": tgt_preview["frontmatter"],
            "target_body_excerpt": tgt_preview["body_excerpt"],
            "target_has_frontmatter": tgt_preview["has_frontmatter"],
            "target_has_body": tgt_preview["has_body"],
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


_SEVERITY_RANK_FOR_TREEMAP = {
    Severity.HIGH.value: 3,
    Severity.MEDIUM.value: 2,
    Severity.LOW.value: 1,
    Severity.NONE.value: 0,
}


def _treemap_cell_color(rank: int) -> str:
    return {
        3: "#ef4444",  # high
        2: "#f97316",  # medium
        1: "#eab308",  # low
    }.get(rank, "#334155")  # no issues touching this bucket


def _treemap_data(result: ScanResult) -> list[dict]:
    """
    Aggregate artifacts by (scope, kind) into a treemap-ready layout.

    Layout: scopes are horizontal slabs sized by total artifact count
    in each scope; within a slab, kinds are vertical slabs sized by
    count per kind. Output is in 0..100 viewBox coordinates.

    Color: each cell's max severity across all issues that touch any
    artifact in that bucket. Buckets with no issues get a muted color.
    """
    buckets: dict[tuple[str, str], int] = {}
    bucket_sev_rank: dict[tuple[str, str], int] = {}

    artifact_bucket: dict[str, tuple[str, str]] = {}
    for a in result.artifacts:
        key = (a.scope.value, a.kind.value)
        buckets[key] = buckets.get(key, 0) + 1
        artifact_bucket[a.id] = key

    for e in result.issues:
        rank = _SEVERITY_RANK_FOR_TREEMAP.get(e.severity.value, 0)
        for endpoint in (e.source, e.target):
            key = artifact_bucket.get(endpoint)
            if key is None:
                continue
            if rank > bucket_sev_rank.get(key, 0):
                bucket_sev_rank[key] = rank

    if not buckets:
        return []

    by_scope: dict[str, list[tuple[str, int]]] = {}
    for (scope, kind), count in buckets.items():
        by_scope.setdefault(scope, []).append((kind, count))

    scopes_sorted = sorted(
        by_scope.items(),
        key=lambda item: -sum(c for _, c in item[1]),
    )
    total = sum(buckets.values())

    cells: list[dict] = []
    x = 0.0
    for scope, kind_counts in scopes_sorted:
        scope_total = sum(c for _, c in kind_counts)
        w = (scope_total / total) * 100 if total else 0
        # Vertical stack of kinds within this scope's column
        kind_counts.sort(key=lambda kc: -kc[1])
        y = 0.0
        for kind, count in kind_counts:
            h = (count / scope_total) * 100 if scope_total else 0
            rank = bucket_sev_rank.get((scope, kind), 0)
            cells.append({
                "scope": scope,
                "kind": kind,
                "count": count,
                "x": round(x, 3),
                "y": round(y, 3),
                "w": round(w, 3),
                "h": round(h, 3),
                "color": _treemap_cell_color(rank),
                "has_issue": rank > 0,
                "severity_rank": rank,
                "label": f"{scope} · {kind}" if w > 12 else kind,
                "show_label": w > 8 and h > 14,
                "show_count": w > 6 and h > 8,
            })
            y += h
        x += w
    return cells


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
    treemap = _treemap_data(result)

    stats_rows = [{"key": k, "value": v} for k, v in sorted(stats.items())]

    score = result.health_score()
    grade = result.health_grade()
    health_color = (
        "#34d399" if score >= 75 else "#eab308" if score >= 50 else "#ef4444"
    )

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
            "health_score": score,
            "health_grade": grade,
            "health_color": health_color,
            "issue_singular": stats.get("issues_total", 0) == 1,
            "orphans_singular": len(orphans) == 1,
            "treemap_cells": treemap,
            "has_treemap": bool(treemap),
        },
    )

    output_path.write_text(html, encoding="utf-8")
    return output_path
