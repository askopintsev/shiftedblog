"""Post CRUD and related editor API views."""

from __future__ import annotations

from typing import Any

from django.core.exceptions import ValidationError as DjangoValidationError
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from api.editor.permissions import IsStaffUser
from api.editor.serializers.posts import (
    CategorySerializer,
    PostDetailSerializer,
    PostGallerySerializer,
    PostListSerializer,
    PostWriteSerializer,
    SeriesSerializer,
)
from api.editor.services.post_write_service import save_post, validate_post_data
from blog.models import SitePublication
from editor.models import Category, Post, PostGalleryImage, Series
from editor.post_history_service import PostHistoryService
from editor.text_quality_service import PostTextQualityService, TextQualityRequestDTO


def _form_errors_response(exc: DjangoValidationError) -> Response:
    if hasattr(exc, "message_dict"):
        return Response({"ok": False, "errors": exc.message_dict}, status=400)
    return Response(
        {"ok": False, "errors": {"non_field_errors": exc.messages}}, status=400
    )


def _write_data_from_request(data: dict[str, Any]) -> dict[str, Any]:
    mapped: dict[str, Any] = {}
    field_map = {
        "author_id": "author",
        "category_id": "category",
        "series_ids": "series",
    }
    for key, value in data.items():
        target = field_map.get(key, key)
        mapped[target] = value
    return mapped


class PostListCreateView(APIView):
    permission_classes = [IsStaffUser]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get(self, request: Request) -> Response:
        qs = Post.objects.select_related("author", "category").prefetch_related(
            "tags",
        )
        status_filter = request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        search = (request.query_params.get("search") or "").strip()
        if search:
            qs = qs.filter(title__icontains=search) | qs.filter(slug__icontains=search)
        serializer = PostListSerializer(qs.order_by("-updated")[:200], many=True)
        return Response({"ok": True, "results": serializer.data})

    def post(self, request: Request) -> Response:
        write_ser = PostWriteSerializer(data=request.data)
        write_ser.is_valid(raise_exception=True)
        data = _write_data_from_request(write_ser.validated_data)
        data.setdefault("author", request.user.pk)
        data.setdefault("status", "draft")
        try:
            instance = validate_post_data(None, data)
            instance.author = instance.author or request.user
            save_post(instance)
        except DjangoValidationError as exc:
            return _form_errors_response(exc)
        out = PostDetailSerializer(instance, context={"request": request})
        return Response({"ok": True, "post": out.data}, status=status.HTTP_201_CREATED)


class PostDetailView(APIView):
    permission_classes = [IsStaffUser]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_object(self, post_id: int) -> Post:
        return get_object_or_404(
            Post.objects.select_related("author", "category").prefetch_related(
                "tags", "series", "gallery_images"
            ),
            pk=post_id,
        )

    def get(self, request: Request, post_id: int) -> Response:
        post = self.get_object(post_id)
        serializer = PostDetailSerializer(post, context={"request": request})
        return Response({"ok": True, "post": serializer.data})

    def patch(self, request: Request, post_id: int) -> Response:
        post = self.get_object(post_id)
        write_ser = PostWriteSerializer(data=request.data, partial=True)
        write_ser.is_valid(raise_exception=True)
        data = _write_data_from_request(write_ser.validated_data)
        if "cover_image" in request.FILES:
            data["cover_image"] = request.FILES["cover_image"]
        try:
            instance = validate_post_data(post, data)
            save_post(instance)
        except DjangoValidationError as exc:
            return _form_errors_response(exc)
        out = PostDetailSerializer(instance, context={"request": request})
        return Response({"ok": True, "post": out.data})


class PostAutosaveView(APIView):
    permission_classes = [IsStaffUser]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def post(self, request: Request, post_id: int) -> Response:
        post = get_object_or_404(Post, pk=post_id)
        write_ser = PostWriteSerializer(data=request.data, partial=True)
        write_ser.is_valid(raise_exception=True)
        data = _write_data_from_request(write_ser.validated_data)
        try:
            instance = validate_post_data(post, data)
            save_post(instance, record_history=True)
        except DjangoValidationError as exc:
            return _form_errors_response(exc)
        return Response({"ok": True, "updated": instance.updated.isoformat()})


class PostHistoryListView(APIView):
    permission_classes = [IsStaffUser]

    def get(self, request: Request, post_id: int) -> Response:
        get_object_or_404(Post, pk=post_id)
        service = PostHistoryService()
        items = service.list_for_post(post_id)
        return Response(
            {
                "ok": True,
                "items": [service.list_item_to_dict(item) for item in items],
                "max_entries": service.max_entries,
            },
        )


class PostHistoryDetailView(APIView):
    permission_classes = [IsStaffUser]

    def get(self, request: Request, post_id: int, history_id: int) -> Response:
        get_object_or_404(Post, pk=post_id)
        service = PostHistoryService()
        snapshot = service.get_snapshot(post_id, history_id)
        if snapshot is None:
            return Response({"ok": False, "error": "Not found."}, status=404)
        return Response(
            {
                "ok": True,
                "snapshot": service.snapshot_to_dict(snapshot),
            },
        )


