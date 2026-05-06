"""
HTTP client for the Meditopia API.
"""

from __future__ import annotations

import httpx
from typing import Any

from . import config


def _headers() -> dict[str, str]:
    token = config.get_token()
    if not token:
        raise RuntimeError("Not authenticated. Run: medi login --token <your-token>")
    return {"Authorization": f"Bearer {token}"}


def _base() -> str:
    return config.get_api_url().rstrip("/")


# ── Auth ──────────────────────────────────────────────────────────────────────


def whoami() -> dict[str, Any]:
    r = httpx.get(f"{_base()}/auth/me", headers=_headers(), timeout=10)
    r.raise_for_status()
    return r.json()


# ── Datasets ──────────────────────────────────────────────────────────────────


def create_dataset(payload: dict[str, Any]) -> dict[str, Any]:
    r = httpx.post(f"{_base()}/datasets", json=payload, headers=_headers(), timeout=30)
    r.raise_for_status()
    return r.json()


def upload_dataset_files(
    owner: str, slug: str, file_tuples: list[tuple]
) -> dict[str, Any]:
    """
    file_tuples: list of (filename, file_bytes, content_type)
    """
    files = [("files", (name, data, ct)) for name, data, ct in file_tuples]
    r = httpx.post(
        f"{_base()}/datasets/{owner}/{slug}/upload",
        headers=_headers(),
        files=files,
        timeout=300,
    )
    r.raise_for_status()
    return r.json()


# ── Models ────────────────────────────────────────────────────────────────────


def create_model(payload: dict[str, Any]) -> dict[str, Any]:
    r = httpx.post(f"{_base()}/models", json=payload, headers=_headers(), timeout=30)
    r.raise_for_status()
    return r.json()

def upload_model_files(
    owner: str, slug: str, file_tuples: list[tuple]
) -> dict[str, Any]:
    files = [("files", (name, data, ct)) for name, data, ct in file_tuples]
    r = httpx.post(
        f"{_base()}/models/{owner}/{slug}/upload",
        headers=_headers(),
        files=files,
        timeout=300,
    )
    r.raise_for_status()
    return r.json()
