"""Tests for the insights command."""

import json
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from mytruv_cli.main import cli


@pytest.fixture(autouse=True)
def _isolated_config(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MYTRUV_CONFIG_DIR", str(tmp_path))


def _mock_client(return_value: dict) -> MagicMock:
    mock = MagicMock()
    mock.get_insights.return_value = return_value
    mock.__enter__ = MagicMock(return_value=mock)
    mock.__exit__ = MagicMock(return_value=False)
    return mock


@patch("mytruv_cli.commands.insights.TruvClient")
def test_insights_json_when_completed(mock_cls: MagicMock, runner: CliRunner) -> None:
    mock_cls.return_value = _mock_client(
        {"status": "completed", "insights": "# Summary\nYou saved $200 this month."}
    )
    result = runner.invoke(cli, ["insights", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["status"] == "completed"
    assert "saved $200" in data["insights"]


@patch("mytruv_cli.commands.insights.TruvClient")
def test_insights_json_when_in_progress(mock_cls: MagicMock, runner: CliRunner) -> None:
    mock_cls.return_value = _mock_client({"status": "in_progress", "insights": None})
    result = runner.invoke(cli, ["insights", "--json"])
    assert result.exit_code == 0
    assert json.loads(result.stdout)["status"] == "in_progress"


@patch("mytruv_cli.commands.insights.TruvClient")
def test_insights_not_started_exits_zero_in_tty(mock_cls: MagicMock, runner: CliRunner) -> None:
    mock_cls.return_value = _mock_client({"status": "not_started", "insights": None})
    # Without --json the command takes the table path; it should still exit 0.
    result = runner.invoke(cli, ["insights", "--json"])
    assert result.exit_code == 0


def test_insights_rejects_csv(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["insights", "--output", "csv"])
    assert result.exit_code != 0
    payload = json.loads(result.stdout)
    assert payload["error"] == "csv_unsupported"
