import difflib

import click
from click.shell_completion import BashComplete, FishComplete, ZshComplete

from mytruv_cli import __version__
from mytruv_cli.commands.auth import auth_group
from mytruv_cli.commands.data import (
    balance_history_cmd,
    balances_cmd,
    income_cmd,
    liabilities_cmd,
    recurring_cmd,
    spending_cmd,
    transactions_cmd,
)
from mytruv_cli.commands.links import links_cmd
from mytruv_cli.commands.user import user_cmd


class _AliasGroup(click.Group):
    def resolve_command(self, ctx: click.Context, args: list[str]) -> tuple:
        cmd_name = args[0] if args else None
        if cmd_name and cmd_name not in self.commands:
            matches = difflib.get_close_matches(cmd_name, self.commands.keys(), n=3, cutoff=0.5)
            if matches:
                hint = ", ".join(f"'{m}'" for m in matches)
                self.fail(f"Unknown command '{cmd_name}'. Did you mean: {hint}?", ctx=ctx)
            else:
                commands = ", ".join(sorted(self.commands.keys()))
                self.fail(f"Unknown command '{cmd_name}'. Available commands: {commands}", ctx=ctx)
        return super().resolve_command(ctx, args)

    @staticmethod
    def fail(message: str, ctx: click.Context) -> None:
        raise click.UsageError(message, ctx=ctx)


@click.group(cls=_AliasGroup, context_settings={"max_content_width": 120, "help_option_names": ["-h", "--help"]})
@click.version_option(version=__version__, package_name="mytruv")
def cli() -> None:
    """mytruv — Access your financial data from the command line.

    Authenticate with your MyTruv account and query balances, transactions,
    income, spending, and more. Output is a table in an interactive terminal,
    and JSON when piped. Use --output json|csv or --json to force a format.

    \b
    Get started:
        mytruv auth login
        mytruv balances
        mytruv transactions --from 2025-01-01

    \b
    Scripting (always JSON on stdout, exit code > 0 on error):
        mytruv balances --json
        mytruv transactions --from 2025-01-01 --output csv
    """


@click.command("completion")
@click.argument("shell", type=click.Choice(["bash", "zsh", "fish"]))
@click.pass_context
def completion_cmd(ctx: click.Context, shell: str) -> None:
    """Print shell completion script for SHELL.

    \b
    Quick install:
        bash:  echo 'source <(mytruv completion bash)' >> ~/.bashrc
        zsh:   echo 'source <(mytruv completion zsh)' >> ~/.zshrc
        fish:  mytruv completion fish > ~/.config/fish/completions/mytruv.fish
    """
    prog = ctx.find_root().info_name
    complete_var = f"_{prog.upper().replace('-', '_')}_COMPLETE"
    classes = {"bash": BashComplete, "zsh": ZshComplete, "fish": FishComplete}
    click.echo(classes[shell](cli, {}, prog, complete_var).source())


@cli.command("mcp")
def mcp_cmd() -> None:
    """Start MCP stdio server for AI agent integration."""
    from mytruv_cli.mcp_server import run_server

    run_server()


cli.add_command(auth_group)
cli.add_command(user_cmd)
cli.add_command(links_cmd)
cli.add_command(balances_cmd)
cli.add_command(liabilities_cmd)
cli.add_command(transactions_cmd)
cli.add_command(spending_cmd)
cli.add_command(income_cmd)
cli.add_command(recurring_cmd)
cli.add_command(balance_history_cmd)
cli.add_command(completion_cmd)


if __name__ == "__main__":
    cli()
