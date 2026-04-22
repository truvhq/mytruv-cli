"""MCP stdio server exposing MyTruv financial data as tools."""

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from mytruv_cli.auth.oauth import OAuthError, login, revoke_token
from mytruv_cli.auth.store import clear_auth, get_valid_token, is_authenticated
from mytruv_cli.client.api import APIError, AuthRequired, TruvClient
from mytruv_cli.config.settings import get_server_url

mcp = FastMCP("MyTruv")

_ANNOTATIONS = ToolAnnotations(readOnlyHint=True, destructiveHint=False, openWorldHint=False)
_AUTH_ANNOTATIONS = ToolAnnotations(
    readOnlyHint=False, destructiveHint=False, idempotentHint=True, openWorldHint=False
)


def _call(fn_name: str, **kwargs: object) -> dict:
    """Call a TruvClient method and return its result, or an error dict."""
    try:
        with TruvClient() as client:
            method = getattr(client, fn_name)
            return method(**kwargs)
    except AuthRequired as e:
        return {"error": "auth_required", "message": str(e)}
    except (APIError, OAuthError) as e:
        return {"error": e.error, "message": str(e)}


@mcp.tool(annotations=_AUTH_ANNOTATIONS)
def authenticate() -> dict:
    """Log in to MyTruv by opening the browser for OAuth authentication.

    Call this when other tools return an 'auth_required' error.
    Opens the default browser for the user to sign in, then stores credentials locally.
    """
    if get_valid_token():
        return {"status": "already_authenticated"}

    try:
        login(get_server_url())
        return {"status": "authenticated"}
    except OAuthError as e:
        return {"error": e.error, "message": e.message}


@mcp.tool(annotations=_AUTH_ANNOTATIONS)
def logout() -> dict:
    """Log out and clear stored MyTruv credentials.

    Revokes tokens server-side (best-effort) and removes local credentials.
    Safe to call when already logged out.
    """
    if is_authenticated():
        revoke_token(get_server_url())
    clear_auth()
    return {"status": "logged_out"}


@mcp.tool(annotations=_ANNOTATIONS)
def account_balances() -> dict:
    """Get current balances for all connected bank accounts.

    Returns per-account details and aggregated totals grouped by account type.
    Use balance_history instead if you need trends over time.
    """
    return _call("get_balances")


@mcp.tool(annotations=_ANNOTATIONS)
def transactions(
    from_date: str,
    to_date: str | None = None,
    categories: str | None = None,
) -> dict:
    """List bank transactions within a date range.

    Args:
        from_date: Start date in YYYY-MM-DD format.
        to_date: End date in YYYY-MM-DD format. Defaults to today.
        categories: Comma-separated category filter. Example: 'Income,Transfer'.
    """
    return _call("get_transactions", from_date=from_date, to_date=to_date, categories=categories)


@mcp.tool(annotations=_ANNOTATIONS)
def spending_analysis(
    group_by: str = "category",
    time_period: str = "month",
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict:
    """Analyze spending patterns grouped by category, merchant, or time period.

    Args:
        group_by: How to group — 'category', 'merchant', or 'time_period'.
        time_period: Time bucket — 'day', 'week', or 'month'.
        start_date: Start date (YYYY-MM-DD). Defaults to 30 days ago.
        end_date: End date (YYYY-MM-DD). Defaults to today.
    """
    params: dict[str, str] = {"group_by": group_by, "time_period": time_period}
    if start_date:
        params["start_date"] = start_date
    if end_date:
        params["end_date"] = end_date
    return _call("get_spending", **params)


@mcp.tool(annotations=_ANNOTATIONS)
def income_report(days: int = 90) -> dict:
    """Get income report from payroll and bank sources.

    Combines income from payroll providers and bank transaction analysis.

    Args:
        days: Number of days to include (1-365). Default: 90.
    """
    return _call("get_income", days=days)


@mcp.tool(annotations=_ANNOTATIONS)
def recurring_transactions() -> dict:
    """Detect recurring transactions — subscriptions, bills, and recurring income.

    Identifies recurring inflows and outflows from connected bank accounts.
    """
    return _call("get_recurring")


@mcp.tool(annotations=_ANNOTATIONS)
def balance_history(
    date_range: str = "3M",
    time_period: str = "week",
) -> dict:
    """Get historical balance trends showing assets, liabilities, and net worth over time.

    Args:
        date_range: How far back — '1M', '3M', '6M', '1Y', or 'ALL'.
        time_period: Aggregation period — 'day', 'week', or 'month'.
    """
    return _call("get_balance_history", date_range=date_range, time_period=time_period)


@mcp.tool(annotations=_ANNOTATIONS)
def liabilities() -> dict:
    """Get liabilities across all connected accounts.

    Includes credit cards and loans with current balances and credit limits.
    """
    return _call("get_liabilities")


@mcp.tool(annotations=_ANNOTATIONS)
def connected_accounts() -> dict:
    """List all connected account links.

    Returns link IDs, providers, data sources, and connection status.
    """
    return _call("get_links")


def run_server() -> None:
    """Entry point for the MCP stdio server."""
    mcp.run(transport="stdio")
