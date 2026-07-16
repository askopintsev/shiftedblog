"""Publish workflow serializers."""

from __future__ import annotations

from rest_framework import serializers

from sender.services.telegram_format import (
    TELEGRAM_FORMAT_CROSSLINK,
    TELEGRAM_FORMAT_FULL,
)


class PublishRequestSerializer(serializers.Serializer):
    post_id = serializers.IntegerField()
    dest_site = serializers.BooleanField(default=False)
    dest_telegram = serializers.BooleanField(default=False)
    telegram_format = serializers.ChoiceField(
        choices=[TELEGRAM_FORMAT_FULL, TELEGRAM_FORMAT_CROSSLINK],
        default=TELEGRAM_FORMAT_FULL,
    )
    crosslink_network = serializers.CharField(
        required=False,
        allow_null=True,
        allow_blank=True,
    )
    telegram_post_story = serializers.BooleanField(default=False)


class TelegramPreviewQuerySerializer(serializers.Serializer):
    post_id = serializers.IntegerField()
    telegram_format = serializers.ChoiceField(
        choices=[TELEGRAM_FORMAT_FULL, TELEGRAM_FORMAT_CROSSLINK],
        default=TELEGRAM_FORMAT_FULL,
    )
    crosslink_network = serializers.CharField(
        required=False,
        allow_null=True,
        allow_blank=True,
    )
