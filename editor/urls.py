from django.urls import path

from editor import views

app_name = "editor"

urlpatterns = [
    path("", views.post_list, name="post_list"),
    path(
        "category/<slug:category_slug>/",
        views.post_list,
        name="post_list_by_category",
    ),
    path("tag/<slug:tag_slug>/", views.post_list, name="post_list_by_tag"),
    path("search/", views.post_search, name="post_search"),
    path("draft/<uuid:uuid>/", views.post_detail_by_uuid, name="post_detail_by_uuid"),
    path("<slug>/", views.post_detail, name="post_detail"),
]
