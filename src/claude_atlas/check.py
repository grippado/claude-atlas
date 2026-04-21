"""The ``check`` command: lint-style issue reporting for CI/scripts.

Produces output suitable for terminals, JSON pipes, and GitHub Actions
annotations. Designed to be used as a pre-commit hook or scheduled job.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from typing import TextIO

from claude_atlas.models import EdgeKind, ScanResult, Severity

_SEVERITY_RANK = {
    Severity.NONE.value: 0,
    Severity.LOW.value: 1,
    Severity.MEDIUM.value: 2,
    Severity.HIGH.value: 3,
}

_KIND_LABELS = {
    EdgeKind.DUPLICATE_EXACT.value: "duplicate_exact",
    EdgeKind.DUPLICATE_SEMANTIC.value: "duplicate_semantic",
    EdgeKind.OVERRIDES.value: "overrides",
    EdgeKind.TRIGGER_COLLISION.value: "trigger_collision",
}


def _suggested_fix(edge_kind: str, src_name: str, tgt_name: str) -> str:
    if edge_kind == EdgeKind.DUPLICATE_EXACT.value:
        return "Delete one — keep the one in the narrower scope."
    if edge_kind == EdgeKind.DUPLICATE_SEMANTIC.value:
        return f"Merge: keep {src_name}'s strongest description, combine triggers, delete the other."
    if edge_kind == EdgeKind.TRIGGER_COLLISION.value:
        return f"Rename triggers in {tgt_name} to disambiguate, or consolidate into one artifact."
    if edge_kind == EdgeKind.OVERRIDES.value:
        return f"If intentional, document it in {src_name}; if accidental, delete the project copy."
    return ""


def _filter_and_sort_issues(result: ScanResult) -> list[dict]:
    by_id = {a.id: a for a in result.artifacts}
    rows: list[dict] = []
    for e in result.issues:
        src = by_id.get(e.source)
        tgt = by_id.get(e.target)
        if src is None or tgt is None:
            continue
        rows.append(
            {
                "severity": e.severity.value,
                "severity_rank": _SEVERITY_RANK.get(e.severity.value, 0),
                "kind": e.kind.value,
                "kind_label": _KIND_LABELS.get(e.kind.value, e.kind.value),
                "source_name": src.name,
                "source_path": str(src.path),
                "target_name": tgt.name,
                "target_path": str(tgt.path),
                "detail": e.detail,
                "weight": e.weight,
                "fix": _suggested_fix(e.kind.value, src.name, tgt.name),
            }
        )
    rows.sort(key=lambda r: (-r["severity_rank"], r["source_path"], r["target_path"]))
    return rows


def _meets_threshold(severity: str, threshold: str) -> bool:
    """
    True if ``severity`` is at or above ``threshold``.

    Special case: threshold ``none`` always returns False — it means "never fail",
    a useful way to run check for reporting only without affecting exit code.
    """
    if threshold == Severity.NONE.value:
        return False
    return _SEVERITY_RANK.get(severity, 0) >= _SEVERITY_RANK.get(threshold, 0)


def _summary_line(rows: list[dict], total_artifacts: int) -> str:
    if not rows:
        return f"No issues detected in {total_artifacts} artifacts."
    counts = Counter(r["severity"] for r in rows)
    parts = []
    for sev in (Severity.HIGH.value, Severity.MEDIUM.value, Severity.LOW.value):
        if counts.get(sev, 0):
            parts.append(f"{counts[sev]} {sev}")
    breakdown = ", ".join(parts) if parts else "0"
    return f"Found {len(rows)} issues ({breakdown}) in {total_artifacts} artifacts."


def format_text(rows: list[dict], total_artifacts: int, top: int, quiet: bool) -> str:
    if quiet:
        return _summary_line(rows, total_artifacts)
    if not rows:
        return _summary_line(rows, total_artifacts)
    shown = rows if top == 0 else rows[:top]
    lines: list[str] = []
    for r in shown:
        sev = r["severity"].upper()
        lines.append(r["source_path"])
        lines.append(f"  {sev} {r['kind_label']}: {r['detail']}")
        lines.append(f"    paired with: {r['target_path']}")
        if r["fix"]:
            lines.append(f"    💡 {r['fix']}")
        lines.append("")
    summary = _summary_line(rows, total_artifacts)
    if top > 0 and len(rows) > top:
        summary += f" Showing top {top}; pass --top 0 for all."
    lines.append(summary)
    return "\n".join(lines)


def format_json(rows: list[dict], total_artifacts: int, top: int, quiet: bool) -> str:
    counts = Counter(r["severity"] for r in rows)
    payload = {
        "summary": {
            "total_issues": len(rows),
            "total_artifacts": total_artifacts,
            "by_severity": {
                "high": counts.get(Severity.HIGH.value, 0),
                "medium": counts.get(Severity.MEDIUM.value, 0),
                "low": counts.get(Severity.LOW.value, 0),
            },
        },
        "issues": [] if quiet else (rows if top == 0 else rows[:top]),
    }
    return json.dumps(payload, indent=2)


def format_github(rows: list[dict], total_artifacts: int, top: int, quiet: bool) -> str:
    if quiet:
        return _summary_line(rows, total_artifacts)
    shown = rows if top == 0 else rows[:top]
    lines: list[str] = []
    for r in shown:
        level = {
            Severity.HIGH.value: "error",
            Severity.MEDIUM.value: "warning",
            Severity.LOW.value: "notice",
        }.get(r["severity"], "notice")
        msg = f"{r['kind_label']}: {r['detail']} (paired with {r['target_path']})"
        msg = msg.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
        lines.append(f"::{level} file={r['source_path']}::{msg}")
    lines.append(_summary_line(rows, total_artifacts))
    return "\n".join(lines)


def run_check(
    result: ScanResult,
    max_severity: str = Severity.HIGH.value,
    output_format: str = "text",
    top: int = 10,
    quiet: bool = False,
    stream: TextIO | None = None,
) -> int:
    """
    Run the check against a scan result. Returns the exit code.
    - 0: no issues at-or-above ``max_severity``
    - 1: issues at-or-above ``max_severity`` were found
    """
    rows = _filter_and_sort_issues(result)
    total_artifacts = len(result.artifacts)

    formatters = {
        "text": format_text,
        "json": format_json,
        "github": format_github,
    }
    formatter = formatters.get(output_format, format_text)
    output = formatter(rows, total_artifacts, top, quiet)

    out = stream if stream is not None else sys.stdout
    out.write(output)
    if not output.endswith("\n"):
        out.write("\n")

    failing = [r for r in rows if _meets_threshold(r["severity"], max_severity)]
    return 1 if failing else 0
