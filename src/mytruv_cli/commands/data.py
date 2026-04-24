from collections.abc import Callable

import click

from mytruv_cli.client.api import APIError, AuthRequired, TruvClient
from mytruv_cli.output.formatter import (
    OutputFormat,
    current_format,
    output_auth_error,
    output_csv,
    output_error,
    output_info,
    output_json,
    output_option,
    output_table,
    output_warning,
)


def _fmt_dollar(val: str | None) -> str:
    if not val:
        return ""
    try:
        return f"${float(val):,.2f}"
    except (ValueError, TypeError):
        return str(val)


def _fmt_pct(val: str | None) -> str:
    if not val:
        return ""
    try:
        return f"{float(val):.1f}%"
    except (ValueError, TypeError):
        return str(val)


def _fetch(fetch_fn: Callable[[TruvClient], dict]) -> dict:
    """Create client, call fetch_fn, handle auth/API errors. Returns data or exits."""
    try:
        with TruvClient() as client:
            return fetch_fn(client)
    except AuthRequired:
        output_auth_error()
    except APIError as e:
        output_error(e.error, e.message)
    return {}  # unreachable — output_error/output_auth_error raise SystemExit


def _run(
    fetch_fn: Callable[[TruvClient], dict],
    *,
    table_columns: list[str] | None = None,
    table_title: str | None = None,
    table_key: str | None = None,
    format_row: Callable[[dict], dict] | None = None,
) -> None:
    """Fetch data and output according to the active format (table/json/csv)."""
    data = _fetch(fetch_fn)
    fmt = current_format()

    if fmt == OutputFormat.JSON or not table_columns:
        output_json(data)
        return

    rows = data
    if table_key and isinstance(data, dict):
        rows = data.get(table_key, [])
    if not isinstance(rows, list):
        # Unexpected shape: stay in the advertised format instead of silently emitting JSON on stdout.
        if fmt == OutputFormat.CSV:
            output_csv([], table_columns)
        else:
            output_json(data)
        return
    if format_row:
        rows = [format_row(r) for r in rows]
    output_table(rows, table_columns, title=table_title)


@click.command("balances")
@output_option
def balances_cmd() -> None:
    """Show aggregated balances across all accounts.

    Groups balances by account type (CHECKING, SAVINGS, CREDIT_CARD, etc.)
    and currency. Includes total account count.

    Returns JSON: {"total_accounts": int, "accounts": [...], "aggregated_balances": [...]}
    """
    _run(
        lambda c: c.get_balances(),
        table_columns=["type", "currency", "balance", "available", "accounts"],
        table_title="Aggregated Balances",
        table_key="aggregated_balances",
        format_row=lambda r: {
            "type": r.get("type", ""),
            "currency": r.get("currency_code", ""),
            "balance": _fmt_dollar(r.get("balance")),
            "available": _fmt_dollar(r.get("available_balance")),
            "accounts": r.get("account_count", ""),
        },
    )


@click.command("liabilities")
@output_option
def liabilities_cmd() -> None:
    """Show aggregated liabilities across all accounts.

    Includes credit cards and loans with current balances and credit limits.

    Returns JSON: {"accounts": [...], "liabilities": {"credit": [...], "loans": [...]}}
    """
    data = _fetch(lambda c: c.get_liabilities())
    fmt = current_format()

    if fmt == OutputFormat.JSON:
        output_json(data)
        return

    columns = ["account", "balance", "available"]
    accounts = data.get("accounts", [])
    if not accounts:
        if fmt == OutputFormat.CSV:
            output_csv([], columns)
        else:
            output_json(data)
        return

    rows = [
        {
            "account": f"{a.get('type', '')} ···{a.get('mask', '')}",
            "balance": _fmt_dollar((a.get("balances") or {}).get("balance")),
            "available": _fmt_dollar((a.get("balances") or {}).get("available_balance")),
        }
        for a in accounts
    ]
    output_table(rows, columns, title="Liabilities")


