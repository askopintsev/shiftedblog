from django.urls import path
from blog import views

app_name = 'blog'

urlpatterns = [
    # post views
    path('', views.post_list, name='post_list'),
    path('category/<slug:category_slug>/', views.post_list, name='post_list_by_category'),
    path('tag/<slug:tag_slug>/', views.post_list, name='post_list_by_tag'),
    path('<int:year>/<int:month>/<int:day>/<slug:post>/',
         views.post_detail,
         name='post_detail'),
    path('search/', views.post_search, name='post_search'),
    path('about', views.about, name='about'),
]
