import csv
import functools
import json
import os
import sys
from enum import Enum

import click
from rich.console import Console
from rich.table import Table

from mytruv_cli.config.constants import EXIT_AUTH_REQUIRED, EXIT_ERROR


class OutputFormat(str, Enum):
    TABLE = "table"
    JSON = "json"
    CSV = "csv"


_format: OutputFormat | None = None
_no_color: bool = False
_agent_deprecation_shown: bool = False


def _env_no_color() -> bool:
    return bool(os.environ.get("NO_COLOR"))


def _make_console() -> Console:
    return Console(stderr=True, no_color=_no_color or _env_no_color())


_console = _make_console()


def set_format(fmt: OutputFormat | None) -> None:
    global _format  # noqa: PLW0603
    _format = fmt


def set_no_color(enabled: bool) -> None:
    global _no_color, _console  # noqa: PLW0603
    _no_color = enabled
    _console = _make_console()


def current_format() -> OutputFormat:
    """Resolve the effective output format. Falls back to TTY detection."""
    if _format is not None:
        return _format
    return OutputFormat.TABLE if sys.stdout.isatty() else OutputFormat.JSON


def is_interactive() -> bool:
    """True when rendering human-oriented tables. False for JSON/CSV."""
    return current_format() == OutputFormat.TABLE


def _emit_agent_deprecation() -> None:
    global _agent_deprecation_shown  # noqa: PLW0603
    if _agent_deprecation_shown:
        return
    _agent_deprecation_shown = True
    print("Warning: --agent is deprecated; use --output json (or --json) instead.", file=sys.stderr)


def output_option(fn):
    """Adds --output / --json / --agent / --no-color flags to a command."""

    @click.option(
        "--output",
        "-o",
        "output_fmt",
        type=click.Choice(["table", "json", "csv"], case_sensitive=False),
        default=None,
        help="Output format: table, json, or csv. Default: table on TTY, json when piped.",
    )
    @click.option("--json", "json_flag", is_flag=True, default=False, help="Shorthand for --output json.")
    @click.option(
        "--agent",
        "-a",
        "agent_flag",
        is_flag=True,
        default=False,
        hidden=True,
        help="Deprecated: use --output json.",
    )
    @click.option("--no-color", "no_color_flag", is_flag=True, default=False, help="Disable ANSI color output.")
    @functools.wraps(fn)
    def wrapper(
        *args,
        output_fmt: str | None,
        json_flag: bool,
        agent_flag: bool,
        no_color_flag: bool,
        **kwargs,
    ):
        if no_color_flag:
            set_no_color(True)
        if output_fmt is not None:
            set_format(OutputFormat(output_fmt.lower()))
        elif json_flag:
            set_format(OutputFormat.JSON)
        elif agent_flag:
            _emit_agent_deprecation()
            set_format(OutputFormat.JSON)
        return fn(*args, **kwargs)

    return wrapper


def output_json(data: object) -> None:
    """Write JSON to stdout."""
    print(json.dumps(data, indent=2, default=str))


def output_csv(rows: list[dict], columns: list[str]) -> None:
    """Write CSV to stdout using `columns` as the field set."""
    writer = csv.DictWriter(sys.stdout, fieldnames=columns, extrasaction="ignore")
    writer.writeheader()
    for row in rows or []:
        writer.writerow({c: row.get(c, "") for c in columns})


def output_table(rows: list[dict], columns: list[str], title: str | None = None) -> None:
    """Render a table (TTY), CSV to stdout, or JSON of the rows — depending on the active format."""
    fmt = current_format()
    if fmt == OutputFormat.TABLE:
        table = Table(title=title)
        for col in columns:
            table.add_column(col)
        for row in rows:
            table.add_row(*[str(row.get(col, "")) for col in columns])
        _console.print(table)
    elif fmt == OutputFormat.CSV:
        output_csv(rows, columns)
    else:
        output_json(rows)


def output_info(message: str) -> None:
    """Print rich-formatted message to stderr. Skipped outside TABLE mode."""
    if is_interactive():
        _console.print(message)


def output_error(error: str, message: str, exit_code: int = EXIT_ERROR) -> None:
    """Print structured error and exit."""
    error_obj = {"error": error, "message": message}

    if is_interactive():
        _console.print(f"[red]Error:[/red] {message}")
    else:
        print(json.dumps(error_obj), file=sys.stdout)

    raise SystemExit(exit_code)


def output_auth_error() -> None:
    output_error(
        "auth_required",
        "Not authenticated. Run 'mytruv auth login' first.",
        exit_code=EXIT_AUTH_REQUIRED,
    )


def output_success(message: str) -> None:
    """Print success message to stderr. Skipped outside TABLE mode."""
    if is_interactive():
        _console.print(f"[green]{message}[/green]")
