"""Fernet helpers for encrypted credential storage. Key from env only."""

from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


def get_fernet() -> Fernet:
    key_raw = getattr(settings, "CREDENTIALS_ENCRYPTION_KEY", None) or ""
    key_raw = key_raw.strip()
    if not key_raw:
        raise ImproperlyConfigured(
            "CREDENTIALS_ENCRYPTION_KEY is not set. Generate with:\n"
            'python -c "from cryptography.fernet import Fernet; '
            "print(Fernet.generate_key().decode())\"'"
        )
    try:
        return Fernet(key_raw.encode("ascii"))
    except (ValueError, TypeError) as exc:
        raise ImproperlyConfigured(
            "CREDENTIALS_ENCRYPTION_KEY must be a valid Fernet key (url-safe base64)."
        ) from exc


def encrypt_bytes(plain: bytes) -> str:
    return get_fernet().encrypt(plain).decode("ascii")


def decrypt_bytes(token: str) -> bytes:
    if not token:
        return b""
    try:
        return get_fernet().decrypt(token.encode("ascii"))
    except InvalidToken as exc:
        raise ValueError(
            "Could not decrypt credential payload (wrong key or corrupt data)."
        ) from exc


def encrypt_text(plain: str) -> str:
    if not plain:
        return ""
    return encrypt_bytes(plain.encode("utf-8"))


def decrypt_text(token: str) -> str:
    if not token:
        return ""
    return decrypt_bytes(token).decode("utf-8")
