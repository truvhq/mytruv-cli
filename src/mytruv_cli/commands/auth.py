import click

from mytruv_cli.auth.store import clear_auth, is_authenticated
from mytruv_cli.client.api import APIError, AuthRequired, TruvClient
from mytruv_cli.config.settings import get_server_url
from mytruv_cli.output.formatter import output_error, output_json, output_success

# `mytruv_cli.auth.oauth` pulls httpx (and httpx's optional rich-based CLI shim).
# We import it lazily inside each callback so `mytruv --help` does not pay that cost.


@click.group("auth")
def auth_group() -> None:
    """Authenticate with your MyTruv account.

    Login opens a browser window for secure OAuth authentication.
    Tokens are stored locally and refreshed automatically.
    """


@auth_group.command("login")
@click.option("--no-browser", is_flag=True, help="Print the login URL instead of opening a browser.")
def login_cmd(no_browser: bool) -> None:
    """Authenticate via browser-based OAuth login.

    Opens your default browser to the MyTruv login page.
    After logging in, the CLI stores tokens locally for subsequent commands.
    Use --no-browser to get a URL you can open manually (useful for remote/headless machines).

    Returns JSON: {"status": "authenticated"}
    """
    from mytruv_cli.auth.oauth import OAuthError, login

    server_url = get_server_url()

    try:
        login(server_url, no_browser=no_browser)
    except OAuthError as e:
        output_error(e.error, e.message)

    result: dict = {"status": "authenticated"}

    try:
        with TruvClient() as client:
            user = client.get_user()
        result["user"] = {
            "email": user.get("email"),
            "first_name": user.get("first_name"),
            "last_name": user.get("last_name"),
        }
    except (AuthRequired, APIError):
        pass

    output_success(f"Authenticated as {result.get('user', {}).get('email', 'unknown')}")
    output_json(result)


@auth_group.command("logout")
def logout_cmd() -> None:
    """Log out and clear stored tokens.

    Revokes tokens on the server (best-effort) and removes local credentials.

    Returns JSON: {"status": "logged_out"}
    """
    if is_authenticated():
        from mytruv_cli.auth.oauth import revoke_token

        server_url = get_server_url()
        revoke_token(server_url)

    clear_auth()

    output_success("Logged out")
    output_json({"status": "logged_out"})


@auth_group.command("status")
def status_cmd() -> None:
    """Show current authentication status.

    Returns JSON: {"authenticated": bool, "user": {...} | null}
    """
    if not is_authenticated():
        output_json({"authenticated": False, "user": None})
        return

    result: dict = {"authenticated": True, "user": None}

    try:
        with TruvClient() as client:
            user = client.get_user()
        result["user"] = {
            "email": user.get("email"),
            "first_name": user.get("first_name"),
            "last_name": user.get("last_name"),
        }
    except (AuthRequired, APIError):
        result["authenticated"] = False

    output_json(result)
