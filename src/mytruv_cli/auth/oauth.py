import base64
import hashlib
import http.server
import secrets
import sys
import threading
import time
import webbrowser
from urllib.parse import parse_qs, urlparse

import httpx

from mytruv_cli.config.constants import CALLBACK_PORT, CLIENT_NAME
from mytruv_cli.config.settings import (
    get_client_credentials,
    get_tokens,
    set_client_credentials,
    set_tokens,
)

_CALLBACK_TIMEOUT = 120  # seconds


class OAuthError(Exception):
    """Raised when the OAuth flow fails."""

    def __init__(self, error: str, message: str) -> None:
        self.error = error
        self.message = message
        super().__init__(message)


class _CallbackHandler(http.server.BaseHTTPRequestHandler):
    """Handles the OAuth callback on localhost."""

    code: str | None = None
    state: str | None = None
    error: str | None = None
    error_description: str | None = None
    received: threading.Event = threading.Event()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)

        _CallbackHandler.error = params.get("error", [None])[0]
        _CallbackHandler.error_description = params.get("error_description", [None])[0]
        _CallbackHandler.code = params.get("code", [None])[0]
        _CallbackHandler.state = params.get("state", [None])[0]
        _CallbackHandler.received.set()

        if _CallbackHandler.error:
            body = _error_html(_CallbackHandler.error_description or _CallbackHandler.error)
        else:
            body = _success_html()

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(body.encode())

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        pass  # suppress server logs


def _html_page(heading: str, body: str, *, color: str = "#16a34a") -> str:
    return f"""<!DOCTYPE html>
<html><head><title>mytruv</title><style>
body{{font-family:system-ui,sans-serif;display:flex;justify-content:center;align-items:center;
min-height:100vh;margin:0;background:#f8f9fa;color:#1a1a2e}}
.card{{text-align:center;padding:3rem;border-radius:12px;background:#fff;box-shadow:0 2px 12px rgba(0,0,0,.08)}}
h1{{color:{color};margin-bottom:.5rem}}
</style></head><body><div class="card">
<h1>{heading}</h1>
<p>{body}</p>
</div></body></html>"""


def _success_html() -> str:
    return _html_page("Authenticated", "You can close this tab and return to the terminal.")


def _error_html(detail: str) -> str:
    return _html_page("Authentication Failed", detail, color="#dc2626")


def _generate_pkce() -> tuple[str, str]:
    """Returns (code_verifier, code_challenge)."""
    verifier = secrets.token_urlsafe(32)
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return verifier, challenge


def _start_callback_server() -> tuple[http.server.HTTPServer, int]:
    """Start a local HTTP server for the OAuth callback. Returns (server, port)."""
    _CallbackHandler.code = None
    _CallbackHandler.state = None
    _CallbackHandler.error = None
    _CallbackHandler.error_description = None
    _CallbackHandler.received = threading.Event()

    for port in [CALLBACK_PORT, 0]:
        try:
            server = http.server.HTTPServer(("127.0.0.1", port), _CallbackHandler)
            actual_port = server.server_address[1]
            return server, actual_port
        except OSError:
            if port == 0:
                raise
            continue

    msg = "Could not start callback server"
    raise OAuthError("server_error", msg)


def register_client(server_url: str, redirect_uri: str) -> tuple[str, str]:
    """Register an OAuth client with the server. Returns (client_id, client_secret)."""
    existing = get_client_credentials()
    if existing:
        return existing

    with httpx.Client(timeout=30) as client:
        resp = client.post(
            f"{server_url}/register",
            json={
                "client_name": CLIENT_NAME,
                "redirect_uris": [redirect_uri],
                "grant_types": ["authorization_code", "refresh_token"],
                "response_types": ["code"],
                "token_endpoint_auth_method": "client_secret_post",
                "scope": "openid profile email",
            },
        )

    if resp.status_code != 201:
        detail = resp.text
        try:
            detail = resp.json().get("error_description", resp.text)
        except Exception:
            pass
        raise OAuthError("registration_failed", f"Client registration failed: {detail}")

    data = resp.json()
    client_id = data["client_id"]
    client_secret = data["client_secret"]
    set_client_credentials(client_id, client_secret)
    return client_id, client_secret


