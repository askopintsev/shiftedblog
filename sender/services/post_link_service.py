"""Persist outbound publication links and Telegram ids."""

from __future__ import annotations

from core.models.network import Network
from editor.models import Post
from sender.models import PostLink
from sender.services.dto import PublishResult


def upsert_post_link(
    post: Post,
    network: Network,
    result: PublishResult,
) -> PostLink:
    """Create or update ``PostLink`` from a successful ``PublishResult``."""
    link, _ = PostLink.objects.update_or_create(
        post=post,
        network=network,
        defaults={
            "message_url": result.message_url,
            "message_id": result.message_id,
            "story_id": result.story_id,
            "story_url": result.story_url or "",
        },
    )
    return link
