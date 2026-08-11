"""Singleton site branding / operator settings (admin-editable)."""

from __future__ import annotations

from django.core.cache import cache
from django.db import models

SITE_SETTINGS_CACHE_KEY = "core.site_settings.solo"
SITE_SETTINGS_CACHE_TTL = 60
SITE_SETTINGS_PK = 1


class SiteSettings(models.Model):
    """Single-row site configuration for self-host operators."""

    site_name = models.CharField(max_length=120, default="ShiftedBlog")
    tagline = models.CharField(max_length=255, blank=True, default="")
    footer_text = models.TextField(
        blank=True,
        default="",
        help_text="Extra footer lines under the copyright (plain text; use new lines).",
    )
    telegram_url = models.URLField(blank=True, default="")
    github_url = models.URLField(blank=True, default="")
    habr_url = models.URLField(blank=True, default="")
    twitter_site = models.CharField(
        max_length=64,
        blank=True,
        default="",
        help_text="X/Twitter handle for twitter:site meta (with or without @).",
    )
    contact_email = models.EmailField(blank=True, default="")
    default_from_email = models.EmailField(blank=True, default="")
    admin_email = models.EmailField(blank=True, default="")
    email_host = models.CharField(max_length=255, blank=True, default="")
    email_port = models.PositiveIntegerField(default=587)
    email_host_user = models.CharField(max_length=255, blank=True, default="")
    email_use_tls = models.BooleanField(default=True)
    email_use_ssl = models.BooleanField(default=False)
    telegram_use_rich_messages = models.BooleanField(
        default=False,
        help_text="Prefer Telegram Bot API rich messages when available.",
    )
    text_quality_checker_enabled = models.BooleanField(
        default=False,
        help_text="Enable optional local Python text-quality checker in admin.",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "core"
        db_table = "core_sitesettings"
        verbose_name = "Site settings"
        verbose_name_plural = "Site settings"

    def __str__(self) -> str:
        return self.site_name or "Site settings"

    def save(self, *args, **kwargs):
        self.pk = SITE_SETTINGS_PK
        super().save(*args, **kwargs)
        cache.delete(SITE_SETTINGS_CACHE_KEY)

    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)
        cache.delete(SITE_SETTINGS_CACHE_KEY)

    def normalized_twitter_site(self) -> str:
        site = (self.twitter_site or "").strip()
        if site and not site.startswith("@"):
            site = f"@{site.lstrip('@')}"
        return site


def get_site_settings() -> SiteSettings:
    """Return the singleton row, creating defaults if missing."""
    cached = cache.get(SITE_SETTINGS_CACHE_KEY)
    if isinstance(cached, SiteSettings):
        return cached

    obj, _created = SiteSettings.objects.get_or_create(pk=SITE_SETTINGS_PK)
    cache.set(SITE_SETTINGS_CACHE_KEY, obj, SITE_SETTINGS_CACHE_TTL)
    return obj
