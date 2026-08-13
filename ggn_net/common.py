from __future__ import annotations

import re
from html import unescape
from urllib.parse import urlsplit


def text(value, limit: int = 300) -> str:
    return re.sub(r"\s+", " ", unescape(str(value or ""))).strip()[:limit]


def integer(value, default: int = 0) -> int:
    if isinstance(value, bool):
        return default
    try:
        number = int(str(value).strip())
    except (TypeError, ValueError):
        return default
    return number if number >= 0 else default


def first(mapping: dict, *keys, default=""):
    for key in keys:
        if key in mapping and mapping[key] not in (None, ""):
            return mapping[key]
    return default


def https_url(value: str) -> str:
    raw = text(value, 2000)
    try:
        parts = urlsplit(raw)
    except ValueError:
        return ""
    return raw if parts.scheme == "https" and parts.hostname else ""


def site_url(config: dict, path: str) -> str:
    base = text(config.get("base_url") or "https://gazellegames.net", 300).rstrip("/")
    return f"{base}/{path.lstrip('/')}"


def info_hash(value: str) -> str | None:
    candidate = text(value, 80).lower()
    return candidate if re.fullmatch(r"[0-9a-f]{40}", candidate) else None
