from __future__ import annotations

from typing import ClassVar

from django.db import models
from django.db.models import BaseConstraint

from core.models.network import Network


class PostLink(models.Model):
    """Published URLs and Telegram ids for a post on a given network."""

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
    message_url = models.URLField(max_length=2048)
    message_id = models.PositiveBigIntegerField(null=True, blank=True)
    story_id = models.PositiveIntegerField(null=True, blank=True)
    story_url = models.URLField(max_length=2048, blank=True, default="")
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
