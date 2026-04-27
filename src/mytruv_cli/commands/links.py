import click

from mytruv_cli.client.api import APIError, AuthRequired, NetworkError, TruvClient
from mytruv_cli.output.formatter import (
    OutputFormat,
    current_format,
    output_auth_error,
    output_error,
    output_json,
    output_option,
    output_table,
)


def _list_links() -> None:
    try:
        with TruvClient() as client:
            data = client.get_links()
    except AuthRequired:
        output_auth_error()
        return
    except APIError as e:
        output_error(e.error, e.message)
        return

    if current_format() == OutputFormat.JSON:
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
    output_table(rows, ["link_id", "provider", "status", "data_source"], title="Connected Accounts")


@click.group("links", invoke_without_command=True)
@output_option
@click.pass_context
def links_cmd(ctx: click.Context) -> None:
    """List connected financial accounts, or inspect them via subcommands.

    Running ``mytruv links`` with no subcommand lists all connections.
    """
    if ctx.invoked_subcommand is None:
        _list_links()


_PAYROLL_SOURCES = {"payroll", "employer", "income"}
_BANK_SOURCES = {"financial_accounts", "bank"}


def _find_link(links: list, link_id: str) -> dict | None:
    for link in links:
        if link.get("id") == link_id:
            return link
    return None


@links_cmd.command("report")
@click.argument("link_id")
@output_option
def report_cmd(link_id: str) -> None:
    """Show the income report for a link.

    Dispatches to the payroll report for payroll links and the bank
    transaction-based income report for financial-account links. Find
    link IDs via ``mytruv links``. Always rendered as JSON regardless
    of --output — the report payload is deeply nested and not tabular.
    """
    try:
        with TruvClient() as client:
            listing = client.get_links()
            links = listing if isinstance(listing, list) else listing.get("links", listing.get("results", []))
            link = _find_link(links, link_id)
            if link is None:
                output_error("not_found", f"Link {link_id} not found.")
                return

            data_source = link.get("data_source", "")
            if data_source in _PAYROLL_SOURCES:
                data = client.get_link_report(link_id)
            elif data_source in _BANK_SOURCES:
                data = client.get_bank_income_report(link_id)
            else:
                output_error(
                    "unsupported_link_type",
                    f"No report available for data_source={data_source!r}.",
                )
                return
    except AuthRequired:
        output_auth_error()
        return
    except NetworkError as e:
        output_error("network_error", str(e))
        return
    except APIError as e:
        output_error(e.error, e.message)
        return

    output_json(data)