class TextQualityView(APIView):
    permission_classes = [IsStaffUser]

    def post(self, request: Request) -> Response:
        payload = request.data if isinstance(request.data, dict) else {}
        text = str(payload.get("text") or "").strip()
        if not text:
            return Response(
                {
                    "schema_version": "1.0",
                    "ok": False,
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "Field 'text' is required.",
                    },
                },
                status=422,
            )
        from uuid import UUID, uuid4

        request_id = payload.get("request_id")
        try:
            parsed_request_id = UUID(str(request_id)) if request_id else uuid4()
        except (TypeError, ValueError):
            parsed_request_id = uuid4()
        dto = TextQualityRequestDTO(
            text=text,
            locale=str(payload.get("locale") or "ru-RU"),
            content_format=str(payload.get("content_format") or "html"),
            request_id=parsed_request_id,
            enable_extra_metrics=bool(payload.get("enable_extra_metrics", True)),
        )
        report = PostTextQualityService().evaluate(dto)
        return Response(report.to_dict())


class PostSitePublishView(APIView):
    permission_classes = [IsStaffUser]

    def post(self, request: Request, post_id: int) -> Response:
        post = get_object_or_404(Post, pk=post_id)
        if post.status != "published":
            return Response(
                {"ok": False, "error": "Post must be published."},
                status=400,
            )
        SitePublication.objects.update_or_create(
            post=post,
            defaults={"published_at": post.published or timezone.now()},
        )
        return Response({"ok": True})


class PostSiteUnpublishView(APIView):
    permission_classes = [IsStaffUser]

    def post(self, request: Request, post_id: int) -> Response:
        post = get_object_or_404(Post, pk=post_id)
        SitePublication.objects.filter(post=post).delete()
        return Response({"ok": True})


class PostGalleryListCreateView(APIView):
    permission_classes = [IsStaffUser]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get(self, request: Request, post_id: int) -> Response:
        post = get_object_or_404(Post, pk=post_id)
        images = post.gallery_images.order_by("gallery_key", "order")
        ser = PostGallerySerializer(images, many=True, context={"request": request})
        return Response({"ok": True, "results": ser.data})

    def post(self, request: Request, post_id: int) -> Response:
        post = get_object_or_404(Post, pk=post_id)
        image = request.FILES.get("image")
        if not image:
            return Response({"ok": False, "error": "image required"}, status=400)
        obj = PostGalleryImage.objects.create(
            post=post,
            gallery_key=int(request.data.get("gallery_key") or 1),
            image=image,
            caption=request.data.get("caption") or "",
            order=int(request.data.get("order") or 0),
        )
        ser = PostGallerySerializer(obj, context={"request": request})
        return Response({"ok": True, "gallery": ser.data}, status=201)


class PostGalleryDetailView(APIView):
    permission_classes = [IsStaffUser]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def patch(self, request: Request, post_id: int, gallery_id: int) -> Response:
        obj = get_object_or_404(PostGalleryImage, pk=gallery_id, post_id=post_id)
        for field in ("gallery_key", "caption", "order"):
            if field in request.data:
                setattr(obj, field, request.data[field])
        if "image" in request.FILES:
            obj.image = request.FILES["image"]
        obj.save()
        ser = PostGallerySerializer(obj, context={"request": request})
        return Response({"ok": True, "gallery": ser.data})

    def delete(self, request: Request, post_id: int, gallery_id: int) -> Response:
        obj = get_object_or_404(PostGalleryImage, pk=gallery_id, post_id=post_id)
        obj.delete()
        return Response(status=204)


class CategoryListCreateView(APIView):
    permission_classes = [IsStaffUser]

    def get(self, request: Request) -> Response:
        qs = Category.objects.order_by("name")
        return Response({"ok": True, "results": CategorySerializer(qs, many=True).data})

    def post(self, request: Request) -> Response:
        ser = CategorySerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response({"ok": True, "category": ser.data}, status=201)


class CategoryDetailView(APIView):
    permission_classes = [IsStaffUser]

    def patch(self, request: Request, category_id: int) -> Response:
        obj = get_object_or_404(Category, pk=category_id)
        ser = CategorySerializer(obj, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response({"ok": True, "category": ser.data})


class SeriesListCreateView(APIView):
    permission_classes = [IsStaffUser]

    def get(self, request: Request) -> Response:
        qs = Series.objects.order_by("name")
        return Response({"ok": True, "results": SeriesSerializer(qs, many=True).data})

    def post(self, request: Request) -> Response:
        ser = SeriesSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response({"ok": True, "series": ser.data}, status=201)


class SeriesDetailView(APIView):
    permission_classes = [IsStaffUser]

    def patch(self, request: Request, series_id: int) -> Response:
        obj = get_object_or_404(Series, pk=series_id)
        ser = SeriesSerializer(obj, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response({"ok": True, "series": ser.data})
