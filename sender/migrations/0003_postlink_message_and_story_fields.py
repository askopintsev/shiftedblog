"""PostLink message/story fields and url rename."""

from __future__ import annotations

import re

from django.db import migrations, models

_TME_MESSAGE_RE = re.compile(r"https?://t\.me/[^/]+/(\d+)/?$")


def backfill_message_ids(apps, schema_editor) -> None:
    PostLink = apps.get_model("sender", "PostLink")
    for link in PostLink.objects.exclude(message_url="").iterator():
        if link.message_id:
            continue
        match = _TME_MESSAGE_RE.match((link.message_url or "").strip())
        if match:
            link.message_id = int(match.group(1))
            link.save(update_fields=["message_id"])


class Migration(migrations.Migration):

    dependencies = [
        ("sender", "0002_seed_site_postlinks_from_publications"),
    ]

    operations = [
        migrations.RenameField(
            model_name="postlink",
            old_name="url",
            new_name="message_url",
        ),
        migrations.AddField(
            model_name="postlink",
            name="message_id",
            field=models.PositiveBigIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="postlink",
            name="story_id",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="postlink",
            name="story_url",
            field=models.URLField(blank=True, default="", max_length=2048),
        ),
        migrations.RunPython(backfill_message_ids, migrations.RunPython.noop),
    ]
