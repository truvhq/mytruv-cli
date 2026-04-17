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
    render_markdown,
    resolved_format,
)

_NOT_READY_MESSAGE = "Insights are still being generated. Try again in a minute."


@click.command("insights")
@output_option
def insights_cmd() -> None:
    """Show AI-generated insights about your finances.

    Calls GET /v2/user/insights. When status is 'completed', renders the
    insights (Markdown in a TTY, JSON otherwise). Otherwise prints a
    wait-hint and exits 0 — insights generate lazily server-side, so a
    later call will succeed.

    Returns JSON: {"status": "not_started|in_progress|completed", "insights": ...}
    """
    fmt = resolved_format()
    if fmt == OutputFormat.CSV:
        output_csv_unsupported()

    try:
        with TruvClient() as client:
            data = client.get_insights()
    except AuthRequired:
        output_auth_error()
        return
    except NetworkError as e:
        output_network_error(e.message)
        return
    except APIError as e:
        output_error(e.error, e.message)
        return

    if fmt == OutputFormat.JSON:
        output_json(data)
        return

    status = data.get("status", "")
    if status != "completed":
        output_info(_NOT_READY_MESSAGE)
        return

    insights = data.get("insights")
    if isinstance(insights, str):
        render_markdown(insights)
    else:
        output_info(str(insights))
