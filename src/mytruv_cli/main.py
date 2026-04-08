import difflib

import click

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


@click.group(cls=_AliasGroup, context_settings={"max_content_width": 120})
@click.version_option(package_name="mytruv")
def cli() -> None:
    """mytruv — Access your financial data from the command line.

    Authenticate with your MyTruv account and query balances, transactions,
    income, spending, and more. Output is JSON when piped or with --agent,
    and tables when run in an interactive terminal.

    \b
    Get started:
        mytruv auth login
        mytruv balances
        mytruv transactions --from 2025-01-01

    \b
    Agent mode (always JSON on stdout, exit code > 0 on error):
        mytruv balances --agent
        mytruv transactions --from 2025-01-01 --agent
    """


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
