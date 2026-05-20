"""Staff-only admin UI for the multi-channel publish workflow."""

from __future__ import annotations

from django.contrib import messages
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from core.models.network import NETWORK_SLUG_SITE, NETWORK_SLUG_TELEGRAM
from editor import models as editor_models
from sender.services.post_sender import run_publish_job
from sender.services.telegram_channel import (
    channel_owner_has_premium,
    telegram_chat_id_from_secrets,
)
from sender.services.telegram_plan import build_preview_payload
from sender.services.telegram_publisher import (
    _telegram_secrets,
    preview_plan_for_post,
)


@require_http_methods(["GET", "POST"])
def publish_workflow(request: HttpRequest) -> HttpResponse:
    posts = editor_models.Post.objects.filter(status="ready_to_publish").order_by(
        "-updated",
    )[:200]

    preview_rows: list[dict] | None = None
    preview_post_id: int | None = None
    telegram_owner_premium: bool | None = None
    telegram_layout_source: str = ""
    selected_post_id = request.GET.get("post_id") or request.POST.get("post_id")

    if request.method == "GET" and request.GET.get("preview_telegram"):
        try:
            preview_post_id = int(selected_post_id or "0")
        except ValueError:
            preview_post_id = 0
        if preview_post_id:
            post = get_object_or_404(
                editor_models.Post.objects.prefetch_related("tags", "gallery_images"),
                pk=preview_post_id,
                status="ready_to_publish",
            )
            secrets = _telegram_secrets()
            plan = preview_plan_for_post(post, secrets)
            preview_rows = build_preview_payload(plan)
            token = (secrets.get("bot_token") or "").strip()
            chat_id = telegram_chat_id_from_secrets(secrets)
            if token and chat_id:
                telegram_owner_premium = channel_owner_has_premium(token, chat_id)
            if plan.has_subscription:
                if telegram_owner_premium is True:
                    telegram_layout_source = (
                        "Channel owner has Telegram Premium (auto-detected)."
                    )
                elif telegram_owner_premium is False:
                    telegram_layout_source = (
                        "Separate text and images (not owner Premium; "
                        "check credential override or env)."
                    )
                else:
                    telegram_layout_source = (
                        "Separate text and images (forced in credentials or env)."
                    )
            else:
                if telegram_owner_premium is False:
                    telegram_layout_source = (
                        "Owner has no Premium: cover caption + gallery when possible."
                    )
                elif telegram_owner_premium is True:
                    telegram_layout_source = (
                        "Owner has Premium but layout override is off."
                    )
                else:
                    telegram_layout_source = (
                        "Standard layout (caption + gallery when one post fits)."
                    )

    if request.method == "POST":
        try:
            post_id = int(request.POST.get("post_id") or "0")
        except ValueError:
            post_id = 0
        slugs: list[str] = []
        if request.POST.get("dest_site"):
            slugs.append(NETWORK_SLUG_SITE)
        if request.POST.get("dest_telegram"):
            slugs.append(NETWORK_SLUG_TELEGRAM)

        result = run_publish_job(post_id, slugs)
        for key, r in result.by_network.items():
            if key == "_":
                messages.error(
                    request,
                    f"Cannot publish: {r.error} — {r.detail}",
                )
            elif r.ok:
                messages.success(request, f"{key}: {r.url or 'ok'}")
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

    try:
        form_post_id = int(selected_post_id or "0") if selected_post_id else None
    except ValueError:
        form_post_id = None

    return render(
        request,
        "admin/sender/publish_workflow.html",
        {
            "title": "Publish to channels",
            "posts": posts,
            "opts": editor_models.Post._meta,
            "NETWORK_SLUG_SITE": NETWORK_SLUG_SITE,
            "NETWORK_SLUG_TELEGRAM": NETWORK_SLUG_TELEGRAM,
            "preview_rows": preview_rows,
            "preview_post_id": preview_post_id,
            "form_post_id": form_post_id,
            "telegram_owner_premium": telegram_owner_premium,
            "telegram_layout_source": telegram_layout_source,
        },
    )
