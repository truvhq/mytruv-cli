import click

from mytruv_cli.client.api import APIError, AuthRequired, TruvClient
from mytruv_cli.output.formatter import (
    agent_option,
    is_interactive,
    output_auth_error,
    output_error,
    output_json,
    output_table,
)


@click.command("links")
@agent_option
def links_cmd() -> None:
    """List connected financial accounts.

    Shows all linked bank accounts and payroll providers with their
    connection status and data source type.

    Returns JSON: {"links": [...], "count": int}
    """
    try:
        with TruvClient() as client:
            data = client.get_links()
    except AuthRequired:
        output_auth_error()
        return
    except APIError as e:
        output_error(e.error, e.message)
        return

    if is_interactive():
        links = data if isinstance(data, list) else data.get("links", data.get("results", []))
        rows = [
            {
                "link_id": link.get("id", ""),
                "provider": (link.get("provider") or {}).get("name", link.get("provider_id", "")),
                "status": link.get("status", ""),
                "data_source": link.get("data_source", ""),
            }
            for link in links
        ]
        output_table(rows, ["link_id", "provider", "status", "data_source"], title="Connected Accounts")
    else:
        output_json(data)
