"""Config and audit serializers."""

from __future__ import annotations

from typing import Any

from rest_framework import serializers

from core.models.network import Credential, Network
from core.models.telegram_settings import TelegramNetworkSettings
from sender.models.post_link import PostLink


class NetworkSerializer(serializers.ModelSerializer):
    class Meta:
        model = Network
        fields = ("id", "slug", "name")


class CredentialListSerializer(serializers.ModelSerializer):
    network_slug = serializers.CharField(source="network.slug", read_only=True)

    class Meta:
        model = Credential
        fields = ("id", "network", "network_slug", "label", "created_at", "updated_at")


class CredentialDetailSerializer(serializers.ModelSerializer):
    network_slug = serializers.CharField(source="network.slug", read_only=True)
    secrets = serializers.JSONField(write_only=True, required=False)
    secrets_masked = serializers.SerializerMethodField()

    class Meta:
        model = Credential
        fields = (
            "id",
            "network",
            "network_slug",
            "label",
            "secrets",
            "secrets_masked",
            "created_at",
            "updated_at",
        )

    def get_secrets_masked(self, obj: Credential) -> dict[str, Any]:
        data = obj.get_secrets_dict()
        masked: dict[str, Any] = {}
        for key, value in data.items():
            if isinstance(value, str) and value:
                masked[key] = "••••••"
            else:
                masked[key] = value
        return masked

    def create(self, validated_data: dict[str, Any]) -> Credential:
        secrets = validated_data.pop("secrets", None)
        instance = Credential(**validated_data)
        if secrets is not None:
            instance.set_secrets_dict(secrets)
        instance.save()
        return instance

    def update(
        self, instance: Credential, validated_data: dict[str, Any]
    ) -> Credential:
        secrets = validated_data.pop("secrets", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if secrets is not None:
            instance.set_secrets_dict(secrets)
        instance.save()
        return instance


class TelegramSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = TelegramNetworkSettings
        fields = (
            "id",
            "story_fallback_image",
            "post_continuation_text",
        )


class PostLinkSerializer(serializers.ModelSerializer):
    post_title = serializers.CharField(source="post.title", read_only=True)
    network_slug = serializers.CharField(source="network.slug", read_only=True)

    class Meta:
        model = PostLink
        fields = (
            "id",
            "post",
            "post_title",
            "network",
            "network_slug",
            "message_url",
            "message_id",
            "story_id",
            "story_url",
            "created_at",
        )
