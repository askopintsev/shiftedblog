"""Move Telegram story fallback to TelegramNetworkSettings."""

from __future__ import annotations

from django.db import migrations, models


def copy_story_fallback_to_telegram_settings(apps, schema_editor) -> None:
    Network = apps.get_model("core", "Network")
    TelegramNetworkSettings = apps.get_model("core", "TelegramNetworkSettings")
    for net in Network.objects.filter(slug="telegram"):
        TelegramNetworkSettings.objects.create(
            network_id=net.pk,
            story_fallback_image=net.story_fallback_image,
        )


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0006_network_story_fallback_image"),
    ]

    operations = [
        migrations.CreateModel(
            name="TelegramNetworkSettings",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "story_fallback_image",
                    models.ImageField(
                        blank=True,
                        help_text=(
                            "Default Telegram story background when a post has no "
                            "cover or inline images."
                        ),
                        null=True,
                        upload_to="network/telegram/",
                    ),
                ),
                (
                    "post_continuation_text",
                    models.CharField(
                        blank=True,
                        help_text=(
                            "Prefix for continuation chunks in multi-part Telegram "
                            "posts. Leave empty to use the built-in default."
                        ),
                        max_length=255,
                        null=True,
                    ),
                ),
                (
                    "network",
                    models.OneToOneField(
                        limit_choices_to={"slug": "telegram"},
                        on_delete=models.deletion.CASCADE,
                        related_name="telegram_settings",
                        to="core.network",
                    ),
                ),
            ],
            options={
                "db_table": "core_telegramnetworksettings",
            },
        ),
        migrations.RunPython(
            copy_story_fallback_to_telegram_settings,
            migrations.RunPython.noop,
        ),
        migrations.RemoveField(
            model_name="network",
            name="story_fallback_image",
        ),
    ]
