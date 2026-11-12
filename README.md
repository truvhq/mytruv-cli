# money

Command-line interface for accessing your [Money by Checkr](https://checkrmoney.com) financial data.

Authenticate with your Money by Checkr account via browser-based OAuth and query balances, transactions, income, spending, and more, all from the terminal.

## Install

```bash
curl -fsSL https://raw.githubusercontent.com/truvhq/checkrmoney-cli/master/scripts/install.sh | sh
```

To install to a custom location, pass `INSTALL_DIR` to the piped shell:

```bash
curl -fsSL https://raw.githubusercontent.com/truvhq/checkrmoney-cli/master/scripts/install.sh | INSTALL_DIR=/usr/local/bin sh
```

Or with [uv](https://docs.astral.sh/uv/):

```bash
uv tool install git+https://github.com/truvhq/checkrmoney-cli.git
```

Installs to `~/.local/bin` by default. Linux binaries need glibc 2.35+ (Ubuntu 22.04, Debian 12, RHEL 9). The binary is a self-extracting bundle that unpacks to `~/.cache/nuitka-onefile/` on first run; set `NUITKA_ONEFILE_TEMPDIR` to override if `$HOME` is read-only.

To uninstall:

```bash
rm "$(command -v money)"
```

### Upgrading from `mytruv`

The CLI used to be called `mytruv`. Run the install command above: it installs `money` and, if an old `mytruv` binary sits in the same folder, replaces it with a link to the new one so existing scripts keep working. You stay signed in, because an existing `~/.config/mytruv` folder is still used. If you installed the Gemini extension, reinstall it from the new repository.

## Quick Start

```bash
money auth login          # authenticate via browser
money links               # list connected accounts
money balances            # check balances
money transactions        # pull recent transactions
money auth logout         # log out
```

## Commands

### Authentication

| Command | Description |
|---|---|
| `money auth login` | Authenticate via browser-based OAuth |
| `money auth login --no-browser` | Print login URL (for headless/remote machines) |
| `money auth logout` | Log out and revoke tokens |
| `money auth status` | Show current authentication status |

### Financial Data

| Command | Description |
|---|---|
| `money user` | Show your user profile |
| `money links` | List connected bank accounts and payroll providers |
| `money balances` | Aggregated balances by account type |
| `money liabilities` | Aggregated liabilities (credit cards, loans) |
| `money transactions` | Bank transactions (supports `--from`, `--to`, `--categories`, `--page`) |
| `money spending` | Spending analysis (supports `--group-by`, `--days`, `--time-period`, `--start-date`, `--end-date`) |
| `money income` | Income report from payroll and bank sources (supports `--days`) |
| `money recurring` | Recurring transactions (subscriptions, deposits) |
| `money balance-history` | Balance trends over time (supports `--date-range`, `--time-period`) |

### Shell Completion

| Command | Description |
|---|---|
| `money completion bash` | Print bash completion script |
| `money completion zsh` | Print zsh completion script |
| `money completion fish` | Print fish completion script |

Add to your shell config:

```bash
# bash (~/.bashrc)
source <(money completion bash)

# zsh (~/.zshrc)
source <(money completion zsh)

# fish (~/.config/fish/config.fish)
money completion fish | source
```

### MCP Server

| Command | Description |
|---|---|
| `money mcp` | Start MCP stdio server for AI agent integration |

### Global Options

| Option | Description |
|---|---|
| `--version` | Show version |
| `--help` | Show help |

## Environment Variables

| Variable | Description |
|---|---|
| `CHECKRMONEY_CONFIG_DIR` | Override the config directory (default: `~/.config/checkrmoney`, or `~/.config/mytruv` if that already exists). `MYTRUV_CONFIG_DIR` is still honored. |

## Agent / Automation Usage

money is designed to be used by AI agents and scripts:

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
{"error": "auth_required", "message": "Not authenticated. Run 'money auth login' first."}
```

### Examples

```bash
# Parse balances with jq
money balances | jq '.aggregated_balances[] | select(.type == "CHECKING")'

# Get transaction count
money transactions | jq '.count'

# Check if authenticated (exit code 0 = yes)
money auth status | jq -e '.authenticated' > /dev/null 2>&1 && echo "logged in"

# Use in a script
if ! money auth status | jq -e '.authenticated' > /dev/null 2>&1; then
    echo "Please run: money auth login"
    exit 1
fi
```

### Interactive vs Piped

```bash
money balances                      # TTY: table on stderr, stdout empty
money balances --json               # JSON on stdout, even in a TTY
money balances --output csv         # CSV on stdout
money balances | cat                # piped: JSON on stdout (auto-detected)
money balances > balances.json      # persist JSON to a file
```

## Gemini CLI Extension

money works as a [Gemini CLI](https://github.com/google-gemini/gemini-cli) extension, giving Gemini access to your financial data through the MCP protocol.

Install the `money` CLI first (see [Install](#install)) so it's on your `$PATH`, then:

```bash
gemini extensions install https://github.com/truvhq/checkrmoney-cli
```

## How Authentication Works

`money auth login` opens your browser for secure OAuth login. Tokens refresh automatically, no need to re-login unless your session fully expires.

## Requirements

- Python 3.10+
- A Money by Checkr account with at least one connected financial account

## License

MIT
