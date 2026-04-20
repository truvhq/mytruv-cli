# mytruv

Command-line interface for accessing your [MyTruv](https://mytruv.com) financial data.

Authenticate with your MyTruv account via browser-based OAuth and query balances, transactions, income, spending, and more — all from the terminal.

## Install

Download and run the install script:

```bash
curl -fsSL https://raw.githubusercontent.com/truvhq/mytruv-cli/main/scripts/install.sh -o install.sh
sh install.sh
```

Or with [uv](https://docs.astral.sh/uv/):

```bash
uv tool install git+https://github.com/truvhq/mytruv-cli.git
```

The install script supports environment variables for automation:

| Variable | Description |
|---|---|
| `INSTALL_DIR` | Override install location (default: `/usr/local/bin`) |
| `MYTRUV_VERSION` | Pin a specific version (default: latest release) |
| `GITHUB_TOKEN` | Authenticate GitHub API requests to avoid rate limits |

> Checksums verify download integrity (corruption detection). They do not protect against a compromised distribution channel. Review the [install script](scripts/install.sh) before running it.

## Quick Start

```bash
mytruv auth login          # authenticate via browser
mytruv links               # list connected accounts
mytruv balances            # check balances
mytruv transactions        # pull recent transactions
mytruv auth logout         # log out
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
| `mytruv transactions` | Bank transactions (supports `--from`, `--to`, `--categories`, `--page`) |
| `mytruv spending` | Spending analysis (supports `--group-by`, `--days`, `--time-period`, `--start-date`, `--end-date`) |
| `mytruv income` | Income report from payroll and bank sources (supports `--days`) |
| `mytruv recurring` | Recurring transactions (subscriptions, deposits) |
| `mytruv balance-history` | Balance trends over time (supports `--date-range`, `--time-period`) |

### Shell Completion

| Command | Description |
|---|---|
| `mytruv completion bash` | Print bash completion script |
| `mytruv completion zsh` | Print zsh completion script |
| `mytruv completion fish` | Print fish completion script |

Add to your shell config:

```bash
# bash (~/.bashrc)
source <(mytruv completion bash)

# zsh (~/.zshrc)
source <(mytruv completion zsh)

# fish (~/.config/fish/config.fish)
mytruv completion fish | source
```

### Global Options

| Option | Description |
|---|---|
| `--version` | Show version |
| `--help` | Show help |

## Environment Variables

| Variable | Description |
|---|---|
| `MYTRUV_CONFIG_DIR` | Override the config directory (default: `~/.config/mytruv`). |

## Agent / Automation Usage

mytruv is designed to be used by AI agents and scripts:

- **When stdout is not a TTY** (piped, redirected, or with `--agent`): structured JSON on **stdout**. Errors are JSON on stdout; exit code reflects status.
- **When stdout is a TTY**: Rich tables rendered on **stderr**; **stdout is empty**. Pipe the command or pass `--agent` to get parseable output.

Human-facing messages (colors, progress, warnings) always go to **stderr**. Exit codes:

| Code | Meaning |
|---|---|
| `0` | Success |
| `1` | Error (API error, network error, etc.) |
| `2` | Authentication required |

Error format:
```json
{"error": "auth_required", "message": "Not authenticated. Run 'mytruv auth login' first."}
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

```bash
mytruv balances                      # TTY: table on stderr, stdout empty
mytruv balances --agent              # JSON on stdout, even in a TTY
mytruv balances | cat                # piped: JSON on stdout (auto-detected)
mytruv balances > balances.json      # persist JSON to a file
```

## How Authentication Works

`mytruv auth login` opens your browser for secure OAuth login. Tokens refresh automatically — no need to re-login unless your session fully expires.

## Development

```bash
git clone https://github.com/truvhq/mytruv-cli.git
cd mytruv-cli
uv sync --all-extras
uv run pre-commit install --install-hooks
```

Run tests:

```bash
uv run pytest
```

Build a standalone binary:

```bash
./scripts/build.sh
```

## Requirements

- Python 3.10+
- A MyTruv account with at least one connected financial account

## License

MIT
