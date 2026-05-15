# pyright: reportAttributeAccessIssue=false

from django.contrib.sitemaps import Sitemap

from blog.querysets import public_posts_queryset


class PostSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.9

    def items(self):
        return public_posts_queryset()

    def lastmod(self, obj):
        return obj.updated
