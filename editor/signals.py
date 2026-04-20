"""Cache invalidation hooks for public post pages."""

from __future__ import annotations

from django.db.models.signals import m2m_changed, post_delete, post_save
from django.dispatch import receiver

from editor.cache_utils import invalidate_editor_public_pages_cache
from editor.models import (
    Category,
    Post,
    PostGalleryImage,
    PostSeries,
    PostSlugRedirect,
)


@receiver(post_save, sender=Post)
@receiver(post_delete, sender=Post)
def _invalidate_on_post_change(sender, instance, **kwargs) -> None:
    invalidate_editor_public_pages_cache()


@receiver(post_save, sender=PostGalleryImage)
@receiver(post_delete, sender=PostGalleryImage)
def _invalidate_on_gallery_change(sender, instance, **kwargs) -> None:
    invalidate_editor_public_pages_cache()


@receiver(post_save, sender=Category)
@receiver(post_delete, sender=Category)
def _invalidate_on_category_change(sender, **kwargs) -> None:
    invalidate_editor_public_pages_cache()


@receiver(post_save, sender=PostSeries)
@receiver(post_delete, sender=PostSeries)
def _invalidate_on_post_series_change(sender, **kwargs) -> None:
    invalidate_editor_public_pages_cache()


@receiver(post_save, sender=PostSlugRedirect)
@receiver(post_delete, sender=PostSlugRedirect)
def _invalidate_on_slug_redirect_change(sender, **kwargs) -> None:
    invalidate_editor_public_pages_cache()


@receiver(m2m_changed, sender=Post.tags.through)
def _invalidate_on_post_tags_change(sender, instance, action, **kwargs) -> None:
    if action not in ("post_add", "post_remove", "post_clear"):
        return
    if isinstance(instance, Post):
        invalidate_editor_public_pages_cache()
