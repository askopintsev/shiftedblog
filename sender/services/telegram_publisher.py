"""Telegram Bot API outbound posting with HTML formatting and series support."""

from __future__ import annotations

import json
import logging
import os
from typing import Any

import requests
from django.conf import settings
from django.core.files.storage import default_storage

from core.models.network import NETWORK_SLUG_TELEGRAM, Credential, Network
from core.models.telegram_settings import post_continuation_prefix
from editor.image_upload import build_share_jpeg_from_cover_bytes
from editor.models import Post
from sender.services.dto import PublishResult
from sender.services.telegram_channel import (
    channel_has_subscription,
    telegram_chat_id_from_secrets,
)
from sender.services.telegram_format import (
    TELEGRAM_FORMAT_CROSSLINK,
    TELEGRAM_FORMAT_FULL,
    prepare_outbound_telegram_html,
    truncate_telegram_html,
)
from sender.services.telegram_plan import (
    MAX_CAPTION_LEN,
    MAX_MEDIA_GROUP,
    TelegramPlannedStep,
    TelegramPublishPlan,
    _chunk_media,
    build_telegram_crosslink_plan,
    build_telegram_plan,
    text_dispatches_for_step,
)

logger = logging.getLogger(__name__)

TG_API = "https://api.telegram.org"
PARSE_MODE = "HTML"


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


def _message_url_from_response(data: dict[str, Any]) -> tuple[int | None, str]:
    result = data.get("result") or {}
    chat = result.get("chat") or {}
    mid = result.get("message_id")
    username = chat.get("username")
    if username and mid is not None:
        return int(mid), f"https://t.me/{username}/{mid}"
    site = getattr(settings, "SITE_URL", "") or ""
    if site and mid is not None:
        return int(mid), f"{site.rstrip('/')}/#telegram-message-{mid}"
    fallback = (getattr(settings, "SITE_URL", "") or "").rstrip("/") + "/"
    return (int(mid) if mid is not None else None), fallback


def _photo_upload_file(storage_path: str) -> tuple[str, bytes, str]:
    """Return ``(field_name, bytes, mime)`` for multipart upload."""
    with default_storage.open(storage_path, "rb") as fh:
        raw = fh.read()
    base = os.path.basename(storage_path)
    stem, ext = os.path.splitext(base)
    ext_l = ext.lower()
    if ext_l in (".avif", ".webp", ".png", ".gif", ".bmp", ".tiff"):
        data = build_share_jpeg_from_cover_bytes(raw)
        return f"{stem}.jpg", data, "image/jpeg"
    if ext_l in (".jpg", ".jpeg"):
        return base, raw, "image/jpeg"
    return base or "image.jpg", raw, "image/jpeg"


def _api_post_json(
    token: str,
    method: str,
    payload: dict[str, Any],
) -> tuple[dict[str, Any], requests.Response]:
    url = f"{TG_API}/bot{token}/{method}"
    resp = requests.post(
        url,
        json=payload,
        timeout=90,
        proxies=_proxies(),
    )
    try:
        body = resp.json()
    except ValueError:
        body = {"ok": False, "description": resp.text[:500]}
    return body, resp


def _api_post_multipart(
    token: str,
    method: str,
    fields: dict[str, tuple[str | None, str] | tuple[str, bytes, str]],
) -> tuple[dict[str, Any], requests.Response]:
    """Send multipart request; non-file fields use ``(None, value)`` tuples."""
    url = f"{TG_API}/bot{token}/{method}"
    resp = requests.post(
        url,
        files=fields,
        timeout=90,
        proxies=_proxies(),
    )
    try:
        body = resp.json()
    except ValueError:
        body = {"ok": False, "description": resp.text[:500]}
    return body, resp


def _fail_from_payload(
    payload: dict[str, Any],
    resp: requests.Response,
) -> PublishResult:
    desc_raw = payload.get("description") or resp.text[:500]
    desc = _telegram_api_error_detail(str(desc_raw))
    lowered = str(desc_raw).lower()
    if "parse" in lowered or "entity" in lowered or "html" in lowered:
        desc = (
            f"{desc} Check Telegram HTML: only <b>, <i>, <u>, <s>, <a>, "
            "<code>, <pre>, <blockquote> tags; no nested duplicate tags."
        )[:700]
    logger.warning("Telegram API error: %s", desc_raw)
    return PublishResult(ok=False, error="telegram_api", detail=desc[:700])


