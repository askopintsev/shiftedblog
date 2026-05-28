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
from sender.services.telegram_format import (
    TELEGRAM_FORMAT_CROSSLINK,
    TELEGRAM_FORMAT_FULL,
)
from sender.services.url_helpers import crosslink_url_for_post

logger = logging.getLogger(__name__)

RETRIES = 3
BACKOFF_SEC = (1.0, 2.0)


def _retry_call(
    func: Callable[..., PublishResult],
    *args: object,
    **kwargs: object,
) -> PublishResult:
    last: PublishResult | None = None
    for attempt in range(RETRIES):
        last = func(*args, **kwargs)
        if last.ok:
            return last
        if attempt < RETRIES - 1:
            delay = BACKOFF_SEC[min(attempt, len(BACKOFF_SEC) - 1)]
            time.sleep(delay)
    assert last is not None
    return last


def _invalid_job(
    post_id: int,
    *,
    error: str,
    detail: str,
) -> PublishJobResult:
    return PublishJobResult(
        all_ok=False,
        post_id=post_id,
        by_network={
            "_": PublishResult(
                ok=False,
                error=error,
                detail=detail,
            )
        },
    )


def _order_slugs_for_crosslink(
    slugs: list[str],
    *,
    crosslink_network: str | None,
) -> list[str]:
    """Publish crosslink target before Telegram when both are selected."""
    if not crosslink_network or crosslink_network not in slugs:
        return slugs
    if NETWORK_SLUG_TELEGRAM not in slugs:
        return slugs
    ordered = [
        s for s in slugs if s != crosslink_network and s != NETWORK_SLUG_TELEGRAM
    ]
    ordered.append(crosslink_network)
    ordered.append(NETWORK_SLUG_TELEGRAM)
    return ordered


def run_publish_job(
    post_id: int,
    network_slugs: Iterable[str],
    *,
    telegram_format: str = TELEGRAM_FORMAT_FULL,
    telegram_crosslink_network: str | None = None,
) -> PublishJobResult:
    """Publish ``post_id`` to each network in ``network_slugs``.

    On full success across all selected networks, sets post status to ``published``.
    ``telegram_format`` selects full post vs crosslink for Telegram.
    """
    slugs = list(network_slugs)
    by_network: dict[str, PublishResult] = {}

    if not slugs:
        return _invalid_job(
            post_id,
            error="no_destinations",
            detail="Select at least one channel.",
        )

    if telegram_format not in (TELEGRAM_FORMAT_FULL, TELEGRAM_FORMAT_CROSSLINK):
        return _invalid_job(
            post_id,
            error="invalid_telegram_format",
            detail=f"Unknown Telegram format {telegram_format!r}.",
        )

    if NETWORK_SLUG_TELEGRAM in slugs and telegram_format == TELEGRAM_FORMAT_CROSSLINK:
        if not telegram_crosslink_network:
            return _invalid_job(
                post_id,
                error="missing_crosslink_network",
                detail=("Select which network the Telegram crosslink should point to."),
            )
        if telegram_crosslink_network == NETWORK_SLUG_TELEGRAM:
            return _invalid_job(
                post_id,
                error="invalid_crosslink_network",
                detail="Crosslink target cannot be Telegram.",
            )
        if telegram_crosslink_network not in slugs:
            return _invalid_job(
                post_id,
                error="crosslink_not_selected",
                detail=(
                    "Crosslink target must be one of the selected destinations "
                    f"(missing {telegram_crosslink_network!r})."
                ),
            )

    slugs = _order_slugs_for_crosslink(
        slugs,
        crosslink_network=telegram_crosslink_network,
    )

    with transaction.atomic():
        post = Post.objects.select_for_update().get(pk=post_id)
        if post.status != "ready_to_publish":
            return _invalid_job(
                post_id,
                error="invalid_status",
                detail=f"Post must be ready_to_publish (got {post.status!r}).",
            )

        crosslink_url: str | None = None
        if (
            NETWORK_SLUG_TELEGRAM in slugs
            and telegram_format == TELEGRAM_FORMAT_CROSSLINK
            and telegram_crosslink_network
        ):
            crosslink_url = crosslink_url_for_post(post, telegram_crosslink_network)
            if not crosslink_url:
                return _invalid_job(
                    post_id,
                    error="missing_crosslink_url",
                    detail=(
                        f"Could not resolve a public URL for crosslink target "
                        f"{telegram_crosslink_network!r}."
                    ),
                )

        for slug in slugs:
            if slug == NETWORK_SLUG_SITE:
                res = _retry_call(site_publisher.publish_to_site, post)
            elif slug == NETWORK_SLUG_TELEGRAM:
                res = _retry_call(
                    telegram_publisher.publish_to_telegram,
                    post,
                    format_mode=telegram_format,
                    crosslink_url=crosslink_url,
                )
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
