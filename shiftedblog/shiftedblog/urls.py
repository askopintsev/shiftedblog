"""shiftedblog URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.contrib.sitemaps.views import sitemap
from blog.sitemap import PostSitemap

from django.conf import settings
from django.conf.urls.static import static


app_name = 'blog'

sitemaps = {
    'posts': PostSitemap,
}

urlpatterns = [
    path('mellon/', admin.site.urls),
    path('', include('blog.urls', namespace='blog')),
    path('sitemap.xml',
         sitemap,
         {'sitemaps': sitemaps},
         name='django.contrib.sitemaps.views.sitemap')
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler404 = 'blog.views.custom_page_not_found_view'
handler500 = 'blog.views.custom_error_view'
handler403 = 'blog.views.custom_permission_denied_view'
handler400 = 'blog.views.custom_bad_request_view'
