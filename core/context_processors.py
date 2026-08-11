"""Template context processors."""

from __future__ import annotations

from django.http import HttpRequest

from core.security_warnings import collect_secrets_rotation_warnings
from core.services.site_settings import SiteSettingsService


def admin_security_warnings(request: HttpRequest) -> dict[str, list[str]]:
    """Expose secrets rotation warnings on Django admin pages only."""
    from django.conf import settings

    path = request.path or ""
    admin_path = f"/{settings.ADMIN_URL}/"
    if not path.startswith(admin_path):
        return {"admin_security_warnings": []}

    user = getattr(request, "user", None)
    if not user or not getattr(user, "is_authenticated", False):
        return {"admin_security_warnings": []}
    if not getattr(user, "is_staff", False):
        return {"admin_security_warnings": []}

    return {"admin_security_warnings": collect_secrets_rotation_warnings()}


def social_meta(request: HttpRequest) -> dict[str, str | None]:
    """Expose X/Twitter account handle for ``twitter:site`` meta tags."""
    return {"twitter_site": SiteSettingsService.effective_twitter_site()}


def site_settings(request: HttpRequest) -> dict:
    """Expose SiteSettings singleton to public templates."""
    return {"site_settings": SiteSettingsService.get()}
