import json
from typing import ClassVar
from uuid import UUID, uuid4

from django.contrib import admin
from django.http import HttpRequest, JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import path, reverse
from django.utils import timezone

from blog.models import SitePublication
from editor import models
from editor.forms import OptionalGalleryFormSet, PostAdminForm
from editor.post_history_service import PostHistoryService
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


class SitePublicationInline(admin.StackedInline):
    model = SitePublication
    extra = 0
    max_num = 1
    can_delete = True
    fields = ("published_at",)


@admin.action(description="Publish selected posts to site")
def publish_selected_posts_to_site(modeladmin, request, queryset):
    for post in queryset:
        if post.status != "published":
            continue
        SitePublication.objects.update_or_create(
            post=post,
            defaults={"published_at": post.published or timezone.now()},
        )


@admin.action(description="Unpublish selected posts from site")
def unpublish_selected_posts_from_site(modeladmin, request, queryset):
    SitePublication.objects.filter(post__in=queryset).delete()


@admin.register(models.Post)
class PostAdmin(admin.ModelAdmin):
    form = PostAdminForm
    change_form_template = "admin/editor/post/change_form.html"
    change_list_template = "admin/editor/post/change_list.html"
    inlines: ClassVar[list] = [PostGalleryImageInline, SitePublicationInline]
    text_quality_service = PostTextQualityService()
    post_history_service = PostHistoryService()
    actions = (publish_selected_posts_to_site, unpublish_selected_posts_from_site)

    class Media:
        css: ClassVar[dict] = {"all": ("editor/css/post_admin_editor.css",)}
        js: ClassVar[tuple] = (
            "editor/js/post_admin_session_keepalive.js",
            "editor/js/post_body_stats.js",
            "editor/js/post_autosave.js",
            "editor/js/post_history.js",
            "editor/js/post_editor_emoji.js",
            "editor/js/post_admin_meta_validation.js",
        )

    list_display = ("id", "title", "slug", "author", "updated", "published", "status")
    list_filter = ("status", "created", "published", "author")
    search_fields = ("title", "body")
    prepopulated_fields: ClassVar[dict] = {"slug": ("title",)}
    readonly_fields = ("views", "updated", "draft_preview_link")
    date_hierarchy = "published"
    ordering = ("status", "published")

    def get_changeform_initial_data(self, request: HttpRequest):
        initial = super().get_changeform_initial_data(request)
        user = request.user
        pk = getattr(user, "pk", None)
        if user.is_authenticated and pk is not None and "author" not in initial:
            initial["author"] = pk
        return initial

    def changelist_view(self, request, extra_context=None):
        merged = dict(extra_context or {})
        merged["sender_publish_url"] = reverse("sender_publish_workflow")
        return super().changelist_view(request, extra_context=merged)

    def changeform_view(
        self,
        request: HttpRequest,
        object_id: str | None = None,
        form_url: str = "",
        extra_context: dict[str, object] | None = None,
    ):
        merged = dict(extra_context) if extra_context else {}
        merged["post_admin_text_quality_url"] = reverse(
            "admin:editor_post_text_quality",
        )
        if object_id is not None:
            merged["post_admin_history_list_url"] = reverse(
                "admin:editor_post_history_list",
                args=[object_id],
            )
            merged["post_history_max_entries"] = self.post_history_service.max_entries
        return super().changeform_view(request, object_id, form_url, merged)

    @staticmethod
    def _is_autosave_request(request: HttpRequest) -> bool:
        return request.headers.get("X-Requested-With") == "XMLHttpRequest"

    def save_model(
        self,
        request: HttpRequest,
        obj: models.Post,
        form: PostAdminForm,
        change: bool,
    ) -> None:
        super().save_model(request, obj, form, change)
        if change and self._is_autosave_request(request):
            self.post_history_service.record_autosave_snapshot(obj)

    def get_urls(self):
        custom_urls = [
            path(
                "text-quality/",
                self.admin_site.admin_view(self.text_quality_view),
                name="editor_post_text_quality",
            ),
            path(
                "<path:object_id>/history/",
                self.admin_site.admin_view(self.post_history_list_view),
                name="editor_post_history_list",
            ),
            path(
                "<path:object_id>/history/<int:history_id>/",
                self.admin_site.admin_view(self.post_history_detail_view),
                name="editor_post_history_detail",
            ),
        ]
        return custom_urls + super().get_urls()

    def post_history_list_view(
        self,
        request: HttpRequest,
        object_id: str,
    ) -> JsonResponse:
        if request.method != "GET":
            return JsonResponse(
                {"ok": False, "error": "Method not allowed."},
                status=405,
            )
        post = get_object_or_404(models.Post, pk=object_id)
        if not self.has_change_permission(request, post):
            return JsonResponse({"ok": False, "error": "Forbidden."}, status=403)
        items = self.post_history_service.list_for_post(post.pk)
        return JsonResponse(
            {
                "ok": True,
                "items": [
                    self.post_history_service.list_item_to_dict(item) for item in items
                ],
                "max_entries": self.post_history_service.max_entries,
            },
            status=200,
        )

    def post_history_detail_view(
        self,
        request: HttpRequest,
        object_id: str,
        history_id: int,
    ) -> JsonResponse:
        if request.method != "GET":
            return JsonResponse(
                {"ok": False, "error": "Method not allowed."},
                status=405,
            )
        post = get_object_or_404(models.Post, pk=object_id)
        if not self.has_change_permission(request, post):
            return JsonResponse({"ok": False, "error": "Forbidden."}, status=403)
        snapshot = self.post_history_service.get_snapshot(post.pk, history_id)
        if snapshot is None:
            return JsonResponse({"ok": False, "error": "Not found."}, status=404)
        return JsonResponse(
            {
                "ok": True,
                "snapshot": self.post_history_service.snapshot_to_dict(snapshot),
            },
            status=200,
        )

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
    list_display = ("name", "slug")
    search_fields = ("name", "slug")
    prepopulated_fields: ClassVar[dict[str, tuple[str, ...]]] = {"slug": ("name",)}
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
