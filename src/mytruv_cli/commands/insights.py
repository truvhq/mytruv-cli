import click

from mytruv_cli.client.api import APIError, AuthRequired, NetworkError, TruvClient
from mytruv_cli.output.formatter import (
    is_interactive,
    output_auth_error,
    output_error,
    output_info,
    output_json,
    output_option,
)


@click.command("insights")
@output_option
def insights_cmd() -> None:
    """Show AI-generated insights about your finances.

    The backend generates insights asynchronously. If they are not ready yet,
    this command prints a hint and exits 0 so scripts can poll safely.

    Returns JSON: {"status": "completed" | "in_progress" | "not_started" | "failed",
                   "insights": [...]}
    """
    try:
        with TruvClient() as client:
            data = client.get_insights()
    except AuthRequired:
        output_auth_error()
        return
    except NetworkError as e:
        output_error("network_error", str(e))
        return
    except APIError as e:
        output_error(e.error, e.message)
        return

    status = data.get("status", "unknown")
    insights = data.get("insights") or []

    if not is_interactive():
        output_json(data)
        return

    if status in ("not_started", "in_progress"):
        output_info("Insights are still being generated. Try again in a minute.")
        return

    if status == "failed":
        output_info("[red]Insights generation failed.[/red]")
        return

    if not insights:
        output_info("No insights available.")
        return

    for item in insights:
        priority = (item.get("priority") or "").upper()
        title = item.get("title", "")
        summary = item.get("summary", "")
        detail = item.get("detail", "")
        follow_up = item.get("follow_up")
        category = item.get("category", "")

        output_info(f"\n[bold]{title}[/bold]  [dim]({category}, {priority})[/dim]")
        if summary:
            output_info(summary)
        if detail:
            output_info(detail)
        if follow_up:
            output_info(f"[cyan]→ {follow_up}[/cyan]")
