"""Build canonical public URL for a blog post."""

from __future__ import annotations

from django.conf import settings
from django.urls import reverse

from editor.models import Post


def public_post_url(post: Post) -> str:
    base = getattr(settings, "SITE_URL", "") or ""
    base = base.rstrip("/")
    path = reverse("blog:post_detail", args=[post.slug])
    if not path.startswith("/"):
        path = "/" + path
    return base + path
