from typing import Any, ClassVar, cast

from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.forms import BaseInlineFormSet, ChoiceField, ModelChoiceField
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
        author_field = cast(ModelChoiceField, self.fields["author"])
        author_field.queryset = user_model.objects.filter(is_active=True)

        st = cast(ChoiceField, self.fields["status"])
        choices = [c for c in models.Post.STATUS_CHOICES if c[0] != "published"]
        if self.instance.pk and self.instance.status == "published":
            choices = list(models.Post.STATUS_CHOICES)
        st.choices = choices
        if not (self.instance.pk and self.instance.status == "published"):
            extra = "“Published” is set only via Multi-channel publish, not here."
            st.help_text = f"{st.help_text} {extra}".strip() if st.help_text else extra

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
        cov_ht = (
            "Required before publishing. JPEG/PNG/WebP uploads are stored as "
            "AVIF or WebP (JPEG if encoding fails)."
        )
        self.fields["cover_image"].help_text = (
            f"{self.fields['cover_image'].help_text} {cov_ht}".strip()
            if self.fields["cover_image"].help_text
            else cov_ht
        )

        for fname in ("title", "short_description", "cover_image"):
            cls = self.fields[fname].widget.attrs.get("class", "")
            self.fields[fname].widget.attrs["class"] = f"{cls} post-seo-field".strip()

    def _has_cover_image(self, cleaned: dict[str, Any]) -> bool:
        val = cleaned.get("cover_image")
        if val is False:
            return False
        field = self.fields["cover_image"]
        if val not in field.empty_values:
            return True
        pk = getattr(self.instance, "pk", None)
        if pk is None:
            return False
        try:
            cover = self.instance.cover_image
            name = getattr(cover, "name", "") if cover else ""
        except ValueError:
            name = ""
        if name and str(name).strip():
            return True
        # Stale in-memory Post after AJAX save: field can disagree with DB until reload.
        stored = (
            models.Post.objects.filter(pk=pk)
            .values_list("cover_image", flat=True)
            .first()
        )
        return bool(stored and str(stored).strip())

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

    def clean(self) -> dict[str, Any]:
        cleaned_raw = super().clean()
        cleaned: dict[str, Any] = cleaned_raw if cleaned_raw is not None else {}
        status = cleaned.get("status")
        prev = getattr(self.instance, "status", None)
        if status == "published" and prev != "published":
            raise ValidationError(
                {
                    "status": (
                        "Published can only be set via Multi-channel publish "
                        "(Editor → Posts → Multi-channel publish)."
                    ),
                },
            )

        if status not in _PUBLISH_STATUSES:
            return cleaned

        title = (cleaned.get("title") or "").strip()
        if title and len(title) > _TITLE_MAX_PUBLISH:
            self.add_error(
                "title",
                ValidationError(
                    "Title is too long for typical search snippets "
                    "(recommended max %(max)d characters, current %(n)d).",
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
                    "previews (max %(max)d characters, current %(n)d).",
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
