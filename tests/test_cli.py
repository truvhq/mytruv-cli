"""Tests for the CLI entry point, help text, and command routing."""

import pytest
from click.testing import CliRunner

from mytruv_cli.main import cli


def test_help(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "mytruv" in result.output
    assert "auth" in result.output
    assert "balances" in result.output
    assert "transactions" in result.output


def test_version(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "1.1.0" in result.output


def test_unknown_command_suggests(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["balance"])
    assert result.exit_code != 0
    assert "Did you mean" in result.output
    assert "balances" in result.output


def test_unknown_command_no_match(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["xyz"])
    assert result.exit_code != 0
    assert "Available commands" in result.output


def test_all_commands_registered() -> None:
    expected = {
        "auth",
        "user",
        "links",
        "balances",
        "liabilities",
        "transactions",
        "spending",
        "income",
        "recurring",
        "balance-history",
        "mcp",
        "insights",
        "completion",
    }
    assert expected == set(cli.commands.keys())


@pytest.mark.parametrize(
    ("shell", "marker"),
    [
        ("bash", "complete -o nosort -F"),
        ("zsh", "#compdef mytruv"),
        ("fish", "complete --no-files --command mytruv"),
    ],
)
def test_completion_emits_shell_script(runner: CliRunner, shell: str, marker: str) -> None:
    result = runner.invoke(cli, ["completion", shell], prog_name="mytruv")
    assert result.exit_code == 0
    assert marker in result.output


def test_auth_subcommands() -> None:
    from mytruv_cli.commands.auth import auth_group

    expected = {"login", "logout", "status"}
    assert expected == set(auth_group.commands.keys())