@click.command("transactions")
@click.option(
    "--from",
    "from_date",
    default=None,
    help="Start date (YYYY-MM-DD). Defaults to 7 days ago.",
)
@click.option(
    "--to",
    "to_date",
    default=None,
    help="End date (YYYY-MM-DD). Defaults to today.",
)
@click.option(
    "--categories",
    default=None,
    help="Comma-separated category filter. Example: 'Income,Transfer'",
)
@click.option("--page", type=int, default=None, help="Page number (1-based). Omit to fetch all.")
@click.option("--page-size", type=int, default=500, help="Results per page (10-500). Default: 500.")
@output_option
def transactions_cmd(
    from_date: str | None, to_date: str | None, categories: str | None, page: int | None, page_size: int
) -> None:
    """List bank transactions within a date range.

    Defaults to last 7 days. Supports filtering by categories and pagination.

    Returns JSON: {"count": int, "accounts": [...], "transactions": [...]}
    """
    from datetime import UTC, datetime, timedelta

    if not from_date:
        from_date = (datetime.now(tz=UTC) - timedelta(days=7)).strftime("%Y-%m-%d")
    effective_to = to_date or datetime.now(tz=UTC).strftime("%Y-%m-%d")

    data = _fetch(
        lambda c: c.get_transactions(
            from_date=from_date, to_date=to_date, categories=categories, page=page, page_size=page_size
        )
    )

    transactions = data.get("transactions", [])
    total_count = data.get("count", len(transactions))
    truncated = total_count > len(transactions)
    fmt = current_format()

    if fmt == OutputFormat.JSON:
        if truncated and page is None:
            data["truncated"] = True
        output_json(data)
        return

    if truncated and page is None:
        output_warning(
            f"Showing {len(transactions)} of {total_count} transactions. "
            f"Use --page and --page-size to paginate."
        )
    rows = [{**r, "amount": _fmt_dollar(r.get("amount"))} for r in transactions]
    output_table(
        rows,
        ["posted_at", "description", "amount", "type"],
        title=f"Transactions ({from_date} to {effective_to})",
    )


@click.command("spending")
@click.option(
    "--group-by",
    default="category",
    type=click.Choice(["category", "merchant", "time_period"], case_sensitive=False),
    help="Group by. Default: category.",
)
@click.option(
    "--time-period",
    default="month",
    type=click.Choice(["day", "week", "month"], case_sensitive=False),
    help="Time period for aggregation. Default: month.",
)
@click.option(
    "--days",
    type=click.IntRange(min=1),
    default=None,
    help="Number of days to analyze. Default: 30, or 180 when --group-by time_period (to span multiple periods).",
)
@click.option("--start-date", default=None, help="Start date (YYYY-MM-DD). Overrides --days.")
@click.option("--end-date", default=None, help="End date (YYYY-MM-DD). Defaults to today.")
@output_option
def spending_cmd(
    group_by: str, time_period: str, days: int | None, start_date: str | None, end_date: str | None
) -> None:
    """Analyze spending by category, merchant, or period.

    Returns categorized spending breakdown with totals and summaries.
    In table mode, shows summary + top categories or merchants.

    Returns JSON: {"spending": {...}, "summary": {...}, "request_id": "...", "created_at": "..."}
    """
    from datetime import UTC, datetime, timedelta

    if days is None:
        days = 180 if group_by == "time_period" and not start_date else 30

    params: dict[str, str] = {"group_by": group_by, "time_period": time_period}
    if start_date:
        params["start_date"] = start_date
    else:
        params["start_date"] = (datetime.now(tz=UTC) - timedelta(days=days)).strftime("%Y-%m-%d")
    if end_date:
        params["end_date"] = end_date

    effective_end = end_date or datetime.now(tz=UTC).strftime("%Y-%m-%d")

    data = _fetch(lambda c: c.get_spending(**params))
    fmt = current_format()

    if fmt == OutputFormat.JSON:
        output_json(data)
        return

    spending = data.get("spending", {})
    if spending.get("by_category"):
        items, name_fn = spending["by_category"], lambda i: i.get("category", "")
    elif spending.get("by_merchant"):
        items, name_fn = spending["by_merchant"], lambda i: i.get("merchant_name", "")
    elif spending.get("by_time_period"):
        items, name_fn = (
            spending["by_time_period"],
            lambda i: f"{i.get('start_date', '')} → {i.get('end_date', '')}",
        )
    else:
        items, name_fn = [], lambda i: ""

    rows = [
        {
            "name": name_fn(item),
            "amount": _fmt_dollar(item.get("total_amount", item.get("amount"))),
            "transactions": item.get("transaction_count", ""),
            "share": _fmt_pct(item.get("percentage_of_total", item.get("percentage"))),
        }
        for item in items
    ]

    if fmt == OutputFormat.CSV:
        output_csv(rows, ["name", "amount", "transactions", "share"])
        return

    summary = data.get("summary", {})
    period_label = f"{params['start_date']} to {effective_end}"
    output_table(
        [
            {
                "total": _fmt_dollar(summary.get("total_spending")),
                "daily_avg": _fmt_dollar(summary.get("average_daily_spending")),
                "monthly_avg": _fmt_dollar(summary.get("average_monthly_spending")),
                "transactions": summary.get("total_transactions", ""),
            }
        ],
        ["total", "daily_avg", "monthly_avg", "transactions"],
        title=f"Spending Summary ({period_label})",
    )
    if rows:
        output_table(rows[:10], ["name", "amount", "transactions", "share"], title="Breakdown")