def login(server_url: str, *, no_browser: bool = False) -> dict:
    """Run the full OAuth login flow. Returns the token response dict."""
    server, port = _start_callback_server()
    redirect_uri = f"http://127.0.0.1:{port}/callback"

    try:
        client_id, client_secret = register_client(server_url, redirect_uri)
    except OAuthError:
        set_client_credentials("", "")
        client_id, client_secret = register_client(server_url, redirect_uri)

    code_verifier, code_challenge = _generate_pkce()
    state = secrets.token_urlsafe(16)

    authorize_url = (
        f"{server_url}/authorize"
        f"?response_type=code"
        f"&client_id={client_id}"
        f"&redirect_uri={redirect_uri}"
        f"&code_challenge={code_challenge}"
        f"&code_challenge_method=S256"
        f"&state={state}"
        f"&scope=openid%20profile%20email"
    )

    thread = threading.Thread(target=server.handle_request, daemon=True)
    thread.start()

    if no_browser:
        print(f"Open this URL in your browser:\n\n  {authorize_url}\n", file=sys.stderr)
    else:
        print("Opening browser for authentication...", file=sys.stderr)
        webbrowser.open(authorize_url)

    if not _CallbackHandler.received.wait(timeout=_CALLBACK_TIMEOUT):
        server.server_close()
        raise OAuthError("timeout", f"Authentication timed out after {_CALLBACK_TIMEOUT}s. Run 'mytruv auth login' to try again.")

    server.server_close()

    if _CallbackHandler.error:
        raise OAuthError(
            _CallbackHandler.error,
            _CallbackHandler.error_description or _CallbackHandler.error,
        )

    if not _CallbackHandler.code:
        raise OAuthError("missing_code", "No authorization code received from server.")

    if _CallbackHandler.state != state:
        raise OAuthError("state_mismatch", "OAuth state parameter mismatch. Possible CSRF attack.")

    with httpx.Client(timeout=30) as client:
        resp = client.post(
            f"{server_url}/token",
            data={
                "grant_type": "authorization_code",
                "code": _CallbackHandler.code,
                "redirect_uri": redirect_uri,
                "client_id": client_id,
                "client_secret": client_secret,
                "code_verifier": code_verifier,
            },
        )

    if resp.status_code != 200:
        detail = resp.text
        try:
            detail = resp.json().get("error_description", resp.text)
        except Exception:
            pass
        raise OAuthError("token_exchange_failed", f"Token exchange failed: {detail}")

    token_data = resp.json()
    expires_at = int(time.time()) + token_data.get("expires_in", 3600)
    set_tokens(
        access_token=token_data["access_token"],
        refresh_token=token_data.get("refresh_token", ""),
        expires_at=expires_at,
    )
    return token_data


def refresh_tokens(server_url: str) -> str | None:
    """Refresh the access token. Returns new access_token or None on failure."""
    tokens = get_tokens()
    if not tokens:
        return None

    _, refresh_token, _ = tokens
    if not refresh_token:
        return None

    creds = get_client_credentials()
    if not creds:
        return None

    client_id, client_secret = creds

    with httpx.Client(timeout=30) as client:
        resp = client.post(
            f"{server_url}/token",
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": client_id,
                "client_secret": client_secret,
            },
        )

    if resp.status_code != 200:
        return None

    token_data = resp.json()
    expires_at = int(time.time()) + token_data.get("expires_in", 3600)
    set_tokens(
        access_token=token_data["access_token"],
        refresh_token=token_data.get("refresh_token", refresh_token),
        expires_at=expires_at,
    )
    return token_data["access_token"]


def revoke_token(server_url: str) -> None:
    """Revoke the current tokens on the server (best-effort)."""
    tokens = get_tokens()
    if not tokens:
        return

    access_token, _, _ = tokens
    creds = get_client_credentials()
    if not creds:
        return

    client_id, client_secret = creds

    try:
        with httpx.Client(timeout=10) as client:
            client.post(
                f"{server_url}/revoke",
                data={
                    "token": access_token,
                    "client_id": client_id,
                    "client_secret": client_secret,
                },
            )
    except httpx.HTTPError:
        pass  # best-effort
