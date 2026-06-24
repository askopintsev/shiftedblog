"""Config and audit API views."""

from __future__ import annotations

from django.shortcuts import get_object_or_404
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from api.editor.permissions import IsStaffUser, IsSuperuserForSecrets
from api.editor.serializers.config import (
    CredentialDetailSerializer,
    CredentialListSerializer,
    NetworkSerializer,
    PostLinkSerializer,
    TelegramSettingsSerializer,
)
from core.models.network import Credential, Network
from core.models.telegram_settings import TelegramNetworkSettings
from sender.models.post_link import PostLink


class NetworkListView(APIView):
    permission_classes = [IsStaffUser]

    def get(self, request: Request) -> Response:
        qs = Network.objects.order_by("name")
        return Response({"ok": True, "results": NetworkSerializer(qs, many=True).data})


class NetworkDetailView(APIView):
    permission_classes = [IsStaffUser]

    def patch(self, request: Request, network_id: int) -> Response:
        obj = get_object_or_404(Network, pk=network_id)
        ser = NetworkSerializer(obj, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response({"ok": True, "network": ser.data})


class CredentialListCreateView(APIView):
    permission_classes = [IsSuperuserForSecrets]

    def get(self, request: Request) -> Response:
        qs = Credential.objects.select_related("network").order_by(
            "network__slug",
            "label",
        )
        return Response(
            {"ok": True, "results": CredentialListSerializer(qs, many=True).data},
        )

    def post(self, request: Request) -> Response:
        ser = CredentialDetailSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response({"ok": True, "credential": ser.data}, status=201)


class CredentialDetailView(APIView):
    permission_classes = [IsSuperuserForSecrets]

    def get(self, request: Request, credential_id: int) -> Response:
        obj = get_object_or_404(
            Credential.objects.select_related("network"), pk=credential_id
        )
        return Response(
            {"ok": True, "credential": CredentialDetailSerializer(obj).data}
        )

    def patch(self, request: Request, credential_id: int) -> Response:
        obj = get_object_or_404(Credential, pk=credential_id)
        ser = CredentialDetailSerializer(obj, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response({"ok": True, "credential": ser.data})

    def delete(self, request: Request, credential_id: int) -> Response:
        obj = get_object_or_404(Credential, pk=credential_id)
        obj.delete()
        return Response(status=204)


class TelegramSettingsView(APIView):
    permission_classes = [IsStaffUser]

    def get(self, request: Request) -> Response:
        obj = TelegramNetworkSettings.objects.select_related("network").first()
        if obj is None:
            return Response({"ok": True, "settings": None})
        return Response(
            {"ok": True, "settings": TelegramSettingsSerializer(obj).data},
        )

    def patch(self, request: Request) -> Response:
        obj = TelegramNetworkSettings.objects.first()
        if obj is None:
            return Response({"ok": False, "error": "Not configured."}, status=404)
        ser = TelegramSettingsSerializer(obj, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response({"ok": True, "settings": ser.data})


class PostLinkAuditView(APIView):
    permission_classes = [IsStaffUser]

    def get(self, request: Request) -> Response:
        qs = PostLink.objects.select_related("post", "network").order_by("-created_at")
        post_id = request.query_params.get("post_id")
        network_slug = request.query_params.get("network")
        if post_id:
            qs = qs.filter(post_id=post_id)
        if network_slug:
            qs = qs.filter(network__slug=network_slug)
        return Response(
            {"ok": True, "results": PostLinkSerializer(qs[:500], many=True).data},
        )
