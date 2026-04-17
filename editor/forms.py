from typing import ClassVar

from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.forms import BaseInlineFormSet
from django_ckeditor_5.widgets import CKEditor5Widget

from editor import models

# SEO-oriented limits when publishing (meta title / description).
_TITLE_MAX_PUBLISH = 100
_SHORT_DESC_MAX_PUBLISH = 200

_PUBLISH_STATUSES: frozenset[str] = frozenset({"ready_to_publish", "published"})


class OptionalGalleryFormSet(BaseInlineFormSet):
    """Allow saving when gallery formset management data is missing."""

    def __init__(self, data=None, *args, **kwargs):
        if data is not None:
            prefix = kwargs.get("prefix") or self.get_default_prefix()
            total_key = f"{prefix}-TOTAL_FORMS"
            initial_key = f"{prefix}-INITIAL_FORMS"
            if total_key not in data or initial_key not in data:
                data = None
        super().__init__(data, *args, **kwargs)


class SearchForm(forms.Form):
    query = forms.CharField()


class PostAdminForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        user_model = get_user_model()
        self.fields["author"].queryset = user_model.objects.filter(is_active=True)

        title_ht = (
            "Required. For search snippets, about "
            f"{_TITLE_MAX_PUBLISH} characters or fewer is recommended."
        )
        self.fields["title"].help_text = (
            f"{self.fields['title'].help_text} {title_ht}".strip()
            if self.fields["title"].help_text
            else title_ht
        )
        sd_ht = (
            f"Optional. About {_SHORT_DESC_MAX_PUBLISH} characters or fewer works well "
            "for meta / social previews (max 300 in DB)."
        )
        self.fields["short_description"].help_text = (
            f"{self.fields['short_description'].help_text} {sd_ht}".strip()
            if self.fields["short_description"].help_text
            else sd_ht
        )
        cov_ht = "Required before publishing."
        self.fields["cover_image"].help_text = (
            f"{self.fields['cover_image'].help_text} {cov_ht}".strip()
            if self.fields["cover_image"].help_text
            else cov_ht
        )

        for fname in ("title", "short_description", "cover_image"):
            cls = self.fields[fname].widget.attrs.get("class", "")
            self.fields[fname].widget.attrs["class"] = f"{cls} post-seo-field".strip()

    def _has_cover_image(self, cleaned: dict) -> bool:
        upload = cleaned.get("cover_image")
        if upload and upload is not False:
            return True
        if self.instance.pk and self.instance.cover_image:
            try:
                return bool(self.instance.cover_image.name)
            except ValueError:
                return False
        return False

    def clean_title(self) -> str:
        title = (self.cleaned_data.get("title") or "").strip()
        if not title:
            raise ValidationError("Title is required.")
        return title

    def clean_short_description(self) -> str | None:
        raw = self.cleaned_data.get("short_description")
        if raw is None:
            return None
        s = raw.strip()
        return s if s else None

    def clean(self):
        cleaned = super().clean()
        status = cleaned.get("status")
        if status not in _PUBLISH_STATUSES:
            return cleaned

        title = (cleaned.get("title") or "").strip()
        if title and len(title) > _TITLE_MAX_PUBLISH:
            self.add_error(
                "title",
                ValidationError(
                    "Title is too long for typical search snippets "
                    f"(recommended max %(max)d characters, current %(n)d).",
                    code="title_seo_length",
                    params={"max": _TITLE_MAX_PUBLISH, "n": len(title)},
                ),
            )

        sd = cleaned.get("short_description")
        if sd and len(sd) > _SHORT_DESC_MAX_PUBLISH:
            self.add_error(
                "short_description",
                ValidationError(
                    "Short description is longer than recommended for meta / social "
                    f"previews (max %(max)d characters, current %(n)d).",
                    code="short_description_seo_length",
                    params={"max": _SHORT_DESC_MAX_PUBLISH, "n": len(sd)},
                ),
            )

        if not self._has_cover_image(cleaned):
            self.add_error(
                "cover_image",
                ValidationError(
                    "Cover image is required when status is "
                    "“Ready to publish” or “Published”.",
                    code="cover_image_required",
                ),
            )

        return cleaned

    class Meta:
        model = models.Post
        fields: ClassVar[list] = [
            "title",
            "slug",
            "author",
            "cover_image",
            "cover_image_credits",
            "cover_description",
            "body",
            "published",
            "status",
            "tags",
            "category",
            "series",
            "short_description",
            "views",
        ]
        widgets: ClassVar[dict] = {
            "body": CKEditor5Widget(attrs={"class": "django_ckeditor_5"}),
        }
