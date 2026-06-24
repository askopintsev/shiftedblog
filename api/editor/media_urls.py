"""Media URL helpers for the editor API."""

from __future__ import annotations

from django.db.models.fields.files import FieldFile


def relative_media_path(path: str) -> str:
    """Normalize storage or ``MEDIA_URL`` paths to ``/media/...``."""
    if not path:
        return ""
    if path.startswith(("http://", "https://")):
        from urllib.parse import urlparse

        return urlparse(path).path
    if not path.startswith("/"):
        return f"/{path.lstrip('/')}"
    return path


def relative_media_url(file_field: FieldFile | None) -> str:
    """Return a same-origin ``/media/...`` path for editor UI assets."""
    if not file_field:
        return ""
    return relative_media_path(file_field.url)
