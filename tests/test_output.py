"""Tests for the --output / --json / --agent flag behavior."""

import csv
import io
import json
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from mytruv_cli.main import cli
from mytruv_cli.output import formatter


@pytest.fixture(autouse=True)
def _isolated_config(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MYTRUV_CONFIG_DIR", str(tmp_path))


@pytest.fixture(autouse=True)
def _reset_output_state() -> None:
    """Ensure the module-level output-format override doesn't leak between tests."""
    formatter.set_output_format(None)
    yield
    formatter.set_output_format(None)


def _mock_client(method: str, return_value: dict) -> MagicMock:
    mock = MagicMock()
    getattr(mock, method).return_value = return_value
    mock.__enter__ = MagicMock(return_value=mock)
    mock.__exit__ = MagicMock(return_value=False)
    return mock


_BALANCES_PAYLOAD = {
    "total_accounts": 1,
    "aggregated_balances": [
        {
            "type": "CHECKING",
            "currency_code": "USD",
            "balance": "1000.00",
            "available_balance": "900.00",
            "account_count": 1,
        },
    ],
}


@patch("mytruv_cli.commands.data.TruvClient")
def test_output_json_flag_produces_json(mock_cls: MagicMock, runner: CliRunner) -> None:
    mock_cls.return_value = _mock_client("get_balances_v2", _BALANCES_PAYLOAD)
    result = runner.invoke(cli, ["balances", "--output", "json"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["total_accounts"] == 1


@patch("mytruv_cli.commands.data.TruvClient")
def test_json_shorthand_produces_json(mock_cls: MagicMock, runner: CliRunner) -> None:
    mock_cls.return_value = _mock_client("get_balances_v2", _BALANCES_PAYLOAD)
    result = runner.invoke(cli, ["balances", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["total_accounts"] == 1


@patch("mytruv_cli.commands.data.TruvClient")
def test_output_csv_flag_produces_csv(mock_cls: MagicMock, runner: CliRunner) -> None:
    mock_cls.return_value = _mock_client("get_balances_v2", _BALANCES_PAYLOAD)
    result = runner.invoke(cli, ["balances", "--output", "csv"])
    assert result.exit_code == 0
    rows = list(csv.DictReader(io.StringIO(result.stdout)))
    assert len(rows) == 1
    assert rows[0]["type"] == "CHECKING"
    assert rows[0]["currency_code"] == "USD"
    # CSV must emit raw (unformatted) values — not display strings like "$1,000.00".
    assert rows[0]["balance"] == "1000.00"
    assert rows[0]["available_balance"] == "900.00"


@patch("mytruv_cli.commands.data.TruvClient")
def test_transactions_csv_has_raw_amount(mock_cls: MagicMock, runner: CliRunner) -> None:
    mock_cls.return_value = _mock_client(
        "get_transactions_v2",
        {
            "count": 1,
            "transactions": [
                {
                    "posted_at": "2025-01-01",
                    "description": "Coffee",
                    "amount": "-5.00",
                    "type": "DEBIT",
                    "category": "Food",
                }
            ],
        },
    )
    result = runner.invoke(cli, ["transactions", "--from", "2025-01-01", "--output", "csv"])
    assert result.exit_code == 0
    rows = list(csv.DictReader(io.StringIO(result.stdout)))
    assert rows[0]["amount"] == "-5.00"
    assert "$" not in result.stdout


@pytest.mark.parametrize("cmd", ["spending", "income", "recurring", "liabilities"])
def test_multi_table_commands_reject_csv(runner: CliRunner, cmd: str) -> None:
    result = runner.invoke(cli, [cmd, "--output", "csv"])
    assert result.exit_code != 0
    payload = json.loads(result.stdout)
    assert payload["error"] == "csv_unsupported"


@patch("mytruv_cli.commands.data.TruvClient")
def test_agent_flag_still_works_and_warns(mock_cls: MagicMock, runner: CliRunner) -> None:
    mock_cls.return_value = _mock_client("get_balances_v2", _BALANCES_PAYLOAD)
    result = runner.invoke(cli, ["balances", "--agent"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["total_accounts"] == 1
    assert "--agent is deprecated" in result.stderr


@patch("mytruv_cli.commands.data.TruvClient")
def test_output_flag_beats_agent_flag(mock_cls: MagicMock, runner: CliRunner) -> None:
    mock_cls.return_value = _mock_client("get_balances_v2", _BALANCES_PAYLOAD)
    result = runner.invoke(cli, ["balances", "--output", "json", "--agent"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["total_accounts"] == 1


@patch("mytruv_cli.commands.data.TruvClient")
def test_alias_tx_routes_to_transactions(mock_cls: MagicMock, runner: CliRunner) -> None:
    mock_cls.return_value = _mock_client(
        "get_transactions_v2",
        {"count": 0, "transactions": []},
    )
    result = runner.invoke(cli, ["tx", "--from", "2025-01-01", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["count"] == 0
