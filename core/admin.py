from __future__ import annotations

import json

from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from core.models import Credential, Network, User


class CredentialAdminForm(forms.ModelForm):
    """Edit secrets as JSON; ciphertext is never shown as a separate field."""

    secrets_json = forms.CharField(
        label="Secrets (JSON)",
        required=False,
        widget=forms.Textarea(attrs={"rows": 6, "cols": 80}),
        help_text=(
            'Example: {"bot_token": "…", "channel_name": "mychannel"}. '
            "Leave blank while editing to keep existing secrets."
        ),
    )

    class Meta:
        model = Credential
        fields = ("network", "label")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            try:
                d = self.instance.get_secrets_dict()
                self.initial["secrets_json"] = json.dumps(
                    d, indent=2, ensure_ascii=False
                )
            except (json.JSONDecodeError, TypeError, ValueError):
                self.initial["secrets_json"] = ""

    def clean(self):
        cleaned = super().clean() or {}
        raw = (cleaned.get("secrets_json") or "").strip()
        if raw:
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError as exc:
                self.add_error("secrets_json", f"Invalid JSON: {exc}")
                return cleaned
            if not isinstance(parsed, dict):
                self.add_error("secrets_json", "JSON must be an object.")
        return cleaned

    def save(self, commit=True):
        inst = super().save(commit=False)
        raw = (self.data.get("secrets_json") or "").strip()
        if raw:
            inst.set_secrets_dict(json.loads(raw))
        elif not self.instance.pk:
            inst.set_secrets_dict({})
        if commit:
            inst.save()
        return inst


@admin.register(Network)
class NetworkAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name", "slug")


@admin.register(Credential)
class CredentialAdmin(admin.ModelAdmin):
    form = CredentialAdminForm
    list_display = ("network", "label", "has_payload", "updated_at")
    list_filter = ("network",)
    search_fields = ("label",)
    readonly_fields = ("created_at", "updated_at")

    @admin.display(description="Has secrets", boolean=True)
    def has_payload(self, obj: Credential) -> bool:
        if not obj.pk:
            return False
        return bool(Credential.get_stored_payload_raw(obj.pk).strip())


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = (
        "email",
        "first_name",
        "last_name",
        "is_staff",
        "is_active",
        "date_joined",
    )
    list_filter = ("is_staff", "is_active", "is_superuser")
    search_fields = ("email", "first_name", "last_name")
    ordering = ("-date_joined",)
    readonly_fields = ("date_joined",)
