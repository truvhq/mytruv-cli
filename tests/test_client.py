"""Tests for TruvClient._request() content-type/status/error handling."""

from unittest.mock import MagicMock, patch

import httpx
import pytest

from mytruv_cli.client.api import APIError, NetworkError, TruvClient


@pytest.fixture(autouse=True)
def _isolated_config(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MYTRUV_CONFIG_DIR", str(tmp_path))


def _make_response(
    status_code: int, *, json_body: object = None, content: bytes = b"", content_type: str = ""
) -> MagicMock:
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.content = content if content else (b"" if json_body is None else b"{}")
    resp.text = resp.content.decode("utf-8", errors="replace")
    resp.headers = {"content-type": content_type}
    resp.json.return_value = json_body if json_body is not None else {}
    return resp


def _client_with_token() -> TruvClient:
    client = TruvClient()
    client._get_access_token = MagicMock(return_value="fake-token")  # type: ignore[method-assign]
    return client


def test_request_handles_204_no_content() -> None:
    client = _client_with_token()
    resp = _make_response(204, content=b"", content_type="")
    with patch.object(client._client, "request", return_value=resp):
        result = client._request("DELETE", "/v1/user")
    assert result is None


def test_request_returns_bytes_for_csv_content_type() -> None:
    client = _client_with_token()
    csv_body = b"date,amount\n2025-01-01,10.00\n"
    resp = _make_response(200, content=csv_body, content_type="text/csv; charset=utf-8")
    with patch.object(client._client, "request", return_value=resp):
        result = client._request("GET", "/v2/users/transactions/export")
    assert result == csv_body


def test_request_returns_parsed_json_for_json_content_type() -> None:
    client = _client_with_token()
    resp = _make_response(200, json_body={"ok": True}, content=b'{"ok": true}', content_type="application/json")
    with patch.object(client._client, "request", return_value=resp):
        result = client._request("GET", "/v1/user")
    assert result == {"ok": True}


def test_request_raises_network_error_on_connect_failure() -> None:
    client = _client_with_token()
    with (
        patch.object(client._client, "request", side_effect=httpx.ConnectError("connection refused")),
        pytest.raises(NetworkError) as exc,
    ):
        client._request("GET", "/v1/user")
    assert "connection refused" in str(exc.value)


def test_request_raises_network_error_on_timeout() -> None:
    client = _client_with_token()
    with (
        patch.object(client._client, "request", side_effect=httpx.ConnectTimeout("timed out")),
        pytest.raises(NetworkError),
    ):
        client._request("GET", "/v1/user")


def test_request_raises_api_error_on_4xx() -> None:
    client = _client_with_token()
    resp = _make_response(
        404,
        json_body={"error": "not_found", "detail": "Nope"},
        content=b'{"error": "not_found", "detail": "Nope"}',
        content_type="application/json",
    )
    with patch.object(client._client, "request", return_value=resp), pytest.raises(APIError) as exc:
        client._request("GET", "/v1/user")
    assert exc.value.status_code == 404
    assert exc.value.error == "not_found"
    assert exc.value.message == "Nope"


def test_export_transactions_csv_returns_bytes() -> None:
    client = _client_with_token()
    csv_body = b"posted_at,description,amount\n2025-01-01,Coffee,-5.00\n"
    resp = _make_response(200, content=csv_body, content_type="text/csv; charset=utf-8")
    with patch.object(client._client, "request", return_value=resp) as mock_req:
        result = client.export_transactions_csv(from_date="2025-01-01", categories="Food")
    assert result == csv_body
    _, kwargs = mock_req.call_args
    assert kwargs["params"]["transacted_at_from"] == "2025-01-01"
    assert kwargs["params"]["categories"] == "Food"


def test_get_transactions_v2_builds_filter_params() -> None:
    client = _client_with_token()
    resp = _make_response(
        200,
        json_body={"count": 0, "transactions": []},
        content=b"{}",
        content_type="application/json",
    )
    with patch.object(client._client, "request", return_value=resp) as mock_req:
        client.get_transactions_v2(
            from_date="2025-01-01",
            sort_by="amount",
            sort_order="asc",
            transaction_type="debit",
            min_amount=10.0,
            max_amount=500.0,
            merchant="Starbucks",
        )
    _, kwargs = mock_req.call_args
    params = kwargs["params"]
    assert params["sort_by"] == "amount"
    assert params["sort_order"] == "asc"
    assert params["transaction_type"] == "debit"
    assert params["min_amount"] == 10.0
    assert params["max_amount"] == 500.0
    assert params["merchant"] == "Starbucks"
