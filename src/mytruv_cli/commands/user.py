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

_USER_COLUMNS = ["first_name", "last_name", "email", "phone"]


@click.command("user")
@output_option
def user_cmd() -> None:
    """Show your user profile.

    Returns JSON: {"first_name", "last_name", "email", "phone", "lifecycle": {...}}
    """
    try:
        with TruvClient() as client:
            data = client.get_user()
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
    elif fmt == OutputFormat.CSV:
        output_csv([data], _USER_COLUMNS)
    else:
        output_table([data], _USER_COLUMNS, title="User Profile")
