import click

from mytruv_cli.client.api import APIError, AuthRequired, NetworkError, TruvClient
from mytruv_cli.output.formatter import (
    OutputFormat,
    current_format,
    output_auth_error,
    output_error,
    output_json,
    output_option,
    output_success,
    output_table,
)


def _list_links() -> None:
    try:
        with TruvClient() as client:
            data = client.get_links()
    except AuthRequired:
        output_auth_error()
        return
    except NetworkError as e:
        output_error("network_error", str(e))
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
    """List connected financial accounts, or manage them via subcommands.

    Running ``mytruv links`` with no subcommand lists all connections.
    Subcommands: ``disconnect``, ``report``.
    """
    if ctx.invoked_subcommand is None:
        _list_links()


@links_cmd.command("disconnect")
@click.argument("link_id")
@click.option("--yes", "-y", "skip_confirm", is_flag=True, help="Skip confirmation prompt.")
@output_option
def disconnect_cmd(link_id: str, skip_confirm: bool) -> None:
    """Permanently remove a link and all its associated data."""
    if not skip_confirm:
        click.confirm(
            f"This will permanently disconnect link {link_id} and remove all its data. Continue?",
            abort=True,
            err=True,
        )

    try:
        with TruvClient() as client:
            client.delete_link(link_id)
    except AuthRequired:
        output_auth_error()
        return
    except NetworkError as e:
        output_error("network_error", str(e))
        return
    except APIError as e:
        output_error(e.error, e.message)
        return

    if current_format() == OutputFormat.TABLE:
        output_success(f"Disconnected {link_id}.")
    else:
        output_json({"link_id": link_id, "disconnected": True})


@links_cmd.command("report")
@click.argument("link_id")
@output_option
def report_cmd(link_id: str) -> None:
    """Show the payroll income report for a link.

    The report payload is nested and non-tabular; always rendered as JSON
    on stdout regardless of --output.
    """
    try:
        with TruvClient() as client:
            data = client.get_link_report(link_id)
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
