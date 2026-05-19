"""Create PostLink rows for site network for all existing site publications."""

from __future__ import annotations

from django.conf import settings
from django.db import migrations
from django.urls import reverse


def seed_site_postlinks(apps, schema_editor) -> None:
    SitePublication = apps.get_model("blog", "SitePublication")
    PostLink = apps.get_model("sender", "PostLink")
    Network = apps.get_model("core", "Network")
    Site = apps.get_model("sites", "Site")

    site_net = Network.objects.filter(slug="site").first()
    if site_net is None:
        return

    base = (getattr(settings, "SITE_URL", "") or "").rstrip("/")
    if not base:
        try:
            site_rec = Site.objects.get(pk=getattr(settings, "SITE_ID", 1))
            base = f"https://{site_rec.domain}".rstrip("/")
        except Site.DoesNotExist:
            base = ""

    for sp in SitePublication.objects.select_related("post").iterator():
        post = sp.post
        path = reverse("blog:post_detail", args=[post.slug])
        if not path.startswith("/"):
            path = "/" + path
        url = (base + path) if base else f"https://example.com{path}"
        PostLink.objects.update_or_create(
            post=post,
            network=site_net,
            defaults={"url": url},
        )


def noop_reverse(apps, schema_editor) -> None:
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("sender", "0001_initial"),
        ("blog", "0003_rename_blog_sitepub_pubat_idx_blog_sitepu_publish_3e0eea_idx"),
        ("sites", "0002_alter_domain_unique"),
    ]

    operations = [
        migrations.RunPython(seed_site_postlinks, noop_reverse),
    ]