@click.command("income")
@click.option("--days", type=int, default=90, help="Number of days to include (1-365). Default: 90.")
@output_option
def income_cmd(days: int) -> None:
    """Show income report from payroll and bank sources.

    Combines income from payroll providers and bank transactions.
    Each employment record includes data_source ('payroll' or 'financial_accounts').
    In table mode, shows the 5 most recent pay statements.

    Returns JSON: {"employments": [...]}
    """
    data = _fetch(lambda c: c.get_income(days=days))
    fmt = current_format()

    if fmt == OutputFormat.JSON:
        output_json(data)
        return

    csv_columns = ["employer", "source", "pay_date", "gross_pay", "net_pay"]
    employments = data.get("employments", [])
    if not employments:
        if fmt == OutputFormat.CSV:
            output_csv([], csv_columns)
        else:
            output_json(data)
        return

    if fmt == OutputFormat.CSV:
        rows = [
            {
                "employer": emp.get("company", {}).get("name", "Unknown"),
                "source": emp.get("data_source", ""),
                "pay_date": s.get("pay_date", ""),
                "gross_pay": _fmt_dollar(s.get("gross_pay")),
                "net_pay": _fmt_dollar(s.get("net_pay")),
            }
            for emp in employments
            for s in emp.get("statements", [])
        ]
        output_csv(rows, csv_columns)
        return

    for emp in employments:
        employer = emp.get("company", {}).get("name", "Unknown")
        source = emp.get("data_source", "")
        income_val = _fmt_dollar(emp.get("income"))
        pay_freq = emp.get("pay_frequency", "")
        output_info(f"\n[bold]{employer}[/bold]  ({source})")
        if income_val or pay_freq:
            output_info(f"  Income: {income_val}  Frequency: {pay_freq}")
        stmts = emp.get("statements", [])[:5]
        if stmts:
            rows = [
                {
                    "pay_date": s.get("pay_date", ""),
                    "gross_pay": _fmt_dollar(s.get("gross_pay")),
                    "net_pay": _fmt_dollar(s.get("net_pay")),
                }
                for s in stmts
            ]
            output_table(rows, ["pay_date", "gross_pay", "net_pay"])


@click.command("recurring")
@output_option
def recurring_cmd() -> None:
    """Detect recurring transactions (subscriptions, etc.).

    Identifies recurring inflows and outflows from connected bank accounts.
    In table mode, shows outflows (expenses) and inflows (income) separately.

    Returns JSON: {"recurring_transactions": {"outflows": [...], "inflows": [...]}}
    """
    data = _fetch(lambda c: c.get_recurring())
    fmt = current_format()

    if fmt == OutputFormat.JSON:
        output_json(data)
        return

    csv_columns = ["direction", "name", "amount", "status", "last", "next"]
    rt = data.get("recurring_transactions", data)
    outflows = rt.get("outflows", [])
    inflows = rt.get("inflows", [])

    if not outflows and not inflows:
        if fmt == OutputFormat.CSV:
            output_csv([], csv_columns)
        else:
            output_json(data)
        return

    def _row(item: dict, direction: str) -> dict:
        return {
            "direction": direction,
            "name": item.get("source_name", ""),
            "amount": _fmt_dollar(item.get("average_amount")),
            "status": item.get("status", ""),
            "last": item.get("last_transaction_date", ""),
            "next": item.get("next_expected_date", ""),
        }

    if fmt == OutputFormat.CSV:
        rows = [_row(o, "outflow") for o in outflows] + [_row(i, "inflow") for i in inflows]
        output_csv(rows, csv_columns)
        return

    if outflows:
        rows = [_row(o, "outflow") for o in outflows]
        output_table(rows, ["name", "amount", "status", "last", "next"], title="Recurring Expenses")
    if inflows:
        rows = [_row(i, "inflow") for i in inflows]
        output_table(rows, ["name", "amount", "status", "last", "next"], title="Recurring Income")


@click.command("balance-history")
@click.option(
    "--date-range",
    default="3M",
    type=click.Choice(["1M", "3M", "6M", "1Y", "ALL"], case_sensitive=False),
    help="Date range. Default: 3M.",
)
@click.option(
    "--time-period",
    default="week",
    type=click.Choice(["day", "week", "month"], case_sensitive=False),
    help="Aggregation period. Default: week.",
)
@output_option
def balance_history_cmd(date_range: str, time_period: str) -> None:
    """Show balance trends over time (assets, net worth).

    Returns time series data points for the specified date range and
    aggregation period.

    Returns JSON: {"time_series": [...], "date_range": "...", "start_date": "...", "end_date": "..."}
    """
    _run(
        lambda c: c.get_balance_history(date_range=date_range, time_period=time_period),
        table_columns=["date", "assets", "liabilities", "net_worth"],
        table_title=f"Balance History ({date_range}, by {time_period})",
        table_key="time_series",
        format_row=lambda r: {
            "date": r.get("date", ""),
            "assets": _fmt_dollar(r.get("assets")),
            "liabilities": _fmt_dollar(r.get("liabilities")),
            "net_worth": _fmt_dollar(r.get("net_worth")),
        },
    )
