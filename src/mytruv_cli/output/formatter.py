import functools
import json
import sys

import click
from rich.console import Console
from rich.table import Table

from mytruv_cli.config.constants import EXIT_AUTH_REQUIRED, EXIT_ERROR

_console = Console(stderr=True)
_force_agent: bool = False


def set_agent_mode(enabled: bool) -> None:
    global _force_agent  # noqa: PLW0603
    _force_agent = enabled


def is_interactive() -> bool:
    """True when in human mode (TTY, no --agent flag). False for agents."""
    if _force_agent:
        return False
    return sys.stdout.isatty()


def agent_option(fn):
    """Decorator that adds --agent flag to a command."""

    @click.option("--agent", "-a", is_flag=True, default=False, help="Force JSON output (agent-friendly).")
    @functools.wraps(fn)
    def wrapper(*args, agent: bool, **kwargs):
        if agent:
            set_agent_mode(True)
        return fn(*args, **kwargs)

    return wrapper


def output_json(data: object) -> None:
    """Write JSON to stdout. Always valid JSON — safe for agents to parse."""
    print(json.dumps(data, indent=2, default=str))


def output_table(rows: list[dict], columns: list[str], title: str | None = None) -> None:
    """Render a rich table to stderr. In agent mode, writes JSON to stdout instead."""
    if is_interactive():
        table = Table(title=title)
        for col in columns:
            table.add_column(col)
        for row in rows:
            table.add_row(*[str(row.get(col, "")) for col in columns])
        _console.print(table)
    else:
        output_json(rows)


def output_info(message: str) -> None:
    """Print rich-formatted message to stderr. Skipped in agent mode."""
    if is_interactive():
        _console.print(message)


def output_error(error: str, message: str, exit_code: int = EXIT_ERROR) -> None:
    """Print structured error to stderr (human) and stdout (agent), then exit."""
    error_obj = {"error": error, "message": message}

    if is_interactive():
        _console.print(f"[red]Error:[/red] {message}")
    else:
        print(json.dumps(error_obj), file=sys.stdout)

    raise SystemExit(exit_code)


def output_auth_error() -> None:
    """Shortcut for authentication errors."""
    output_error(
        "auth_required",
        "Not authenticated. Run 'mytruv auth login' first.",
        exit_code=EXIT_AUTH_REQUIRED,
    )


def output_success(message: str) -> None:
    """Print success message to stderr. Skipped in agent mode."""
    if is_interactive():
        _console.print(f"[green]{message}[/green]")
