from collections.abc import Callable

import click

from mytruv_cli.client.api import APIError, AuthRequired, NetworkError, TruvClient
from mytruv_cli.output.formatter import (
    OutputFormat,
    output_auth_error,
    output_csv,
    output_csv_unsupported,
    output_error,
    output_info,
    output_json,
    output_network_error,
    output_option,
    output_raw_csv,
    output_table,
    resolved_format,
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


def _fetch(fetch_fn: Callable[[TruvClient], object]) -> object:
    """Create client, call fetch_fn, handle auth/network/API errors. Returns data or exits."""
    try:
        with TruvClient() as client:
            return fetch_fn(client)
    except AuthRequired:
        output_auth_error()
    except NetworkError as e:
        output_network_error(e.message)
    except APIError as e:
        output_error(e.error, e.message)
    return {}  # unreachable — the helpers above raise SystemExit


def _run(
    fetch_fn: Callable[[TruvClient], dict],
    *,
    table_columns: list[str] | None = None,
    table_title: str | None = None,
    table_key: str | None = None,
    format_row: Callable[[dict], dict] | None = None,
    csv_columns: list[str] | None = None,
) -> None:
    """Fetch data and output in the resolved format.

    CSV emits raw (unformatted) row values using `csv_columns`. Commands that
    can't express their output as one flat table must omit `csv_columns`, which
    makes --output csv exit with csv_unsupported.
    """
    fmt = resolved_format()
    if fmt == OutputFormat.CSV and csv_columns is None:
        output_csv_unsupported()

    data = _fetch(fetch_fn)

    if fmt == OutputFormat.JSON:
        output_json(data)
        return

    rows: object = data
    if table_key and isinstance(data, dict):
        rows = data.get(table_key, [])

    if fmt == OutputFormat.CSV:
        if not isinstance(rows, list):
            output_csv_unsupported()
        output_csv(rows, csv_columns or [])
        return

    if not isinstance(rows, list):
        output_json(data)
        return

    if format_row:
        rows = [format_row(r) for r in rows]

    output_table(rows, table_columns or [], title=table_title)


@click.command("balances")
@output_option
def balances_cmd() -> None:
    """Show aggregated balances across all accounts.

    Groups balances by account type (CHECKING, SAVINGS, CREDIT_CARD, etc.)
    and currency. Includes total account count.

    Returns JSON: {"total_accounts": int, "accounts": [...], "aggregated_balances": [...]}
    """
    _run(
        lambda c: c.get_balances_v2(),
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
        csv_columns=["type", "currency_code", "balance", "available_balance", "account_count"],
    )


@click.command("liabilities")
@output_option
def liabilities_cmd() -> None:
    """Show aggregated liabilities across all accounts.

    Includes credit cards and loans with current balances and credit limits.

    Returns JSON: {"accounts": [...], "liabilities": {"credit": [...], "loans": [...]}}
    """
    fmt = resolved_format()
    if fmt == OutputFormat.CSV:
        output_csv_unsupported()

    data = _fetch(lambda c: c.get_liabilities_v2())

    if fmt == OutputFormat.JSON:
        output_json(data)
        return

    accounts = data.get("accounts", [])
    rows = [
        {
            "account": f"{a.get('type', '')} ···{a.get('mask', '')}",
            "balance": _fmt_dollar((a.get("balances") or {}).get("balance")),
            "available": _fmt_dollar((a.get("balances") or {}).get("available_balance")),
        }
        for a in accounts
    ]
    if rows:
        output_table(rows, ["account", "balance", "available"], title="Liabilities")
    else:
        output_json(data)


@click.command("transactions")
@click.option("--from", "from_date", default=None, help="Start date (YYYY-MM-DD). Defaults to 7 days ago.")
@click.option("--to", "to_date", default=None, help="End date (YYYY-MM-DD). Defaults to today.")
@click.option(
    "--sort",
    "sort_by",
    default="date",
    type=click.Choice(["date", "amount"], case_sensitive=False),
    help="Sort field. Default: date.",
)
@click.option(
    "--order",
    "sort_order",
    default="desc",
    type=click.Choice(["asc", "desc"], case_sensitive=False),
    help="Sort direction. Default: desc.",
)
@click.option(
    "--type",
    "transaction_type",
    default=None,
    type=click.Choice(["debit", "credit"], case_sensitive=False),
    help="Filter by transaction type.",
)
@click.option("--account", "account_ids", default=None, help="Comma-separated account IDs.")
@click.option("--categories", default=None, help="Comma-separated category names. Example: 'Income,Transfer'")
@click.option("--min-amount", type=float, default=None, help="Minimum absolute amount.")
@click.option("--max-amount", type=float, default=None, help="Maximum absolute amount.")
@click.option("--merchant", default=None, help="Filter by merchant name (substring match).")
@click.option("--page", type=int, default=None, help="Page number (1-based). Omit to fetch all.")
@click.option("--page-size", type=int, default=500, help="Results per page (10-500). Default: 500.")
@output_option
def transactions_cmd(
    from_date: str | None,
    to_date: str | None,
    sort_by: str,
    sort_order: str,
    transaction_type: str | None,
    account_ids: str | None,
    categories: str | None,
    min_amount: float | None,
    max_amount: float | None,
    merchant: str | None,
    page: int | None,
    page_size: int,
) -> None:
    """List bank transactions with rich filtering.

    Defaults to the last 7 days. Supports sorting, account/category/merchant
    filters, amount ranges, and pagination.

    Returns JSON: {"count": int, "accounts": [...], "transactions": [...]}
    """
    from datetime import UTC, datetime, timedelta

    if not from_date:
        from_date = (datetime.now(tz=UTC) - timedelta(days=7)).strftime("%Y-%m-%d")
    effective_to = to_date or datetime.now(tz=UTC).strftime("%Y-%m-%d")

    if resolved_format() == OutputFormat.CSV:
        content = _fetch(
            lambda c: c.export_transactions_csv(
                from_date=from_date,
                to_date=to_date,
                transaction_type=transaction_type,
                account_ids=account_ids,
                categories=categories,
                min_amount=min_amount,
                max_amount=max_amount,
                merchant=merchant,
            )
        )
        output_raw_csv(content)
        return

    _run(
        lambda c: c.get_transactions_v2(
            from_date=from_date,
            to_date=to_date,
            sort_by=sort_by,
            sort_order=sort_order,
            transaction_type=transaction_type,
            account_ids=account_ids,
            categories=categories,
            min_amount=min_amount,
            max_amount=max_amount,
            merchant=merchant,
            page=page,
            page_size=page_size,
        ),
        table_columns=["posted_at", "description", "amount", "type"],
        table_title=f"Transactions ({from_date} to {effective_to})",
        table_key="transactions",
        format_row=lambda r: {**r, "amount": _fmt_dollar(r.get("amount"))},
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
@click.option("--days", type=int, default=30, help="Number of days to analyze. Default: 30.")
@click.option("--start-date", default=None, help="Start date (YYYY-MM-DD). Overrides --days.")
@click.option("--end-date", default=None, help="End date (YYYY-MM-DD). Defaults to today.")
@click.option("--top", "top", type=int, default=10, help="Max breakdown rows shown in table mode. Default: 10.")
@output_option
def spending_cmd(
    group_by: str,
    time_period: str,
    days: int,
    start_date: str | None,
    end_date: str | None,
    top: int,
) -> None:
    """Analyze spending by category, merchant, or period.

    Returns categorized spending breakdown with totals and summaries.
    In table mode, shows summary + top categories or merchants.

    Returns JSON: {"spending": {...}, "summary": {...}, "request_id": "...", "created_at": "..."}
    """
    from datetime import UTC, datetime, timedelta

    # When grouping by time_period with default days, use 90 days so there are multiple buckets
    if group_by == "time_period" and days == 30 and not start_date:
        days = 180

    params: dict[str, str] = {"group_by": group_by, "time_period": time_period}
    if start_date:
        params["start_date"] = start_date
    else:
        params["start_date"] = (datetime.now(tz=UTC) - timedelta(days=days)).strftime("%Y-%m-%d")
    if end_date:
        params["end_date"] = end_date

    effective_end = end_date or datetime.now(tz=UTC).strftime("%Y-%m-%d")

    fmt = resolved_format()
    if fmt == OutputFormat.CSV:
        output_csv_unsupported()

    data = _fetch(lambda c: c.get_spending_v2(**params))

    if fmt == OutputFormat.JSON:
        output_json(data)
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
        items = None
    if items:
        rows = [
            {
                "name": name_fn(item),
                "amount": _fmt_dollar(item.get("total_amount", item.get("amount"))),
                "transactions": item.get("transaction_count", ""),
                "share": _fmt_pct(item.get("percentage_of_total", item.get("percentage"))),
            }
            for item in items[:top]
        ]
        output_table(rows, ["name", "amount", "transactions", "share"], title="Breakdown")


@click.command("income")
@click.option("--days", type=int, default=90, help="Number of days to include (1-365). Default: 90.")
@click.option("--top", "top", type=int, default=5, help="Max recent pay statements shown per employer. Default: 5.")
@output_option
def income_cmd(days: int, top: int) -> None:
    """Show income report from payroll and bank sources.

    Combines income from payroll providers and bank transactions.
    Each employment record includes data_source ('payroll' or 'financial_accounts').

    Returns JSON: {"employments": [...]}
    """
    fmt = resolved_format()
    if fmt == OutputFormat.CSV:
        output_csv_unsupported()

    data = _fetch(lambda c: c.get_income(days=days))

    if fmt == OutputFormat.JSON:
        output_json(data)
        return

    employments = data.get("employments", [])
    if not employments:
        output_json(data)
        return
    for emp in employments:
        employer = emp.get("company", {}).get("name", "Unknown")
        source = emp.get("data_source", "")
        income_val = _fmt_dollar(emp.get("income"))
        pay_freq = emp.get("pay_frequency", "")
        output_info(f"\n[bold]{employer}[/bold]  ({source})")
        if income_val or pay_freq:
            output_info(f"  Income: {income_val}  Frequency: {pay_freq}")
        stmts = emp.get("statements", [])[:top]
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
    fmt = resolved_format()
    if fmt == OutputFormat.CSV:
        output_csv_unsupported()

    data = _fetch(lambda c: c.get_recurring_v2())

    if fmt == OutputFormat.JSON:
        output_json(data)
        return

    rt = data.get("recurring_transactions", data)
    outflows = rt.get("outflows", [])
    inflows = rt.get("inflows", [])
    if outflows:
        rows = [
            {
                "name": o.get("source_name", ""),
                "amount": _fmt_dollar(o.get("average_amount")),
                "status": o.get("status", ""),
                "last": o.get("last_transaction_date", ""),
                "next": o.get("next_expected_date", ""),
            }
            for o in outflows
        ]
        output_table(rows, ["name", "amount", "status", "last", "next"], title="Recurring Expenses")
    if inflows:
        rows = [
            {
                "name": i.get("source_name", ""),
                "amount": _fmt_dollar(i.get("average_amount")),
                "status": i.get("status", ""),
                "last": i.get("last_transaction_date", ""),
                "next": i.get("next_expected_date", ""),
            }
            for i in inflows
        ]
        output_table(rows, ["name", "amount", "status", "last", "next"], title="Recurring Income")
    if not outflows and not inflows:
        output_json(data)


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
        lambda c: c.get_balance_history_v2(date_range=date_range, time_period=time_period),
        table_columns=["date", "assets", "liabilities", "net_worth"],
        table_title=f"Balance History ({date_range}, by {time_period})",
        table_key="time_series",
        format_row=lambda r: {
            "date": r.get("date", ""),
            "assets": _fmt_dollar(r.get("assets")),
            "liabilities": _fmt_dollar(r.get("liabilities")),
            "net_worth": _fmt_dollar(r.get("net_worth")),
        },
        csv_columns=["date", "assets", "liabilities", "net_worth"],
    )
