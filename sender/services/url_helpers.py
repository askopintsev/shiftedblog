"""Build canonical public URL for a blog post."""

from __future__ import annotations

from django.conf import settings
from django.http import HttpRequest
from django.urls import reverse

from core.models.network import NETWORK_SLUG_SITE
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
    if link and (link.url or "").strip():
        return link.url.strip()
    return None


def post_og_image_absolute_url(
    post: Post,
    request: HttpRequest | None = None,
) -> str | None:
    """Absolute JPEG URL for social link previews (Telegram, X/Twitter, etc.)."""
    if not post.cover_image:
        return None
    path = reverse("blog:post_og_image", args=[post.slug])
    if request is not None:
        return request.build_absolute_uri(path)
    base = getattr(settings, "SITE_URL", "") or ""
    base = base.rstrip("/")
    if not path.startswith("/"):
        path = "/" + path
    return base + path
