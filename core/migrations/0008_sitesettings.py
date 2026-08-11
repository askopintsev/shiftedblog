from __future__ import annotations

from django.db import migrations, models


def seed_default_site_settings(apps, schema_editor):
    SiteSettings = apps.get_model("core", "SiteSettings")
    SiteSettings.objects.update_or_create(
        pk=1,
        defaults={
            "site_name": "Shifted Stuff",
            "tagline": "",
            # Cyrillic seed for the upstream public site branding.
            "footer_text": (  # noqa: RUF001
                "Автор: Александр Скопинцев\n"  # noqa: RUF001
                "Все материалы лицензированы под CC BY-NC-ND 4.0."  # noqa: RUF001
            ),
            "telegram_url": "https://t.me/shifted_stuff",
            "github_url": "https://github.com/askopintsev",
            "habr_url": "https://career.habr.com/shifter",
            "twitter_site": "@shifted_stuff",
            "contact_email": "askopintsev@hotmail.com",
            "default_from_email": "",
            "admin_email": "",
            "email_host": "",
            "email_port": 587,
            "email_host_user": "",
            "email_use_tls": True,
            "email_use_ssl": False,
            "telegram_use_rich_messages": False,
            "text_quality_checker_enabled": False,
        },
    )


def unseed_site_settings(apps, schema_editor):
    SiteSettings = apps.get_model("core", "SiteSettings")
    SiteSettings.objects.filter(pk=1).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0007_telegramnetworksettings"),
    ]

    operations = [
        migrations.CreateModel(
            name="SiteSettings",
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
                ("site_name", models.CharField(default="ShiftedBlog", max_length=120)),
                ("tagline", models.CharField(blank=True, default="", max_length=255)),
                (
                    "footer_text",
                    models.TextField(
                        blank=True,
                        default="",
                        help_text=(
                            "Extra footer lines under the copyright "
                            "(plain text; use new lines)."
                        ),
                    ),
                ),
                ("telegram_url", models.URLField(blank=True, default="")),
                ("github_url", models.URLField(blank=True, default="")),
                ("habr_url", models.URLField(blank=True, default="")),
                (
                    "twitter_site",
                    models.CharField(
                        blank=True,
                        default="",
                        help_text=(
                            "X/Twitter handle for twitter:site meta "
                            "(with or without @)."
                        ),
                        max_length=64,
                    ),
                ),
                (
                    "contact_email",
                    models.EmailField(blank=True, default="", max_length=254),
                ),
                (
                    "default_from_email",
                    models.EmailField(blank=True, default="", max_length=254),
                ),
                (
                    "admin_email",
                    models.EmailField(blank=True, default="", max_length=254),
                ),
                (
                    "email_host",
                    models.CharField(blank=True, default="", max_length=255),
                ),
                ("email_port", models.PositiveIntegerField(default=587)),
                (
                    "email_host_user",
                    models.CharField(blank=True, default="", max_length=255),
                ),
                ("email_use_tls", models.BooleanField(default=True)),
                ("email_use_ssl", models.BooleanField(default=False)),
                (
                    "telegram_use_rich_messages",
                    models.BooleanField(
                        default=False,
                        help_text=(
                            "Prefer Telegram Bot API rich messages when available."
                        ),
                    ),
                ),
                (
                    "text_quality_checker_enabled",
                    models.BooleanField(
                        default=False,
                        help_text=(
                            "Enable optional local Python text-quality checker "
                            "in admin."
                        ),
                    ),
                ),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Site settings",
                "verbose_name_plural": "Site settings",
                "db_table": "core_sitesettings",
            },
        ),
        migrations.RunPython(seed_default_site_settings, unseed_site_settings),
    ]
