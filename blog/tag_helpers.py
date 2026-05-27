from __future__ import annotations

from django.http import HttpResponsePermanentRedirect
from django.urls import reverse
from django.utils.text import slugify
from taggit.models import Tag
from unidecode import unidecode


def tag_slug_from_name(name: str, *, suffix: int | None = None) -> str:
    """Latin tag slug; matches taggit ``TAGGIT_STRIP_UNICODE_WHEN_SLUGIFYING``."""
    slug = slugify(unidecode(name or ""))
    if suffix is not None:
        slug = f"{slug}_{suffix}"
    return slug


def resolve_tag_for_list(
    tag_slug: str | None,
) -> tuple[Tag | None, HttpResponsePermanentRedirect | None]:
    """Resolve tag by canonical slug; 301 from legacy Unicode slug URLs."""
    token = (tag_slug or "").strip()
    if not token:
        return None, None

    tag = Tag.objects.filter(slug=token).first()
    if tag is not None:
        return tag, None

    canonical = tag_slug_from_name(token)
    if canonical and canonical != token:
        tag = Tag.objects.filter(slug=canonical).first()
        if tag is not None:
            url = reverse("blog:post_list_by_tag", args=[tag.slug])
            return tag, HttpResponsePermanentRedirect(url)

    return None, None
