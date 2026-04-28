import csv
import functools
import json
import os
import sys
from enum import Enum
from typing import TYPE_CHECKING

import click

from mytruv_cli.config.constants import EXIT_AUTH_REQUIRED, EXIT_ERROR

if TYPE_CHECKING:
    from rich.console import Console


class OutputFormat(str, Enum):
    JSON = "json"
    CSV = "csv"


_format: OutputFormat | None = None
_no_color: bool = False
_console: "Console | None" = None


def _env_no_color() -> bool:
    return bool(os.environ.get("NO_COLOR"))


def _get_console() -> "Console":
    """Build the stderr Console on first use. Rich is the heaviest import in the
    CLI; deferring it keeps `--help` and other no-output paths fast."""
    global _console  # noqa: PLW0603
    if _console is None:
        from rich.console import Console

        _console = Console(stderr=True, no_color=_no_color or _env_no_color())
    return _console


def set_format(fmt: OutputFormat | None) -> None:
    global _format  # noqa: PLW0603
    _format = fmt


def set_no_color(enabled: bool) -> None:
    global _no_color, _console  # noqa: PLW0603
    _no_color = enabled
    _console = None  # rebuild on next access


def current_format() -> OutputFormat | None:
    """Resolve the effective output format. None means render a human-oriented table."""
    if _format is not None:
        return _format
    return None if sys.stdout.isatty() else OutputFormat.JSON


def is_interactive() -> bool:
    """True when rendering human-oriented tables. False for JSON/CSV."""
    return current_format() is None


def output_option(fn):
    """Adds --output / --json / --no-color flags to a command."""

    @click.option(
        "--output",
        "-o",
        "output_fmt",
        type=click.Choice(["json", "csv"], case_sensitive=False),
        default=None,
        help="Output format: json or csv. Default: table on TTY, json when piped.",
    )
    @click.option("--json", "json_flag", is_flag=True, default=False, help="Shorthand for --output json.")
    @click.option("--no-color", "no_color_flag", is_flag=True, default=False, help="Disable ANSI color output.")
    @functools.wraps(fn)
    def wrapper(
        *args,
        output_fmt: str | None,
        json_flag: bool,
        no_color_flag: bool,
        **kwargs,
    ):
        # Reset state so earlier invocations (tests, embedded callers) don't leak.
        set_format(None)
        set_no_color(no_color_flag)

        if output_fmt is not None:
            set_format(OutputFormat(output_fmt.lower()))
        elif json_flag:
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
    """Render rows in the active output format."""
    fmt = current_format()
    if fmt is None:
        from rich.table import Table

        table = Table(title=title)
        for col in columns:
            table.add_column(col)
        for row in rows:
            table.add_row(*[str(row.get(col, "")) for col in columns])
        _get_console().print(table)
    elif fmt == OutputFormat.CSV:
        output_csv(rows, columns)
    else:
        output_json(rows)


def output_info(message: str) -> None:
    """Print rich-formatted message to stderr. Skipped outside TABLE mode."""
    if is_interactive():
        _get_console().print(message)


def output_warning(message: str) -> None:
    """Emit a warning to stderr regardless of output format, so stdout stays format-consistent."""
    if is_interactive():
        _get_console().print(f"[yellow]Warning:[/yellow] {message}")
    else:
        print(f"Warning: {message}", file=sys.stderr)


def output_error(error: str, message: str, exit_code: int = EXIT_ERROR) -> None:
    """Write a structured error to stderr and exit, keeping stdout format-consistent."""
    if is_interactive():
        _get_console().print(f"[red]Error:[/red] {message}")
    else:
        print(json.dumps({"error": error, "message": message}), file=sys.stderr)

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
        _get_console().print(f"[green]{message}[/green]")
