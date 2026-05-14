from editor.models import Post


def public_posts_queryset():
    return Post.objects.filter(
        status="published",
        site_publication__isnull=False,
    )
