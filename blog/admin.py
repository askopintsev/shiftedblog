from django.contrib import admin

from blog import models
from blog.forms import PostAdminForm


@admin.register(models.Post)
class PostAdmin(admin.ModelAdmin):
    form = PostAdminForm

    list_display = ("title", "slug", "author", "published", "status")
    list_filter = ("status", "created", "published", "author")
    search_fields = ("title", "body")
    prepopulated_fields = {"slug": ("title",)}
    readonly_fields = ("views",)
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


@admin.register(models.SkillGroup)
class SkillGroupAdmin(admin.ModelAdmin):
    list_display = ("name",)
    ordering = ("name",)


@admin.register(models.Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ("name", "rating")
    ordering = ("name",)


@admin.register(models.AccountGroup)
class AccountGroupAdmin(admin.ModelAdmin):
    list_display = ("name",)
    ordering = ("name",)


@admin.register(models.Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ("name", "group")
    ordering = ("name",)


@admin.register(models.Person)
class PersonAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name", "greeting", "biography")
    ordering = ("name",)


@admin.register(models.User)
class UserAdmin(admin.ModelAdmin):
    list_display = (
        "email",
        "first_name",
        "last_name",
        "is_staff",
        "is_active",
        "date_joined",
    )
    list_filter = ("is_staff", "is_active", "is_superuser")
    search_fields = ("email", "first_name", "last_name")
    ordering = ("-date_joined",)
    readonly_fields = ("date_joined",)