def _send_message(
    token: str,
    chat_id: str,
    text: str,
    *,
    enable_link_preview: bool = False,
) -> tuple[PublishResult, str, int | None]:
    if not text:
        return PublishResult(ok=True), "", None
    text = prepare_outbound_telegram_html(text)
    payload, resp = _api_post_json(
        token,
        "sendMessage",
        {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": PARSE_MODE,
            "disable_web_page_preview": not enable_link_preview,
        },
    )
    if not payload.get("ok"):
        return _fail_from_payload(payload, resp), "", None
    message_id, link = _message_url_from_response(payload)
    return (
        PublishResult(ok=True, message_url=link, message_id=message_id),
        link,
        message_id,
    )


def _send_photo(
    token: str,
    chat_id: str,
    storage_path: str,
    caption: str | None,
) -> tuple[PublishResult, str, int | None]:
    fname, photo_bytes, mime = _photo_upload_file(storage_path)
    fields: dict[str, tuple[str | None, str] | tuple[str, bytes, str]] = {
        "chat_id": (None, str(chat_id)),
        "photo": (fname, photo_bytes, mime),
    }
    if caption:
        caption = prepare_outbound_telegram_html(
            truncate_telegram_html(caption, MAX_CAPTION_LEN),
        )
        fields["caption"] = (None, caption)
        fields["parse_mode"] = (None, PARSE_MODE)
    payload, resp = _api_post_multipart(token, "sendPhoto", fields)
    if not payload.get("ok"):
        return _fail_from_payload(payload, resp), "", None
    message_id, link = _message_url_from_response(payload)
    return (
        PublishResult(ok=True, message_url=link, message_id=message_id),
        link,
        message_id,
    )


def _send_media_group(
    token: str,
    chat_id: str,
    paths: list[str],
    caption: str | None = None,
) -> tuple[PublishResult, str, int | None]:
    if not paths:
        return PublishResult(ok=True), "", None
    media_json: list[dict[str, str]] = []
    fields: dict[str, tuple[str | None, str] | tuple[str, bytes, str]] = {
        "chat_id": (None, str(chat_id)),
    }
    for i, path in enumerate(paths[:MAX_MEDIA_GROUP]):
        key = f"file{i}"
        fname, data, mime = _photo_upload_file(path)
        item: dict[str, str] = {"type": "photo", "media": f"attach://{key}"}
        if i == 0 and caption:
            item["caption"] = prepare_outbound_telegram_html(
                truncate_telegram_html(caption, MAX_CAPTION_LEN),
            )
            item["parse_mode"] = PARSE_MODE
        media_json.append(item)
        fields[key] = (fname, data, mime)
    fields["media"] = (None, json.dumps(media_json, separators=(",", ":")))
    payload, resp = _api_post_multipart(token, "sendMediaGroup", fields)
    if not payload.get("ok"):
        return _fail_from_payload(payload, resp), "", None
    result = payload.get("result") or []
    first = result[0] if isinstance(result, list) and result else {}
    message_id, link = _message_url_from_response({"result": first})
    return (
        PublishResult(ok=True, message_url=link, message_id=message_id),
        link,
        message_id,
    )


