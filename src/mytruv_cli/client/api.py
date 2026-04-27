import httpx

from mytruv_cli import __version__
from mytruv_cli.auth.oauth import refresh_tokens
from mytruv_cli.auth.store import get_valid_token, needs_refresh
from mytruv_cli.config.settings import get_server_url, get_tokens


class AuthRequired(Exception):
    """Raised when the user is not authenticated."""

    def __init__(self) -> None:
        super().__init__("Not authenticated. Run 'mytruv auth login' first.")


class APIError(Exception):
    """Raised when the API returns a non-success response."""

    def __init__(self, status_code: int, error: str, message: str) -> None:
        self.status_code = status_code
        self.error = error
        self.message = message
        super().__init__(message)


class NetworkError(Exception):
    """Raised when the API is unreachable (DNS, timeout, connection refused, etc.)."""

    def __init__(self, message: str) -> None:
        super().__init__(message)


_DATE_RANGE_MAP = {"1M": "1_month", "3M": "3_months", "6M": "6_months", "1Y": "1_year", "ALL": "all"}


def _build_transactions_params(
    *,
    from_date: str,
    to_date: str | None,
    categories: str | None,
    transaction_type: str | None,
    account_ids: str | None,
    min_amount: str | None,
    max_amount: str | None,
    merchant: str | None,
    sort_by: str,
    sort_order: str,
) -> dict[str, str | int]:
    """Shared query-param builder for /v2/users/transactions and its /export sibling."""
    params: dict[str, str | int] = {
        "transacted_at_from": from_date,
        "sort_by": sort_by,
        "sort_order": sort_order,
    }
    if to_date:
        params["transacted_at_to"] = to_date
    if categories:
        params["categories"] = categories
    if transaction_type:
        params["transaction_type"] = transaction_type.upper()
    if account_ids:
        params["account_ids"] = account_ids
    if min_amount is not None:
        params["min_amount"] = min_amount
    if max_amount is not None:
        params["max_amount"] = max_amount
    if merchant:
        params["merchant"] = merchant
    return params


class TruvClient:
    def __init__(self) -> None:
        self._server_url = get_server_url()
        self._client = httpx.Client(
            base_url=self._server_url,
            timeout=30.0,
            headers={"User-Agent": f"mytruv/{__version__}"},
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def _get_access_token(self) -> str:
        """Get a valid access token, refreshing if needed."""
        if needs_refresh():
            new_token = refresh_tokens(self._server_url)
            if new_token:
                return new_token

        token = get_valid_token()
        if token:
            return token

        tokens = get_tokens()
        if tokens:
            new_token = refresh_tokens(self._server_url)
            if new_token:
                return new_token

        raise AuthRequired

    def _send(self, method: str, path: str, token: str, **kwargs: object) -> httpx.Response:
        try:
            return self._client.request(
                method,
                path,
                headers={"Authorization": f"Bearer {token}"},
                **kwargs,
            )
        except httpx.RequestError as e:
            raise NetworkError(f"Network error: {e}") from e

    def _request(self, method: str, path: str, **kwargs: object) -> dict | bytes:
        """Make an authenticated API request. Returns JSON dict or raw bytes for CSV."""
        token = self._get_access_token()
        resp = self._send(method, path, token, **kwargs)

        if resp.status_code == 401:
            new_token = refresh_tokens(self._server_url)
            if new_token:
                resp = self._send(method, path, new_token, **kwargs)

        if resp.status_code == 401:
            raise AuthRequired

        if resp.status_code >= 400:
            error = "api_error"
            message = resp.text
            try:
                body = resp.json()
                message = body.get("detail", body.get("message", resp.text))
                error = body.get("error", f"http_{resp.status_code}")
            except Exception:
                pass
            raise APIError(resp.status_code, error, message)

        content_type = resp.headers.get("content-type", "").lower()
        if content_type.startswith("text/csv"):
            return resp.content
        return resp.json()

    # ── User ──

    def get_user(self) -> dict:
        return self._request("GET", "/v1/user")

    # ── Links ──

    def get_links(self) -> dict:
        return self._request("GET", "/v1/links")

    # ── Financial data (v2) ──

    def get_balances(self) -> dict:
        return self._request("GET", "/v2/links/balances")

    def get_liabilities(self) -> dict:
        return self._request("GET", "/v2/links/liabilities")

    def get_transactions(
        self,
        *,
        from_date: str,
        to_date: str | None = None,
        categories: str | None = None,
        transaction_type: str | None = None,
        account_ids: str | None = None,
        min_amount: str | None = None,
        max_amount: str | None = None,
        merchant: str | None = None,
        sort_by: str = "date",
        sort_order: str = "desc",
        page: int | None = None,
        page_size: int = 500,
    ) -> dict:
        params = _build_transactions_params(
            from_date=from_date,
            to_date=to_date,
            categories=categories,
            transaction_type=transaction_type,
            account_ids=account_ids,
            min_amount=min_amount,
            max_amount=max_amount,
            merchant=merchant,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        params["page_size"] = page_size
        if page is not None:
            params["page"] = page
        return self._request("GET", "/v2/users/transactions", params=params)

    def export_transactions_csv(
        self,
        *,
        from_date: str,
        to_date: str | None = None,
        categories: str | None = None,
        transaction_type: str | None = None,
        account_ids: str | None = None,
        min_amount: str | None = None,
        max_amount: str | None = None,
        merchant: str | None = None,
        sort_by: str = "date",
        sort_order: str = "desc",
    ) -> bytes:
        params = _build_transactions_params(
            from_date=from_date,
            to_date=to_date,
            categories=categories,
            transaction_type=transaction_type,
            account_ids=account_ids,
            min_amount=min_amount,
            max_amount=max_amount,
            merchant=merchant,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        return self._request("GET", "/v2/users/transactions/export", params=params)

    def get_spending(self, **params: object) -> dict:
        return self._request("GET", "/v2/users/spending", params=params)

    def get_income(self, *, days: int = 90) -> dict:
        # Income endpoint has no v2 counterpart; stay on v1.
        return self._request("GET", "/v1/users/income", params={"days": days})

    def get_recurring(self, *, status: str = "active") -> dict:
        return self._request("GET", "/v2/users/recurring-transactions", params={"status": status})

    def get_balance_history(
        self,
        *,
        date_range: str = "3M",
        time_period: str = "week",
    ) -> dict:
        return self._request(
            "GET",
            "/v2/users/balance-history",
            params={
                "date_range": _DATE_RANGE_MAP.get(date_range.upper(), date_range),
                "time_period": time_period,
            },
        )

    def get_link_report(self, link_id: str) -> dict:
        return self._request("GET", f"/v1/links/{link_id}/report")

    def get_insights(self) -> dict:
        return self._request("GET", "/v2/user/insights")
