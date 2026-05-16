"""Tests for the ``fix`` command's pure logic.

Interactive parts (rich Prompt) are exercised via the CLI runner in
test_core if/when needed; here we cover the deterministic functions
that hold the actual business logic.
"""

from __future__ import annotations

from claude_atlas.fix import (
    build_prompt,
    filter_by_severity,
    parse_selection,
)


def _row(i: int, severity: str = "high", kind: str = "duplicate_exact") -> dict:
    return {
        "severity": severity,
        "severity_rank": 3,
        "kind": kind,
        "kind_label": kind,
        "source_name": f"s{i}",
        "source_path": f"/tmp/s{i}.md",
        "target_name": f"t{i}",
        "target_path": f"/tmp/t{i}.md",
        "detail": f"detail {i}",
        "weight": 1.0,
        "fix": f"do thing {i}",
    }


def test_parse_selection_empty_means_all() -> None:
    assert parse_selection("", 5) == [0, 1, 2, 3, 4]
    assert parse_selection("   ", 3) == [0, 1, 2]


def test_parse_selection_all_keyword() -> None:
    assert parse_selection("all", 4) == [0, 1, 2, 3]
    assert parse_selection("ALL", 4) == [0, 1, 2, 3]


def test_parse_selection_quit() -> None:
    assert parse_selection("q", 4) == []
    assert parse_selection("quit", 4) == []
    assert parse_selection("exit", 4) == []


def test_parse_selection_individual_indices() -> None:
    assert parse_selection("1,3,5", 6) == [0, 2, 4]


def test_parse_selection_ranges() -> None:
    assert parse_selection("2-4", 6) == [1, 2, 3]
    assert parse_selection("1,3-5", 6) == [0, 2, 3, 4]


def test_parse_selection_reversed_range_is_still_handled() -> None:
    assert parse_selection("5-2", 6) == [1, 2, 3, 4]


def test_parse_selection_clamps_out_of_range() -> None:
    # Issue list has only 3 — asking for 5 and a 4-7 range should clamp
    assert parse_selection("1,5,4-7", 3) == [0]


def test_parse_selection_dedupes() -> None:
    assert parse_selection("1,2,1-3", 5) == [0, 1, 2]


def test_parse_selection_ignores_garbage_tokens() -> None:
    assert parse_selection("1,foo,3-bar,2", 5) == [0, 1]


def test_filter_by_severity_passthrough_when_none() -> None:
    rows = [_row(1, "high"), _row(2, "low")]
    assert filter_by_severity(rows, None) == rows


def test_filter_by_severity_matches() -> None:
    rows = [_row(1, "high"), _row(2, "low"), _row(3, "high")]
    out = filter_by_severity(rows, "high")
    assert [r["source_name"] for r in out] == ["s1", "s3"]


def test_filter_by_severity_invalid_is_passthrough() -> None:
    rows = [_row(1, "high")]
    assert filter_by_severity(rows, "bogus") == rows


def test_build_prompt_empty_says_so() -> None:
    out = build_prompt([])
    assert "no issues selected" in out.lower()


def test_build_prompt_lists_each_issue_with_paths_and_fix() -> None:
    rows = [_row(1, "high"), _row(2, "medium", kind="trigger_collision")]
    out = build_prompt(rows)
    # Header pluralization
    assert "2 issues to triage" in out
    # Each issue numbered
    assert "## 1. duplicate_exact (HIGH)" in out
    assert "## 2. trigger_collision (MEDIUM)" in out
    # Paths surfaced
    assert "/tmp/s1.md" in out
    assert "/tmp/t2.md" in out
    # Fix suggestions surfaced
    assert "do thing 1" in out
    assert "do thing 2" in out
    # Safety reminder present
    assert "ask me to confirm" in out.lower()


def test_build_prompt_singular_when_one_issue() -> None:
    out = build_prompt([_row(1)])
    assert "1 issue to triage" in out
