"""Shared HTTP helpers for all web-touching tools."""

import json
import urllib.request
from typing import Any

DEFAULT_UA = "Mozilla/5.0 (compatible; AERA-Agent/1.0)"
TIMEOUT = 10


def http_get(url: str, headers: dict | None = None,
             timeout: int = TIMEOUT) -> str:
    hdrs = {"User-Agent": DEFAULT_UA}
    if headers:
        hdrs.update(headers)
    req = urllib.request.Request(url, headers=hdrs)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", errors="replace")


def http_json(url: str, headers: dict | None = None,
              timeout: int = TIMEOUT) -> Any:
    return json.loads(http_get(url, headers, timeout))
