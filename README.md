# mytruv

Command-line interface for accessing your [MyTruv](https://mytruv.com) financial data.

Authenticate with your MyTruv account via browser-based OAuth and query balances, transactions, income, spending, and more — all from the terminal.

## Install

```bash
# pip
pip install .

# pipx (isolated install)
pipx install .

# uv
uv tool install .
```

After installation, the `mytruv` command is available globally.

You can also run without installing:

```bash
# With uv
cd mytruv-cli && uv run mytruv --help

# With Python directly
python -m mytruv_cli --help
```

## Quick Start

```bash
# 1. Log in (opens browser)
mytruv auth login

# 2. View your accounts
mytruv links

# 3. Check balances
mytruv balances

# 4. Pull recent transactions
mytruv transactions

# 5. Log out
mytruv auth logout
```

## Commands

### Authentication

| Command | Description |
|---|---|
| `mytruv auth login` | Authenticate via browser-based OAuth |
| `mytruv auth login --no-browser` | Print login URL (for headless/remote machines) |
| `mytruv auth logout` | Log out and revoke tokens |
| `mytruv auth status` | Show current authentication status |

### Financial Data

| Command | Description |
|---|---|
| `mytruv user` | Show your user profile |
| `mytruv links` | List connected bank accounts and payroll providers |
| `mytruv balances` | Aggregated balances by account type |
| `mytruv liabilities` | Aggregated liabilities (credit cards, loans) |
| `mytruv transactions` | Bank transactions with filters (`--from`, `--to`, `--sort`, `--order`, `--type`, `--account`, `--categories`, `--min-amount`, `--max-amount`, `--merchant`, `--page`, `--page-size`). `--output csv` streams from the server-side export endpoint. |
| `mytruv spending` | Spending analysis (`--group-by`, `--days`, `--time-period`, `--start-date`, `--end-date`, `--top`) |
| `mytruv income` | Income report from payroll and bank sources (`--days`, `--top`) |
| `mytruv recurring` | Recurring transactions (subscriptions, deposits) |
| `mytruv balance-history` | Balance trends over time (`--date-range`, `--time-period`) |
| `mytruv subscription` | Show the active subscription, if any |
| `mytruv insights` | AI-generated insights about your finances |

### Global Options

| Option | Description |
|---|---|
| `--version` | Show version |
| `--help` | Show help |

### Per-command Output Options

Every data command accepts:

| Option | Description |
|---|---|
| `--output table\|json\|csv`, `-o` | Override the output format. Defaults to `table` in a TTY, `json` when piped. |
| `--json` | Shorthand for `--output json`. |
| `--no-color` | Disable colored output. |

CSV output emits raw (unformatted) values and is supported on single-table commands (`balances`, `transactions`, `balance-history`, `links`, `user`). Commands that render multiple tables (`spending`, `income`, `recurring`, `liabilities`) exit with `csv_unsupported` — use `--output json` instead.

### Aliases

| Alias | Command |
|---|---|
| `tx` | `transactions` |
| `bal` | `balances` |
| `hist` | `balance-history` |
| `rec` | `recurring` |
| `sub` | `subscription` |

## Agent / Automation Usage

mytruv is designed to be used by AI agents and scripts:

- **stdout** is machine-readable: valid JSON by default, or valid CSV with `--output csv`
- **stderr** has human-friendly messages (colors, tables) — ignored by parsers
- **Errors** are structured JSON on stdout with meaningful exit codes:

```
Exit 0 — success
Exit 1 — error (API error, network error, etc.)
Exit 2 — authentication required
```

Error format:
```json
{"error": "auth_required", "message": "Not authenticated.", "hint": "Run 'mytruv auth login' first."}
```

### Examples

```bash
# Parse balances with jq
mytruv balances | jq '.aggregated_balances[] | select(.type == "CHECKING")'

# Get transaction count
mytruv transactions | jq '.count'

# Check if authenticated (exit code 0 = yes)
mytruv auth status | jq -e '.authenticated' > /dev/null 2>&1 && echo "logged in"

# Use in a script
if ! mytruv auth status | jq -e '.authenticated' > /dev/null 2>&1; then
    echo "Please run: mytruv auth login"
    exit 1
fi
```

### Interactive vs Piped

When run in a terminal (TTY), commands display rich tables. When piped, output is raw JSON:

```bash
# Terminal: shows a formatted table
mytruv balances

# Piped: outputs JSON
mytruv balances | cat
mytruv balances > balances.json
```

## How Authentication Works

`mytruv auth login` opens your browser for secure OAuth login. Tokens refresh automatically — no need to re-login unless your session fully expires.

## Requirements

- Python 3.13+
- A MyTruv account with at least one connected financial account
