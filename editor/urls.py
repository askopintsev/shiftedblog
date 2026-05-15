from django.urls import path

from editor import views

app_name = "editor"

urlpatterns = [
    path("draft/<uuid:uuid>/", views.post_detail_by_uuid, name="post_detail_by_uuid"),
]
