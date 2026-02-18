from django.urls import path

from team import views

app_name = "team"

urlpatterns = [
    path("about", views.about, name="about"),
]
