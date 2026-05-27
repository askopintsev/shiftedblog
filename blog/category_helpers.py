from __future__ import annotations

from django.http import HttpResponsePermanentRedirect
from django.urls import reverse

from editor.models import Category


def resolve_category_for_list(
    category_slug: str | None,
) -> tuple[Category | None, HttpResponsePermanentRedirect | None]:
    """Resolve category by canonical slug; 301 from legacy URL segments."""
    token = (category_slug or "").strip()
    if not token:
        return None, None

    category = Category.get_by_url_slug(token)
    if category is not None:
        return category, None

    for candidate in Category.objects.all().order_by("pk"):
        legacy = candidate.legacy_url_segment()
        if legacy == token and candidate.slug != token:
            url = reverse("blog:post_list_by_category", args=[candidate.slug])
            return None, HttpResponsePermanentRedirect(url)

    return None, None
