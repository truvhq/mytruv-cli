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
