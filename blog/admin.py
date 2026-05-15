from django.contrib import admin

from blog.models import SitePublication


@admin.register(SitePublication)
class SitePublicationAdmin(admin.ModelAdmin):
    list_display = ("post", "published_at")
    search_fields = ("post__title", "post__slug")
    autocomplete_fields = ("post",)
    ordering = ("-published_at",)
