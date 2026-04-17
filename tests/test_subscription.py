"""Tests for the subscription command."""

import json
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from mytruv_cli.main import cli


@pytest.fixture(autouse=True)
def _isolated_config(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MYTRUV_CONFIG_DIR", str(tmp_path))


def _mock_client(return_value: object) -> MagicMock:
    mock = MagicMock()
    mock.get_subscription.return_value = return_value
    mock.__enter__ = MagicMock(return_value=mock)
    mock.__exit__ = MagicMock(return_value=False)
    return mock


@patch("mytruv_cli.commands.subscription.TruvClient")
def test_subscription_json(mock_cls: MagicMock, runner: CliRunner) -> None:
    mock_cls.return_value = _mock_client(
        {
            "plan": {"name": "Pro", "price_amount": "9.99", "currency": "USD", "interval": "month"},
            "status": "active",
            "current_period_start": "2026-04-01",
            "current_period_end": "2026-05-01",
            "trial_end": None,
        }
    )
    result = runner.invoke(cli, ["subscription", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["plan"]["name"] == "Pro"
    assert data["status"] == "active"


@patch("mytruv_cli.commands.subscription.TruvClient")
def test_subscription_none_exits_zero(mock_cls: MagicMock, runner: CliRunner) -> None:
    mock_cls.return_value = _mock_client(None)
    result = runner.invoke(cli, ["subscription", "--json"])
    assert result.exit_code == 0
    assert json.loads(result.stdout) is None


@patch("mytruv_cli.commands.subscription.TruvClient")
def test_subscription_alias_sub(mock_cls: MagicMock, runner: CliRunner) -> None:
    mock_cls.return_value = _mock_client(None)
    result = runner.invoke(cli, ["sub", "--json"])
    assert result.exit_code == 0


def test_subscription_rejects_csv(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["subscription", "--output", "csv"])
    assert result.exit_code != 0
    payload = json.loads(result.stdout)
    assert payload["error"] == "csv_unsupported"
