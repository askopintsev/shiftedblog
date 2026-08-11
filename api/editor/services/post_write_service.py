"""Validate and persist posts using existing PostAdminForm rules."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.files.uploadedfile import UploadedFile
from django.forms import model_to_dict

from editor.forms import PostAdminForm
from editor.models import Post, PostSeries, Series

_FORM_FILE_FIELDS = ("cover_image",)
_SERIES_UNSET = object()


@dataclass(frozen=True)
class ValidatedPostData:
    instance: Post
    save_m2m: Callable[[], None]


def _extract_uploaded_files(form_data: dict[str, Any]) -> dict[str, UploadedFile]:
    files: dict[str, UploadedFile] = {}
    for field in _FORM_FILE_FIELDS:
        value = form_data.get(field)
        if isinstance(value, UploadedFile):
            files[field] = form_data.pop(field)
    return files


def _normalize_form_tags(form_data: dict[str, Any]) -> None:
    value = form_data.get("tags")
    if isinstance(value, list):
        form_data["tags"] = ", ".join(
            str(tag).strip() for tag in value if str(tag).strip()
        )


def validate_post_data(
    instance: Post | None,
    data: dict[str, Any],
) -> ValidatedPostData:
    """Apply PostAdminForm validation; return unsaved instance with cleaned data."""
    if instance is None:
        instance = Post()
    form_data: dict[str, Any] = {}
    if instance.pk:
        form_data = model_to_dict(instance)
        form_data["tags"] = list(instance.tags.names())
        form_data["series"] = list(instance.series.values_list("pk", flat=True))
    else:
        form_data["views"] = instance.views or 0
    form_data.update(data)
    files = _extract_uploaded_files(form_data)
    _normalize_form_tags(form_data)
    form = PostAdminForm(data=form_data, files=files, instance=instance)
    if not form.is_valid():
        raise DjangoValidationError(form.errors)
    return ValidatedPostData(instance=form.save(commit=False), save_m2m=form.save_m2m)


def save_post(validated: ValidatedPostData, *, record_history: bool = False) -> Post:
    """Persist post; optionally record autosave history snapshot."""
    instance = validated.instance
    instance.save()
    validated.save_m2m()
    if record_history:
        from editor.post_history_service import PostHistoryService

        PostHistoryService().record_autosave_snapshot(instance)
    return instance


def apply_series_membership(
    post: Post,
    *,
    series_id: int | None,
    order_position: int | None = None,
) -> None:
    """Replace post series membership (single series + optional position)."""
    PostSeries.objects.filter(post=post).delete()
    if series_id is None:
        return
    if not Series.objects.filter(pk=series_id).exists():
        raise DjangoValidationError({"series_id": ["Unknown series."]})
    if order_position is not None:
        conflict = (
            PostSeries.objects.filter(
                series_id=series_id,
                order_position=order_position,
            )
            .exclude(post_id=post.pk)
            .exists()
        )
        if conflict:
            raise DjangoValidationError(
                {
                    "series_order_position": [
                        "This position is already used in the series.",
                    ],
                },
            )
    PostSeries.objects.create(
        post=post,
        series_id=series_id,
        order_position=order_position,
    )


def pop_series_write_fields(
    validated_data: dict[str, Any],
) -> tuple[Any, Any]:
    """Remove series write keys from form payload; return (series_id, order)."""
    series_id = validated_data.pop("series_id", _SERIES_UNSET)
    order_position = validated_data.pop("series_order_position", _SERIES_UNSET)
    return series_id, order_position


def series_fields_were_set(series_id: Any) -> bool:
    return series_id is not _SERIES_UNSET
