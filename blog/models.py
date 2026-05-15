from __future__ import annotations

from django.db import models


class SitePublication(models.Model):
    post = models.OneToOneField(
        "editor.Post",
        on_delete=models.CASCADE,
        related_name="site_publication",
    )
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-published_at",)
        indexes = (models.Index(fields=["published_at"]),)

    def __str__(self) -> str:
        return f"Site publication for {self.post_id}"
