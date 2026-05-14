"""Invalidate full-page cache for public blog list/detail views."""

from __future__ import annotations

import logging

from django.core.cache import caches

logger = logging.getLogger(__name__)


def invalidate_blog_public_pages_cache() -> None:
    cache = caches["default"]
    delete_pattern = getattr(cache, "delete_pattern", None)
    if delete_pattern is None:
        logger.debug("Cache backend has no delete_pattern; skip blog page purge")
        return
    try:
        delete_pattern("*blog.post_list*")
        delete_pattern("*blog.post_detail*")
        delete_pattern("*editor.post_list*")
        delete_pattern("*editor.post_detail*")
    except Exception:
        logger.exception("Failed to invalidate blog public page cache")
