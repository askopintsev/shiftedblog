"""Telegram channel stories via MTProto operator session (Telethon)."""

from __future__ import annotations

import asyncio
import logging
import random
from typing import Any

from django.conf import settings
from django.core.files.storage import default_storage

from editor.models import Post
from sender.services.dto import PublishResult, StoryAvailabilityDTO
from sender.services.story_media import StoryMediaError, resolve_story_image_path
from sender.services.telegram_channel import (
    _api_get,
    telegram_chat_id_from_secrets,
)
from sender.services.telegram_format import crosslink_label_text
from sender.services.telegram_publisher import _telegram_secrets

logger = logging.getLogger(__name__)

STORY_PERIOD_SEC = 86400
_AVAILABILITY_CACHE_PREFIX = "sender:tg:story_available:"
_AVAILABILITY_CACHE_TTL = 600
_STORY_NOT_CONFIGURED_REASON = (
    "Telegram operator session is not configured (optional). "
    "Stories stay disabled until api_id, api_hash, and operator_session are set."
)
_TELETHON_MISSING_REASON = "Telethon is not installed. Stories are disabled."


def story_url_for(channel_username: str, story_id: int) -> str:
    name = (channel_username or "").strip().lstrip("@")
    return f"https://t.me/{name}/s/{story_id}"


def _channel_username_from_secrets(secrets: dict[str, Any]) -> str:
    raw = (secrets.get("channel_name") or "").strip().lstrip("@")
    if raw:
        return raw
    return (getattr(settings, "TELEGRAM_CHANNEL_NAME", "") or "").strip().lstrip("@")


def _has_operator_credentials(secrets: dict[str, Any]) -> bool:
    api_id_raw = secrets.get("api_id") or getattr(settings, "TELEGRAM_API_ID", "")
    api_hash = (
        secrets.get("api_hash") or getattr(settings, "TELEGRAM_API_HASH", "") or ""
    ).strip()
    session = (
        secrets.get("operator_session")
        or getattr(settings, "TELEGRAM_OPERATOR_SESSION", "")
        or ""
    ).strip()
    return bool(api_id_raw and api_hash and session)


def _operator_credentials(secrets: dict[str, Any]) -> tuple[int, str, str]:
    api_id_raw = secrets.get("api_id") or getattr(settings, "TELEGRAM_API_ID", "")
    api_hash = (
        secrets.get("api_hash") or getattr(settings, "TELEGRAM_API_HASH", "") or ""
    ).strip()
    session = (
        secrets.get("operator_session")
        or getattr(settings, "TELEGRAM_OPERATOR_SESSION", "")
        or ""
    ).strip()
    if not api_id_raw or not api_hash or not session:
        raise ValueError(_STORY_NOT_CONFIGURED_REASON)
    return int(api_id_raw), api_hash, session


def _import_telethon():
    try:
        from telethon import TelegramClient
        from telethon.sessions import StringSession
    except ImportError as exc:
        raise ImportError(_TELETHON_MISSING_REASON) from exc
    return TelegramClient, StringSession


def _bot_can_post_stories(token: str, chat_id: str) -> bool | None:
    if not token or not chat_id:
        return None
    me = _api_get(token, "getMe", {})
    if not me.get("ok"):
        return None
    bot_id = (me.get("result") or {}).get("id")
    if bot_id is None:
        return None
    member = _api_get(
        token,
        "getChatMember",
        {"chat_id": chat_id, "user_id": bot_id},
    )
    if not member.get("ok"):
        return None
    result = member.get("result") or {}
    if "can_post_stories" in result:
        return bool(result.get("can_post_stories"))
    return None


def _map_story_error(exc: BaseException) -> str:
    text = str(exc)
    upper = text.upper()
    if "BOOSTS_REQUIRED" in upper:
        return "Channel needs more boosts before stories can be posted."
    if "STORIES_TOO_MUCH" in upper:
        return "No free story slots on the channel."
    if "CHAT_ADMIN_REQUIRED" in upper:
        return "Operator account is not a channel admin with story rights."
    if "SESSION" in upper or "AUTH" in upper:
        return "Telegram operator session is invalid or expired."
    return text[:500]


async def _async_check_story_availability(
    secrets: dict[str, Any],
) -> StoryAvailabilityDTO:
    if not _has_operator_credentials(secrets):
        return StoryAvailabilityDTO(
            available=False,
            reason=_STORY_NOT_CONFIGURED_REASON,
        )

    token = (
        secrets.get("bot_token") or getattr(settings, "TELEGRAM_BOT_TOKEN", "")
    ).strip()
    chat_id = telegram_chat_id_from_secrets(secrets)
    bot_stories = _bot_can_post_stories(token, chat_id)
    if bot_stories is False:
        return StoryAvailabilityDTO(
            available=False,
            reason="Bot lacks Post Stories administrator permission.",
            bot_can_post_stories=False,
        )

    try:
        api_id, api_hash, session_str = _operator_credentials(secrets)
    except ValueError as exc:
        return StoryAvailabilityDTO(
            available=False,
            reason=str(exc),
            bot_can_post_stories=bot_stories,
        )

    channel_username = _channel_username_from_secrets(secrets)
    if not channel_username:
        return StoryAvailabilityDTO(
            available=False,
            reason="Telegram channel_name is not configured.",
            bot_can_post_stories=bot_stories,
        )

    try:
        telegram_client_cls, string_session_cls = _import_telethon()
        from telethon.tl.functions.stories import CanSendStoryRequest
    except ImportError as exc:
        return StoryAvailabilityDTO(
            available=False,
            reason=str(exc),
            bot_can_post_stories=bot_stories,
        )

    client = telegram_client_cls(string_session_cls(session_str), api_id, api_hash)
    await client.connect()
    try:
        if not await client.is_user_authorized():
            return StoryAvailabilityDTO(
                available=False,
                reason="Telegram operator session is not authorized.",
                bot_can_post_stories=bot_stories,
            )
        entity = await client.get_entity(channel_username)
        result = await client(CanSendStoryRequest(peer=entity))
        free_slots = int(getattr(result, "count", 0) or 0)
        if free_slots <= 0:
            return StoryAvailabilityDTO(
                available=False,
                reason="No free story slots on the channel.",
                bot_can_post_stories=bot_stories,
                free_story_slots=0,
            )
        return StoryAvailabilityDTO(
            available=True,
            reason="Stories can be posted.",
            bot_can_post_stories=bot_stories,
            free_story_slots=free_slots,
        )
    except Exception as exc:
        logger.warning("Story availability check failed: %s", exc)
        return StoryAvailabilityDTO(
            available=False,
            reason=_map_story_error(exc),
            bot_can_post_stories=bot_stories,
        )
    finally:
        await client.disconnect()


