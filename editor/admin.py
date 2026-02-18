from typing import ClassVar

from django.contrib import admin

from editor import models
from editor.forms import OptionalGalleryFormSet, PostAdminForm


class PostGalleryImageInline(admin.TabularInline):
    model = models.PostGalleryImage
    formset = OptionalGalleryFormSet
    extra = 0
    ordering = ("gallery_key", "order")
    fields = ("gallery_key", "image", "caption", "order")
    verbose_name = "Gallery image"
    verbose_name_plural = "Gallery images (insert [gallery:1], [gallery:2], … in body where each gallery should appear)"


@admin.register(models.Post)
class PostAdmin(admin.ModelAdmin):
    form = PostAdminForm
    inlines = [PostGalleryImageInline]

    list_display = ("title", "slug", "author", "published", "status")
    list_filter = ("status", "created", "published", "author")
    search_fields = ("title", "body")
    prepopulated_fields: ClassVar[dict] = {"slug": ("title",)}
    readonly_fields = ("views", "draft_preview_link")
    date_hierarchy = "published"
    ordering = ("status", "published")


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
