"""The ``fix`` command: turn detected issues into a Claude Code prompt.

Reuses ``check`` for issue collection, then either runs an interactive
picker or accepts all issues in non-interactive mode. Output is a
single markdown block on stdout, ready to paste into Claude Code.

The tool never edits or deletes files — it just hands you a prompt.
"""

from __future__ import annotations

from claude_atlas.check import _filter_and_sort_issues
from claude_atlas.models import ScanResult, Severity

_SEVERITY_VALUES = {Severity.HIGH.value, Severity.MEDIUM.value, Severity.LOW.value}


def parse_selection(spec: str, total: int) -> list[int]:
    """
    Parse a selection spec against a list of ``total`` issues.

    Accepts:
      - "" or "all" → all indices [0, total).
      - "quit" / "q" → empty list.
      - "high" / "medium" / "low" → handled by the caller, not here.
      - comma list with optional ranges: "1,3,5-7" (1-based, inclusive).

    Returns a sorted list of 0-based indices, deduplicated, clamped to
    valid range. Invalid tokens are skipped silently — the caller may
    re-prompt if the result is empty.
    """
    s = spec.strip().lower()
    if not s or s == "all":
        return list(range(total))
    if s in {"quit", "q", "exit"}:
        return []

    picked: set[int] = set()
    for token in s.split(","):
        token = token.strip()
        if not token:
            continue
        if "-" in token:
            lo, _, hi = token.partition("-")
            try:
                a = int(lo)
                b = int(hi)
            except ValueError:
                continue
            if a > b:
                a, b = b, a
            for n in range(a, b + 1):
                if 1 <= n <= total:
                    picked.add(n - 1)
        else:
            try:
                n = int(token)
            except ValueError:
                continue
            if 1 <= n <= total:
                picked.add(n - 1)
    return sorted(picked)


def filter_by_severity(rows: list[dict], severity: str | None) -> list[dict]:
    """Return rows matching ``severity`` (or all rows if severity is None)."""
    if severity is None or severity not in _SEVERITY_VALUES:
        return rows
    return [r for r in rows if r["severity"] == severity]


def build_prompt(rows: list[dict]) -> str:
    """
    Build a markdown prompt summarizing the selected issues.

    The prompt is written for Claude Code: it explains the situation,
    lists each issue with file paths and the suggested fix, and asks
    Claude to confirm before deleting anything.
    """
    if not rows:
        return (
            "# Claude Atlas — no issues selected\n\n"
            "Nothing to fix. Run `claude-atlas check` first to see what's "
            "available, then pass a selection to `claude-atlas fix`."
        )

    n = len(rows)
    intro = (
        f"# Claude Atlas — {n} issue{'s' if n != 1 else ''} to triage\n\n"
        "claude-atlas detected the issues below in my Claude Code setup. "
        "For each one, please:\n\n"
        "1. Open both files and confirm whether the issue is real (not a false positive).\n"
        "2. Propose a fix following the suggestion under the issue.\n"
        "3. **Ask me to confirm before deleting or editing any file.** "
        "claude-atlas never modifies artifacts on its own and neither should you.\n"
    )

    sections: list[str] = [intro]
    for i, r in enumerate(rows, start=1):
        sev = r["severity"].upper()
        block = (
            f"\n## {i}. {r['kind_label']} ({sev})\n\n"
            f"- **Source:** `{r['source_path']}` (`{r['source_name']}`)\n"
            f"- **Target:** `{r['target_path']}` (`{r['target_name']}`)\n"
            f"- **Detail:** {r['detail']}\n"
        )
        if r.get("fix"):
            block += f"- **Suggested fix:** {r['fix']}\n"
        sections.append(block)

    sections.append(
        "\n---\n\nWork through them in order. Stop and ask me anything that's "
        "ambiguous."
    )
    return "".join(sections)


def collect_issues(result: ScanResult, severity: str | None = None) -> list[dict]:
    """Get sorted issue rows from a scan result, optionally filtered by severity."""
    rows = _filter_and_sort_issues(result)
    return filter_by_severity(rows, severity)
