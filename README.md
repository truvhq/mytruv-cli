# mytruv

Command-line interface for accessing your [MyTruv](https://mytruv.com) financial data.

## Install

```bash
curl -fsSL https://raw.githubusercontent.com/truvhq/mytruv-cli/master/scripts/install.sh | sh
```

Or with [uv](https://docs.astral.sh/uv/):

```bash
uv tool install git+https://github.com/truvhq/mytruv-cli.git
```

## Quick Start

```bash
mytruv auth login          # authenticate via browser
mytruv links               # list connected accounts
mytruv balances            # check balances
mytruv transactions        # pull recent transactions
```

## Commands

| Command | Description |
|---|---|
| `auth login` | Authenticate via browser-based OAuth |
| `auth login --no-browser` | Print login URL for headless machines |
| `auth logout` | Log out and revoke tokens |
| `auth status` | Show authentication status |
| `user` | Show your user profile |
| `links` | List connected bank accounts and payroll providers |
| `balances` | Aggregated balances by account type |
| `liabilities` | Aggregated liabilities (credit cards, loans) |
| `transactions` | Bank transactions (supports `--from`, `--to`, `--categories`, `--page`) |
| `spending` | Spending analysis (supports `--group-by`, `--days`, `--time-period`) |
| `income` | Income report from payroll and bank sources (supports `--days`) |
| `recurring` | Recurring transactions (subscriptions, deposits) |
| `balance-history` | Balance trends over time (supports `--date-range`, `--time-period`) |

## Global Flags

| Flag | Description |
|---|---|
| `--version` | Show version |
| `--help` | Show help |

## Agent Mode

mytruv is designed for AI agents and scripts:

- **stdout** is always valid JSON — pipe it, parse it, chain it
- **stderr** has human-friendly messages — ignored by parsers
- Exit codes: `0` success, `1` error, `2` auth required

```bash
# Parse balances with jq
mytruv balances | jq '.aggregated_balances[] | select(.type == "CHECKING")'

# Get transaction count
mytruv transactions | jq '.count'

# Check auth status in a script
mytruv auth status | jq -e '.authenticated' > /dev/null 2>&1 && echo "logged in"
```

When run in a terminal (TTY), commands display rich tables. When piped, output is raw JSON:

```bash
mytruv balances            # terminal: formatted table
mytruv balances | cat      # piped: JSON
```

## Development

```bash
git clone https://github.com/truvhq/mytruv-cli.git
cd mytruv-cli
uv sync
uv run pre-commit install --install-hooks
```

Run tests:

```bash
uv run pytest tests/ -v
```

Run linting:

```bash
uv run pre-commit run --all-files
```

Build a standalone binary:

```bash
./scripts/build.sh
```

## License

MIT