def _execute_step(
    step: TelegramPlannedStep,
    *,
    token: str,
    chat_id: str,
    has_subscription: bool,
) -> tuple[PublishResult, str, int | None]:
    """Run one plan step; return result, first message URL and id in step."""
    dispatches = text_dispatches_for_step(
        step,
        has_subscription=has_subscription,
    )
    caption = next((text for kind, text in dispatches if kind == "caption"), None)
    message = next((text for kind, text in dispatches if kind == "message"), None)
    first_link = ""
    first_message_id: int | None = None
    link_preview = step.enable_link_preview

    if step.combined_album:
        for chunk_idx, chunk in enumerate(_chunk_media(step.media_paths)):
            chunk_caption = (
                caption if chunk_idx == 0 and step.caption_on_media_group else None
            )
            res, link, mid = _send_media_group(token, chat_id, chunk, chunk_caption)
            if not res.ok:
                return res, first_link, first_message_id
            if link and not first_link:
                first_link = link
            if mid is not None and first_message_id is None:
                first_message_id = mid
        if message:
            res, link, mid = _send_message(
                token,
                chat_id,
                message,
                enable_link_preview=link_preview,
            )
            if not res.ok:
                return res, first_link, first_message_id
            if link and not first_link:
                first_link = link
            if mid is not None and first_message_id is None:
                first_message_id = mid
        return (
            PublishResult(
                ok=True,
                message_url=first_link,
                message_id=first_message_id,
            ),
            first_link,
            first_message_id,
        )

    if step.cover_path:
        res, link, mid = _send_photo(token, chat_id, step.cover_path, caption)
        if not res.ok:
            return res, first_link, first_message_id
        if link and not first_link:
            first_link = link
        if mid is not None and first_message_id is None:
            first_message_id = mid

    if message:
        res, link, mid = _send_message(
            token,
            chat_id,
            message,
            enable_link_preview=link_preview,
        )
        if not res.ok:
            return res, first_link, first_message_id
        if link and not first_link:
            first_link = link
        if mid is not None and first_message_id is None:
            first_message_id = mid

    for chunk in _chunk_media(step.media_paths):
        res, link, mid = _send_media_group(token, chat_id, chunk)
        if not res.ok:
            return res, first_link, first_message_id
        if link and not first_link:
            first_link = link
        if mid is not None and first_message_id is None:
            first_message_id = mid

    return (
        PublishResult(
            ok=True,
            message_url=first_link,
            message_id=first_message_id,
        ),
        first_link,
        first_message_id,
    )


def _telegram_runtime(
    secrets: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], str, str]:
    secrets = secrets if secrets is not None else _telegram_secrets()
    token = (
        secrets.get("bot_token") or getattr(settings, "TELEGRAM_BOT_TOKEN", "")
    ).strip()
    chat_id = telegram_chat_id_from_secrets(secrets)
    return secrets, token, chat_id


def resolve_telegram_plan(
    post: Post,
    secrets: dict[str, Any] | None = None,
    *,
    format_mode: str = TELEGRAM_FORMAT_FULL,
    crosslink_url: str | None = None,
) -> TelegramPublishPlan:
    """Single entry point for preview and publish — same formatting and layout."""
    post = Post.objects.prefetch_related("tags", "gallery_images").get(pk=post.pk)
    if format_mode == TELEGRAM_FORMAT_CROSSLINK:
        url = (crosslink_url or "").strip()
        if not url:
            return TelegramPublishPlan(steps=[])
        return build_telegram_crosslink_plan(post, link_url=url)
    secrets, token, chat_id = _telegram_runtime(secrets)
    return build_plan_for_post(post, secrets, token=token, chat_id=chat_id)


def build_plan_for_post(
    post: Post,
    secrets: dict[str, Any],
    *,
    token: str = "",
    chat_id: str = "",
) -> TelegramPublishPlan:
    has_sub = channel_has_subscription(secrets, token=token, chat_id=chat_id)
    return build_telegram_plan(
        post,
        has_subscription=has_sub,
        continuation_prefix=post_continuation_prefix(),
    )


def preview_plan_for_post(
    post: Post,
    secrets: dict[str, Any] | None = None,
    *,
    format_mode: str = TELEGRAM_FORMAT_FULL,
    crosslink_url: str | None = None,
) -> TelegramPublishPlan:
    """Alias for :func:`resolve_telegram_plan` (admin preview)."""
    return resolve_telegram_plan(
        post,
        secrets,
        format_mode=format_mode,
        crosslink_url=crosslink_url,
    )


def publish_to_telegram(
    post: Post,
    *,
    format_mode: str = TELEGRAM_FORMAT_FULL,
    crosslink_url: str | None = None,
) -> PublishResult:
    secrets, token, chat_id = _telegram_runtime()

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

    plan = resolve_telegram_plan(
        post,
        secrets,
        format_mode=format_mode,
        crosslink_url=crosslink_url,
    )
    if not plan.steps:
        return PublishResult(ok=False, error="empty_plan", detail="Nothing to publish.")

    stored_link = ""
    stored_message_id: int | None = None

    for step in plan.steps:
        res, step_link, step_message_id = _execute_step(
            step,
            token=token,
            chat_id=chat_id,
            has_subscription=plan.has_subscription,
        )
        if not res.ok:
            return res
        if step_link and not stored_link:
            stored_link = step_link
        if step_message_id is not None and stored_message_id is None:
            stored_message_id = step_message_id

    return PublishResult(
        ok=True,
        message_url=stored_link,
        message_id=stored_message_id,
    )
