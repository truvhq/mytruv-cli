import os
import sys
import tempfile
from pathlib import Path

try:
    import fcntl
except ImportError:
    fcntl = None  # type: ignore[assignment]

import tomllib

import tomli_w

from mytruv_cli.config.constants import DEFAULT_SERVER_URL


def config_dir() -> Path:
    return Path(os.environ.get("MYTRUV_CONFIG_DIR", Path.home() / ".config" / "mytruv"))


def config_path() -> Path:
    return config_dir() / "config.toml"


def _ensure_dir() -> None:
    d = config_dir()
    d.mkdir(parents=True, exist_ok=True)
    if sys.platform != "win32":
        os.chmod(d, 0o700)


def load_config() -> dict:
    try:
        with open(config_path(), "rb") as f:
            return tomllib.load(f)
    except FileNotFoundError:
        return {}


def save_config(cfg: dict) -> None:
    _ensure_dir()
    path = config_path()
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as f:
            if fcntl is not None:
                fcntl.flock(f, fcntl.LOCK_EX)
            tomli_w.dump(cfg, f)
        if sys.platform != "win32":
            os.chmod(tmp, 0o600)
        os.replace(tmp, path)
    except BaseException:
        os.unlink(tmp)
        raise


def get_client_credentials() -> tuple[str, str] | None:
    cfg = load_config()
    client = cfg.get("client")
    if client and client.get("client_id") and client.get("client_secret"):
        return (client["client_id"], client["client_secret"])
    return None


def set_client_credentials(client_id: str, client_secret: str) -> None:
    cfg = load_config()
    cfg["client"] = {"client_id": client_id, "client_secret": client_secret}
    save_config(cfg)


def clear_client_credentials() -> None:
    cfg = load_config()
    cfg.pop("client", None)
    save_config(cfg)


def get_tokens() -> tuple[str, str, int] | None:
    """Returns (access_token, refresh_token, expires_at) or None."""
    cfg = load_config()
    tokens = cfg.get("tokens")
    if tokens and tokens.get("access_token") and tokens.get("refresh_token"):
        return (tokens["access_token"], tokens["refresh_token"], tokens.get("expires_at", 0))
    return None


def set_tokens(access_token: str, refresh_token: str, expires_at: int) -> None:
    cfg = load_config()
    cfg["tokens"] = {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expires_at": expires_at,
    }
    save_config(cfg)


def clear_tokens() -> None:
    cfg = load_config()
    cfg.pop("tokens", None)
    save_config(cfg)


def get_server_url() -> str:
    if url := os.environ.get("MYTRUV_SERVER_URL", "").strip():
        return url
    cfg = load_config()
    return cfg.get("server_url", DEFAULT_SERVER_URL)
