"""Orchestrate multi-channel publishing."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable, Iterable

from django.db import transaction

from core.models.network import NETWORK_SLUG_SITE, NETWORK_SLUG_TELEGRAM, Network
from editor.models import Post
from sender.models import PostLink
from sender.services import site_publisher, telegram_publisher
from sender.services.dto import PublishJobResult, PublishResult

logger = logging.getLogger(__name__)

RETRIES = 3
BACKOFF_SEC = (1.0, 2.0)


def _retry_call(
    func: Callable[..., PublishResult],
    *args: object,
) -> PublishResult:
    last: PublishResult | None = None
    for attempt in range(RETRIES):
        last = func(*args)
        if last.ok:
            return last
        if attempt < RETRIES - 1:
            delay = BACKOFF_SEC[min(attempt, len(BACKOFF_SEC) - 1)]
            time.sleep(delay)
    assert last is not None
    return last


def run_publish_job(
    post_id: int,
    network_slugs: Iterable[str],
    *,
    variant: str = "full_text",
) -> PublishJobResult:
    """Publish ``post_id`` to each network in ``network_slugs``.

    On full success across all selected networks, sets post status to ``published``.
    ``variant`` is reserved for future formatting modes.
    """
    _ = variant
    slugs = list(network_slugs)
    by_network: dict[str, PublishResult] = {}

    if not slugs:
        return PublishJobResult(
            all_ok=False,
            post_id=post_id,
            by_network={
                "_": PublishResult(
                    ok=False,
                    error="no_destinations",
                    detail="Select at least one channel.",
                )
            },
        )

    with transaction.atomic():
        post = Post.objects.select_for_update().get(pk=post_id)
        if post.status != "ready_to_publish":
            return PublishJobResult(
                all_ok=False,
                post_id=post_id,
                by_network={
                    "_": PublishResult(
                        ok=False,
                        error="invalid_status",
                        detail=f"Post must be ready_to_publish (got {post.status!r}).",
                    )
                },
            )

        for slug in slugs:
            if slug == NETWORK_SLUG_SITE:
                res = _retry_call(site_publisher.publish_to_site, post)
            elif slug == NETWORK_SLUG_TELEGRAM:
                res = _retry_call(telegram_publisher.publish_to_telegram, post)
            else:
                res = PublishResult(
                    ok=False,
                    error="unknown_network",
                    detail=slug,
                )
            by_network[slug] = res
            if res.ok:
                network = Network.objects.get(slug=slug)
                PostLink.objects.update_or_create(
                    post=post,
                    network=network,
                    defaults={"url": res.url},
                )
            else:
                logger.warning(
                    "Publish failed network=%s post_id=%s error=%s",
                    slug,
                    post_id,
                    res.detail or res.error,
                )

        all_ok = all(by_network[s].ok for s in slugs)
        status_updated = False
        if all_ok:
            post.status = "published"
            post.save(_allow_publish_via_sender=True)
            status_updated = True

    return PublishJobResult(
        all_ok=all_ok,
        post_id=post_id,
        by_network=by_network,
        status_updated=status_updated,
    )
