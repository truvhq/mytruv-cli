import os
import time

from mytruv_cli.config.settings import clear_client_credentials, clear_tokens, get_tokens

_EXPIRY_BUFFER = 30  # refresh 30s before actual expiry


def is_authenticated() -> bool:
    return bool(os.environ.get("MYTRUV_TOKEN", "").strip()) or get_tokens() is not None


def get_valid_token() -> str | None:
    """Return access_token if it exists and is not expired (with buffer). Else None."""
    if token := os.environ.get("MYTRUV_TOKEN", "").strip():
        return token
    tokens = get_tokens()
    if not tokens:
        return None
    access_token, _, expires_at = tokens
    if expires_at and time.time() >= expires_at - _EXPIRY_BUFFER:
        return None
    return access_token


def needs_refresh() -> bool:
    """True if tokens exist but access_token is expiring within the buffer."""
    tokens = get_tokens()
    if not tokens:
        return False
    _, _, expires_at = tokens
    return bool(expires_at and time.time() >= expires_at - _EXPIRY_BUFFER)


def clear_auth() -> None:
    clear_tokens()
    clear_client_credentials()
