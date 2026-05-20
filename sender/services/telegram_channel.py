"""Resolve Telegram channel layout from credentials and Bot API (owner Premium)."""

from __future__ import annotations

import logging
import re
from typing import Any

import requests
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

TG_API = "https://api.telegram.org"
_CHAT_ID_NUMERIC = re.compile(r"^-?\d+$")
_OWNER_PREMIUM_CACHE_PREFIX = "sender:tg:owner_premium:"
_OWNER_PREMIUM_CACHE_TTL = 3600


def telegram_chat_id_from_secrets(secrets: dict[str, Any]) -> str:
    """Resolve credential/env values to Bot API ``chat_id``."""
    raw = (
        secrets.get("channel_name")
        or secrets.get("chat_id")
        or getattr(settings, "TELEGRAM_CHANNEL_NAME", "")
        or getattr(settings, "TELEGRAM_CHAT_ID", "")
    )
    if raw is None:
        return ""
    s = str(raw).strip()
    if not s:
        return ""
    if _CHAT_ID_NUMERIC.fullmatch(s):
        return s
    name = s.lstrip("@").strip()
    return f"@{name}" if name else ""


def _proxies() -> dict[str, str] | None:
    p = (
        getattr(settings, "TELEGRAM_HTTP_PROXY", "")
        or getattr(settings, "HTTPS_PROXY", "")
        or getattr(settings, "HTTP_PROXY", "")
    )
    p = (p or "").strip()
    if not p:
        return None
    return {"http": p, "https": p}


def _api_get(
    token: str,
    method: str,
    params: dict[str, Any],
) -> dict[str, Any]:
    url = f"{TG_API}/bot{token}/{method}"
    try:
        resp = requests.get(url, params=params, timeout=30, proxies=_proxies())
        return resp.json()
    except (requests.RequestException, ValueError) as exc:
        logger.warning("Telegram %s failed: %s", method, exc)
        return {"ok": False, "description": str(exc)}


def _parse_bool_override(value: Any) -> bool | None:
    """Return bool when set; ``None`` means use auto-detection."""
    if value is True:
        return True
    if value is False:
        return False
    if isinstance(value, str):
        s = value.strip().lower()
        if s in ("1", "true", "yes", "on"):
            return True
        if s in ("0", "false", "no", "off"):
            return False
        if s == "auto":
            return None
    return None


def channel_owner_has_premium(token: str, chat_id: str) -> bool | None:
    """Return whether the channel *creator* has Telegram Premium.

    Uses ``getChatAdministrators`` (bot must be a channel admin).
    Result is cached per ``chat_id`` for one hour. Returns ``None`` if unknown.
    """
    if not token or not chat_id:
        return None

    cache_key = f"{_OWNER_PREMIUM_CACHE_PREFIX}{chat_id}"
    cached = cache.get(cache_key)
    if cached is not None:
        return bool(cached)

    payload = _api_get(
        token,
        "getChatAdministrators",
        {"chat_id": chat_id},
    )
    if not payload.get("ok"):
        desc = (payload.get("description") or "")[:300]
        logger.warning(
            "getChatAdministrators failed chat_id=%s: %s",
            chat_id,
            desc,
        )
        return None

    owner_user: dict[str, Any] | None = None
    for member in payload.get("result") or []:
        if not isinstance(member, dict):
            continue
        if member.get("status") == "creator":
            owner_user = member.get("user") or {}
            break

    if not owner_user:
        logger.warning(
            "No channel owner (creator) in getChatAdministrators for chat_id=%s",
            chat_id,
        )
        return None

    is_premium = bool(owner_user.get("is_premium"))
    cache.set(cache_key, is_premium, _OWNER_PREMIUM_CACHE_TTL)
    return is_premium


def channel_has_subscription(
    secrets: dict[str, Any],
    *,
    token: str = "",
    chat_id: str = "",
) -> bool:
    """Whether to use separate text/image layout (owner Premium or explicit flag).

    Priority:
    1. ``channel_subscription`` / ``has_subscription`` in credential JSON
       (``true``/``false``; omit or ``\"auto\"`` to detect via API).
    2. Bot API: channel owner ``user.is_premium`` from ``getChatAdministrators``.
    3. ``TELEGRAM_CHANNEL_HAS_SUBSCRIPTION`` env fallback when API is unavailable.
    """
    for key in ("channel_subscription", "has_subscription"):
        if key in secrets:
            override = _parse_bool_override(secrets[key])
            if override is not None:
                return override

    if token and chat_id:
        detected = channel_owner_has_premium(token, chat_id)
        if detected is not None:
            return detected

    env_val = getattr(settings, "TELEGRAM_CHANNEL_HAS_SUBSCRIPTION", False)
    if isinstance(env_val, str):
        return env_val.strip().lower() in ("1", "true", "yes", "on")
    return bool(env_val)
