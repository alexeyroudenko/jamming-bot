"""Thread-safe HTTP client with keep-alive for storage-service."""

from __future__ import annotations

import os
import threading
from urllib.parse import quote

import requests

STORAGE_SERVICE_URL = os.getenv("STORAGE_SERVICE_URL", "http://storage_service:7781").rstrip("/")

_lock = threading.Lock()
_session: requests.Session | None = None


def _session_get() -> requests.Session:
    global _session
    if _session is None:
        s = requests.Session()
        s.headers.setdefault("Connection", "keep-alive")
        _session = s
    return _session


def _url(path: str) -> str:
    if not path.startswith("/"):
        path = "/" + path
    return f"{STORAGE_SERVICE_URL}{path}"


def storage_request(method: str, path: str, **kwargs):
    with _lock:
        return _session_get().request(method, _url(path), **kwargs)


def storage_post_store(payload: dict, timeout: float = 30):
    return storage_request("POST", "/store", json=payload, timeout=timeout)


def storage_patch_step(number: str, payload: dict, timeout: float = 12):
    n = quote(str(number), safe="")
    return storage_request("PATCH", f"/update/step/{n}", json=payload, timeout=timeout)


def storage_post_analysis(payload: dict, timeout: float = 5):
    return storage_request("POST", "/analysis/store", json=payload, timeout=timeout)


def storage_post_exists_batch(numbers: list, timeout: float = 60):
    return storage_request("POST", "/exists/batch", json={"numbers": numbers}, timeout=timeout)


def storage_get(path: str, *, timeout: float = 15, params=None, stream: bool = False):
    if not path.startswith("/"):
        path = "/" + path
    return storage_request("GET", path, timeout=timeout, params=params, stream=stream)
