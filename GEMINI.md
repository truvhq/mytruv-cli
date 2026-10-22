# mytruv — Gemini CLI extension

Personal finance data from [MyTruv](https://mytruv.com): balances, transactions, income, spending, and recurring charges for the authenticated user. All tools are read-only.

## Authentication

The first call opens a browser for OAuth login. If any tool returns `{"error": "auth_required", ...}`, call `authenticate` once and retry the original tool. Tokens are stored locally in `~/.config/mytruv/config.toml` and refresh automatically.

## Which tool to use

| If the user asks about… | Call |
|---|---|
| Current account balances, "how much do I have" | `account_balances` |
| Net worth or balance trends over time | `balance_history` |
| Credit cards, loans, debt | `liabilities` |
| Individual transactions in a date range | `transactions` |
| Aggregated spend by category / merchant / time | `spending_analysis` |
| Income from paychecks and bank deposits | `income_report` |
| Subscriptions, recurring bills | `recurring_transactions` |
| Which banks / payroll providers are connected | `connected_accounts` |
| User is logged out | `authenticate` |

Prefer `spending_analysis` over `transactions` + manual summing when the question is about totals.

## Conventions

- Dates are `YYYY-MM-DD` strings. If the user says "last month" or "this week", convert to explicit dates before calling.
- When no range is specified, default to the last 30 days for `transactions` and `spending_analysis`.
- Money amounts are returned as numbers in USD unless noted.
- Account identifiers returned by `connected_accounts` can be referenced when explaining which institution a balance or transaction came from.

## Privacy

This extension only reads the signed-in user's own financial data via the MyTruv API. Nothing is written, and data isn't shared beyond what Gemini shows the user in the current session.
