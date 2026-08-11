"""Sidebar recommendations for post detail (similar + newest)."""

# pyright: reportAttributeAccessIssue=false

from __future__ import annotations

from django.db.models import Count

from blog.querysets import public_posts_queryset
from editor.models import Post, Series


def post_is_public_on_site(post: Post | None) -> bool:
    if post is None or post.status != "published":
        return False
    return hasattr(post, "site_publication")


def series_navigation(
    post: Post,
) -> tuple[Series | None, Post | None, Post | None]:
    """Return ``(series, previous_on_site, next_on_site)`` for *post*."""
    previous_post = None
    next_post = None
    current_series = None
    post_series = post.post_series.filter(order_position__isnull=False).first()
    if not post_series:
        return None, None, None
    current_series = post_series.series
    previous_post = post.get_previous_post_in_series(current_series)
    if not post_is_public_on_site(previous_post):
        previous_post = None
    next_post = post.get_next_post_in_series(current_series)
    if not post_is_public_on_site(next_post):
        next_post = None
    return current_series, previous_post, next_post


def similar_and_newest_posts(
    post: Post,
    *,
    excluded_ids: list[int] | None = None,
    similar_limit: int = 3,
    total_limit: int = 5,
) -> tuple[list[Post], list[Post]]:
    """On-site published posts only (excludes drafts and off-site published)."""
    excluded = set(excluded_ids or [])
    excluded.add(post.id)
    post_tags_ids = list(post.tags.values_list("id", flat=True))

    similar_qs = public_posts_queryset().exclude(id__in=excluded)
    if post_tags_ids:
        similar_qs = similar_qs.filter(tags__in=post_tags_ids)
        similar_posts = list(
            similar_qs.annotate(same_tags=Count("tags")).order_by(
                "-same_tags",
                "-published",
            )[:similar_limit],
        )
    else:
        similar_posts = []

    similar_ids = {item.id for item in similar_posts}
    newest_limit = max(0, total_limit - len(similar_posts))
    newest_posts = list(
        public_posts_queryset()
        .exclude(id__in=excluded | similar_ids)
        .order_by("-published")[:newest_limit],
    )
    return similar_posts, newest_posts
