"""Invalidate full-page cache for public post list/detail views (django-redis)."""

from __future__ import annotations

import logging

from django.core.cache import caches

logger = logging.getLogger(__name__)


def invalidate_editor_public_pages_cache() -> None:
    """Drop cached HTML for ``post_list`` / ``post_detail`` (pattern purge)."""
    cache = caches["default"]
    delete_pattern = getattr(cache, "delete_pattern", None)
    if delete_pattern is None:
        logger.debug("Cache backend has no delete_pattern; skip editor page purge")
        return
    try:
        delete_pattern("*editor.post_list*")
        delete_pattern("*editor.post_detail*")
    except Exception:
        logger.exception("Failed to invalidate editor public page cache")
