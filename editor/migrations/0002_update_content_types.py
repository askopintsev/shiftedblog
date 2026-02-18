# Update django_content_type rows from blog to editor for all editor models.
# This automatically fixes taggit, admin_log, permissions, and any other
# table that references content types.

from django.db import migrations


def forwards(apps, schema_editor):
    ContentType = apps.get_model("contenttypes", "ContentType")
    model_names = ["category", "series", "post", "postseries"]
    ContentType.objects.filter(app_label="blog", model__in=model_names).update(
        app_label="editor"
    )


def backwards(apps, schema_editor):
    ContentType = apps.get_model("contenttypes", "ContentType")
    model_names = ["category", "series", "post", "postseries"]
    ContentType.objects.filter(app_label="editor", model__in=model_names).update(
        app_label="blog"
    )


class Migration(migrations.Migration):

    dependencies = [
        ("editor", "0001_initial"),
        ("contenttypes", "0002_remove_content_type_name"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
