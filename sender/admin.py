from django.contrib import admin

from core.models import User
from sender.models import PostLink


@admin.register(PostLink)
class PostLinkAdmin(admin.ModelAdmin):
    list_display = (
        "post",
        "network",
        "message_url",
        "message_id",
        "story_id",
        "created_at",
    )
    list_filter = ("network", "created_at")
    search_fields = ("post__title", "post__slug", "message_url", "story_url")
    readonly_fields = (
        "post",
        "network",
        "message_url",
        "message_id",
        "story_id",
        "story_url",
        "created_at",
    )
    ordering = ("-created_at",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        user = request.user
        return isinstance(user, User) and user.is_staff

    def has_delete_permission(self, request, obj=None):
        user = request.user
        return isinstance(user, User) and user.is_superuser