def check_story_availability(
    secrets: dict[str, Any] | None = None,
) -> StoryAvailabilityDTO:
    secrets = secrets if secrets is not None else _telegram_secrets()
    from django.core.cache import cache

    chat_id = telegram_chat_id_from_secrets(secrets)
    cache_key = f"{_AVAILABILITY_CACHE_PREFIX}{chat_id or 'default'}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    if not _has_operator_credentials(secrets):
        result = StoryAvailabilityDTO(
            available=False,
            reason=_STORY_NOT_CONFIGURED_REASON,
        )
        cache.set(cache_key, result, _AVAILABILITY_CACHE_TTL)
        return result

    result = asyncio.run(_async_check_story_availability(secrets))
    cache.set(cache_key, result, _AVAILABILITY_CACHE_TTL)
    return result


async def _async_publish_story(
    *,
    secrets: dict[str, Any],
    image_path: str,
    message_url: str,
    caption: str,
) -> tuple[int, str]:
    try:
        telegram_client_cls, string_session_cls = _import_telethon()
        from telethon.tl.functions.stories import SendStoryRequest
        from telethon.tl.types import (
            InputMediaUploadedPhoto,
            InputPrivacyValueAllowAll,
            MediaAreaCoordinates,
            MediaAreaUrl,
        )
    except ImportError as exc:
        raise ImportError(_TELETHON_MISSING_REASON) from exc

    api_id, api_hash, session_str = _operator_credentials(secrets)
    channel_username = _channel_username_from_secrets(secrets)
    if not channel_username:
        raise ValueError("Telegram channel_name is not configured.")

    abs_path = default_storage.path(image_path)
    client = telegram_client_cls(string_session_cls(session_str), api_id, api_hash)
    await client.connect()
    try:
        if not await client.is_user_authorized():
            raise ValueError("Telegram operator session is not authorized.")
        entity = await client.get_entity(channel_username)
        uploaded = await client.upload_file(abs_path)
        media = InputMediaUploadedPhoto(file=uploaded)
        link_area = MediaAreaUrl(
            coordinates=MediaAreaCoordinates(
                x=20.0,
                y=78.0,
                w=60.0,
                h=14.0,
                rotation=0.0,
                radius=8.0,
            ),
            url=message_url,
        )
        updates = await client(
            SendStoryRequest(
                peer=entity,
                media=media,
                privacy_rules=[InputPrivacyValueAllowAll()],
                random_id=random.randint(1, 2**63 - 1),
                period=STORY_PERIOD_SEC,
                caption=caption or None,
                media_areas=[link_area],
            ),
        )
        story_id = _story_id_from_updates(updates)
        if story_id is None:
            raise ValueError("Telegram did not return a story id.")
        return story_id, story_url_for(channel_username, story_id)
    finally:
        await client.disconnect()


def _story_id_from_updates(updates: Any) -> int | None:
    for story in getattr(updates, "stories", []) or []:
        story_id = getattr(story, "id", None)
        if story_id is not None:
            return int(story_id)
    for update in getattr(updates, "updates", []) or []:
        story = getattr(update, "story", None)
        if story is not None and getattr(story, "id", None) is not None:
            return int(story.id)
    return None


def publish_story_for_post(
    post: Post,
    *,
    message_url: str,
    message_id: int | None,
    secrets: dict[str, Any] | None = None,
) -> PublishResult:
    """Post a channel story linking to the published Telegram message."""
    _ = message_id
    secrets = secrets if secrets is not None else _telegram_secrets()
    try:
        from core.models.network import NETWORK_SLUG_TELEGRAM, Network

        network = Network.objects.get(slug=NETWORK_SLUG_TELEGRAM)
        image_path = resolve_story_image_path(post, network=network)
    except StoryMediaError as exc:
        return PublishResult(
            ok=False,
            error="story_media_missing",
            detail=str(exc),
        )
    except Exception as exc:
        return PublishResult(
            ok=False,
            error="story_setup_failed",
            detail=str(exc),
        )

    availability = check_story_availability(secrets)
    if not availability.available:
        return PublishResult(
            ok=False,
            error="story_unavailable",
            detail=availability.reason,
        )

    caption = crosslink_label_text(post)
    try:
        story_id, story_url = asyncio.run(
            _async_publish_story(
                secrets=secrets,
                image_path=image_path,
                message_url=message_url,
                caption=caption,
            ),
        )
    except Exception as exc:
        logger.exception("Telegram story publish failed for post_id=%s", post.pk)
        return PublishResult(
            ok=False,
            error="story_publish_failed",
            detail=_map_story_error(exc),
        )

    return PublishResult(
        ok=True,
        message_url=message_url,
        message_id=message_id,
        story_id=story_id,
        story_url=story_url,
    )
