"""Publish post to the public site via ``SitePublication``."""

from __future__ import annotations

from django.utils import timezone

from blog.models import SitePublication
from editor.models import Post
from sender.services.dto import PublishResult
from sender.services.url_helpers import public_post_url


def publish_to_site(post: Post) -> PublishResult:
    SitePublication.objects.update_or_create(
        post=post,
        defaults={"published_at": post.published or timezone.now()},
    )
    return PublishResult(ok=True, url=public_post_url(post))
