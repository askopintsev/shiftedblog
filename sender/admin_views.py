"""Staff-only admin UI for the multi-channel publish workflow."""

from __future__ import annotations

from django.contrib import messages
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from core.models.network import NETWORK_SLUG_SITE, NETWORK_SLUG_TELEGRAM
from editor import models as editor_models
from sender.services.post_sender import run_publish_job


@require_http_methods(["GET", "POST"])
def publish_workflow(request: HttpRequest) -> HttpResponse:
    posts = editor_models.Post.objects.filter(status="ready_to_publish").order_by(
        "-updated",
    )[:200]

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

    return render(
        request,
        "admin/sender/publish_workflow.html",
        {
            "title": "Publish to channels",
            "posts": posts,
            "opts": editor_models.Post._meta,
            "NETWORK_SLUG_SITE": NETWORK_SLUG_SITE,
            "NETWORK_SLUG_TELEGRAM": NETWORK_SLUG_TELEGRAM,
        },
    )
