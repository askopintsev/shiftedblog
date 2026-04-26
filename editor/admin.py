import json
from typing import ClassVar
from uuid import UUID, uuid4

from django.contrib import admin
from django.http import HttpRequest, JsonResponse
from django.urls import path

from editor import models
from editor.forms import OptionalGalleryFormSet, PostAdminForm
from editor.text_quality_service import PostTextQualityService, TextQualityRequestDTO


@admin.register(models.PostSlugRedirect)
class PostSlugRedirectAdmin(admin.ModelAdmin):
    list_display = ("old_slug", "post")
    search_fields = ("old_slug", "post__title")
    autocomplete_fields = ("post",)


class PostGalleryImageInline(admin.TabularInline):
    model = models.PostGalleryImage
    formset = OptionalGalleryFormSet
    extra = 0
    ordering = ("gallery_key", "order")
    fields = ("gallery_key", "image", "caption", "order")
    verbose_name = "Gallery image"
    verbose_name_plural = "Gallery images (insert [gallery:1], [gallery:2], … in body)"


@admin.register(models.Post)
class PostAdmin(admin.ModelAdmin):
    form = PostAdminForm
    inlines: ClassVar[list] = [PostGalleryImageInline]
    text_quality_service = PostTextQualityService()

    class Media:
        css: ClassVar[dict] = {"all": ("editor/css/post_admin_editor.css",)}
        js: ClassVar[tuple] = (
            "editor/js/post_admin_session_keepalive.js",
            "editor/js/post_body_stats.js",
            "editor/js/post_autosave.js",
            "editor/js/post_admin_meta_validation.js",
        )

    list_display = ("title", "slug", "author", "updated", "published", "status")
    list_filter = ("status", "created", "published", "author")
    search_fields = ("title", "body")
    prepopulated_fields: ClassVar[dict] = {"slug": ("title",)}
    readonly_fields = ("views", "updated", "draft_preview_link")
    date_hierarchy = "published"
    ordering = ("status", "published")

    def get_urls(self):
        custom_urls = [
            path(
                "text-quality/",
                self.admin_site.admin_view(self.text_quality_view),
                name="editor_post_text_quality",
            ),
        ]
        return custom_urls + super().get_urls()

    def text_quality_view(self, request: HttpRequest) -> JsonResponse:
        method = str(request.META.get("REQUEST_METHOD", "GET")).upper()
        if method != "POST":
            return JsonResponse(
                {
                    "schema_version": "1.0",
                    "request_id": str(uuid4()),
                    "ok": False,
                    "error": {
                        "code": "METHOD_NOT_ALLOWED",
                        "message": "Use POST for text quality analysis.",
                        "details": {},
                    },
                },
                status=405,
            )

        try:
            payload = json.loads(request.body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            payload = {}

        text = str(payload.get("text") or "").strip()
        if not text:
            request_id = payload.get("request_id")
            return JsonResponse(
                {
                    "schema_version": "1.0",
                    "request_id": str(request_id or uuid4()),
                    "ok": False,
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "Field 'text' is required.",
                        "details": {"field": "text"},
                    },
                },
                status=422,
            )

        request_id = payload.get("request_id")
        try:
            parsed_request_id = UUID(request_id) if request_id else uuid4()
        except (TypeError, ValueError):
            parsed_request_id = uuid4()
        request_dto = TextQualityRequestDTO(
            text=text,
            locale=str(payload.get("locale") or "ru-RU"),
            content_format=str(payload.get("content_format") or "html"),
            request_id=parsed_request_id,
            enable_extra_metrics=bool(payload.get("enable_extra_metrics", True)),
        )
        report = self.text_quality_service.evaluate(request_dto)
        return JsonResponse(report.to_dict(), status=200)


@admin.register(models.Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name",)
    ordering = ("name",)


@admin.register(models.Series)
class SeriesAdmin(admin.ModelAdmin):
    list_display = ("name",)
    ordering = ("name",)


@admin.register(models.PostSeries)
class PostSeriesAdmin(admin.ModelAdmin):
    list_display = ("post", "series", "order_position")
    list_filter = ("series",)
    search_fields = ("post__title", "series__name")
    ordering = ("series", "order_position")
