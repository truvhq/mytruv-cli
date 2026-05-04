# mytruv

Command-line interface for accessing your [MyTruv](https://mytruv.com) financial data.

Authenticate with your MyTruv account via browser-based OAuth and query balances, transactions, income, spending, and more — all from the terminal.

## Install


Download and run the install script:

```bash
curl -fsSL https://raw.githubusercontent.com/truvhq/mytruv-cli/master/scripts/install.sh -o install.sh
sh install.sh
```

Or with [uv](https://docs.astral.sh/uv/):

```bash
uv tool install git+https://github.com/truvhq/mytruv-cli.git
```

Installs to `~/.local/bin` by default; override with `INSTALL_DIR=/usr/local/bin`. Linux binaries need glibc 2.35+ (Ubuntu 22.04, Debian 12, RHEL 9). The binary is a self-extracting bundle that unpacks to `~/.cache/nuitka-onefile/` on first run — set `NUITKA_ONEFILE_TEMPDIR` to override if `$HOME` is read-only.

To uninstall:

```bash
rm "$(command -v mytruv)"
```

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

### MCP Server

| Command | Description |
|---|---|
| `mytruv mcp` | Start MCP stdio server for AI agent integration |

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

- **stdout** carries data in the selected format: JSON by default when piped, or CSV with `--output csv`
- **stderr** carries human-friendly messages (colors, tables, warnings) and structured error JSON on failure
- **Exit code** signals success or failure; parse `stderr` for error details

| Code | Meaning |
|---|---|
| `0` | Success |
| `1` | Error (API error, network error, etc.) |
| `2` | Authentication required |

Error format (emitted on **stderr**, never on stdout):
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
mytruv balances --json               # JSON on stdout, even in a TTY
mytruv balances --output csv         # CSV on stdout
mytruv balances | cat                # piped: JSON on stdout (auto-detected)
mytruv balances > balances.json      # persist JSON to a file
```

## Gemini CLI Extension

mytruv works as a [Gemini CLI](https://github.com/google-gemini/gemini-cli) extension, giving Gemini access to your financial data through the MCP protocol.

Install the `mytruv` CLI first (see [Install](#install)) so it's on your `$PATH`, then:

```bash
gemini extensions install https://github.com/truvhq/mytruv-cli
```

## How Authentication Works

`mytruv auth login` opens your browser for secure OAuth login. Tokens refresh automatically — no need to re-login unless your session fully expires.

## Requirements

- Python 3.10+
- A MyTruv account with at least one connected financial account

## License

MIT
