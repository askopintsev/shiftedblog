from typing import ClassVar

from django import forms
from django.contrib.auth import get_user_model
from django.forms import BaseInlineFormSet
from django_ckeditor_5.widgets import CKEditor5Widget

from editor import models


class OptionalGalleryFormSet(BaseInlineFormSet):
    """Allow saving the post when gallery formset management data is missing (galleries optional)."""

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
        User = get_user_model()
        self.fields["author"].queryset = User.objects.filter(is_active=True)

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
