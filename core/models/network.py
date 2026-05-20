"""Networks and encrypted credentials for outbound integrations."""

from __future__ import annotations

import json
from typing import Any, ClassVar

from django.db import models
from django.db.models import BaseConstraint

from core import crypto
from core.fields import FernetEncryptedTextField

# Convention for publisher registry (extend for new channels).
NETWORK_SLUG_SITE = "site"
NETWORK_SLUG_TELEGRAM = "telegram"


class Network(models.Model):
    """Logical destination channel (site, telegram, …)."""

    slug = models.SlugField(
        max_length=64,
        unique=True,
        db_index=True,
        help_text="Stable id, e.g. site, telegram.",
    )
    name = models.CharField(max_length=120)

    class Meta:
        app_label = "core"
        db_table = "core_network"
        ordering: ClassVar[list[str]] = ["name"]

    def __str__(self) -> str:
        return self.name


class Credential(models.Model):
    """Encrypted secrets for a network (e.g. Telegram bot token + chat id as JSON)."""

    network = models.ForeignKey(
        Network,
        on_delete=models.CASCADE,
        related_name="credentials",
    )
    label = models.CharField(
        max_length=120,
        blank=True,
        default="",
        help_text='Optional, e.g. "production".',
    )
    encrypted_payload = FernetEncryptedTextField(
        blank=True,
        default="",
        help_text=(
            'Encrypted JSON, e.g. {"bot_token": "…", "channel_name": "mychannel"} '
            '(optional "chat_id" for numeric targets).'
        ),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "core"
        db_table = "core_credential"
        constraints: ClassVar[list[BaseConstraint]] = [
            models.UniqueConstraint(
                fields=["network", "label"],
                name="core_credential_network_label_uniq",
            ),
        ]
        ordering: ClassVar[list[str]] = ["network__slug", "label"]

    def __str__(self) -> str:
        return f"{self.network.slug}:{self.label or 'default'}"

    def set_secrets_dict(self, data: dict[str, Any]) -> None:
        """Serialize and encrypt secrets (call save() after)."""
        self.encrypted_payload = json.dumps(data, separators=(",", ":"))

    @classmethod
    def get_stored_payload_raw(cls, pk: int) -> str:
        """Read ``encrypted_payload`` from DB without decrypting (admin-safe)."""
        from django.db import connection

        table = cls._meta.db_table
        with connection.cursor() as cursor:
            cursor.execute(
                f"SELECT encrypted_payload FROM {table} WHERE id = %s",
                [pk],
            )
            row = cursor.fetchone()
        return (row[0] or "") if row else ""

    def get_secrets_dict(self) -> dict[str, Any]:
        """Return decrypted JSON as dict; empty if no payload."""
        if not self.pk:
            return {}
        plain = crypto.payload_plaintext_from_stored(
            self.get_stored_payload_raw(self.pk)
        )
        if not plain:
            return {}
        return json.loads(plain)
