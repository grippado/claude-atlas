"""Tests for the ``check`` command and its formatters."""

from __future__ import annotations

import io
import json
from pathlib import Path

from claude_atlas.check import (
    _meets_threshold,
    format_github,
    format_json,
    format_text,
    run_check,
)
from claude_atlas.models import (
    Artifact,
    ArtifactKind,
    Edge,
    EdgeKind,
    ScanResult,
    Scope,
    Severity,
)


def _mk_artifact(name: str, body: str = "body") -> Artifact:
    import hashlib
    return Artifact(
        id=f"agent:global:{name}",
        kind=ArtifactKind.AGENT,
        name=name,
        path=Path(f"/tmp/{name}.md"),
        scope=Scope.GLOBAL,
        root=Path("/tmp"),
        body=body,
        body_hash=hashlib.sha256(body.encode()).hexdigest(),
    )


def _mk_result_with_issues() -> ScanResult:
    a = _mk_artifact("a", "body-a")
    b = _mk_artifact("b", "body-a")
    c = _mk_artifact("c", "body-c")
    d = _mk_artifact("d", "body-d")
    e = _mk_artifact("e", "body-e")
    f = _mk_artifact("f", "body-f")

    return ScanResult(
        artifacts=[a, b, c, d, e, f],
        edges=[
            Edge(source=a.id, target=b.id, kind=EdgeKind.DUPLICATE_EXACT,
                 severity=Severity.HIGH, detail="identical SHA"),
            Edge(source=c.id, target=d.id, kind=EdgeKind.DUPLICATE_SEMANTIC,
                 severity=Severity.MEDIUM, detail="jaccard=0.72"),
            Edge(source=e.id, target=f.id, kind=EdgeKind.TRIGGER_COLLISION,
                 severity=Severity.LOW, detail="shared: refactor, cleanup", weight=2.0),
        ],
        roots_scanned=[Path("/tmp")],
    )


def test_meets_threshold() -> None:
    assert _meets_threshold("high", "high") is True
    assert _meets_threshold("medium", "high") is False
    assert _meets_threshold("high", "medium") is True
    assert _meets_threshold("low", "low") is True
    assert _meets_threshold("none", "low") is False


def test_meets_threshold_none_means_never_fail() -> None:
    """--max-severity none should always return False (report-only mode)."""
    assert _meets_threshold("high", "none") is False
    assert _meets_threshold("medium", "none") is False
    assert _meets_threshold("low", "none") is False
    assert _meets_threshold("none", "none") is False


def test_run_check_max_severity_none_returns_zero() -> None:
    """End-to-end: --max-severity none with HIGH issues still returns 0."""
    result = _mk_result_with_issues()
    out = io.StringIO()
    code = run_check(result, max_severity="none", stream=out)
    assert code == 0
    assert "Found" in out.getvalue() or "issues" in out.getvalue().lower()


def test_text_format_lists_each_issue() -> None:
    rows = [
        {"severity": "high", "severity_rank": 3,
         "kind": "duplicate_exact", "kind_label": "duplicate_exact",
         "source_name": "a", "source_path": "/tmp/a.md",
         "target_name": "b", "target_path": "/tmp/b.md",
         "detail": "identical SHA", "weight": 1.0, "fix": "Delete one."},
    ]
    out = format_text(rows, total_artifacts=6, top=10, quiet=False)
    assert "/tmp/a.md" in out
    assert "HIGH duplicate_exact" in out
    assert "identical SHA" in out
    assert "/tmp/b.md" in out
    assert "💡" in out
    assert "Found 1 issues" in out


def test_text_format_quiet_only_summary() -> None:
    rows = [{"severity": "high", "severity_rank": 3, "kind": "duplicate_exact",
             "kind_label": "duplicate_exact", "source_name": "a", "source_path": "/a",
             "target_name": "b", "target_path": "/b", "detail": "x", "weight": 1.0, "fix": ""}]
    out = format_text(rows, total_artifacts=10, top=10, quiet=True)
    assert "Found 1 issues" in out
    assert "/a" not in out


def test_text_format_no_issues() -> None:
    out = format_text([], total_artifacts=42, top=10, quiet=False)
    assert "No issues" in out
    assert "42" in out


def test_text_format_top_truncates_and_notes_it() -> None:
    rows = [
        {"severity": "low", "severity_rank": 1, "kind": "trigger_collision",
         "kind_label": "trigger_collision", "source_name": f"a{i}", "source_path": f"/a{i}",
         "target_name": f"b{i}", "target_path": f"/b{i}", "detail": "x",
         "weight": 1.0, "fix": ""}
        for i in range(15)
    ]
    out = format_text(rows, total_artifacts=20, top=5, quiet=False)
    assert "/a0" in out
    assert "/a4" in out
    assert "/a5" not in out
    assert "Showing top 5" in out


