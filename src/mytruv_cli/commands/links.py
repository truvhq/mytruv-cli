import click

from mytruv_cli.client.api import APIError, AuthRequired, NetworkError, TruvClient
from mytruv_cli.output.formatter import (
    OutputFormat,
    output_auth_error,
    output_csv,
    output_error,
    output_json,
    output_network_error,
    output_option,
    output_table,
    resolved_format,
)

_LINK_COLUMNS = ["link_id", "provider", "status", "data_source"]


@click.command("links")
@output_option
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
    except NetworkError as e:
        output_network_error(e.message)
        return
    except APIError as e:
        output_error(e.error, e.message)
        return

    fmt = resolved_format()
    if fmt == OutputFormat.JSON:
        output_json(data)
        return

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
    if fmt == OutputFormat.CSV:
        output_csv(rows, _LINK_COLUMNS)
        return
    output_table(rows, _LINK_COLUMNS, title="Connected Accounts")
