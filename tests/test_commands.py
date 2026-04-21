"""Tests for CLI commands with mocked API client."""

import json
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from mytruv_cli.main import cli


@pytest.fixture(autouse=True)
def _isolated_config(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MYTRUV_CONFIG_DIR", str(tmp_path))


def _mock_client(method: str, return_value: dict) -> MagicMock:
    """Create a mock TruvClient that works as a context manager."""
    mock = MagicMock()
    getattr(mock, method).return_value = return_value
    mock.__enter__ = MagicMock(return_value=mock)
    mock.__exit__ = MagicMock(return_value=False)
    return mock


def _mock_client_error(method: str, error: Exception) -> MagicMock:
    """Create a mock TruvClient that raises on the given method."""
    mock = MagicMock()
    getattr(mock, method).side_effect = error
    mock.__enter__ = MagicMock(return_value=mock)
    mock.__exit__ = MagicMock(return_value=False)
    return mock


# -- Auth commands --


def test_auth_status_not_authenticated(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["auth", "status"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["authenticated"] is False


def test_auth_logout_when_not_authenticated(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["auth", "logout", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["status"] == "logged_out"


# -- Data commands (mocked client) --


@patch("mytruv_cli.commands.data.TruvClient")
def test_balances_json(mock_cls: MagicMock, runner: CliRunner) -> None:
    mock_cls.return_value = _mock_client(
        "get_balances",
        {
            "total_accounts": 2,
            "aggregated_balances": [
                {
                    "type": "CHECKING",
                    "currency_code": "USD",
                    "balance": "1000.00",
                    "available_balance": "900.00",
                    "account_count": 1,
                },
            ],
        },
    )

    result = runner.invoke(cli, ["balances", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["total_accounts"] == 2
    assert data["aggregated_balances"][0]["type"] == "CHECKING"


@patch("mytruv_cli.commands.data.TruvClient")
def test_transactions_json(mock_cls: MagicMock, runner: CliRunner) -> None:
    mock_cls.return_value = _mock_client(
        "get_transactions",
        {
            "count": 1,
            "transactions": [
                {
                    "posted_at": "2025-03-01",
                    "description": "Coffee",
                    "amount": "-5.50",
                    "type": "DEBIT",
                    "status": "POSTED",
                },
            ],
        },
    )

    result = runner.invoke(cli, ["transactions", "--from", "2025-01-01", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["count"] == 1
    assert data["transactions"][0]["description"] == "Coffee"


@patch("mytruv_cli.commands.data.TruvClient")
def test_spending_json(mock_cls: MagicMock, runner: CliRunner) -> None:
    mock_cls.return_value = _mock_client(
        "get_spending",
        {
            "spending": {
                "by_category": [
                    {
                        "category": "Food",
                        "total_amount": "500.00",
                        "transaction_count": 20,
                        "percentage_of_total": "33.3",
                    }
                ]
            },
            "summary": {
                "total_spending": "1500.00",
                "average_daily_spending": "50.00",
                "average_monthly_spending": "1500.00",
                "total_transactions": 60,
            },
        },
    )

    result = runner.invoke(cli, ["spending", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["summary"]["total_spending"] == "1500.00"


@pytest.mark.parametrize("days_arg", ["0", "-1", "-30"])
def test_spending_days_invalid(days_arg: str, runner: CliRunner) -> None:
    result = runner.invoke(cli, ["spending", "--days", days_arg, "--json"])
    assert result.exit_code != 0
    assert "invalid" in result.output.lower() or "error" in result.output.lower()


@patch("mytruv_cli.commands.data.TruvClient")
def test_spending_days_default_time_period(mock_cls: MagicMock, runner: CliRunner) -> None:
    mock = _mock_client("get_spending", {"spending": {}, "summary": {}})
    mock_cls.return_value = mock
    runner.invoke(cli, ["spending", "--group-by", "time_period", "--json"])
    call_kwargs = mock.get_spending.call_args.kwargs
    expected = (datetime.now(tz=UTC) - timedelta(days=180)).strftime("%Y-%m-%d")
    assert call_kwargs["start_date"] == expected


@patch("mytruv_cli.commands.data.TruvClient")
def test_spending_days_default_other_group_by(mock_cls: MagicMock, runner: CliRunner) -> None:
    mock = _mock_client("get_spending", {"spending": {}, "summary": {}})
    mock_cls.return_value = mock
    runner.invoke(cli, ["spending", "--group-by", "category", "--json"])
    call_kwargs = mock.get_spending.call_args.kwargs
    expected = (datetime.now(tz=UTC) - timedelta(days=30)).strftime("%Y-%m-%d")
    assert call_kwargs["start_date"] == expected


@patch("mytruv_cli.commands.data.TruvClient")
def test_spending_days_explicit_overrides_time_period_default(mock_cls: MagicMock, runner: CliRunner) -> None:
    mock = _mock_client("get_spending", {"spending": {}, "summary": {}})
    mock_cls.return_value = mock
    runner.invoke(cli, ["spending", "--group-by", "time_period", "--days", "30", "--json"])
    call_kwargs = mock.get_spending.call_args.kwargs
    expected = (datetime.now(tz=UTC) - timedelta(days=30)).strftime("%Y-%m-%d")
    assert call_kwargs["start_date"] == expected


@patch("mytruv_cli.commands.data.TruvClient")
def test_income_json(mock_cls: MagicMock, runner: CliRunner) -> None:
    mock_cls.return_value = _mock_client(
        "get_income",
        {
            "employments": [
                {
                    "company": {"name": "Acme"},
                    "data_source": "payroll",
                    "income": "85000",
                    "pay_frequency": "annual",
                    "statements": [{"pay_date": "2025-03-15", "gross_pay": "3269.23", "net_pay": "2450.00"}],
                }
            ],
        },
    )

    result = runner.invoke(cli, ["income", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["employments"][0]["company"]["name"] == "Acme"


@patch("mytruv_cli.commands.data.TruvClient")
def test_recurring_json(mock_cls: MagicMock, runner: CliRunner) -> None:
    mock_cls.return_value = _mock_client(
        "get_recurring",
        {
            "recurring_transactions": {
                "outflows": [
                    {"source_name": "Netflix", "average_amount": "15.99", "frequency": "MONTHLY", "status": "active"}
                ],
                "inflows": [
                    {
                        "source_name": "Acme Corp",
                        "average_amount": "3200.00",
                        "frequency": "BIWEEKLY",
                        "status": "active",
                    }
                ],
            },
        },
    )

    result = runner.invoke(cli, ["recurring", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["recurring_transactions"]["outflows"][0]["source_name"] == "Netflix"


@patch("mytruv_cli.commands.data.TruvClient")
def test_balance_history_json(mock_cls: MagicMock, runner: CliRunner) -> None:
    mock_cls.return_value = _mock_client(
        "get_balance_history",
        {
            "time_series": [
                {"date": "2025-03-01", "assets": "50000.00", "liabilities": "10000.00", "net_worth": "40000.00"}
            ],
            "date_range": "3M",
            "start_date": "2025-01-01",
            "end_date": "2025-03-31",
        },
    )

    result = runner.invoke(cli, ["balance-history", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["time_series"][0]["net_worth"] == "40000.00"


# -- User and links --


@patch("mytruv_cli.commands.user.TruvClient")
def test_user_json(mock_cls: MagicMock, runner: CliRunner) -> None:
    mock_cls.return_value = _mock_client(
        "get_user",
        {
            "first_name": "Jane",
            "last_name": "Doe",
            "email": "jane@example.com",
            "phone": "+1234567890",
        },
    )

    result = runner.invoke(cli, ["user", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["email"] == "jane@example.com"


@patch("mytruv_cli.commands.links.TruvClient")
def test_links_json(mock_cls: MagicMock, runner: CliRunner) -> None:
    mock_cls.return_value = _mock_client(
        "get_links",
        {
            "results": [
                {
                    "id": "abc123",
                    "provider": {"name": "Chase"},
                    "provider_id": "chase",
                    "status": "done",
                    "data_source": "financial_accounts",
                },
            ],
            "count": 1,
        },
    )

    result = runner.invoke(cli, ["links", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["results"][0]["provider"]["name"] == "Chase"


# -- Error handling --


@patch("mytruv_cli.commands.data.TruvClient")
def test_auth_required_error(mock_cls: MagicMock, runner: CliRunner) -> None:
    from mytruv_cli.client.api import AuthRequired

    mock_cls.return_value = _mock_client_error("get_balances", AuthRequired())

    result = runner.invoke(cli, ["balances", "--json"])
    assert result.exit_code == 2
    data = json.loads(result.output)
    assert data["error"] == "auth_required"


@patch("mytruv_cli.commands.data.TruvClient")
def test_api_error(mock_cls: MagicMock, runner: CliRunner) -> None:
    from mytruv_cli.client.api import APIError

    mock_cls.return_value = _mock_client_error("get_balances", APIError(404, "not_found", "No data found"))

    result = runner.invoke(cli, ["balances", "--json"])
    assert result.exit_code == 1
    data = json.loads(result.output)
    assert data["error"] == "not_found"
    assert data["message"] == "No data found"


@patch("mytruv_cli.commands.data.TruvClient")
def test_network_error(mock_cls: MagicMock, runner: CliRunner) -> None:
    from mytruv_cli.client.api import NetworkError

    mock_cls.return_value = _mock_client_error("get_balances", NetworkError("Network error: connection refused"))

    result = runner.invoke(cli, ["balances", "--json"])
    assert result.exit_code == 1
    data = json.loads(result.output)
    assert data["error"] == "network_error"
    assert "connection refused" in data["message"]


# -- Transactions v2 filters --


@patch("mytruv_cli.commands.data.TruvClient")
def test_transactions_passes_v2_filters(mock_cls: MagicMock, runner: CliRunner) -> None:
    mock = _mock_client("get_transactions", {"count": 0, "transactions": []})
    mock_cls.return_value = mock

    result = runner.invoke(
        cli,
        [
            "transactions",
            "--from",
            "2026-01-01",
            "--type",
            "debit",
            "--min-amount",
            "10",
            "--merchant",
            "Amazon",
            "--sort",
            "amount",
            "--order",
            "asc",
            "--json",
        ],
    )
    assert result.exit_code == 0, result.output
    kwargs = mock.get_transactions.call_args.kwargs
    assert kwargs["transaction_type"] == "debit"
    assert kwargs["min_amount"] == "10"
    assert kwargs["merchant"] == "Amazon"
    assert kwargs["sort_by"] == "amount"
    assert kwargs["sort_order"] == "asc"


@patch("mytruv_cli.commands.data.TruvClient")
def test_transactions_csv_streams_server_export(mock_cls: MagicMock, runner: CliRunner) -> None:
    mock = MagicMock()
    mock.export_transactions_csv.return_value = b"date,amount\n2026-01-01,-5.50\n"
    mock.__enter__ = MagicMock(return_value=mock)
    mock.__exit__ = MagicMock(return_value=False)
    mock_cls.return_value = mock

    result = runner.invoke(cli, ["transactions", "--from", "2026-01-01", "--output", "csv"])
    assert result.exit_code == 0, result.output
    assert result.output.startswith("date,amount")
    # Ensure we called the export, not the list endpoint
    mock.export_transactions_csv.assert_called_once()
    mock.get_transactions.assert_not_called()


@patch("mytruv_cli.commands.data.TruvClient")
def test_transactions_categories_legacy_alias(mock_cls: MagicMock, runner: CliRunner) -> None:
    mock = _mock_client("get_transactions", {"count": 0, "transactions": []})
    mock_cls.return_value = mock

    result = runner.invoke(cli, ["transactions", "--from", "2026-01-01", "--categories", "Food,Transfer", "--json"])
    assert result.exit_code == 0, result.output
    assert mock.get_transactions.call_args.kwargs["categories"] == "Food,Transfer"


# -- Subscription --


@patch("mytruv_cli.commands.subscription.TruvClient")
def test_subscription_active(mock_cls: MagicMock, runner: CliRunner) -> None:
    mock_cls.return_value = _mock_client(
        "get_subscription",
        {
            "name": "Pro",
            "price": 999,
            "currency": "usd",
            "interval": "month",
            "is_trial": False,
            "current_period_end": 1735689600,
        },
    )

    result = runner.invoke(cli, ["subscription", "--json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["active"] is True
    assert data["subscription"]["name"] == "Pro"


@patch("mytruv_cli.commands.subscription.TruvClient")
def test_subscription_inactive(mock_cls: MagicMock, runner: CliRunner) -> None:
    mock_cls.return_value = _mock_client("get_subscription", None)

    result = runner.invoke(cli, ["subscription", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["active"] is False
    assert data["subscription"] is None


# -- Insights --


@patch("mytruv_cli.commands.insights.TruvClient")
def test_insights_in_progress_exits_zero(mock_cls: MagicMock, runner: CliRunner) -> None:
    mock_cls.return_value = _mock_client("get_insights", {"status": "in_progress", "insights": []})

    result = runner.invoke(cli, ["insights", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["status"] == "in_progress"


@patch("mytruv_cli.commands.insights.TruvClient")
def test_insights_completed(mock_cls: MagicMock, runner: CliRunner) -> None:
    mock_cls.return_value = _mock_client(
        "get_insights",
        {
            "status": "completed",
            "insights": [
                {
                    "id": "i1",
                    "category": "expenses",
                    "priority": "high",
                    "title": "Subscription creep",
                    "summary": "You added three subscriptions this month.",
                    "detail": "Full detail...",
                    "follow_up": "Review recurring charges",
                }
            ],
        },
    )

    result = runner.invoke(cli, ["insights", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["status"] == "completed"
    assert data["insights"][0]["title"] == "Subscription creep"


# -- Write commands (PR 4) --


@patch("mytruv_cli.commands.refresh.TruvClient")
def test_refresh_all_links_sends_no_body(mock_cls: MagicMock, runner: CliRunner) -> None:
    mock_cls.return_value = _mock_client(
        "refresh_data",
        {"refreshed_links": [{"link_id": "L1", "task_id": "T1", "provider_name": "Chase"}], "skipped_count": 2},
    )

    result = runner.invoke(cli, ["refresh", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["skipped_count"] == 2
    mock_cls.return_value.refresh_data.assert_called_once_with(None)


@patch("mytruv_cli.commands.refresh.TruvClient")
def test_refresh_with_link_ids_sends_list(mock_cls: MagicMock, runner: CliRunner) -> None:
    mock_cls.return_value = _mock_client(
        "refresh_data",
        {"refreshed_links": [], "skipped_count": 0},
    )

    result = runner.invoke(cli, ["refresh", "--link-id", "L1", "--link-id", "L2", "--json"])
    assert result.exit_code == 0
    mock_cls.return_value.refresh_data.assert_called_once_with(["L1", "L2"])


@patch("mytruv_cli.commands.links.TruvClient")
def test_disconnect_requires_confirmation(mock_cls: MagicMock, runner: CliRunner) -> None:
    """Without --yes, declining the prompt aborts and never calls delete_link."""
    mock_cls.return_value = _mock_client("delete_link", {})

    result = runner.invoke(cli, ["links", "disconnect", "L1"], input="n\n")
    assert result.exit_code != 0
    mock_cls.return_value.delete_link.assert_not_called()


@patch("mytruv_cli.commands.links.TruvClient")
def test_disconnect_yes_skips_prompt(mock_cls: MagicMock, runner: CliRunner) -> None:
    mock_cls.return_value = _mock_client("delete_link", {})

    result = runner.invoke(cli, ["links", "disconnect", "L1", "--yes", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data == {"link_id": "L1", "disconnected": True}
    mock_cls.return_value.delete_link.assert_called_once_with("L1")


@patch("mytruv_cli.commands.links.TruvClient")
def test_disconnect_handles_204(mock_cls: MagicMock, runner: CliRunner) -> None:
    """Backend passthrough may return {} on 204; should not traceback."""
    mock_cls.return_value = _mock_client("delete_link", {})

    result = runner.invoke(cli, ["links", "disconnect", "L1", "--yes", "--json"])
    assert result.exit_code == 0


@patch("mytruv_cli.commands.links.TruvClient")
def test_links_report_always_json(mock_cls: MagicMock, runner: CliRunner) -> None:
    report_body = {"link_id": "L1", "accounts": [{"id": "A1", "balance": "100.00"}]}
    mock_cls.return_value = _mock_client("get_link_report", report_body)

    # Even without --json on a non-TTY test runner, we want the raw JSON body.
    result = runner.invoke(cli, ["links", "report", "L1"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data == report_body


@patch("mytruv_cli.commands.links.TruvClient")
def test_bare_links_still_lists(mock_cls: MagicMock, runner: CliRunner) -> None:
    """Group promotion must not break `mytruv links` as a plain list command."""
    mock_cls.return_value = _mock_client(
        "get_links",
        {
            "results": [
                {"id": "L1", "provider": {"name": "Chase"}, "status": "done", "data_source": "financial_accounts"}
            ]
        },
    )

    result = runner.invoke(cli, ["links", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["results"][0]["id"] == "L1"
    mock_cls.return_value.get_links.assert_called_once()
