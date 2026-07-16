"""Validate and persist posts using existing PostAdminForm rules."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.files.uploadedfile import UploadedFile
from django.forms import model_to_dict

from editor.forms import PostAdminForm
from editor.models import Post

_FORM_FILE_FIELDS = ("cover_image",)


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
