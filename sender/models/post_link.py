from __future__ import annotations

from typing import ClassVar

from django.db import models
from django.db.models import BaseConstraint

from core.models.network import Network


class PostLink(models.Model):
    """Canonical published URL for a post on a given network."""

    post = models.ForeignKey(
        "editor.Post",
        on_delete=models.CASCADE,
        related_name="sender_links",
    )
    network = models.ForeignKey(
        Network,
        on_delete=models.CASCADE,
        related_name="post_links",
    )
    url = models.URLField(max_length=2048)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "sender"
        db_table = "sender_postlink"
        constraints: ClassVar[list[BaseConstraint]] = [
            models.UniqueConstraint(
                fields=("post", "network"),
                name="sender_postlink_post_network_uniq",
            ),
        ]
        ordering: ClassVar[list[str]] = ["-created_at"]

    def __str__(self) -> str:
        return f"{getattr(self, 'post_id', '')!s} @ {self.network.slug}"
