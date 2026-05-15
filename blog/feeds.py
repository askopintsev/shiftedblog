from django.contrib.syndication.views import Feed
from django.utils.feedgenerator import Atom1Feed

from blog.querysets import public_posts_queryset


class LatestPostsFeed(Feed):
    title = "Shifted Stuff"
    link = "/"
    description = "Latest published posts."
    feed_type = Atom1Feed

    def items(self):
        return public_posts_queryset().order_by("-published")[:20]

    def item_title(self, item):
        return item.title

    def item_description(self, item):
        return item.short_description or ""

    def item_link(self, item):
        return item.get_absolute_url()
