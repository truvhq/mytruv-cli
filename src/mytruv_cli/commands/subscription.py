import click

from mytruv_cli.client.api import APIError, AuthRequired, NetworkError, TruvClient
from mytruv_cli.output.formatter import (
    OutputFormat,
    current_format,
    is_interactive,
    output_auth_error,
    output_error,
    output_info,
    output_json,
    output_option,
    output_table,
)


def _fmt_price(cents: int | None, currency: str | None) -> str:
    if cents is None:
        return ""
    symbol = "$" if (currency or "").lower() == "usd" else f"{currency} "
    return f"{symbol}{cents / 100:.2f}"


def _fmt_period(ts: int | None) -> str:
    if not ts:
        return ""
    from datetime import UTC, datetime

    return datetime.fromtimestamp(ts, tz=UTC).strftime("%Y-%m-%d")


@click.command("subscription")
@output_option
def subscription_cmd() -> None:
    """Show the active subscription.

    Returns JSON: {"active": bool, "subscription": {...} | null}
    Exits 0 when there is no active subscription.
    """
    try:
        with TruvClient() as client:
            sub = client.get_subscription()
    except AuthRequired:
        output_auth_error()
        return
    except NetworkError as e:
        output_error("network_error", str(e))
        return
    except APIError as e:
        output_error(e.error, e.message)
        return

    payload = {"active": sub is not None, "subscription": sub}

    if sub is None:
        output_info("No active subscription.")
        if not is_interactive():
            output_json(payload)
        return

    if current_format() == OutputFormat.JSON:
        output_json(payload)
        return

    row = {
        "plan": sub.get("name", ""),
        "price": _fmt_price(sub.get("price"), sub.get("currency")),
        "interval": sub.get("interval", ""),
        "trial": "yes" if sub.get("is_trial") else "no",
        "period_end": _fmt_period(sub.get("current_period_end")),
    }
    output_table([row], ["plan", "price", "interval", "trial", "period_end"], title="Active Subscription")
