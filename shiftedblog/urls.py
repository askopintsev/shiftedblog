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
from django.views.generic import TemplateView

from blog.views import custom_image_upload
from shiftedblog.rate_limited_views import (
    RateLimitedLoginView,
    RateLimitedSetupView,
    RateLimitedQRGeneratorView,
)

import two_factor.urls


app_name = 'blog'

sitemaps = {
    'posts': PostSitemap,
}

zen_html_file = settings.DZEN_VERIFICATION_FILE

# Admin URL path (configurable via ADMIN_URL environment variable)
# Defaults to 'mellon' for backward compatibility
admin_url = getattr(settings, 'ADMIN_URL', 'mellon')

urlpatterns = [
    path("custom-image-upload/", custom_image_upload, name="custom_image_upload"),
    # path("ckeditor5/", include('django_ckeditor_5.urls')),
    path(f'{admin_url}/', admin.site.urls),
    path('', include('blog.urls', namespace='blog')),
    path(
        'sitemap.xml',
        sitemap,
        {'sitemaps': sitemaps},
        name='django.contrib.sitemaps.views.sitemap',
    ),
    # Rate-limited authentication endpoints (override two_factor URLs)
    path('login/', RateLimitedLoginView.as_view(), name='login'),
    path('account/login/', RateLimitedLoginView.as_view(), name='account_login'),
    path('account/two_factor/setup/', RateLimitedSetupView.as_view(), name='setup'),
    path('account/two_factor/qrcode/', RateLimitedQRGeneratorView.as_view(), name='qr'),
    # Include other two-factor URLs (backup, disable, etc.)
    path('', include((two_factor.urls.urlpatterns), namespace='two_factor')),
    path('robots.txt', TemplateView.as_view(template_name='static_html/robots.txt', content_type='text/plain')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT,)

if settings.DZEN_VERIFICATION_FILE:
    urlpatterns.append(
        path(
            settings.DZEN_VERIFICATION_FILE,
            TemplateView.as_view(template_name=f"static_html/{settings.DZEN_VERIFICATION_FILE}"),
            name="zen_static_page",
        )
    )

handler400 = 'blog.views.custom_bad_request_view'
handler403 = 'blog.views.custom_permission_denied_view'
handler404 = 'blog.views.custom_page_not_found_view'
handler500 = 'blog.views.custom_error_view'
