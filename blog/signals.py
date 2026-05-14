from __future__ import annotations

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from blog.cache_utils import invalidate_blog_public_pages_cache
from blog.models import SitePublication


@receiver(post_save, sender=SitePublication)
@receiver(post_delete, sender=SitePublication)
def _invalidate_on_site_publication_change(sender, **kwargs) -> None:
    invalidate_blog_public_pages_cache()
