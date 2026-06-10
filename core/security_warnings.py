"""Admin security warnings (secrets rotation reminders)."""

from __future__ import annotations

from datetime import date, datetime, timedelta

from django.conf import settings
from django.utils import timezone

from core.models import Credential


def _parse_rotation_date(raw: str) -> date | None:
    value = (raw or "").strip()
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def _age_days(since: date, *, today: date) -> int:
    return (today - since).days


def collect_secrets_rotation_warnings(*, today: date | None = None) -> list[str]:
    """Return human-readable admin warnings for aged secrets."""
    if today is None:
        today = timezone.localdate()

    max_age = getattr(settings, "SECRETS_ROTATION_MAX_AGE_DAYS", 90)
    warnings: list[str] = []

    secret_rotated = _parse_rotation_date(
        getattr(settings, "SECRET_KEY_ROTATED_AT", "")
    )
    if secret_rotated is None:
        warnings.append(
            "SECRET_KEY rotation date is not set. Add SECRET_KEY_ROTATED_AT "
            "(YYYY-MM-DD) in Doppler after rotating."
        )
    elif _age_days(secret_rotated, today=today) >= max_age:
        warnings.append(
            f"SECRET_KEY was last rotated {_age_days(secret_rotated, today=today)} "
            f"days ago (threshold: {max_age}). Rotate in Doppler and redeploy."
        )

    cred_key_rotated = _parse_rotation_date(
        getattr(settings, "CREDENTIALS_ENCRYPTION_KEY_ROTATED_AT", "")
    )
    if cred_key_rotated is None:
        warnings.append(
            "CREDENTIALS_ENCRYPTION_KEY rotation date is not set. "
            "Add CREDENTIALS_ENCRYPTION_KEY_ROTATED_AT in Doppler."
        )
    elif _age_days(cred_key_rotated, today=today) >= max_age:
        warnings.append(
            "CREDENTIALS_ENCRYPTION_KEY was last rotated "
            f"{_age_days(cred_key_rotated, today=today)} days ago "
            f"(threshold: {max_age}). Plan re-encryption after key rotation."
        )

    threshold = today - timedelta(days=max_age)
    stale_credentials = Credential.objects.filter(updated_at__date__lt=threshold)
    for credential in stale_credentials.order_by("updated_at")[:5]:
        warnings.append(
            f"Credential '{credential}' was last updated on "
            f"{credential.updated_at.date().isoformat()} "
            f"(>{max_age} days). Review and rotate stored secrets."
        )

    extra = stale_credentials.count() - 5
    if extra > 0:
        warnings.append(
            f"{extra} more credential(s) exceed the rotation age threshold."
        )

    return warnings
