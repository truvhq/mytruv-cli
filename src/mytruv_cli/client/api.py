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
    """Raised when the HTTP client cannot reach the server (connection/timeout)."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


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

    def _do_request(self, method: str, path: str, token: str, **kwargs: object) -> httpx.Response:
        """Single HTTP call. Catches connectivity errors and raises NetworkError."""
        try:
            return self._client.request(
                method,
                path,
                headers={"Authorization": f"Bearer {token}"},
                **kwargs,
            )
        except httpx.RequestError as e:
            raise NetworkError(str(e) or e.__class__.__name__) from e

    def _request(self, method: str, path: str, *, raw: bool = False, **kwargs: object) -> dict | list | bytes | None:
        """Authenticated API request with auto-retry on 401.

        Returns:
            - None for 204 No Content
            - bytes for non-JSON bodies (e.g. text/csv) or when raw=True
            - parsed JSON otherwise
        """
        token = self._get_access_token()
        resp = self._do_request(method, path, token, **kwargs)

        if resp.status_code == 401:
            new_token = refresh_tokens(self._server_url)
            if new_token:
                resp = self._do_request(method, path, new_token, **kwargs)

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

        if resp.status_code == 204 or not resp.content:
            return None

        content_type = resp.headers.get("content-type", "").lower()
        if raw or not content_type.startswith("application/json"):
            return resp.content

        return resp.json()

    # ── User ──

    def get_user(self) -> dict:
        return self._request("GET", "/v1/user")

    # ── Links ──

    def get_links(self) -> dict:
        return self._request("GET", "/v1/links")

    # ── Financial data ──

    def get_balances(self) -> dict:
        return self._request("GET", "/v1/links/balances")

    def get_liabilities(self) -> dict:
        return self._request("GET", "/v1/links/liabilities")

    def get_transactions(
        self,
        *,
        from_date: str,
        to_date: str | None = None,
        categories: str | None = None,
        page: int | None = None,
        page_size: int = 500,
    ) -> dict:
        params: dict[str, str | int] = {
            "transacted_at_from": from_date,
            "page_size": page_size,
        }
        if to_date:
            params["transacted_at_to"] = to_date
        if categories:
            params["categories"] = categories
        if page is not None:
            params["page"] = page
        return self._request("GET", "/v1/users/transactions", params=params)

    def get_spending(self, **params: object) -> dict:
        return self._request("GET", "/v1/users/spending", params=params)

    def get_income(self, *, days: int = 90) -> dict:
        return self._request("GET", "/v1/users/income", params={"days": days})

    def get_recurring(self) -> dict:
        return self._request("GET", "/v1/users/recurring-transactions")

    def get_balance_history(
        self,
        *,
        date_range: str = "3M",
        time_period: str = "week",
    ) -> dict:
        return self._request(
            "GET",
            "/v1/users/balance-history",
            params={"date_range": date_range, "time_period": time_period},
        )

    def get_link_report(self, link_id: str) -> dict:
        return self._request("GET", f"/v1/links/{link_id}/report")
