"""Tests for auth store: token validity, refresh detection."""

import time

import pytest

from mytruv_cli.auth.store import clear_auth, get_valid_token, is_authenticated, needs_refresh
from mytruv_cli.config.settings import set_tokens


@pytest.fixture(autouse=True)
def _isolated_config(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MYTRUV_CONFIG_DIR", str(tmp_path))


def test_not_authenticated_when_no_tokens() -> None:
    assert not is_authenticated()
    assert get_valid_token() is None
    assert not needs_refresh()


def test_authenticated_with_valid_token() -> None:
    set_tokens(access_token="tok", refresh_token="ref", expires_at=int(time.time()) + 3600)
    assert is_authenticated()
    assert get_valid_token() == "tok"
    assert not needs_refresh()


def test_needs_refresh_when_expiring_soon() -> None:
    set_tokens(access_token="tok", refresh_token="ref", expires_at=int(time.time()) + 10)
    assert is_authenticated()
    assert get_valid_token() is None  # within 30s buffer
    assert needs_refresh()


def test_expired_token_returns_none() -> None:
    set_tokens(access_token="tok", refresh_token="ref", expires_at=int(time.time()) - 100)
    assert is_authenticated()  # tokens exist
    assert get_valid_token() is None  # but expired


def test_clear_auth() -> None:
    set_tokens(access_token="tok", refresh_token="ref", expires_at=int(time.time()) + 3600)
    assert is_authenticated()
    clear_auth()
    assert not is_authenticated()
