from django import forms

from django_ckeditor_5.widgets import CKEditor5Widget

from blog import models


class SearchForm(forms.Form):
    query = forms.CharField()


class PostAdminForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['author'].queryset = models.User.objects.filter(is_active=True)

    class Meta:
        model = models.Post
        fields = '__all__'
        widgets = {
            'body': CKEditor5Widget(
                attrs={"class": "django_ckeditor_5"},
            )
        }
