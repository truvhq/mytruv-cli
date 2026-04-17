import csv
import functools
import json
import os
import sys
from enum import StrEnum

import click
from rich.console import Console
from rich.table import Table

from mytruv_cli.config.constants import EXIT_AUTH_REQUIRED, EXIT_ERROR


class OutputFormat(StrEnum):
    TABLE = "table"
    JSON = "json"
    CSV = "csv"


_force_format: OutputFormat | None = None
_console: Console = Console(stderr=True, no_color=bool(os.environ.get("NO_COLOR")))


def set_output_format(fmt: OutputFormat | None) -> None:
    global _force_format  # noqa: PLW0603
    _force_format = fmt


def _disable_color() -> None:
    global _console  # noqa: PLW0603
    _console = Console(stderr=True, no_color=True)


def resolved_format() -> OutputFormat:
    """Return the effective output format: explicit override > TTY auto-detect."""
    if _force_format is not None:
        return _force_format
    return OutputFormat.TABLE if sys.stdout.isatty() else OutputFormat.JSON


def is_interactive() -> bool:
    """True when output is formatted for humans (tables, colors). False for JSON/CSV."""
    return resolved_format() == OutputFormat.TABLE


def output_option(fn):
    """Decorator that adds --output/--json/--no-color/--agent flags.

    Precedence: --output > --json > --agent > TTY detection.
    --agent is hidden and prints a deprecation warning to stderr.
    """

    @click.option(
        "--output",
        "-o",
        "output_fmt",
        type=click.Choice([f.value for f in OutputFormat], case_sensitive=False),
        default=None,
        help="Output format: table, json, or csv. Defaults to table in TTY, json when piped.",
    )
    @click.option("--json", "json_shorthand", is_flag=True, default=False, help="Shorthand for --output json.")
    @click.option("--no-color", is_flag=True, default=False, help="Disable colored output.")
    @click.option("--agent", is_flag=True, default=False, hidden=True, help="[Deprecated] Use --output json.")
    @functools.wraps(fn)
    def wrapper(*args, output_fmt: str | None, json_shorthand: bool, no_color: bool, agent: bool, **kwargs):
        if no_color:
            _disable_color()

        if output_fmt:
            set_output_format(OutputFormat(output_fmt.lower()))
        elif json_shorthand:
            set_output_format(OutputFormat.JSON)
        elif agent:
            print(
                "[mytruv] --agent is deprecated; use --output json (or --json). It will be removed in v2.0.",
                file=sys.stderr,
            )
            set_output_format(OutputFormat.JSON)

        return fn(*args, **kwargs)

    return wrapper


def output_json(data: object) -> None:
    """Write JSON to stdout. Always valid JSON — safe for agents to parse."""
    print(json.dumps(data, indent=2, default=str))


def output_csv(rows: list[dict], columns: list[str]) -> None:
    """Write CSV to stdout with the given column order."""
    writer = csv.DictWriter(sys.stdout, fieldnames=columns, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow(row)


def output_raw_csv(content: str | bytes) -> None:
    """Write pre-formatted CSV (e.g. from a server-side export endpoint) to stdout verbatim."""
    if isinstance(content, bytes):
        sys.stdout.buffer.write(content)
    else:
        sys.stdout.write(content)


def output_table(rows: list[dict], columns: list[str], title: str | None = None) -> None:
    """Render rows as a rich table to stderr. Callers must route JSON/CSV themselves."""
    table = Table(title=title)
    for col in columns:
        table.add_column(col)
    for row in rows:
        table.add_row(*[str(row.get(col, "")) for col in columns])
    _console.print(table)


def output_info(message: str) -> None:
    """Print a rich-formatted message to stderr. Silent in non-interactive modes."""
    if is_interactive():
        _console.print(message)


def output_error(error: str, message: str, exit_code: int = EXIT_ERROR, hint: str | None = None) -> None:
    """Print a structured error and exit. Human-readable in TTY, JSON on stdout otherwise."""
    if is_interactive():
        _console.print(f"[red]Error:[/red] {message}")
        if hint:
            _console.print(f"[dim]{hint}[/dim]")
    else:
        payload: dict[str, str] = {"error": error, "message": message}
        if hint:
            payload["hint"] = hint
        print(json.dumps(payload), file=sys.stdout)

    raise SystemExit(exit_code)


def output_auth_error() -> None:
    """Shortcut for authentication errors."""
    output_error(
        "auth_required",
        "Not authenticated.",
        exit_code=EXIT_AUTH_REQUIRED,
        hint="Run 'mytruv auth login' first.",
    )


def output_network_error(message: str) -> None:
    """Shortcut for network connectivity errors."""
    output_error(
        "network_error",
        f"Could not reach the mytruv server: {message}",
        hint="Check your internet connection and try again.",
    )


def output_csv_unsupported() -> None:
    """Shortcut for commands that can't express their output as a single CSV table."""
    output_error(
        "csv_unsupported",
        "CSV output is not supported for this command.",
        hint="Use --output json instead.",
    )


def output_success(message: str) -> None:
    """Print a success message to stderr. Silent in non-interactive modes."""
    if is_interactive():
        _console.print(f"[green]{message}[/green]")
