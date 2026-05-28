# Generated manually for Telegram story fallback image on Network.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0005_alter_credential_encrypted_payload"),
    ]

    operations = [
        migrations.AddField(
            model_name="network",
            name="story_fallback_image",
            field=models.ImageField(
                blank=True,
                help_text=(
                    "Default Telegram story background when a post has no cover "
                    "or inline images."
                ),
                null=True,
                upload_to="network/telegram/",
            ),
        ),
    ]
