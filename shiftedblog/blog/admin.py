from django.contrib import admin
from blog.models import Post, Category


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    class Media:
        css = {
            "all": ("css/custom_admin.css",)
        }
        js = ("js/tinymce.js",)

    list_display = ('title', 'slug', 'author', 'published', 'status')
    list_filter = ('status', 'created', 'published', 'author')
    search_fields = ('title', 'body')
    prepopulated_fields = {'slug': ('title',)}
    raw_id_fields = ('author',)
    date_hierarchy = 'published'
    ordering = ('status', 'published')


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)
    ordering = ('name',)


