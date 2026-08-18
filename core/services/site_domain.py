"""Keep django.contrib.sites in sync with SITE_URL."""

from __future__ import annotations

from urllib.parse import urlparse

from django.conf import settings
from django.contrib.sites.models import Site


def hostname_from_site_url(site_url: str) -> str:
    parsed = urlparse((site_url or "").strip())
    return (parsed.hostname or "").lower()


def cookie_parent_domain(hostname: str) -> str:
    host = (hostname or "").lower().strip(".")
    if host.startswith("www."):
        return host[4:]
    return host


def sync_sites_framework_from_site_url(*, site_url: str | None = None) -> Site:
    """Set Site.domain / Site.name from SITE_URL (pk = SITE_ID)."""
    url = (
        site_url if site_url is not None else getattr(settings, "SITE_URL", "")
    ) or ""
    host = hostname_from_site_url(url)
    if not host:
        raise ValueError("SITE_URL is missing or has no hostname")
    site_id = getattr(settings, "SITE_ID", 1)
    site, _created = Site.objects.update_or_create(
        pk=site_id,
        defaults={"domain": host, "name": host},
    )
    return site
