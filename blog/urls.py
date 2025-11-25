from django.contrib import admin
from django.urls import path
from blog import views

app_name = 'blog'

# Admin site customization
admin.site.site_header = 'Shifted Blog'
admin.site.site_title = 'Admin dashboard'
admin.site.index_title = 'Shifted Blog'

urlpatterns = [
    # post views
    path('', views.post_list, name='post_list'),
    path('category/<slug:category_slug>/', views.post_list, name='post_list_by_category'),
    path('tag/<slug:tag_slug>/', views.post_list, name='post_list_by_tag'),
    path('search/', views.post_search, name='post_search'),
    path('about', views.about, name='about'),
    path('<slug>/', views.post_detail, name='post_detail'),
]
