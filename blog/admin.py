from django.contrib import admin

from blog import models
from blog.forms import PostAdminForm


@admin.register(models.Post)
class PostAdmin(admin.ModelAdmin):
    form = PostAdminForm

    list_display = ('title', 'slug', 'author', 'published', 'status')
    list_filter = ('status', 'created', 'published', 'author')
    search_fields = ('title', 'body')
    prepopulated_fields = {'slug': ('title',)}

    date_hierarchy = 'published'
    ordering = ('status', 'published')


@admin.register(models.Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)
    ordering = ('name',)

@admin.register(models.Series)
class SeriesAdmin(admin.ModelAdmin):
    list_display = ('name',)
    ordering = ('name',)


@admin.register(models.PostSeries)
class PostSeriesAdmin(admin.ModelAdmin):
    list_display = ('post', 'series', 'order_position')
    list_filter = ('series',)
    search_fields = ('post__title', 'series__name')
    ordering = ('series', 'order_position')


@admin.register(models.SkillGroup)
class SkillGroupAdmin(admin.ModelAdmin):
    list_display = ('name',)
    ordering = ('name',)


@admin.register(models.Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ('name', 'rating')
    ordering = ('name',)


@admin.register(models.AccountGroup)
class AccountGroupAdmin(admin.ModelAdmin):
    list_display = ('name',)
    ordering = ('name',)


@admin.register(models.Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ('name', 'group')
    ordering = ('name',)


@admin.register(models.Person)
class PersonAdmin(admin.ModelAdmin):
    pass


@admin.register(models.User)
class UserAdmin(admin.ModelAdmin):
    pass