def test_json_format_is_valid_json() -> None:
    rows = [
        {"severity": "high", "severity_rank": 3, "kind": "duplicate_exact",
         "kind_label": "duplicate_exact", "source_name": "a", "source_path": "/a",
         "target_name": "b", "target_path": "/b", "detail": "x", "weight": 1.0, "fix": "delete"},
        {"severity": "medium", "severity_rank": 2, "kind": "duplicate_semantic",
         "kind_label": "duplicate_semantic", "source_name": "c", "source_path": "/c",
         "target_name": "d", "target_path": "/d", "detail": "y", "weight": 0.7, "fix": "merge"},
    ]
    out = format_json(rows, total_artifacts=10, top=10, quiet=False)
    parsed = json.loads(out)
    assert parsed["summary"]["total_issues"] == 2
    assert parsed["summary"]["total_artifacts"] == 10
    assert parsed["summary"]["by_severity"]["high"] == 1
    assert parsed["summary"]["by_severity"]["medium"] == 1
    assert len(parsed["issues"]) == 2


def test_json_format_quiet_omits_issues() -> None:
    rows = [{"severity": "high", "severity_rank": 3, "kind": "duplicate_exact",
             "kind_label": "x", "source_name": "a", "source_path": "/a",
             "target_name": "b", "target_path": "/b", "detail": "x", "weight": 1.0, "fix": ""}]
    parsed = json.loads(format_json(rows, total_artifacts=5, top=10, quiet=True))
    assert parsed["summary"]["total_issues"] == 1
    assert parsed["issues"] == []


def test_github_format_uses_correct_annotation_levels() -> None:
    rows = [
        {"severity": "high", "severity_rank": 3, "kind": "duplicate_exact",
         "kind_label": "duplicate_exact", "source_name": "a", "source_path": "/a.md",
         "target_name": "b", "target_path": "/b.md", "detail": "x", "weight": 1.0, "fix": ""},
        {"severity": "medium", "severity_rank": 2, "kind": "duplicate_semantic",
         "kind_label": "duplicate_semantic", "source_name": "c", "source_path": "/c.md",
         "target_name": "d", "target_path": "/d.md", "detail": "y", "weight": 0.7, "fix": ""},
        {"severity": "low", "severity_rank": 1, "kind": "trigger_collision",
         "kind_label": "trigger_collision", "source_name": "e", "source_path": "/e.md",
         "target_name": "f", "target_path": "/f.md", "detail": "z", "weight": 1.0, "fix": ""},
    ]
    out = format_github(rows, total_artifacts=10, top=10, quiet=False)
    assert "::error file=/a.md::" in out
    assert "::warning file=/c.md::" in out
    assert "::notice file=/e.md::" in out


def test_github_format_escapes_special_chars() -> None:
    rows = [{"severity": "high", "severity_rank": 3, "kind": "x", "kind_label": "x",
             "source_name": "a", "source_path": "/a.md",
             "target_name": "b", "target_path": "/b.md",
             "detail": "has\nnewline and 100% percent", "weight": 1.0, "fix": ""}]
    out = format_github(rows, total_artifacts=2, top=10, quiet=False)
    assert "%0A" in out
    assert "%25" in out


def test_run_check_returns_zero_when_no_issues_at_threshold() -> None:
    result = ScanResult(artifacts=[_mk_artifact("solo")], edges=[], roots_scanned=[Path("/tmp")])
    out = io.StringIO()
    code = run_check(result, max_severity="high", output_format="text", top=10,
                     quiet=False, stream=out)
    assert code == 0
    assert "No issues" in out.getvalue()


def test_run_check_returns_one_when_high_issue_present() -> None:
    result = _mk_result_with_issues()
    out = io.StringIO()
    code = run_check(result, max_severity="high", output_format="text", top=10,
                     quiet=False, stream=out)
    assert code == 1


def test_run_check_threshold_medium_catches_medium() -> None:
    result = ScanResult(
        artifacts=[_mk_artifact("a"), _mk_artifact("b")],
        edges=[Edge(source="agent:global:a", target="agent:global:b",
                    kind=EdgeKind.DUPLICATE_SEMANTIC, severity=Severity.MEDIUM,
                    detail="jaccard=0.7")],
        roots_scanned=[Path("/tmp")],
    )
    out = io.StringIO()
    assert run_check(result, max_severity="medium", stream=out) == 1
    out2 = io.StringIO()
    assert run_check(result, max_severity="high", stream=out2) == 0


def test_run_check_threshold_low_catches_low() -> None:
    result = ScanResult(
        artifacts=[_mk_artifact("a"), _mk_artifact("b")],
        edges=[Edge(source="agent:global:a", target="agent:global:b",
                    kind=EdgeKind.TRIGGER_COLLISION, severity=Severity.LOW,
                    detail="shared: x, y", weight=2.0)],
        roots_scanned=[Path("/tmp")],
    )
    out = io.StringIO()
    assert run_check(result, max_severity="low", stream=out) == 1


def test_run_check_json_format_produces_valid_json() -> None:
    result = _mk_result_with_issues()
    out = io.StringIO()
    run_check(result, output_format="json", stream=out)
    parsed = json.loads(out.getvalue())
    assert "summary" in parsed
    assert "issues" in parsed


def test_run_check_top_zero_shows_all() -> None:
    result = _mk_result_with_issues()
    out = io.StringIO()
    run_check(result, output_format="text", top=0, stream=out)
    text = out.getvalue()
    assert "/tmp/a.md" in text
    assert "/tmp/c.md" in text
    assert "/tmp/e.md" in text
