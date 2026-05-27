from __future__ import annotations

from editor.models import Category

# Primary nav category slugs (order preserved). Set ``Category.slug`` in admin.
NAV_CATEGORY_SLUGS: tuple[str, ...] = ("blog", "projects")


def nav_categories(request):
    by_slug = {
        category.slug: category
        for category in Category.objects.filter(slug__in=NAV_CATEGORY_SLUGS)
    }
    return {
        "nav_categories": [
            by_slug[slug] for slug in NAV_CATEGORY_SLUGS if slug in by_slug
        ],
    }
