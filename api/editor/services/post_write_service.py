"""Validate and persist posts using existing PostAdminForm rules."""

from __future__ import annotations

from typing import Any

from django.core.exceptions import ValidationError as DjangoValidationError
from django.forms import model_to_dict

from editor.forms import PostAdminForm
from editor.models import Post


def validate_post_data(
    instance: Post | None,
    data: dict[str, Any],
) -> Post:
    """Apply PostAdminForm validation; return unsaved instance with cleaned data."""
    if instance is None:
        instance = Post()
    form_data: dict[str, Any] = {}
    if instance.pk:
        form_data = model_to_dict(instance)
        form_data["tags"] = list(instance.tags.names())
        form_data["series"] = list(instance.series.values_list("pk", flat=True))
    form_data.update(data)
    form = PostAdminForm(data=form_data, instance=instance)
    if not form.is_valid():
        raise DjangoValidationError(form.errors)
    return form.save(commit=False)


def save_post(instance: Post, *, record_history: bool = False) -> Post:
    """Persist post; optionally record autosave history snapshot."""
    instance.save()
    if record_history:
        from editor.post_history_service import PostHistoryService

        PostHistoryService().record_autosave_snapshot(instance)
    return instance
