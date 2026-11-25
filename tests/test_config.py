"""Tests for config settings: read/write tokens, client credentials, server URL."""

import os

import pytest

from money_cli.config.settings import (
    clear_tokens,
    config_dir,
    config_path,
    get_client_credentials,
    get_server_url,
    get_tokens,
    set_client_credentials,
    set_tokens,
)


@pytest.fixture(autouse=True)
def _isolated_config(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CHECKRMONEY_CONFIG_DIR", str(tmp_path))


def test_default_server_url() -> None:
    assert get_server_url() == "https://api.checkrmoney.com"


def test_tokens_roundtrip() -> None:
    assert get_tokens() is None

    set_tokens(access_token="abc", refresh_token="def", expires_at=9999999999)
    tokens = get_tokens()
    assert tokens is not None
    assert tokens == ("abc", "def", 9999999999)


def test_clear_tokens() -> None:
    set_tokens(access_token="abc", refresh_token="def", expires_at=9999999999)
    clear_tokens()
    assert get_tokens() is None


def test_client_credentials_roundtrip() -> None:
    assert get_client_credentials() is None

    set_client_credentials("cid", "csecret")
    creds = get_client_credentials()
    assert creds == ("cid", "csecret")


def test_empty_client_credentials_ignored() -> None:
    set_client_credentials("", "")
    assert get_client_credentials() is None


def test_config_file_permissions(tmp_path) -> None:
    set_tokens(access_token="x", refresh_token="y", expires_at=1)
    path = config_path()
    mode = os.stat(path).st_mode & 0o777
    assert mode == 0o600


def test_custom_server_url(tmp_path) -> None:
    import tomli_w

    cfg_path = config_path()
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    with open(cfg_path, "wb") as f:
        tomli_w.dump({"server_url": "https://custom.example.com"}, f)

    assert get_server_url() == "https://custom.example.com"


class TestConfigDir:
    @pytest.fixture(autouse=True)
    def _home(self, tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("CHECKRMONEY_CONFIG_DIR", raising=False)
        monkeypatch.delenv("MYTRUV_CONFIG_DIR", raising=False)
        monkeypatch.setenv("HOME", str(tmp_path))

    def test_defaults_to_new_folder(self, tmp_path) -> None:
        assert config_dir() == tmp_path / ".config" / "checkrmoney"

    def test_existing_legacy_folder_used_until_new_one_exists(self, tmp_path) -> None:
        (tmp_path / ".config" / "mytruv").mkdir(parents=True)
        assert config_dir() == tmp_path / ".config" / "mytruv"

        (tmp_path / ".config" / "checkrmoney").mkdir(parents=True)
        assert config_dir() == tmp_path / ".config" / "checkrmoney"

    def test_env_override_prefers_new_variable(self, tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("MYTRUV_CONFIG_DIR", str(tmp_path / "old"))
        assert config_dir() == tmp_path / "old"

        monkeypatch.setenv("CHECKRMONEY_CONFIG_DIR", str(tmp_path / "new"))
        assert config_dir() == tmp_path / "new"
