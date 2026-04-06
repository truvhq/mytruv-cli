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


@click.command("user")
@agent_option
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
    except APIError as e:
        output_error(e.error, e.message)
        return

    if is_interactive():
        output_table(
            [data],
            ["first_name", "last_name", "email", "phone"],
            title="User Profile",
        )
    else:
        output_json(data)
