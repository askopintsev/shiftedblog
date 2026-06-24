"""Publish workflow API views."""

from __future__ import annotations

from django.shortcuts import get_object_or_404
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from api.editor.permissions import IsStaffUser
from api.editor.serializers.posts import PostListSerializer
from api.editor.serializers.publish import (
    PublishRequestSerializer,
    TelegramPreviewQuerySerializer,
)
from api.editor.services import publish_adapter
from editor.models import Post


class PublishReadyPostsView(APIView):
    permission_classes = [IsStaffUser]

    def get(self, request: Request) -> Response:
        posts = publish_adapter.ready_posts_queryset()
        ser = PostListSerializer(posts, many=True)
        return Response({"ok": True, "results": ser.data})


class TelegramPreviewView(APIView):
    permission_classes = [IsStaffUser]

    def get(self, request: Request) -> Response:
        ser = TelegramPreviewQuerySerializer(data=request.query_params)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        get_object_or_404(
            Post,
            pk=data["post_id"],
            status="ready_to_publish",
        )
        crosslink = (data.get("crosslink_network") or "").strip() or None
        preview = publish_adapter.telegram_preview_dict(
            data["post_id"],
            telegram_format=data["telegram_format"],
            crosslink_network=crosslink,
        )
        if preview is None:
            return Response(
                {"ok": False, "error": "Could not build preview."},
                status=400,
            )
        return Response({"ok": True, **preview})


class StoryAvailabilityView(APIView):
    permission_classes = [IsStaffUser]

    def get(self, request: Request) -> Response:
        return Response({"ok": True, **publish_adapter.story_availability_dict()})


class PublishView(APIView):
    permission_classes = [IsStaffUser]

    def post(self, request: Request) -> Response:
        ser = PublishRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        crosslink = (data.get("crosslink_network") or "").strip() or None
        result = publish_adapter.run_publish(
            data["post_id"],
            dest_site=data["dest_site"],
            dest_telegram=data["dest_telegram"],
            telegram_format=data["telegram_format"],
            crosslink_network=crosslink,
            telegram_post_story=data["telegram_post_story"],
        )
        return Response({"ok": result["all_ok"], "result": result})
