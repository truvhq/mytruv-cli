"""Tests for the CLI entry point, help text, and command routing."""

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
    assert "0.1.0" in result.output


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
        "completion",
    }
    assert expected == set(cli.commands.keys())


def test_auth_subcommands() -> None:
    from mytruv_cli.commands.auth import auth_group

    expected = {"login", "logout", "status"}
    assert expected == set(auth_group.commands.keys())


def test_completion_bash(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["completion", "bash"])
    assert result.exit_code == 0
    assert "mytruv" in result.output


def test_completion_zsh(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["completion", "zsh"])
    assert result.exit_code == 0
    assert "mytruv" in result.output


def test_completion_fish(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["completion", "fish"])
    assert result.exit_code == 0
    assert "mytruv" in result.output


def test_no_input_flag_sets_agent_mode(runner: CliRunner, monkeypatch) -> None:
    import mytruv_cli.output.formatter as fmt

    monkeypatch.setattr(fmt, "_force_agent", False)
    monkeypatch.setattr(fmt, "_no_input", False)

    result = runner.invoke(cli, ["--no-input", "completion", "bash"])
    assert result.exit_code == 0
    assert fmt._force_agent is True
    assert fmt._no_input is True
