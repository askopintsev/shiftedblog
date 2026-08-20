from editor.models import Post


def public_posts_queryset():
    """Posts visible on the anonymous public blog (requires SitePublication)."""
    return Post.objects.filter(
        status="published",
        site_publication__isnull=False,
    )


def feed_posts_queryset():
    """Staff lenta feed: all published posts regardless of site channel."""
    return Post.objects.filter(status="published")
