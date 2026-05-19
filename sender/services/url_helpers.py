"""Build canonical public URL for a blog post."""

from __future__ import annotations

from django.conf import settings
from django.urls import reverse

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
