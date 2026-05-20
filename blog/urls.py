from django.urls import path

from blog import views
from blog.feeds import LatestPostsFeed

app_name = "blog"

urlpatterns = [
    path("", views.post_list, name="post_list"),
    path("sitemap/", views.html_sitemap, name="html_sitemap"),
    path("feed/", LatestPostsFeed(), name="feed"),
    path(
        "category/<slug:category_slug>/",
        views.post_list,
        name="post_list_by_category",
    ),
    path("tag/<slug:tag_slug>/", views.post_list, name="post_list_by_tag"),
    path("search/", views.post_search, name="post_search"),
    path("lenta/", views.post_feed_lenta, name="post_lenta"),
    path("og-image/<slug>.jpg", views.post_og_image, name="post_og_image"),
    path("<slug>/", views.post_detail, name="post_detail"),
]
