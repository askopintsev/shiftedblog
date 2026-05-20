from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from django.utils.html import strip_tags

from editor.models import POST_HISTORY_MAX_ENTRIES, Post, PostHistory


@dataclass(frozen=True)
class PostHistorySnapshotDTO:
    title: str
    body: str
    short_description: str | None


@dataclass(frozen=True)
class PostHistoryListItemDTO:
    id: int
    created_at: str
    preview: str


class PostHistoryService:
    max_entries = POST_HISTORY_MAX_ENTRIES

    def record_autosave_snapshot(self, post: Post) -> PostHistory | None:
        """Store history when autosaved content differs from the latest snapshot."""
        snapshot = PostHistorySnapshotDTO(
            title=(post.title or "").strip(),
            body=post.body or "",
            short_description=self._normalize_short_description(post.short_description),
        )
        latest = (
            PostHistory.objects.filter(post_id=post.pk)
            .order_by("-created_at", "-pk")
            .first()
        )
        if latest is not None and self._snapshot_matches(latest, snapshot):
            return None

        history = PostHistory.objects.create(
            post_id=post.pk,
            title=snapshot.title,
            body=snapshot.body,
            short_description=snapshot.short_description,
        )
        self._prune_old_entries(post.pk)
        return history

    def list_for_post(
        self,
        post_id: int,
        *,
        limit: int | None = None,
    ) -> list[PostHistoryListItemDTO]:
        cap = limit if limit is not None else self.max_entries
        rows = PostHistory.objects.filter(post_id=post_id).order_by(
            "-created_at", "-pk"
        )[:cap]
        return [self._to_list_item(row) for row in rows]

    def get_snapshot(
        self,
        post_id: int,
        history_id: int,
    ) -> PostHistorySnapshotDTO | None:
        row = PostHistory.objects.filter(post_id=post_id, pk=history_id).first()
        if row is None:
            return None
        return PostHistorySnapshotDTO(
            title=row.title or "",
            body=row.body or "",
            short_description=row.short_description,
        )

    def _prune_old_entries(self, post_id: int) -> None:
        keep_pks = list(
            PostHistory.objects.filter(post_id=post_id)
            .order_by("-created_at", "-pk")
            .values_list("pk", flat=True)[: self.max_entries]
        )
        if not keep_pks:
            return
        PostHistory.objects.filter(post_id=post_id).exclude(pk__in=keep_pks).delete()

    @staticmethod
    def _normalize_short_description(value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped if stripped else None

    @staticmethod
    def _snapshot_matches(row: PostHistory, snapshot: PostHistorySnapshotDTO) -> bool:
        return (
            (row.title or "") == snapshot.title
            and (row.body or "") == snapshot.body
            and row.short_description == snapshot.short_description
        )

    @staticmethod
    def _to_list_item(row: PostHistory) -> PostHistoryListItemDTO:
        plain = strip_tags(row.body or "").strip()
        preview = plain[:120] + ("…" if len(plain) > 120 else "")
        return PostHistoryListItemDTO(
            id=row.pk,
            created_at=row.created_at.isoformat(),
            preview=preview or "(empty body)",
        )

    def list_item_to_dict(self, item: PostHistoryListItemDTO) -> dict[str, Any]:
        return {
            "id": item.id,
            "created_at": item.created_at,
            "preview": item.preview,
        }

    def snapshot_to_dict(self, snapshot: PostHistorySnapshotDTO) -> dict[str, Any]:
        return {
            "title": snapshot.title,
            "body": snapshot.body,
            "short_description": snapshot.short_description,
        }
