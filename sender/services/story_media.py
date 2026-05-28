"""Resolve story background image path for Telegram stories."""

from __future__ import annotations

from django.core.files.storage import default_storage

from core.models.network import NETWORK_SLUG_TELEGRAM, Network
from core.models.telegram_settings import get_telegram_network_settings
from editor.models import Post
from sender.services.telegram_plan import (
    collect_body_image_paths,
    extract_img_srcs_from_html,
    storage_path_from_src,
)


class StoryMediaError(Exception):
    """Story media could not be resolved."""


def resolve_story_image_path(post: Post, *, network: Network) -> str:
    """Return storage-relative path for the story photo.

    Priority: cover → first inline body image → first gallery image →
    network fallback image.
    """
    if post.cover_image:
        path = post.cover_image.name
        if path and default_storage.exists(path):
            return path

    for src in extract_img_srcs_from_html(post.body or ""):
        path = storage_path_from_src(src)
        if path and default_storage.exists(path):
            return path

    if post.pk is not None:
        for path in collect_body_image_paths(post):
            if path and default_storage.exists(path):
                return path

    if network.slug == NETWORK_SLUG_TELEGRAM:
        tg_settings = get_telegram_network_settings()
        if tg_settings and tg_settings.story_fallback_image:
            path = tg_settings.story_fallback_image.name
            if path and default_storage.exists(path):
                return path

    if network.slug == NETWORK_SLUG_TELEGRAM:
        raise StoryMediaError(
            "No story image found on the post and Telegram network has no "
            "story fallback image configured."
        )
    raise StoryMediaError("No story image available for this post.")
