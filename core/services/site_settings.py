"""Helpers for SiteSettings with environment fallbacks."""

from __future__ import annotations

from dataclasses import dataclass

from django.conf import settings
from django.core.mail import get_connection

from core.models.site_settings import SiteSettings, get_site_settings


@dataclass(frozen=True, slots=True)
class EffectiveEmailConfig:
    """Resolved outbound email settings for send_mail / get_connection."""

    admin_email: str
    default_from_email: str
    host: str
    port: int
    username: str
    password: str
    use_tls: bool
    use_ssl: bool


class SiteSettingsService:
    """Read SiteSettings with env fallbacks for bootstrapping."""

    @staticmethod
    def get() -> SiteSettings:
        return get_site_settings()

    @classmethod
    def effective_twitter_site(cls) -> str | None:
        # SiteSettings (admin) wins; env / override_settings is bootstrap fallback.
        site = cls.get().normalized_twitter_site()
        if site:
            return site
        env_site = (getattr(settings, "TWITTER_SITE", "") or "").strip()
        if env_site and not env_site.startswith("@"):
            env_site = f"@{env_site.lstrip('@')}"
        return env_site or None

    @classmethod
    def telegram_use_rich_messages(cls) -> bool:
        # Env / override_settings can force-enable; SiteSettings can enable in admin.
        if getattr(settings, "TELEGRAM_USE_RICH_MESSAGES", False):
            return True
        return bool(cls.get().telegram_use_rich_messages)

    @classmethod
    def text_quality_checker_enabled(cls) -> bool:
        if getattr(settings, "TEXT_QUALITY_PY_CHECKER_ENABLED", False):
            return True
        return bool(cls.get().text_quality_checker_enabled)

    @classmethod
    def effective_email(cls) -> EffectiveEmailConfig:
        row = cls.get()
        return EffectiveEmailConfig(
            admin_email=(row.admin_email or getattr(settings, "ADMIN_EMAIL", "") or ""),
            default_from_email=(
                row.default_from_email
                or getattr(settings, "DEFAULT_FROM_EMAIL", "")
                or "noreply@localhost"
            ),
            host=(row.email_host or getattr(settings, "EMAIL_HOST", "") or ""),
            port=int(row.email_port or getattr(settings, "EMAIL_PORT", 587) or 587),
            username=(
                row.email_host_user or getattr(settings, "EMAIL_HOST_USER", "") or ""
            ),
            password=getattr(settings, "EMAIL_HOST_PASSWORD", "") or "",
            use_tls=bool(row.email_use_tls)
            if row.email_host
            else bool(getattr(settings, "EMAIL_USE_TLS", True)),
            use_ssl=bool(row.email_use_ssl)
            if row.email_host
            else bool(getattr(settings, "EMAIL_USE_SSL", False)),
        )

    @classmethod
    def get_email_connection(cls, fail_silently: bool = False):
        """SMTP connection using SiteSettings host fields; password from env."""
        cfg = cls.effective_email()
        if not cfg.host:
            return get_connection(fail_silently=fail_silently)
        return get_connection(
            host=cfg.host,
            port=cfg.port,
            username=cfg.username,
            password=cfg.password,
            use_tls=cfg.use_tls,
            use_ssl=cfg.use_ssl,
            fail_silently=fail_silently,
        )
