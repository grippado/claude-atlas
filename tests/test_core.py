"""Core tests for claude-atlas."""

from __future__ import annotations

import tempfile
from pathlib import Path

from claude_atlas.analysis.graph import (
    _distinctive_triggers,
    build_all_edges,
    detect_exact_duplicates,
    detect_overrides,
    detect_semantic_duplicates,
    detect_trigger_collisions,
)
from claude_atlas.models import Artifact, ArtifactKind, EdgeKind, Scope, Severity
from claude_atlas.report.renderer import render_html
from claude_atlas.scanner.discovery import find_claude_dirs, resolve_scan_targets
from claude_atlas.scanner.parsers import parse_artifact_file, scan_claude_dir


def _make_artifact(
    name: str,
    kind: ArtifactKind = ArtifactKind.SKILL,
    scope: Scope = Scope.GLOBAL,
    body: str = "",
    triggers: list[str] | None = None,
    description: str = "",
) -> Artifact:
    return Artifact(
        id=f"{kind.value}:{scope.value}:{name}",
        kind=kind, name=name, path=Path(f"/tmp/{name}.md"),
        scope=scope, root=Path("/tmp"),
        description=description, triggers=triggers or [], body=body,
        body_hash=__import__("hashlib").sha256(body.strip().encode()).hexdigest(),
    )


def test_exact_duplicate_detection() -> None:
    body = "This is a shared body between two agents that are otherwise different."
    a = _make_artifact("agent-a", kind=ArtifactKind.AGENT, body=body)
    b = _make_artifact("agent-b", kind=ArtifactKind.AGENT, body=body)
    c = _make_artifact("agent-c", kind=ArtifactKind.AGENT, body="totally different content here")
    edges = detect_exact_duplicates([a, b, c])
    assert len(edges) == 1
    assert edges[0].kind == EdgeKind.DUPLICATE_EXACT
    assert edges[0].severity == Severity.HIGH


def test_semantic_duplicate_severity() -> None:
    a = _make_artifact("refactor-a", body="refactor patterns architecture review clean improve quality standards")
    b = _make_artifact("refactor-b", body="refactor architecture patterns clean improve quality standards review")
    c = _make_artifact("refactor-c", body="refactor architecture patterns improve quality review different thing entirely nope")
    edges = detect_semantic_duplicates([a, b, c], threshold=0.3)
    high = [e for e in edges if e.severity == Severity.HIGH]
    medium = [e for e in edges if e.severity == Severity.MEDIUM]
    assert len(high) >= 1
    assert len(medium) >= 1 or len(high) > 1


def test_overrides_severity_is_high() -> None:
    g = _make_artifact("doc-writer", kind=ArtifactKind.AGENT, scope=Scope.GLOBAL, body="global")
    p = _make_artifact("doc-writer", kind=ArtifactKind.AGENT, scope=Scope.PROJECT, body="project version")
    edges = detect_overrides([g, p])
    assert len(edges) == 1
    assert edges[0].severity == Severity.HIGH


def test_trigger_collision_drops_domain_stopwords() -> None:
    a = _make_artifact("a", triggers=["agent", "user", "code"])
    b = _make_artifact("b", triggers=["agent", "user", "code"])
    edges = detect_trigger_collisions([a, b])
    assert len(edges) == 0


def test_trigger_collision_drops_short_tokens() -> None:
    a = _make_artifact("a", triggers=["api", "app", "go"])
    b = _make_artifact("b", triggers=["api", "app", "go"])
    edges = detect_trigger_collisions([a, b])
    assert len(edges) == 0


def test_trigger_collision_real_distinctive_tokens() -> None:
    a = _make_artifact("a", triggers=["refactor", "cleanup", "quality"])
    b = _make_artifact("b", triggers=["refactor", "cleanup", "something-else"])
    c = _make_artifact("c", triggers=["unrelated", "totally", "distinct"])
    edges = detect_trigger_collisions([a, b, c])
    assert len(edges) == 1
    assert edges[0].kind == EdgeKind.TRIGGER_COLLISION
    assert edges[0].severity == Severity.LOW


