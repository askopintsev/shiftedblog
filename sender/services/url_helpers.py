"""Build canonical public URL for a blog post."""

from __future__ import annotations

from django.conf import settings
from django.core.files.storage import default_storage
from django.http import HttpRequest
from django.urls import reverse

from core.models.network import NETWORK_SLUG_SITE
from editor.image_upload import (
    share_jpeg_has_social_dimensions,
    social_share_storage_name,
)
from editor.models import Post


def public_post_url(post: Post) -> str:
    """Return canonical public URL for ``post`` (used when storing ``PostLink``).

    ``settings.SITE_URL`` must include scheme, host, and **non-default port** in dev
    (e.g. ``http://localhost:8888``) so stored URLs match how users open the site.
    For same-origin links in HTML templates, prefer
    ``request.build_absolute_uri(post.get_absolute_url())`` so the port always matches
    the current request.
    """
    base = getattr(settings, "SITE_URL", "") or ""
    base = base.rstrip("/")
    path = reverse("blog:post_detail", args=[post.slug])
    if not path.startswith("/"):
        path = "/" + path
    return base + path


def crosslink_url_for_post(post: Post, network_slug: str) -> str | None:
    """Public URL on *network_slug* for Telegram crosslink posts."""
    if network_slug == NETWORK_SLUG_SITE:
        return public_post_url(post)
    from sender.models import PostLink

    link = (
        PostLink.objects.filter(post=post, network__slug=network_slug)
        .order_by("-pk")
        .first()
    )
    if link and (link.message_url or "").strip():
        return link.message_url.strip()
    return None


def _share_image_cache_bust(post: Post) -> int:
    updated = getattr(post, "updated", None)
    if updated is not None:
        return int(updated.timestamp())
    return 0


def post_share_image_media_url(post: Post) -> str | None:
    """Relative URL to nginx-served share JPEG, or ``None`` if unavailable."""
    if not post.cover_image or not post.cover_image.name:
        return None

    share_name = social_share_storage_name(post.cover_image.name)
    if not default_storage.exists(share_name):
        return None

    with default_storage.open(share_name, "rb") as share_file:
        if not share_jpeg_has_social_dimensions(share_file.read()):
            return None

    media_path = default_storage.url(share_name)
    version = _share_image_cache_bust(post)
    joiner = "&" if "?" in media_path else "?"
    return f"{media_path}{joiner}v={version}"


def _absolute_url(path: str, request: HttpRequest | None) -> str:
    if request is not None:
        return request.build_absolute_uri(path)
    base = getattr(settings, "SITE_URL", "") or ""
    base = base.rstrip("/")
    if not path.startswith("/"):
        path = "/" + path
    return base + path


def post_og_image_absolute_url(
    post: Post,
    request: HttpRequest | None = None,
) -> str | None:
    """Absolute JPEG URL for social link previews (Telegram, X/Twitter, etc.)."""
    media_url = post_share_image_media_url(post)
    if media_url is not None:
        return _absolute_url(media_url, request)

    if not post.cover_image:
        return None

    path = reverse("blog:post_og_image", args=[post.slug])
    return _absolute_url(path, request)
