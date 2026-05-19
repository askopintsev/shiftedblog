"""Custom model fields."""

from __future__ import annotations

from typing import Any

from django.core.exceptions import ValidationError
from django.db import models

from core import crypto


class FernetEncryptedTextField(models.TextField):
    """Stores Fernet ciphertext in the database; exposes plaintext in Python."""

    description = "Fernet-encrypted text"

    def from_db_value(self, value: str | None, expression: Any, connection: Any) -> str:
        if value is None or value == "":
            return ""
        try:
            return crypto.decrypt_text(value)
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc

    def to_python(self, value: Any) -> str:
        if isinstance(value, str) or value is None:
            v = value or ""
            return v
        return str(value)

    def get_prep_value(self, value: Any) -> str:
        if value is None or value == "":
            return ""
        text = value if isinstance(value, str) else str(value)
        return crypto.encrypt_text(text)