def test_trigger_collision_medium_severity_on_four_shared() -> None:
    a = _make_artifact("a", kind=ArtifactKind.AGENT, triggers=["refactor", "cleanup", "quality", "architecture", "review"])
    b = _make_artifact("b", kind=ArtifactKind.AGENT, triggers=["refactor", "cleanup", "quality", "architecture", "different"])
    edges = detect_trigger_collisions([a, b])
    assert len(edges) == 1
    assert edges[0].severity == Severity.MEDIUM


def test_trigger_collision_cross_kind_is_low() -> None:
    a = _make_artifact("a", kind=ArtifactKind.SKILL, triggers=["refactor", "cleanup", "quality", "architecture"])
    b = _make_artifact("b", kind=ArtifactKind.COMMAND, triggers=["refactor", "cleanup", "quality", "architecture"])
    edges = detect_trigger_collisions([a, b])
    assert len(edges) == 1
    assert edges[0].severity == Severity.LOW


def test_distinctive_triggers_helper() -> None:
    assert _distinctive_triggers(["agent", "user", "refactor", "api"]) == {"refactor"}
    assert _distinctive_triggers([]) == set()


def test_discovery_and_parsers() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        claude = tmp_path / "myrepo" / ".claude"
        (claude / "agents").mkdir(parents=True)
        (claude / "skills" / "my-skill").mkdir(parents=True)
        (claude / "commands").mkdir(parents=True)
        (claude / "agents" / "writer.md").write_text(
            "---\nname: writer\ndescription: writes docs\n---\nBody goes here for writer agent."
        )
        (claude / "skills" / "my-skill" / "SKILL.md").write_text(
            "---\nname: my-skill\ndescription: a test skill\n---\nSkill body."
        )
        (claude / "commands" / "hello.md").write_text(
            "---\ndescription: say hello\n---\nCommand body."
        )
        found = find_claude_dirs([tmp_path])
        assert len(found) == 1
        assert found[0] == claude.resolve()
        targets = resolve_scan_targets([tmp_path])
        assert claude.resolve() in targets
        artifacts = scan_claude_dir(claude)
        kinds = {a.kind for a in artifacts}
        assert kinds == {ArtifactKind.AGENT, ArtifactKind.SKILL, ArtifactKind.COMMAND}


def test_parse_artifact_file_handles_no_frontmatter() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        f = tmp_path / "plain.md"
        f.write_text("just a plain body, no frontmatter at all here.")
        a = parse_artifact_file(f, ArtifactKind.AGENT, tmp_path)
        assert a is not None
        assert a.name == "plain"
        assert a.body_hash


def test_parse_artifact_file_handles_malformed_multiline_description() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        f = tmp_path / "studio-coach.md"
        f.write_text(
            "---\nname: studio-coach\ndescription: PROACTIVELY use this agent when\n"
            "complex multi-agent tasks begin, when agents\nseem stuck or overwhelmed, or when the team\n"
            "needs motivation and coordination.\n---\n\nYou are the studio coach.\n"
        )
        a = parse_artifact_file(f, ArtifactKind.AGENT, tmp_path)
        assert a is not None
        assert a.name == "studio-coach"
        assert "PROACTIVELY" in a.description
        assert len(a.triggers) > 0


def test_build_all_edges_integration() -> None:
    dup = "shared body text for duplicate detection test purposes here now"
    a = _make_artifact("x", kind=ArtifactKind.AGENT, body=dup, triggers=["refactor", "cleanup"])
    b = _make_artifact("y", kind=ArtifactKind.AGENT, body=dup, triggers=["refactor", "cleanup", "architecture"])
    edges = build_all_edges([a, b])
    kinds = {e.kind for e in edges}
    assert EdgeKind.DUPLICATE_EXACT in kinds
    assert EdgeKind.TRIGGER_COLLISION in kinds


def test_render_html_produces_file() -> None:
    from claude_atlas.models import ScanResult
    a = _make_artifact("solo", description="alone in the world")
    result = ScanResult(artifacts=[a], edges=[], roots_scanned=[Path("/tmp")])
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "report.html"
        render_html(result, out)
        assert out.is_file()
        content = out.read_text()
        assert "Claude Atlas" in content
        assert "cytoscape" in content
        assert "solo" in content
        assert "search" in content.lower()
        assert "Isolated" in content
