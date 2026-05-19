"""Telegram Bot API outbound posting."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

import requests
from django.conf import settings
from django.utils.html import strip_tags

from core.models.network import NETWORK_SLUG_TELEGRAM, Credential, Network
from editor.models import Post
from sender.services.dto import PublishResult

logger = logging.getLogger(__name__)

TG_API = "https://api.telegram.org"
MAX_LEN = 4096
# Bot API ``chat_id`` accepts numeric ids or @username for public channels.
_CHAT_ID_NUMERIC = re.compile(r"^-?\d+$")


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


def _plain_body(html: str) -> str:
    text = strip_tags(html or "")
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > MAX_LEN - 50:
        text = text[: MAX_LEN - 50] + "… [truncated]"
    return text[:MAX_LEN]


def _telegram_secrets() -> dict[str, Any]:
    try:
        net = Network.objects.get(slug=NETWORK_SLUG_TELEGRAM)
    except Network.DoesNotExist:
        return {}
    cred = Credential.objects.filter(network=net).order_by("pk").first()
    if not cred:
        return {}
    try:
        return cred.get_secrets_dict()
    except (json.JSONDecodeError, ValueError, TypeError):
        return {}


def _telegram_chat_id_api_value(secrets: dict[str, Any]) -> str:
    """Resolve DB/env secrets to the value sent as Bot API ``chat_id``."""
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


def _telegram_api_error_detail(description: str) -> str:
    """Append operator hints for common Telegram setup mistakes."""
    base = (description or "").strip()[:500]
    lowered = base.lower()
    if "not a member" in lowered or "chat not found" in lowered:
        hint = (
            " Add the bot under Channel → Administrators with "
            '"Post messages", or use a numeric chat_id for private channels.'
        )
        return (base + hint)[:700]
    return base


def _message_url_from_response(data: dict[str, Any]) -> str:
    result = data.get("result") or {}
    chat = result.get("chat") or {}
    mid = result.get("message_id")
    username = chat.get("username")
    if username and mid is not None:
        return f"https://t.me/{username}/{mid}"
    site = getattr(settings, "SITE_URL", "") or ""
    if site and mid is not None:
        return f"{site.rstrip('/')}/#telegram-message-{mid}"
    return (getattr(settings, "SITE_URL", "") or "").rstrip("/") + "/"


def publish_to_telegram(post: Post) -> PublishResult:
    secrets = _telegram_secrets()
    token = (
        secrets.get("bot_token") or getattr(settings, "TELEGRAM_BOT_TOKEN", "")
    ).strip()
    chat_id = _telegram_chat_id_api_value(secrets)

    if not token or not chat_id:
        return PublishResult(
            ok=False,
            error="missing_credentials",
            detail=(
                "Set Telegram credential (bot_token, channel_name) or env "
                "TELEGRAM_BOT_TOKEN / TELEGRAM_CHANNEL_NAME "
                "(or TELEGRAM_CHAT_ID for numeric chat id)."
            ),
        )

    title = (post.title or "").strip()
    plain = _plain_body(post.body)
    text = f"{title}\n\n{plain}".strip() if title else plain.strip()
    payload = {
        "chat_id": chat_id,
        "text": text,
        "disable_web_page_preview": True,
    }
    url = f"{TG_API}/bot{token}/sendMessage"
    try:
        resp = requests.post(
            url,
            json=payload,
            timeout=45,
            proxies=_proxies(),
        )
        data = resp.json()
    except (requests.RequestException, ValueError) as exc:
        logger.warning("Telegram request failed: %s", exc)
        return PublishResult(ok=False, error="request_error", detail=str(exc)[:500])

    if not data.get("ok"):
        desc_raw = data.get("description") or resp.text[:500]
        desc = _telegram_api_error_detail(str(desc_raw))
        logger.warning("Telegram API error: %s", desc_raw)
        return PublishResult(ok=False, error="telegram_api", detail=desc[:700])

    link = _message_url_from_response(data)
    return PublishResult(ok=True, url=link)
