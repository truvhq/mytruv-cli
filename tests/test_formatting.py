"""Tests for output formatting helpers."""

import json
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from mytruv_cli.commands.data import _fmt_dollar, _fmt_pct
from mytruv_cli.main import cli
from mytruv_cli.output import formatter as fmt_mod


@pytest.fixture(autouse=True)
def _reset_formatter_state() -> None:
    fmt_mod.set_format(None)
    fmt_mod.set_no_color(False)
    fmt_mod._agent_deprecation_shown = False  # noqa: SLF001


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
def test_agent_flag_deprecated(mock_cls: MagicMock, runner: CliRunner) -> None:
    mock_cls.return_value = _mock_balances_client()
    result = runner.invoke(cli, ["balances", "--agent"])
    assert result.exit_code == 0
    # stderr is captured in result.stderr; combined in result.output in Click 8.2+.
    assert "deprecated" in result.output.lower()


@patch("mytruv_cli.commands.data.TruvClient")
def test_no_color_flag(mock_cls: MagicMock, runner: CliRunner) -> None:
    mock_cls.return_value = _mock_balances_client()
    result = runner.invoke(cli, ["balances", "--no-color", "--json"])
    assert result.exit_code == 0


def test_output_precedence_over_agent(runner: CliRunner) -> None:
    """--output takes precedence over --agent."""
    with patch("mytruv_cli.commands.data.TruvClient") as mock_cls:
        mock_cls.return_value = _mock_balances_client()
        result = runner.invoke(cli, ["balances", "--output", "csv", "--agent"])
    assert result.exit_code == 0
    assert "type,currency" in result.output
