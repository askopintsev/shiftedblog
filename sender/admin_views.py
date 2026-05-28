"""Staff-only admin UI for the multi-channel publish workflow."""

from __future__ import annotations

import logging

from django.contrib import messages
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from core.models.network import NETWORK_SLUG_SITE, NETWORK_SLUG_TELEGRAM
from editor import models as editor_models
from sender.services.dto import StoryAvailabilityDTO
from sender.services.post_sender import run_publish_job
from sender.services.telegram_channel import (
    channel_owner_has_premium,
    telegram_chat_id_from_secrets,
)
from sender.services.telegram_format import (
    TELEGRAM_FORMAT_CROSSLINK,
    TELEGRAM_FORMAT_FULL,
)
from sender.services.telegram_plan import build_preview_payload
from sender.services.telegram_publisher import (
    _telegram_secrets,
    preview_plan_for_post,
)
from sender.services.telegram_stories import check_story_availability
from sender.services.url_helpers import crosslink_url_for_post

logger = logging.getLogger(__name__)

CROSSLINK_NETWORK_CHOICES: tuple[tuple[str, str], ...] = ((NETWORK_SLUG_SITE, "Site"),)


def _parse_post_id(raw: str | None) -> int:
    try:
        return int(raw or "0")
    except ValueError:
        return 0


def _parse_telegram_format(raw: str | None) -> str:
    if (raw or "").strip() == TELEGRAM_FORMAT_CROSSLINK:
        return TELEGRAM_FORMAT_CROSSLINK
    return TELEGRAM_FORMAT_FULL


def _parse_crosslink_network(raw: str | None) -> str | None:
    slug = (raw or "").strip()
    if not slug:
        return None
    allowed = {choice[0] for choice in CROSSLINK_NETWORK_CHOICES}
    return slug if slug in allowed else None


def _build_telegram_preview(
    request: HttpRequest,
    post_id: int,
    *,
    telegram_format: str = TELEGRAM_FORMAT_FULL,
    crosslink_network: str | None = None,
) -> tuple[dict | None, int | None, bool | None, str]:
    """Return preview payload and layout metadata for ``post_id``."""
    if not post_id:
        messages.error(request, "Select a post before previewing Telegram formatting.")
        return None, None, None, ""

    post = get_object_or_404(
        editor_models.Post.objects.prefetch_related("tags", "gallery_images"),
        pk=post_id,
        status="ready_to_publish",
    )

    crosslink_url: str | None = None
    if telegram_format == TELEGRAM_FORMAT_CROSSLINK:
        if not crosslink_network:
            messages.error(
                request,
                "Select a crosslink target network before previewing.",
            )
            return None, post_id, None, ""
        crosslink_url = crosslink_url_for_post(post, crosslink_network)
        if not crosslink_url:
            messages.error(
                request,
                f"Could not resolve a URL for crosslink target {crosslink_network!r}.",
            )
            return None, post_id, None, ""

    try:
        secrets = _telegram_secrets()
        plan = preview_plan_for_post(
            post,
            secrets,
            format_mode=telegram_format,
            crosslink_url=crosslink_url,
        )
        preview_payload = build_preview_payload(plan)
    except Exception:
        logger.exception("Telegram preview failed for post_id=%s", post_id)
        messages.error(
            request,
            "Could not build Telegram preview. Check server logs for details.",
        )
        return None, post_id, None, ""

    if not preview_payload.get("cards"):
        messages.warning(request, "Nothing to preview for the selected post.")

    if telegram_format == TELEGRAM_FORMAT_CROSSLINK:
        layout_source = (
            f"Crosslink to {crosslink_network}: text-only message with linked label "
            "and tags."
        )
        return preview_payload, post_id, None, layout_source

    token = (secrets.get("bot_token") or "").strip()
    chat_id = telegram_chat_id_from_secrets(secrets)
    telegram_owner_premium: bool | None = None
    if token and chat_id:
        try:
            telegram_owner_premium = channel_owner_has_premium(token, chat_id)
        except Exception:
            logger.exception(
                "Telegram owner Premium lookup failed for chat_id=%s",
                chat_id,
            )

    layout_source = ""
    if plan.has_subscription:
        if telegram_owner_premium is True:
            layout_source = (
                "Channel owner has Telegram Premium; album uses caption on first photo."
            )
        elif telegram_owner_premium is False:
            layout_source = (
                "Cover-only posts may send text separately; "
                "album uses caption on first photo."
            )
        else:
            layout_source = (
                "Premium layout from credentials or env (album caption on first photo)."
            )
    elif telegram_owner_premium is False:
        layout_source = "Owner has no Premium: cover caption + gallery when possible."
    elif telegram_owner_premium is True:
        layout_source = "Owner has Premium but layout override is off."
    else:
        layout_source = "Standard layout (caption + gallery when one post fits)."

    return preview_payload, post_id, telegram_owner_premium, layout_source


