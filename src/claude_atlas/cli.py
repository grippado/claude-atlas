"""Command-line interface for claude-atlas."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from claude_atlas import __version__
from claude_atlas.analysis.graph import build_all_edges
from claude_atlas.analysis.llm_judge import DEFAULT_MODEL, refine_with_llm
from claude_atlas.check import run_check
from claude_atlas.models import ScanResult, Severity
from claude_atlas.report.renderer import render_html
from claude_atlas.scanner.discovery import resolve_scan_targets
from claude_atlas.scanner.parsers import parse_memory_file, scan_claude_dir

app = typer.Typer(
    name="claude-atlas",
    help="Scan, map, and visualize your Claude Code setup.",
    no_args_is_help=True,
    add_completion=False,
)
console = Console()


def _run_scan(
    paths: list[Path],
    no_global: bool,
    auto_discover: list[Path],
    max_depth: int,
    include_memory: bool,
) -> ScanResult:
    roots = resolve_scan_targets(
        paths=paths,
        include_global=not no_global,
        auto_discover_from=auto_discover or None,
        max_depth=max_depth,
    )

    artifacts = []
    for root in roots:
        artifacts.extend(scan_claude_dir(root))

    if include_memory:
        memory_roots = [r.parent if r.name == ".claude" else r for r in roots]
        if auto_discover:
            memory_roots.extend(auto_discover)
        from claude_atlas.scanner.discovery import find_memory_files

        for mp in find_memory_files(memory_roots, max_depth=max_depth):
            art = parse_memory_file(mp)
            if art:
                artifacts.append(art)

    edges = build_all_edges(artifacts)
    return ScanResult(artifacts=artifacts, edges=edges, roots_scanned=roots)


@app.command()
def scan(
    paths: list[Path] = typer.Option(
        None, "--paths", "-p",
        help="Explicit .claude/ dirs or repo dirs to scan. Repeatable.",
    ),
    auto_discover: list[Path] = typer.Option(
        None, "--auto-discover", "-a",
        help="Trees to walk looking for nested .claude/ dirs. Repeatable.",
    ),
    output: Path = typer.Option(
        Path("./claude-atlas.html"), "--output", "-o", help="Output HTML path.",
    ),
    no_global: bool = typer.Option(False, "--no-global", help="Skip scanning ~/.claude."),
    max_depth: int = typer.Option(4, "--max-depth", help="Max walk depth."),
    no_memory: bool = typer.Option(False, "--no-memory", help="Skip CLAUDE.md memory files."),
    semantic: bool = typer.Option(
        False, "--semantic",
        help="Refine duplicate candidates with Anthropic API (needs ANTHROPIC_API_KEY).",
    ),
    model: str = typer.Option(DEFAULT_MODEL, "--model", help="Model for --semantic."),
) -> None:
    """Scan, analyze, and render the report in one shot."""
    paths = paths or []
    auto_discover = auto_discover or []

    with console.status("[bold cyan]Scanning..."):
        result = _run_scan(
            paths=paths, no_global=no_global, auto_discover=auto_discover,
            max_depth=max_depth, include_memory=not no_memory,
        )

    if semantic:
        with console.status("[bold cyan]Refining with LLM judge..."):
            result.edges = refine_with_llm(result.edges, result.artifacts, model=model)

    _print_summary(result)

    out_path = render_html(result, output)
    console.print(f"\n[bold green]✓[/bold green] Report written to [cyan]{out_path}[/cyan]")


@app.command()
def check(
    paths: list[Path] = typer.Option(
        None, "--paths", "-p",
        help="Explicit .claude/ dirs or repo dirs to scan. Repeatable.",
    ),
    auto_discover: list[Path] = typer.Option(
        None, "--auto-discover", "-a",
        help="Trees to walk looking for nested .claude/ dirs. Repeatable.",
    ),
    no_global: bool = typer.Option(False, "--no-global", help="Skip scanning ~/.claude."),
    max_depth: int = typer.Option(4, "--max-depth", help="Max walk depth."),
    no_memory: bool = typer.Option(False, "--no-memory", help="Skip CLAUDE.md memory files."),
    max_severity: str = typer.Option(
        Severity.HIGH.value, "--max-severity",
        help="Exit 1 if any issue at this severity or above is found. "
             "One of: low, medium, high, none. Default: high.",
    ),
    output_format: str = typer.Option(
        "text", "--format",
        help="Output format: text (default, lint-style), json, or github (Actions annotations).",
    ),
    top: int = typer.Option(
        10, "--top",
        help="Show top N most severe issues. Pass 0 to show all. Default: 10.",
    ),
    quiet: bool = typer.Option(
        False, "--quiet", "-q",
        help="Only print summary line; suppress per-issue details.",
    ),
) -> None:
    """
    Lint-style health check of your Claude Code setup.

    Designed for pre-commit hooks, CI, and quick terminal checks.
    Exits 0 if no issues at or above --max-severity, else 1.

    Examples:
      claude-atlas check                              # check ~/.claude, fail on HIGH
      claude-atlas check --max-severity medium       # also fail on MEDIUM
      claude-atlas check --format github             # for GitHub Actions
      claude-atlas check --top 0 --format json       # everything as JSON
      claude-atlas check --quiet                     # one-line summary only
    """
    valid_severities = {s.value for s in Severity}
    if max_severity not in valid_severities:
        console.print(
            f"[bold red]error:[/bold red] --max-severity must be one of "
            f"{sorted(valid_severities)}, got {max_severity!r}",
            highlight=False,
        )
        raise typer.Exit(2)

    valid_formats = {"text", "json", "github"}
    if output_format not in valid_formats:
        console.print(
            f"[bold red]error:[/bold red] --format must be one of "
            f"{sorted(valid_formats)}, got {output_format!r}",
            highlight=False,
        )
        raise typer.Exit(2)

    paths = paths or []
    auto_discover = auto_discover or []

    try:
        result = _run_scan(
            paths=paths, no_global=no_global, auto_discover=auto_discover,
            max_depth=max_depth, include_memory=not no_memory,
        )
    except Exception as e:
        console.print(f"[bold red]scan failed:[/bold red] {e}", highlight=False)
        raise typer.Exit(2) from e

    exit_code = run_check(
        result,
        max_severity=max_severity,
        output_format=output_format,
        top=top,
        quiet=quiet,
    )
    raise typer.Exit(exit_code)


@app.command()
def report(
    paths: list[Path] = typer.Option(None, "--paths", "-p"),
    output: Path = typer.Option(Path("./claude-atlas.html"), "--output", "-o"),
) -> None:
    """Alias for ``scan`` with default flags. Useful for quick re-renders."""
    scan(
        paths=paths, auto_discover=None, output=output,
        no_global=False, max_depth=4, no_memory=False,
        semantic=False, model=DEFAULT_MODEL,
    )


@app.command()
def version() -> None:
    """Print the installed claude-atlas version."""
    console.print(f"claude-atlas {__version__}")


def _print_summary(result: ScanResult) -> None:
    table = Table(title="Scan summary", show_header=True, header_style="bold cyan")
    table.add_column("metric")
    table.add_column("value", justify="right")
    for k, v in sorted(result.stats().items()):
        table.add_row(k, str(v))
    console.print(table)

    issues = result.issues
    if issues:
        console.print(f"\n[bold yellow]⚠[/bold yellow]  {len(issues)} issue(s) detected.")
    else:
        console.print("\n[bold green]✓[/bold green] No issues detected.")


if __name__ == "__main__":
    app()
