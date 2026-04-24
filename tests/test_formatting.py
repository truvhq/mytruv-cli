"""Tests for output formatting helpers."""

import json
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from mytruv_cli.commands.data import _fmt_dollar, _fmt_pct
from mytruv_cli.main import cli


def test_fmt_dollar() -> None:
    assert _fmt_dollar("1234.56") == "$1,234.56"
    assert _fmt_dollar("0") == "$0.00"
    assert _fmt_dollar("1000000") == "$1,000,000.00"


def test_fmt_dollar_none() -> None:
    assert _fmt_dollar(None) == ""
    assert _fmt_dollar("") == ""


def test_fmt_dollar_invalid() -> None:
    assert _fmt_dollar("not_a_number") == "not_a_number"


def test_fmt_pct() -> None:
    assert _fmt_pct("33.3") == "33.3%"
    assert _fmt_pct("100") == "100.0%"
    assert _fmt_pct("0.5") == "0.5%"


def test_fmt_pct_none() -> None:
    assert _fmt_pct(None) == ""
    assert _fmt_pct("") == ""


def test_fmt_pct_invalid() -> None:
    assert _fmt_pct("abc") == "abc"


def _mock_balances_client() -> MagicMock:
    mock = MagicMock()
    mock.get_balances.return_value = {
        "total_accounts": 1,
        "aggregated_balances": [
            {
                "type": "CHECKING",
                "currency_code": "USD",
                "balance": "1000.00",
                "available_balance": "900.00",
                "account_count": 1,
            }
        ],
    }
    mock.__enter__ = MagicMock(return_value=mock)
    mock.__exit__ = MagicMock(return_value=False)
    return mock


@patch("mytruv_cli.commands.data.TruvClient")
def test_output_json_flag(mock_cls: MagicMock, runner: CliRunner) -> None:
    mock_cls.return_value = _mock_balances_client()
    result = runner.invoke(cli, ["balances", "--output", "json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["total_accounts"] == 1


@patch("mytruv_cli.commands.data.TruvClient")
def test_output_csv_flag(mock_cls: MagicMock, runner: CliRunner) -> None:
    mock_cls.return_value = _mock_balances_client()
    result = runner.invoke(cli, ["balances", "--output", "csv"])
    assert result.exit_code == 0
    lines = [line for line in result.output.splitlines() if line.strip()]
    assert lines[0] == "type,currency,balance,available,accounts"
    assert "CHECKING" in lines[1]


@patch("mytruv_cli.commands.data.TruvClient")
def test_json_shorthand(mock_cls: MagicMock, runner: CliRunner) -> None:
    mock_cls.return_value = _mock_balances_client()
    result = runner.invoke(cli, ["balances", "--json"])
    assert result.exit_code == 0
    json.loads(result.output)


@patch("mytruv_cli.commands.data.TruvClient")
def test_no_color_flag(mock_cls: MagicMock, runner: CliRunner) -> None:
    mock_cls.return_value = _mock_balances_client()
    result = runner.invoke(cli, ["balances", "--no-color", "--json"])
    assert result.exit_code == 0


@patch("mytruv_cli.commands.data.TruvClient")
def test_no_color_env(mock_cls: MagicMock, runner: CliRunner, monkeypatch) -> None:
    """NO_COLOR env var must disable ANSI colors without requiring --no-color."""
    monkeypatch.setenv("NO_COLOR", "1")
    from mytruv_cli.output import formatter

    # Re-evaluate console after env change so the test reflects real startup order.
    formatter.set_no_color(False)
    assert formatter._env_no_color() is True

    mock_cls.return_value = _mock_balances_client()
    result = runner.invoke(cli, ["balances", "--json"])
    assert result.exit_code == 0


def test_format_state_does_not_leak_between_invocations(runner: CliRunner) -> None:
    """Each @output_option invocation must reset module state so earlier flags don't persist."""
    with patch("mytruv_cli.commands.data.TruvClient") as mock_cls:
        mock_cls.return_value = _mock_balances_client()
        # First call sets format=CSV.
        csv_result = runner.invoke(cli, ["balances", "--output", "csv"])
        assert csv_result.exit_code == 0
        assert csv_result.output.startswith("type,currency")

        # Second call has no flags — must fall back to auto-detect (non-TTY → JSON),
        # not inherit CSV from the prior invocation.
        default_result = runner.invoke(cli, ["balances"])
        assert default_result.exit_code == 0
        json.loads(default_result.output)  # valid JSON, not CSV


@patch("mytruv_cli.commands.data.TruvClient")
def test_liabilities_csv_empty_stays_csv(mock_cls: MagicMock, runner: CliRunner) -> None:
    """--output csv on an empty result must still emit CSV (header-only), not fall back to JSON."""
    mock = MagicMock()
    mock.get_liabilities.return_value = {"accounts": [], "liabilities": {"credit": [], "loans": []}}
    mock.__enter__ = MagicMock(return_value=mock)
    mock.__exit__ = MagicMock(return_value=False)
    mock_cls.return_value = mock

    result = runner.invoke(cli, ["liabilities", "--output", "csv"])
    assert result.exit_code == 0
    lines = [line for line in result.output.splitlines() if line.strip()]
    assert lines == ["account,balance,available"]


@patch("mytruv_cli.commands.data.TruvClient")
def test_income_csv_empty_stays_csv(mock_cls: MagicMock, runner: CliRunner) -> None:
    mock = MagicMock()
    mock.get_income.return_value = {"employments": []}
    mock.__enter__ = MagicMock(return_value=mock)
    mock.__exit__ = MagicMock(return_value=False)
    mock_cls.return_value = mock

    result = runner.invoke(cli, ["income", "--output", "csv"])
    assert result.exit_code == 0
    lines = [line for line in result.output.splitlines() if line.strip()]
    assert lines == ["employer,source,pay_date,gross_pay,net_pay"]


@patch("mytruv_cli.commands.data.TruvClient")
def test_recurring_csv_empty_stays_csv(mock_cls: MagicMock, runner: CliRunner) -> None:
    mock = MagicMock()
    mock.get_recurring.return_value = {"recurring_transactions": {"outflows": [], "inflows": []}}
    mock.__enter__ = MagicMock(return_value=mock)
    mock.__exit__ = MagicMock(return_value=False)
    mock_cls.return_value = mock

    result = runner.invoke(cli, ["recurring", "--output", "csv"])
    assert result.exit_code == 0
    lines = [line for line in result.output.splitlines() if line.strip()]
    assert lines == ["direction,name,amount,status,last,next"]
