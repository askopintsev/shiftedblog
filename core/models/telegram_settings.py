"""Telegram-specific settings linked to the Telegram ``Network`` row."""

from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import models

from core.models.network import NETWORK_SLUG_TELEGRAM, Network


class TelegramNetworkSettings(models.Model):
    """Per-network Telegram publish options (story media, continuation label)."""

    network = models.OneToOneField(
        Network,
        on_delete=models.CASCADE,
        related_name="telegram_settings",
        limit_choices_to={"slug": NETWORK_SLUG_TELEGRAM},
    )
    story_fallback_image = models.ImageField(
        upload_to="network/telegram/",
        blank=True,
        null=True,
        help_text=(
            "Default Telegram story background when a post has no cover or "
            "inline images."
        ),
    )
    post_continuation_text = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text=(
            "Prefix for continuation chunks in multi-part Telegram posts. "
            "Leave empty to use the built-in default."
        ),
    )

    class Meta:
        app_label = "core"
        db_table = "core_telegramnetworksettings"

    def __str__(self) -> str:
        return f"Telegram settings ({self.network.slug})"

    def clean(self) -> None:
        super().clean()
        network_pk = getattr(self, "network_id", None)
        if network_pk and self.network.slug != NETWORK_SLUG_TELEGRAM:
            raise ValidationError(
                {
                    "network": (
                        "Telegram settings can only be linked to the Telegram network."
                    ),
                },
            )

    def effective_continuation_prefix(self) -> str | None:
        text = (self.post_continuation_text or "").strip()
        return text or None


def get_telegram_network_settings() -> TelegramNetworkSettings | None:
    """Return Telegram settings row, or ``None`` if not configured."""
    return (
        TelegramNetworkSettings.objects.select_related("network")
        .filter(network__slug=NETWORK_SLUG_TELEGRAM)
        .first()
    )


def post_continuation_prefix() -> str | None:
    """Configured continuation prefix, or ``None`` for the built-in default."""
    settings = get_telegram_network_settings()
    if settings is None:
        return None
    return settings.effective_continuation_prefix()
