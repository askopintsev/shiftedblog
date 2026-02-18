# Add UUID field to Post for secret draft preview URL

import uuid

from django.db import migrations, models


def fill_uuids(apps, schema_editor):
    Post = apps.get_model("editor", "Post")
    for post in Post.objects.all():
        post.uuid = uuid.uuid4()
        post.save(update_fields=["uuid"])


class Migration(migrations.Migration):
    dependencies = [
        ("editor", "0005_postgalleryimage_gallery_key"),
    ]

    operations = [
        migrations.AddField(
            model_name="post",
            name="uuid",
            field=models.UUIDField(
                null=True,
                unique=True,
                help_text="Secret UUID for draft preview URL.",
            ),
        ),
        migrations.RunPython(fill_uuids, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="post",
            name="uuid",
            field=models.UUIDField(
                default=uuid.uuid4,
                editable=False,
                help_text="Secret UUID for draft preview URL.",
                unique=True,
            ),
        ),
    ]
