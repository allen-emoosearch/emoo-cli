"""Configuration read/write for ~/.emoo/config.json."""

import json
import os
from pathlib import Path
from typing import Optional


CONFIG_DIR = Path.home() / ".emoo"
CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULT_BASE_URL = "https://app.emooai.com/open-api/v1"


def _ensure_dir() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def load() -> dict:
    """Load config, returning empty dict if not exists."""
    if CONFIG_FILE.exists():
        return json.loads(CONFIG_FILE.read_text())
    return {}


def save(data: dict) -> None:
    _ensure_dir()
    CONFIG_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False))


def get(key: str, default=None):
    return load().get(key, default)


def set_(key: str, value) -> None:
    data = load()
    data[key] = value
    save(data)


def get_base_url() -> str:
    return load().get("base_url", DEFAULT_BASE_URL)


def get_token() -> Optional[str]:
    return load().get("access_token")


def get_client_credentials() -> tuple[Optional[str], Optional[str]]:
    cfg = load()
    return cfg.get("client_id"), cfg.get("client_secret")


def get_default_user_id() -> Optional[str]:
    return load().get("default_user_id")


def get_api_key() -> Optional[str]:
    return load().get("api_key")


def is_api_key_auth() -> bool:
    return bool(load().get("api_key"))
