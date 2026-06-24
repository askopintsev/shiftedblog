"""Thin adapter around sender publish workflow."""

from __future__ import annotations

from typing import Any

from core.models.network import NETWORK_SLUG_SITE, NETWORK_SLUG_TELEGRAM
from editor.models import Post
from sender.admin_views import _build_telegram_preview
from sender.services.dto import PublishJobResult, StoryAvailabilityDTO
from sender.services.post_sender import run_publish_job
from sender.services.telegram_publisher import _telegram_secrets
from sender.services.telegram_stories import check_story_availability


def publish_job_result_to_dict(result: PublishJobResult) -> dict[str, Any]:
    by_network: dict[str, Any] = {}
    for key, item in result.by_network.items():
        by_network[key] = {
            "ok": item.ok,
            "message_url": item.message_url,
            "message_id": item.message_id,
            "story_id": item.story_id,
            "story_url": item.story_url,
            "error": item.error,
            "detail": item.detail,
        }
    return {
        "all_ok": result.all_ok,
        "post_id": result.post_id,
        "status_updated": result.status_updated,
        "by_network": by_network,
    }


def run_publish(
    post_id: int,
    *,
    dest_site: bool,
    dest_telegram: bool,
    telegram_format: str,
    crosslink_network: str | None,
    telegram_post_story: bool,
) -> dict[str, Any]:
    slugs: list[str] = []
    if dest_site:
        slugs.append(NETWORK_SLUG_SITE)
    if dest_telegram:
        slugs.append(NETWORK_SLUG_TELEGRAM)
    result = run_publish_job(
        post_id,
        slugs,
        telegram_format=telegram_format,
        telegram_crosslink_network=crosslink_network,
        telegram_post_story=telegram_post_story,
    )
    return publish_job_result_to_dict(result)


def story_availability_dict() -> dict[str, Any]:
    try:
        dto = check_story_availability(_telegram_secrets())
    except Exception:
        dto = StoryAvailabilityDTO(
            available=False,
            reason="Story availability check failed.",
        )
    return {
        "available": dto.available,
        "reason": dto.reason,
        "bot_can_post_stories": dto.bot_can_post_stories,
        "free_story_slots": dto.free_story_slots,
    }


def telegram_preview_dict(
    post_id: int,
    *,
    telegram_format: str,
    crosslink_network: str | None,
) -> dict[str, Any] | None:
    from django.http import HttpRequest

    request = HttpRequest()
    payload, _, owner_premium, layout_source = _build_telegram_preview(
        request,
        post_id,
        telegram_format=telegram_format,
        crosslink_network=crosslink_network,
    )
    if payload is None:
        return None
    return {
        "preview_payload": payload,
        "preview_cards": payload.get("cards"),
        "telegram_owner_premium": owner_premium,
        "telegram_layout_source": layout_source,
    }


def ready_posts_queryset():
    return Post.objects.filter(status="ready_to_publish").order_by("-updated")[:200]