@require_http_methods(["GET", "POST"])
def publish_workflow(request: HttpRequest) -> HttpResponse:
    posts = editor_models.Post.objects.filter(status="ready_to_publish").order_by(
        "-updated",
    )[:200]

    preview_payload: dict | None = None
    preview_post_id: int | None = None
    telegram_owner_premium: bool | None = None
    telegram_layout_source: str = ""
    selected_post_id = request.GET.get("post_id") or request.POST.get("post_id")
    form_telegram_format = _parse_telegram_format(
        request.GET.get("telegram_format") or request.POST.get("telegram_format"),
    )
    form_crosslink_network = _parse_crosslink_network(
        request.GET.get("crosslink_network") or request.POST.get("crosslink_network"),
    )
    form_telegram_post_story = bool(
        request.GET.get("telegram_post_story")
        or request.POST.get("telegram_post_story"),
    )
    telegram_story_availability = None
    if request.method == "GET":
        try:
            telegram_story_availability = check_story_availability(_telegram_secrets())
        except Exception:
            logger.exception("Telegram story availability check failed")
            telegram_story_availability = StoryAvailabilityDTO(
                available=False,
                reason="Story availability check failed.",
            )

    if request.method == "GET" and request.GET.get("preview_telegram"):
        post_id = _parse_post_id(selected_post_id)
        (
            preview_payload,
            preview_post_id,
            telegram_owner_premium,
            telegram_layout_source,
        ) = _build_telegram_preview(
            request,
            post_id,
            telegram_format=form_telegram_format,
            crosslink_network=form_crosslink_network,
        )

    if request.method == "POST" and request.POST.get("workflow_action") == "publish":
        post_id = _parse_post_id(selected_post_id)
        slugs: list[str] = []
        if request.POST.get("dest_site"):
            slugs.append(NETWORK_SLUG_SITE)
        if request.POST.get("dest_telegram"):
            slugs.append(NETWORK_SLUG_TELEGRAM)

        result = run_publish_job(
            post_id,
            slugs,
            telegram_format=form_telegram_format,
            telegram_crosslink_network=form_crosslink_network,
            telegram_post_story=form_telegram_post_story,
        )
        for key, r in result.by_network.items():
            if key == "_":
                messages.error(
                    request,
                    f"Cannot publish: {r.error} — {r.detail}",
                )
            elif r.ok:
                detail = r.message_url or "ok"
                if r.story_url:
                    detail = f"{detail} (story: {r.story_url})"
                messages.success(request, f"{key}: {detail}")
            else:
                messages.error(
                    request,
                    f"{key}: {r.error} — {r.detail}",
                )

        if result.all_ok and result.status_updated:
            messages.success(
                request,
                "All selected channels succeeded. Post status set to Published.",
            )
        elif result.all_ok and not result.by_network.get("_"):
            messages.success(request, "Selected channels completed.")

        return HttpResponseRedirect(reverse("sender_publish_workflow"))

    elif request.method == "POST":
        messages.error(request, "Unknown publish action.")

    form_post_id = _parse_post_id(selected_post_id) or None

    return render(
        request,
        "admin/sender/publish_workflow.html",
        {
            "title": "Publish to channels",
            "posts": posts,
            "opts": editor_models.Post._meta,
            "NETWORK_SLUG_SITE": NETWORK_SLUG_SITE,
            "NETWORK_SLUG_TELEGRAM": NETWORK_SLUG_TELEGRAM,
            "TELEGRAM_FORMAT_FULL": TELEGRAM_FORMAT_FULL,
            "TELEGRAM_FORMAT_CROSSLINK": TELEGRAM_FORMAT_CROSSLINK,
            "crosslink_network_choices": CROSSLINK_NETWORK_CHOICES,
            "form_telegram_format": form_telegram_format,
            "form_crosslink_network": form_crosslink_network,
            "form_telegram_post_story": form_telegram_post_story,
            "telegram_story_availability": telegram_story_availability,
            "preview_payload": preview_payload,
            "preview_cards": (preview_payload or {}).get("cards"),
            "preview_post_id": preview_post_id,
            "form_post_id": preview_post_id or form_post_id,
            "telegram_owner_premium": telegram_owner_premium,
            "telegram_layout_source": telegram_layout_source,
        },
    )
