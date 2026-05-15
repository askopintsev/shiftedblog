from django.db import migrations
from django.utils import timezone


def seed_site_publications(apps, schema_editor):
    post_model = apps.get_model("editor", "Post")
    site_publication_model = apps.get_model("blog", "SitePublication")

    for post in post_model.objects.filter(status="published").iterator():
        site_publication_model.objects.get_or_create(
            post=post,
            defaults={"published_at": post.published or timezone.now()},
        )


def noop_reverse(apps, schema_editor):
    return None


class Migration(migrations.Migration):
    dependencies = [
        ("blog", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_site_publications, noop_reverse),
    ]
