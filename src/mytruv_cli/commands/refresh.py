import click

from mytruv_cli.client.api import APIError, AuthRequired, NetworkError, TruvClient
from mytruv_cli.output.formatter import (
    OutputFormat,
    current_format,
    output_auth_error,
    output_error,
    output_info,
    output_json,
    output_option,
    output_table,
)


@click.command("refresh")
@click.option(
    "--link-id",
    "link_ids",
    multiple=True,
    metavar="ID",
    help="Refresh only the given link (repeat for multiple). Omit to refresh all eligible links.",
)
@output_option
def refresh_cmd(link_ids: tuple[str, ...]) -> None:
    """Trigger a data refresh for connected financial links.

    Only links with status 'done' that haven't been updated in the last 8 hours
    are eligible; others are counted in skipped_count. Returns JSON:
    {"refreshed_links": [{"link_id", "task_id", "provider_name"}, ...], "skipped_count": int}
    """
    try:
        with TruvClient() as client:
            result = client.refresh_data(list(link_ids) if link_ids else None)
    except AuthRequired:
        output_auth_error()
        return
    except NetworkError as e:
        output_error("network_error", str(e))
        return
    except APIError as e:
        output_error(e.error, e.message)
        return

    fmt = current_format()
    if fmt == OutputFormat.JSON:
        output_json(result)
        return

    refreshed = result.get("refreshed_links", []) or []
    skipped = result.get("skipped_count", 0)

    if not refreshed:
        output_info(f"No links refreshed (skipped: {skipped}).")
        if fmt == OutputFormat.CSV:
            output_table([], ["link_id", "task_id", "provider"], title=None)
        return

    rows = [
        {
            "link_id": r.get("link_id", ""),
            "task_id": r.get("task_id", ""),
            "provider": r.get("provider_name", ""),
        }
        for r in refreshed
    ]
    output_table(rows, ["link_id", "task_id", "provider"], title="Refreshed Links")
    output_info(f"Refreshed: {len(refreshed)} · Skipped: {skipped}")
