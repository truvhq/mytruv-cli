import click

from mytruv_cli.client.api import APIError, AuthRequired, NetworkError, TruvClient
from mytruv_cli.output.formatter import (
    OutputFormat,
    output_auth_error,
    output_csv_unsupported,
    output_error,
    output_info,
    output_json,
    output_network_error,
    output_option,
    output_table,
    resolved_format,
)


def _fmt_price(amount: object, currency: str | None) -> str:
    if amount in (None, ""):
        return ""
    try:
        value = f"{float(amount):.2f}"  # type: ignore[arg-type]
    except (TypeError, ValueError):
        value = str(amount)
    return f"{currency} {value}" if currency else value


@click.command("subscription")
@output_option
def subscription_cmd() -> None:
    """Show the active subscription, if any.

    Returns JSON: {"plan": {...}, "status": "...", "current_period_start": "...",
                   "current_period_end": "...", "trial_end": "..."}
    or null when there is no active subscription.
    """
    fmt = resolved_format()
    if fmt == OutputFormat.CSV:
        output_csv_unsupported()

    try:
        with TruvClient() as client:
            data = client.get_subscription()
    except AuthRequired:
        output_auth_error()
        return
    except NetworkError as e:
        output_network_error(e.message)
        return
    except APIError as e:
        output_error(e.error, e.message)
        return

    if data is None:
        if fmt == OutputFormat.JSON:
            output_json(None)
        else:
            output_info("No active subscription.")
        return

    if fmt == OutputFormat.JSON:
        output_json(data)
        return

    plan = data.get("plan") or {}
    row = {
        "plan": plan.get("name", ""),
        "price": _fmt_price(plan.get("price_amount"), plan.get("currency")),
        "interval": plan.get("interval", ""),
        "status": data.get("status", ""),
        "trial_end": data.get("trial_end") or "",
        "period": f"{data.get('current_period_start', '')} → {data.get('current_period_end', '')}",
    }
    output_table([row], ["plan", "price", "interval", "status", "trial_end", "period"], title="Subscription")
