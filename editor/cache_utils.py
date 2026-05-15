"""Invalidate full-page cache for public post list/detail views (django-redis)."""

from __future__ import annotations

from blog.cache_utils import invalidate_blog_public_pages_cache


def invalidate_editor_public_pages_cache() -> None:
    """Back-compat alias while public pages live in the blog app."""
    invalidate_blog_public_pages_cache()
