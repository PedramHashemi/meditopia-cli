"""
Manages ~/.meditopia/config.json — stores token and API URL.
"""

import json
from pathlib import Path

CONFIG_DIR = Path.home() / ".meditopia"
CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULT_API_URL = "http://localhost:8000/api/v1"


def load() -> dict:
    if CONFIG_FILE.exists():
        return json.loads(CONFIG_FILE.read_text())
    return {}


def save(data: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(data, indent=2))


def get_token() -> str | None:
    return load().get("token")


def get_api_url() -> str:
    return load().get("api_url", DEFAULT_API_URL)


def set_credentials(token: str, api_url: str = DEFAULT_API_URL) -> None:
    cfg = load()
    cfg["token"] = token
    cfg["api_url"] = api_url
    save(cfg)


def clear() -> None:
    if CONFIG_FILE.exists():
        CONFIG_FILE.unlink()
